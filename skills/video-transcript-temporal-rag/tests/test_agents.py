"""
Unit tests for the 6 specialized Video QA agents.
"""

import sys
import unittest
from pathlib import Path

# Ensure skill root is in sys.path
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from src.models import VideoQAState, EvidenceChunk, QueryPlan, VerificationResult
from src.storage import InMemoryTranscriptStore
from src.normalizer import TranscriptNormalizer
from src.llm.client import LLMClient

from src.agents.planner import QueryPlannerAgent, normalize_query
from src.agents.retrieval import RetrievalAgent
from src.agents.timeline import TimelineAgent
from src.agents.verification import EvidenceVerificationAgent
from src.agents.synthesis import AnswerSynthesisAgent
from src.agents.guardrail import SafetyGuardrailAgent
from src.agents.coordinator import ReActCoordinator

class TestSixAgents(unittest.TestCase):

    def setUp(self):
        self.store = InMemoryTranscriptStore()
        sample_data = {
            "title": "Industrial History",
            "duration": 300.0,
            "segments": [
                {"id": 0, "start": 0.0, "end": 60.0, "text": "In 1950, reconstruction began with industrial planning."},
                {"id": 1, "start": 61.0, "end": 150.0, "text": "Next, the automobile and electronics sectors grew rapidly with Toyota and Sony."},
                {"id": 2, "start": 151.0, "end": 240.0, "text": "High speed train lines and infrastructure like Shinkansen were constructed."},
                {"id": 3, "start": 241.0, "end": 300.0, "text": "Finally, the bubble economy burst, concluding this major economic transformation."}
            ]
        }
        transcript = TranscriptNormalizer.normalize(sample_data, video_id="hist_vid")
        self.store.load_transcript(transcript)
        self.llm = LLMClient(provider="mock", allow_mock=True)

    def test_agent1_planner_normalization(self):
        planner = QueryPlannerAgent()

        state1 = VideoQAState(query="what video about", video_id="hist_vid")
        res1 = planner.run(state1)
        self.assertEqual(res1.plan.intent, "WHOLE_VIDEO_SUMMARY")
        self.assertEqual(res1.plan.normalized_query, "What is this video about?")

        state2 = VideoQAState(query="give me a summary", video_id="hist_vid")
        res2 = planner.run(state2)
        self.assertEqual(res2.plan.intent, "WHOLE_VIDEO_SUMMARY")

        state3 = VideoQAState(query="main points?", video_id="hist_vid")
        res3 = planner.run(state3)
        self.assertEqual(res3.plan.intent, "WHOLE_VIDEO_SUMMARY")

        state4 = VideoQAState(query="what happened after industrial planning?", video_id="hist_vid")
        res4 = planner.run(state4)
        self.assertEqual(res4.plan.intent, "TIMELINE_RECONSTRUCTION")
        self.assertEqual(res4.plan.temporal_marker, "after")

    def test_agent2_retrieval(self):
        planner = QueryPlannerAgent()
        retriever = RetrievalAgent(store=self.store)

        state = VideoQAState(query="what video about", video_id="hist_vid")
        state = planner.run(state)
        state = retriever.run(state)
        self.assertTrue(len(state.retrieved_chunks) > 0)
        self.assertFalse(state.retrieved_chunks[0].is_diagnostic)

    def test_agent3_timeline(self):
        timeline_agent = TimelineAgent(store=self.store)
        chunks = [
            EvidenceChunk(id="c2", chunk_index=2, text="Later", start_time=150.0, end_time=200.0),
            EvidenceChunk(id="c1", chunk_index=1, text="Earlier", start_time=50.0, end_time=100.0)
        ]
        state = VideoQAState(query="test", video_id="hist_vid", retrieved_chunks=chunks)
        state = timeline_agent.run(state)
        self.assertEqual(state.retrieved_chunks[0].id, "c1")
        self.assertEqual(state.retrieved_chunks[1].id, "c2")

    def test_agent4_verification(self):
        verifier = EvidenceVerificationAgent()
        planner = QueryPlannerAgent()

        state_summary = VideoQAState(query="what video about", video_id="hist_vid")
        state_summary = planner.run(state_summary)
        state_summary.retrieved_chunks = [
            EvidenceChunk(id="c1", chunk_index=0, text="General overview text", start_time=0.0, end_time=10.0)
        ]
        state_summary = verifier.run(state_summary)
        self.assertTrue(state_summary.verification.supported)
        self.assertEqual(state_summary.verification.confidence, 0.95)

        state_unsupported = VideoQAState(query="What did they say about dinosaurs and jurassic park?", video_id="hist_vid")
        state_unsupported = planner.run(state_unsupported)
        state_unsupported.retrieved_chunks = [
            EvidenceChunk(id="c1", chunk_index=0, text="Automobile industrial growth Toyota Sony", start_time=0.0, end_time=10.0)
        ]
        state_unsupported = verifier.run(state_unsupported)
        self.assertFalse(state_unsupported.verification.supported)
        self.assertEqual(state_unsupported.verification.confidence, 0.0)

    def test_agent5_synthesis(self):
        synthesizer = AnswerSynthesisAgent(llm_client=self.llm)
        planner = QueryPlannerAgent()

        state = VideoQAState(query="what video about", video_id="hist_vid")
        state = planner.run(state)
        state.retrieved_chunks = [
            EvidenceChunk(id="c1", chunk_index=0, text="Industrial growth in Japan", start_time=0.0, end_time=50.0)
        ]
        state.verification = VerificationResult(supported=True, confidence=0.95)
        state = synthesizer.run(state)
        self.assertTrue(len(state.draft_answer) > 0)
        self.assertTrue(len(state.citations) > 0)

    def test_agent6_guardrail_rejection(self):
        guardrail = SafetyGuardrailAgent()
        state = VideoQAState(query="What about aliens?", video_id="hist_vid")
        state.verification = VerificationResult(supported=False, confidence=0.0, reason="No concepts found")
        state.draft_answer = "Some hallucinated answer"
        state = guardrail.run(state)
        self.assertEqual(state.final_answer, "I couldn't find sufficient evidence for that in this video.")

    def test_complete_react_coordinator(self):
        coord = ReActCoordinator(store=self.store, llm_client=self.llm)
        res = coord.process(query="what video about", video_id="hist_vid", video_title="Industrial History", duration=300.0)
        self.assertEqual(res.classified_intent, "WHOLE_VIDEO_SUMMARY")
        self.assertTrue(res.confidence >= 0.8)
        self.assertIn("Main Points", res.answer)
        self.assertTrue(len(res.audit_trail) >= 5)

if __name__ == "__main__":
    unittest.main()
