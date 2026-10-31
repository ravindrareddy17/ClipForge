"""
Agent 3: TimelineAgent
Validates chronological sequence, verifies narrative flow,
and resolves temporal milestone queries ('what happened after X', 'prior to Y').
"""

from typing import List
from .base import BaseAgent
from ..models import VideoQAState, EvidenceChunk
from ..storage import BaseTranscriptStore


class TimelineAgent(BaseAgent):
    """Agent 3: Ensures temporal accuracy and chronological consistency."""

    def __init__(self, store: BaseTranscriptStore):
        super().__init__(name="TimelineAgent")
        self.store = store

    def run(self, state: VideoQAState) -> VideoQAState:
        chunks = state.retrieved_chunks
        if not chunks:
            state.timeline_adjusted = True
            return state

        # Check for diagnostic chunks
        if any(c.is_diagnostic for c in chunks):
            state.timeline_adjusted = True
            return state

        plan = state.plan
        marker = plan.temporal_marker if plan else None

        # Always enforce chronological baseline
        chunks.sort(key=lambda c: c.start_time)

        if marker == "after":
            # Target milestone was likely the first match
            milestone_start = chunks[0].start_time
            all_chunks = self.store.get_all_chunks(state.video_id)
            if all_chunks:
                after_chunks = [c for c in all_chunks if c.start_time >= milestone_start]
                if after_chunks:
                    chunks = after_chunks[:5]
                    state.log(f"[{self.name}] Resolved 'after' temporal constraint from {milestone_start}s onwards.")

        elif marker == "before":
            milestone_start = chunks[-1].start_time
            all_chunks = self.store.get_all_chunks(state.video_id)
            if all_chunks:
                before_chunks = [c for c in all_chunks if c.end_time <= milestone_start]
                if before_chunks:
                    chunks = before_chunks[-5:]
                    state.log(f"[{self.name}] Resolved 'before' temporal constraint up to {milestone_start}s.")

        chunks.sort(key=lambda c: c.start_time)
        state.retrieved_chunks = chunks
        state.timeline_adjusted = True
        state.log(f"[{self.name}] Finalized chronological timeline across {len(chunks)} chunks.")
        return state
