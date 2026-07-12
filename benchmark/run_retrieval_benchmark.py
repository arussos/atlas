#!/usr/bin/env python3
"""
M3.2 — Retrieval Score Engine  (M3.2.1 — Baseline Correctness Hardening)

Valuta la qualità del retrieval RAG interrogando una Knowledge Collection
di Open WebUI e confrontando i chunk recuperati con i criteri del dataset.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENDPOINT DI RETRIEVAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST /api/v1/retrieval/query/collection

Payload (QueryCollectionsForm verificato su Open WebUI v0.10.2):
  collection_names      : list[str]        — UUID da GET /api/v1/knowledge/
  query                 : str              — testo della domanda
  k                     : int | None       — numero di chunk (None → server default)
  k_reranker            : int | None       — reranker top-k
  r                     : float | None     — soglia rilevanza (None = nessuna)
  hybrid                : bool | None      — None = lascia decidere al server
  hybrid_bm25_weight    : float | None
  enable_enriched_texts : bool | None

SEMANTICA HYBRID SEARCH (verificata nella build locale):
  Il backend attiva la ricerca ibrida solo quando:
    config.ENABLE_RAG_HYBRID_SEARCH is True
    AND (form_data.hybrid is None OR form_data.hybrid is True)

  In modalità baseline ("server"):
  • il campo `hybrid` NON viene incluso nel payload (equivale a None)
  • la configurazione persistente del server determina il comportamento effettivo
  • effective_hybrid_search = server_hybrid_search

Risposta:
  documents : [[chunk_text_1, ...]]   outer list = per-query, usiamo [0]
  metadatas : [[{name, source, ...}]]
  distances : [[score_1, ...]]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ISPEZIONE DELLA BUILD LOCALE (comandi da eseguire sul container)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. Ottenere il container ID di Open WebUI
docker ps --filter "ancestor=ghcr.io/open-webui/open-webui" --format "{{.ID}}"

# 2. Decorator della route e modello Pydantic
docker exec <CONTAINER_ID> grep -n \
  "query/collection\\|QueryCollectionsForm\\|hybrid_bm25" \
  /app/backend/open_webui/routers/retrieval.py | head -40

# 3. Codice sorgente completo del modello Pydantic
docker exec <CONTAINER_ID> python3 - <<'EOF'
from open_webui.routers.retrieval import QueryCollectionsForm
import inspect
print(inspect.getsource(QueryCollectionsForm))
EOF

# 4. Tipo di collection_names e field schema
docker exec <CONTAINER_ID> python3 - <<'EOF'
from open_webui.routers.retrieval import QueryCollectionsForm
import json
print(json.dumps(QueryCollectionsForm.model_json_schema(), indent=2))
EOF

# 5. Struttura della risposta (query_collection)
docker exec <CONTAINER_ID> python3 - <<'EOF'
from open_webui.retrieval.utils import query_collection
import inspect
src = inspect.getsource(query_collection)
print(src[:3000])
EOF

# 6. Chiavi esposte da GET /api/v1/retrieval/config
docker exec <CONTAINER_ID> python3 - <<'EOF'
import asyncio, json
from open_webui.routers.retrieval import get_rag_config
from unittest.mock import MagicMock
req = MagicMock()
req.app.state.config = MagicMock()
result = asyncio.run(get_rag_config(req))
print(json.dumps(dict(result), indent=2, default=str))
EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIGURAZIONE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Variabili d'ambiente:
  ATLAS_OPENWEBUI_URL      URL base di Open WebUI
  ATLAS_OPENWEBUI_EMAIL    email per l'autenticazione
  ATLAS_OPENWEBUI_PASSWORD password per l'autenticazione

Dipendenze esterne: PyYAML (benchmark/requirements.txt)

Fonte: github.com/open-webui/open-webui routers/retrieval.py,
       retrieval/utils.py, issue #14432.
       Evidenza locale su build v0.10.2: QueryCollectionsForm verificato.
"""

