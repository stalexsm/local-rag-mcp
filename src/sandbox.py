"""Knowledge-base sandbox: decide which file paths may be read.

Pure path logic consulted by the MCP server before opening any file. A
string-prefix check is not enough — the sibling directory "…/docs-evil"
starts with "…/docs" — so the decision compares resolved paths
structurally (Path.is_relative_to).
"""

from pathlib import Path

from config import DOCUMENTS_DIR


def is_within(file_path: str | Path, base_dir: str | Path) -> bool:
    """True if file_path resolves inside base_dir (siblings are excluded).

    Paths resolve non-strictly, so a not-yet-existing file inside the base
    is still recognized as inside; opening it fails later, outside the
    sandbox decision.
    """
    return Path(file_path).resolve().is_relative_to(Path(base_dir).resolve())


def is_within_documents(file_path: str | Path) -> bool:
    """Sandbox verdict against the configured documents directory."""
    return is_within(file_path, DOCUMENTS_DIR)
