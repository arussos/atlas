"""
M4.2a RC2 — Tests for tools/episodes/boundary_candidates.py

Covers spec section 13 (C. count invariant with intermediate nodes, D.
empty visible text, F. role transitions, G. time gap, H. determinism,
I. version), section 14 (strengthened no-cross-conversation test), plus
integration-level checks (reasons content, marker/lexical wiring,
intermediate provenance on BoundaryCandidate).
"""

import json

from tests.episodes.fixtures import chain_conversation, linear_conversation, make_conversation, make_node
from tools.episodes.boundary_candidates import generate_boundary_candidates, write_output
from tools.episodes.models import FEATURE_VERSION


# ---------------------------------------------------------------------------
# C. Candidate count invariant (against visible dialogue messages)
# ---------------------------------------------------------------------------


def test_zero_messages_yields_zero_candidates():
    fixture = linear_conversation("conv-0", 0)
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates(
        [fixture["conversation"]], fixture["nodes"]
    )
    assert current_path["conv-0"] == 0
    assert visible["conv-0"] == 0
    assert len(candidates) == 0


def test_one_message_yields_zero_candidates():
    fixture = linear_conversation("conv-1", 1)
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates(
        [fixture["conversation"]], fixture["nodes"]
    )
    assert visible["conv-1"] == 1
    assert len(candidates) == 0


def test_two_messages_yields_one_candidate():
    fixture = linear_conversation("conv-2", 2)
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates(
        [fixture["conversation"]], fixture["nodes"]
    )
    assert visible["conv-2"] == 2
    assert len(candidates) == 1


def test_five_messages_yields_four_candidates():
    fixture = linear_conversation("conv-5", 5)
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates(
        [fixture["conversation"]], fixture["nodes"]
    )
    assert visible["conv-5"] == 5
    assert len(candidates) == 4
    assert [c.sequence_index for c in candidates] == [0, 1, 2, 3]


def test_count_invariant_holds_with_intermediate_non_visible_nodes():
    # A(text) -> X(thoughts) -> Y(reasoning_recap) -> B(text) -> C(text)
    # current_path_message_nodes = 5, visible_dialogue_messages = 3,
    # candidates == max(3 - 1, 0) == 2 (A->B, B->C), never A->X, X->Y, Y->B.
    fixture = chain_conversation(
        "conv-mixed",
        [
            dict(role="user", content_type="text", text_parts=["A"]),
            dict(role="assistant", content_type="thoughts", text_parts=["X"]),
            dict(role="assistant", content_type="reasoning_recap", text_parts=["Y"]),
            dict(role="assistant", content_type="text", text_parts=["B"]),
            dict(role="user", content_type="text", text_parts=["C"]),
        ],
    )
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates(
        [fixture["conversation"]], fixture["nodes"]
    )
    assert current_path["conv-mixed"] == 5
    assert visible["conv-mixed"] == 3
    assert len(candidates) == 2
    assert [(c.before_node_id, c.after_node_id) for c in candidates] == [("n1", "n4"), ("n4", "n5")]


def test_no_candidate_crosses_conversation_boundary():
    fixture_a = linear_conversation("conv-a", 3)
    fixture_b = linear_conversation("conv-b", 3)
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates(
        [fixture_a["conversation"], fixture_b["conversation"]],
        fixture_a["nodes"] + fixture_b["nodes"],
    )
    assert len(candidates) == 4  # 2 per conversation
    for c in candidates:
        assert c.conversation_id in {"conv-a", "conv-b"}
    conv_a_candidates = [c for c in candidates if c.conversation_id == "conv-a"]
    conv_b_candidates = [c for c in candidates if c.conversation_id == "conv-b"]
    assert len(conv_a_candidates) == 2
    assert len(conv_b_candidates) == 2


