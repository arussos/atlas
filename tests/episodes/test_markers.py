"""
M4.2a — Tests for tools/episodes/markers.py

Covers spec section 17.D: case-insensitivity, multiple markers, all four
categories.
"""

from tools.episodes.markers import (
    CLOSURE_MARKERS,
    OPENING_MARKERS,
    RESUME_MARKERS,
    TRANSITION_MARKERS,
    find_markers,
)


def test_opening_marker_matched():
    # "passiamo a" is deliberately also a substring match here ("passiamo al")
    # — matching is plain substring, no word boundaries, per spec section 11.
    assert find_markers("bene, ora passiamo al prossimo argomento", OPENING_MARKERS) == [
        "ora passiamo",
        "passiamo a",
    ]


def test_closure_marker_matched():
    assert find_markers("ottimo, ora funziona correttamente", CLOSURE_MARKERS) == ["ora funziona"]


def test_resume_marker_matched():
    assert find_markers("riprendiamo da dove eravamo rimasti", RESUME_MARKERS) == ["riprendiamo"]


def test_transition_marker_matched():
    assert find_markers("per quanto riguarda il secondo punto", TRANSITION_MARKERS) == ["per quanto riguarda"]


def test_case_insensitive_matching():
    assert find_markers("ORA PASSIAMO al problema successivo", OPENING_MARKERS) == [
        "ora passiamo",
        "passiamo a",
    ]
    assert find_markers("Ora Funziona tutto", CLOSURE_MARKERS) == ["ora funziona"]


def test_no_marker_found_returns_empty_list():
    assert find_markers("questo testo non contiene alcun marker noto", OPENING_MARKERS) == []


def test_empty_text_returns_empty_list():
    assert find_markers("", OPENING_MARKERS) == []
    assert find_markers(None, OPENING_MARKERS) == []


def test_multiple_markers_in_same_text_all_returned_in_lexicon_order():
    text = "problema risolto, bene così, ora funziona"
    matches = find_markers(text, CLOSURE_MARKERS)
    # lexicon order is preserved regardless of the order they appear in text
    assert matches == ["ora funziona", "risolto", "problema risolto", "bene così"]


def test_matched_phrase_preserves_exact_lexicon_casing():
    matches = find_markers("ADESSO OCCUPIAMOCI di questo", TRANSITION_MARKERS)
    assert matches == ["adesso occupiamoci"]
    assert matches[0] == "adesso occupiamoci"  # exact lexicon phrase, not the raw matched text
