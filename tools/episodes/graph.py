"""
M4.2a — Ricostruzione del grafo del current path a partire dai nodi ACNF.

Ricostruisce l'ordine canonico dei messaggi per una conversazione
percorrendo la catena di parent_id da conversation.current_node_id fino
alla technical root, per poi invertirla. I timestamp non vengono mai usati
per l'ordinamento — sono una feature, non una fonte d'ordine (vedi
docs/M4.2A_DETERMINISTIC_BOUNDARY_CANDIDATES.md, sezione 6).

Le anomalie strutturali (current node mancante, parent dangling, ciclo)
vengono registrate come diagnostica e mai sollevate come eccezione — è il
chiamante a decidere cosa, se qualcosa, può ancora essere recuperato per
quella conversazione.
"""

from typing import Any, Dict, List, Optional, Tuple

from .models import Anomaly


def reconstruct_current_path(
    conversation_id: str,
    current_node_id: Optional[str],
    nodes_by_id: Dict[str, Dict[str, Any]],
) -> Tuple[List[str], List[Anomaly]]:
    """
    Restituisce (ordered_node_ids, anomalies).

    ordered_node_ids è la catena root-to-current_node_id, in ordine
    canonico (dal più vecchio). nodes_by_id mappa node_id -> dict del nodo
    ACNF grezzo, già limitato a questa singola conversazione (node_id è
    univoco solo all'interno di una conversazione, non globalmente).
    """
    anomalies: List[Anomaly] = []

    if not current_node_id:
        anomalies.append(
            Anomaly(
                "missing_current_node",
                conversation_id,
                None,
                "Conversation has no current_node_id",
            )
        )
        return [], anomalies

    if current_node_id not in nodes_by_id:
        anomalies.append(
            Anomaly(
                "missing_current_node",
                conversation_id,
                current_node_id,
                "current_node_id does not reference any node present in nodes.jsonl for this conversation",
            )
        )
        return [], anomalies

    chain: List[str] = []
    visited = set()
    node_id: Optional[str] = current_node_id

    while node_id is not None:
        if node_id in visited:
            anomalies.append(
                Anomaly(
                    "current_path_cycle",
                    conversation_id,
                    node_id,
                    "Cycle detected while walking the current path via parent_id",
                )
            )
            break
        visited.add(node_id)

        node = nodes_by_id.get(node_id)
        if node is None:
            anomalies.append(
                Anomaly(
                    "dangling_parent",
                    conversation_id,
                    node_id,
                    "current path references a node id not present in nodes.jsonl for this conversation",
                )
            )
            break

        chain.append(node_id)
        node_id = node.get("parent_id")

    chain.reverse()
    return chain, anomalies
