"""
M5.1 — ChatGPT Retrieval Unit Projection engine.

Consuma ACNF v0.1 (acquisition.json, conversations.jsonl, nodes.jsonl)
prodotto da M4.1 e produce record RetrievalUnit deterministici in JSONL.

L'ordine resta autorevole dal grafo: il current path viene ricostruito
con tools/episodes/graph.py (walk su parent_id da current_node_id — mai
un sort su created_at) e proiettato sulla sottosequenza dialogue
visibile con tools/episodes/projection.py (unica policy di visibilità,
VISIBLE_DIALOGUE_CONTENT_TYPES). Questo modulo non riordina mai i nodi
e non implementa una seconda policy di visibilità.

Windowing v0.1: finestre di WINDOW_SIZE=6 nodi visibili, stride
WINDOW_STRIDE=3, ultima finestra eventualmente più corta, mai scartata.
Nessun token count, nessuna soglia di caratteri/tempo, nessun boundary
semantico, nessun uso di M4.2b.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

# Riuso deliberato delle utility stabili M4.2a: ordine del grafo,
# projection di visibilità, estrazione testo, input selection dei
# nodi-messaggio del current path (select_current_path_message_nodes —
# la policy vive solo lì, mai duplicata qui) e raggruppamento nodi per
# conversazione (_index_nodes_by_conversation è interna a M4.2a ma è la
# più piccola API esistente che già fa questo lavoro con la stessa
# semantica di anomalia duplicate_node_id — duplicarla qui creerebbe due
# convenzioni). Nessun import da tools.semantic_boundary / M4.2b.
from tools.episodes.boundary_candidates import (
    _index_nodes_by_conversation,
    select_current_path_message_nodes,
)
from tools.episodes.graph import reconstruct_current_path
from tools.episodes.models import Anomaly
from tools.episodes.projection import project_dialogue_timeline
from tools.episodes.text import extract_visible_text

from .hashing import compute_content_hash, compute_retrieval_unit_id
from .models import (
    PROJECTION_VERSION,
    SOURCE_TYPE_CHATGPT,
    WINDOW_SIZE,
    WINDOW_STRIDE,
    RetrievalUnit,
)

# Separatore tra i blocchi-nodo renderizzati in RetrievalUnit.text.
# Stabile e arbitrario; parte del contratto di rendering v0.1.
_NODE_BLOCK_SEPARATOR = "\n\n"

# Marker di ruolo quando il nodo non trasporta un role (mai osservato per
# nodi dialogue visibili, ma il rendering non deve mai crashare né
# diventare non deterministico).
_UNKNOWN_ROLE = "unknown"


def compute_windows(
    visible_count: int,
    window_size: int = WINDOW_SIZE,
    stride: int = WINDOW_STRIDE,
) -> List[Tuple[int, int]]:
    """
    Restituisce le finestre [start, end) 0-based sulla sequenza dei nodi
    visibili: start a passi di stride, end = min(start + window_size,
    visible_count). La generazione si ferma alla prima finestra che
    include l'ultimo nodo — le code corte non vengono mai scartate, ogni
    nodo visibile appartiene ad almeno una finestra. 0 nodi -> 0 finestre;
    1..window_size nodi -> 1 finestra.
    """
    if visible_count <= 0:
        return []
    windows: List[Tuple[int, int]] = []
    start = 0
    while True:
        end = min(start + window_size, visible_count)
        windows.append((start, end))
        if end >= visible_count:
            return windows
        start += stride


def render_unit_text(visible_nodes: List[Dict[str, Any]]) -> str:
    """
    Rendering deterministico del testo della unit: per ogni nodo visibile
    incluso, in ordine di grafo,

        [<role>]
        <testo estratto da extract_visible_text>

    blocchi uniti da una riga vuota. Nessun riassunto, nessun testo
    generato, nessun nodo tecnico, nessun titolo di conversazione (il
    titolo resta metadata). Ricostruibile dai node_ids contro ACNF.
    """
    blocks = []
    for node in visible_nodes:
        role = node.get("role") or _UNKNOWN_ROLE
        text = extract_visible_text(node.get("content_type"), node.get("content"))
        blocks.append(f"[{role}]\n{text}")
    return _NODE_BLOCK_SEPARATOR.join(blocks)


def _build_unit(
    conversation: Dict[str, Any],
    window_visible_nodes: List[Dict[str, Any]],
    window_intermediates: List[List[Dict[str, Any]]],
    ordinal_start: int,
    *,
    acquisition_id: str,
    acnf_schema_version: str,
) -> RetrievalUnit:
    """
    Costruisce il RetrievalUnit per una finestra di nodi visibili.

    window_intermediates è la fetta di intermediates_before allineata ai
    nodi della finestra ESCLUSO il primo (cioè gli intermedi strettamente
    tra nodi visibili inclusi): gli intermedi prima del primo nodo della
    finestra appartengono alla provenance della coppia precedente, come
    in M4.2a.
    """
    conversation_id = conversation.get("conversation_id")
    node_ids = [node.get("node_id") for node in window_visible_nodes]

    intermediate_node_ids = [
        node.get("node_id")
        for intermediates in window_intermediates
        for node in intermediates
    ]

    text = render_unit_text(window_visible_nodes)

    retrieval_unit_id = compute_retrieval_unit_id(
        projection_version=PROJECTION_VERSION,
        conversation_id=conversation_id,
        node_ids=node_ids,
    )
    content_hash = compute_content_hash(
        retrieval_unit_id=retrieval_unit_id,
        text=text,
        node_hashes=[node.get("node_hash") for node in window_visible_nodes],
        intermediate_node_ids=intermediate_node_ids,
    )

    return RetrievalUnit(
        retrieval_unit_id=retrieval_unit_id,
        projection_version=PROJECTION_VERSION,
        source_type=SOURCE_TYPE_CHATGPT,
        acquisition_id=acquisition_id,
        acnf_schema_version=acnf_schema_version,
        conversation_id=conversation_id,
        source_id=conversation.get("source_id"),
        conversation_title=conversation.get("title"),
        source_conversation_hash=conversation.get("conversation_hash"),
        node_ids=node_ids,
        first_node_id=node_ids[0],
        last_node_id=node_ids[-1],
        ordinal_start=ordinal_start,
        ordinal_end=ordinal_start + len(node_ids) - 1,
        message_count=len(node_ids),
        start_timestamp=window_visible_nodes[0].get("created_at"),
        end_timestamp=window_visible_nodes[-1].get("created_at"),
        intermediate_node_ids=intermediate_node_ids,
        text=text,
        content_hash=content_hash,
    )


def generate_retrieval_units(
    conversations: List[Dict[str, Any]],
    nodes: List[Dict[str, Any]],
    *,
    acquisition_id: str,
    acnf_schema_version: str,
) -> Tuple[List[RetrievalUnit], List[Anomaly], Dict[str, int], Dict[str, int]]:
    """
    Elabora ogni conversazione in modo indipendente, nell'ordine di
    conversations.jsonl (esso stesso deterministico, ereditato da M4.1).
    Per conversazione: ricostruzione current path (ordine di grafo, mai
    timestamp) -> Dialogue Timeline Projection -> finestre 6/3 ->
    RetrievalUnit. Nessuna unit attraversa un confine tra conversazioni.

    Restituisce (units, anomalies,
    per_conversation_visible_message_counts,
    per_conversation_unit_counts). Le unit di una conversazione sono in
    ordine di ordinal_start crescente.
    """
    anomalies: List[Anomaly] = []
    nodes_by_conversation = _index_nodes_by_conversation(nodes, anomalies)

    all_units: List[RetrievalUnit] = []
    per_conversation_visible_counts: Dict[str, int] = {}
    per_conversation_unit_counts: Dict[str, int] = {}

    for conversation in conversations:
        conversation_id = conversation.get("conversation_id")
        conversation_nodes = nodes_by_conversation.get(conversation_id, {})

        ordered_node_ids, path_anomalies = reconstruct_current_path(
            conversation_id, conversation.get("current_node_id"), conversation_nodes
        )
        anomalies.extend(path_anomalies)

        # Input selection autorevole condivisa con M4.2a — il predicato
        # vive solo nell'helper, mai duplicato qui (vedi il suo docstring).
        message_nodes = select_current_path_message_nodes(ordered_node_ids, conversation_nodes)

        visible_nodes, intermediates_before = project_dialogue_timeline(message_nodes)
        per_conversation_visible_counts[conversation_id] = len(visible_nodes)

        conversation_units = [
            _build_unit(
                conversation,
                visible_nodes[start:end],
                intermediates_before[start + 1 : end],
                start,
                acquisition_id=acquisition_id,
                acnf_schema_version=acnf_schema_version,
            )
            for start, end in compute_windows(len(visible_nodes))
        ]

        per_conversation_unit_counts[conversation_id] = len(conversation_units)
        all_units.extend(conversation_units)

    return (
        all_units,
        anomalies,
        per_conversation_visible_counts,
        per_conversation_unit_counts,
    )


def write_output(units: List[RetrievalUnit], output_dir: Path) -> None:
    """Scrive retrieval_units.jsonl con la stessa convenzione JSONL di M4.1/M4.2a
    (una riga per record, sort_keys, ensure_ascii=False): stesso input +
    stessa projection version -> byte identici, in ordine stabile."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "retrieval_units.jsonl", "w", encoding="utf-8") as f:
        for unit in units:
            f.write(json.dumps(unit.to_dict(), sort_keys=True, ensure_ascii=False))
            f.write("\n")


def _read_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Project ACNF v0.1 into deterministic ChatGPT retrieval units (M5.1)"
    )
    parser.add_argument(
        "acnf_dir",
        type=Path,
        help="Directory containing acquisition.json, conversations.jsonl and nodes.jsonl",
    )
    parser.add_argument("output_dir", type=Path, help="Directory to write retrieval_units.jsonl into")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    with open(args.acnf_dir / "acquisition.json", "r", encoding="utf-8") as f:
        acquisition = json.load(f)

    conversations = list(_read_jsonl(args.acnf_dir / "conversations.jsonl"))
    nodes = list(_read_jsonl(args.acnf_dir / "nodes.jsonl"))

    units, anomalies, per_conv_visible, per_conv_units = generate_retrieval_units(
        conversations,
        nodes,
        acquisition_id=acquisition["acquisition_id"],
        acnf_schema_version=acquisition["normalized_schema_version"],
    )

    write_output(units, args.output_dir)

    print(
        f"Processed {len(conversations)} conversations, "
        f"{sum(per_conv_visible.values())} visible dialogue nodes, "
        f"produced {len(units)} retrieval units"
    )
    print(f"Anomalies: {len(anomalies)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
