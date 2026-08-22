"""
M4.2a — Lessico deterministico di marker orientato all'italiano (v0.1).

Il matching è case-insensitive (casefold Unicode) per sottostringa contro
testo normalizzato — nessun fuzzy matching, nessun LLM. Quando un marker
scatta, viene preservata nel record del candidate la frase esatta del
lessico (non la sottostringa grezza trovata né la sua posizione).

Su quale lato della transizione (before_text vs. after_text) viene
confrontata ciascuna categoria è una decisione di design non resa esplicita
in docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md — risolta qui (vedi
tools/episodes/boundary_candidates.py, _build_candidate): i closure marker
sono confrontati contro before_text (descrivono cosa il messaggio
precedente ha chiuso), i marker opening/resume/transition sono confrontati
contro after_text (descrivono come inizia il messaggio successivo).

NOTA (Gold Pilot 001, freeze M4.2a): sui dati reali i marker di
apertura/chiusura aggiungono un po' di evidenza, ma nessun marker da solo
è prova di un boundary — vedi la sezione "Marker findings" della
documentazione. Il lessico non è stato modificato in questa passata.
"""

from typing import List

OPENING_MARKERS: List[str] = [
    "ora passiamo",
    "passiamo a",
    "nuovo problema",
    "nuova questione",
    "altra cosa",
    "veniamo a",
    "cambiamo argomento",
    "ora vorrei",
    "a questo punto",
]

CLOSURE_MARKERS: List[str] = [
    "ora funziona",
    "adesso funziona",
    "risolto",
    "problema risolto",
    "bene così",
    "questo è chiuso",
    "possiamo chiudere",
    "abbiamo finito",
]

RESUME_MARKERS: List[str] = [
    "riprendiamo",
    "torniamo a",
    "continuiamo da",
    "come dicevamo",
    "ripartiamo da",
    "proseguiamo",
]

TRANSITION_MARKERS: List[str] = [
    "invece",
    "per quanto riguarda",
    "adesso occupiamoci",
    "ora vediamo",
    "passiamo invece",
]


def find_markers(text: str, lexicon: List[str]) -> List[str]:
    """
    Restituisce le frasi del lessico (nell'ordine del lessico, con il
    casing esatto del lessico) trovate come sottostringa case-insensitive
    di text. Deterministico — nessun fuzzy matching, nessuna
    normalizzazione oltre al casefold.
    """
    if not text:
        return []
    normalized = text.casefold()
    return [phrase for phrase in lexicon if phrase.casefold() in normalized]
