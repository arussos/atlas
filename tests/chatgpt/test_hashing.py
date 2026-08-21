"""
M4.1 — Tests for tools/chatgpt/hashing.py

Covers: determinism, dict key ordering independence, Unicode stability,
content-change sensitivity, and exclusion of operational/derived fields
from content-identity hashes.
"""

from tools.chatgpt.hashing import (
    canonical_hash,
    canonical_json_bytes,
    compute_acquisition_id,
    compute_asset_hash,
    compute_conversation_hash,
    compute_node_hash,
)


# ---------------------------------------------------------------------------
# canonical_hash / canonical_json_bytes
# ---------------------------------------------------------------------------


def test_same_object_same_hash():
    obj = {"a": 1, "b": [1, 2, 3], "c": {"nested": True}}
    assert canonical_hash(obj) == canonical_hash(dict(obj))


def test_dict_key_ordering_does_not_alter_hash():
    obj_a = {"alpha": 1, "beta": 2, "gamma": 3}
    obj_b = {"gamma": 3, "alpha": 1, "beta": 2}
    assert canonical_hash(obj_a) == canonical_hash(obj_b)


def test_nested_dict_key_ordering_does_not_alter_hash():
    obj_a = {"outer": {"x": 1, "y": 2}, "list": [{"a": 1, "b": 2}]}
    obj_b = {"list": [{"b": 2, "a": 1}], "outer": {"y": 2, "x": 1}}
    assert canonical_hash(obj_a) == canonical_hash(obj_b)


def test_unicode_stable():
    obj = {"title": "Progetto ATLAS — città, perché, così"}
    h1 = canonical_hash(obj)
    h2 = canonical_hash(dict(obj))
    assert h1 == h2
    # non-ASCII must be preserved, not \u-escaped, in canonical bytes
    raw = canonical_json_bytes(obj)
    assert "città".encode("utf-8") in raw
    assert "\\u" not in raw.decode("utf-8")


def test_none_values_stable():
    obj_a = {"a": None, "b": 1}
    obj_b = {"b": 1, "a": None}
    assert canonical_hash(obj_a) == canonical_hash(obj_b)


def test_content_modification_changes_hash():
    obj_a = {"content": "hello"}
    obj_b = {"content": "hello world"}
    assert canonical_hash(obj_a) != canonical_hash(obj_b)


def test_list_order_matters_for_generic_canonical_hash():
    # canonical_hash itself does not reorder lists — only callers that
    # know list order is semantically irrelevant (e.g. asset_refs) sort
    # before calling it. This is exercised in compute_node_hash below.
    obj_a = {"items": [1, 2, 3]}
    obj_b = {"items": [3, 2, 1]}
    assert canonical_hash(obj_a) != canonical_hash(obj_b)


# ---------------------------------------------------------------------------
# compute_node_hash
# ---------------------------------------------------------------------------


def _base_node_kwargs(**overrides):
    kwargs = dict(
        conversation_id="conv-1",
        node_id="node-1",
        parent_id="node-0",
        message_id="msg-1",
        has_message=True,
        role="user",
        created_at=1700000000.0,
        content_type="text",
        content={"content_type": "text", "parts": ["hello"]},
        asset_refs=[],
    )
    kwargs.update(overrides)
    return kwargs


def test_node_hash_deterministic():
    kwargs = _base_node_kwargs()
    assert compute_node_hash(**kwargs) == compute_node_hash(**dict(kwargs))


def test_node_hash_changes_with_content():
    h1 = compute_node_hash(**_base_node_kwargs())
    h2 = compute_node_hash(**_base_node_kwargs(content={"content_type": "text", "parts": ["goodbye"]}))
    assert h1 != h2


def _ref(asset_id, pointer_uri="uri", content_type="image_asset_pointer"):
    return {"asset_id": asset_id, "pointer_uri": pointer_uri, "content_type": content_type}


def test_node_hash_asset_refs_order_independent():
    h1 = compute_node_hash(**_base_node_kwargs(asset_refs=[_ref("file-a"), _ref("file-b")]))
    h2 = compute_node_hash(**_base_node_kwargs(asset_refs=[_ref("file-b"), _ref("file-a")]))
    assert h1 == h2


def test_node_hash_sensitive_to_asset_ref_pointer_uri():
    # Two occurrences referencing the same asset_id via a different
    # pointer_uri must not hash identically — reference metadata is part
    # of node content identity.
    h1 = compute_node_hash(**_base_node_kwargs(asset_refs=[_ref("file-a", pointer_uri="file-service://file-a")]))
    h2 = compute_node_hash(**_base_node_kwargs(asset_refs=[_ref("file-a", pointer_uri="sediment://file-a")]))
    assert h1 != h2


def test_node_hash_sensitive_to_parent_id():
    h1 = compute_node_hash(**_base_node_kwargs(parent_id="node-0"))
    h2 = compute_node_hash(**_base_node_kwargs(parent_id="node-x"))
    assert h1 != h2


def test_node_hash_sensitive_to_has_message():
    # A malformed message object present but missing its own id has
    # message_id=None, same as a node with no message at all — has_message
    # must still make these distinguishable.
    h1 = compute_node_hash(**_base_node_kwargs(message_id=None, has_message=True))
    h2 = compute_node_hash(**_base_node_kwargs(message_id=None, has_message=False))
    assert h1 != h2


