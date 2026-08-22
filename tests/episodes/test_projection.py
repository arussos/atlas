"""
M4.2a RC2 — Tests for tools/episodes/projection.py (Dialogue Timeline Projection).

Covers spec section 13.A (basic projection), 13.B (intermediate
provenance), 13.E (unknown content type never crashes and is excluded).
"""

from tests.episodes.fixtures import make_node
from tools.episodes.projection import (
    VISIBLE_DIALOGUE_CONTENT_TYPES,
    is_visible_dialogue_node,
    project_dialogue_timeline,
)


def test_visible_dialogue_content_types_is_exactly_text_and_multimodal_text():
    assert VISIBLE_DIALOGUE_CONTENT_TYPES == frozenset({"text", "multimodal_text"})


def test_text_and_multimodal_text_are_visible():
    text_node = make_node("conv", "a", "root", content_type="text", text_parts=["hi"])
    multimodal_node = make_node("conv", "b", "a", content_type="multimodal_text", text_parts=["hi"])
    assert is_visible_dialogue_node(text_node) is True
    assert is_visible_dialogue_node(multimodal_node) is True


def test_thoughts_and_reasoning_recap_are_not_visible():
    thoughts_node = make_node("conv", "x", "root", content_type="thoughts", text_parts=["internal"])
    recap_node = make_node("conv", "y", "x", content_type="reasoning_recap", text_parts=["internal"])
    assert is_visible_dialogue_node(thoughts_node) is False
    assert is_visible_dialogue_node(recap_node) is False


def test_empty_text_node_is_still_visible():
    node = make_node("conv", "a", "root", content_type="text", text_parts=[])
    assert is_visible_dialogue_node(node) is True


def test_unknown_content_type_is_treated_as_non_visible_and_does_not_crash():
    node = make_node("conv", "w", "root", content_type="some_future_type", text_parts=["W"])
    assert is_visible_dialogue_node(node) is False


# ---------------------------------------------------------------------------
# A. Basic projection
# ---------------------------------------------------------------------------


def test_basic_projection_skips_thoughts_and_reasoning_recap():
    a = make_node("conv", "a", "root", role="user", content_type="text", text_parts=["A"])
    x = make_node("conv", "x", "a", role="assistant", content_type="thoughts", text_parts=["X"])
    y = make_node("conv", "y", "x", role="assistant", content_type="reasoning_recap", text_parts=["Y"])
    b = make_node("conv", "b", "y", role="assistant", content_type="text", text_parts=["B"])
    c = make_node("conv", "c", "b", role="user", content_type="text", text_parts=["C"])

    visible, intermediates_before = project_dialogue_timeline([a, x, y, b, c])

    assert [n["node_id"] for n in visible] == ["a", "b", "c"]
    assert len(intermediates_before) == 3
    assert intermediates_before[0] == []
    assert [n["node_id"] for n in intermediates_before[1]] == ["x", "y"]
    assert intermediates_before[2] == []


# ---------------------------------------------------------------------------
# B. Intermediate provenance
# ---------------------------------------------------------------------------


def test_intermediate_provenance_preserves_order_and_content_types():
    a = make_node("conv", "a", "root", role="user", content_type="text", text_parts=["A"])
    x = make_node("conv", "x", "a", role="assistant", content_type="thoughts", text_parts=["X"])
    y = make_node("conv", "y", "x", role="assistant", content_type="reasoning_recap", text_parts=["Y"])
    b = make_node("conv", "b", "y", role="assistant", content_type="text", text_parts=["B"])

    visible, intermediates_before = project_dialogue_timeline([a, x, y, b])

    assert len(intermediates_before[1]) == 2
    assert [n["node_id"] for n in intermediates_before[1]] == ["x", "y"]
    assert [n["content_type"] for n in intermediates_before[1]] == ["thoughts", "reasoning_recap"]


# ---------------------------------------------------------------------------
# E. Unknown content type between two visible nodes
# ---------------------------------------------------------------------------


def test_unknown_content_type_excluded_from_visible_but_preserved_as_provenance():
    a = make_node("conv", "a", "root", role="user", content_type="text", text_parts=["A"])
    weird = make_node("conv", "w", "a", role="assistant", content_type="some_future_type", text_parts=["W"])
    b = make_node("conv", "b", "w", role="assistant", content_type="text", text_parts=["B"])

    visible, intermediates_before = project_dialogue_timeline([a, weird, b])

    assert [n["node_id"] for n in visible] == ["a", "b"]
    assert [n["node_id"] for n in intermediates_before[1]] == ["w"]
    assert [n["content_type"] for n in intermediates_before[1]] == ["some_future_type"]


def test_leading_non_visible_nodes_before_first_visible_are_dropped():
    x = make_node("conv", "x", "root", role="assistant", content_type="thoughts", text_parts=["X"])
    a = make_node("conv", "a", "x", role="user", content_type="text", text_parts=["A"])

    visible, intermediates_before = project_dialogue_timeline([x, a])

    assert [n["node_id"] for n in visible] == ["a"]
    assert intermediates_before == [[]]


def test_trailing_non_visible_nodes_after_last_visible_are_not_attached_anywhere():
    a = make_node("conv", "a", "root", role="user", content_type="text", text_parts=["A"])
    x = make_node("conv", "x", "a", role="assistant", content_type="thoughts", text_parts=["X"])

    visible, intermediates_before = project_dialogue_timeline([a, x])

    assert [n["node_id"] for n in visible] == ["a"]
    assert intermediates_before == [[]]


def test_empty_input_yields_empty_projection():
    visible, intermediates_before = project_dialogue_timeline([])
    assert visible == []
    assert intermediates_before == []


def test_all_non_visible_yields_empty_visible_timeline():
    x = make_node("conv", "x", "root", role="assistant", content_type="thoughts", text_parts=["X"])
    y = make_node("conv", "y", "x", role="assistant", content_type="reasoning_recap", text_parts=["Y"])

    visible, intermediates_before = project_dialogue_timeline([x, y])

    assert visible == []
    assert intermediates_before == []
