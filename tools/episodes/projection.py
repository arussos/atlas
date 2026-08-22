"""
M4.2a RC2 — Dialogue Timeline Projection.

La run RC1 su dati reali ha dimostrato che il dominio dei candidate era
concettualmente sbagliato: generare candidate tra ogni nodo-messaggio del
current path (inclusi i nodi tecnici "thoughts" / "reasoning_recap") ha
fabbricato >99% delle transizioni assistant->assistant come artefatti di
nodi non visibili, non veri turni di dialogo. Vedi
docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md per il dettaglio.

Questo modulo proietta la sequenza ordinata di nodi-messaggio del current
path (vedi tools/episodes/graph.py — l'ordine del grafo resta autorevole;
questo modulo non riordina né rideriva mai l'ordine) sulla sottosequenza
dei nodi che erano effettivamente turni di dialogo visibili all'utente
finale:

    ACNF current path
        -> dialogue timeline projection (questo modulo)
        -> nodi dialogue visibili
        -> coppie consecutive di nodi visibili
        -> BoundaryCandidate

I nodi non visibili saltati tra due nodi visibili non vengono scartati —
vengono restituiti come provenance ordinata, così che BoundaryCandidate
possa registrare cosa è stato saltato tra i suoi estremi before/after.
ACNF stesso non viene mai modificato; questo modulo si limita a leggere
la lista di nodi-messaggio del current path già filtrata per una singola
conversazione.
"""

from typing import Any, Dict, List, Tuple

# Content type che rappresentano turni di dialogo visibili all'utente
# finale, eleggibili come vertici BoundaryCandidate. Tutto il resto sul
# current path (thoughts, reasoning_recap, e qualsiasi content type
# futuro/sconosciuto) resta preservato in ACNF ma non è un vertice di
# boundary per v0.1 — vedi docs, content-type visibility policy.
# Deliberatamente una costante separata e nominata indipendentemente da
# _TEXT_PART_CONTENT_TYPES (privata, in tools/episodes/text.py): oggi i
# due insiemi coincidono, ma uno governa la projection (quali nodi sono
# vertici di boundary) e l'altro la forma della text-extraction — possono
# divergere in futuro.
VISIBLE_DIALOGUE_CONTENT_TYPES = frozenset({"text", "multimodal_text"})


def is_visible_dialogue_node(node: Dict[str, Any]) -> bool:
    """
    True se e solo se il content_type del nodo è un tipo dialogue visibile v0.1.

    La visibilità è una decisione di content-type/dominio, non una
    decisione basata sulla lunghezza del testo: un nodo "text" con parts
    vuote resta comunque un nodo dialogue visibile ai fini della
    projection. I content type sconosciuti sono trattati come non
    visibili — mai un crash, mai un'ipotesi.
    """
    return node.get("content_type") in VISIBLE_DIALOGUE_CONTENT_TYPES


def project_dialogue_timeline(
    message_nodes: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
    """
    Proietta una lista ordinata di nodi-messaggio del current path sulla
    sua sottosequenza dialogue visibile, preservando sempre l'ordine del
    grafo.

    Restituisce (visible_nodes, intermediates_before):

    - visible_nodes: la sottosequenza di message_nodes che sono nodi
      dialogue visibili, nell'ordine originale del grafo.
    - intermediates_before[i]: la lista ordinata dei nodi non visibili
      apparsi sul current path strettamente tra visible_nodes[i - 1] e
      visible_nodes[i]. intermediates_before[0] è sempre [] — eventuali
      nodi non visibili prima del primo nodo visibile non hanno un nodo
      visibile precedente a cui agganciarsi come provenance, quindi
      vengono scartati, non agganciati a un candidate sintetico.

    len(visible_nodes) == len(intermediates_before). Un BoundaryCandidate
    costruito da visible_nodes[i] -> visible_nodes[i + 1] prende la sua
    provenance intermedia da intermediates_before[i + 1].
    """
    visible_nodes: List[Dict[str, Any]] = []
    intermediates_before: List[List[Dict[str, Any]]] = []
    pending: List[Dict[str, Any]] = []

    for node in message_nodes:
        if is_visible_dialogue_node(node):
            # Eventuali nodi non visibili accumulati prima del primissimo
            # nodo visibile non hanno un nodo visibile precedente a cui
            # agganciarsi come provenance — li scartiamo qui invece di
            # portarli in intermediates_before[0], che nessun candidate
            # legge mai.
            intermediates_before.append(pending if visible_nodes else [])
            visible_nodes.append(node)
            pending = []
        else:
            pending.append(node)

    return visible_nodes, intermediates_before
