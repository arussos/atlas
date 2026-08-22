"""Test H/I/J: FakeSemanticJudge (judge.py). Nessuna dipendenza di rete/modello reale."""

import socket

import pytest

from tools.semantic_boundary.judge import FakeSemanticJudge, JudgeError, JudgeResponse
from tools.semantic_boundary.models import DECISION_BOUNDARY, DECISION_UNCERTAIN

from tests.semantic_boundary.fixtures import make_candidate_dict, make_timeline
from tools.semantic_boundary.resolver import build_request


def _request(candidate_id="cand-1"):
    timeline = make_timeline([f"n{i}" for i in range(4)])
    candidate = make_candidate_dict(candidate_id=candidate_id, before_node_id="n1", after_node_id="n2")
    return build_request(candidate, timeline)


def test_default_response_is_uncertain_with_zero_confidence():
    judge = FakeSemanticJudge()
    response = judge.resolve(_request())
    assert response.decision == DECISION_UNCERTAIN
    assert response.confidence == 0.0
    assert response.judge_name == FakeSemanticJudge.JUDGE_NAME


def test_preregistered_response_is_returned_for_matching_candidate_id():
    canned = JudgeResponse(
        decision=DECISION_BOUNDARY,
        confidence=0.85,
        reason="Cambia il problema.",
        judge_name="fake-fixture-judge",
        judge_version="test-0.1",
    )
    judge = FakeSemanticJudge(responses={"cand-1": canned})
    response = judge.resolve(_request(candidate_id="cand-1"))
    assert response is canned


def test_failing_candidate_id_raises_judge_error():
    judge = FakeSemanticJudge(failing_candidate_ids=frozenset({"cand-1"}))
    with pytest.raises(JudgeError):
        judge.resolve(_request(candidate_id="cand-1"))


def test_non_failing_candidate_id_does_not_raise():
    judge = FakeSemanticJudge(failing_candidate_ids=frozenset({"other-id"}))
    judge.resolve(_request(candidate_id="cand-1"))  # non deve sollevare


def test_fake_judge_never_opens_a_network_socket(monkeypatch):
    """J: nessuna dipendenza di rete/modello reale — anche solo tentare di aprire un socket è un fallimento del test."""

    def _forbidden(*args, **kwargs):
        raise AssertionError("FakeSemanticJudge must never touch the network")

    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    judge = FakeSemanticJudge()
    judge.resolve(_request())  # deve funzionare senza mai chiamare connect()
