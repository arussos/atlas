"""
M4.2a — Similarità lessicale deterministica tra due testi di messaggio.

Nessuna dipendenza NLP, nessun modello di embedding. Approccio scelto (vedi
docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md, sezione sulla lexical
similarity): casefolding Unicode, tokenizzazione a parole via regex (\\w+,
che scarta implicitamente la punteggiatura), un piccolo stopword set
italiano deterministico rimosso prima del confronto, e similarità di
Jaccard sugli insiemi di token risultanti.

Jaccard è stata preferita a cosine/vettori di frequenza dei token perché è
più semplice da ragionare e testare in modo deterministico per i casi
limite che questo modulo deve definire, e perché questa feature è solo
informativa — non è di per sé una decisione di boundary.

NOTA (Gold Pilot 001, freeze M4.2a): sui dati reali la lexical similarity
si è rivelata debolmente discriminante per i boundary semantici — vedi la
sezione "Jaccard / lexical shift" della documentazione. Va trattata solo
come evidenza di supporto; questo modulo non è stato modificato in questa
passata di chiusura.
"""

import re
from typing import FrozenSet, Tuple

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

# Piccolo stopword set italiano deterministico — deliberatamente corto per
# non inglobare parole brevi ma significative dal punto di vista topico
# (es. sostantivi di dominio).
STOPWORDS: FrozenSet[str] = frozenset(
    {
        "il", "lo", "la", "i", "gli", "le", "un", "uno", "una",
        "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
        "e", "o", "che", "non", "si", "è", "sono",
    }
)


def tokenize(text: str) -> FrozenSet[str]:
    """Casefold, tokenizza su \\w+, scarta le stopword. Deterministico, indipendente dall'ordine."""
    if not text:
        return frozenset()
    tokens = _TOKEN_RE.findall(text.casefold())
    return frozenset(token for token in tokens if token not in STOPWORDS)


def jaccard_similarity(before_text: str, after_text: str) -> float:
    """
    Similarità di Jaccard sugli insiemi di token filtrati dalle stopword.

    Casi limite (vedi doc, sezione lexical similarity — tutti testati in
    tests/episodes/test_lexical.py):
    - entrambi vuoti (o interamente stopword) -> 1.0: nessun testo da
      confrontare implica nessuna evidenza di uno shift lessicale.
    - esattamente uno vuoto -> 0.0: nessuna sovrapposizione possibile.
    - altrimenti |intersezione| / |unione|.
    """
    before_tokens = tokenize(before_text)
    after_tokens = tokenize(after_text)

    if not before_tokens and not after_tokens:
        return 1.0
    if not before_tokens or not after_tokens:
        return 0.0

    intersection = before_tokens & after_tokens
    union = before_tokens | after_tokens
    return len(intersection) / len(union)


def lexical_features(before_text: str, after_text: str) -> Tuple[float, float]:
    """Restituisce (lexical_similarity, lexical_shift_score) dove shift = 1 - similarity."""
    similarity = jaccard_similarity(before_text, after_text)
    return similarity, 1.0 - similarity