def test_no_candidate_crosses_conversation_boundary_endpoint_membership():
    """
    Spec section 14: verify actual endpoint membership, not only
    candidate.conversation_id counts. Uses distinct node id sets per
    conversation so a candidate leaking a before/after node from the
    wrong conversation would be caught.
    """
    fixture_a = chain_conversation(
        "conv-a",
        [
            dict(node_id="a1", role="user", content_type="text", text_parts=["A1"]),
            dict(node_id="a2", role="assistant", content_type="text", text_parts=["A2"]),
            dict(node_id="a3", role="user", content_type="text", text_parts=["A3"]),
        ],
    )
    fixture_b = chain_conversation(
        "conv-b",
        [
            dict(node_id="b1", role="user", content_type="text", text_parts=["B1"]),
            dict(node_id="b2", role="assistant", content_type="text", text_parts=["B2"]),
            dict(node_id="b3", role="user", content_type="text", text_parts=["B3"]),
        ],
    )
    candidates, _, _, _, _ = generate_boundary_candidates(
        [fixture_a["conversation"], fixture_b["conversation"]],
        fixture_a["nodes"] + fixture_b["nodes"],
    )
    expected_nodes = {"conv-a": {"a1", "a2", "a3"}, "conv-b": {"b1", "b2", "b3"}}
    assert len(candidates) == 4
    for c in candidates:
        own = expected_nodes[c.conversation_id]
        other = expected_nodes["conv-b" if c.conversation_id == "conv-a" else "conv-a"]
        assert c.before_node_id in own
        assert c.after_node_id in own
        assert c.before_node_id not in other
        assert c.after_node_id not in other


# ---------------------------------------------------------------------------
# B. Intermediate provenance on BoundaryCandidate
# ---------------------------------------------------------------------------


def test_intermediate_provenance_on_candidate():
    fixture = chain_conversation(
        "conv-prov",
        [
            dict(role="user", content_type="text", text_parts=["A"]),
            dict(role="assistant", content_type="thoughts", text_parts=["X"]),
            dict(role="assistant", content_type="reasoning_recap", text_parts=["Y"]),
            dict(role="assistant", content_type="text", text_parts=["B"]),
        ],
    )
    candidates, _, _, _, _ = generate_boundary_candidates([fixture["conversation"]], fixture["nodes"])
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.before_node_id == "n1"
    assert candidate.after_node_id == "n4"
    assert candidate.intermediate_node_count == 2
    assert candidate.intermediate_node_ids == ["n2", "n3"]
    assert candidate.intermediate_content_types == ["thoughts", "reasoning_recap"]


def test_directly_adjacent_visible_nodes_have_zero_intermediate_nodes():
    fixture = linear_conversation("conv-adjacent", 2)
    candidates, _, _, _, _ = generate_boundary_candidates([fixture["conversation"]], fixture["nodes"])
    assert len(candidates) == 1
    assert candidates[0].intermediate_node_count == 0
    assert candidates[0].intermediate_node_ids == []
    assert candidates[0].intermediate_content_types == []


# ---------------------------------------------------------------------------
# D. Empty visible text is still a visible dialogue node
# ---------------------------------------------------------------------------


def test_empty_text_node_still_participates_as_a_boundary_vertex():
    fixture = chain_conversation(
        "conv-empty",
        [
            dict(role="user", content_type="text", text_parts=["A"]),
            dict(role="assistant", content_type="text", text_parts=[]),
            dict(role="user", content_type="text", text_parts=["C"]),
        ],
    )
    candidates, anomalies, current_path, visible, cands = generate_boundary_candidates(
        [fixture["conversation"]], fixture["nodes"]
    )
    assert visible["conv-empty"] == 3
    assert len(candidates) == 2
    assert [(c.before_node_id, c.after_node_id) for c in candidates] == [("n1", "n2"), ("n2", "n3")]


# ---------------------------------------------------------------------------
# F. Role transitions — no artificial assistant->assistant candidates
# ---------------------------------------------------------------------------


def test_no_artificial_assistant_to_assistant_transition_from_thoughts():
    fixture = chain_conversation(
        "conv-roles",
        [
            dict(role="user", content_type="text", text_parts=["A"]),
            dict(role="assistant", content_type="thoughts", text_parts=["X"]),
            dict(role="assistant", content_type="reasoning_recap", text_parts=["Y"]),
            dict(role="assistant", content_type="text", text_parts=["B"]),
        ],
    )
    candidates, _, _, _, _ = generate_boundary_candidates([fixture["conversation"]], fixture["nodes"])
    assert len(candidates) == 1
    assert candidates[0].before_role == "user"
    assert candidates[0].after_role == "assistant"


# ---------------------------------------------------------------------------
# G. Time gap uses visible endpoints, not skipped intermediate nodes
# ---------------------------------------------------------------------------