import argparse
import json
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print(
        "Error: PyYAML è richiesto.\n"
        "  pip3 install PyYAML\n"
        "  oppure: pip3 install -r benchmark/requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------

HTTP_TIMEOUT = 30
DEFAULT_TOP_K = 5

REQUIRED_QUESTION_FIELDS = [
    "id",
    "category",
    "question",
    "expected_documents",
    "must_contain",
    "must_not_contain",
    "notes",
]


# ---------------------------------------------------------------------------
# Helper configurazione
# ---------------------------------------------------------------------------


_SENTINEL = object()


def first_present(data: dict, *keys: str) -> Optional[object]:
    """
    Restituisce il valore della prima chiave presente in data.
    Preserva valori falsy validi: False, 0, "".
    Restituisce None solo se nessuna chiave è presente.
    """
    for key in keys:
        val = data.get(key, _SENTINEL)
        if val is not _SENTINEL:
            return val
    return None


# ---------------------------------------------------------------------------
# Dataclass di dominio
# ---------------------------------------------------------------------------


@dataclass
class MetricsSnapshot:
    """Snapshot di metriche di retrieval su un sottoinsieme di domande."""
    document_hit_rate: float
    average_document_recall: float
    average_term_coverage: float
    negative_precision_rate: float
    full_pass_rate: float


@dataclass
class BenchmarkConfig:
    project: str
    dataset: str
    timestamp_utc: str
    openwebui_version: Optional[str] = None
    embedding_model: Optional[str] = None
    # Hybrid search: tre campi distinti per tracciare la semantica completa
    server_hybrid_search: Optional[bool] = None   # ENABLE_RAG_HYBRID_SEARCH del server
    requested_hybrid_mode: str = "server"         # "server" in questa milestone
    effective_hybrid_search: Optional[bool] = None  # = server_hybrid_search in modo "server"
    top_k: Optional[int] = None
    top_k_reranker: Optional[int] = None
    full_context: Optional[bool] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None


@dataclass
class QuestionResult:
    id: str
    category: str
    question: str
    retrieved_documents: list
    expected_documents: list
    document_hit: bool
    document_recall: float
    matched_terms: list
    missing_terms: list
    forbidden_terms_found: list
    term_coverage: float
    negative_precision: bool
    full_pass: bool
    retrieval_count: int
    duration_ms: int
    error: Optional[str]


@dataclass
class CategorySummary:
    category: str
    total: int
    completed: int
    failed: int
    document_hit_rate: float
    average_document_recall: float
    average_term_coverage: float
    negative_precision_rate: float
    full_pass_rate: float


@dataclass
class BenchmarkSummary:
    configuration: BenchmarkConfig
    total_questions: int
    completed_questions: int
    failed_questions: int
    completed_only_metrics: MetricsSnapshot   # solo domande completate
    all_question_metrics: MetricsSnapshot     # intero dataset (errori = 0)
    total_duration_ms: int
    results: list
    categories: list


# ---------------------------------------------------------------------------
# Dataset: caricamento e validazione
# ---------------------------------------------------------------------------


def load_dataset(path: str) -> list[dict]:
    """Carica e restituisce le domande dal file YAML."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset non trovato: {path}")
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "questions" not in data:
        raise ValueError("Il dataset deve avere una chiave 'questions' al livello radice")
    questions = data["questions"]
    if not isinstance(questions, list):
        raise ValueError("'questions' deve essere una lista")
    return questions


def validate_dataset(questions: list[dict]) -> list[str]:
    """Restituisce la lista di errori di validazione (vuota = valido)."""
    errors: list[str] = []
    seen_ids: set[str] = set()
    for i, q in enumerate(questions):
        qid = q.get("id", f"<item {i}>")
        if qid in seen_ids:
            errors.append(f"{qid}: ID duplicato")
        seen_ids.add(qid)
        for fname in REQUIRED_QUESTION_FIELDS:
            if fname not in q:
                errors.append(f"{qid}: campo obbligatorio mancante '{fname}'")
        docs = q.get("expected_documents")
        if not isinstance(docs, list) or len(docs) == 0:
            errors.append(f"{qid}: expected_documents deve essere una lista non vuota")
        mc = q.get("must_contain")
        if not isinstance(mc, list) or len(mc) == 0:
            errors.append(f"{qid}: must_contain deve essere una lista non vuota")
        mnc = q.get("must_not_contain")
        if not isinstance(mnc, list):
            errors.append(f"{qid}: must_not_contain deve essere una lista")
    return errors


def filter_questions(
    questions: list[dict],
    question_id: Optional[str],
    category: Optional[str],
    limit: Optional[int],
) -> list[dict]:
    """Applica i filtri CLI alla lista di domande."""
    result = questions
    if question_id:
        result = [q for q in result if q["id"] == question_id]
    if category:
        result = [q for q in result if q["category"] == category]
    if limit and limit > 0:
        result = result[:limit]
    return result


# ---------------------------------------------------------------------------
# HTTP utilities
# ---------------------------------------------------------------------------


def _http_json(
    url: str,
    token: Optional[str] = None,
    payload: Optional[dict] = None,
    method: str = "GET",
    timeout: int = HTTP_TIMEOUT,
) -> dict:
    """Esegue una chiamata HTTP e restituisce il JSON parsato."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Autenticazione
# ---------------------------------------------------------------------------


def authenticate(base_url: str, email: str, password: str) -> str:
    """Restituisce il bearer token. Solleva RuntimeError in caso di errore."""
    url = f"{base_url}/api/v1/auths/signin"
    try:
        data = _http_json(url, payload={"email": email, "password": password}, method="POST")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Autenticazione fallita: HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"Autenticazione fallita: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("Autenticazione fallita: risposta non è JSON valido") from exc
    token = data.get("token")
    if not token:
        raise RuntimeError("Autenticazione fallita: nessun token nella risposta")
    return token


# ---------------------------------------------------------------------------
# Knowledge Collection
# ---------------------------------------------------------------------------


def _parse_collections_response(data: object) -> list[dict]:
    """Accetta lista diretta o risposta paginata {"items": [...], "total": N}."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data["items"]
    raise ValueError(
        f"Risposta GET /api/v1/knowledge/ inattesa: tipo {type(data).__name__}"
    )


def find_collection(base_url: str, token: str, project: str) -> tuple[str, str]:
    """Restituisce (collection_id, collection_name). Solleva RuntimeError se non trovata."""
    url = f"{base_url}/api/v1/knowledge/"
    try:
        data = _http_json(url, token=token)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Lista collection fallita: HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"Lista collection fallita: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("Lista collection fallita: risposta non è JSON valido") from exc
    collections = _parse_collections_response(data)
    for col in collections:
        if col.get("name") == project:
            return col["id"], col["name"]
    available = [c.get("name") for c in collections]
    raise RuntimeError(
        f"Knowledge Collection '{project}' non trovata. "
        f"Disponibili: {available}"
    )


# ---------------------------------------------------------------------------
# Configurazione Open WebUI (best-effort)
# ---------------------------------------------------------------------------


def fetch_openwebui_config(base_url: str, token: str) -> dict:
    """
    Recupera la configurazione runtime di Open WebUI.
    Usa first_present() per preservare valori falsy validi (False, 0).
    Restituisce dict con None per i campi non disponibili.
    """
    config: dict = {}

    try:
        data = _http_json(f"{base_url}/api/config", token=token)
        config["openwebui_version"] = data.get("version")
    except Exception:
        config["openwebui_version"] = None

    try:
        data = _http_json(f"{base_url}/api/v1/retrieval/config", token=token)
        config["embedding_model"] = first_present(
            data, "embedding_model", "EMBEDDING_MODEL", "RAG_EMBEDDING_MODEL"
        )
        config["server_hybrid_search"] = first_present(
            data, "ENABLE_RAG_HYBRID_SEARCH", "hybrid_search", "enable_rag_hybrid_search"
        )
        config["top_k"] = first_present(
            data, "top_k", "TOP_K", "RAG_TOP_K"
        )
        config["top_k_reranker"] = first_present(
            data, "top_k_reranker", "TOP_K_RERANKER"
        )
        config["full_context"] = first_present(
            data, "full_context", "RAG_FULL_CONTEXT"
        )
        config["chunk_size"] = first_present(
            data, "chunk_size", "CHUNK_SIZE", "RAG_CHUNK_SIZE"
        )
        config["chunk_overlap"] = first_present(
            data, "chunk_overlap", "CHUNK_OVERLAP", "RAG_CHUNK_OVERLAP"
        )
    except Exception:
        for key in (
            "embedding_model", "server_hybrid_search", "top_k", "top_k_reranker",
            "full_context", "chunk_size", "chunk_overlap",
        ):
            config.setdefault(key, None)

    return config


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def _extract_first(data: dict, key: str) -> list:
    """Estrae il primo inner-list da un campo di risposta annidato."""
    outer = data.get(key)
    if not outer or not isinstance(outer, list):
        return []
    first = outer[0] if outer else []
    return first if isinstance(first, list) else []


def retrieve_chunks(
    base_url: str,
    token: str,
    collection_id: str,
    question: str,
    top_k: int = DEFAULT_TOP_K,
    hybrid: Optional[bool] = None,
) -> tuple[list[str], list[dict], list[float]]:
    """
    Interroga l'endpoint POST /api/v1/retrieval/query/collection.

    hybrid=None  → il campo 'hybrid' è assente dal payload;
                   il server usa ENABLE_RAG_HYBRID_SEARCH (baseline "server")
    hybrid=True  → il campo 'hybrid': true è inviato esplicitamente
    hybrid=False → il campo 'hybrid': false è inviato esplicitamente

    Nota: la build locale usa `k = form_data.k if form_data.k else config.TOP_K`,
    quindi k=0 non è un override effettivo e ricade sul valore del server.

    Restituisce (testi, metadata, scores).
    """
    url = f"{base_url}/api/v1/retrieval/query/collection"
    payload: dict = {
        "collection_names": [collection_id],
        "query": question,
        "k": top_k,
        "r": None,
    }
    if hybrid is not None:
        payload["hybrid"] = hybrid
    # hybrid assente dal payload → server decide autonomamente

    data = _http_json(url, token=token, payload=payload, method="POST")
    texts: list[str] = _extract_first(data, "documents")
    metadatas: list[dict] = _extract_first(data, "metadatas")
    scores: list[float] = _extract_first(data, "distances")
    return texts, metadatas, scores


def extract_doc_names(metadatas: list[dict]) -> list[str]:
    """Estrae il nome del file sorgente dai metadata di ogni chunk."""
    names: list[str] = []
    for m in metadatas:
        raw = m.get("name") or m.get("source") or ""
        names.append(Path(raw).name if raw else "")
    return names


# ---------------------------------------------------------------------------
# Valutazione
# ---------------------------------------------------------------------------


def _norm(text: str) -> str:
    """Normalizzazione Unicode NFC + casefold + whitespace collassato."""
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def evaluate(
    question: dict,
    doc_names: list[str],
    retrieved_text: str,
    duration_ms: int,
    error: Optional[str] = None,
) -> QuestionResult:
    """Calcola tutte le metriche per una singola domanda."""
    expected = question["expected_documents"]
    must_contain = question["must_contain"]
    must_not_contain = question["must_not_contain"]

    norm_retrieved = {_norm(Path(d).name) for d in doc_names}
    found_expected = [e for e in expected if _norm(Path(e).name) in norm_retrieved]
    document_hit = len(found_expected) == len(expected)
    document_recall = len(found_expected) / len(expected) if expected else 1.0

    norm_text = _norm(retrieved_text)
    matched_terms = [t for t in must_contain if _norm(t) in norm_text]
    missing_terms = [t for t in must_contain if _norm(t) not in norm_text]
    term_coverage = len(matched_terms) / len(must_contain) if must_contain else 1.0

    if not must_not_contain:
        forbidden_terms_found: list[str] = []
        negative_precision = True
    else:
        forbidden_terms_found = [t for t in must_not_contain if _norm(t) in norm_text]
        negative_precision = len(forbidden_terms_found) == 0

    full_pass = document_hit and term_coverage == 1.0 and negative_precision

    return QuestionResult(
        id=question["id"],
        category=question["category"],
        question=question["question"],
        retrieved_documents=doc_names,
        expected_documents=expected,
        document_hit=document_hit,
        document_recall=document_recall,
        matched_terms=matched_terms,
        missing_terms=missing_terms,
        forbidden_terms_found=forbidden_terms_found,
        term_coverage=term_coverage,
        negative_precision=negative_precision,
        full_pass=full_pass,
        retrieval_count=len(doc_names),
        duration_ms=duration_ms,
        error=error,
    )


def evaluate_error(question: dict, error: str, duration_ms: int) -> QuestionResult:
    """Costruisce un QuestionResult di errore quando il retrieval fallisce."""
    return QuestionResult(
        id=question["id"],
        category=question["category"],
        question=question["question"],
        retrieved_documents=[],
        expected_documents=question["expected_documents"],
        document_hit=False,
        document_recall=0.0,
        matched_terms=[],
        missing_terms=question["must_contain"],
        forbidden_terms_found=[],
        term_coverage=0.0,
        negative_precision=False,
        full_pass=False,
        retrieval_count=0,
        duration_ms=duration_ms,
        error=error,
    )


# ---------------------------------------------------------------------------
# Aggregazione
# ---------------------------------------------------------------------------


def _safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _compute_metrics(subset: list[QuestionResult]) -> MetricsSnapshot:
    """Calcola le metriche su un sottoinsieme di QuestionResult."""
    if not subset:
        return MetricsSnapshot(0.0, 0.0, 0.0, 0.0, 0.0)
    return MetricsSnapshot(
        document_hit_rate=_safe_mean([1.0 if r.document_hit else 0.0 for r in subset]),
        average_document_recall=_safe_mean([r.document_recall for r in subset]),
        average_term_coverage=_safe_mean([r.term_coverage for r in subset]),
        negative_precision_rate=_safe_mean([1.0 if r.negative_precision else 0.0 for r in subset]),
        full_pass_rate=_safe_mean([1.0 if r.full_pass else 0.0 for r in subset]),
    )


def aggregate_results(results: list[QuestionResult]) -> dict:
    """
    Calcola due gruppi di metriche:
      completed_only_metrics — solo domande completate senza errori
      all_question_metrics   — intero dataset; errori = valori peggiori (0/False)
    """
    completed = [r for r in results if r.error is None]
    failed_count = sum(1 for r in results if r.error is not None)

    completed_only = _compute_metrics(completed)
    # evaluate_error() già imposta tutti i valori a 0/False → _compute_metrics
    # su tutti i risultati penalizza automaticamente gli errori
    all_questions = _compute_metrics(results)

    by_category: dict[str, list[QuestionResult]] = {}
    for r in results:
        by_category.setdefault(r.category, []).append(r)

    categories: list[CategorySummary] = []
    for cat in sorted(by_category):
        cat_results = by_category[cat]
        cat_completed = [r for r in cat_results if r.error is None]
        cat_failed = [r for r in cat_results if r.error is not None]
        m = _compute_metrics(cat_completed)
        categories.append(
            CategorySummary(
                category=cat,
                total=len(cat_results),
                completed=len(cat_completed),
                failed=len(cat_failed),
                document_hit_rate=m.document_hit_rate,
                average_document_recall=m.average_document_recall,
                average_term_coverage=m.average_term_coverage,
                negative_precision_rate=m.negative_precision_rate,
                full_pass_rate=m.full_pass_rate,
            )
        )

    return {
        "total": len(results),
        "completed": len(completed),
        "failed": failed_count,
        "completed_only_metrics": completed_only,
        "all_question_metrics": all_questions,
        "categories": categories,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_results_atomic(path: str, summary: dict) -> None:
    """Scrittura JSON atomica: file temporaneo → os.replace."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp, dest)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def _pct(value: float) -> str:
    return f"{value * 100:5.1f}%"


def print_report(
    project: str,
    total: int,
    completed: int,
    failed: int,
    metrics: dict,
    results: list[QuestionResult],
) -> None:
    print(f"\nRetrieval Benchmark — {project}\n")
    print(f"Questions: {total}")
    print(f"Completed: {completed}")
    print(f"Errors:    {failed}")
    print()
    print(f"Document Hit Rate:   {_pct(metrics['document_hit_rate'])}")
    print(f"Average Recall:      {_pct(metrics['average_document_recall'])}")
    print(f"Term Coverage:       {_pct(metrics['average_term_coverage'])}")
    print(f"Negative Precision:  {_pct(metrics['negative_precision_rate'])}")
    print(f"Full Pass Rate:      {_pct(metrics['full_pass_rate'])}")

    worst = sorted(
        results,
        key=lambda r: (r.full_pass, r.document_recall, r.term_coverage),
    )[:10]

    non_perfect = [r for r in worst if not r.full_pass or r.error]
    if non_perfect:
        print("\nWorst 10 questions:")
        for r in non_perfect:
            status = "ERROR" if r.error else "FAIL"
            print(
                f"  [{status}] {r.id} ({r.category})"
                f" — recall={_pct(r.document_recall)}, coverage={_pct(r.term_coverage)}"
            )
            if r.error:
                print(f"           Error: {r.error}")
            if r.missing_terms:
                print(f"           Missing terms: {r.missing_terms}")
            if not r.document_hit and not r.error:
                missing_docs = [
                    d for d in r.expected_documents
                    if _norm(Path(d).name) not in {_norm(rd) for rd in r.retrieved_documents}
                ]
                if missing_docs:
                    print(f"           Missing docs: {missing_docs}")


# ---------------------------------------------------------------------------
# Variabili d'ambiente
# ---------------------------------------------------------------------------


def load_env() -> tuple[str, str, str]:
    """Restituisce (url, email, password) dall'ambiente. Solleva RuntimeError se mancanti."""
    url = os.environ.get("ATLAS_OPENWEBUI_URL", "").rstrip("/")
    email = os.environ.get("ATLAS_OPENWEBUI_EMAIL", "")
    password = os.environ.get("ATLAS_OPENWEBUI_PASSWORD", "")
    missing = [
        name for name, val in [
            ("ATLAS_OPENWEBUI_URL", url),
            ("ATLAS_OPENWEBUI_EMAIL", email),
            ("ATLAS_OPENWEBUI_PASSWORD", password),
        ] if not val
    ]
    if missing:
        raise RuntimeError(
            f"Variabili d'ambiente mancanti: {', '.join(missing)}"
        )
    return url, email, password


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="M3.2 — Retrieval benchmark runner per Open WebUI Knowledge Collections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Esempi:\n"
            "  # Dry-run (nessuna chiamata HTTP)\n"
            "  python3 benchmark/run_retrieval_benchmark.py \\\n"
            "    --dataset benchmark/abrazo/retrieval-benchmark.yaml \\\n"
            "    --project ABRAZO --output benchmark/results/out.json --dry-run\n\n"
            "  # Baseline completa\n"
            "  python3 benchmark/run_retrieval_benchmark.py \\\n"
            "    --dataset benchmark/abrazo/retrieval-benchmark.yaml \\\n"
            "    --project ABRAZO \\\n"
            "    --output benchmark/results/abrazo-baseline-v1.json"
        ),
    )
    p.add_argument("--dataset", required=True, help="Percorso al file YAML del dataset")
    p.add_argument("--project", required=True, help="Nome della Knowledge Collection (es. ABRAZO)")
    p.add_argument("--output", required=True, help="Percorso del file JSON di output")
    p.add_argument("--limit", type=int, default=None, metavar="N",
                   help="Esegui solo le prime N domande")
    p.add_argument("--question-id", default=None, metavar="ID",
                   help="Esegui una singola domanda per ID")
    p.add_argument("--category", default=None, metavar="CATEGORY",
                   help="Esegui solo le domande di una categoria")
    p.add_argument("--dry-run", action="store_true",
                   help="Valida dataset e configurazione senza chiamate HTTP")
    p.add_argument("--verbose", action="store_true",
                   help="Stampa il dettaglio del retrieval per ogni domanda")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Caricamento e validazione dataset
    try:
        questions = load_dataset(args.dataset)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    errors = validate_dataset(questions)
    if errors:
        print("Validazione dataset fallita:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    selected = filter_questions(questions, args.question_id, args.category, args.limit)
    if not selected:
        print("Nessuna domanda corrisponde ai filtri.", file=sys.stderr)
        return 1

    # Dry-run
    if args.dry_run:
        print(f"Dry-run — {len(selected)} domanda/e selezionata/e da '{args.dataset}'")
        print(f"Project: {args.project}  Output: {args.output}")
        print()
        for q in selected:
            print(f"  [{q['category']}] {q['id']}: {q['question'][:70]}")
        print()
        print("Nessuna chiamata HTTP eseguita.")
        return 0

    # Variabili d'ambiente
    try:
        base_url, email, password = load_env()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Autenticazione
    print(f"Autenticazione verso {base_url} ...")
    try:
        token = authenticate(base_url, email, password)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Ricerca collection
    print(f"Ricerca collection '{args.project}' ...")
    try:
        collection_id, collection_name = find_collection(base_url, token, args.project)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Configurazione (best-effort)
    print("Recupero configurazione Open WebUI ...")
    ow_config = fetch_openwebui_config(base_url, token)

    # top_k: None se non presente, int altrimenti (k=0 → server usa il suo default)
    raw_top_k = ow_config.get("top_k")
    top_k: int = int(raw_top_k) if raw_top_k is not None else DEFAULT_TOP_K

    # Hybrid search: modalità "server" — non forziamo nulla nel payload
    server_hybrid = ow_config.get("server_hybrid_search")  # bool | None
    requested_hybrid_mode = "server"
    effective_hybrid = server_hybrid  # in modo "server" effective = server config

    config = BenchmarkConfig(
        project=args.project,
        dataset=str(Path(args.dataset).resolve()),
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        openwebui_version=ow_config.get("openwebui_version"),
        embedding_model=ow_config.get("embedding_model"),
        server_hybrid_search=server_hybrid,
        requested_hybrid_mode=requested_hybrid_mode,
        effective_hybrid_search=effective_hybrid,
        top_k=top_k,
        top_k_reranker=ow_config.get("top_k_reranker"),
        full_context=ow_config.get("full_context"),
        chunk_size=ow_config.get("chunk_size"),
        chunk_overlap=ow_config.get("chunk_overlap"),
    )

    # Esecuzione benchmark — hybrid=None lascia decidere al server
    cid_short = collection_id[:8] + "..."
    print(
        f"\nEsecuzione {len(selected)} domanda/e su collection "
        f"'{collection_name}' (id={cid_short})\n"
    )

    results: list[QuestionResult] = []
    total_start = time.monotonic()

    for i, q in enumerate(selected, 1):
        print(f"  [{i:3}/{len(selected)}] {q['id']}", end=" ", flush=True)
        t0 = time.monotonic()
        try:
            texts, metadatas, _ = retrieve_chunks(
                base_url, token, collection_id, q["question"],
                top_k=top_k, hybrid=None,  # baseline: server decide
            )
            duration_ms = int((time.monotonic() - t0) * 1000)
            doc_names = extract_doc_names(metadatas)
            retrieved_text = "\n".join(texts)
            result = evaluate(q, doc_names, retrieved_text, duration_ms)
            results.append(result)

            status = "PASS" if result.full_pass else "fail"
            print(
                f"→ {status}"
                f" (recall={_pct(result.document_recall)}"
                f" coverage={_pct(result.term_coverage)}"
                f" {duration_ms}ms)"
            )

            if args.verbose:
                print(f"         docs:    {doc_names}")
                if result.missing_terms:
                    print(f"         missing: {result.missing_terms}")

        except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            duration_ms = int((time.monotonic() - t0) * 1000)
            error_msg = str(exc)
            results.append(evaluate_error(q, error_msg, duration_ms))
            print(f"→ ERROR: {error_msg}")

    total_duration_ms = int((time.monotonic() - total_start) * 1000)

    # Aggregazione
    agg = aggregate_results(results)

    summary = BenchmarkSummary(
        configuration=config,
        total_questions=agg["total"],
        completed_questions=agg["completed"],
        failed_questions=agg["failed"],
        completed_only_metrics=agg["completed_only_metrics"],
        all_question_metrics=agg["all_question_metrics"],
        total_duration_ms=total_duration_ms,
        results=results,
        categories=agg["categories"],
    )

    # Scrittura output atomica — fallimento = exit 1
    summary_dict = asdict(summary)
    try:
        write_results_atomic(args.output, summary_dict)
        print(f"\nRisultati scritti in: {args.output}")
    except Exception as exc:
        print(f"\nError: impossibile scrivere i risultati in '{args.output}': {exc}", file=sys.stderr)
        return 1

    # Report console — usa all_question_metrics (penalizza gli errori)
    all_metrics_dict = asdict(agg["all_question_metrics"])
    print_report(
        args.project,
        agg["total"],
        agg["completed"],
        agg["failed"],
        all_metrics_dict,
        results,
    )

    return 0 if agg["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
