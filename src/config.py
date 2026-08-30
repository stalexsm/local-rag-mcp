# Configuration for Company Knowledge Base Assistant

from pathlib import Path

# Directory of this file: src/. Config paths below are anchored here so the
# app resolves them identically no matter which working directory it is
# launched from (the MCP server may be started from anywhere).
SRC_DIR = Path(__file__).resolve().parent


def resolve_path(value: str | Path) -> str:
    """Resolve a config path against src/ unless it is already absolute."""
    value = Path(value)
    return str(value if value.is_absolute() else SRC_DIR / value)


# Document directory - update this to point to your company documentation
# (a relative value is resolved against src/, the directory of this file)
DOCUMENTS_DIR = resolve_path("./docs")

# Chunking configuration
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100

# Embedding model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# FAISS index paths (relative to src directory)
FAISS_INDEX_PATH = "index.faiss"
CHUNKS_PATH = "chunks.pkl"

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:0.6b"

# RAG retrieval configuration
TOP_K = 5

# Hybrid search (FTS/BM25 in parallel with vector search, RRF merge)
# Kill-switch: False restores the legacy vector-only top-TOP_K behavior.
HYBRID_SEARCH = True
# Candidates each retriever returns before the RRF merge
CANDIDATE_POOL_SIZE = 20
# RRF constant: larger k flattens rank differences between retrievers
RRF_K = 60
