"""
M4.2a — Shared synthetic ACNF fixture builders for the boundary-candidate
engine tests. All data here is synthetic; no real conversation content.

These build raw dicts shaped like conversations.jsonl / nodes.jsonl
records (as tools.episodes.boundary_candidates reads them), not
tools.chatgpt dataclass instances — M4.2a only ever consumes the ACNF
JSONL shape, never the normalizer's Python objects.
"""

from typing import Any, Dict, List, Optional


def make_conversation(conversation_id: str, current_node_id: Optional[str]) -> Dict[str, Any]:
    return {"conversation_id": conversation_id, "current_node_id": current_node_id}


def make_node(
    conversation_id: str,
    node_id: str,
    parent_id: Optional[str],
    *,
    has_message: bool = True,
    role: Optional[str] = "user",
    created_at: Optional[float] = None,
    content_type: Optional[str] = "text",
    text_parts: Optional[List[str]] = None,
    content: Any = None,
    is_technical_root: bool = False,
    is_current_path: bool = True,
    message_id: Optional[str] = None,
) -> Dict[str, Any]:
    if content is None and text_parts is not None:
        content = {"content_type": content_type, "parts": text_parts}
    return {
        "conversation_id": conversation_id,
        "node_id": node_id,
        "parent_id": parent_id,
        "message_id": message_id if message_id is not None else (f"m-{node_id}" if has_message else None),
        "has_message": has_message,
        "role": role if has_message else None,
        "created_at": created_at,
        "content_type": content_type if has_message else None,
        "content": content,
        "is_technical_root": is_technical_root,
        "is_current_path": is_current_path,
    }


def linear_conversation(conversation_id: str, message_count: int, base_time: float = 0.0) -> Dict[str, Any]:
    """
    A linear conversation: technical root -> message_1 -> ... -> message_N,
    alternating user/assistant roles, ascending timestamps 1 second apart.
    Returns {"conversation": ..., "nodes": [...]}.
    """
    nodes = [
        make_node(
            conversation_id,
            "root",
            None,
            has_message=False,
            is_technical_root=True,
            content_type=None,
        )
    ]
    parent = "root"
    for i in range(1, message_count + 1):
        node_id = f"n{i}"
        role = "user" if i % 2 == 1 else "assistant"
        nodes.append(
            make_node(
                conversation_id,
                node_id,
                parent,
                role=role,
                created_at=base_time + i,
                text_parts=[f"message {i}"],
            )
        )
        parent = node_id

    current_node_id = f"n{message_count}" if message_count > 0 else "root"
    conversation = make_conversation(conversation_id, current_node_id)
    return {"conversation": conversation, "nodes": nodes}


def chain_conversation(conversation_id: str, node_specs: List[Dict[str, Any]], base_time: float = 0.0) -> Dict[str, Any]:
    """
    Build a linear technical-root -> n1 -> n2 -> ... conversation from an
    explicit ordered list of node specs, for tests that need mixed
    visible/non-visible content types along the current path (e.g. RC2
    dialogue timeline projection). Each spec is a dict of make_node
    kwargs, minus conversation_id/node_id/parent_id/created_at which are
    assigned automatically (created_at ascending, 1 second apart, unless
    a spec explicitly overrides it). Returns {"conversation": ..., "nodes": [...]}.
    """
    nodes = [
        make_node(
            conversation_id,
            "root",
            None,
            has_message=False,
            is_technical_root=True,
            content_type=None,
        )
    ]
    parent = "root"
    for i, spec in enumerate(node_specs, start=1):
        node_id = spec.get("node_id", f"n{i}")
        kwargs = dict(spec)
        kwargs.pop("node_id", None)
        kwargs.setdefault("created_at", base_time + i)
        nodes.append(make_node(conversation_id, node_id, parent, **kwargs))
        parent = node_id

    current_node_id = nodes[-1]["node_id"] if len(nodes) > 1 else "root"
    conversation = make_conversation(conversation_id, current_node_id)
    return {"conversation": conversation, "nodes": nodes}
