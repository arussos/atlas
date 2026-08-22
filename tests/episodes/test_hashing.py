"""
M4.2a — Tests for tools/episodes/hashing.py

Covers determinism and independence from tools.chatgpt.hashing (M4.2a's
identity scheme must not be coupled to the OpenAI RAW normalizer).
"""

from tools.episodes.hashing import canonical_hash, compute_candidate_hash, compute_candidate_id


def test_candidate_id_deterministic():
    kwargs = dict(
        conversation_id="conv-1",
        before_node_id="n1",
        after_node_id="n2",
        feature_version="m4.2a-0.1",
    )
    assert compute_candidate_id(**kwargs) == compute_candidate_id(**dict(kwargs))


def test_candidate_id_changes_with_node_pair():
    base = dict(conversation_id="conv-1", before_node_id="n1", after_node_id="n2", feature_version="m4.2a-0.1")
    other = dict(base, after_node_id="n3")
    assert compute_candidate_id(**base) != compute_candidate_id(**other)


def test_candidate_id_changes_with_feature_version():
    base = dict(conversation_id="conv-1", before_node_id="n1", after_node_id="n2", feature_version="m4.2a-0.1")
    other = dict(base, feature_version="m4.2a-0.2")
    assert compute_candidate_id(**base) != compute_candidate_id(**other)


def test_candidate_id_is_not_a_random_uuid():
    import inspect

    # deterministic hash-based id — never depends on uuid module
    assert "uuid" not in inspect.getsource(compute_candidate_id)


def test_candidate_hash_deterministic():
    payload = {"a": 1, "b": [1, 2, 3]}
    assert compute_candidate_hash(payload) == compute_candidate_hash(dict(payload))


def test_candidate_hash_sensitive_to_content():
    h1 = compute_candidate_hash({"candidate_score": 0.5})
    h2 = compute_candidate_hash({"candidate_score": 0.6})
    assert h1 != h2


def test_module_does_not_import_tools_chatgpt():
    import ast
    import inspect

    import tools.episodes.hashing as hashing_mod

    tree = ast.parse(inspect.getsource(hashing_mod))
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert not any(name.startswith("tools.chatgpt") for name in imported_modules)


def test_canonical_hash_unicode_stable():
    obj = {"title": "Progetto ATLAS — città"}
    assert canonical_hash(obj) == canonical_hash(dict(obj))
