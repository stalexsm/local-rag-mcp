import pickle
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import faiss
import requests
from sentence_transformers import SentenceTransformer

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CANDIDATE_POOL_SIZE,
    CHUNKS_PATH,
    EMBEDDING_MODEL,
    FAISS_INDEX_PATH,
    HYBRID_SEARCH,
    OLLAMA_MODEL,
    OLLAMA_URL,
    QUERY_EXPANSION,
    RRF_K,
    TOP_K,
)
from rag.expansion import expand_query
from rag.fts import build_fts_index, fts_search
from rag.merge import rrf_merge

model = SentenceTransformer(EMBEDDING_MODEL)

# Global variables for index and chunks
index = None
chunks = []
# In-memory BM25 index over `chunks` (ADR-0002); None while chunks are empty.
bm25_index = None


def _load_chunks(chunks_path):
    """Load chunks and rebuild the in-memory BM25 index from them."""
    global chunks, bm25_index
    with open(chunks_path, "rb") as f:
        chunks = pickle.load(f)
    # ADR-0002: BM25 is built in memory from the loaded chunk set, so it
    # cannot drift from the FAISS index and creates no third artifact.
    bm25_index = build_fts_index(chunks)


def _ensure_index_exists():
    """Ensure FAISS index exists, build it if it doesn't."""
    global index, chunks

    # Resolve paths relative to src directory
    src_dir = Path(__file__).parent.parent
    index_path = src_dir / FAISS_INDEX_PATH
    chunks_path = src_dir / CHUNKS_PATH

    # Check if index exists
    if index_path.exists() and chunks_path.exists():
        try:
            index = faiss.read_index(str(index_path))
            _load_chunks(chunks_path)
            return True
        except Exception as e:
            print(f"⚠️  Warning: Error loading existing index: {e}")
            print("Rebuilding index...")

    # Index doesn't exist or failed to load, build it
    print("📦 Index not found. Building index from documents...")
    try:
        from rag.build_index import build_index

        build_index()

        # Load the newly created index
        if index_path.exists() and chunks_path.exists():
            index = faiss.read_index(str(index_path))
            _load_chunks(chunks_path)
            print("✅ Index built and loaded successfully")
            return True
        else:
            print("❌ Failed to build index. No documents found or error occurred.")
            from config import DOCUMENTS_DIR

            print(f"   Check that documents exist in: {DOCUMENTS_DIR}")
            return False
    except Exception as e:
        print(f"❌ Error building index: {e}")
        import traceback

        traceback.print_exc()
        return False


# Initialize index on module load
_ensure_index_exists()


def _positions_to_chunks(positions: list[int]) -> list[dict]:
    """Map chunk positions from a ranking onto the loaded chunk list."""
    return [chunks[pos] for pos in positions]


def _vector_positions(query: str, n: int) -> list[int]:
    """Vector retriever: FAISS top-n candidates as positional chunk indices."""
    if index is None:
        return []
    q_emb = model.encode([query])
    faiss.normalize_L2(q_emb)
    scores, ids = index.search(q_emb, n)
    return [int(i) for i in ids[0] if i != -1]


def _fts_positions(query: str) -> list[int]:
    """FTS retriever: BM25 candidates as positional chunk indices."""
    if bm25_index is None:
        return []
    return fts_search(bm25_index, query, CANDIDATE_POOL_SIZE)


def retrieve(query: str, verbose: bool = False):
    """Retrieve relevant chunks for a query.

    Hybrid mode (default): query expansion first, then vector and FTS
    retrievers run in parallel (ADR-0003), their candidate pools fuse via
    RRF, and the final TOP_K is taken from the merged ranking. Keywords
    feed the FTS retriever only; the vector retriever keeps the original
    question (keywords blur its embedding). A retriever failure degrades
    to the other one, an expansion failure to the bare question; a query
    never fails because of search.
    """
    # Ensure index exists before retrieving (may build it as a side effect).
    if index is None or len(chunks) == 0:
        _ensure_index_exists()

    if index is None or len(chunks) == 0:
        return []

    if not HYBRID_SEARCH:
        # Kill-switch: legacy vector-only top-TOP_K behavior. Expansion is
        # skipped too — the vector retriever ignores keywords anyway.
        return _positions_to_chunks(_vector_positions(query, TOP_K))

    # Query Expansion: keywords for the FTS retriever only. Any expansion
    # failure yields [] — the FTS query stays the bare question.
    if QUERY_EXPANSION:
        keywords = expand_query(query)
        if verbose:
            if keywords:
                print(f"🔑 Extracted keywords: {', '.join(keywords)}")
            else:
                print("🔑 No keywords extracted; FTS searches the question only")
    else:
        keywords = []
        if verbose:
            print("🔑 Query expansion disabled; FTS searches the question only")

    fts_query = " ".join([query, *keywords])
    if verbose:
        print(f"🔎 FTS searches: {fts_query!r}")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_vector_positions, query, CANDIDATE_POOL_SIZE),
            executor.submit(_fts_positions, fts_query),
        ]

    rankings: list[list[int]] = []
    for future in futures:
        try:
            rankings.append(future.result())
        except Exception as e:
            # Fallback: the failed retriever drops out of the merge.
            print(f"⚠️  Retriever failed ({type(e).__name__}: {e}); merging the survivor")

    merged_positions = rrf_merge(rankings, RRF_K)[:TOP_K]
    return _positions_to_chunks(merged_positions)


def build_prompt(query, contexts):
    """Build prompt with retrieved context."""
    if not contexts:
        return f"""
<role>You are a helpful assistant that answers questions about company information.</role>
<instructions>Answer the question based on your general knowledge. If you don't know, say so.</instructions>

<query>
{query}
</query>

<assistant>
"""

    context_text = "\n\n".join(f"[Source: {c['source']}]\n{c['text']}" for c in contexts)

    return f"""
<role>You are a helpful assistant that answers questions about company information.</role>
<instructions>Answer the question ONLY based on the context provided below. If the answer is not in the context, say "I don't have that information in the knowledge base."</instructions>

<context>
{context_text}
</context>

<query>
{query}
</query>

<assistant>
"""


def ask_llm(prompt):
    """Query Ollama LLM."""
    response = requests.post(
        OLLAMA_URL, json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    )
    return response.json()["response"]


def ask(query: str):
    """Answer a question using RAG."""
    contexts = retrieve(query)
    prompt = build_prompt(query, contexts)
    return ask_llm(prompt), contexts


if __name__ == "__main__":
    while True:
        q = input("\n❓ Question: ")
        if q.lower() in {"exit", "quit"}:
            break
        print("\n🤖 Answer:\n")
        answer, sources = ask(q)
        print(answer)
        if sources:
            print("\n📚 Sources:")
            for src in sources:
                print(f"  - {src['source']}")
