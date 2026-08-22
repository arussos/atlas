"""Test E: determinismo dell'hashing (hashing.py)."""

import copy

from tools.semantic_boundary.hashing import compute_request_hash, compute_resolution_hash
from tools.semantic_boundary.resolver import build_request

from tests.semantic_boundary.fixtures import make_candidate_dict, make_timeline


def _request():
    timeline = make_timeline([f"n{i}" for i in range(6)])
    candidate = make_candidate_dict(before_node_id="n2", after_node_id="n3")
    return build_request(candidate, timeline)


def test_request_hash_is_deterministic_across_identical_builds():
    timeline = make_timeline([f"n{i}" for i in range(6)])
    candidate_a = make_candidate_dict(before_node_id="n2", after_node_id="n3")
    candidate_b = copy.deepcopy(candidate_a)

    request_a = build_request(candidate_a, timeline)
    request_b = build_request(candidate_b, timeline)

    assert compute_request_hash(request_a) == compute_request_hash(request_b)


def test_request_hash_changes_when_a_semantic_field_changes():
    timeline = make_timeline([f"n{i}" for i in range(6)])
    baseline = build_request(make_candidate_dict(before_node_id="n2", after_node_id="n3"), timeline)
    changed = build_request(
        make_candidate_dict(before_node_id="n2", after_node_id="n3", candidate_score=0.99),
        timeline,
    )

    assert compute_request_hash(baseline) != compute_request_hash(changed)


def test_request_hash_changes_when_evidence_markers_change():
    timeline = make_timeline([f"n{i}" for i in range(6)])
    baseline = build_request(make_candidate_dict(before_node_id="n2", after_node_id="n3"), timeline)
    changed = build_request(
        make_candidate_dict(before_node_id="n2", after_node_id="n3", opening_markers=["ora passiamo a"]),
        timeline,
    )

    assert compute_request_hash(baseline) != compute_request_hash(changed)


def test_resolution_hash_is_deterministic():
    kwargs = dict(
        candidate_id="cand-1",
        decision="SAME_EPISODE",
        confidence=0.7,
        reason="stessa attività",
        resolver_version="m4.2b-0.1",
        judge_name="fake-fixture-judge",
        judge_version="test-0.1",
    )
    assert compute_resolution_hash(**kwargs) == compute_resolution_hash(**kwargs)


def test_resolution_hash_changes_when_decision_changes():
    base_kwargs = dict(
        candidate_id="cand-1",
        confidence=0.7,
        reason="stessa attività",
        resolver_version="m4.2b-0.1",
        judge_name="fake-fixture-judge",
        judge_version="test-0.1",
    )
    hash_same = compute_resolution_hash(decision="SAME_EPISODE", **base_kwargs)
    hash_boundary = compute_resolution_hash(decision="BOUNDARY", **base_kwargs)
    assert hash_same != hash_boundary


def test_resolution_hash_changes_when_confidence_changes():
    base_kwargs = dict(
        candidate_id="cand-1",
        decision="SAME_EPISODE",
        reason="stessa attività",
        resolver_version="m4.2b-0.1",
        judge_name="fake-fixture-judge",
        judge_version="test-0.1",
    )
    hash_a = compute_resolution_hash(confidence=0.7, **base_kwargs)
    hash_b = compute_resolution_hash(confidence=0.71, **base_kwargs)
    assert hash_a != hash_b
