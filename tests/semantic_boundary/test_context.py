"""Test A/B: costruzione del contesto e ritaglio (context.py)."""

import pytest

from tools.semantic_boundary.context import clip_context
from tools.semantic_boundary.models import RequestValidationError

from tests.semantic_boundary.fixtures import make_timeline


def test_endpoint_turns_are_always_included():
    timeline = make_timeline(["n1", "n2", "n3", "n4"])
    before, after = clip_context(timeline, "n2", "n3")
    assert before[-1].node_id == "n2"
    assert after[0].node_id == "n3"


def test_default_window_is_two_before_two_after():
    timeline = make_timeline(["n0", "n1", "n2", "n3", "n4", "n5"])
    before, after = clip_context(timeline, "n2", "n3")
    assert [t.node_id for t in before] == ["n1", "n2"]
    assert [t.node_id for t in after] == ["n3", "n4"]


def test_order_is_preserved():
    timeline = make_timeline(["n0", "n1", "n2", "n3", "n4", "n5"])
    timeline_ids = [t.node_id for t in timeline]
    before, after = clip_context(timeline, "n2", "n3")
    before_ids = [t.node_id for t in before]
    after_ids = [t.node_id for t in after]
    assert before_ids == sorted(before_ids, key=timeline_ids.index)
    assert after_ids == sorted(after_ids, key=timeline_ids.index)


def test_short_timeline_is_correctly_limited_at_the_start():
    """La finestra prima del candidate è più corta della richiesta se la timeline inizia lì."""
    timeline = make_timeline(["n0", "n1", "n2"])
    before, after = clip_context(timeline, "n0", "n1")
    assert [t.node_id for t in before] == ["n0"]
    assert [t.node_id for t in after] == ["n1", "n2"]


def test_short_timeline_is_correctly_limited_at_the_end():
    """La finestra dopo il candidate è più corta della richiesta se la timeline finisce lì."""
    timeline = make_timeline(["n0", "n1", "n2"])
    before, after = clip_context(timeline, "n1", "n2")
    assert [t.node_id for t in before] == ["n0", "n1"]
    assert [t.node_id for t in after] == ["n2"]


def test_longer_timeline_is_correctly_clipped_beyond_window():
    timeline = make_timeline([f"n{i}" for i in range(20)])
    before, after = clip_context(timeline, "n10", "n11", before_window=2, after_window=2)
    assert [t.node_id for t in before] == ["n9", "n10"]
    assert [t.node_id for t in after] == ["n11", "n12"]


def test_custom_window_sizes_are_respected():
    timeline = make_timeline([f"n{i}" for i in range(20)])
    before, after = clip_context(timeline, "n10", "n11", before_window=1, after_window=3)
    assert [t.node_id for t in before] == ["n10"]
    assert [t.node_id for t in after] == ["n11", "n12", "n13"]


def test_missing_before_node_id_raises():
    timeline = make_timeline(["n0", "n1"])
    with pytest.raises(RequestValidationError):
        clip_context(timeline, "missing", "n1")


def test_missing_after_node_id_raises():
    timeline = make_timeline(["n0", "n1"])
    with pytest.raises(RequestValidationError):
        clip_context(timeline, "n0", "missing")


def test_after_not_strictly_after_before_raises():
    timeline = make_timeline(["n0", "n1", "n2"])
    with pytest.raises(RequestValidationError):
        clip_context(timeline, "n1", "n0")


def test_after_equal_to_before_raises():
    timeline = make_timeline(["n0", "n1"])
    with pytest.raises(RequestValidationError):
        clip_context(timeline, "n0", "n0")
