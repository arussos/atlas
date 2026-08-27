"""
M4.2a — Deterministic Boundary Candidate Engine.

Consuma ACNF v0.1 (conversations.jsonl, nodes.jsonl) prodotto da M4.1,
proietta la sequenza di nodi-messaggio del current path sulla sua
sottosequenza dialogue visibile (tools/episodes/projection.py — la
Dialogue Timeline Projection), e produce esattamente un record
BoundaryCandidate per ogni coppia consecutiva di nodi dialogue visibili,
per conversazione. Nessun boundary attraversa un confine tra conversazioni.
Nessun LLM, embedding o inferenza generativa viene usato in nessun punto
di questo modulo — vedi docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md.

candidate_class (LOW/MEDIUM/HIGH) è evidenza deterministica, non una
decisione di episodio — SAME_EPISODE / NEW_EPISODE / UNCERTAIN è compito
di M4.2b. Vedi la sezione "Boundary Evidence Score" della documentazione
per la semantica corretta di candidate_score: non è una probabilità di
boundary semantico.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from . import validation as validation_mod
from .graph import reconstruct_current_path
from .hashing import compute_candidate_hash, compute_candidate_id
from .lexical import lexical_features
from .markers import CLOSURE_MARKERS, OPENING_MARKERS, RESUME_MARKERS, TRANSITION_MARKERS, find_markers
from .models import FEATURE_VERSION, Anomaly, BoundaryCandidate
from .projection import project_dialogue_timeline
from .scoring import DEFAULT_SCORE_CONFIG, BoundaryScoreConfig, classify_candidate, compute_candidate_score
from .text import extract_visible_text
from .timegap import compute_time_gap


def _read_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _format_time_gap_reason(seconds: float) -> str:
    """Reason leggibile per il time-gap, es. "time_gap=14.2h" — unità adattiva, 1 decimale."""
    if seconds < 60:
        return f"time_gap={seconds:.1f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"time_gap={minutes:.1f}m"
    hours = seconds / 3600
    if hours < 24:
        return f"time_gap={hours:.1f}h"
    days = seconds / 86400
    return f"time_gap={days:.1f}d"


def _index_nodes_by_conversation(
    nodes: Iterable[Dict[str, Any]], anomalies: List[Anomaly]
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Raggruppa i nodi ACNF per conversation_id, poi per node_id (node_id è
    univoco solo all'interno di una conversazione, non globalmente — stessa
    convenzione di tools/chatgpt). Un node_id duplicato all'interno della
    stessa conversazione è un'anomalia strutturale: la seconda occorrenza
    viene scartata, senza mai sovrascrivere silenziosamente la prima.
    """
    by_conversation: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for node in nodes:
        conversation_id = node.get("conversation_id")
        node_id = node.get("node_id")
        bucket = by_conversation.setdefault(conversation_id, {})
        if node_id in bucket:
            anomalies.append(
                Anomaly(
                    "duplicate_node_id",
                    conversation_id,
                    node_id,
                    "Duplicate node_id found within the same conversation in nodes.jsonl",
                )
            )
            continue
        bucket[node_id] = node
    return by_conversation


