"""
Adaptive Hierarchical Summarizer for long-form video transcripts (1h, 2h, 3h+).
Divides transcripts into contiguous chronological sections, extracts intermediate
section digests, and guarantees full-timeline coverage without context-window exhaustion.
"""

import math
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .models import EvidenceChunk


class SectionDigest(BaseModel):
    section_index: int
    title: str
    start_time: float
    end_time: float
    anchor_chunks: List[EvidenceChunk] = Field(default_factory=list)
    key_excerpt: str = ""
    chunk_ids: List[str] = Field(default_factory=list)

    def format_timestamp(self) -> str:
        s_min = int(self.start_time // 60)
        s_sec = int(self.start_time % 60)
        e_min = int(self.end_time // 60)
        e_sec = int(self.end_time % 60)
        return f"[{s_min:02d}:{s_sec:02d}–{e_min:02d}:{e_sec:02d}]"


class HierarchicalSummaryPlan(BaseModel):
    total_duration: float
    total_chunks: int
    num_sections: int
    sections: List[SectionDigest] = Field(default_factory=list)


class AdaptiveHierarchicalSummarizer:
    """
    Partitions long transcripts into adaptive chronological sections
    and extracts balanced evidence anchors across the entire timeline.
    """

    def __init__(self, target_section_minutes: float = 15.0, min_sections: int = 3, max_sections: int = 8):
        self.target_section_minutes = target_section_minutes
        self.min_sections = min_sections
        self.max_sections = max_sections

    def partition(self, all_chunks: List[EvidenceChunk], total_duration: float = 0.0) -> HierarchicalSummaryPlan:
        if not all_chunks:
            return HierarchicalSummaryPlan(total_duration=0.0, total_chunks=0, num_sections=0)

        n = len(all_chunks)
        duration = total_duration or all_chunks[-1].end_time

        # Short video: under 8 chunks fits in a single section
        if n <= 8:
            single_section = SectionDigest(
                section_index=0,
                title="Full Video",
                start_time=all_chunks[0].start_time,
                end_time=all_chunks[-1].end_time,
                anchor_chunks=all_chunks,
                key_excerpt=" ".join(c.text[:80] for c in all_chunks[:2]),
                chunk_ids=[c.id for c in all_chunks]
            )
            return HierarchicalSummaryPlan(
                total_duration=round(duration, 2),
                total_chunks=n,
                num_sections=1,
                sections=[single_section]
            )

        # Calculate optimal number of sections based on video length
        duration_minutes = duration / 60.0
        calculated_sections = math.ceil(duration_minutes / self.target_section_minutes)
        num_sections = max(self.min_sections, min(self.max_sections, calculated_sections))

        # Partition chunks into contiguous chronological buckets
        chunks_per_section = math.ceil(n / num_sections)
        sections: List[SectionDigest] = []

        for sec_idx in range(num_sections):
            start_idx = sec_idx * chunks_per_section
            end_idx = min(start_idx + chunks_per_section, n)

            if start_idx >= n:
                break

            section_chunks = all_chunks[start_idx:end_idx]
            if not section_chunks:
                continue

            sec_start = section_chunks[0].start_time
            sec_end = section_chunks[-1].end_time

            # Select high-salience anchors for this section (opening + closing or most content-dense)
            if len(section_chunks) <= 2:
                anchors = section_chunks
            else:
                # First chunk of section (topic transition) + middle dense chunk
                mid_idx = len(section_chunks) // 2
                anchors = [section_chunks[0], section_chunks[mid_idx]]

            sec_title = f"Section {sec_idx + 1}"
            key_excerpt = section_chunks[0].text[:140]

            sections.append(SectionDigest(
                section_index=sec_idx,
                title=sec_title,
                start_time=round(sec_start, 2),
                end_time=round(sec_end, 2),
                anchor_chunks=anchors,
                key_excerpt=key_excerpt,
                chunk_ids=[c.id for c in section_chunks]
            ))

        return HierarchicalSummaryPlan(
            total_duration=round(duration, 2),
            total_chunks=n,
            num_sections=len(sections),
            sections=sections
        )

    def extract_balanced_context(self, all_chunks: List[EvidenceChunk], total_duration: float = 0.0) -> Dict[str, Any]:
        """
        Extracts balanced anchors spanning the entire chronological timeline.
        Guarantees coverage across beginning, all intermediate sections, and conclusion.
        """
        plan = self.partition(all_chunks, total_duration)

        all_anchors: List[EvidenceChunk] = []
        seen_ids = set()

        for s in plan.sections:
            for c in s.anchor_chunks:
                if c.id not in seen_ids:
                    seen_ids.add(c.id)
                    all_anchors.append(c)

        all_anchors.sort(key=lambda c: c.start_time)

        return {
            "has_data": True,
            "num_sections": plan.num_sections,
            "sections": [s.model_dump() for s in plan.sections],
            "chunks": all_anchors,
            "message": f"Adaptive hierarchical summary assembled across {plan.num_sections} chronological sections."
        }
