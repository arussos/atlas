"""Make the repository root importable so `tools.retrieval_units.*` and
`tests.episodes.fixtures` resolve regardless of how pytest is invoked
(plain `pytest`, `python3 -m pytest`, or from a different working
directory)."""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
