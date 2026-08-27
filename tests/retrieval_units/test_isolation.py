"""
M5.1 — Tests for spec section 11/14-S: zero dependency on
tools.semantic_boundary / M4.2b. M5.1 may only reuse stable M4.2a
graph/projection/text utilities.
"""

import sys
from pathlib import Path

import tools.retrieval_units.hashing  # noqa: F401
import tools.retrieval_units.models  # noqa: F401
import tools.retrieval_units.projection  # noqa: F401

_PACKAGE_DIR = Path(tools.retrieval_units.projection.__file__).resolve().parent


def test_no_semantic_boundary_module_is_imported():
    assert not any(name.startswith("tools.semantic_boundary") for name in sys.modules)


def test_no_semantic_boundary_import_in_package_source():
    # Import statements only — prose/docstrings may legitimately mention
    # the non-goal by name.
    for path in sorted(_PACKAGE_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for line in source.splitlines():
            if "import" not in line or line.strip().startswith("#"):
                continue
            assert "semantic_boundary" not in line, f"{path.name}: {line!r}"
            assert "SemanticJudge" not in line, f"{path.name}: {line!r}"


def test_m51_reuses_shared_input_selection_helper():
    # The current-path message-node selection policy must live in exactly
    # one place (M4.2a) — M5.1 binds the very same function object, never
    # a re-implementation of the predicate.
    from tools.episodes.boundary_candidates import select_current_path_message_nodes

    assert (
        tools.retrieval_units.projection.select_current_path_message_nodes
        is select_current_path_message_nodes
    )
    # And the predicate's field names appear nowhere in M5.1 source.
    for path in sorted(_PACKAGE_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "is_technical_root" not in source, path.name
        assert "is_current_path" not in source, path.name


def test_reused_episode_modules_are_limited_to_stable_m42a_utilities():
    # Imports from tools.episodes are allowed only for the stable M4.2a
    # graph/projection/text/models utilities and the node-indexing helper
    # in boundary_candidates — never scoring/markers/lexical/timegap
    # (M4.2a evidence logic) and never anything M4.2b.
    source = (_PACKAGE_DIR / "projection.py").read_text(encoding="utf-8")
    forbidden = (
        "from tools.episodes.scoring",
        "from tools.episodes.markers",
        "from tools.episodes.lexical",
        "from tools.episodes.timegap",
        "from tools.episodes.validation",
    )
    for snippet in forbidden:
        assert snippet not in source
