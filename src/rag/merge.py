"""RRF (Reciprocal Rank Fusion) merge of retriever rankings.

Fusion works on ranks, not raw scores: vector similarity and BM25 scores
are incompatible scales, so only positions are fused, with equal weights.
"""


def rrf_merge(rankings: list[list[int]], k: int) -> list[int]:
    """Merge ranked lists of chunk positions into one best-first ranking.

    Each ranking holds positional chunk indices, best first. A chunk's
    score is the sum over rankings of 1 / (k + rank), rank starting at 1
    (equal weights); duplicates merge by chunk position. Ties resolve to
    the earliest first appearance, so the result is deterministic.
    """
    scores: dict[int, float] = {}
    first_seen: dict[int, int] = {}
    for ranking in rankings:
        for rank, pos in enumerate(ranking, start=1):
            scores[pos] = scores.get(pos, 0.0) + 1.0 / (k + rank)
            first_seen.setdefault(pos, len(first_seen))
    return sorted(scores, key=lambda pos: (-scores[pos], first_seen[pos]))
