"""Test A/C/H/I: costruzione request, mapping evidenza, runner e fallimento judge (resolver.py)."""

import pytest

from tools.semantic_boundary.judge import FakeSemanticJudge, JudgeError, JudgeResponse
from tools.semantic_boundary.models import (
    DECISION_BOUNDARY,
    DECISION_SAME_EPISODE,
    RequestValidationError,
)
from tools.semantic_boundary.resolver import (
    ResolutionFailure,
    build_request,
    resolve_candidate,
    run_resolutions,
)

from tests.semantic_boundary.fixtures import make_candidate_dict, make_timeline


def test_build_request_includes_two_before_two_after_with_endpoints():
    timeline = make_timeline([f"n{i}" for i in range(6)])
    candidate = make_candidate_dict(before_node_id="n2", after_node_id="n3")
    request = build_request(candidate, timeline)

    assert [t.node_id for t in request.before_context] == ["n1", "n2"]
    assert [t.node_id for t in request.after_context] == ["n3", "n4"]
    assert request.before_context[-1].node_id == "n2"
    assert request.after_context[0].node_id == "n3"


def test_build_request_preserves_order():
    timeline = make_timeline([f"n{i}" for i in range(6)])
    candidate = make_candidate_dict(before_node_id="n2", after_node_id="n3")
    request = build_request(candidate, timeline)

    before_ids = [t.node_id for t in request.before_context]
    after_ids = [t.node_id for t in request.after_context]
    assert before_ids == ["n1", "n2"]
    assert after_ids == ["n3", "n4"]


def test_build_request_maps_m4_2a_evidence_fields_correctly():
    timeline = make_timeline([f"n{i}" for i in range(4)])
    candidate = make_candidate_dict(
        before_node_id="n1",
        after_node_id="n2",
        candidate_class="HIGH",
        candidate_score=0.91,
        time_gap_seconds=3600.0,
        time_gap_bucket="long",
        lexical_shift_score=0.77,
        opening_markers=["ora passiamo a"],
        closure_markers=["risolto"],
        resume_markers=["torniamo su"],
        transition_markers=["cambiamo argomento"],
        intermediate_node_count=3,
    )
    request = build_request(candidate, timeline)
    evidence = request.m4_2a_evidence

    assert evidence.candidate_class == "HIGH"
    assert evidence.candidate_score == 0.91
    assert evidence.time_gap_seconds == 3600.0
    assert evidence.time_gap_bucket == "long"
    assert evidence.lexical_shift_score == 0.77
    assert evidence.opening_markers == ["ora passiamo a"]
    assert evidence.closure_markers == ["risolto"]
    assert evidence.resume_markers == ["torniamo su"]
    assert evidence.transition_markers == ["cambiamo argomento"]
    assert evidence.intermediate_node_count == 3


def test_build_request_missing_field_raises():
    timeline = make_timeline([f"n{i}" for i in range(4)])
    candidate = make_candidate_dict(before_node_id="n1", after_node_id="n2")
    del candidate["candidate_score"]
    with pytest.raises(RequestValidationError):
        build_request(candidate, timeline)


def test_resolve_candidate_with_fake_judge_produces_valid_resolution():
    timeline = make_timeline([f"n{i}" for i in range(4)])
    candidate = make_candidate_dict(before_node_id="n1", after_node_id="n2", candidate_id="cand-x")
    request = build_request(candidate, timeline)

    judge = FakeSemanticJudge(
        responses={
            "cand-x": JudgeResponse(
                decision=DECISION_BOUNDARY,
                confidence=0.9,
                reason="Cambia obiettivo operativo.",
                judge_name="fake-fixture-judge",
                judge_version="test-0.1",
            )
        }
    )
    resolution = resolve_candidate(request, judge)

    assert resolution.candidate_id == "cand-x"
    assert resolution.decision == DECISION_BOUNDARY
    assert resolution.confidence == 0.9
    assert resolution.resolution_hash


def test_run_resolutions_batch_with_fake_judge():
    timeline = make_timeline([f"n{i}" for i in range(4)])
    candidates = [
        (make_candidate_dict(candidate_id="a", before_node_id="n1", after_node_id="n2"), timeline),
        (make_candidate_dict(candidate_id="b", before_node_id="n2", after_node_id="n3"), timeline),
    ]
    judge = FakeSemanticJudge(default_decision=DECISION_SAME_EPISODE, default_confidence=0.4)

    resolutions, failures = run_resolutions(candidates, judge)

    assert len(resolutions) == 2
    assert failures == []
    assert {r.candidate_id for r in resolutions} == {"a", "b"}
    assert all(r.decision == DECISION_SAME_EPISODE for r in resolutions)


def test_judge_failure_is_surfaced_not_swallowed_by_resolve_candidate():
    timeline = make_timeline([f"n{i}" for i in range(4)])
    candidate = make_candidate_dict(before_node_id="n1", after_node_id="n2", candidate_id="will-fail")
    request = build_request(candidate, timeline)
    judge = FakeSemanticJudge(failing_candidate_ids=frozenset({"will-fail"}))

    with pytest.raises(JudgeError):
        resolve_candidate(request, judge)


def test_judge_failure_is_captured_explicitly_in_batch_runner():
    timeline = make_timeline([f"n{i}" for i in range(4)])
    candidates = [
        (make_candidate_dict(candidate_id="ok", before_node_id="n1", after_node_id="n2"), timeline),
        (make_candidate_dict(candidate_id="bad", before_node_id="n2", after_node_id="n3"), timeline),
    ]
    judge = FakeSemanticJudge(failing_candidate_ids=frozenset({"bad"}))

    resolutions, failures = run_resolutions(candidates, judge)

    assert len(resolutions) == 1
    assert resolutions[0].candidate_id == "ok"
    assert len(failures) == 1
    assert isinstance(failures[0], ResolutionFailure)
    assert failures[0].candidate_id == "bad"
    assert failures[0].error_type == "JudgeError"


def test_malformed_candidate_failure_is_captured_explicitly_in_batch_runner():
    timeline = make_timeline([f"n{i}" for i in range(4)])
    malformed = make_candidate_dict(candidate_id="malformed", before_node_id="n1", after_node_id="n2")
    del malformed["time_gap_bucket"]
    candidates = [(malformed, timeline)]
    judge = FakeSemanticJudge()

    resolutions, failures = run_resolutions(candidates, judge)

    assert resolutions == []
    assert len(failures) == 1
    assert failures[0].candidate_id == "malformed"
    assert failures[0].error_type == "RequestValidationError"
