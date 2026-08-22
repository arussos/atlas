"""Test D: contratto dati e validazione dell'output (models.py)."""

import pytest

from tools.semantic_boundary.models import (
    DECISION_BOUNDARY,
    DECISION_SAME_EPISODE,
    DECISION_UNCERTAIN,
    RequestValidationError,
    ResolutionValidationError,
    SemanticEvidence,
    SemanticResolution,
    SemanticResolutionRequest,
    validate_confidence,
    validate_decision,
    validate_request,
    validate_resolution,
)

from tests.semantic_boundary.fixtures import make_turn


def _evidence(**overrides):
    defaults = dict(
        candidate_class="MEDIUM",
        candidate_score=0.5,
        time_gap_seconds=60.0,
        time_gap_bucket="short",
        lexical_shift_score=0.2,
        opening_markers=[],
        closure_markers=[],
        resume_markers=[],
        transition_markers=[],
        intermediate_node_count=0,
    )
    defaults.update(overrides)
    return SemanticEvidence(**defaults)


def _request(**overrides):
    defaults = dict(
        candidate_id="cand-1",
        conversation_id="conv-1",
        before_node_id="n2",
        after_node_id="n3",
        before_context=[make_turn("n1"), make_turn("n2")],
        after_context=[make_turn("n3"), make_turn("n4")],
        m4_2a_evidence=_evidence(),
    )
    defaults.update(overrides)
    return SemanticResolutionRequest(**defaults)


def test_valid_request_passes_validation():
    validate_request(_request())  # non deve sollevare


def test_request_missing_candidate_id_rejected():
    with pytest.raises(RequestValidationError):
        validate_request(_request(candidate_id=""))


def test_request_endpoint_not_included_in_before_context_rejected():
    with pytest.raises(RequestValidationError):
        validate_request(_request(before_context=[make_turn("n1")]))


def test_request_endpoint_not_included_in_after_context_rejected():
    with pytest.raises(RequestValidationError):
        validate_request(_request(after_context=[make_turn("n4")]))


def test_request_empty_before_context_rejected():
    with pytest.raises(RequestValidationError):
        validate_request(_request(before_context=[]))


def test_request_empty_after_context_rejected():
    with pytest.raises(RequestValidationError):
        validate_request(_request(after_context=[]))


def test_request_invalid_evidence_rejected():
    with pytest.raises(RequestValidationError):
        validate_request(_request(m4_2a_evidence=_evidence(candidate_class="")))


def test_evidence_negative_time_gap_rejected():
    with pytest.raises(RequestValidationError):
        validate_request(_request(m4_2a_evidence=_evidence(time_gap_seconds=-1.0)))


def test_evidence_time_gap_none_is_allowed():
    validate_request(_request(m4_2a_evidence=_evidence(time_gap_seconds=None)))


def test_evidence_non_string_marker_rejected():
    with pytest.raises(RequestValidationError):
        validate_request(_request(m4_2a_evidence=_evidence(opening_markers=[1, 2])))


@pytest.mark.parametrize("decision", [DECISION_SAME_EPISODE, DECISION_BOUNDARY, DECISION_UNCERTAIN])
def test_valid_decisions_are_accepted(decision):
    validate_decision(decision)  # non deve sollevare


def test_invalid_decision_rejected():
    with pytest.raises(ResolutionValidationError):
        validate_decision("NOT_A_DECISION")


@pytest.mark.parametrize("confidence", [0.0, 0.5, 1.0])
def test_valid_confidence_accepted(confidence):
    validate_confidence(confidence)  # non deve sollevare


@pytest.mark.parametrize("confidence", [-0.01, 1.01, 2.0, -5])
def test_invalid_confidence_rejected(confidence):
    with pytest.raises(ResolutionValidationError):
        validate_confidence(confidence)


def test_confidence_bool_rejected():
    with pytest.raises(ResolutionValidationError):
        validate_confidence(True)


def _resolution(**overrides):
    defaults = dict(
        candidate_id="cand-1",
        decision=DECISION_SAME_EPISODE,
        confidence=0.8,
        reason="Continua lo stesso task.",
        resolver_version="m4.2b-0.1",
        judge_name="fake-fixture-judge",
        judge_version="test-0.1",
        resolution_hash="deadbeef",
    )
    defaults.update(overrides)
    return SemanticResolution(**defaults)


@pytest.mark.parametrize("decision", [DECISION_SAME_EPISODE, DECISION_BOUNDARY, DECISION_UNCERTAIN])
def test_valid_resolution_for_each_decision_passes(decision):
    validate_resolution(_resolution(decision=decision))


def test_resolution_invalid_decision_rejected():
    with pytest.raises(ResolutionValidationError):
        validate_resolution(_resolution(decision="MAYBE"))


def test_resolution_confidence_out_of_range_rejected():
    with pytest.raises(ResolutionValidationError):
        validate_resolution(_resolution(confidence=1.5))


def test_resolution_empty_reason_rejected():
    with pytest.raises(ResolutionValidationError):
        validate_resolution(_resolution(reason=""))
