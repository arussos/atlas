"""
M5.1 — Tests for the CLI / JSONL output (spec section 14: Q byte-equivalent
determinism; spec section 12: output ordering and single output format).
"""

import json

from tests.episodes.fixtures import linear_conversation
from tools.retrieval_units.projection import generate_retrieval_units, main, write_output


def _write_acnf_dir(tmp_path, name, fixtures, acquisition_id="acq-cli-001"):
    acnf_dir = tmp_path / name
    acnf_dir.mkdir()
    acquisition = {
        "acquisition_id": acquisition_id,
        "source_filename": "export.zip",
        "source_sha256": "0" * 64,
        "normalized_schema_version": "0.1",
        "export_metadata": {},
        "normalized_at": "2026-08-28T00:00:00Z",
    }
    (acnf_dir / "acquisition.json").write_text(
        json.dumps(acquisition, sort_keys=True, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with open(acnf_dir / "conversations.jsonl", "w", encoding="utf-8") as f:
        for fixture in fixtures:
            f.write(json.dumps(fixture["conversation"], sort_keys=True, ensure_ascii=False) + "\n")
    with open(acnf_dir / "nodes.jsonl", "w", encoding="utf-8") as f:
        for fixture in fixtures:
            for node in fixture["nodes"]:
                f.write(json.dumps(node, sort_keys=True, ensure_ascii=False) + "\n")
    return acnf_dir


def test_cli_writes_retrieval_units_jsonl(tmp_path, capsys):
    fixtures = [linear_conversation("conv-1", 9), linear_conversation("conv-2", 3)]
    acnf_dir = _write_acnf_dir(tmp_path, "acnf", fixtures)
    out_dir = tmp_path / "out"

    exit_code = main([str(acnf_dir), str(out_dir)])
    assert exit_code == 0

    lines = (out_dir / "retrieval_units.jsonl").read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert len(records) == 3  # conv-1: 2 units, conv-2: 1 unit
    assert [r["conversation_id"] for r in records] == ["conv-1", "conv-1", "conv-2"]
    assert records[0]["acquisition_id"] == "acq-cli-001"
    assert records[0]["acnf_schema_version"] == "0.1"
    # No parallel output formats: the CLI writes exactly one file.
    assert [p.name for p in sorted(out_dir.iterdir())] == ["retrieval_units.jsonl"]

    out = capsys.readouterr().out
    assert "retrieval units" in out


def test_same_input_produces_byte_equivalent_output(tmp_path):
    fixtures = [linear_conversation("conv-1", 14), linear_conversation("conv-2", 7)]
    acnf_dir = _write_acnf_dir(tmp_path, "acnf", fixtures)

    out_1 = tmp_path / "out1"
    out_2 = tmp_path / "out2"
    assert main([str(acnf_dir), str(out_1)]) == 0
    assert main([str(acnf_dir), str(out_2)]) == 0

    bytes_1 = (out_1 / "retrieval_units.jsonl").read_bytes()
    bytes_2 = (out_2 / "retrieval_units.jsonl").read_bytes()
    assert bytes_1 == bytes_2
    assert len(bytes_1) > 0


def test_units_are_ordered_by_ordinal_start_within_conversation(tmp_path):
    fixture = linear_conversation("conv-1", 14)
    units, _, _, _ = generate_retrieval_units(
        [fixture["conversation"]], fixture["nodes"], acquisition_id="a", acnf_schema_version="0.1"
    )
    write_output(units, tmp_path)
    records = [
        json.loads(line)
        for line in (tmp_path / "retrieval_units.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [r["ordinal_start"] for r in records] == [0, 3, 6, 9]


def test_serialized_record_contains_full_contract(tmp_path):
    fixture = linear_conversation("conv-1", 2)
    units, _, _, _ = generate_retrieval_units(
        [fixture["conversation"]], fixture["nodes"], acquisition_id="a", acnf_schema_version="0.1"
    )
    write_output(units, tmp_path)
    record = json.loads((tmp_path / "retrieval_units.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert set(record.keys()) == {
        "retrieval_unit_id",
        "projection_version",
        "source_type",
        "acquisition_id",
        "acnf_schema_version",
        "conversation_id",
        "source_id",
        "conversation_title",
        "source_conversation_hash",
        "node_ids",
        "first_node_id",
        "last_node_id",
        "ordinal_start",
        "ordinal_end",
        "message_count",
        "start_timestamp",
        "end_timestamp",
        "intermediate_node_ids",
        "text",
        "content_hash",
    }
    assert record["source_type"] == "chatgpt"
