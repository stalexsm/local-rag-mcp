"""FTS seam (rag.fts): in-memory BM25 over a caller-passed chunk list.

The contract under test: the index is built from exactly the chunks the
caller passes (no third artifact, ADR-0002), tokenization is lowercase
word-splitting shared by corpus and query, filename tokens boost their
document's chunks, and ranking follows literal matches — chunks with no
overlap are not candidates.
"""

from rank_bm25 import BM25Okapi

from rag.fts import build_fts_index, fts_search, tokenize

# Hand-made chunks in the pipeline shape (the fields the seam reads from
# chunk_documents output). Plain data — no mocks, no generated artifacts.
CHUNKS = [
    {"text": "Employees may work remotely two days per week.", "source": "docs/handbook.txt"},
    {"text": "Vacation requests go through the HR portal.", "source": "docs/vacation.txt"},
    {"text": "The office cafeteria opens at eight in the morning.", "source": "docs/office.txt"},
]


def test_tokenize_lowercases_and_splits_on_words() -> None:
    assert tokenize("Vacation Policy-2024: отпуск!") == ["vacation", "policy", "2024", "отпуск"]


def test_index_is_built_from_passed_chunks() -> None:
    assert isinstance(build_fts_index(CHUNKS), BM25Okapi)


def test_verbatim_match_ranks_first_and_zero_overlap_drops_out() -> None:
    """Chunks matching the query words literally; non-matching ones score <= 0."""
    assert fts_search(build_fts_index(CHUNKS), "vacation HR portal", top_n=3) == [1]


def test_search_tokenizes_query_like_the_corpus() -> None:
    """Case and punctuation in the query do not hide literal matches."""
    assert fts_search(build_fts_index(CHUNKS), "  Cafeteria OPENS at EIGHT!", top_n=3) == [2]


def test_filename_tokens_surface_chunks_the_body_lacks() -> None:
    """Query tokens found only in the source path still elect that chunk.

    "handbook" occurs solely in chunk 0's file name — filename tokens are
    part of its document, so the chunk is the only candidate.
    """
    assert fts_search(build_fts_index(CHUNKS), "handbook", top_n=3) == [0]


def test_filename_tokens_rank_equal_bodies() -> None:
    """Between equal bodies the chunk whose file name matches ranks first.

    Five chunks so "leave" stays a positive-IDF term (BM25 needs it in
    fewer than half the documents): two siblings share the body, one also
    carries the token in its file name, three are unrelated filler.
    """
    chunks = [
        {"text": "Annual leave accrues monthly.", "source": "docs/payroll.txt"},
        {"text": "Annual leave accrues monthly.", "source": "docs/leave.txt"},
        {"text": "The office cafeteria opens at eight.", "source": "docs/office.txt"},
        {"text": "Parking permits renew each January.", "source": "docs/parking.txt"},
        {"text": "Security badges are required at all times.", "source": "docs/security.txt"},
    ]
    assert fts_search(build_fts_index(chunks), "leave", top_n=5) == [1, 0]


def test_top_n_limits_best_first_results() -> None:
    assert fts_search(build_fts_index(CHUNKS), "vacation hr portal cafeteria", top_n=2) == [1, 2]


def test_query_without_matches_returns_no_candidates() -> None:
    assert fts_search(build_fts_index(CHUNKS), "quantum garlic", top_n=3) == []
