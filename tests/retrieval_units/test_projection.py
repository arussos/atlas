"""
M5.1 — Tests for generate_retrieval_units (spec section 14: A–N plus
graph-order authority, visibility-policy reuse, intermediate-node
provenance, and cross-conversation isolation).

All fixtures are synthetic and reuse the shared ACNF JSONL-shape
builders from tests/episodes/fixtures.py — same shape M4.2a consumes.
"""

from tests.episodes.fixtures import chain_conversation, linear_conversation, make_conversation, make_node
from tools.retrieval_units.models import PROJECTION_VERSION, SOURCE_TYPE_CHATGPT
from tools.retrieval_units.projection import generate_retrieval_units

ACQUISITION_ID = "acq-test-001"
ACNF_SCHEMA_VERSION = "0.1"


def generate(conversations, nodes):
    return generate_retrieval_units(
        conversations,
        nodes,
        acquisition_id=ACQUISITION_ID,
        acnf_schema_version=ACNF_SCHEMA_VERSION,
    )


# ---------------------------------------------------------------------------
# A–F. Unit counts and window spans
# ---------------------------------------------------------------------------


def test_zero_visible_nodes_yields_zero_units():
    fixture = linear_conversation("conv-a", 0)
    units, _, visible, per_conv = generate([fixture["conversation"]], fixture["nodes"])
    assert units == []
    assert visible["conv-a"] == 0
    assert per_conv["conv-a"] == 0


def test_only_technical_nodes_yields_zero_units():
    # Current path exists but no node is a visible dialogue node.
    fixture = chain_conversation(
        "conv-a2",
        [
            {"role": "assistant", "content_type": "thoughts", "content": {"content_type": "thoughts"}},
            {"role": "assistant", "content_type": "reasoning_recap", "content": {"content_type": "reasoning_recap"}},
        ],
    )
    units, _, visible, per_conv = generate([fixture["conversation"]], fixture["nodes"])
    assert units == []
    assert visible["conv-a2"] == 0
    assert per_conv["conv-a2"] == 0


def test_one_visible_node_yields_one_unit():
    fixture = linear_conversation("conv-b", 1)
    units, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert len(units) == 1
    assert units[0].node_ids == ["n1"]
    assert units[0].ordinal_start == 0
    assert units[0].ordinal_end == 0
    assert units[0].message_count == 1


def test_fewer_than_six_visible_nodes_yields_one_unit_with_all():
    fixture = linear_conversation("conv-c", 5)
    units, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert len(units) == 1
    assert units[0].node_ids == ["n1", "n2", "n3", "n4", "n5"]


def test_exactly_six_yields_one_unit():
    fixture = linear_conversation("conv-d", 6)
    units, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert len(units) == 1
    assert units[0].node_ids == [f"n{i}" for i in range(1, 7)]


def test_nine_visible_nodes_yields_windows_1_6_and_4_9():
    fixture = linear_conversation("conv-e", 9)
    units, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert len(units) == 2
    assert units[0].node_ids == [f"n{i}" for i in range(1, 7)]
    assert units[1].node_ids == [f"n{i}" for i in range(4, 10)]
    assert (units[0].ordinal_start, units[0].ordinal_end) == (0, 5)
    assert (units[1].ordinal_start, units[1].ordinal_end) == (3, 8)


def test_fourteen_visible_nodes_yields_four_units_with_short_tail():
    fixture = linear_conversation("conv-f", 14)
    units, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert [unit.node_ids for unit in units] == [
        [f"n{i}" for i in range(1, 7)],
        [f"n{i}" for i in range(4, 10)],
        [f"n{i}" for i in range(7, 13)],
        [f"n{i}" for i in range(10, 15)],
    ]
    assert units[-1].message_count == 5
    assert (units[-1].ordinal_start, units[-1].ordinal_end) == (9, 13)


# ---------------------------------------------------------------------------
# G. Coverage
# ---------------------------------------------------------------------------


def test_every_visible_node_appears_in_at_least_one_unit():
    for count in (1, 5, 6, 7, 9, 14, 20):
        fixture = linear_conversation(f"conv-g{count}", count)
        units, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
        covered = set()
        for unit in units:
            covered.update(unit.node_ids)
        assert covered == {f"n{i}" for i in range(1, count + 1)}


