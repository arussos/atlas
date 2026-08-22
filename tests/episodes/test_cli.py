"""
M4.2a — End-to-end CLI test for tools/episodes/boundary_candidates.py.

Writes synthetic conversations.jsonl/nodes.jsonl to a temp ACNF dir (as
M4.1 would produce them), runs the CLI main(), and checks the outputs.
"""

import json

from tests.episodes.fixtures import linear_conversation
from tools.episodes.boundary_candidates import main


def _write_acnf_dir(tmp_path, fixtures):
    acnf_dir = tmp_path / "acnf"
    acnf_dir.mkdir()
    conversations = [f["conversation"] for f in fixtures]
    nodes = [n for f in fixtures for n in f["nodes"]]
    with open(acnf_dir / "conversations.jsonl", "w", encoding="utf-8") as f:
        for c in conversations:
            f.write(json.dumps(c) + "\n")
    with open(acnf_dir / "nodes.jsonl", "w", encoding="utf-8") as f:
        for n in nodes:
            f.write(json.dumps(n) + "\n")
    return acnf_dir


def test_cli_end_to_end_writes_expected_outputs(tmp_path):
    fixtures = [linear_conversation("conv-1", 3), linear_conversation("conv-2", 5)]
    acnf_dir = _write_acnf_dir(tmp_path, fixtures)
    output_dir = tmp_path / "out"

    exit_code = main([str(acnf_dir), str(output_dir)])

    assert exit_code == 0
    assert (output_dir / "boundary_candidates.jsonl").exists()
    assert (output_dir / "boundary_validation.json").exists()

    lines = (output_dir / "boundary_candidates.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2 + 4  # (3-1) + (5-1)

    validation = json.loads((output_dir / "boundary_validation.json").read_text(encoding="utf-8"))
    assert validation["passed"] is True
    assert validation["metrics"]["candidates"] == 6
    assert validation["metrics"]["conversations_processed"] == 2


def test_cli_two_runs_produce_byte_identical_jsonl(tmp_path):
    fixtures = [linear_conversation("conv-1", 4)]
    acnf_dir = _write_acnf_dir(tmp_path, fixtures)

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    main([str(acnf_dir), str(out1)])
    main([str(acnf_dir), str(out2)])

    assert (out1 / "boundary_candidates.jsonl").read_bytes() == (out2 / "boundary_candidates.jsonl").read_bytes()
