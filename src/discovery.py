"""Shared discovery of knowledge-base documents.

The RAG ingest pipeline and the MCP server tools need the same filter:
files under DOCUMENTS_DIR with a supported extension (case-insensitive).
This module is intentionally dependency-light (pathlib + config only),
so importing it does not pull pypdf/python-docx into the MCP server
process via the `rag` package.
"""

import sys
from collections.abc import Iterator
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent))
from config import DOCUMENTS_DIR

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


def is_supported_file(path: Path) -> bool:
    """True if path is a file with a supported extension (case-insensitive)."""
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def iter_supported_files(base_dir: str | Path = DOCUMENTS_DIR) -> Iterator[Path]:
    """Yield every file under base_dir with a supported extension."""
    base = Path(base_dir)
    if not base.exists():
        return
    for path in base.rglob("*"):
        if is_supported_file(path):
            yield path