# ---------------------------------------------------------------------------
# H. Hidden/technical nodes never leak into text; visibility policy reused
# ---------------------------------------------------------------------------


def test_technical_node_text_never_appears_in_unit_text():
    fixture = chain_conversation(
        "conv-h",
        [
            {"role": "user", "text_parts": ["visible question"]},
            {
                "role": "assistant",
                "content_type": "thoughts",
                "content": {"content_type": "thoughts", "thoughts": [{"content": "SECRET-REASONING"}]},
            },
            {"role": "assistant", "text_parts": ["visible answer"]},
        ],
    )
    units, _, visible, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert visible["conv-h"] == 2
    assert len(units) == 1
    assert "SECRET-REASONING" not in units[0].text
    assert "visible question" in units[0].text
    assert "visible answer" in units[0].text
    # The skipped technical node is preserved as ordered id-only provenance.
    assert units[0].intermediate_node_ids == ["n2"]
    assert units[0].node_ids == ["n1", "n3"]


def test_unknown_content_types_are_excluded_per_existing_policy():
    fixture = chain_conversation(
        "conv-h2",
        [
            {"role": "user", "text_parts": ["one"]},
            {
                "role": "assistant",
                "content_type": "some_future_type",
                "content": {"content_type": "some_future_type", "parts": ["FUTURE-CONTENT"]},
            },
            {"role": "assistant", "text_parts": ["two"]},
        ],
    )
    units, _, visible, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert visible["conv-h2"] == 2
    assert len(units) == 1
    assert units[0].node_ids == ["n1", "n3"]
    assert "FUTURE-CONTENT" not in units[0].text


# ---------------------------------------------------------------------------
# I. Graph order is authoritative — timestamps never determine order
# ---------------------------------------------------------------------------


def test_visible_node_order_follows_graph_order_not_timestamps():
    # Descending timestamps: a created_at sort would reverse the graph order.
    fixture = chain_conversation(
        "conv-i",
        [
            {"role": "user", "text_parts": ["first"], "created_at": 100.0},
            {"role": "assistant", "text_parts": ["second"], "created_at": 50.0},
            {"role": "user", "text_parts": ["third"], "created_at": 10.0},
        ],
    )
    units, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert len(units) == 1
    assert units[0].node_ids == ["n1", "n2", "n3"]
    assert units[0].text.index("first") < units[0].text.index("second") < units[0].text.index("third")
    # Timestamps are features, not an order source: they are copied as-is.
    assert units[0].start_timestamp == 100.0
    assert units[0].end_timestamp == 10.0


# ---------------------------------------------------------------------------
# J. Role markers
# ---------------------------------------------------------------------------


def test_role_markers_are_preserved_in_order():
    fixture = chain_conversation(
        "conv-j",
        [
            {"role": "user", "text_parts": ["question"]},
            {"role": "assistant", "text_parts": ["answer"]},
        ],
    )
    units, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert units[0].text == "[user]\nquestion\n\n[assistant]\nanswer"


# ---------------------------------------------------------------------------
# K. Missing timestamps remain None — never synthesized
# ---------------------------------------------------------------------------


def test_missing_timestamps_remain_none():
    fixture = chain_conversation(
        "conv-k",
        [
            {"role": "user", "text_parts": ["a"], "created_at": None},
            {"role": "assistant", "text_parts": ["b"], "created_at": None},
        ],
    )
    units, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert units[0].start_timestamp is None
    assert units[0].end_timestamp is None


# ---------------------------------------------------------------------------
# L. node_ids / first_node_id / last_node_id are exact
# ---------------------------------------------------------------------------


def test_node_id_fields_are_exact():
    fixture = linear_conversation("conv-l", 9)
    units, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    for unit in units:
        assert unit.first_node_id == unit.node_ids[0]
        assert unit.last_node_id == unit.node_ids[-1]
        assert unit.message_count == len(unit.node_ids)
        assert unit.ordinal_end - unit.ordinal_start + 1 == unit.message_count


