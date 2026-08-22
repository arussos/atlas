"""
M4.2a — Tests for tools/episodes/scoring.py

Covers spec section 17.G: opening/transition/closure increase score,
resume lowers it, time gap alone never forces HIGH, clamping, and
LOW/MEDIUM/HIGH threshold boundaries.
"""

from tools.episodes.models import CANDIDATE_CLASS_HIGH, CANDIDATE_CLASS_LOW, CANDIDATE_CLASS_MEDIUM
from tools.episodes.scoring import BoundaryScoreConfig, classify_candidate, compute_candidate_score
from tools.episodes.timegap import TIME_GAP_BUCKET_GE_7D, TIME_GAP_BUCKET_LT_1M, TIME_GAP_BUCKET_UNKNOWN


def _score(**overrides):
    kwargs = dict(
        time_gap_bucket=TIME_GAP_BUCKET_LT_1M,
        opening_markers=[],
        closure_markers=[],
        resume_markers=[],
        transition_markers=[],
        lexical_shift_score=0.0,
    )
    kwargs.update(overrides)
    return compute_candidate_score(**kwargs)


def test_opening_marker_increases_score():
    baseline = _score()
    with_opening = _score(opening_markers=["ora passiamo"])
    assert with_opening > baseline


def test_transition_marker_increases_score():
    baseline = _score()
    with_transition = _score(transition_markers=["invece"])
    assert with_transition > baseline


def test_closure_marker_contributes_positively():
    baseline = _score()
    with_closure = _score(closure_markers=["risolto"])
    assert with_closure > baseline


def test_resume_marker_lowers_score():
    without_resume = _score(opening_markers=["ora passiamo"], transition_markers=["invece"])
    with_resume = _score(opening_markers=["ora passiamo"], transition_markers=["invece"], resume_markers=["riprendiamo"])
    assert with_resume < without_resume


def test_time_gap_alone_does_not_force_high():
    score = _score(time_gap_bucket=TIME_GAP_BUCKET_GE_7D)
    config = BoundaryScoreConfig()
    assert score < config.high_threshold
    assert classify_candidate(score) != CANDIDATE_CLASS_HIGH


def test_time_gap_alone_does_not_even_reach_medium():
    score = _score(time_gap_bucket=TIME_GAP_BUCKET_GE_7D)
    config = BoundaryScoreConfig()
    assert score < config.low_threshold
    assert classify_candidate(score) == CANDIDATE_CLASS_LOW


def test_unknown_time_gap_bucket_contributes_nothing():
    assert _score(time_gap_bucket=TIME_GAP_BUCKET_UNKNOWN) == 0.0


def test_score_clamped_to_zero_minimum():
    # opening + transition + closure + max lexical, minus a strong resume
    # penalty, must never go below 0.0
    score = _score(
        opening_markers=["ora passiamo"],
        resume_markers=["riprendiamo"],
        lexical_shift_score=0.0,
    )
    assert score >= 0.0


def test_score_clamped_to_one_maximum():
    score = _score(
        time_gap_bucket=TIME_GAP_BUCKET_GE_7D,
        opening_markers=["ora passiamo"],
        closure_markers=["risolto"],
        transition_markers=["invece"],
        lexical_shift_score=1.0,
    )
    assert score <= 1.0


def test_threshold_boundary_low_medium():
    config = BoundaryScoreConfig()
    assert classify_candidate(config.low_threshold - 0.001, config) == CANDIDATE_CLASS_LOW
    assert classify_candidate(config.low_threshold, config) == CANDIDATE_CLASS_MEDIUM


def test_threshold_boundary_medium_high():
    config = BoundaryScoreConfig()
    assert classify_candidate(config.high_threshold - 0.001, config) == CANDIDATE_CLASS_MEDIUM
    assert classify_candidate(config.high_threshold, config) == CANDIDATE_CLASS_HIGH


def test_zero_evidence_classifies_low():
    assert classify_candidate(_score()) == CANDIDATE_CLASS_LOW
