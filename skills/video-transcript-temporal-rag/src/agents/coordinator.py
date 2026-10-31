"""
ReActCoordinator: Orchestrates the sequential execution of the 6 specialized agents.
"""

from typing import Optional, Callable
from ..models import VideoQAState, SkillResponse
from ..storage import BaseTranscriptStore
from ..llm.client import LLMClient

from .planner import QueryPlannerAgent
from .retrieval import RetrievalAgent
from .timeline import TimelineAgent
from .verification import EvidenceVerificationAgent
from .synthesis import AnswerSynthesisAgent
from .guardrail import SafetyGuardrailAgent


class ReActCoordinator:
    """Manages state transitions across the 6 Video QA agents."""

    def __init__(self, store: BaseTranscriptStore, llm_client: LLMClient):
        self.store = store
        self.llm = llm_client

        # Instantiate agents
        self.planner = QueryPlannerAgent()
        self.retriever = RetrievalAgent(store=self.store)
        self.timeline_agent = TimelineAgent(store=self.store)
        self.verifier = EvidenceVerificationAgent()
        self.synthesizer = AnswerSynthesisAgent(llm_client=self.llm)
        self.guardrail = SafetyGuardrailAgent()

    def process(
        self,
        query: str,
        video_id: str = "video_default",
        video_title: str = "Video",
        duration: float = 0.0,
        status_callback: Optional[Callable[[str], None]] = None
    ) -> SkillResponse:
        """Executes the complete 6-Agent ReAct loop."""
        state = VideoQAState(
            query=query,
            video_id=video_id,
            video_title=video_title,
            duration=duration
        )

        def notify(msg: str):
            if status_callback:
                try:
                    status_callback(msg)
                except Exception:
                    pass

        # Step 1: Query Planning
        notify("Analyzing query & classifying intent...")
        state = self.planner.run(state)

        # Step 2: Retrieval
        notify("Retrieving evidence chunks...")
        state = self.retriever.run(state)

        # Step 3: Timeline Alignment
        notify("Resolving chronological timeline...")
        state = self.timeline_agent.run(state)

        # Step 4: Evidence Verification
        notify("Verifying factual evidence & confidence...")
        state = self.verifier.run(state)

        # Step 5: Answer Synthesis
        notify("Synthesizing grounded answer...")
        state = self.synthesizer.run(state)

        # Step 6: Safety Guardrails
        notify("Evaluating safety guardrails...")
        state = self.guardrail.run(state)

        confidence_val = state.verification.confidence if state.verification else 0.0
        intent_val = state.plan.intent if state.plan else "FACTUAL_LOOKUP"

        return SkillResponse(
            answer=state.final_answer,
            confidence=confidence_val,
            classified_intent=intent_val,
            normalized_query=state.normalized_query,
            citations=state.citations,
            audit_trail=state.audit_trail
        )
