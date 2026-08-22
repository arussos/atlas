"""
M4.2a — Estrazione deterministica del testo visibile dal contenuto dei nodi ACNF.

Solo il contenuto effettivamente visto da un utente finale è eleggibile
come testo per il boundary-detection. I content type thoughts /
reasoning_recap sono esclusi di default — anche se un nodo ACNF può
trasportarli, usare il ragionamento interno del modello come segnale di
"testo visibile" rappresenterebbe in modo scorretto ciò che le feature dei
boundary candidate stanno effettivamente misurando (vedi
docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md, sezione sullo schema
BoundaryCandidate).

Non modifica mai il contenuto ACNF; non solleva mai eccezioni su contenuto
malformato o sconosciuto.
"""

from typing import Any

# Separatore usato per unire più string part. Stabile e arbitrario — serve
# solo a evitare che contenuto multi-part venga incollato token-a-token dal
# tokenizer lessicale a valle.
_STABLE_PART_SEPARATOR = "\n"

# content_type noti per non trasportare testo visibile all'utente finale,
# ai fini di M4.2a. Elencati esplicitamente così l'esclusione è visibile
# nel codice, non implicita dal "non nell'insieme supportato" sotto.
_EXCLUDED_CONTENT_TYPES = {"thoughts", "reasoning_recap"}

# content_type con una lista "parts" di elementi testuali e/o non testuali.
_TEXT_PART_CONTENT_TYPES = {"text", "multimodal_text"}


def extract_visible_text(content_type: Any, content: Any) -> str:
    """
    Restituisce il testo deterministico, visibile all'utente, per il
    contenuto del messaggio di un nodo ACNF. Restituisce "" per i content
    type senza testo visibile utilizzabile, per i content type sconosciuti
    e per contenuto malformato — non solleva mai eccezioni.
    """
    if content_type in _EXCLUDED_CONTENT_TYPES:
        return ""

    if content_type not in _TEXT_PART_CONTENT_TYPES:
        return ""

    if not isinstance(content, dict):
        return ""

    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""

    strings = [part for part in parts if isinstance(part, str)]
    return _STABLE_PART_SEPARATOR.join(strings)
