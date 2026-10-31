"""
Golden Benchmark Test Suite for video-transcript-temporal-rag.
Validates the 10 benchmark queries across intent classification,
temporal ordering, grounded synthesis, and hallucination rejection.
"""

import sys
import unittest
from pathlib import Path

# Ensure skill root is in sys.path
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from src.skill import VideoIntelligenceSkill

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples"
TRANSCRIPT_PATH = SAMPLE_DIR / "sample_whisper.json"

class TestGoldenBenchmark(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.skill = VideoIntelligenceSkill(provider="mock", allow_mock=True)
        cls.skill.load_transcript(TRANSCRIPT_PATH)

    def test_01_informal_summary(self):
        """1. Informal summary query must classify as WHOLE_VIDEO_SUMMARY."""
        res = self.skill.ask("what video about")
        self.assertEqual(res.classified_intent, "WHOLE_VIDEO_SUMMARY")
        self.assertEqual(res.normalized_query, "What is this video about?")
        self.assertTrue(res.confidence >= 0.8)
        self.assertIn("Main Points", res.answer)

    def test_02_explicit_summary(self):
        """2. Explicit summary command."""
        res = self.skill.ask("summarize this video")
        self.assertEqual(res.classified_intent, "WHOLE_VIDEO_SUMMARY")
        self.assertTrue(res.confidence >= 0.8)

    def test_03_factual_lookup(self):
        """3. Specific factual question."""
        res = self.skill.ask("What did the speaker say about Japan's post-war economy?")
        self.assertEqual(res.classified_intent, "FACTUAL_LOOKUP")
        self.assertTrue(res.confidence >= 0.3)
        self.assertNotIn("I couldn't find sufficient evidence", res.answer)

    def test_04_timestamp_search(self):
        """4. Temporal timestamp query."""
        res = self.skill.ask("When did the discussion about industrialization begin?")
        self.assertIn(res.classified_intent, ["TIMESTAMP_SEARCH", "FACTUAL_LOOKUP"])
        self.assertTrue(res.confidence >= 0.3)

    def test_05_chronological_progression(self):
        """5. Chronological sequence query (what happened after)."""
        res = self.skill.ask("What happened after industrial reconstruction?")
        self.assertEqual(res.classified_intent, "TIMELINE_RECONSTRUCTION")
        self.assertTrue(res.confidence >= 0.3)

    def test_06_direct_fact_verification(self):
        """6. Verification query about exports."""
        res = self.skill.ask("Did the speaker mention exports?")
        self.assertEqual(res.classified_intent, "FACTUAL_LOOKUP")
        self.assertTrue(res.confidence >= 0.3)

    def test_07_thematic_summary(self):
        """7. Thematic domain query."""
        res = self.skill.ask("Summarize everything about Japan's automobile industry.")
        self.assertIn(res.classified_intent, ["WHOLE_VIDEO_SUMMARY", "FACTUAL_LOOKUP"])
        self.assertTrue(res.confidence >= 0.3)

    def test_08_informal_short_query(self):
        """8. Informal short query 'main points?'."""
        res = self.skill.ask("main points?")
        self.assertEqual(res.classified_intent, "WHOLE_VIDEO_SUMMARY")
        self.assertEqual(res.normalized_query, "What are the main points of this video?")
        self.assertTrue(res.confidence >= 0.8)

    def test_09_negative_control_out_of_scope(self):
        """9. Out of scope query must be rejected by guardrails without hallucination."""
        res = self.skill.ask("What did they say about cryptocurrency and Bitcoin?")
        self.assertEqual(res.confidence, 0.0)
        self.assertEqual(res.answer, "I couldn't find sufficient evidence for that in this video.")

    def test_10_empty_transcript_diagnostic(self):
        """10. Unindexed/empty transcript must return informative diagnostic."""
        empty_skill = VideoIntelligenceSkill(provider="mock", allow_mock=True)
        # Ask without loading any transcript
        res = empty_skill.ask("what video about", video_id="unloaded_video")
        self.assertIn("not been loaded or indexed yet", res.answer)

if __name__ == "__main__":
    unittest.main()
