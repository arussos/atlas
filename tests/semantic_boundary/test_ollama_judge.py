"""
M4.2b-B — Test di OllamaSemanticJudge e del batch runner Gold Pilot
(ollama.py). Nessuna chiamata di rete reale: tutto l'HTTP è mockato
sostituendo tools.semantic_boundary.ollama._http_post_json, tranne il
test dedicato a dimostrare che nessun socket reale viene mai aperto.
"""

import json
import socket

import pytest

from tools.semantic_boundary.judge import FakeSemanticJudge, JudgeResponse
from tools.semantic_boundary.models import (
    DECISION_BOUNDARY,
    DECISION_SAME_EPISODE,
    DECISION_UNCERTAIN,
    RequestValidationError,
)
from tools.semantic_boundary.prompt import TASK_INSTRUCTION
from tools.semantic_boundary.resolver import ResolutionFailure
import tools.semantic_boundary.ollama as ollama_module
from tools.semantic_boundary.ollama import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_BASE_URL,
    GENERATE_ENDPOINT_PATH,
    OllamaHTTPError,
    OllamaResponseError,
    OllamaSemanticJudge,
    OllamaTimeoutError,
    OllamaTransportError,
    build_request_from_gold_pilot_record,
    run_gold_pilot_batch,
)

from tests.semantic_boundary.fixtures import make_candidate_dict, make_timeline
from tools.semantic_boundary.resolver import build_request


def _request(candidate_id="cand-1"):
    timeline = make_timeline([f"n{i}" for i in range(4)])
    candidate = make_candidate_dict(candidate_id=candidate_id, before_node_id="n1", after_node_id="n2")
    return build_request(candidate, timeline)


def _gold_pilot_record(**overrides):
    record = make_candidate_dict(before_node_id="n1", after_node_id="n2")
    record["before_context"] = [
        {"node_id": "n0", "role": "user", "text": "prima domanda", "content_type": "text"},
        {"node_id": "n1", "role": "assistant", "text": "prima risposta", "content_type": "text"},
    ]
    record["after_context"] = [
        {"node_id": "n2", "role": "user", "text": "seconda domanda", "content_type": "text"},
        {"node_id": "n3", "role": "assistant", "text": "seconda risposta", "content_type": "text"},
    ]
    record.update(overrides)
    return record


def _ok_envelope(decision="SAME_EPISODE", confidence=0.7, reason="Continua lo stesso task."):
    return {"response": '{"decision": "%s", "confidence": %s, "reason": "%s"}' % (decision, confidence, reason)}


