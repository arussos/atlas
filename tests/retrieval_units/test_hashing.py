"""
M5.1 — Tests for identity vs content versioning (spec section 14: O, P, R)
and for the canonical hashing helpers.
"""

from tests.episodes.fixtures import linear_conversation
from tools.retrieval_units.hashing import (
    canonical_hash,
    compute_content_hash,
    compute_retrieval_unit_id,
)
from tools.retrieval_units.projection import generate_retrieval_units


def generate(conversations, nodes, acquisition_id="acq-1", acnf_schema_version="0.1"):
    return generate_retrieval_units(
        conversations,
        nodes,
        acquisition_id=acquisition_id,
        acnf_schema_version=acnf_schema_version,
    )


# ---------------------------------------------------------------------------
# O. Same logical unit -> same retrieval_unit_id
# ---------------------------------------------------------------------------


def test_same_logical_unit_yields_same_retrieval_unit_id():
    fixture = linear_conversation("conv-o", 9)
    units_1, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    units_2, _, _, _ = generate([fixture["conversation"]], fixture["nodes"])
    assert [u.retrieval_unit_id for u in units_1] == [u.retrieval_unit_id for u in units_2]
    # Distinct windows have distinct identities.
    assert len({u.retrieval_unit_id for u in units_1}) == len(units_1)


def test_retrieval_unit_id_is_stable_across_acquisitions():
    # Same conversation/node identity in a later export (different
    # acquisition) -> same stable identity, different provenance fields.
    fixture = linear_conversation("conv-o2", 6)
    units_1, _, _, _ = generate([fixture["conversation"]], fixture["nodes"], acquisition_id="acq-1")
    units_2, _, _, _ = generate([fixture["conversation"]], fixture["nodes"], acquisition_id="acq-2")
    assert units_1[0].retrieval_unit_id == units_2[0].retrieval_unit_id
    assert units_1[0].acquisition_id == "acq-1"
    assert units_2[0].acquisition_id == "acq-2"


# ---------------------------------------------------------------------------
# P. Same identity, changed source content -> same id, different content_hash
# ---------------------------------------------------------------------------


def test_changed_source_text_changes_content_hash_but_not_identity():
    fixture_1 = linear_conversation("conv-p", 3)
    fixture_2 = linear_conversation("conv-p", 3)
    # Same node identity, edited content (as a later export would show it).
    fixture_2["nodes"][1]["content"] = {"content_type": "text", "parts": ["message 1 EDITED"]}
    units_1, _, _, _ = generate([fixture_1["conversation"]], fixture_1["nodes"])
    units_2, _, _, _ = generate([fixture_2["conversation"]], fixture_2["nodes"])
    assert units_1[0].retrieval_unit_id == units_2[0].retrieval_unit_id
    assert units_1[0].content_hash != units_2[0].content_hash


def test_changed_node_hash_alone_changes_content_hash_but_not_identity():
    # Even when the extracted text is unchanged, a changed ACNF node_hash
    # (e.g. asset_refs or non-part content changed at source) must be
    # detected by content_hash while identity stays stable.
    fixture_1 = linear_conversation("conv-p2", 3)
    fixture_2 = linear_conversation("conv-p2", 3)
    for node in fixture_1["nodes"]:
        node["node_hash"] = "hash-A"
    for node in fixture_2["nodes"]:
        node["node_hash"] = "hash-A"
    fixture_2["nodes"][1]["node_hash"] = "hash-B"
    units_1, _, _, _ = generate([fixture_1["conversation"]], fixture_1["nodes"])
    units_2, _, _, _ = generate([fixture_2["conversation"]], fixture_2["nodes"])
    assert units_1[0].retrieval_unit_id == units_2[0].retrieval_unit_id
    assert units_1[0].text == units_2[0].text
    assert units_1[0].content_hash != units_2[0].content_hash


# ---------------------------------------------------------------------------
# R. projection_version participates in identity
# ---------------------------------------------------------------------------


def test_projection_version_participates_in_identity():
    id_v01 = compute_retrieval_unit_id(
        projection_version="0.1", conversation_id="c", node_ids=["n1", "n2"]
    )
    id_v02 = compute_retrieval_unit_id(
        projection_version="0.2", conversation_id="c", node_ids=["n1", "n2"]
    )
    assert id_v01 != id_v02


def test_identity_depends_on_conversation_and_ordered_node_ids():
    base = compute_retrieval_unit_id(projection_version="0.1", conversation_id="c", node_ids=["n1", "n2"])
    other_conv = compute_retrieval_unit_id(projection_version="0.1", conversation_id="d", node_ids=["n1", "n2"])
    other_order = compute_retrieval_unit_id(projection_version="0.1", conversation_id="c", node_ids=["n2", "n1"])
    assert base != other_conv
    assert base != other_order


def test_content_hash_covers_intermediate_provenance():
    hash_1 = compute_content_hash(
        retrieval_unit_id="id", text="t", node_hashes=["a"], intermediate_node_ids=[]
    )
    hash_2 = compute_content_hash(
        retrieval_unit_id="id", text="t", node_hashes=["a"], intermediate_node_ids=["tech"]
    )
    assert hash_1 != hash_2


def test_canonical_hash_is_deterministic_and_key_order_independent():
    assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})
