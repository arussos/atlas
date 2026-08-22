"""
M4.2b-A — Gold Pilot evaluator.

Confronta gli esiti prodotti dal resolver (resolutions.jsonl) contro le
etichette manuali del Gold Pilot (gold-pilot-labeled.jsonl), MAI contro
candidate_class di M4.2a. Un resolver che si limitasse a mappare
HIGH -> BOUNDARY / LOW -> SAME_EPISODE sarebbe architetturalmente
invalido anche se qualche metrica campionaria migliorasse — vedi
docs/M4.2B_SEMANTIC_BOUNDARY_RESOLVER.md.

Nessun dato reale del Gold Pilot è incluso in questo repository: questo
modulo opera solo su file esterni forniti dall'utente. Solo libreria
standard, nessuna dipendenza ML.
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from tools.semantic_boundary.models import (
    DECISION_BOUNDARY,
    DECISION_SAME_EPISODE,
    DECISION_UNCERTAIN,
    SemanticBoundaryError,
    VALID_DECISIONS,
    validate_confidence,
    validate_decision,
)

GOLD_LABEL_TRUE = "TRUE"
GOLD_LABEL_FALSE = "FALSE"
GOLD_LABEL_AMBIGUOUS = "AMBIGUOUS"

VALID_GOLD_LABELS = frozenset({GOLD_LABEL_TRUE, GOLD_LABEL_FALSE, GOLD_LABEL_AMBIGUOUS})

# Mappatura Gold Pilot -> decisione attesa (sezione 14 del mandato M4.2b-A).
GOLD_LABEL_TO_EXPECTED_DECISION = {
    GOLD_LABEL_TRUE: DECISION_BOUNDARY,
    GOLD_LABEL_FALSE: DECISION_SAME_EPISODE,
    GOLD_LABEL_AMBIGUOUS: DECISION_UNCERTAIN,
}


class EvaluationDataError(SemanticBoundaryError):
    """Sollevata per record malformati, mancanti o duplicati nei dataset di valutazione."""


@dataclass
class GoldRecord:
    candidate_id: str
    gold_label: str

    @property
    def expected_decision(self) -> str:
        return GOLD_LABEL_TO_EXPECTED_DECISION[self.gold_label]


@dataclass
class ResolutionRecord:
    candidate_id: str
    decision: str
    confidence: float


@dataclass
class PrecisionRecallF1:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


@dataclass
class EvaluationReport:
    total_gold_records: int
    total_resolution_records: int
    matched_records: int
    exact_matches: int
    accuracy: float
    confusion_matrix: Dict[str, Dict[str, int]]
    boundary_metrics: PrecisionRecallF1
    same_episode_metrics: PrecisionRecallF1
    expected_uncertain_count: int
    actual_uncertain_count: int
    gold_only_candidate_ids: List[str] = field(default_factory=list)
    resolution_only_candidate_ids: List[str] = field(default_factory=list)

    NOTE = (
        "Gold Pilot 001 is a pilot diagnostic set (N=60, only 5 TRUE cases), "
        "not a statistically robust benchmark. Treat these metrics as directional."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "note": self.NOTE,
            "total_gold_records": self.total_gold_records,
            "total_resolution_records": self.total_resolution_records,
            "matched_records": self.matched_records,
            "exact_matches": self.exact_matches,
            "accuracy": self.accuracy,
            "confusion_matrix": self.confusion_matrix,
            "boundary_metrics": self.boundary_metrics.to_dict(),
            "same_episode_metrics": self.same_episode_metrics.to_dict(),
            "expected_uncertain_count": self.expected_uncertain_count,
            "actual_uncertain_count": self.actual_uncertain_count,
            "gold_only_candidate_ids": self.gold_only_candidate_ids,
            "resolution_only_candidate_ids": self.resolution_only_candidate_ids,
        }


def _load_jsonl(path: str) -> List[Tuple[int, Dict[str, Any]]]:
    records: List[Tuple[int, Dict[str, Any]]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvaluationDataError(f"{path}:{line_number}: invalid JSON ({exc})") from exc
            if not isinstance(record, dict):
                raise EvaluationDataError(f"{path}:{line_number}: record must be a JSON object")
            records.append((line_number, record))
    return records


def load_gold_records(path: str) -> Dict[str, GoldRecord]:
    """
    Carica il Gold Pilot etichettato manualmente. Ogni riga deve avere
    almeno {"candidate_id": ..., "gold_label": "TRUE"|"FALSE"|"AMBIGUOUS"}.
    candidate_id duplicato, mancante o gold_label invalido/mancante sono
    errori espliciti, mai record scartati silenziosamente.
    """
    records: Dict[str, GoldRecord] = {}
    for line_number, raw in _load_jsonl(path):
        candidate_id = raw.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise EvaluationDataError(f"{path}:{line_number}: missing or invalid candidate_id")
        gold_label = raw.get("gold_label")
        if gold_label not in VALID_GOLD_LABELS:
            raise EvaluationDataError(
                f"{path}:{line_number}: invalid gold_label {gold_label!r} "
                f"for candidate_id={candidate_id!r}, must be one of {sorted(VALID_GOLD_LABELS)}"
            )
        if candidate_id in records:
            raise EvaluationDataError(f"{path}:{line_number}: duplicate candidate_id {candidate_id!r}")
        records[candidate_id] = GoldRecord(candidate_id=candidate_id, gold_label=gold_label)
    return records


def load_resolution_records(path: str) -> Dict[str, ResolutionRecord]:
    """
    Carica gli esiti di risoluzione prodotti dal resolver. Ogni riga deve
    avere almeno {"candidate_id", "decision", "confidence"}. decision
    invalida, confidence fuori [0,1], candidate_id mancante o duplicato
    sono errori espliciti.
    """
    records: Dict[str, ResolutionRecord] = {}
    for line_number, raw in _load_jsonl(path):
        candidate_id = raw.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise EvaluationDataError(f"{path}:{line_number}: missing or invalid candidate_id")

        decision = raw.get("decision")
        try:
            validate_decision(decision)
        except SemanticBoundaryError as exc:
            raise EvaluationDataError(
                f"{path}:{line_number}: candidate_id={candidate_id!r}: {exc}"
            ) from exc

        confidence = raw.get("confidence")
        try:
            validate_confidence(confidence)
        except SemanticBoundaryError as exc:
            raise EvaluationDataError(
                f"{path}:{line_number}: candidate_id={candidate_id!r}: {exc}"
            ) from exc

        if candidate_id in records:
            raise EvaluationDataError(f"{path}:{line_number}: duplicate candidate_id {candidate_id!r}")

        records[candidate_id] = ResolutionRecord(
            candidate_id=candidate_id, decision=decision, confidence=float(confidence)
        )
    return records


def _compute_prf(tp: int, fp: int, fn: int) -> PrecisionRecallF1:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return PrecisionRecallF1(
        true_positives=tp, false_positives=fp, false_negatives=fn,
        precision=precision, recall=recall, f1=f1,
    )


def evaluate(gold_path: str, resolutions_path: str) -> EvaluationReport:
    gold_records = load_gold_records(gold_path)
    resolution_records = load_resolution_records(resolutions_path)

    gold_ids = set(gold_records)
    resolution_ids = set(resolution_records)
    matched_ids = sorted(gold_ids & resolution_ids)
    gold_only_ids = sorted(gold_ids - resolution_ids)
    resolution_only_ids = sorted(resolution_ids - gold_ids)

    confusion_matrix: Dict[str, Dict[str, int]] = {
        expected: {actual: 0 for actual in sorted(VALID_DECISIONS)}
        for expected in sorted(VALID_DECISIONS)
    }

    exact_matches = 0
    expected_uncertain_count = 0
    actual_uncertain_count = 0

    for candidate_id in matched_ids:
        gold = gold_records[candidate_id]
        resolution = resolution_records[candidate_id]
        expected = gold.expected_decision
        actual = resolution.decision

        confusion_matrix[expected][actual] += 1
        if expected == actual:
            exact_matches += 1
        if expected == DECISION_UNCERTAIN:
            expected_uncertain_count += 1
        if actual == DECISION_UNCERTAIN:
            actual_uncertain_count += 1

    matched_count = len(matched_ids)
    accuracy = exact_matches / matched_count if matched_count > 0 else 0.0

    def _class_counts(target: str) -> Tuple[int, int, int]:
        tp = confusion_matrix[target][target]
        fp = sum(
            confusion_matrix[expected][target]
            for expected in VALID_DECISIONS
            if expected != target
        )
        fn = sum(
            confusion_matrix[target][actual]
            for actual in VALID_DECISIONS
            if actual != target
        )
        return tp, fp, fn

    boundary_metrics = _compute_prf(*_class_counts(DECISION_BOUNDARY))
    same_episode_metrics = _compute_prf(*_class_counts(DECISION_SAME_EPISODE))

    return EvaluationReport(
        total_gold_records=len(gold_records),
        total_resolution_records=len(resolution_records),
        matched_records=matched_count,
        exact_matches=exact_matches,
        accuracy=accuracy,
        confusion_matrix=confusion_matrix,
        boundary_metrics=boundary_metrics,
        same_episode_metrics=same_episode_metrics,
        expected_uncertain_count=expected_uncertain_count,
        actual_uncertain_count=actual_uncertain_count,
        gold_only_candidate_ids=gold_only_ids,
        resolution_only_candidate_ids=resolution_only_ids,
    )


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.semantic_boundary.evaluation",
        description="M4.2b-A Gold Pilot evaluator: confronta resolutions.jsonl contro gold-pilot-labeled.jsonl",
    )
    parser.add_argument("gold_pilot_path", help="Path to gold-pilot-labeled.jsonl (external, not committed)")
    parser.add_argument("resolutions_path", help="Path to resolutions.jsonl produced by the resolver")
    args = parser.parse_args(argv)

    try:
        report = evaluate(args.gold_pilot_path, args.resolutions_path)
    except (EvaluationDataError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
