"""
M4.2a RC2 — Tests for tools/episodes/validation.py

Covers spec section 12 (RC2 metrics: current_path_message_nodes,
visible_dialogue_messages, non_visible_current_path_message_nodes,
candidates_with_intermediate_nodes, intermediate_nodes_skipped_total),
candidate-count invariant against visible dialogue messages, and
structural anomalies (duplicate node id) surfaced through the full
pipeline.
"""

from tests.episodes.fixtures import chain_conversation, linear_conversation, make_conversation, make_node
from tools.episodes.boundary_candidates import generate_boundary_candidates
from tools.episodes.validation import EXPECTED_BASELINES, check_invariant, compute_metrics, validate


def test_compute_metrics_matches_candidate_count():
    fixture = linear_conversation("conv-1", 5)
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates(
        [fixture["conversation"]], fixture["nodes"]
    )
    metrics = compute_metrics(
        candidates,
        conversations_processed=1,
        current_path_message_nodes=sum(current_path.values()),
        visible_dialogue_messages=sum(visible.values()),
    )
    assert metrics["candidates"] == 4
    assert metrics["conversations_processed"] == 1
    assert metrics["current_path_message_nodes"] == 5
    assert metrics["visible_dialogue_messages"] == 5
    assert metrics["non_visible_current_path_message_nodes"] == 0
    assert metrics["low_candidates"] + metrics["medium_candidates"] + metrics["high_candidates"] == 4


def test_compute_metrics_reports_non_visible_and_intermediate_provenance():
    fixture = chain_conversation(
        "conv-mixed",
        [
            dict(role="user", content_type="text", text_parts=["A"]),
            dict(role="assistant", content_type="thoughts", text_parts=["X"]),
            dict(role="assistant", content_type="reasoning_recap", text_parts=["Y"]),
            dict(role="assistant", content_type="text", text_parts=["B"]),
        ],
    )
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates(
        [fixture["conversation"]], fixture["nodes"]
    )
    metrics = compute_metrics(
        candidates,
        conversations_processed=1,
        current_path_message_nodes=sum(current_path.values()),
        visible_dialogue_messages=sum(visible.values()),
    )
    assert metrics["current_path_message_nodes"] == 4
    assert metrics["visible_dialogue_messages"] == 2
    assert metrics["non_visible_current_path_message_nodes"] == 2
    assert metrics["candidates"] == 1
    assert metrics["candidates_with_intermediate_nodes"] == 1
    assert metrics["intermediate_nodes_skipped_total"] == 2


def test_check_invariant_passes_for_correct_counts():
    violations = check_invariant({"conv-1": 5, "conv-2": 1, "conv-3": 0}, {"conv-1": 4, "conv-2": 0, "conv-3": 0})
    assert violations == []


def test_check_invariant_flags_mismatch():
    violations = check_invariant({"conv-1": 5}, {"conv-1": 3})
    assert len(violations) == 1
    assert "conv-1" in violations[0]


def test_validate_passes_on_clean_synthetic_run():
    fixture = linear_conversation("conv-1", 5)
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates(
        [fixture["conversation"]], fixture["nodes"]
    )
    report = validate(
        candidates,
        anomalies,
        conversations_processed=1,
        current_path_message_nodes=sum(current_path.values()),
        visible_dialogue_messages=sum(visible.values()),
        per_conversation_visible_message_counts=visible,
        per_conversation_candidate_counts=cands,
    )
    assert report.passed is True
    assert report.invariant_violations == []
    assert report.metrics["structural_anomalies"] == 0


def test_validate_fails_when_duplicate_node_id_anomaly_present():
    conversation = make_conversation("conv-dup", "n1")
    nodes = [
        make_node("conv-dup", "root", None, has_message=False, is_technical_root=True, content_type=None),
        make_node("conv-dup", "n1", "root", role="user", created_at=1.0, text_parts=["hello"]),
        # duplicate node_id within the same conversation
        make_node("conv-dup", "n1", "root", role="user", created_at=1.0, text_parts=["hello again"]),
    ]
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates([conversation], nodes)
    assert any(a.type == "duplicate_node_id" for a in anomalies)

    report = validate(
        candidates,
        anomalies,
        conversations_processed=1,
        current_path_message_nodes=sum(current_path.values()),
        visible_dialogue_messages=sum(visible.values()),
        per_conversation_visible_message_counts=visible,
        per_conversation_candidate_counts=cands,
    )
    assert report.passed is False
    assert report.metrics["structural_anomalies"] == 1


def test_validate_fails_on_baseline_gate_divergence():
    fixture = linear_conversation("conv-1", 5)
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates(
        [fixture["conversation"]], fixture["nodes"]
    )
    report = validate(
        candidates,
        anomalies,
        conversations_processed=1,
        current_path_message_nodes=sum(current_path.values()),
        visible_dialogue_messages=sum(visible.values()),
        per_conversation_visible_message_counts=visible,
        per_conversation_candidate_counts=cands,
        expected={"candidates": 999},
    )
    assert report.passed is False
    assert report.gate_results[0]["passed"] is False


def test_chatgpt_acq_001_baseline_defined_and_isolated():
    assert "chatgpt-acq-001" in EXPECTED_BASELINES
    baseline = EXPECTED_BASELINES["chatgpt-acq-001"]
    assert baseline["conversations_processed"] == 777
    assert baseline["current_path_message_nodes"] == 32679
    assert baseline["visible_dialogue_messages"] == 26187
    assert baseline["non_visible_current_path_message_nodes"] == 6492
    assert baseline["candidates"] == 25410
