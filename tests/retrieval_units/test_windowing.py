"""
M5.1 — Tests for compute_windows (spec section 4: window 6 / stride 3 /
tail never dropped; spec section 14 cases A–F on the pure windowing
function, plus a coverage sweep).
"""

from tools.retrieval_units.projection import compute_windows


def test_zero_visible_nodes_yields_zero_windows():
    assert compute_windows(0) == []


def test_one_visible_node_yields_one_window():
    assert compute_windows(1) == [(0, 1)]


def test_fewer_than_six_yields_one_window_with_all_nodes():
    assert compute_windows(5) == [(0, 5)]
    assert compute_windows(3) == [(0, 3)]


def test_exactly_six_yields_one_window():
    assert compute_windows(6) == [(0, 6)]


def test_nine_yields_windows_1_6_and_4_9():
    # 0-based [start, end) equivalents of the spec's 1-based 1-6 / 4-9.
    assert compute_windows(9) == [(0, 6), (3, 9)]


def test_fourteen_yields_spec_windows():
    # Spec: 1-6, 4-9, 7-12, 10-14 (1-based inclusive).
    assert compute_windows(14) == [(0, 6), (3, 9), (6, 12), (9, 14)]


def test_seven_produces_short_tail_not_dropped():
    assert compute_windows(7) == [(0, 6), (3, 7)]


def test_every_visible_node_is_covered_and_windows_are_ordered():
    for n in range(0, 50):
        windows = compute_windows(n)
        covered = set()
        for start, end in windows:
            assert 0 <= start < end <= n
            covered.update(range(start, end))
        assert covered == set(range(n))
        starts = [start for start, _ in windows]
        assert starts == sorted(starts)
        if windows:
            # The last window always includes the last node — no tail loss.
            assert windows[-1][1] == n
