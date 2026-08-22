"""
M4.2b-B — OllamaSemanticJudge: primo adapter reale del SemanticJudge,
verso un modello Ollama LOCALE.

Locale per design: l'endpoint di default (127.0.0.1:11434) non lascia mai
Atlas. Nessun provider cloud, nessun embedding, nessuna retrieval, nessuna
ensemble/voting — vedi docs/M4.2B_SEMANTIC_BOUNDARY_RESOLVER.md, sezione
M4.2b-B, per lo scope esatto e i non-goal.

Riusa senza modificarli: il contratto dati (models.py), l'astrazione
SemanticJudge (judge.py), la costruzione deterministica del prompt
(prompt.py, TASK_INSTRUCTION + render_judge_prompt) e il runner
(resolver.py, resolve_candidate). Questo modulo aggiunge solo il trasporto
HTTP verso Ollama, il parsing/validazione dell'output strutturato e un
loader/CLI per eseguire un file esterno di tipo Gold Pilot.

Solo libreria standard: urllib.request/urllib.error per l'HTTP, nessuna
dipendenza aggiunta (niente requests/httpx/ollama-python).
"""

import argparse
import json
import logging
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from tools.semantic_boundary.judge import JudgeError, JudgeResponse, SemanticJudge
from tools.semantic_boundary.models import (
    DialogueTurn,
    RequestValidationError,
    ResolutionValidationError,
    SemanticEvidence,
    SemanticResolution,
    SemanticResolutionRequest,
    validate_confidence,
    validate_decision,
    validate_request,
)
from tools.semantic_boundary.prompt import render_judge_prompt
from tools.semantic_boundary.resolver import ResolutionFailure, resolve_candidate

LOGGER = logging.getLogger("tools.semantic_boundary.ollama")

# Endpoint di default: SOLO loopback. Mai un indirizzo Atlas remoto
# hard-coded (vedi mandato M4.2b-B, sezione 5).
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.1:8b"
DEFAULT_TIMEOUT_SECONDS = 120.0

GENERATE_ENDPOINT_PATH = "/api/generate"

ADAPTER_NAME = "ollama"
ADAPTER_VERSION = "0.1"

# Istruzione di formato output, in aggiunta al TASK_INSTRUCTION di M4.2b-A
# (prompt.py). Specifica solo la forma strutturata attesa, non altera la
# semantica del task né viene mai adattata contro i 60 casi Gold Pilot.
OUTPUT_FORMAT_INSTRUCTION = """\
OUTPUT FORMAT (strict):
Respond with exactly one JSON object and nothing else: no prose, no \
markdown code fences, no chain-of-thought. The JSON object must have \
exactly these keys:
{
  "decision": "SAME_EPISODE" | "BOUNDARY" | "UNCERTAIN",
  "confidence": <number between 0.0 and 1.0>,
  "reason": "<short, concise, auditable, semantic explanation>"
}\
"""

# Campi obbligatori di un record Gold Pilot esterno grezzo (una riga
# JSONL). Convenzione M4.2b-B: candidate dict "piatto" (stessa forma
# richiesta da resolver.build_request) + before_context/after_context già
# ritagliati (liste di dict conformi a DialogueTurn.to_dict()). gold_label
# e gold_notes, se presenti, non compaiono qui di proposito: non sono mai
# letti da build_request_from_gold_pilot_record, quindi non possono mai
# propagarsi nella request né nel prompt inviato al modello.
_REQUIRED_RECORD_FIELDS = (
    "candidate_id",
    "conversation_id",
    "before_node_id",
    "after_node_id",
    "candidate_class",
    "candidate_score",
    "time_gap_seconds",
    "time_gap_bucket",
    "lexical_shift_score",
    "opening_markers",
    "closure_markers",
    "resume_markers",
    "transition_markers",
    "intermediate_node_count",
    "before_context",
    "after_context",
)


class OllamaError(JudgeError):
    """Base per i fallimenti dell'adapter Ollama. Sottoclasse di JudgeError: il runner (resolver.py) la cattura senza modifiche."""


class OllamaTransportError(OllamaError):
    """Fallimento di connessione/trasporto (es. connection refused). Ammesso un solo retry tecnico, vedi _call_with_transport_retry."""


class OllamaTimeoutError(OllamaError):
    """Timeout esplicito della richiesta HTTP verso Ollama. Nessun retry automatico."""


class OllamaHTTPError(OllamaError):
    """Risposta HTTP non-200 da Ollama. Nessun retry automatico."""


