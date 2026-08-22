"""Test F/G/J: Gold Pilot evaluator (evaluation.py). Solo file locali, nessuna rete."""

import json

import pytest

from tools.semantic_boundary.evaluation import (
    EvaluationDataError,
    evaluate,
    load_gold_records,
    load_resolution_records,
    main,
)
from tools.semantic_boundary.models import DECISION_BOUNDARY, DECISION_SAME_EPISODE, DECISION_UNCERTAIN


def _write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


GOLD_RECORDS = [
    {"candidate_id": "g1", "gold_label": "TRUE"},
    {"candidate_id": "g2", "gold_label": "FALSE"},
    {"candidate_id": "g3", "gold_label": "FALSE"},
    {"candidate_id": "g4", "gold_label": "AMBIGUOUS"},
    {"candidate_id": "g5", "gold_label": "TRUE"},
    {"candidate_id": "g6", "gold_label": "FALSE"},
]

RESOLUTION_RECORDS = [
    {"candidate_id": "g1", "decision": "BOUNDARY", "confidence": 0.9},
    {"candidate_id": "g2", "decision": "SAME_EPISODE", "confidence": 0.8},
    {"candidate_id": "g3", "decision": "BOUNDARY", "confidence": 0.6},
    {"candidate_id": "g4", "decision": "UNCERTAIN", "confidence": 0.3},
    {"candidate_id": "g5", "decision": "SAME_EPISODE", "confidence": 0.4},
    {"candidate_id": "g6", "decision": "SAME_EPISODE", "confidence": 0.95},
]


@pytest.fixture
def gold_path(tmp_path):
    path = tmp_path / "gold-pilot-labeled.jsonl"
    _write_jsonl(path, GOLD_RECORDS)
    return str(path)


@pytest.fixture
def resolutions_path(tmp_path):
    path = tmp_path / "resolutions.jsonl"
    _write_jsonl(path, RESOLUTION_RECORDS)
    return str(path)


def test_load_gold_records_maps_labels_to_expected_decisions(gold_path):
    records = load_gold_records(gold_path)
    assert records["g1"].expected_decision == DECISION_BOUNDARY
    assert records["g2"].expected_decision == DECISION_SAME_EPISODE
    assert records["g4"].expected_decision == DECISION_UNCERTAIN


def test_evaluate_exact_matches_and_accuracy(gold_path, resolutions_path):
    report = evaluate(gold_path, resolutions_path)
    # correct: g1, g2, g4, g6 ; wrong: g3, g5
    assert report.matched_records == 6
    assert report.exact_matches == 4
    assert report.accuracy == pytest.approx(4 / 6)


def test_evaluate_confusion_matrix(gold_path, resolutions_path):
    report = evaluate(gold_path, resolutions_path)
    cm = report.confusion_matrix
    assert cm[DECISION_BOUNDARY][DECISION_BOUNDARY] == 1  # g1
    assert cm[DECISION_BOUNDARY][DECISION_SAME_EPISODE] == 1  # g5 mismatch
    assert cm[DECISION_SAME_EPISODE][DECISION_SAME_EPISODE] == 2  # g2, g6
    assert cm[DECISION_SAME_EPISODE][DECISION_BOUNDARY] == 1  # g3 mismatch
    assert cm[DECISION_UNCERTAIN][DECISION_UNCERTAIN] == 1  # g4


def test_evaluate_boundary_precision_recall_f1(gold_path, resolutions_path):
    report = evaluate(gold_path, resolutions_path)
    metrics = report.boundary_metrics
    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.precision == pytest.approx(0.5)
    assert metrics.recall == pytest.approx(0.5)
    assert metrics.f1 == pytest.approx(0.5)


def test_evaluate_same_episode_precision_recall_f1(gold_path, resolutions_path):
    report = evaluate(gold_path, resolutions_path)
    metrics = report.same_episode_metrics
    assert metrics.true_positives == 2
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.precision == pytest.approx(2 / 3)
    assert metrics.recall == pytest.approx(2 / 3)


def test_evaluate_uncertain_counts(gold_path, resolutions_path):
    report = evaluate(gold_path, resolutions_path)
    assert report.expected_uncertain_count == 1
    assert report.actual_uncertain_count == 1


def test_evaluate_reports_unmatched_ids_without_dropping_them(tmp_path):
    gold_path = tmp_path / "gold.jsonl"
    resolutions_path = tmp_path / "resolutions.jsonl"
    _write_jsonl(gold_path, GOLD_RECORDS + [{"candidate_id": "gold-only", "gold_label": "FALSE"}])
    _write_jsonl(
        resolutions_path,
        RESOLUTION_RECORDS + [{"candidate_id": "resolution-only", "decision": "UNCERTAIN", "confidence": 0.1}],
    )
    report = evaluate(str(gold_path), str(resolutions_path))
    assert report.gold_only_candidate_ids == ["gold-only"]
    assert report.resolution_only_candidate_ids == ["resolution-only"]
    assert report.matched_records == 6


def test_duplicate_candidate_id_in_gold_raises(tmp_path):
    path = tmp_path / "gold.jsonl"
    _write_jsonl(path, GOLD_RECORDS + [{"candidate_id": "g1", "gold_label": "FALSE"}])
    with pytest.raises(EvaluationDataError):
        load_gold_records(str(path))


def test_duplicate_candidate_id_in_resolutions_raises(tmp_path):
    path = tmp_path / "resolutions.jsonl"
    _write_jsonl(path, RESOLUTION_RECORDS + [{"candidate_id": "g1", "decision": "UNCERTAIN", "confidence": 0.1}])
    with pytest.raises(EvaluationDataError):
        load_resolution_records(str(path))


def test_missing_candidate_id_in_gold_raises(tmp_path):
    path = tmp_path / "gold.jsonl"
    _write_jsonl(path, [{"gold_label": "TRUE"}])
    with pytest.raises(EvaluationDataError):
        load_gold_records(str(path))


def test_invalid_gold_label_raises(tmp_path):
    path = tmp_path / "gold.jsonl"
    _write_jsonl(path, [{"candidate_id": "g1", "gold_label": "MAYBE"}])
    with pytest.raises(EvaluationDataError):
        load_gold_records(str(path))


def test_invalid_decision_in_resolutions_raises(tmp_path):
    path = tmp_path / "resolutions.jsonl"
    _write_jsonl(path, [{"candidate_id": "g1", "decision": "NOT_VALID", "confidence": 0.5}])
    with pytest.raises(EvaluationDataError):
        load_resolution_records(str(path))


def test_confidence_out_of_range_in_resolutions_raises(tmp_path):
    path = tmp_path / "resolutions.jsonl"
    _write_jsonl(path, [{"candidate_id": "g1", "decision": "BOUNDARY", "confidence": 1.5}])
    with pytest.raises(EvaluationDataError):
        load_resolution_records(str(path))


def test_malformed_json_line_raises(tmp_path):
    path = tmp_path / "gold.jsonl"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("{not valid json\n")
    with pytest.raises(EvaluationDataError):
        load_gold_records(str(path))


def test_cli_main_prints_json_report(gold_path, resolutions_path, capsys):
    exit_code = main([gold_path, resolutions_path])
    assert exit_code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["matched_records"] == 6
    assert payload["exact_matches"] == 4


def test_cli_main_returns_nonzero_on_data_error(tmp_path, resolutions_path, capsys):
    bad_gold_path = tmp_path / "bad-gold.jsonl"
    _write_jsonl(bad_gold_path, [{"candidate_id": "g1", "gold_label": "NOT_VALID"}])
    exit_code = main([str(bad_gold_path), resolutions_path])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "error:" in captured.err
