"""
ClipForge AI V2 - Unit Tests for Video-Level Summary Intent & Query Normalization
Tests intent classification, informal query normalization, whole-video evidence assembly,
and follow-up detailed questioning.
"""

import sys
import os
import unittest

# Ensure backend package is accessible
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from clipforge_engine.video_qa_agents import (
    normalize_query, QueryPlannerAgent, RetrievalAgent,
    tool_assemble_video_summary_context, EvidenceVerificationAgent,
    run_video_qa_pipeline
)
from clipforge_engine.db import get_projects, get_videos


class TestVideoSummaryIntent(unittest.TestCase):

    def setUp(self):
        projects = get_projects()
        self.assertTrue(len(projects) > 0, "At least one project must exist in DB")
        self.project_id = projects[0]["id"]
        videos = get_videos(self.project_id)
        self.assertTrue(len(videos) > 0, "At least one video must exist in DB")
        self.video_id = videos[0]["id"]

    def test_01_query_normalization(self):
        """Verify that informal and fragmented queries are mapped to canonical forms."""
        test_cases = [
            ("what video about", "What is this video about?"),
            ("what is video about", "What is this video about?"),
            ("tell me about this video", "Tell me about this video."),
            ("summarize this video", "Summarize this video."),
            ("main points?", "What are the main points of this video?"),
            ("explain the video", "Explain the video."),
            ("give me an overview", "Give me an overview of this video."),
            ("what does this video discuss", "What does this video discuss?"),
            ("video about", "What is this video about?")
        ]
        for raw, expected in test_cases:
            canonical = normalize_query(raw)
            self.assertEqual(canonical, expected, f"Failed normalizing: {raw}")

    def test_02_intent_classification_variants(self):
        """Verify all requested summary variants enter VIDEO_SUMMARY intent."""
        summary_queries = [
            "what video about",
            "what is this video about",
            "what is the video about",
            "tell me about this video",
            "summarize this video",
            "give me a summary",
            "what are the main points",
            "explain the video",
            "give me an overview",
            "what does this video discuss",
            "what is discussed in this video",
            "main points?",
            "explain the video",
            "what video about?"
        ]
        planner = QueryPlannerAgent()
        for q in summary_queries:
            plan = planner.plan(q)
            self.assertEqual(
                plan.get("intent"),
                "video_summary",
                f"Query '{q}' should be classified as 'video_summary', got '{plan.get('intent')}'"
            )

    def test_03_detailed_questions_intent_routing(self):
        """Verify detailed and follow-up questions route to their appropriate specific intents."""
        planner = QueryPlannerAgent()

        # Factual query
        p1 = planner.plan("What did the speaker say about Japan's post-war economy?")
        self.assertEqual(p1["intent"], "factual_lookup")

        # Timestamp query
        p2 = planner.plan("When did the discussion about industrialization begin?")
        self.assertEqual(p2["intent"], "timestamp_search")

        # Chronology query
        p3 = planner.plan("What happened after that?")
        self.assertEqual(p3["intent"], "chronology")
        self.assertEqual(p3["temporal_marker"], "after")

        # Factual query
        p4 = planner.plan("Did the speaker mention exports?")
        self.assertEqual(p4["intent"], "factual_lookup")

    def test_04_whole_video_evidence_assembly(self):
        """Verify that whole-video summary tool gathers balanced chunks across duration."""
        bundle = tool_assemble_video_summary_context(self.project_id, self.video_id)
        self.assertTrue(bundle.get("has_data"), "Should have data for indexed video")
        chunks = bundle.get("chunks", [])
        self.assertTrue(len(chunks) >= 3, f"Expected at least 3 sampled chunks, got {len(chunks)}")
        
        # Verify chronological order
        start_times = [c["metadata"]["start_time"] for c in chunks]
        self.assertEqual(start_times, sorted(start_times), "Chunks must be strictly chronological")

    def test_05_unindexed_video_diagnostic(self):
        """Verify that a video with no transcript returns an informative diagnostic, not generic insufficient evidence."""
        fake_vid_id = "non-existent-video-id-999"
        bundle = tool_assemble_video_summary_context(self.project_id, fake_vid_id)
        self.assertFalse(bundle.get("has_data"))
        self.assertIn("not been indexed yet", bundle.get("message", "").lower())

        verifier = EvidenceVerificationAgent()
        plan = QueryPlannerAgent.plan("what video about")
        retriever = RetrievalAgent()
        diagnostic_chunks = retriever.retrieve(self.project_id, fake_vid_id, plan)
        self.assertTrue(len(diagnostic_chunks) > 0)
        self.assertTrue(diagnostic_chunks[0].get("metadata", {}).get("is_diagnostic"))

        verified, conf, reason = verifier.verify("what video about", diagnostic_chunks)
        self.assertFalse(verified)
        self.assertIn("not been indexed yet", reason.lower())

    def test_06_video_summary_full_pipeline_execution(self):
        """Verify run_video_qa_pipeline succeeds for 'what video about' with citations."""
        res = run_video_qa_pipeline(
            project_id=self.project_id,
            video_id=self.video_id,
            query="what video about"
        )
        self.assertTrue(res["verified"])
        self.assertEqual(res["plan"]["intent"], "video_summary")
        self.assertGreaterEqual(res["confidence"], 0.7)
        self.assertTrue(len(res["citations"]) > 0, "Summary must include citations")
        # Answer must not be the generic insufficient evidence message
        self.assertNotIn("couldn't find sufficient evidence", res["answer"].lower())
        # Check for bracketed timestamps in answer
        self.assertTrue("[" in res["answer"] and "]" in res["answer"], "Answer must have bracketed timestamps")


if __name__ == "__main__":
    unittest.main()