class OllamaResponseError(OllamaError):
    """Corpo risposta non JSON, struttura mancante, decision/confidence/reason invalidi. Vedi _parse_with_repair_retry per l'unico retry ammesso."""


def _http_post_json(url: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    """
    Esegue una singola POST non-streaming verso Ollama e restituisce il
    body decodificato come dict. Non effettua alcun retry: quello è
    responsabilità del chiamante (vedi _call_with_transport_retry /
    _parse_with_repair_retry). Non logga mai il body della richiesta o
    della risposta.
    """
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.getcode()
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise OllamaHTTPError(f"Ollama HTTP error: status={exc.code}") from exc
    except socket.timeout as exc:
        raise OllamaTimeoutError(f"Ollama request timed out after {timeout}s") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, socket.timeout):
            raise OllamaTimeoutError(f"Ollama request timed out after {timeout}s") from exc
        raise OllamaTransportError(f"Ollama connection failed: {exc.reason}") from exc

    if status != 200:
        raise OllamaHTTPError(f"Ollama HTTP error: status={status}")

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise OllamaResponseError(f"Ollama HTTP body is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise OllamaResponseError("Ollama HTTP body is not a JSON object")

    return parsed


class OllamaSemanticJudge(SemanticJudge):
    """
    SemanticJudge reale, locale, verso un modello Ollama non-streaming.

    Nessun tool, nessuna web search, nessuna retrieval, nessuna memoria di
    conversazione: una singola richiesta /api/generate per ogni candidate,
    con l'input deterministico prodotto da tools.semantic_boundary.prompt
    (TASK_INSTRUCTION + contesto + evidenza M4.2a) più il solo requisito
    di formato output aggiunto da questo modulo. temperature=0.0 fisso;
    seed opzionale e configurabile. Nessuna diversità di campionamento
    viene mai introdotta.

    Privacy: con l'endpoint di default (127.0.0.1) il testo di dialogo non
    lascia mai la macchina locale. Il logging diagnostico (candidate_id,
    model, latency, status) non include mai il corpo del prompt o della
    risposta del modello.
    """

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        seed: Optional[int] = None,
    ) -> None:
        resolved_base_url = base_url or os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL
        if not isinstance(model, str) or not model.strip():
            raise ValueError("OllamaSemanticJudge: model must be a non-empty string")
        if not isinstance(resolved_base_url, str) or not resolved_base_url.strip():
            raise ValueError("OllamaSemanticJudge: base_url must resolve to a non-empty string")
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
            raise ValueError("OllamaSemanticJudge: timeout must be > 0")
        self.base_url = resolved_base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.seed = seed
        # judge_version veicola la metadata di modello senza toccare lo
        # schema di SemanticResolution (nessun campo "model" dedicato
        # esiste in models.py — vedi mandato M4.2b-B, sezione 15).
        self.judge_name = ADAPTER_NAME
        self.judge_version = f"{ADAPTER_VERSION}+{model}"

    def resolve(self, request: SemanticResolutionRequest) -> JudgeResponse:
        validate_request(request)

        prompt_text = render_judge_prompt(request) + "\n\n" + OUTPUT_FORMAT_INSTRUCTION
        options: Dict[str, Any] = {"temperature": 0.0}
        if self.seed is not None:
            options["seed"] = self.seed
        payload = {
            "model": self.model,
            "prompt": prompt_text,
            "stream": False,
            "format": "json",
            "options": options,
        }
        url = f"{self.base_url}{GENERATE_ENDPOINT_PATH}"

        start = time.monotonic()
        try:
            envelope = self._call_with_transport_retry(url, payload)
            judge_response = self._parse_with_repair_retry(envelope, url, payload)
        except JudgeError as exc:
            self._log_call(request.candidate_id, status="error", error_type=type(exc).__name__, start=start)
            raise

        self._log_call(request.candidate_id, status="ok", start=start)
        return judge_response

    def _call_with_transport_retry(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Un solo retry tecnico, esclusivamente per OllamaTransportError (mandato M4.2b-B, sezione 13)."""
        try:
            return _http_post_json(url, payload, self.timeout)
        except OllamaTransportError:
            return _http_post_json(url, payload, self.timeout)

    def _parse_with_repair_retry(
        self, envelope: Dict[str, Any], url: str, payload: Dict[str, Any]
    ) -> JudgeResponse:
        """
        Estrae decision/confidence/reason dall'envelope Ollama. Se il
        parsing fallisce (JSON malformato/mancante), effettua un unico
        retry con lo stesso identico input semantico (mandato M4.2b-B,
        sezione 13) e poi si arrende esplicitamente. Un JSON valido ma con
        decision/confidence semanticamente invalidi NON attiva il retry:
        è un fallimento di validazione, non un JSON malformato.

        Un fallimento infrastrutturale durante il repair retry (timeout,
        HTTP, trasporto) NON viene mai riclassificato come
        OllamaResponseError: si propaga con il proprio tipo esplicito
        (OllamaTimeoutError / OllamaHTTPError / OllamaTransportError).
        Solo una seconda risposta malformata/non parsabile produce
        OllamaResponseError.
        """
        parsed = self._extract_decision_tuple(envelope)
        if parsed is None:
            envelope = _http_post_json(url, payload, self.timeout)
            parsed = self._extract_decision_tuple(envelope)
            if parsed is None:
                raise OllamaResponseError(
                    "Ollama returned malformed/unparseable structured JSON after repair retry"
                )

        decision, confidence, reason = parsed
        try:
            validate_decision(decision)
            validate_confidence(confidence)
        except ResolutionValidationError as exc:
            raise OllamaResponseError(str(exc)) from exc
        if not reason.strip():
            raise OllamaResponseError("Ollama structured response has an empty 'reason'")

        response = JudgeResponse(
            decision=decision,
            confidence=float(confidence),
            reason=reason,
            judge_name=self.judge_name,
            judge_version=self.judge_version,
        )
        response.validate()
        return response

    @staticmethod
    def _extract_decision_tuple(envelope: Dict[str, Any]) -> Optional[Tuple[str, Any, str]]:
        if not isinstance(envelope, dict):
            return None
        response_text = envelope.get("response")
        if not isinstance(response_text, str) or not response_text.strip():
            return None
        try:
            obj = json.loads(response_text)
        except json.JSONDecodeError:
            return None
        if not isinstance(obj, dict):
            return None
        if set(obj.keys()) != {"decision", "confidence", "reason"}:
            return None

        decision = obj.get("decision")
        confidence = obj.get("confidence")
        reason = obj.get("reason")
        if not isinstance(decision, str):
            return None
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            return None
        if not isinstance(reason, str):
            return None
        return decision, confidence, reason

    def _log_call(self, candidate_id: str, *, status: str, start: float, error_type: Optional[str] = None) -> None:
        """Log diagnostico minimale: mai il corpo di prompt/risposta (privacy, mandato M4.2b-B, sezione 14)."""
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        fields = {"candidate_id": candidate_id, "model": self.model, "status": status, "latency_ms": latency_ms}
        if error_type is not None:
            fields["error_type"] = error_type
        LOGGER.info("ollama_judge_call %s", fields)


def _turn_from_dict(raw: Any) -> DialogueTurn:
    if not isinstance(raw, dict):
        raise RequestValidationError("gold pilot context turn must be a JSON object")
    node_id = raw.get("node_id")
    role = raw.get("role")
    text = raw.get("text")
    content_type = raw.get("content_type")
    if not isinstance(node_id, str) or not node_id:
        raise RequestValidationError("gold pilot context turn missing non-empty node_id")
    if not isinstance(role, str) or not role:
        raise RequestValidationError("gold pilot context turn missing non-empty role")
    if not isinstance(text, str):
        raise RequestValidationError("gold pilot context turn missing text")
    if content_type is not None and not isinstance(content_type, str):
        raise RequestValidationError("gold pilot context turn content_type must be a string when present")
    return DialogueTurn(node_id=node_id, role=role, text=text, content_type=content_type)


def build_request_from_gold_pilot_record(record: Dict[str, Any]) -> SemanticResolutionRequest:
    """
    Costruisce una SemanticResolutionRequest da un record grezzo di un
    file esterno di tipo Gold Pilot (una riga JSONL). Legge solo i campi
    elencati in _REQUIRED_RECORD_FIELDS: gold_label/gold_notes, se
    presenti nel record, non sono mai letti né possono quindi propagarsi
    nella request o nel prompt del judge (protezione anti-leakage,
    mandato M4.2b-B sezione 9/16).
    """
    missing = [field_name for field_name in _REQUIRED_RECORD_FIELDS if field_name not in record]
    if missing:
        raise RequestValidationError(f"malformed gold pilot record: missing field(s) {missing}")

    before_context = [_turn_from_dict(turn) for turn in record["before_context"]]
    after_context = [_turn_from_dict(turn) for turn in record["after_context"]]

    evidence = SemanticEvidence(
        candidate_class=record["candidate_class"],
        candidate_score=record["candidate_score"],
        time_gap_seconds=record["time_gap_seconds"],
        time_gap_bucket=record["time_gap_bucket"],
        lexical_shift_score=record["lexical_shift_score"],
        opening_markers=list(record["opening_markers"]),
        closure_markers=list(record["closure_markers"]),
        resume_markers=list(record["resume_markers"]),
        transition_markers=list(record["transition_markers"]),
        intermediate_node_count=record["intermediate_node_count"],
    )

    request = SemanticResolutionRequest(
        candidate_id=record["candidate_id"],
        conversation_id=record["conversation_id"],
        before_node_id=record["before_node_id"],
        after_node_id=record["after_node_id"],
        before_context=before_context,
        after_context=after_context,
        m4_2a_evidence=evidence,
    )
    validate_request(request)
    return request


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RequestValidationError(f"{path}:{line_number}: invalid JSON ({exc})") from exc
            if not isinstance(record, dict):
                raise RequestValidationError(f"{path}:{line_number}: record must be a JSON object")
            records.append(record)
    return records


def run_gold_pilot_batch(
    records: List[Dict[str, Any]], judge: SemanticJudge
) -> Tuple[List[SemanticResolution], List[ResolutionFailure]]:
    """
    Esegue in batch build_request_from_gold_pilot_record +
    resolve_candidate per una lista di record grezzi. Un fallimento su un
    singolo record (record malformato o JudgeError, incluso qualunque
    OllamaError) non interrompe il batch: viene raccolto come
    ResolutionFailure esplicito, mai scartato silenziosamente.
    """
    resolutions: List[SemanticResolution] = []
    failures: List[ResolutionFailure] = []

    for record in records:
        candidate_id = record.get("candidate_id", "<missing candidate_id>")
        try:
            request = build_request_from_gold_pilot_record(record)
            resolution = resolve_candidate(request, judge)
            resolutions.append(resolution)
        except (RequestValidationError, ResolutionValidationError, ValueError, JudgeError) as exc:
            failures.append(
                ResolutionFailure(
                    candidate_id=candidate_id,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )

    return resolutions, failures


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.semantic_boundary.ollama",
        description=(
            "M4.2b-B: esegue un file esterno Gold Pilot JSONL tramite un "
            "OllamaSemanticJudge locale e scrive le risoluzioni prodotte. "
            "I gold_label del file esterno non vengono mai inviati al modello."
        ),
    )
    parser.add_argument("gold_pilot_path", help="Path al file esterno gold-pilot-labeled.jsonl (non incluso nel repo)")
    parser.add_argument("output_path", help="Path di output per le SemanticResolution prodotte (JSONL)")
    parser.add_argument(
        "--failures-path",
        default=None,
        help="Path di output per i fallimenti espliciti (default: <output_path>.failures.jsonl)",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Modello Ollama (default: {DEFAULT_MODEL})")
    parser.add_argument(
        "--ollama-url",
        default=None,
        help=f"Endpoint Ollama (default: OLLAMA_BASE_URL o {DEFAULT_OLLAMA_BASE_URL})",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Timeout per candidate, in secondi")
    parser.add_argument("--seed", type=int, default=None, help="Seed opzionale, se supportato dal modello")
    args = parser.parse_args(argv)

    failures_path = args.failures_path or f"{args.output_path}.failures.jsonl"

    try:
        records = _read_jsonl(args.gold_pilot_path)
    except (OSError, RequestValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    judge = OllamaSemanticJudge(base_url=args.ollama_url, model=args.model, timeout=args.timeout, seed=args.seed)
    resolutions, failures = run_gold_pilot_batch(records, judge)

    with open(args.output_path, "w", encoding="utf-8") as handle:
        for resolution in resolutions:
            handle.write(json.dumps(resolution.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    with open(failures_path, "w", encoding="utf-8") as handle:
        for failure in failures:
            failure_record = {
                "candidate_id": failure.candidate_id,
                "error_type": failure.error_type,
                "error_message": failure.error_message,
            }
            handle.write(json.dumps(failure_record, ensure_ascii=False, sort_keys=True) + "\n")

    print(
        f"resolved={len(resolutions)} failed={len(failures)} "
        f"output={args.output_path} failures={failures_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
