"""
Agent 2: RetrievalAgent
Executes targeted retrieval strategies based on the QueryPlanner's directives.
Routes to whole-video summary context assembly, timestamp neighborhood, or hybrid RAG.
"""

from typing import Dict, Any, List
from .base import BaseAgent
from ..models import VideoQAState, EvidenceChunk
from ..storage import BaseTranscriptStore


class RetrievalAgent(BaseAgent):
    """Agent 2: Retrieves candidate evidence chunks according to the plan."""

    def __init__(self, store: BaseTranscriptStore):
        super().__init__(name="RetrievalAgent")
        self.store = store

    def run(self, state: VideoQAState) -> VideoQAState:
        if not state.plan:
            state.log(f"[{self.name}] No plan found. Skipping retrieval.")
            return state

        intent = state.plan.intent
        vid = state.video_id
        target_ts = state.plan.target_timestamp
        sub_queries = state.plan.sub_queries

        collected: Dict[str, EvidenceChunk] = {}

        # Strategy A: Whole-Video Summary Context Assembly
        if intent == "WHOLE_VIDEO_SUMMARY":
            summary_bundle = self.store.get_summary_context(vid)
            chunks = summary_bundle.get("chunks", [])
            if not chunks:
                state.retrieved_chunks = [
                    EvidenceChunk(
                        id="missing_index",
                        text="The transcript for this video has not been loaded or indexed yet.",
                        start_time=0.0,
                        end_time=0.0,
                        video_id=vid,
                        is_diagnostic=True
                    )
                ]
                state.log(f"[{self.name}] Whole-video summary requested, but transcript is empty/not indexed.")
                return state

            state.retrieved_chunks = chunks
            state.log(f"[{self.name}] Assembled {len(chunks)} balanced chunks across opening, middle, and conclusion.")
            return state

        # Strategy B: Timestamp Specific Search
        if intent == "TIMESTAMP_SEARCH" and target_ts is not None:
            ts_chunks = self.store.get_chunks_around_timestamp(vid, target_ts)
            for c in ts_chunks:
                collected[c.id] = c

        # Strategy C: Comparative Analysis (beginning + ending)
        if intent == "COMPARATIVE_ANALYSIS":
            all_chunks = self.store.get_all_chunks(vid)
            if all_chunks:
                for c in all_chunks[:2]:
                    collected[c.id] = c
                for c in all_chunks[-2:]:
                    collected[c.id] = c

        # Strategy D: Sub-query Hybrid Search
        for sq in sub_queries:
            hits = self.store.search_hybrid(sq, vid, top_k=4)
            for h in hits:
                cid = h.id
                if cid not in collected:
                    collected[cid] = h
                else:
                    collected[cid].score = max(collected[cid].score, h.score)

        # Sort by score descending and take top 6
        ranked = sorted(collected.values(), key=lambda c: c.score, reverse=True)
        final_subset = ranked[:6]

        # Chronological sort for coherent presentation
        final_subset.sort(key=lambda c: c.start_time)
        state.retrieved_chunks = final_subset
        state.log(f"[{self.name}] Retrieved {len(final_subset)} relevant evidence chunks.")
        return state