def select_current_path_message_nodes(
    ordered_node_ids: List[str],
    conversation_nodes: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Selezione autorevole dei nodi-messaggio del current path (doc M4.2a,
    sezione input selection): has_message == true, is_current_path ==
    true, is_technical_root == false. Per costruzione ogni nodo prodotto
    dal walk su parent_id (reconstruct_current_path) è già sul current
    path; questo filtro è la guardia finale ed esplicita contro
    l'inclusione silenziosa di un nodo malformato/inconsistente invece
    della sua esclusione.

    Restituisce l'insieme completo dei nodi-messaggio del current path —
    visibili e non visibili insieme — nell'ordine esatto di
    ordered_node_ids (ordine di grafo): nessun sort, nessun uso dei
    timestamp, nessuna policy di visibilità (quella resta in
    tools/episodes/projection.py, a valle).

    Helper pubblico di proposito: è l'unica sede della policy di input
    selection, riusata sia da generate_boundary_candidates (M4.2a) sia
    da tools/retrieval_units (M5.1) — mai duplicarne il predicato.
    """
    return [
        conversation_nodes[node_id]
        for node_id in ordered_node_ids
        if conversation_nodes[node_id].get("has_message") is True
        and conversation_nodes[node_id].get("is_current_path") is True
        and conversation_nodes[node_id].get("is_technical_root") is False
    ]


def _build_candidate(
    conversation_id: str,
    sequence_index: int,
    before_node: Dict[str, Any],
    after_node: Dict[str, Any],
    intermediate_nodes: List[Dict[str, Any]],
    config: BoundaryScoreConfig,
) -> BoundaryCandidate:
    before_text = extract_visible_text(before_node.get("content_type"), before_node.get("content"))
    after_text = extract_visible_text(after_node.get("content_type"), after_node.get("content"))

    # Il lato del matching dei marker è una decisione di design documentata
    # — vedi il docstring del modulo tools/episodes/markers.py: i closure
    # marker chiudono il messaggio precedente (before_text); i marker
    # opening/resume/transition descrivono come inizia il messaggio
    # successivo (after_text).
    opening_markers = find_markers(after_text, OPENING_MARKERS)
    closure_markers = find_markers(before_text, CLOSURE_MARKERS)
    resume_markers = find_markers(after_text, RESUME_MARKERS)
    transition_markers = find_markers(after_text, TRANSITION_MARKERS)

    lexical_similarity, lexical_shift_score = lexical_features(before_text, after_text)

    time_gap_seconds, time_gap_bucket = compute_time_gap(
        before_node.get("created_at"), after_node.get("created_at")
    )

    candidate_score = compute_candidate_score(
        time_gap_bucket=time_gap_bucket,
        opening_markers=opening_markers,
        closure_markers=closure_markers,
        resume_markers=resume_markers,
        transition_markers=transition_markers,
        lexical_shift_score=lexical_shift_score,
        config=config,
    )
    candidate_class = classify_candidate(candidate_score, config=config)

    reasons: List[str] = []
    if time_gap_seconds is not None:
        reasons.append(_format_time_gap_reason(time_gap_seconds))
    else:
        reasons.append("time_gap=unknown")
    for marker in opening_markers:
        reasons.append(f"opening_marker={marker}")
    for marker in closure_markers:
        reasons.append(f"closure_marker={marker}")
    for marker in resume_markers:
        reasons.append(f"resume_marker={marker}")
    for marker in transition_markers:
        reasons.append(f"transition_marker={marker}")
    reasons.append(f"lexical_shift={lexical_shift_score:.2f}")

    before_node_id = before_node.get("node_id")
    after_node_id = after_node.get("node_id")

    # Solo provenance — mai contenuto. Vedi tools/episodes/projection.py
    # e docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md, sezione intermediate
    # node provenance. L'ordine originale del current path è preservato.
    intermediate_node_ids = [node.get("node_id") for node in intermediate_nodes]
    intermediate_content_types = [node.get("content_type") for node in intermediate_nodes]
    intermediate_node_count = len(intermediate_nodes)

    candidate_id = compute_candidate_id(
        conversation_id=conversation_id,
        before_node_id=before_node_id,
        after_node_id=after_node_id,
        feature_version=FEATURE_VERSION,
    )

    # candidate_hash copre l'intero contenuto canonico eccetto se stesso
    # (auto-referenziale) — in questo schema non esistono metadati
    # operativi/wall-clock da escludere. La provenance dei nodi intermedi
    # partecipa all'hash: saltare un insieme diverso di nodi non visibili
    # tra la stessa coppia before/after è un candidate materialmente
    # diverso.
    payload: Dict[str, Any] = {
        "candidate_id": candidate_id,
        "conversation_id": conversation_id,
        "before_node_id": before_node_id,
        "after_node_id": after_node_id,
        "before_message_id": before_node.get("message_id"),
        "after_message_id": after_node.get("message_id"),
        "sequence_index": sequence_index,
        "before_role": before_node.get("role"),
        "after_role": after_node.get("role"),
        "before_created_at": before_node.get("created_at"),
        "after_created_at": after_node.get("created_at"),
        "time_gap_seconds": time_gap_seconds,
        "time_gap_bucket": time_gap_bucket,
        "explicit_opening_markers": opening_markers,
        "explicit_closure_markers": closure_markers,
        "explicit_resume_markers": resume_markers,
        "explicit_transition_markers": transition_markers,
        "lexical_similarity": lexical_similarity,
        "lexical_shift_score": lexical_shift_score,
        "before_text_length": len(before_text),
        "after_text_length": len(after_text),
        "candidate_score": candidate_score,
        "candidate_class": candidate_class,
        "reasons": reasons,
        "intermediate_node_ids": intermediate_node_ids,
        "intermediate_content_types": intermediate_content_types,
        "intermediate_node_count": intermediate_node_count,
        "feature_version": FEATURE_VERSION,
    }

    candidate_hash = compute_candidate_hash(payload)

    return BoundaryCandidate(candidate_hash=candidate_hash, **payload)


def generate_boundary_candidates(
    conversations: List[Dict[str, Any]],
    nodes: List[Dict[str, Any]],
    config: BoundaryScoreConfig = DEFAULT_SCORE_CONFIG,
) -> Tuple[List[BoundaryCandidate], List[Anomaly], Dict[str, int], Dict[str, int], Dict[str, int]]:
    """
    Elabora ogni conversazione in modo indipendente, nell'ordine di
    conversations.jsonl (esso stesso deterministico, ereditato da M4.1).
    Per ogni conversazione, ricostruisce il current path, poi lo proietta
    sulla sua sottosequenza dialogue visibile (tools/episodes/projection.py)
    prima di generare i candidate — i candidate collegano nodi *visibili*
    consecutivi, mai nodi-messaggio grezzi del current path.

    Restituisce (candidates, anomalies,
    per_conversation_current_path_message_counts,
    per_conversation_visible_message_counts,
    per_conversation_candidate_counts).
    """
    anomalies: List[Anomaly] = []
    nodes_by_conversation = _index_nodes_by_conversation(nodes, anomalies)

    all_candidates: List[BoundaryCandidate] = []
    per_conversation_current_path_message_counts: Dict[str, int] = {}
    per_conversation_visible_message_counts: Dict[str, int] = {}
    per_conversation_candidate_counts: Dict[str, int] = {}

    for conversation in conversations:
        conversation_id = conversation.get("conversation_id")
        current_node_id = conversation.get("current_node_id")
        conversation_nodes = nodes_by_conversation.get(conversation_id, {})

        ordered_node_ids, path_anomalies = reconstruct_current_path(
            conversation_id, current_node_id, conversation_nodes
        )
        anomalies.extend(path_anomalies)

        # Selezione autorevole condivisa (vedi il docstring dell'helper):
        # insieme completo dei nodi-messaggio del current path, visibili
        # e non visibili insieme; la projection avviene dopo.
        message_nodes = select_current_path_message_nodes(ordered_node_ids, conversation_nodes)

        per_conversation_current_path_message_counts[conversation_id] = len(message_nodes)

        visible_nodes, intermediates_before = project_dialogue_timeline(message_nodes)
        per_conversation_visible_message_counts[conversation_id] = len(visible_nodes)

        conversation_candidates = [
            _build_candidate(
                conversation_id,
                i,
                visible_nodes[i],
                visible_nodes[i + 1],
                intermediates_before[i + 1],
                config,
            )
            for i in range(len(visible_nodes) - 1)
        ]

        per_conversation_candidate_counts[conversation_id] = len(conversation_candidates)
        all_candidates.extend(conversation_candidates)

    return (
        all_candidates,
        anomalies,
        per_conversation_current_path_message_counts,
        per_conversation_visible_message_counts,
        per_conversation_candidate_counts,
    )


def write_output(candidates: List[BoundaryCandidate], output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "boundary_candidates.jsonl", "w", encoding="utf-8") as f:
        for candidate in candidates:
            f.write(json.dumps(candidate.to_dict(), sort_keys=True, ensure_ascii=False))
            f.write("\n")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic boundary candidates from ACNF v0.1 (M4.2a)"
    )
    parser.add_argument("acnf_dir", type=Path, help="Directory containing conversations.jsonl and nodes.jsonl")
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Directory to write boundary_candidates.jsonl and boundary_validation.json into",
    )
    parser.add_argument(
        "--expected-baseline",
        choices=sorted(validation_mod.EXPECTED_BASELINES.keys()),
        default=None,
        help="Compare validation metrics against a known baseline (e.g. chatgpt-acq-001)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    conversations = list(_read_jsonl(args.acnf_dir / "conversations.jsonl"))
    nodes = list(_read_jsonl(args.acnf_dir / "nodes.jsonl"))

    (
        candidates,
        anomalies,
        per_conv_current_path_messages,
        per_conv_visible_messages,
        per_conv_candidates,
    ) = generate_boundary_candidates(conversations, nodes)

    write_output(candidates, args.output_dir)

    expected = validation_mod.EXPECTED_BASELINES.get(args.expected_baseline) if args.expected_baseline else None
    report = validation_mod.validate(
        candidates,
        anomalies,
        conversations_processed=len(conversations),
        current_path_message_nodes=sum(per_conv_current_path_messages.values()),
        visible_dialogue_messages=sum(per_conv_visible_messages.values()),
        per_conversation_visible_message_counts=per_conv_visible_messages,
        per_conversation_candidate_counts=per_conv_candidates,
        expected=expected,
        expected_baseline_name=args.expected_baseline,
    )
    validation_mod.write_validation_json(report, args.output_dir / "boundary_validation.json")

    print(f"Processed {len(conversations)} conversations, produced {len(candidates)} boundary candidates")
    print(f"Anomalies: {len(anomalies)}")
    if expected is not None:
        print(f"Baseline validation ({args.expected_baseline}): {'PASSED' if report.passed else 'FAILED'}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
