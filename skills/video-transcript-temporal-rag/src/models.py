"""
Data models and typed schemas for the Video Transcript Temporal RAG skill.
Built with Pydantic v2.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class WordItem(BaseModel):
    word: str
    start: float
    end: float


class TranscriptSegment(BaseModel):
    id: Optional[int] = None
    start: float
    end: float
    text: str
    words: Optional[List[WordItem]] = None


class NormalizedTranscript(BaseModel):
    video_id: str = "video_default"
    title: str = "Video Transcript"
    duration: float = 0.0
    segments: List[TranscriptSegment] = Field(default_factory=list)
    full_text: str = ""


def format_timestamp(seconds: float) -> str:
    """Format seconds into MM:SS or HH:MM:SS."""
    total_sec = max(0, int(seconds))
    hrs = total_sec // 3600
    mins = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def format_time_range(start: float, end: float) -> str:
    """Format start and end seconds into a timestamp range [MM:SS-MM:SS]."""
    s_str = format_timestamp(start)
    e_str = format_timestamp(end)
    if s_str == e_str:
        return f"[{s_str}]"
    return f"[{s_str}–{e_str}]"


class EvidenceChunk(BaseModel):
    id: str
    chunk_index: int = 0
    text: str
    start_time: float = 0.0
    end_time: float = 0.0
    video_id: str = "video_default"
    score: float = 0.0
    topic: str = ""
    is_diagnostic: bool = False

    def format_timestamp(self) -> str:
        return format_time_range(self.start_time, self.end_time)


class CitationItem(BaseModel):
    timestamp: str
    start_seconds: float
    end_seconds: float
    text_excerpt: str
    relevance_score: float = 0.0


class QueryPlan(BaseModel):
    intent: str = "FACTUAL_LOOKUP"
    sub_queries: List[str] = Field(default_factory=list)
    temporal_marker: Optional[str] = None
    target_timestamp: Optional[float] = None
    original_query: str = ""
    normalized_query: str = ""


class VerificationResult(BaseModel):
    supported: bool = True
    confidence: float = 0.0
    reason: str = ""
    matching_keywords: List[str] = Field(default_factory=list)


class VideoQAState(BaseModel):
    query: str
    normalized_query: str = ""
    video_id: str = "video_default"
    video_title: str = "Video"
    duration: float = 0.0
    plan: Optional[QueryPlan] = None
    retrieved_chunks: List[EvidenceChunk] = Field(default_factory=list)
    timeline_adjusted: bool = False
    verification: Optional[VerificationResult] = None
    draft_answer: str = ""
    final_answer: str = ""
    citations: List[CitationItem] = Field(default_factory=list)
    audit_trail: List[str] = Field(default_factory=list)

    def log(self, message: str) -> None:
        self.audit_trail.append(message)


class SkillResponse(BaseModel):
    answer: str
    confidence: float
    classified_intent: str
    normalized_query: str
    citations: List[CitationItem] = Field(default_factory=list)
    audit_trail: List[str] = Field(default_factory=list)
