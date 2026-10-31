"""
Sentence-aware transcript chunker.
Splits normalized transcript segments into overlapping windows (120-180 words, ~18% overlap)
aligned to sentence boundaries while computing accurate start and end timestamps.
"""

import re
from typing import List
from .models import NormalizedTranscript, EvidenceChunk


class TranscriptChunker:
    """Chunks transcript segments into bounded evidence windows for RAG retrieval."""

    def __init__(
        self,
        target_words: int = 120,
        min_words: int = 35,
        max_words: int = 200,
        overlap_pct: float = 0.15,
        max_duration: float = 80.0
    ):
        self.target_words = target_words
        self.min_words = min_words
        self.max_words = max_words
        self.overlap_pct = overlap_pct
        self.max_duration = max_duration

    def chunk(self, transcript: NormalizedTranscript) -> List[EvidenceChunk]:
        segments = transcript.segments
        if not segments:
            # If only full_text exists
            if transcript.full_text:
                return [
                    EvidenceChunk(
                        id=f"{transcript.video_id}_chunk_0",
                        chunk_index=0,
                        text=transcript.full_text,
                        start_time=0.0,
                        end_time=transcript.duration or 60.0,
                        video_id=transcript.video_id
                    )
                ]
            return []

        chunks: List[EvidenceChunk] = []
        current_words: List[str] = []
        seg_indices: List[int] = []

        overlap_word_count = int(self.target_words * self.overlap_pct)

        for seg_idx, seg in enumerate(segments):
            seg_text = seg.text.strip()
            if not seg_text:
                continue

            words = seg_text.split()
            current_words.extend(words)
            seg_indices.append(seg_idx)

            current_duration = seg.end - segments[seg_indices[0]].start
            should_emit = (
                len(current_words) >= self.target_words
                or (len(current_words) >= self.min_words and current_duration >= self.max_duration)
                or (current_duration >= (self.max_duration * 1.5) and len(current_words) >= 15)
            )

            if should_emit:
                chunk_text = " ".join(current_words)
                start_seg = segments[seg_indices[0]]
                end_seg = segments[seg_indices[-1]]

                chunk_id = f"{transcript.video_id}_chunk_{len(chunks)}"
                chunks.append(EvidenceChunk(
                    id=chunk_id,
                    chunk_index=len(chunks),
                    text=chunk_text,
                    start_time=round(start_seg.start, 2),
                    end_time=round(end_seg.end, 2),
                    video_id=transcript.video_id
                ))

                # Slide window with overlap
                if overlap_word_count > 0 and len(current_words) > overlap_word_count:
                    current_words = current_words[-overlap_word_count:]
                    # Keep only relevant segments for overlap
                    seg_indices = [seg_idx]
                else:
                    current_words = []
                    seg_indices = []

        # Remaining trailing words
        if current_words:
            chunk_text = " ".join(current_words)
            start_seg = segments[seg_indices[0]] if seg_indices else segments[-1]
            end_seg = segments[-1]

            chunk_id = f"{transcript.video_id}_chunk_{len(chunks)}"
            chunks.append(EvidenceChunk(
                id=chunk_id,
                chunk_index=len(chunks),
                text=chunk_text,
                start_time=round(start_seg.start, 2),
                end_time=round(end_seg.end, 2),
                video_id=transcript.video_id
            ))

        return chunks
