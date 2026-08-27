"""
M5.1 — ChatGPT Retrieval Unit Projection.

Deriva unità di retrieval deterministiche e model-independent dalla
memoria ChatGPT già normalizzata (ACNF v0.1, prodotto da M4.1),
riusando la Dialogue Timeline Projection di M4.2a
(tools/episodes/projection.py) come unica policy di visibilità:

    ACNF normalized conversation
        -> authoritative current-path ordering (tools/episodes/graph.py)
        -> visible dialogue projection (tools/episodes/projection.py)
        -> deterministic overlapping RetrievalUnit records
        -> JSONL

Fuori scope qui: Episode Builder, segmentazione semantica, embedding,
vector indexing, Qdrant, Open WebUI, retriever, reranker, LLM.
Nessuna dipendenza da tools.semantic_boundary / M4.2b.
ACNF resta la fonte di verità; RetrievalUnit.text è dato derivato.
Vedi docs/M5.1_CHATGPT_RETRIEVAL_UNITS.md.
"""
