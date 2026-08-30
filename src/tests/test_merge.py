"""RRF merge seam (rag.merge.rrf_merge): ranks in, one fused ranking out.

The contract under test: fusion uses rank positions only — vector and BM25
scores never enter the merge (they live on incompatible scales) — with equal
weight per ranking, duplicate chunks merged into one entry, and
deterministic tie-breaking by earliest first appearance.
"""

from rag.merge import rrf_merge


def test_single_ranking_is_preserved() -> None:
    """One ranking fuses to itself: 1/(k+rank) strictly decreases with rank."""
    assert rrf_merge([[10, 20, 30]], k=60) == [10, 20, 30]


def test_consensus_chunk_ranks_first_and_all_chunks_survive() -> None:
    """A chunk ranked by both retrievers beats chunks ranked by one only.

    Expected order follows the documented formula: 2 = 1/61 + 1/61,
    1 = 1/61, 4 = 1/62, tie 3 = 5 = 1/63 resolved by first appearance.
    """
    assert rrf_merge([[1, 2, 3], [2, 4, 5]], k=60) == [2, 1, 4, 3, 5]


def test_duplicate_chunks_merge_into_one_entry() -> None:
    """A chunk present in several rankings appears exactly once in the merge."""
    merged = rrf_merge([[0, 1], [1, 2]], k=60)
    assert merged == [1, 0, 2]
    assert len(merged) == len(set(merged))


def test_equal_weights_and_deterministic_ties() -> None:
    """Rankings weigh equally: mirrored inputs score identically.

    The aggregate of 0 and 1 is the same (1/(k+1) + 1/(k+2) each), so the
    result is decided by first appearance — and is therefore deterministic.
    """
    assert rrf_merge([[0, 1], [1, 0]], k=60) == [0, 1]


def test_fusion_depends_only_on_ranks_not_score_scales() -> None:
    """Same rank structure fuses to the same order regardless of k.

    Vector similarity (0..1) and BM25 (unbounded positive) would order
    candidates differently; the merge never sees their scores, so the
    consensus-beats-singleton order is stable for any k.
    """
    vector, bm25 = [1, 2, 3], [2, 4, 5]
    assert rrf_merge([vector, bm25], k=1) == rrf_merge([vector, bm25], k=60)


def test_no_rankings_merge_to_empty() -> None:
    assert rrf_merge([], k=60) == []


def test_empty_ranking_drops_out_without_distorting_the_survivor() -> None:
    """Degradation: a failed retriever contributes nothing to the merge."""
    assert rrf_merge([[], [7, 8]], k=60) == [7, 8]