# ---------------------------------------------------------------------------
# compute_conversation_hash
# ---------------------------------------------------------------------------


def _base_conv_kwargs(**overrides):
    kwargs = dict(
        conversation_id="conv-1",
        source_id="conv-1",
        title="Test conversation",
        created_at=1700000000.0,
        updated_at=1700000100.0,
        current_node_id="node-2",
        default_model_slug="gpt-test",
        archived=False,
        starred=None,
        memory_scope=None,
        source_metadata={},
        node_hashes=[("node-1", "hash1"), ("node-2", "hash2")],
    )
    kwargs.update(overrides)
    return kwargs


def test_conversation_hash_deterministic():
    kwargs = _base_conv_kwargs()
    assert compute_conversation_hash(**kwargs) == compute_conversation_hash(**dict(kwargs))


def test_conversation_hash_node_hash_order_independent():
    h1 = compute_conversation_hash(**_base_conv_kwargs(node_hashes=[("node-1", "hash1"), ("node-2", "hash2")]))
    h2 = compute_conversation_hash(**_base_conv_kwargs(node_hashes=[("node-2", "hash2"), ("node-1", "hash1")]))
    assert h1 == h2


def test_conversation_hash_changes_when_node_hash_changes():
    h1 = compute_conversation_hash(**_base_conv_kwargs(node_hashes=[("node-1", "hash1")]))
    h2 = compute_conversation_hash(**_base_conv_kwargs(node_hashes=[("node-1", "hash1-modified")]))
    assert h1 != h2


def test_conversation_hash_sensitive_to_current_node_id():
    h1 = compute_conversation_hash(**_base_conv_kwargs(current_node_id="node-2"))
    h2 = compute_conversation_hash(**_base_conv_kwargs(current_node_id="node-1"))
    assert h1 != h2


def test_conversation_hash_sensitive_to_source_metadata():
    h1 = compute_conversation_hash(**_base_conv_kwargs(source_metadata={}))
    h2 = compute_conversation_hash(**_base_conv_kwargs(source_metadata={"conversation_template_id": "tmpl-1"}))
    assert h1 != h2


# ---------------------------------------------------------------------------
# compute_asset_hash
# ---------------------------------------------------------------------------


def _base_asset_kwargs(**overrides):
    kwargs = dict(
        asset_id="file-ABC123",
        physical_filename="file-ABC123.dat",
        original_filename="image.png",
        mime_type="image/png",
        size_bytes=1024,
        sha256="deadbeef",
        storage_kind="exported",
    )
    kwargs.update(overrides)
    return kwargs


def test_asset_hash_deterministic():
    kwargs = _base_asset_kwargs()
    assert compute_asset_hash(**kwargs) == compute_asset_hash(**dict(kwargs))


def test_asset_hash_changes_with_sha256():
    h1 = compute_asset_hash(**_base_asset_kwargs(sha256="aaa"))
    h2 = compute_asset_hash(**_base_asset_kwargs(sha256="bbb"))
    assert h1 != h2


def test_asset_hash_changes_with_storage_kind():
    # storage_kind is part of asset identity (exported vs. reference_only),
    # not provenance: two records that otherwise share every field must
    # still hash distinctly if their storage_kind differs.
    h1 = compute_asset_hash(**_base_asset_kwargs(storage_kind="exported"))
    h2 = compute_asset_hash(**_base_asset_kwargs(storage_kind="reference_only"))
    assert h1 != h2


def test_reference_only_asset_hash_deterministic_with_all_none_fields():
    kwargs = dict(
        asset_id="file_0000000098dc71f6889f91e3db3e2290",
        physical_filename=None,
        original_filename=None,
        mime_type=None,
        size_bytes=None,
        sha256=None,
        storage_kind="reference_only",
    )
    assert compute_asset_hash(**kwargs) == compute_asset_hash(**dict(kwargs))


def test_asset_hash_structurally_independent_of_message_provenance():
    # compute_asset_hash never accepts conversation/message identifiers,
    # nor per-reference pointer detail — the same physical asset must
    # hash identically regardless of which conversation/message
    # references it, or how any given occurrence described it.
    import inspect

    params = inspect.signature(compute_asset_hash).parameters
    assert "source_conversation_id" not in params
    assert "source_message_id" not in params
    assert "pointer_uri" not in params
    assert "source_type" not in params
    assert "content_type" not in params


# ---------------------------------------------------------------------------
# compute_acquisition_id — operational metadata exclusion
# ---------------------------------------------------------------------------


def test_acquisition_id_deterministic_for_same_source():
    id1 = compute_acquisition_id("sha-abc", "0.1")
    id2 = compute_acquisition_id("sha-abc", "0.1")
    assert id1 == id2


def test_acquisition_id_independent_of_normalization_timestamp():
    # compute_acquisition_id never accepts a timestamp — this test
    # documents that operational metadata (normalization wall-clock time)
    # structurally cannot influence the acquisition_id.
    import inspect

    params = inspect.signature(compute_acquisition_id).parameters
    assert "normalized_at" not in params
    assert "timestamp" not in params


def test_acquisition_id_changes_with_source_sha256():
    id1 = compute_acquisition_id("sha-abc", "0.1")
    id2 = compute_acquisition_id("sha-xyz", "0.1")
    assert id1 != id2