class _RecordingHttp:
    """Fake per _http_post_json: registra ogni chiamata e restituisce risposte pre-programmate in sequenza."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def __call__(self, url, payload, timeout):
        self.calls.append({"url": url, "payload": payload, "timeout": timeout})
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


# A/B/C/D: URL, model, non-streaming, prompt M4.2b-A inviati correttamente.
def test_request_uses_configured_url_model_and_is_non_streaming(monkeypatch):
    fake = _RecordingHttp([_ok_envelope()])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge(base_url="http://127.0.0.1:11434", model="llama3.1:8b")
    judge.resolve(_request())

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["url"] == "http://127.0.0.1:11434" + GENERATE_ENDPOINT_PATH
    assert call["payload"]["model"] == "llama3.1:8b"
    assert call["payload"]["stream"] is False
    assert TASK_INSTRUCTION in call["payload"]["prompt"]


def test_default_base_url_and_model_when_unset(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    fake = _RecordingHttp([_ok_envelope()])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    judge.resolve(_request())

    assert fake.calls[0]["url"] == DEFAULT_OLLAMA_BASE_URL + GENERATE_ENDPOINT_PATH
    assert fake.calls[0]["payload"]["model"] == DEFAULT_MODEL


def test_temperature_zero_and_optional_seed(monkeypatch):
    fake = _RecordingHttp([_ok_envelope()])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge(seed=42)
    judge.resolve(_request())

    options = fake.calls[0]["payload"]["options"]
    assert options["temperature"] == 0.0
    assert options["seed"] == 42


# E: gold labels/notes non finiscono mai nell'input al modello.
def test_gold_label_and_notes_are_never_sent_to_the_judge(monkeypatch):
    record = _gold_pilot_record(gold_label="TRUE", gold_notes="secret annotator note")
    request = build_request_from_gold_pilot_record(record)

    fake = _RecordingHttp([_ok_envelope()])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    judge.resolve(request)

    prompt_sent = fake.calls[0]["payload"]["prompt"]
    assert "gold_label" not in prompt_sent
    assert "secret annotator note" not in prompt_sent
    assert "gold_notes" not in prompt_sent


def test_build_request_from_gold_pilot_record_ignores_gold_fields():
    record = _gold_pilot_record(gold_label="AMBIGUOUS", gold_notes="do not leak this")
    request = build_request_from_gold_pilot_record(record)

    assert "gold_label" not in request.to_dict()
    serialized = str(request.to_dict())
    assert "do not leak this" not in serialized


# F/G/H: risposte strutturate valide per ciascuna decisione.
@pytest.mark.parametrize(
    "decision",
    [DECISION_SAME_EPISODE, DECISION_BOUNDARY, DECISION_UNCERTAIN],
)
def test_valid_structured_response_for_each_decision(monkeypatch, decision):
    fake = _RecordingHttp([_ok_envelope(decision=decision, confidence=0.55, reason="Motivazione breve.")])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    response = judge.resolve(_request())

    assert response.decision == decision
    assert response.confidence == 0.55
    assert response.reason == "Motivazione breve."
    assert response.judge_name == "ollama"
    assert response.judge_version == f"0.1+{DEFAULT_MODEL}"


# I: JSON malformato viene rifiutato dopo il repair retry.
def test_malformed_json_is_rejected_after_repair_retry(monkeypatch):
    fake = _RecordingHttp([{"response": "not json at all"}, {"response": "still not json"}])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaResponseError):
        judge.resolve(_request())
    assert len(fake.calls) == 2  # un solo repair retry, stesso identico input


def test_repair_retry_succeeds_on_second_attempt(monkeypatch):
    fake = _RecordingHttp([{"response": "not json"}, _ok_envelope(decision=DECISION_BOUNDARY)])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    response = judge.resolve(_request())

    assert response.decision == DECISION_BOUNDARY
    assert len(fake.calls) == 2
    assert fake.calls[0]["payload"] == fake.calls[1]["payload"]  # stesso input semantico


# J: decision invalida rifiutata SENZA retry (JSON valido, valore invalido).
def test_invalid_decision_rejected_without_retry(monkeypatch):
    fake = _RecordingHttp([_ok_envelope(decision="MAYBE")])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaResponseError):
        judge.resolve(_request())
    assert len(fake.calls) == 1


# K: confidence fuori range rifiutata SENZA retry.
def test_confidence_out_of_range_rejected_without_retry(monkeypatch):
    fake = _RecordingHttp([_ok_envelope(confidence=1.5)])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaResponseError):
        judge.resolve(_request())
    assert len(fake.calls) == 1


# L: fallimento HTTP surfaced esplicitamente, nessun retry (non è un transport error).
def test_http_failure_is_surfaced_without_retry(monkeypatch):
    fake = _RecordingHttp([OllamaHTTPError("Ollama HTTP error: status=500")])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaHTTPError):
        judge.resolve(_request())
    assert len(fake.calls) == 1


# M: timeout surfaced esplicitamente, nessun retry.
def test_timeout_is_surfaced_without_retry(monkeypatch):
    fake = _RecordingHttp([OllamaTimeoutError("Ollama request timed out after 120.0s")])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaTimeoutError):
        judge.resolve(_request())
    assert len(fake.calls) == 1


def test_transport_error_is_retried_once_then_succeeds(monkeypatch):
    fake = _RecordingHttp([OllamaTransportError("connection refused"), _ok_envelope()])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    response = judge.resolve(_request())

    assert response.decision == DECISION_SAME_EPISODE
    assert len(fake.calls) == 2


def test_transport_error_surfaces_after_single_retry_exhausted(monkeypatch):
    fake = _RecordingHttp([OllamaTransportError("connection refused"), OllamaTransportError("connection refused")])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaTransportError):
        judge.resolve(_request())
    assert len(fake.calls) == 2  # tentativo iniziale + un solo retry, non di più


# Review finding 1: un fallimento infrastrutturale durante il repair retry
# mantiene il proprio tipo esplicito, non viene mai riclassificato come
# OllamaResponseError.
def test_timeout_during_repair_retry_is_not_reclassified(monkeypatch):
    fake = _RecordingHttp(
        [{"response": "not json"}, OllamaTimeoutError("Ollama request timed out after 120.0s")]
    )
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaTimeoutError):
        judge.resolve(_request())
    assert len(fake.calls) == 2


def test_http_failure_during_repair_retry_is_not_reclassified(monkeypatch):
    fake = _RecordingHttp(
        [{"response": "not json"}, OllamaHTTPError("Ollama HTTP error: status=500")]
    )
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaHTTPError):
        judge.resolve(_request())
    assert len(fake.calls) == 2


def test_transport_failure_during_repair_retry_is_not_reclassified(monkeypatch):
    fake = _RecordingHttp(
        [{"response": "not json"}, OllamaTransportError("connection refused")]
    )
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaTransportError):
        judge.resolve(_request())
    assert len(fake.calls) == 2


def test_second_malformed_response_during_repair_retry_is_still_response_error(monkeypatch):
    fake = _RecordingHttp([{"response": "not json"}, {"response": "still not json"}])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaResponseError):
        judge.resolve(_request())
    assert len(fake.calls) == 2


# Review finding 2: chiavi extra o mancanti nell'oggetto JSON strutturato
# rendono la risposta non valida, anche se decision/confidence/reason sono
# individualmente corretti.
def test_structured_response_with_unexpected_extra_key_is_rejected(monkeypatch):
    envelope = {
        "response": json.dumps(
            {
                "decision": DECISION_SAME_EPISODE,
                "confidence": 0.7,
                "reason": "Motivazione valida.",
                "chain_of_thought": "not allowed",
            }
        )
    }
    fake = _RecordingHttp([envelope, envelope])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaResponseError):
        judge.resolve(_request())
    assert len(fake.calls) == 2  # repair retry consumato, poi si arrende


def test_structured_response_missing_a_required_key_is_rejected(monkeypatch):
    envelope = {"response": json.dumps({"decision": DECISION_SAME_EPISODE, "confidence": 0.7})}
    fake = _RecordingHttp([envelope, envelope])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    with pytest.raises(OllamaResponseError):
        judge.resolve(_request())
    assert len(fake.calls) == 2


# Review finding 3: guardrail minimi sulla configurazione del costruttore.
def test_constructor_rejects_empty_model():
    with pytest.raises(ValueError):
        OllamaSemanticJudge(model="")


def test_constructor_rejects_blank_model():
    with pytest.raises(ValueError):
        OllamaSemanticJudge(model="   ")


def test_constructor_rejects_blank_base_url(monkeypatch):
    # "" è falsy e ricade sul fallback (env var / default): il guardrail
    # deve intercettare un base_url risolto ma composto solo da spazi,
    # es. una OLLAMA_BASE_URL malconfigurata.
    monkeypatch.setenv("OLLAMA_BASE_URL", "   ")
    with pytest.raises(ValueError):
        OllamaSemanticJudge()


def test_constructor_rejects_non_positive_timeout():
    with pytest.raises(ValueError):
        OllamaSemanticJudge(timeout=0)
    with pytest.raises(ValueError):
        OllamaSemanticJudge(timeout=-5.0)


# N: nessuna chiamata di rete reale — anche solo aprire un socket è un fallimento del test.
def test_ollama_judge_never_opens_a_real_socket(monkeypatch):
    def _forbidden(*args, **kwargs):
        raise AssertionError("OllamaSemanticJudge must never touch the real network in unit tests")

    monkeypatch.setattr(socket.socket, "connect", _forbidden)

    class _FakeHttpResponse:
        def __init__(self, body):
            self._body = body.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def getcode(self):
            return 200

        def read(self):
            return self._body

    import json as _json

    def _fake_urlopen(request, timeout=None):
        return _FakeHttpResponse(_json.dumps(_ok_envelope(decision=DECISION_UNCERTAIN)))

    monkeypatch.setattr(ollama_module.urllib.request, "urlopen", _fake_urlopen)

    judge = OllamaSemanticJudge()
    response = judge.resolve(_request())
    assert response.decision == DECISION_UNCERTAIN


# O/P: batch runner preserva la mappatura candidate_id e non scarta mai fallimenti.
def test_batch_runner_preserves_candidate_id_mapping():
    records = [
        _gold_pilot_record(candidate_id="a", gold_label="TRUE"),
        _gold_pilot_record(candidate_id="b", gold_label="FALSE"),
    ]
    judge = FakeSemanticJudge(
        responses={
            "a": JudgeResponse(
                decision=DECISION_BOUNDARY, confidence=0.9, reason="r-a",
                judge_name="fake-fixture-judge", judge_version="test-0.1",
            ),
            "b": JudgeResponse(
                decision=DECISION_SAME_EPISODE, confidence=0.2, reason="r-b",
                judge_name="fake-fixture-judge", judge_version="test-0.1",
            ),
        }
    )

    resolutions, failures = run_gold_pilot_batch(records, judge)

    assert failures == []
    by_id = {r.candidate_id: r for r in resolutions}
    assert by_id["a"].decision == DECISION_BOUNDARY
    assert by_id["b"].decision == DECISION_SAME_EPISODE


def test_batch_runner_captures_failures_explicitly_without_dropping_them():
    malformed = _gold_pilot_record(candidate_id="malformed")
    del malformed["time_gap_bucket"]
    failing_judge_record = _gold_pilot_record(candidate_id="will-fail")

    judge = FakeSemanticJudge(failing_candidate_ids=frozenset({"will-fail"}))
    resolutions, failures = run_gold_pilot_batch([malformed, failing_judge_record], judge)

    assert resolutions == []
    assert len(failures) == 2
    failure_ids = {f.candidate_id for f in failures}
    assert failure_ids == {"malformed", "will-fail"}
    assert all(isinstance(f, ResolutionFailure) for f in failures)


def test_malformed_gold_pilot_record_missing_context_raises():
    record = _gold_pilot_record()
    del record["after_context"]
    with pytest.raises(RequestValidationError):
        build_request_from_gold_pilot_record(record)


# Q: costruzione della request deterministica e invariata.
def test_request_construction_is_deterministic(monkeypatch):
    record = _gold_pilot_record()
    request_1 = build_request_from_gold_pilot_record(record)
    request_2 = build_request_from_gold_pilot_record(record)
    assert request_1.to_dict() == request_2.to_dict()

    calls = []
    fake = _RecordingHttp([_ok_envelope(), _ok_envelope()])
    monkeypatch.setattr(ollama_module, "_http_post_json", fake)

    judge = OllamaSemanticJudge()
    judge.resolve(request_1)
    judge.resolve(request_2)
    assert fake.calls[0]["payload"]["prompt"] == fake.calls[1]["payload"]["prompt"]
