"""
M4.2a — Tests for tools/episodes/graph.py

Covers spec section 17.A (graph order over timestamp order) and 17.I
(structural anomalies: missing current node, cycle, dangling parent).
"""

from tools.episodes.graph import reconstruct_current_path


def _node(node_id, parent_id):
    return {"node_id": node_id, "parent_id": parent_id}


# ---------------------------------------------------------------------------
# A. Graph order (not timestamp order)
# ---------------------------------------------------------------------------


def test_order_follows_parent_chain_not_timestamps():
    # technical root -> user A -> assistant A -> user B -> assistant B
    # Timestamps (not modeled here at all — graph.py never looks at them)
    # would sort differently; only parent_id must determine order.
    nodes_by_id = {
        "root": _node("root", None),
        "user_a": _node("user_a", "root"),
        "asst_a": _node("asst_a", "user_a"),
        "user_b": _node("user_b", "asst_a"),
        "asst_b": _node("asst_b", "user_b"),
    }
    ordered, anomalies = reconstruct_current_path("conv-1", "asst_b", nodes_by_id)
    assert anomalies == []
    assert ordered == ["root", "user_a", "asst_a", "user_b", "asst_b"]


def test_order_follows_branch_selected_by_current_node():
    nodes_by_id = {
        "root": _node("root", None),
        "user_b": _node("user_b", "root"),
        "asst_b1": _node("asst_b1", "user_b"),
        "asst_b2": _node("asst_b2", "user_b"),
    }
    ordered, anomalies = reconstruct_current_path("conv-1", "asst_b1", nodes_by_id)
    assert anomalies == []
    assert ordered == ["root", "user_b", "asst_b1"]
    assert "asst_b2" not in ordered


# ---------------------------------------------------------------------------
# I. Structural anomalies
# ---------------------------------------------------------------------------


def test_missing_current_node_id_flagged():
    ordered, anomalies = reconstruct_current_path("conv-1", None, {"root": _node("root", None)})
    assert ordered == []
    assert len(anomalies) == 1
    assert anomalies[0].type == "missing_current_node"
    assert anomalies[0].conversation_id == "conv-1"


def test_current_node_not_in_mapping_flagged():
    ordered, anomalies = reconstruct_current_path("conv-1", "ghost", {"root": _node("root", None)})
    assert ordered == []
    assert len(anomalies) == 1
    assert anomalies[0].type == "missing_current_node"
    assert anomalies[0].node_id == "ghost"


def test_dangling_parent_flagged_and_walk_stops():
    # user_b's parent "missing_root" is not present in nodes_by_id.
    nodes_by_id = {
        "user_b": _node("user_b", "missing_root"),
    }
    ordered, anomalies = reconstruct_current_path("conv-1", "user_b", nodes_by_id)
    assert ordered == ["user_b"]
    assert len(anomalies) == 1
    assert anomalies[0].type == "dangling_parent"
    assert anomalies[0].node_id == "missing_root"


def test_cycle_detected_and_walk_stops():
    # a -> b -> a (cycle), reached from "b"
    nodes_by_id = {
        "a": _node("a", "b"),
        "b": _node("b", "a"),
    }
    ordered, anomalies = reconstruct_current_path("conv-1", "b", nodes_by_id)
    assert len(anomalies) == 1
    assert anomalies[0].type == "current_path_cycle"
    # walk must terminate rather than loop forever
    assert set(ordered) <= {"a", "b"}
