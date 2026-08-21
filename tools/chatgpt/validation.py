"""
M4.1 — ACNF validation layer.

Computes structural metrics from a normalization result and, optionally,
compares them against a known expected baseline (e.g. CHATGPT-ACQ-001).
Generic validation never depends on baseline-specific numbers — baseline
comparison is opt-in, selected explicitly by the caller.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ASSET_STORAGE_KIND_REFERENCE_ONLY

# Known baseline for the real export CHATGPT-ACQ-001 (see
# docs/M4.1_CHATGPT_LOSSLESS_NORMALIZER.md, sections 3 and 10). Used only
# when explicitly requested via --expected-baseline; never applied by
# default, and never referenced by the generic validation/metrics logic.
# logical_assets / reference_only_assets were added after the RC1
# real-data run identified 122 sediment:// reference-only assets with no
# physical .dat payload — see the doc's "Asset storage classes" section.
EXPECTED_BASELINES: Dict[str, Dict[str, int]] = {
    "chatgpt-acq-001": {
        "conversations": 777,
        "nodes": 33642,
        "messages": 32865,
        "technical_roots": 777,
        "conversations_with_branches": 65,
        "branching_parents": 75,
        "off_current_path_nodes": 186,
        "conversation_asset_mappings": 6146,
        "physical_dat_assets": 6242,
        "library_files_records": 2136,
        "logical_assets": 6364,
        "reference_only_assets": 122,
    },
}


@dataclass
class ValidationReport:
    metrics: Dict[str, int]
    anomalies: List[Dict[str, Any]]
    expected_baseline_name: Optional[str]
    expected: Optional[Dict[str, int]]
    gate_results: List[Dict[str, Any]]
    passed: bool
    validated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": self.metrics,
            "anomalies": self.anomalies,
            "expected_baseline_name": self.expected_baseline_name,
            "expected_baseline": self.expected,
            "gate_results": self.gate_results,
            "passed": self.passed,
            "validated_at": self.validated_at,
        }


def compute_metrics(result: Any) -> Dict[str, int]:
    """
    Compute structural metrics from a NormalizationResult. Independent of
    any specific expected baseline.
    """
    conversations = result.conversations
    nodes = result.nodes

    # node_id is only unique within a conversation, not globally, so the
    # parent key must be scoped by conversation_id to avoid conflating
    # same-named nodes (e.g. "root") across different conversations.
    children_by_parent: Dict[tuple, set] = {}
    for node in nodes:
        if node.parent_id is not None:
            key = (node.conversation_id, node.parent_id)
            children_by_parent.setdefault(key, set()).add(node.node_id)

    branching_parents = sum(1 for children in children_by_parent.values() if len(children) > 1)
    conversations_with_branches = sum(1 for c in conversations if c.has_branches)
    technical_roots = sum(1 for n in nodes if n.is_technical_root)
    # A "message" is any node whose raw mapping entry carried a message
    # object, even a malformed one missing its own id — matching how
    # ConversationRecord.message_count and NodeRecord.has_message are
    # populated during normalization. This must stay in sync with those,
    # not re-derived from message_id, which a malformed message may lack.
    messages = sum(1 for n in nodes if n.has_message)
    off_current_path_nodes = sum(1 for n in nodes if not n.is_current_path)

    # Generic, dataset-independent: total distinct logical assets
    # (whatever their storage_kind) vs. those observed with no physical
    # export payload (see models.ASSET_STORAGE_KIND_REFERENCE_ONLY / the
    # RC1 sediment:// finding).
    logical_assets = len(result.assets)
    reference_only_assets = sum(1 for a in result.assets if a.storage_kind == ASSET_STORAGE_KIND_REFERENCE_ONLY)

    return {
        "conversations": len(conversations),
        "nodes": len(nodes),
        "messages": messages,
        "technical_roots": technical_roots,
        "conversations_with_branches": conversations_with_branches,
        "branching_parents": branching_parents,
        "off_current_path_nodes": off_current_path_nodes,
        "conversation_asset_mappings": result.conversation_asset_file_names_count,
        "physical_dat_assets": result.physical_dat_asset_count,
        "library_files_records": len(result.library_files),
        "logical_assets": logical_assets,
        "reference_only_assets": reference_only_assets,
    }


def validate(
    result: Any,
    expected: Optional[Dict[str, int]] = None,
    expected_baseline_name: Optional[str] = None,
) -> ValidationReport:
    """
    Build a ValidationReport from a NormalizationResult.

    Validation fails if any structural anomaly was recorded during
    normalization, or if any provided expected-baseline gate diverges.
    """
    metrics = compute_metrics(result)
    gate_results: List[Dict[str, Any]] = []
    passed = True

    if expected is not None:
        for key in expected:
            actual = metrics.get(key)
            ok = actual == expected[key]
            if not ok:
                passed = False
            gate_results.append({"metric": key, "expected": expected[key], "actual": actual, "passed": ok})

    anomaly_dicts = [a.to_dict() for a in result.anomalies]
    if anomaly_dicts:
        passed = False

    return ValidationReport(
        metrics=metrics,
        anomalies=anomaly_dicts,
        expected_baseline_name=expected_baseline_name,
        expected=expected,
        gate_results=gate_results,
        passed=passed,
        validated_at=datetime.now(timezone.utc).isoformat(),
    )


def write_validation_json(report: ValidationReport, output_dir: Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "validation.json", "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, sort_keys=True, ensure_ascii=False, indent=2)
        f.write("\n")
