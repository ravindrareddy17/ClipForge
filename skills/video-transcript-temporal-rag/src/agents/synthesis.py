"""
Agent 5: AnswerSynthesisAgent
Synthesizes structured, evidence-grounded answers with verifiable inline timestamp citations [MM:SS].
"""

import re
from typing import List, Dict, Any, Optional

from .base import BaseAgent
from ..models import VideoQAState, EvidenceChunk, CitationItem
from ..llm.client import LLMClient


class AnswerSynthesisAgent(BaseAgent):
    """Agent 5: Drafts structured, timestamp-cited markdown responses."""

    def __init__(self, llm_client: LLMClient):
        super().__init__(name="AnswerSynthesisAgent")
        self.llm = llm_client

    def run(self, state: VideoQAState) -> VideoQAState:
        # Check if verification failed completely
        if state.verification and not state.verification.supported and state.verification.confidence == 0.0:
            state.draft_answer = "I couldn't find sufficient evidence for that in this video."
            state.log(f"[{self.name}] Unsupported query; set draft answer to default refusal.")
            return state

        chunks = state.retrieved_chunks
        if not chunks:
            state.draft_answer = "I couldn't find sufficient evidence for that in this video."
            state.log(f"[{self.name}] No chunks available for synthesis.")
            return state

        intent = state.plan.intent if state.plan else "FACTUAL_LOOKUP"

        # Build context string
        context_parts = []
        for c in chunks:
            ts_str = c.format_timestamp()
            context_parts.append(f"{ts_str} {c.text}")
        context_str = "\n\n".join(context_parts)

        system_prompt = (
            "You are a video intelligence assistant. Answer questions based ONLY on the provided video transcript evidence. "
            "You MUST cite relevant timestamps in [MM:SS] format for every key point or factual claim. "
            "Never invent timestamps or facts not present in the context. If the answer cannot be found in the evidence, "
            "state clearly that the information is not discussed."
        )

        if intent == "WHOLE_VIDEO_SUMMARY":
            user_prompt = f"""VIDEO CONTEXT:
Video Title: {state.video_title}
Duration: {state.duration}s

<transcript_evidence>
{context_str}
</transcript_evidence>

USER REQUEST:
{state.normalized_query}

INSTRUCTIONS:
Provide a structured whole-video overview using this exact format:
1. A concise 1-2 sentence overview summarizing what the video is about.
2. 'Main Points:' followed by 3 to 7 numbered key points tracing the narrative progression across the entire timeline (covering opening, intermediate developments, and conclusion). Each point MUST include relevant timestamp citations [MM:SS] or [MM:SS–MM:SS].
3. 'Conclusion:' a brief summary of the final thoughts or takeaway [MM:SS].

Ground every point strictly in the transcript evidence. Do not omit middle-section developments."""
        else:
            user_prompt = f"""VIDEO CONTEXT:
Video Title: {state.video_title}

<transcript_evidence>
{context_str}
</transcript_evidence>

USER QUESTION:
{state.normalized_query}

INSTRUCTIONS:
Answer the question directly and factually based ONLY on the evidence above.
Include inline timestamp citations [MM:SS] for every factual statement.
Keep your response concise, clear, and fully grounded."""

        try:
            draft = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1500,
                temperature=0.2
            )
            state.draft_answer = draft
            usage = self.llm.get_last_usage()
            if usage:
                p_tok = usage.get("prompt_tokens", 0)
                c_tok = usage.get("completion_tokens", 0)
                t_tok = usage.get("total_tokens", 0)
                state.log(f"[{self.name}] Synthesized response ({len(draft)} chars). Tokens: {p_tok} prompt + {c_tok} completion = {t_tok} total.")
            else:
                state.log(f"[{self.name}] Synthesized response ({len(draft)} chars).")
        except Exception as e:
            state.draft_answer = f"Error generating answer: {e}"
            if state.verification:
                state.verification.confidence = 0.0
                state.verification.supported = False
            state.log(f"[{self.name}] LLM generation error: {e}")

        # Extract citations
        self._extract_citations(state)
        return state

    def _extract_citations(self, state: VideoQAState) -> None:
        """Parses [MM:SS] or [MM:SS-MM:SS] from the draft and matches to retrieved chunks."""
        answer = state.draft_answer
        ts_pattern = re.compile(r"\[(\d{1,2}:\d{2})(?:[–-](\d{1,2}:\d{2}))?\]")
        matches = ts_pattern.findall(answer)

        citations: List[CitationItem] = []
        seen_st = set()

        for m in matches:
            start_str = m[0]
            end_str = m[1] if m[1] else start_str
            # Parse to seconds
            p_st = start_str.split(":")
            sec_st = float(p_st[0]) * 60 + float(p_st[1])
            p_et = end_str.split(":")
            sec_et = float(p_et[0]) * 60 + float(p_et[1])

            if sec_st in seen_st:
                continue
            seen_st.add(sec_st)

            # Find best matching chunk by temporal overlap
            matched_chunk = None
            best_overlap = -1.0
            for c in state.retrieved_chunks:
                overlap_start = max(c.start_time, sec_st)
                overlap_end = min(c.end_time, sec_et)
                overlap = overlap_end - overlap_start
                if overlap > best_overlap:
                    best_overlap = overlap
                    matched_chunk = c

            if (not matched_chunk or best_overlap < 0) and state.retrieved_chunks:
                matched_chunk = min(state.retrieved_chunks, key=lambda c: abs(c.start_time - sec_st))

            if matched_chunk:
                chunk_text = matched_chunk.text
                if len(chunk_text) > 160:
                    # Look for query tokens in chunk_text to center excerpt around the relevant point
                    kw_match = None
                    if state.normalized_query:
                        words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", state.normalized_query.lower())
                                 if w not in ("what", "when", "where", "which", "about", "tell", "show", "speaker", "video", "did", "does", "the", "and", "for", "with", "have", "has")]
                        # Prioritize longer, specific terms
                        words.sort(key=len, reverse=True)
                        for w in words:
                            idx = chunk_text.lower().find(w)
                            if idx != -1:
                                kw_match = idx
                                break

                    if kw_match is not None:
                        start_pos = max(0, kw_match - 40)
                        end_pos = min(len(chunk_text), kw_match + 140)
                        prefix = "..." if start_pos > 0 else ""
                        suffix = "..." if end_pos < len(chunk_text) else ""
                        excerpt = f"{prefix}{chunk_text[start_pos:end_pos].strip()}{suffix}"
                    else:
                        excerpt = chunk_text[:150] + "..."
                else:
                    excerpt = chunk_text
            else:
                excerpt = "Video timestamp reference"
            disp_ts = f"[{start_str}–{end_str}]" if start_str != end_str else f"[{start_str}]"

            citations.append(CitationItem(
                timestamp=disp_ts,
                start_seconds=sec_st,
                end_seconds=sec_et,
                text_excerpt=excerpt,
                relevance_score=matched_chunk.score if matched_chunk else 0.8
            ))

        # Ensure citations are always sorted chronologically by timeline start
        citations.sort(key=lambda c: c.start_seconds)
        state.citations = citations
