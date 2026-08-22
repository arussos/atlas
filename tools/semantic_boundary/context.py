"""
M4.2b-A — Politica di contesto v0.1 per il Semantic Boundary Resolver.

Estrae una finestra fissa e piccola di turni di dialogo visibili attorno a
una candidate transition: fino a 2 turni prima e 2 dopo, includendo sempre
i due turni endpoint (before_node_id, after_node_id). Non esegue alcuna
retrieval, non consulta altre conversazioni, non aggiunge memoria di
progetto nascosta — riceve in input solo la sequenza già proiettata dei
nodi dialogue visibili di UNA conversazione (Dialogue Timeline Projection
di M4.2a, tools/episodes/projection.py) e ne estrae una sotto-finestra.
"""

from typing import List, Tuple

from tools.semantic_boundary.models import DialogueTurn, RequestValidationError

DEFAULT_BEFORE_WINDOW = 2
DEFAULT_AFTER_WINDOW = 2


def clip_context(
    turns: List[DialogueTurn],
    before_node_id: str,
    after_node_id: str,
    *,
    before_window: int = DEFAULT_BEFORE_WINDOW,
    after_window: int = DEFAULT_AFTER_WINDOW,
) -> Tuple[List[DialogueTurn], List[DialogueTurn]]:
    """
    Ritaglia (before_context, after_context) da turns, preservando
    l'ordine originale e includendo sempre i turni endpoint.

    before_context: fino a before_window turni che terminano con
    before_node_id incluso.
    after_context: fino a after_window turni che iniziano con
    after_node_id incluso.

    turns deve contenere sia before_node_id sia after_node_id, con
    after_node_id che segue strettamente before_node_id nella sequenza
    (così come costruito da M4.2a: coppie consecutive di nodi dialogue
    visibili). Solleva RequestValidationError altrimenti — mai un
    troncamento silenzioso o una finestra vuota.
    """
    if before_window < 1 or after_window < 1:
        raise RequestValidationError("before_window and after_window must each be >= 1")

    index_by_node_id = {turn.node_id: i for i, turn in enumerate(turns)}

    if before_node_id not in index_by_node_id:
        raise RequestValidationError(f"before_node_id {before_node_id!r} not found in supplied timeline")
    if after_node_id not in index_by_node_id:
        raise RequestValidationError(f"after_node_id {after_node_id!r} not found in supplied timeline")

    before_index = index_by_node_id[before_node_id]
    after_index = index_by_node_id[after_node_id]

    if after_index <= before_index:
        raise RequestValidationError(
            "after_node_id must occur strictly after before_node_id in the supplied timeline"
        )

    before_context = turns[max(0, before_index - before_window + 1): before_index + 1]
    after_context = turns[after_index: after_index + after_window]

    return before_context, after_context
