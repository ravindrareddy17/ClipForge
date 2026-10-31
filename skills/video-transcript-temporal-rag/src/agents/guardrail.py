"""
Agent 6: SafetyGuardrailAgent
Enforces hallucination checks, boundary enforcement, honest refusals,
and diagnostic explanations.
"""

from .base import BaseAgent
from ..models import VideoQAState


class SafetyGuardrailAgent(BaseAgent):
    """Agent 6: Intercepts ungrounded claims, hallucinations, and out-of-scope queries."""

    def __init__(self):
        super().__init__(name="SafetyGuardrailAgent")

    def run(self, state: VideoQAState) -> VideoQAState:
        verification = state.verification
        draft = state.draft_answer

        # 1. Check for missing transcript diagnostic
        if state.retrieved_chunks and state.retrieved_chunks[0].is_diagnostic:
            state.final_answer = state.retrieved_chunks[0].text
            state.log(f"[{self.name}] Finalized with diagnostic indexing explanation.")
            return state

        # 2. Check for LLM generation error
        if draft.startswith("Error generating answer:"):
            state.final_answer = draft
            state.log(f"[{self.name}] Finalized with LLM provider error.")
            return state

        # 2. Check for verification rejection
        if verification and (not verification.supported or verification.confidence < 0.20):
            state.final_answer = "I couldn't find sufficient evidence for that in this video."
            state.log(f"[{self.name}] Guardrail intercepted: Insufficient evidence (confidence {verification.confidence}).")
            return state

        # 3. If draft answer already states insufficient evidence
        if "couldn't find" in draft.lower() or "not mentioned" in draft.lower():
            state.final_answer = draft
            state.citations = []  # Clear citations on negative refusal
            state.log(f"[{self.name}] Preserved model's explicit insufficient evidence statement.")
            return state

        # 4. Prune hallucinated citations exceeding video duration
        if state.duration > 0 and state.citations:
            valid_citations = []
            for c in state.citations:
                if c.start_seconds <= (state.duration + 5.0):
                    valid_citations.append(c)
                else:
                    state.log(f"[{self.name}] Pruned out-of-bounds citation {c.timestamp} ({c.start_seconds}s > video duration {state.duration}s).")
            state.citations = valid_citations

        # 5. Enforce timestamp citations if evidence is present and confidence is high
        if "[" not in draft and "]" not in draft and state.retrieved_chunks:
            # Append reference timestamp
            c0 = state.retrieved_chunks[0]
            draft += f"\n\n*Reference: {c0.format_timestamp()}*"
            state.log(f"[{self.name}] Appended fallback timestamp citation.")

        state.final_answer = draft
        state.log(f"[{self.name}] Answer passed safety verification.")
        return state
