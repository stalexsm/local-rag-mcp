"""FTS (BM25) over the loaded chunk set, in memory (ADR-0002).

The index is built from the same chunk list that backs the FAISS index at
search initialization, so a third on-disk artifact is never created and
rebuilding the index remains the only maintenance operation. Tokenization
is lowercase + split on word characters, no stemming — Russian morphology
is covered by the vector retriever inside the same merge.
"""

import re

from rank_bm25 import BM25Okapi

_WORD_RE = re.compile(r"\w+")


def tokenize(text: str) -> list[str]:
    """Lowercase text and split it into word tokens (no stemming)."""
    return _WORD_RE.findall(text.lower())


def build_fts_index(chunks) -> BM25Okapi:
    """Build an in-memory BM25 index from the passed chunk list.

    Tokens of the source path and file name are added to every chunk, so a
    query naming a document boosts that document's chunks even when the
    words do not occur in the chunk text.
    """
    corpus = [tokenize(chunk["text"]) + tokenize(chunk["source"]) for chunk in chunks]
    return BM25Okapi(corpus)


def fts_search(bm25_index: BM25Okapi, query: str, top_n: int) -> list[int]:
    """Rank chunks against the query text, best first, as positional indices.

    Pure function over the passed index and query. Chunks with no literal
    match (score <= 0) are not candidates.
    """
    scores = bm25_index.get_scores(tokenize(query))
    positives = [i for i in range(len(scores)) if scores[i] > 0]
    positives.sort(key=lambda i: scores[i], reverse=True)
    return positives[:top_n]