# ---------------------------------------------------------------------------
# M–N. Provenance
# ---------------------------------------------------------------------------


def test_acquisition_and_schema_provenance_are_preserved():
    fixture = linear_conversation("conv-m", 3)
    units, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert units[0].acquisition_id == ACQUISITION_ID
    assert units[0].acnf_schema_version == ACNF_SCHEMA_VERSION
    assert units[0].source_type == SOURCE_TYPE_CHATGPT
    assert units[0].projection_version == PROJECTION_VERSION


def test_conversation_provenance_is_exact():
    fixture = linear_conversation("conv-n", 3)
    conversation = dict(fixture["conversation"])
    conversation["source_id"] = "src-42"
    conversation["title"] = "Il titolo"
    conversation["conversation_hash"] = "deadbeef"
    units, _, _, _ = generate([conversation], fixture["nodes"])
    assert units[0].conversation_id == "conv-n"
    assert units[0].source_id == "src-42"
    assert units[0].conversation_title == "Il titolo"
    assert units[0].source_conversation_hash == "deadbeef"
    # The title stays metadata — never injected into the embedded text.
    assert "Il titolo" not in units[0].text


# ---------------------------------------------------------------------------
# Intermediate provenance window attribution
# ---------------------------------------------------------------------------


def test_intermediates_attach_only_to_windows_that_span_them():
    # 9 visible nodes with a technical node between visible #3 and #4.
    # Window 1 spans visible 1–6 (contains the 3->4 gap); window 2 spans
    # visible 4–9 and starts AT visible #4, so the technical node before
    # its first node belongs to window 1 only (same attribution rule as
    # M4.2a intermediates_before).
    specs = []
    for i in range(1, 10):
        specs.append({"role": "user" if i % 2 else "assistant", "text_parts": [f"msg {i}"]})
    specs.insert(3, {
        "node_id": "tech",
        "role": "assistant",
        "content_type": "thoughts",
        "content": {"content_type": "thoughts"},
    })
    fixture = chain_conversation("conv-int", specs)
    units, _, visible, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert visible["conv-int"] == 9
    assert len(units) == 2
    assert units[0].intermediate_node_ids == ["tech"]
    assert units[1].intermediate_node_ids == []


# ---------------------------------------------------------------------------
# Cross-conversation isolation and output ordering
# ---------------------------------------------------------------------------


def test_units_never_cross_conversations_and_follow_input_order():
    fixture_b = linear_conversation("conv-zzz", 9)
    fixture_a = linear_conversation("conv-aaa", 7)
    # Deliberately pass conv-zzz first: output must follow the input
    # (conversations.jsonl) order, not any resorting.
    units, _, _, per_conv = generate(
        [fixture_b["conversation"], fixture_a["conversation"]],
        fixture_b["nodes"] + fixture_a["nodes"],
    )
    assert per_conv == {"conv-zzz": 2, "conv-aaa": 2}
    assert [unit.conversation_id for unit in units] == ["conv-zzz", "conv-zzz", "conv-aaa", "conv-aaa"]
    for unit in units:
        assert all(node_id.startswith("n") for node_id in unit.node_ids)
    # Within each conversation, units are ordered by ordinal_start.
    assert [unit.ordinal_start for unit in units] == [0, 3, 0, 3]


def test_missing_current_node_is_an_anomaly_not_a_crash():
    conversation = make_conversation("conv-x", None)
    units, anomalies, _, per_conv = generate([conversation], [])
    assert units == []
    assert per_conv["conv-x"] == 0
    assert any(anomaly.type == "missing_current_node" for anomaly in anomalies)


def test_non_current_path_nodes_are_excluded():
    fixture = linear_conversation("conv-y", 3)
    # Add a stray visible node not on the current path (side branch).
    stray = make_node("conv-y", "side", "n1", role="assistant", text_parts=["BRANCH"], is_current_path=False)
    units, _, visible, _ = generate([fixture["conversation"]], fixture["nodes"] + [stray])
    assert visible["conv-y"] == 3
    assert len(units) == 1
    assert "BRANCH" not in units[0].text
    assert "side" not in units[0].node_ids
