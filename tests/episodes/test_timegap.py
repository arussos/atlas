"""
M4.2a — Tests for tools/episodes/timegap.py

Covers spec section 17.C: exact bucket boundaries and invalid/negative gaps.
"""

from tools.episodes.timegap import (
    TIME_GAP_BUCKET_LT_1M,
    TIME_GAP_BUCKET_1M_5M,
    TIME_GAP_BUCKET_5M_15M,
    TIME_GAP_BUCKET_15M_30M,
    TIME_GAP_BUCKET_30M_1H,
    TIME_GAP_BUCKET_1H_3H,
    TIME_GAP_BUCKET_3H_12H,
    TIME_GAP_BUCKET_12H_1D,
    TIME_GAP_BUCKET_1D_7D,
    TIME_GAP_BUCKET_GE_7D,
    TIME_GAP_BUCKET_UNKNOWN,
    compute_time_gap,
)


def _gap(seconds):
    return compute_time_gap(1000.0, 1000.0 + seconds)


def test_boundary_59_is_lt_1m():
    assert _gap(59)[1] == TIME_GAP_BUCKET_LT_1M


def test_boundary_60_is_1m_5m():
    assert _gap(60)[1] == TIME_GAP_BUCKET_1M_5M


def test_boundary_299_is_1m_5m():
    assert _gap(299)[1] == TIME_GAP_BUCKET_1M_5M


def test_boundary_300_is_5m_15m():
    assert _gap(300)[1] == TIME_GAP_BUCKET_5M_15M


def test_boundary_899_is_5m_15m():
    assert _gap(899)[1] == TIME_GAP_BUCKET_5M_15M


def test_boundary_900_is_15m_30m():
    assert _gap(900)[1] == TIME_GAP_BUCKET_15M_30M


def test_boundary_1799_is_15m_30m():
    assert _gap(1799)[1] == TIME_GAP_BUCKET_15M_30M


def test_boundary_1800_is_30m_1h():
    assert _gap(1800)[1] == TIME_GAP_BUCKET_30M_1H


def test_boundary_3599_is_30m_1h():
    assert _gap(3599)[1] == TIME_GAP_BUCKET_30M_1H


def test_boundary_3600_is_1h_3h():
    assert _gap(3600)[1] == TIME_GAP_BUCKET_1H_3H


def test_boundary_10799_is_1h_3h():
    assert _gap(10799)[1] == TIME_GAP_BUCKET_1H_3H


def test_boundary_10800_is_3h_12h():
    assert _gap(10800)[1] == TIME_GAP_BUCKET_3H_12H


def test_boundary_43199_is_3h_12h():
    assert _gap(43199)[1] == TIME_GAP_BUCKET_3H_12H


def test_boundary_43200_is_12h_1d():
    assert _gap(43200)[1] == TIME_GAP_BUCKET_12H_1D


def test_boundary_86399_is_12h_1d():
    assert _gap(86399)[1] == TIME_GAP_BUCKET_12H_1D


def test_boundary_86400_is_1d_7d():
    assert _gap(86400)[1] == TIME_GAP_BUCKET_1D_7D


def test_boundary_604799_is_1d_7d():
    assert _gap(604799)[1] == TIME_GAP_BUCKET_1D_7D


def test_boundary_604800_is_ge_7d():
    assert _gap(604800)[1] == TIME_GAP_BUCKET_GE_7D


def test_seconds_value_preserved_for_valid_gap():
    seconds, bucket = _gap(120)
    assert seconds == 120
    assert bucket == TIME_GAP_BUCKET_1M_5M


def test_negative_gap_is_unknown():
    seconds, bucket = compute_time_gap(2000.0, 1000.0)
    assert seconds is None
    assert bucket == TIME_GAP_BUCKET_UNKNOWN


def test_none_before_is_unknown():
    seconds, bucket = compute_time_gap(None, 1000.0)
    assert seconds is None
    assert bucket == TIME_GAP_BUCKET_UNKNOWN


def test_none_after_is_unknown():
    seconds, bucket = compute_time_gap(1000.0, None)
    assert seconds is None
    assert bucket == TIME_GAP_BUCKET_UNKNOWN


def test_both_none_is_unknown():
    seconds, bucket = compute_time_gap(None, None)
    assert seconds is None
    assert bucket == TIME_GAP_BUCKET_UNKNOWN


def test_non_numeric_timestamp_is_unknown():
    seconds, bucket = compute_time_gap("not-a-timestamp", 1000.0)
    assert seconds is None
    assert bucket == TIME_GAP_BUCKET_UNKNOWN


def test_boolean_timestamp_is_not_valid():
    # bool is a subclass of int in Python but must not be accepted as a
    # valid timestamp.
    seconds, bucket = compute_time_gap(True, 1000.0)
    assert seconds is None
    assert bucket == TIME_GAP_BUCKET_UNKNOWN


def test_zero_gap_is_lt_1m():
    seconds, bucket = compute_time_gap(1000.0, 1000.0)
    assert seconds == 0
    assert bucket == TIME_GAP_BUCKET_LT_1M
