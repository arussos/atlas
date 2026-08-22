"""
M4.2a — Deterministic Boundary Candidate Engine.

Consuma ACNF v0.1 (conversations.jsonl, nodes.jsonl), prodotto a monte da
tools/chatgpt (M4.1), e produce record di feature candidate per gli
episode boundary. Questo package non legge dati OpenAI RAW export e non
importa nulla da tools.chatgpt — conosce solo la forma JSONL di ACNF.

Fuori scope qui (rimandato a M4.2b): la decisione finale SAME_EPISODE /
NEW_EPISODE / UNCERTAIN, qualsiasi inferenza LLM/embedding, e qualsiasi
estrazione semantica (decisioni, problemi, soluzioni, riassunti, progetti).
"""
