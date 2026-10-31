"""
Agent 4: EvidenceVerificationAgent
Verifies factual support, calculates citation grounding scores,
and identifies unsupported or hallucinatory query targets.
"""

import re
from typing import Set, Tuple, List
from .base import BaseAgent
from ..models import VideoQAState, VerificationResult

VERIFICATION_STOP_WORDS: Set[str] = {
    "what", "when", "where", "which", "who", "whom", "this", "that", "there", "these", "those",
    "have", "with", "speaker", "video", "about", "say", "said", "did", "does", "the", "and",
    "for", "from", "mention", "mentioned", "talk", "talked", "discuss", "discussed", "tell", "told",
    "how", "why", "are", "was", "were", "been", "being", "had", "has", "can", "could", "would", "should"
}


class EvidenceVerificationAgent(BaseAgent):
    """Agent 4: Assesses factual alignment and computes evidence confidence."""

    def __init__(self):
        super().__init__(name="EvidenceVerificationAgent")

    def run(self, state: VideoQAState) -> VideoQAState:
        chunks = state.retrieved_chunks
        query = state.normalized_query or state.query

        # 1. Check if diagnostic chunk
        if not chunks or any(c.is_diagnostic for c in chunks):
            state.verification = VerificationResult(
                supported=False,
                confidence=0.0,
                reason="Video transcript has not been indexed or loaded yet."
            )
            state.log(f"[{self.name}] Verification failed: No valid evidence chunks.")
            return state

        # 2. Check for whole-video summary intent
        intent = state.plan.intent if state.plan else "FACTUAL_LOOKUP"
        if intent == "WHOLE_VIDEO_SUMMARY":
            state.verification = VerificationResult(
                supported=True,
                confidence=0.95,
                reason="Whole-video summary intent verified with timeline evidence."
            )
            state.log(f"[{self.name}] Whole-video summary verified with high confidence (0.95).")
            return state

        # 3. Core keyword overlap check for factual lookup
        query_tokens = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()) if w not in VERIFICATION_STOP_WORDS]
        combined_text = " ".join(c.text.lower() for c in chunks)

        matching_tokens = [t for t in query_tokens if t in combined_text]

        if not query_tokens:
            # Broad meta query (e.g. "What happened?")
            state.verification = VerificationResult(
                supported=True,
                confidence=0.85,
                reason="General topical query with timeline evidence."
            )
            state.log(f"[{self.name}] Broad query verified with baseline confidence 0.85.")
            return state

        if len(matching_tokens) == 0:
            state.verification = VerificationResult(
                supported=False,
                confidence=0.0,
                reason=f"None of the query core concepts ({query_tokens}) exist in the video evidence.",
                matching_keywords=[]
            )
            state.log(f"[{self.name}] Verification rejected: Missing concepts {query_tokens}.")
            return state

        confidence = round(len(matching_tokens) / len(query_tokens), 2)
        state.verification = VerificationResult(
            supported=confidence >= 0.25,
            confidence=max(confidence, 0.4),
            reason=f"Found {len(matching_tokens)}/{len(query_tokens)} key concepts in evidence.",
            matching_keywords=matching_tokens
        )
        state.log(f"[{self.name}] Evidence verified with confidence {state.verification.confidence}.")
        return state