def test_time_gap_uses_visible_endpoint_timestamps_not_intermediate_nodes():
    fixture = chain_conversation(
        "conv-timegap",
        [
            dict(role="user", content_type="text", text_parts=["A"], created_at=0.0),
            # intermediate node with a wildly different timestamp — must
            # not influence the computed gap.
            dict(role="assistant", content_type="thoughts", text_parts=["X"], created_at=999999.0),
            dict(role="assistant", content_type="text", text_parts=["B"], created_at=100.0),
        ],
    )
    candidates, _, _, _, _ = generate_boundary_candidates([fixture["conversation"]], fixture["nodes"])
    assert len(candidates) == 1
    assert candidates[0].time_gap_seconds == 100.0


# ---------------------------------------------------------------------------
# H. Determinism
# ---------------------------------------------------------------------------


def test_same_input_produces_identical_candidate_ids_and_hashes():
    fixture = linear_conversation("conv-det", 4)
    run1, _, _, _, _ = generate_boundary_candidates([fixture["conversation"]], fixture["nodes"])
    run2, _, _, _, _ = generate_boundary_candidates([fixture["conversation"]], fixture["nodes"])

    ids1 = [c.candidate_id for c in run1]
    ids2 = [c.candidate_id for c in run2]
    hashes1 = [c.candidate_hash for c in run1]
    hashes2 = [c.candidate_hash for c in run2]

    assert ids1 == ids2
    assert hashes1 == hashes2
    assert len(set(ids1)) == len(ids1)  # ids are unique per pair


def test_byte_identical_jsonl_across_two_runs(tmp_path):
    fixture = linear_conversation("conv-byte", 6)

    candidates1, _, _, _, _ = generate_boundary_candidates([fixture["conversation"]], fixture["nodes"])
    candidates2, _, _, _, _ = generate_boundary_candidates([fixture["conversation"]], fixture["nodes"])

    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    write_output(candidates1, out1)
    write_output(candidates2, out2)

    bytes1 = (out1 / "boundary_candidates.jsonl").read_bytes()
    bytes2 = (out2 / "boundary_candidates.jsonl").read_bytes()
    assert bytes1 == bytes2


def test_candidate_id_is_not_a_random_uuid():
    fixture = linear_conversation("conv-stable", 2)
    candidates, _, _, _, _ = generate_boundary_candidates([fixture["conversation"]], fixture["nodes"])
    candidate = candidates[0]
    # sha256 hex digest: 64 lowercase hex chars, not a UUID4 (which has dashes)
    assert len(candidate.candidate_id) == 64
    assert "-" not in candidate.candidate_id
    assert all(ch in "0123456789abcdef" for ch in candidate.candidate_id)


# ---------------------------------------------------------------------------
# I. Version — RC2 semantics identity separate from RC1
# ---------------------------------------------------------------------------


def test_feature_version_changed_from_rc1():
    assert FEATURE_VERSION != "m4.2a-0.1"
    assert FEATURE_VERSION == "m4.2a-0.2"


# ---------------------------------------------------------------------------
# Integration: reasons / markers / lexical wiring
# ---------------------------------------------------------------------------


def test_reasons_do_not_contain_full_message_text():
    conversation = make_conversation("conv-r", "n2")
    nodes = [
        make_node("conv-r", "root", None, has_message=False, is_technical_root=True, content_type=None),
        make_node("conv-r", "n1", "root", role="user", created_at=1.0, text_parts=["ora funziona, risolto tutto"]),
        make_node("conv-r", "n2", "n1", role="assistant", created_at=2.0, text_parts=["ora passiamo al prossimo problema"]),
    ]
    candidates, _, _, _, _ = generate_boundary_candidates([conversation], nodes)
    assert len(candidates) == 1
    candidate = candidates[0]
    reasons_blob = " ".join(candidate.reasons)
    assert "prossimo problema" not in reasons_blob
    assert any(r.startswith("closure_marker=") for r in candidate.reasons)
    assert any(r.startswith("opening_marker=") for r in candidate.reasons)
    assert candidate.feature_version == FEATURE_VERSION


def test_candidate_serializes_to_json_cleanly():
    fixture = linear_conversation("conv-json", 3)
    candidates, _, _, _, _ = generate_boundary_candidates([fixture["conversation"]], fixture["nodes"])
    for candidate in candidates:
        # must not raise, and round-trip must preserve candidate_id
        blob = json.dumps(candidate.to_dict(), sort_keys=True, ensure_ascii=False)
        restored = json.loads(blob)
        assert restored["candidate_id"] == candidate.candidate_id
        assert "intermediate_node_ids" in restored
        assert "intermediate_content_types" in restored
        assert "intermediate_node_count" in restored
