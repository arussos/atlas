"""
M4.2a — Livello di validazione dei boundary candidate.

Calcola metriche strutturali a partire da una run di generazione candidate
e verifica l'invariante sul conteggio dei candidate
(docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md, sezioni projection /
candidate-count-invariant):

    candidates_in_conversation == max(visible_dialogue_message_count - 1, 0)

per ogni conversazione, e la somma corpus-wide della stessa. L'invariante è
calcolato contro il conteggio dei messaggi dialogue *visibili proiettati*,
non contro il conteggio grezzo dei nodi-messaggio del current path — vedi
tools/episodes/projection.py. La validazione generica non dipende mai da
numeri specifici di un baseline — il confronto col baseline è opt-in,
selezionato esplicitamente dal chiamante, rispecchiando
tools/chatgpt/validation.py.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import CANDIDATE_CLASS_HIGH, CANDIDATE_CLASS_LOW, CANDIDATE_CLASS_MEDIUM
from .timegap import TIME_GAP_BUCKET_UNKNOWN

# Baseline nota per l'output ACNF M4.1 di CHATGPT-ACQ-001, semantica RC2
# (dialogue timeline projection) — vedi
# docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md. Usata solo quando
# richiesta esplicitamente via --expected-baseline; mai applicata di
# default, e mai referenziata dalla logica generica di metriche/invarianti.
# Ha soppiantato la baseline RC1 di 31902 candidate, che generava candidate
# contro i nodi-messaggio grezzi del current path, inclusi i nodi non
# visibili thoughts/reasoning_recap.
EXPECTED_BASELINES: Dict[str, Dict[str, int]] = {
    "chatgpt-acq-001": {
        "conversations_processed": 777,
        "current_path_message_nodes": 32679,
        "visible_dialogue_messages": 26187,
        "non_visible_current_path_message_nodes": 6492,
        "candidates": 25410,
    },
}


@dataclass
class ValidationReport:
    metrics: Dict[str, int]
    anomalies: List[Dict[str, Any]]
    invariant_violations: List[str]
    expected_baseline_name: Optional[str]
    expected: Optional[Dict[str, int]]
    gate_results: List[Dict[str, Any]]
    passed: bool
    validated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": self.metrics,
            "anomalies": self.anomalies,
            "invariant_violations": self.invariant_violations,
            "expected_baseline_name": self.expected_baseline_name,
            "expected_baseline": self.expected,
            "gate_results": self.gate_results,
            "passed": self.passed,
            "validated_at": self.validated_at,
        }


def compute_metrics(
    candidates: List[Any],
    conversations_processed: int,
    current_path_message_nodes: int,
    visible_dialogue_messages: int,
) -> Dict[str, int]:
    """Calcola metriche strutturali generiche, indipendenti dal baseline."""
    low = sum(1 for c in candidates if c.candidate_class == CANDIDATE_CLASS_LOW)
    medium = sum(1 for c in candidates if c.candidate_class == CANDIDATE_CLASS_MEDIUM)
    high = sum(1 for c in candidates if c.candidate_class == CANDIDATE_CLASS_HIGH)

    with_time_gap = sum(1 for c in candidates if c.time_gap_bucket != TIME_GAP_BUCKET_UNKNOWN)
    with_opening_marker = sum(1 for c in candidates if c.explicit_opening_markers)
    with_closure_marker = sum(1 for c in candidates if c.explicit_closure_markers)
    with_resume_marker = sum(1 for c in candidates if c.explicit_resume_markers)
    with_transition_marker = sum(1 for c in candidates if c.explicit_transition_markers)
    # "Lexical feature presente" significa che entrambi i lati avevano
    # testo estraibile, quindi il confronto di Jaccard trasportava un
    # segnale reale e non uno dei casi limite di input vuoto definiti (vedi
    # tools/episodes/lexical.py).
    with_lexical_feature = sum(1 for c in candidates if c.before_text_length > 0 and c.after_text_length > 0)

    candidates_with_intermediate_nodes = sum(1 for c in candidates if c.intermediate_node_count > 0)
    intermediate_nodes_skipped_total = sum(c.intermediate_node_count for c in candidates)

    return {
        "conversations_processed": conversations_processed,
        "current_path_message_nodes": current_path_message_nodes,
        "visible_dialogue_messages": visible_dialogue_messages,
        "non_visible_current_path_message_nodes": current_path_message_nodes - visible_dialogue_messages,
        # "candidates" è la metrica principale/alias per il conteggio dei
        # boundary candidate proiettati (== len(candidates) == somma per
        # conversazione di max(visible_dialogue_messages - 1, 0)) — vedi
        # doc, sezione candidate count invariant.
        "candidates": len(candidates),
        "candidates_with_intermediate_nodes": candidates_with_intermediate_nodes,
        "intermediate_nodes_skipped_total": intermediate_nodes_skipped_total,
        "low_candidates": low,
        "medium_candidates": medium,
        "high_candidates": high,
        "with_time_gap": with_time_gap,
        "with_opening_marker": with_opening_marker,
        "with_closure_marker": with_closure_marker,
        "with_resume_marker": with_resume_marker,
        "with_transition_marker": with_transition_marker,
        "with_lexical_feature": with_lexical_feature,
    }


def check_invariant(
    per_conversation_visible_message_counts: Dict[str, int],
    per_conversation_candidate_counts: Dict[str, int],
) -> List[str]:
    """
    Verifica, per ogni conversazione, che candidates == max(visible_dialogue_messages - 1, 0).
    Restituisce descrizioni leggibili delle violazioni; una lista vuota
    significa che l'invariante vale ovunque.
    """
    violations: List[str] = []
    for conversation_id, visible_message_count in per_conversation_visible_message_counts.items():
        expected = max(visible_message_count - 1, 0)
        actual = per_conversation_candidate_counts.get(conversation_id, 0)
        if actual != expected:
            violations.append(
                f"conversation_id={conversation_id}: expected {expected} candidates "
                f"({visible_message_count} visible dialogue messages), got {actual}"
            )
    return violations


def validate(
    candidates: List[Any],
    anomalies: List[Any],
    conversations_processed: int,
    current_path_message_nodes: int,
    visible_dialogue_messages: int,
    per_conversation_visible_message_counts: Dict[str, int],
    per_conversation_candidate_counts: Dict[str, int],
    expected: Optional[Dict[str, int]] = None,
    expected_baseline_name: Optional[str] = None,
) -> ValidationReport:
    """
    Costruisce un ValidationReport. La validazione fallisce se l'invariante
    sul conteggio dei candidate è violato per qualche conversazione, se è
    stata registrata qualche anomalia strutturale, o se un gate di
    expected-baseline fornito diverge.
    """
    metrics = compute_metrics(
        candidates, conversations_processed, current_path_message_nodes, visible_dialogue_messages
    )
    metrics["structural_anomalies"] = len(anomalies)

    invariant_violations = check_invariant(per_conversation_visible_message_counts, per_conversation_candidate_counts)

    gate_results: List[Dict[str, Any]] = []
    passed = not invariant_violations and not anomalies

    if expected is not None:
        for key in expected:
            actual = metrics.get(key)
            ok = actual == expected[key]
            if not ok:
                passed = False
            gate_results.append({"metric": key, "expected": expected[key], "actual": actual, "passed": ok})

    anomaly_dicts = [a.to_dict() for a in anomalies]

    return ValidationReport(
        metrics=metrics,
        anomalies=anomaly_dicts,
        invariant_violations=invariant_violations,
        expected_baseline_name=expected_baseline_name,
        expected=expected,
        gate_results=gate_results,
        passed=passed,
        validated_at=datetime.now(timezone.utc).isoformat(),
    )


def write_validation_json(report: ValidationReport, output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, sort_keys=True, ensure_ascii=False, indent=2)
        f.write("\n")
