"""
M4.2b-A — Astrazione SemanticJudge, provider-indipendente.

Nessun provider reale è implementato in questo pass: nessuna chiamata
cloud (OpenAI/Anthropic/Google), nessun Ollama/OpenRouter, nessuna rete.
Questo modulo definisce solo il contratto che futuri adapter dovranno
rispettare, più un judge fittizio (FakeSemanticJudge) usato esclusivamente
per testare l'infrastruttura — runner, serializzazione, evaluator,
determinismo, percorsi di errore. Il fake judge non deve mai imitare
intelligenza semantica.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional

from tools.semantic_boundary.models import (
    DECISION_UNCERTAIN,
    SemanticResolutionRequest,
    validate_confidence,
    validate_decision,
)


class JudgeError(Exception):
    """
    Sollevata quando un SemanticJudge non riesce a produrre un esito
    (fallimento del provider, risposta malformata, timeout, ecc.). Non va
    mai catturata e ignorata silenziosamente dal runner: deve sempre
    risultare in un esito osservabile (eccezione propagata o fallimento
    registrato esplicitamente — vedi resolver.py).
    """


@dataclass
class JudgeResponse:
    """
    Esito grezzo restituito da un SemanticJudge.resolve(). Non contiene
    ancora candidate_id/resolver_version/resolution_hash: quei campi sono
    assemblati dal resolver (tools/semantic_boundary/resolver.py), che è
    l'unico responsabile del calcolo dell'hash finale.
    """

    decision: str
    confidence: float
    reason: str
    judge_name: str
    judge_version: str

    def validate(self) -> None:
        validate_decision(self.decision)
        validate_confidence(self.confidence)
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("JudgeResponse.reason must be a non-empty string")
        if not isinstance(self.judge_name, str) or not self.judge_name:
            raise ValueError("JudgeResponse.judge_name must be a non-empty string")
        if not isinstance(self.judge_version, str) or not self.judge_version:
            raise ValueError("JudgeResponse.judge_version must be a non-empty string")


class SemanticJudge(ABC):
    """
    Contratto provider-indipendente per la risoluzione semantica di una
    candidate transition. Le implementazioni future (judge cloud, judge
    locale via Ollama, ecc.) devono rispettare questa interfaccia; nessuna
    di esse è implementata in questo pass.
    """

    @abstractmethod
    def resolve(self, request: SemanticResolutionRequest) -> JudgeResponse:
        """Decide SAME_EPISODE / BOUNDARY / UNCERTAIN per una singola request."""
        raise NotImplementedError


class FakeSemanticJudge(SemanticJudge):
    """
    Judge fittizio, interamente deterministico, per soli scopi di test di
    infrastruttura. Non implementa alcuna logica semantica: restituisce
    una risposta di default fissa, oppure una risposta pre-registrata per
    uno specifico candidate_id, oppure solleva JudgeError per i
    candidate_id marcati come "failing" — utile per testare i percorsi di
    errore del runner senza alcuna dipendenza da rete o modello reale.
    """

    JUDGE_NAME = "fake-fixture-judge"
    JUDGE_VERSION = "test-0.1"

    def __init__(
        self,
        *,
        default_decision: str = DECISION_UNCERTAIN,
        default_confidence: float = 0.0,
        default_reason: str = "Fixture judge: no semantic evaluation performed.",
        responses: Optional[Dict[str, JudgeResponse]] = None,
        failing_candidate_ids: Optional[FrozenSet[str]] = None,
    ) -> None:
        validate_decision(default_decision)
        validate_confidence(default_confidence)
        self._default_decision = default_decision
        self._default_confidence = default_confidence
        self._default_reason = default_reason
        self._responses = dict(responses) if responses else {}
        self._failing_candidate_ids = frozenset(failing_candidate_ids or ())

    def resolve(self, request: SemanticResolutionRequest) -> JudgeResponse:
        if request.candidate_id in self._failing_candidate_ids:
            raise JudgeError(f"fixture judge configured to fail for candidate_id={request.candidate_id!r}")

        if request.candidate_id in self._responses:
            response = self._responses[request.candidate_id]
        else:
            response = JudgeResponse(
                decision=self._default_decision,
                confidence=self._default_confidence,
                reason=self._default_reason,
                judge_name=self.JUDGE_NAME,
                judge_version=self.JUDGE_VERSION,
            )

        response.validate()
        return response
