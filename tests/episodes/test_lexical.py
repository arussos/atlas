"""
M4.2a — Tests for tools/episodes/lexical.py

Covers spec section 17.F: identical text, completely different text,
partial overlap, empty inputs, Italian accents.
"""

from tools.episodes.lexical import jaccard_similarity, lexical_features, tokenize


def test_identical_text_similarity_is_one():
    assert jaccard_similarity("installiamo Zabbix", "installiamo Zabbix") == 1.0


def test_completely_different_text_similarity_is_zero():
    assert jaccard_similarity("configurazione MikroTik", "monitoraggio repeater UHF") == 0.0


def test_partial_overlap_similarity_between_zero_and_one():
    similarity = jaccard_similarity("installiamo Zabbix su Debian", "installiamo Zabbix su Ubuntu")
    assert 0.0 < similarity < 1.0


def test_partial_overlap_exact_jaccard_value():
    # tokens (after casefold, stopword removal of "su"): {installiamo, zabbix, debian} vs
    # {installiamo, zabbix, ubuntu} -> intersection=2, union=4 -> 0.5
    similarity = jaccard_similarity("installiamo Zabbix su Debian", "installiamo Zabbix su Ubuntu")
    assert similarity == 0.5


def test_both_empty_similarity_is_one():
    assert jaccard_similarity("", "") == 1.0


def test_one_empty_one_non_empty_similarity_is_zero():
    assert jaccard_similarity("", "qualcosa di nuovo") == 0.0
    assert jaccard_similarity("qualcosa di vecchio", "") == 0.0


def test_single_token_identical():
    assert jaccard_similarity("ciao", "ciao") == 1.0


def test_single_token_different():
    assert jaccard_similarity("ciao", "mondo") == 0.0


def test_italian_accents_tokenized_and_compared_correctly():
    tokens = tokenize("è già così, città perché così")
    assert "città" in tokens
    assert "perché" in tokens
    assert "già" in tokens
    assert "così" in tokens
    # "è" is a stopword and must be removed
    assert "è" not in tokens


def test_italian_accented_tokens_match_across_texts():
    similarity = jaccard_similarity("la città è bellissima", "città meravigliosa oggi")
    assert similarity > 0.0


def test_lexical_features_shift_is_complement_of_similarity():
    similarity, shift = lexical_features("stessa frase identica", "stessa frase identica")
    assert similarity == 1.0
    assert shift == 0.0

    similarity, shift = lexical_features("argomento alfa", "argomento beta gamma")
    assert shift == 1.0 - similarity


def test_tokenize_removes_punctuation_implicitly():
    assert tokenize("ciao, mondo!") == frozenset({"ciao", "mondo"})
