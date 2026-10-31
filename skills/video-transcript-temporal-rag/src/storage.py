"""
Standalone Transcript Storage Adapter.
Provides zero-dependency in-memory and persistent SQLite storage options,
completely decoupled from the main ClipForge application database.
"""

import sqlite3
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from .models import NormalizedTranscript, EvidenceChunk
from .chunker import TranscriptChunker
from .hierarchical import AdaptiveHierarchicalSummarizer
from .search.lexical import LexicalSearcher
from .search.semantic import SemanticSearcher
from .search.fusion import reciprocal_rank_fusion, expand_chunk_context


class BaseTranscriptStore(ABC):
    """Abstract interface for transcript storage and chunk indexing."""

    @abstractmethod
    def load_transcript(self, transcript: NormalizedTranscript) -> List[EvidenceChunk]:
        """Loads and chunks a transcript into storage."""
        pass

    @abstractmethod
    def get_all_chunks(self, video_id: str) -> List[EvidenceChunk]:
        """Retrieves all indexed chunks for a video, ordered chronologically."""
        pass

    @abstractmethod
    def search_lexical(self, query: str, video_id: str, top_k: int = 5) -> List[EvidenceChunk]:
        """Performs BM25 lexical keyword retrieval."""
        pass

    @abstractmethod
    def search_hybrid(self, query: str, video_id: str, top_k: int = 5) -> List[EvidenceChunk]:
        """Performs hybrid lexical-semantic retrieval."""
        pass

    @abstractmethod
    def get_summary_context(self, video_id: str) -> Dict[str, Any]:
        """Assembles whole-video balanced sample chunks (opening, middle, conclusion)."""
        pass

    @abstractmethod
    def get_chunks_around_timestamp(self, video_id: str, target_seconds: float, window_seconds: float = 45.0) -> List[EvidenceChunk]:
        """Retrieves chunks covering or nearest to a target timestamp."""
        pass


class InMemoryTranscriptStore(BaseTranscriptStore):
    """
    Lightning-fast ephemeral in-memory storage.
    Ideal for serverless execution and single-run Agensi calls.
    Zero disk footprint, zero heavy database dependencies.
    """

    def __init__(self, chunker: Optional[TranscriptChunker] = None):
        self.chunker = chunker or TranscriptChunker()
        self.lexical_searcher = LexicalSearcher()
        self.semantic_searcher = SemanticSearcher()
        self.hierarchical_summarizer = AdaptiveHierarchicalSummarizer()
        self.transcripts: Dict[str, NormalizedTranscript] = {}
        self.chunks_by_video: Dict[str, List[EvidenceChunk]] = {}

    def load_transcript(self, transcript: NormalizedTranscript) -> List[EvidenceChunk]:
        self.transcripts[transcript.video_id] = transcript
        chunks = self.chunker.chunk(transcript)
        self.chunks_by_video[transcript.video_id] = chunks

        # Attempt semantic indexing if ChromaDB is available
        self.semantic_searcher.index(chunks)
        return chunks

    def get_all_chunks(self, video_id: str) -> List[EvidenceChunk]:
        return list(self.chunks_by_video.get(video_id, []))

    def search_lexical(self, query: str, video_id: str, top_k: int = 5) -> List[EvidenceChunk]:
        chunks = self.get_all_chunks(video_id)
        return self.lexical_searcher.search(query, chunks, top_k=top_k)

    def search_hybrid(self, query: str, video_id: str, top_k: int = 5) -> List[EvidenceChunk]:
        chunks = self.get_all_chunks(video_id)
        if not chunks:
            return []

        lex_hits = self.lexical_searcher.search(query, chunks, top_k=top_k * 2)

        if self.semantic_searcher.available:
            sem_hits = self.semantic_searcher.search(query, top_k=top_k * 2)
            if sem_hits:
                fused = reciprocal_rank_fusion([lex_hits, sem_hits], weights=[0.45, 0.55], top_n=top_k)
                return expand_chunk_context(chunks, fused, window_chunks=1)

        # Pure lexical with context expansion
        return expand_chunk_context(chunks, lex_hits[:top_k], window_chunks=1)

    def get_summary_context(self, video_id: str) -> Dict[str, Any]:
        all_chunks = self.get_all_chunks(video_id)
        transcript = self.transcripts.get(video_id)

        if not all_chunks:
            return {
                "has_data": False,
                "video_title": transcript.title if transcript else "Video",
                "duration": transcript.duration if transcript else 0.0,
                "chunks": [],
                "num_sections": 0,
                "sections": [],
                "message": "No transcript chunks available for this video."
            }

        duration = transcript.duration if transcript else (all_chunks[-1].end_time if all_chunks else 0.0)
        bundle = self.hierarchical_summarizer.extract_balanced_context(all_chunks, duration)
        bundle["video_title"] = transcript.title if transcript else "Video"
        bundle["duration"] = duration
        return bundle

    def get_chunks_around_timestamp(self, video_id: str, target_seconds: float, window_seconds: float = 45.0) -> List[EvidenceChunk]:
        all_chunks = self.get_all_chunks(video_id)
        if not all_chunks:
            return []

        min_t = target_seconds - window_seconds
        max_t = target_seconds + window_seconds

        matching: List[EvidenceChunk] = []
        for c in all_chunks:
            if c.start_time <= max_t and c.end_time >= min_t:
                chunk_copy = c.model_copy()
                mid = (c.start_time + c.end_time) / 2.0
                chunk_copy.score = round(max(0.1, 1.0 - (abs(mid - target_seconds) / max(window_seconds, 1.0)) * 0.5), 4)
                matching.append(chunk_copy)

        matching.sort(key=lambda x: abs(((x.start_time + x.end_time) / 2.0) - target_seconds))
        return matching[:5]
