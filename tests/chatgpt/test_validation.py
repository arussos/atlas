"""
M4.1 — Tests for tools/chatgpt/validation.py

Covers: generic metric computation (baseline-independent), and opt-in
comparison against a known expected baseline (e.g. CHATGPT-ACQ-001),
including gate divergence failing validation.
"""

from tools.chatgpt.normalizer import normalize_export
from tools.chatgpt.validation import EXPECTED_BASELINES, compute_metrics, validate
from tests.chatgpt.fixtures import write_synthetic_export as _write_synthetic_export


def test_generic_validation_does_not_depend_on_baseline_numbers(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_synthetic_export(zip_path)
    result = normalize_export(zip_path)

    metrics = compute_metrics(result)
    assert metrics["conversations"] == 2
    assert metrics["nodes"] == 9  # 7 branching-fixture nodes + 2 multimodal-fixture nodes
    assert metrics["technical_roots"] == 2
    assert metrics["conversations_with_branches"] == 1
    assert metrics["branching_parents"] == 1
    assert metrics["conversation_asset_mappings"] == 1
    assert metrics["physical_dat_assets"] == 1
    assert metrics["library_files_records"] == 0
    assert metrics["logical_assets"] == 1
    assert metrics["reference_only_assets"] == 0


def test_validate_passes_without_baseline_when_no_anomalies(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_synthetic_export(zip_path)
    result = normalize_export(zip_path)

    report = validate(result, expected=None)
    assert report.passed is True
    assert report.gate_results == []


def test_validate_fails_on_gate_divergence(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_synthetic_export(zip_path)
    result = normalize_export(zip_path)

    wrong_expected = {"conversations": 999}
    report = validate(result, expected=wrong_expected)
    assert report.passed is False
    assert report.gate_results[0]["passed"] is False


def test_validate_passes_when_gate_matches(tmp_path):
    zip_path = tmp_path / "export.zip"
    _write_synthetic_export(zip_path)
    result = normalize_export(zip_path)

    matching_expected = {"conversations": 2, "nodes": 9}
    report = validate(result, expected=matching_expected)
    assert report.passed is True
    assert all(g["passed"] for g in report.gate_results)


def test_validate_fails_when_anomalies_present():
    class FakeResult:
        conversations = []
        nodes = []
        assets = []
        library_files = []
        anomalies = []
        conversation_asset_file_names_count = 0
        physical_dat_asset_count = 0

    from tools.chatgpt.models import Anomaly

    fake = FakeResult()
    fake.anomalies = [Anomaly("no_technical_root", "conv-x", None, "test anomaly")]

    report = validate(fake, expected=None)
    assert report.passed is False
    assert len(report.anomalies) == 1


def test_chatgpt_acq_001_baseline_is_defined_and_not_used_by_default():
    assert "chatgpt-acq-001" in EXPECTED_BASELINES
    baseline = EXPECTED_BASELINES["chatgpt-acq-001"]
    assert baseline["conversations"] == 777
    assert baseline["nodes"] == 33642
    assert baseline["messages"] == 32865
    assert baseline["technical_roots"] == 777
    assert baseline["conversations_with_branches"] == 65
    assert baseline["branching_parents"] == 75
    assert baseline["off_current_path_nodes"] == 186
    assert baseline["conversation_asset_mappings"] == 6146
    assert baseline["physical_dat_assets"] == 6242
    assert baseline["library_files_records"] == 2136
    assert baseline["logical_assets"] == 6364
    assert baseline["reference_only_assets"] == 122
