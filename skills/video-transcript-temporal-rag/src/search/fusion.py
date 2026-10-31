"""
Reciprocal Rank Fusion (RRF) and context expansion utilities.
Combines multiple ranked retrieval results and ensures contextual boundaries.
"""

from typing import List, Dict, Any, Optional
from ..models import EvidenceChunk


def reciprocal_rank_fusion(
    ranked_lists: List[List[EvidenceChunk]],
    weights: Optional[List[float]] = None,
    k: int = 60,
    top_n: int = 5
) -> List[EvidenceChunk]:
    """
    Merges multiple ranked lists of EvidenceChunks using Reciprocal Rank Fusion (RRF):
    RRF_score(chunk) = sum_over_lists( weight_i / (k + rank_i) )
    """
    if not ranked_lists:
        return []

    if len(ranked_lists) == 1:
        return ranked_lists[0][:top_n]

    if weights is None:
        weights = [1.0 / len(ranked_lists)] * len(ranked_lists)

    scores: Dict[str, float] = {}
    chunk_map: Dict[str, EvidenceChunk] = {}

    for list_idx, chunk_list in enumerate(ranked_lists):
        w = weights[list_idx]
        for rank, chunk in enumerate(chunk_list):
            cid = chunk.id
            if cid not in chunk_map:
                chunk_map[cid] = chunk.model_copy()
            # 1-based rank
            rrf_val = w / (k + (rank + 1))
            scores[cid] = scores.get(cid, 0.0) + rrf_val

    # Sort chunks by final RRF score
    sorted_cids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    results: List[EvidenceChunk] = []
    for cid in sorted_cids[:top_n]:
        c = chunk_map[cid]
        c.score = round(scores[cid], 5)
        results.append(c)

    return results


def expand_chunk_context(
    all_chunks: List[EvidenceChunk],
    seed_chunks: List[EvidenceChunk],
    window_chunks: int = 1
) -> List[EvidenceChunk]:
    """
    Expands high-relevance seed chunks by adding preceding and succeeding neighbor chunks
    within window_chunks distance to provide complete conversational context.
    """
    if not seed_chunks or not all_chunks:
        return seed_chunks

    index_to_chunk = {c.chunk_index: c for c in all_chunks}
    included_indices = set()

    for sc in seed_chunks:
        idx = sc.chunk_index
        for offset in range(-window_chunks, window_chunks + 1):
            target_idx = idx + offset
            if target_idx in index_to_chunk:
                included_indices.add(target_idx)

    expanded = [index_to_chunk[idx].model_copy() for idx in sorted(included_indices)]
    return expanded
