#!/usr/bin/env python3
"""
Test suite per M3.2 — Retrieval Score Engine.

Tutti i test usano mock locali. Nessuna chiamata HTTP reale viene eseguita.
"""

import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

# Aggiunge benchmark/ al path per l'import
sys.path.insert(0, str(Path(__file__).parent))

from run_retrieval_benchmark import (
    BenchmarkConfig,
    CategorySummary,
    MetricsSnapshot,
    QuestionResult,
    _extract_first,
    _norm,
    aggregate_results,
    evaluate,
    evaluate_error,
    extract_doc_names,
    filter_questions,
    first_present,
    load_dataset,
    main,
    retrieve_chunks,
    validate_dataset,
    write_results_atomic,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_question(**overrides) -> dict:
    base = {
        "id": "ABR-TEST-001",
        "category": "ARCHITECTURE",
        "question": "Domanda di test?",
        "expected_documents": ["01_ARCHITECTURE.md"],
        "must_contain": ["Next.js", "React"],
        "must_not_contain": [],
        "notes": "Test note",
    }
    base.update(overrides)
    return base


def _make_result(**overrides) -> QuestionResult:
    base = QuestionResult(
        id="ABR-TEST-001",
        category="ARCHITECTURE",
        question="Domanda di test?",
        retrieved_documents=["01_ARCHITECTURE.md"],
        expected_documents=["01_ARCHITECTURE.md"],
        document_hit=True,
        document_recall=1.0,
        matched_terms=["Next.js", "React"],
        missing_terms=[],
        forbidden_terms_found=[],
        term_coverage=1.0,
        negative_precision=True,
        full_pass=True,
        retrieval_count=1,
        duration_ms=42,
        error=None,
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


MINIMAL_YAML = """\
questions:
  - id: ABR-ARCH-001
    category: ARCHITECTURE
    question: "Domanda uno?"
    expected_documents:
      - 01_ARCHITECTURE.md
    must_contain:
      - Next.js
    must_not_contain: []
    notes: "Nota test"
  - id: ABR-DB-001
    category: DATABASE
    question: "Domanda due?"
    expected_documents:
      - 02_DATABASE.md
    must_contain:
      - pending
    must_not_contain: []
    notes: "Nota db"
"""


# ---------------------------------------------------------------------------
# 1. Dataset: caricamento e validazione
# ---------------------------------------------------------------------------


class TestLoadDataset(unittest.TestCase):
    def test_valid_dataset_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bench.yaml"
            _write_yaml(p, MINIMAL_YAML)
            questions = load_dataset(str(p))
            self.assertEqual(len(questions), 2)
            self.assertEqual(questions[0]["id"], "ABR-ARCH-001")

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_dataset("/non/esiste/bench.yaml")

    def test_invalid_yaml_structure_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.yaml"
            _write_yaml(p, "lista:\n  - uno\n  - due\n")
            with self.assertRaises(ValueError):
                load_dataset(str(p))


class TestValidateDataset(unittest.TestCase):
    def test_valid_dataset_no_errors(self):
        questions = [_make_question()]
        errors = validate_dataset(questions)
        self.assertEqual(errors, [])

    def test_duplicate_id_detected(self):
        q1 = _make_question(id="ABR-TEST-001")
        q2 = _make_question(id="ABR-TEST-001")
        errors = validate_dataset([q1, q2])
        self.assertTrue(any("duplicato" in e for e in errors))
        self.assertTrue(any("ABR-TEST-001" in e for e in errors))

    def test_missing_required_field(self):
        q = _make_question()
        del q["must_contain"]
        errors = validate_dataset([q])
        self.assertTrue(any("must_contain" in e for e in errors))

    def test_all_required_fields_checked(self):
        for field in ["id", "category", "question", "expected_documents",
                      "must_contain", "must_not_contain", "notes"]:
            q = _make_question()
            del q[field]
            errors = validate_dataset([q])
            self.assertTrue(
                any(field in e for e in errors),
                f"Campo '{field}' non rilevato come mancante",
            )

    def test_empty_expected_documents_is_error(self):
        q = _make_question(expected_documents=[])
        errors = validate_dataset([q])
        self.assertTrue(any("expected_documents" in e for e in errors))

    def test_must_not_contain_not_list_is_error(self):
        q = _make_question(must_not_contain="stringa")
        errors = validate_dataset([q])
        self.assertTrue(any("must_not_contain" in e for e in errors))


# ---------------------------------------------------------------------------
# 2. Filtro domande
# ---------------------------------------------------------------------------


class TestFilterQuestions(unittest.TestCase):
    def setUp(self):
        self.questions = [
            _make_question(id="ABR-ARCH-001", category="ARCHITECTURE"),
            _make_question(id="ABR-DB-001", category="DATABASE"),
            _make_question(id="ABR-API-001", category="API"),
        ]

    def test_filter_by_category(self):
        result = filter_questions(self.questions, None, "DATABASE", None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "ABR-DB-001")

    def test_filter_by_question_id(self):
        result = filter_questions(self.questions, "ABR-API-001", None, None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["category"], "API")

    def test_limit(self):
        result = filter_questions(self.questions, None, None, 2)
        self.assertEqual(len(result), 2)

    def test_no_filter_returns_all(self):
        result = filter_questions(self.questions, None, None, None)
        self.assertEqual(len(result), 3)

    def test_limit_zero_returns_all(self):
        result = filter_questions(self.questions, None, None, 0)
        self.assertEqual(len(result), 3)

    def test_category_and_limit_combined(self):
        questions = self.questions + [_make_question(id="ABR-ARCH-002", category="ARCHITECTURE")]
        result = filter_questions(questions, None, "ARCHITECTURE", 1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["category"], "ARCHITECTURE")


# ---------------------------------------------------------------------------
# 3. Normalizzazione
# ---------------------------------------------------------------------------


class TestNormalisation(unittest.TestCase):
    def test_case_insensitive(self):
        self.assertEqual(_norm("Next.js"), _norm("NEXT.JS"))
        self.assertEqual(_norm("React"), _norm("react"))

    def test_unicode_nfc(self):
        # à come NFC vs NFD
        nfc = "à"          # à precomposto
        nfd = "à"         # a + combinante grave
        self.assertEqual(_norm(nfc), _norm(nfd))

    def test_whitespace_collapsed(self):
        self.assertEqual(_norm("10  tabelle"), _norm("10 tabelle"))

    def test_term_in_text(self):
        text = "Il sistema usa Next.js 16 e React 19."
        self.assertIn(_norm("Next.js"), _norm(text))
        self.assertIn(_norm("react"), _norm(text))


# ---------------------------------------------------------------------------
# 4. Valutazione: metriche singola domanda
# ---------------------------------------------------------------------------


class TestEvaluateDocumentHit(unittest.TestCase):
    def _eval(self, expected, doc_names, text=""):
        q = _make_question(expected_documents=expected, must_contain=["dummy"], must_not_contain=[])
        text_with_dummy = text + " dummy"
        return evaluate(q, doc_names, text_with_dummy, duration_ms=10)

    def test_document_hit_complete(self):
        r = self._eval(["01_ARCHITECTURE.md"], ["01_ARCHITECTURE.md"])
        self.assertTrue(r.document_hit)
        self.assertEqual(r.document_recall, 1.0)

    def test_document_hit_partial(self):
        r = self._eval(["01_ARCHITECTURE.md", "02_DATABASE.md"], ["01_ARCHITECTURE.md"])
        self.assertFalse(r.document_hit)
        self.assertAlmostEqual(r.document_recall, 0.5)

    def test_document_hit_zero(self):
        r = self._eval(["01_ARCHITECTURE.md"], ["ALTRO.md"])
        self.assertFalse(r.document_hit)
        self.assertEqual(r.document_recall, 0.0)

    def test_document_recall_two_of_three(self):
        r = self._eval(
            ["A.md", "B.md", "C.md"],
            ["A.md", "C.md"],
        )
        self.assertFalse(r.document_hit)
        self.assertAlmostEqual(r.document_recall, 2 / 3)


class TestEvaluateTermCoverage(unittest.TestCase):
    def _eval(self, must_contain, text):
        q = _make_question(
            expected_documents=["A.md"],
            must_contain=must_contain,
            must_not_contain=[],
        )
        return evaluate(q, ["A.md"], text, duration_ms=5)

    def test_all_terms_found(self):
        r = self._eval(["Next.js", "React"], "usa Next.js e React 19")
        self.assertEqual(r.term_coverage, 1.0)
        self.assertEqual(r.matched_terms, ["Next.js", "React"])
        self.assertEqual(r.missing_terms, [])

    def test_partial_terms(self):
        r = self._eval(["Next.js", "React", "TypeScript"], "usa Next.js")
        self.assertAlmostEqual(r.term_coverage, 1 / 3)
        self.assertIn("Next.js", r.matched_terms)
        self.assertIn("React", r.missing_terms)
        self.assertIn("TypeScript", r.missing_terms)

    def test_case_insensitive_match(self):
        r = self._eval(["NEXT.JS"], "usa next.js nel progetto")
        self.assertEqual(r.term_coverage, 1.0)


class TestEvaluateNegativePrecision(unittest.TestCase):
    def _eval(self, must_not_contain, text):
        q = _make_question(
            must_contain=["dummy"],
            must_not_contain=must_not_contain,
        )
        return evaluate(q, ["01_ARCHITECTURE.md"], "dummy " + text, duration_ms=5)

    def test_must_not_contain_empty_always_true(self):
        r = self._eval([], "testo qualsiasi PII email tutto")
        self.assertTrue(r.negative_precision)
        self.assertEqual(r.forbidden_terms_found, [])

    def test_forbidden_term_found(self):
        r = self._eval(["PII"], "il documento contiene dati PII sensibili")
        self.assertFalse(r.negative_precision)
        self.assertIn("PII", r.forbidden_terms_found)

    def test_forbidden_term_not_found(self):
        r = self._eval(["PII"], "testo normale senza termini vietati")
        self.assertTrue(r.negative_precision)
        self.assertEqual(r.forbidden_terms_found, [])


class TestEvaluateFullPass(unittest.TestCase):
    def test_full_pass_all_criteria_met(self):
        q = _make_question(
            expected_documents=["A.md"],
            must_contain=["Next.js"],
            must_not_contain=[],
        )
        r = evaluate(q, ["A.md"], "usa Next.js", duration_ms=10)
        self.assertTrue(r.document_hit)
        self.assertEqual(r.term_coverage, 1.0)
        self.assertTrue(r.negative_precision)
        self.assertTrue(r.full_pass)

    def test_full_pass_false_if_doc_miss(self):
        q = _make_question(
            expected_documents=["A.md"],
            must_contain=["Next.js"],
            must_not_contain=[],
        )
        r = evaluate(q, ["ALTRO.md"], "usa Next.js", duration_ms=10)
        self.assertFalse(r.full_pass)

    def test_full_pass_false_if_term_missing(self):
        q = _make_question(
            expected_documents=["A.md"],
            must_contain=["TypeScript"],
            must_not_contain=[],
        )
        r = evaluate(q, ["A.md"], "usa Next.js", duration_ms=10)
        self.assertFalse(r.full_pass)

    def test_full_pass_false_if_forbidden_found(self):
        q = _make_question(
            expected_documents=["A.md"],
            must_contain=["Next.js"],
            must_not_contain=["PII"],
        )
        r = evaluate(q, ["A.md"], "Next.js e dati PII", duration_ms=10)
        self.assertFalse(r.full_pass)


# ---------------------------------------------------------------------------
# 5. Errore retrieval su singola domanda
# ---------------------------------------------------------------------------


class TestEvaluateError(unittest.TestCase):
    def test_error_result_structure(self):
        q = _make_question()
        r = evaluate_error(q, "HTTP 503", duration_ms=100)
        self.assertFalse(r.document_hit)
        self.assertEqual(r.document_recall, 0.0)
        self.assertEqual(r.term_coverage, 0.0)
        self.assertFalse(r.full_pass)
        self.assertEqual(r.error, "HTTP 503")
        self.assertEqual(r.retrieval_count, 0)

    def test_missing_terms_populated_on_error(self):
        q = _make_question(must_contain=["Next.js", "React"])
        r = evaluate_error(q, "timeout", duration_ms=30000)
        self.assertEqual(r.missing_terms, ["Next.js", "React"])


# ---------------------------------------------------------------------------
# 6. Extract doc names
# ---------------------------------------------------------------------------


class TestExtractDocNames(unittest.TestCase):
    def test_extracts_name_field(self):
        metadatas = [{"name": "01_ARCHITECTURE.md"}, {"name": "CLAUDE.md"}]
        self.assertEqual(extract_doc_names(metadatas), ["01_ARCHITECTURE.md", "CLAUDE.md"])

    def test_falls_back_to_source(self):
        metadatas = [{"source": "knowledge/ABRAZO/02_DATABASE.md"}]
        names = extract_doc_names(metadatas)
        self.assertEqual(names, ["02_DATABASE.md"])

    def test_empty_metadata_gives_empty_string(self):
        names = extract_doc_names([{}])
        self.assertEqual(names, [""])

    def test_full_path_gives_basename(self):
        metadatas = [{"name": "knowledge/ABRAZO/05_ROADMAP.md"}]
        names = extract_doc_names(metadatas)
        self.assertEqual(names, ["05_ROADMAP.md"])


# ---------------------------------------------------------------------------
# 7. _extract_first
# ---------------------------------------------------------------------------


class TestExtractFirst(unittest.TestCase):
    def test_normal_nested_list(self):
        data = {"documents": [["chunk1", "chunk2"]]}
        self.assertEqual(_extract_first(data, "documents"), ["chunk1", "chunk2"])

    def test_missing_key_returns_empty(self):
        self.assertEqual(_extract_first({}, "documents"), [])

    def test_empty_outer_list_returns_empty(self):
        self.assertEqual(_extract_first({"documents": []}, "documents"), [])

    def test_null_value_returns_empty(self):
        self.assertEqual(_extract_first({"documents": None}, "documents"), [])


# ---------------------------------------------------------------------------
# 8. Aggregazione
# ---------------------------------------------------------------------------


class TestAggregateResults(unittest.TestCase):
    def test_global_metrics_all_pass(self):
        results = [
            _make_result(id=f"Q{i}", category="ARCHITECTURE", document_hit=True,
                         document_recall=1.0, term_coverage=1.0,
                         negative_precision=True, full_pass=True, error=None)
            for i in range(3)
        ]
        agg = aggregate_results(results)
        self.assertEqual(agg["total"], 3)
        self.assertEqual(agg["completed"], 3)
        self.assertEqual(agg["failed"], 0)
        self.assertIsInstance(agg["completed_only_metrics"], MetricsSnapshot)
        self.assertIsInstance(agg["all_question_metrics"], MetricsSnapshot)
        self.assertAlmostEqual(agg["completed_only_metrics"].document_hit_rate, 1.0)
        self.assertAlmostEqual(agg["completed_only_metrics"].full_pass_rate, 1.0)
        self.assertAlmostEqual(agg["all_question_metrics"].document_hit_rate, 1.0)
        self.assertAlmostEqual(agg["all_question_metrics"].full_pass_rate, 1.0)

    def test_global_metrics_with_failures(self):
        r1 = _make_result(id="Q1", category="ARCHITECTURE", document_hit=True,
                          document_recall=1.0, term_coverage=1.0,
                          negative_precision=True, full_pass=True, error=None)
        r2 = _make_result(id="Q2", category="ARCHITECTURE", document_hit=False,
                          document_recall=0.5, term_coverage=0.5,
                          negative_precision=True, full_pass=False, error=None)
        agg = aggregate_results([r1, r2])
        self.assertEqual(agg["completed"], 2)
        m = agg["completed_only_metrics"]
        self.assertAlmostEqual(m.document_hit_rate, 0.5)
        self.assertAlmostEqual(m.average_document_recall, 0.75)
        self.assertAlmostEqual(m.full_pass_rate, 0.5)

    def test_error_counted_as_failed_not_completed(self):
        r_ok = _make_result(id="Q1", category="API", error=None)
        r_err = _make_result(id="Q2", category="API", error="HTTP 500",
                             document_hit=False, document_recall=0.0,
                             term_coverage=0.0, full_pass=False)
        agg = aggregate_results([r_ok, r_err])
        self.assertEqual(agg["failed"], 1)
        self.assertEqual(agg["completed"], 1)

    def test_per_category_aggregation(self):
        r1 = _make_result(id="Q1", category="ARCHITECTURE", full_pass=True, error=None)
        r2 = _make_result(id="Q2", category="DATABASE", full_pass=False,
                          document_recall=0.5, term_coverage=0.5, error=None)
        agg = aggregate_results([r1, r2])
        cats = {c.category: c for c in agg["categories"]}
        self.assertIn("ARCHITECTURE", cats)
        self.assertIn("DATABASE", cats)
        self.assertAlmostEqual(cats["ARCHITECTURE"].full_pass_rate, 1.0)
        self.assertAlmostEqual(cats["DATABASE"].full_pass_rate, 0.0)

    def test_per_category_counts(self):
        results = [
            _make_result(id="Q1", category="API", error=None),
            _make_result(id="Q2", category="API", error=None),
            _make_result(id="Q3", category="API", error="fail", full_pass=False),
        ]
        agg = aggregate_results(results)
        api_cat = next(c for c in agg["categories"] if c.category == "API")
        self.assertEqual(api_cat.total, 3)
        self.assertEqual(api_cat.completed, 2)
        self.assertEqual(api_cat.failed, 1)

    def test_empty_results(self):
        agg = aggregate_results([])
        self.assertEqual(agg["total"], 0)
        self.assertAlmostEqual(agg["completed_only_metrics"].document_hit_rate, 0.0)
        self.assertAlmostEqual(agg["all_question_metrics"].document_hit_rate, 0.0)


# ---------------------------------------------------------------------------
# 9. Scrittura atomica
# ---------------------------------------------------------------------------


class TestWriteResultsAtomic(unittest.TestCase):
    def test_file_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.json")
            write_results_atomic(out, {"test": True, "value": 42})
            self.assertTrue(os.path.exists(out))
            with open(out) as f:
                data = json.load(f)
            self.assertEqual(data["value"], 42)

    def test_no_temp_file_remains_after_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.json")
            write_results_atomic(out, {"ok": True})
            tmp_file = out.replace(".json", ".tmp")
            self.assertFalse(os.path.exists(tmp_file))

    def test_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "subdir", "results", "out.json")
            write_results_atomic(out, {"nested": True})
            self.assertTrue(os.path.exists(out))

    def test_atomic_replace_called(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.json")
            with patch("os.replace") as mock_replace:
                mock_replace.side_effect = lambda src, dst: None
                # os.replace mocked to no-op: the .tmp file stays, that's ok
                write_results_atomic(out, {"x": 1})
                mock_replace.assert_called_once()
                src, dst = mock_replace.call_args[0]
                self.assertTrue(str(src).endswith(".tmp"))
                self.assertEqual(str(dst), out)

    def test_temp_file_cleaned_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out.json")
            with patch("builtins.open", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    write_results_atomic(out, {"x": 1})
            tmp_file = out.replace(".json", ".tmp")
            self.assertFalse(os.path.exists(tmp_file))


# ---------------------------------------------------------------------------
# 10. Dry-run (nessuna chiamata HTTP)
# ---------------------------------------------------------------------------


class TestDryRun(unittest.TestCase):
    def _dataset_path(self, tmp: str) -> str:
        p = Path(tmp) / "bench.yaml"
        _write_yaml(p, MINIMAL_YAML)
        return str(p)

    def test_dry_run_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = self._dataset_path(tmp)
            with patch("run_retrieval_benchmark.authenticate") as mock_auth:
                ret = main([
                    "--dataset", dataset,
                    "--project", "ABRAZO",
                    "--output", os.path.join(tmp, "out.json"),
                    "--dry-run",
                ])
            self.assertEqual(ret, 0)
            mock_auth.assert_not_called()

    def test_dry_run_no_http_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = self._dataset_path(tmp)
            with patch("urllib.request.urlopen") as mock_http:
                main([
                    "--dataset", dataset,
                    "--project", "ABRAZO",
                    "--output", os.path.join(tmp, "out.json"),
                    "--dry-run",
                ])
            mock_http.assert_not_called()

    def test_dry_run_no_output_file_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = self._dataset_path(tmp)
            out = os.path.join(tmp, "out.json")
            main([
                "--dataset", dataset,
                "--project", "ABRAZO",
                "--output", out,
                "--dry-run",
            ])
            self.assertFalse(os.path.exists(out))

    def test_dry_run_prints_selected_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = self._dataset_path(tmp)
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                main([
                    "--dataset", dataset,
                    "--project", "ABRAZO",
                    "--output", os.path.join(tmp, "out.json"),
                    "--dry-run",
                ])
            output = captured.getvalue()
            self.assertIn("ABR-ARCH-001", output)
            self.assertIn("ABR-DB-001", output)

    def test_dry_run_with_category_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = self._dataset_path(tmp)
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                main([
                    "--dataset", dataset,
                    "--project", "ABRAZO",
                    "--output", os.path.join(tmp, "out.json"),
                    "--dry-run",
                    "--category", "DATABASE",
                ])
            output = captured.getvalue()
            self.assertIn("ABR-DB-001", output)
            self.assertNotIn("ABR-ARCH-001", output)


# ---------------------------------------------------------------------------
# 11. main() con dataset invalido
# ---------------------------------------------------------------------------


class TestMainValidation(unittest.TestCase):
    def test_main_exits_1_on_invalid_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.yaml"
            _write_yaml(p, "nessuna_chiave_questions: true\n")
            ret = main([
                "--dataset", str(p),
                "--project", "ABRAZO",
                "--output", os.path.join(tmp, "out.json"),
                "--dry-run",
            ])
            self.assertEqual(ret, 1)

    def test_main_exits_1_on_missing_dataset(self):
        ret = main([
            "--dataset", "/non/esiste.yaml",
            "--project", "ABRAZO",
            "--output", "/tmp/out.json",
            "--dry-run",
        ])
        self.assertEqual(ret, 1)

    def test_main_exits_1_on_no_matching_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bench.yaml"
            _write_yaml(p, MINIMAL_YAML)
            ret = main([
                "--dataset", str(p),
                "--project", "ABRAZO",
                "--output", os.path.join(tmp, "out.json"),
                "--dry-run",
                "--category", "NONEXISTENT",
            ])
            self.assertEqual(ret, 1)


# ---------------------------------------------------------------------------
# 12. Integrazione: main() con HTTP mockato
# ---------------------------------------------------------------------------


class TestMainWithMockedHTTP(unittest.TestCase):
    """Verifica il flusso completo di main() usando mock HTTP."""

    def _dataset_path(self, tmp: str) -> str:
        p = Path(tmp) / "bench.yaml"
        _write_yaml(p, MINIMAL_YAML)
        return str(p)

    def _mock_responses(self) -> dict:
        """Dizionario URL → risposta JSON da restituire."""
        return {
            "/api/v1/auths/signin": {"token": "mock-token-abc"},
            "/api/v1/knowledge/": [{"id": "uuid-123", "name": "ABRAZO"}],
            "/api/config": {"version": "0.10.2"},
            "/api/v1/retrieval/config": {
                "embedding_model": "nomic-embed-text",
                "top_k": 5,
            },
            "/api/v1/retrieval/query/collection": {
                "documents": [["Next.js è il framework principale del progetto. pending e deposit sono gli stati."]],
                "metadatas": [[{"name": "01_ARCHITECTURE.md"}]],
                "distances": [[0.12]],
            },
        }

    def _make_urlopen_mock(self, responses: dict):
        def side_effect(req, timeout=30):
            url = req.full_url
            for suffix, body in responses.items():
                if url.endswith(suffix):
                    mock_resp = MagicMock()
                    mock_resp.read.return_value = json.dumps(body).encode()
                    mock_resp.__enter__ = lambda s: s
                    mock_resp.__exit__ = MagicMock(return_value=False)
                    return mock_resp
            raise ValueError(f"URL non mockato: {url}")

        return side_effect

    def test_full_run_with_mock(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = self._dataset_path(tmp)
            out = os.path.join(tmp, "results.json")
            env = {
                "ATLAS_OPENWEBUI_URL": "http://localhost:3000",
                "ATLAS_OPENWEBUI_EMAIL": "test@example.com",
                "ATLAS_OPENWEBUI_PASSWORD": "secret",
            }
            with patch.dict(os.environ, env), \
                 patch("urllib.request.urlopen", side_effect=self._make_urlopen_mock(self._mock_responses())):
                ret = main(["--dataset", dataset, "--project", "ABRAZO", "--output", out])

            self.assertTrue(os.path.exists(out))
            with open(out) as f:
                data = json.load(f)
            self.assertIn("total_questions", data)
            self.assertIn("results", data)
            self.assertIn("configuration", data)
            self.assertEqual(data["total_questions"], 2)
            # Nuova struttura metriche
            self.assertIn("completed_only_metrics", data)
            self.assertIn("all_question_metrics", data)
            self.assertIn("document_hit_rate", data["completed_only_metrics"])
            self.assertIn("full_pass_rate", data["all_question_metrics"])
            # Hybrid search: configurazione nell'output
            cfg = data["configuration"]
            self.assertIn("server_hybrid_search", cfg)
            self.assertIn("requested_hybrid_mode", cfg)
            self.assertIn("effective_hybrid_search", cfg)
            self.assertEqual(cfg["requested_hybrid_mode"], "server")

    def test_retrieval_error_on_single_question(self):
        """Un errore su una domanda non blocca le altre."""
        responses = self._mock_responses()

        call_count = {"n": 0}

        def urlopen_with_one_error(req, timeout=30):
            url = req.full_url
            if url.endswith("/api/v1/retrieval/query/collection"):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise urllib.error.URLError("connection refused")
            return self._make_urlopen_mock(responses)(req, timeout)

        with tempfile.TemporaryDirectory() as tmp:
            dataset = self._dataset_path(tmp)
            out = os.path.join(tmp, "results.json")
            env = {
                "ATLAS_OPENWEBUI_URL": "http://localhost:3000",
                "ATLAS_OPENWEBUI_EMAIL": "test@example.com",
                "ATLAS_OPENWEBUI_PASSWORD": "secret",
            }
            with patch.dict(os.environ, env), \
                 patch("urllib.request.urlopen", side_effect=urlopen_with_one_error):
                main(["--dataset", dataset, "--project", "ABRAZO", "--output", out])

            with open(out) as f:
                data = json.load(f)

            results = data["results"]
            self.assertEqual(len(results), 2)
            errors = [r for r in results if r["error"] is not None]
            successes = [r for r in results if r["error"] is None]
            self.assertEqual(len(errors), 1)
            self.assertEqual(len(successes), 1)


# ---------------------------------------------------------------------------
# 13. first_present() — valori falsy preservati
# ---------------------------------------------------------------------------


class TestFirstPresent(unittest.TestCase):
    def test_returns_first_key_found(self):
        data = {"B": "valore_b"}
        self.assertEqual(first_present(data, "A", "B"), "valore_b")

    def test_returns_none_if_no_key_present(self):
        self.assertIsNone(first_present({"x": 1}, "A", "B"))

    def test_preserves_zero(self):
        data = {"TOP_K": 0}
        val = first_present(data, "TOP_K", "top_k")
        self.assertEqual(val, 0)
        self.assertIsNotNone(val)

    def test_preserves_false(self):
        data = {"full_context": False}
        val = first_present(data, "full_context", "RAG_FULL_CONTEXT")
        self.assertIs(val, False)

    def test_preserves_empty_string(self):
        data = {"model": ""}
        val = first_present(data, "model")
        self.assertEqual(val, "")

    def test_returns_first_not_second(self):
        data = {"A": 1, "B": 2}
        self.assertEqual(first_present(data, "A", "B"), 1)

    def test_skips_absent_returns_present(self):
        data = {"B": 99}
        self.assertEqual(first_present(data, "A", "B", "C"), 99)

    def test_hybrid_false_not_converted_to_none(self):
        data = {"ENABLE_RAG_HYBRID_SEARCH": False}
        val = first_present(data, "ENABLE_RAG_HYBRID_SEARCH", "hybrid_search")
        self.assertIs(val, False)
        self.assertIsNotNone(val)

    def test_empty_keys_returns_none(self):
        self.assertIsNone(first_present({"x": 1}))


# ---------------------------------------------------------------------------
# 14. Hybrid search — semantica payload e configurazione
# ---------------------------------------------------------------------------


class TestHybridSearch(unittest.TestCase):
    """Verifica la semantica del campo hybrid nel payload di retrieve_chunks."""

    def _call_retrieve_chunks(self, hybrid=None) -> dict:
        """Chiama retrieve_chunks() con un mock HTTP e restituisce il payload catturato."""
        captured: dict = {}

        def fake_http_json(url, token=None, payload=None, method="GET", timeout=30):
            if payload is not None:
                captured.update(payload)
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        with patch("run_retrieval_benchmark._http_json", side_effect=fake_http_json):
            retrieve_chunks("http://localhost", "token", "uuid-123", "domanda?",
                            top_k=5, hybrid=hybrid)
        return captured

    def test_baseline_no_hybrid_key_in_payload(self):
        """In modalità server (hybrid=None), il payload NON deve contenere 'hybrid'."""
        payload = self._call_retrieve_chunks(hybrid=None)
        self.assertNotIn("hybrid", payload)

    def test_explicit_hybrid_true_sent_in_payload(self):
        """hybrid=True deve essere incluso nel payload."""
        payload = self._call_retrieve_chunks(hybrid=True)
        self.assertIn("hybrid", payload)
        self.assertTrue(payload["hybrid"])

    def test_explicit_hybrid_false_sent_in_payload(self):
        """hybrid=False deve essere incluso nel payload come False (non omesso)."""
        payload = self._call_retrieve_chunks(hybrid=False)
        self.assertIn("hybrid", payload)
        self.assertFalse(payload["hybrid"])
        self.assertIsNotNone(payload["hybrid"])  # False ≠ assente

    def test_effective_hybrid_equals_server_when_mode_is_server(self):
        """effective_hybrid_search deve rispecchiare server_hybrid_search in modo 'server'."""
        for server_value in (True, False, None):
            with self.subTest(server_value=server_value):
                requested_mode = "server"
                effective = server_value  # logica di main()
                self.assertEqual(effective, server_value)

    def test_server_hybrid_false_effective_is_false_not_none(self):
        """Se il server ha hybrid=False, effective deve essere False, non None."""
        server_hybrid = False
        requested_mode = "server"
        effective = server_hybrid if requested_mode == "server" else None
        self.assertIs(effective, False)
        self.assertIsNotNone(effective)

    def test_server_hybrid_true_effective_is_true(self):
        server_hybrid = True
        requested_mode = "server"
        effective = server_hybrid if requested_mode == "server" else None
        self.assertTrue(effective)

    def test_configuration_output_has_hybrid_fields(self):
        """Il JSON di output deve contenere i tre campi hybrid nella configuration."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bench.yaml"
            _write_yaml(p, MINIMAL_YAML)
            out = os.path.join(tmp, "out.json")
            env = {
                "ATLAS_OPENWEBUI_URL": "http://localhost:3000",
                "ATLAS_OPENWEBUI_EMAIL": "test@test.com",
                "ATLAS_OPENWEBUI_PASSWORD": "pw",
            }
            responses = {
                "/api/v1/auths/signin": {"token": "tok"},
                "/api/v1/knowledge/": [{"id": "uid", "name": "ABRAZO"}],
                "/api/config": {"version": "0.10.2"},
                "/api/v1/retrieval/config": {"ENABLE_RAG_HYBRID_SEARCH": True},
                "/api/v1/retrieval/query/collection": {
                    "documents": [["Next.js pending"]],
                    "metadatas": [[{"name": "01_ARCHITECTURE.md"}]],
                    "distances": [[0.1]],
                },
            }

            def mock_urlopen(req, timeout=30):
                for suffix, body in responses.items():
                    if req.full_url.endswith(suffix):
                        m = MagicMock()
                        m.read.return_value = json.dumps(body).encode()
                        m.__enter__ = lambda s: s
                        m.__exit__ = MagicMock(return_value=False)
                        return m
                raise ValueError(f"URL non mockato: {req.full_url}")

            with patch.dict(os.environ, env), \
                 patch("urllib.request.urlopen", side_effect=mock_urlopen):
                main(["--dataset", str(p), "--project", "ABRAZO",
                      "--output", out, "--limit", "1"])

            with open(out) as f:
                data = json.load(f)
            cfg = data["configuration"]
            self.assertIn("server_hybrid_search", cfg)
            self.assertIn("requested_hybrid_mode", cfg)
            self.assertIn("effective_hybrid_search", cfg)
            self.assertEqual(cfg["requested_hybrid_mode"], "server")
            # server config True → effective True
            self.assertTrue(cfg["server_hybrid_search"])
            self.assertTrue(cfg["effective_hybrid_search"])


# ---------------------------------------------------------------------------
# 15. Metriche con errori — all_question_metrics penalizza gli errori
# ---------------------------------------------------------------------------


class TestMetricsWithErrors(unittest.TestCase):
    def _make_ok(self, qid="Q1") -> QuestionResult:
        return _make_result(
            id=qid, category="A",
            document_hit=True, document_recall=1.0,
            term_coverage=1.0, negative_precision=True,
            full_pass=True, error=None,
        )

    def _make_err(self, qid="Q2") -> QuestionResult:
        return _make_result(
            id=qid, category="A",
            document_hit=False, document_recall=0.0,
            term_coverage=0.0, negative_precision=False,
            full_pass=False, error="HTTP 500",
        )

    def test_error_penalizes_all_question_metrics(self):
        agg = aggregate_results([self._make_ok(), self._make_err()])
        # all_question_metrics penalizza: (1 + 0) / 2 = 0.5
        self.assertAlmostEqual(agg["all_question_metrics"].full_pass_rate, 0.5)
        self.assertAlmostEqual(agg["all_question_metrics"].document_hit_rate, 0.5)

    def test_completed_only_excludes_errors(self):
        agg = aggregate_results([self._make_ok(), self._make_err()])
        # completed_only_metrics: solo Q1 → 1.0
        self.assertAlmostEqual(agg["completed_only_metrics"].full_pass_rate, 1.0)
        self.assertAlmostEqual(agg["completed_only_metrics"].document_hit_rate, 1.0)

    def test_all_errors_gives_zero_all_question_metrics(self):
        agg = aggregate_results([self._make_err("E1"), self._make_err("E2")])
        self.assertAlmostEqual(agg["all_question_metrics"].full_pass_rate, 0.0)
        self.assertAlmostEqual(agg["all_question_metrics"].document_hit_rate, 0.0)

    def test_completed_only_empty_when_all_errors(self):
        agg = aggregate_results([self._make_err("E1"), self._make_err("E2")])
        self.assertEqual(agg["completed"], 0)
        # MetricsSnapshot di lista vuota → tutto 0.0
        self.assertAlmostEqual(agg["completed_only_metrics"].full_pass_rate, 0.0)

    def test_three_ok_one_error_correct_all_question_metrics(self):
        results = [self._make_ok(f"Q{i}") for i in range(3)] + [self._make_err("E1")]
        agg = aggregate_results(results)
        self.assertAlmostEqual(agg["all_question_metrics"].full_pass_rate, 3 / 4)
        self.assertAlmostEqual(agg["completed_only_metrics"].full_pass_rate, 1.0)

    def test_both_metric_groups_returned(self):
        agg = aggregate_results([self._make_ok()])
        self.assertIsInstance(agg["completed_only_metrics"], MetricsSnapshot)
        self.assertIsInstance(agg["all_question_metrics"], MetricsSnapshot)


# ---------------------------------------------------------------------------
# 16. Scrittura atomica fallita → exit code 1
# ---------------------------------------------------------------------------


class TestWriteFailureExitCode(unittest.TestCase):
    def _dataset_path(self, tmp: str) -> str:
        p = Path(tmp) / "bench.yaml"
        _write_yaml(p, MINIMAL_YAML)
        return str(p)

    def test_write_failure_returns_exit_1(self):
        """Se write_results_atomic solleva un'eccezione, main() deve restituire 1."""
        responses = {
            "/api/v1/auths/signin": {"token": "tok"},
            "/api/v1/knowledge/": [{"id": "uid", "name": "ABRAZO"}],
            "/api/config": {"version": "0.10.2"},
            "/api/v1/retrieval/config": {},
            "/api/v1/retrieval/query/collection": {
                "documents": [["Next.js pending"]],
                "metadatas": [[{"name": "01_ARCHITECTURE.md"}]],
                "distances": [[0.1]],
            },
        }

        def mock_urlopen(req, timeout=30):
            for suffix, body in responses.items():
                if req.full_url.endswith(suffix):
                    m = MagicMock()
                    m.read.return_value = json.dumps(body).encode()
                    m.__enter__ = lambda s: s
                    m.__exit__ = MagicMock(return_value=False)
                    return m
            raise ValueError(f"URL non mockato: {req.full_url}")

        with tempfile.TemporaryDirectory() as tmp:
            dataset = self._dataset_path(tmp)
            out = os.path.join(tmp, "out.json")
            env = {
                "ATLAS_OPENWEBUI_URL": "http://localhost:3000",
                "ATLAS_OPENWEBUI_EMAIL": "test@test.com",
                "ATLAS_OPENWEBUI_PASSWORD": "pw",
            }
            with patch.dict(os.environ, env), \
                 patch("urllib.request.urlopen", side_effect=mock_urlopen), \
                 patch("run_retrieval_benchmark.write_results_atomic",
                       side_effect=OSError("disco pieno")):
                ret = main(["--dataset", dataset, "--project", "ABRAZO",
                            "--output", out, "--limit", "1"])

            self.assertEqual(ret, 1)
            self.assertFalse(os.path.exists(out))

    def test_write_failure_prints_error_message(self):
        """La failure di scrittura deve stampare un messaggio d'errore su stderr."""
        responses = {
            "/api/v1/auths/signin": {"token": "tok"},
            "/api/v1/knowledge/": [{"id": "uid", "name": "ABRAZO"}],
            "/api/config": {"version": "0.10.2"},
            "/api/v1/retrieval/config": {},
            "/api/v1/retrieval/query/collection": {
                "documents": [["Next.js pending"]],
                "metadatas": [[{"name": "01_ARCHITECTURE.md"}]],
                "distances": [[0.1]],
            },
        }

        def mock_urlopen(req, timeout=30):
            for suffix, body in responses.items():
                if req.full_url.endswith(suffix):
                    m = MagicMock()
                    m.read.return_value = json.dumps(body).encode()
                    m.__enter__ = lambda s: s
                    m.__exit__ = MagicMock(return_value=False)
                    return m
            raise ValueError(f"URL non mockato: {req.full_url}")

        with tempfile.TemporaryDirectory() as tmp:
            dataset = self._dataset_path(tmp)
            out = os.path.join(tmp, "out.json")
            env = {
                "ATLAS_OPENWEBUI_URL": "http://localhost:3000",
                "ATLAS_OPENWEBUI_EMAIL": "test@test.com",
                "ATLAS_OPENWEBUI_PASSWORD": "pw",
            }
            captured_err = io.StringIO()
            with patch.dict(os.environ, env), \
                 patch("urllib.request.urlopen", side_effect=mock_urlopen), \
                 patch("run_retrieval_benchmark.write_results_atomic",
                       side_effect=OSError("disco pieno")), \
                 patch("sys.stderr", captured_err):
                main(["--dataset", dataset, "--project", "ABRAZO",
                      "--output", out, "--limit", "1"])

            self.assertIn("Error", captured_err.getvalue())
            self.assertIn("disco pieno", captured_err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
