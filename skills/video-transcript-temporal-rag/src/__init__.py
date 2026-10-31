"""
ClipForge Video Intelligence - Standalone Temporal RAG Skill for Agensi.io
"""
from .skill import VideoIntelligenceSkill
from .models import NormalizedTranscript, SkillResponse, CitationItem, EvidenceChunk
from .normalizer import TranscriptNormalizer
from .storage import InMemoryTranscriptStore

__version__ = "1.0.0"
__all__ = [
    "VideoIntelligenceSkill",
    "NormalizedTranscript",
    "SkillResponse",
    "CitationItem",
    "EvidenceChunk",
    "TranscriptNormalizer",
    "InMemoryTranscriptStore"
]
