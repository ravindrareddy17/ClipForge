"""
Timestamp Quality & Citation Grounding Verification Test Suite.
Verifies temporal precision, multi-event sequencing, anti-hallucination guardrails,
and exact substring citation matching.
"""

import sys
import unittest
from pathlib import Path

# Ensure skill root is in sys.path
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from src.skill import VideoIntelligenceSkill
from src.models import (
    NormalizedTranscript,
    TranscriptSegment,
    CitationItem,
    EvidenceChunk,
    QueryPlan,
    VerificationResult,
    VideoQAState,
    format_timestamp,
    format_time_range
)
from src.agents.verification import EvidenceVerificationAgent
from src.agents.guardrail import SafetyGuardrailAgent


class TestTimestampQuality(unittest.TestCase):

    def setUp(self):
        self.sample_path = Path(__file__).resolve().parent.parent / "examples" / "sample_whisper.json"
        self.skill = VideoIntelligenceSkill(provider="mock", allow_mock=True)
        self.transcript = self.skill.load_transcript(self.sample_path)

    def test_timestamp_formatting_helpers(self):
        """Test timestamp formatting functions for standard, hour+, and edge cases."""
        self.assertEqual(format_timestamp(0), "00:00")
        self.assertEqual(format_timestamp(45.2), "00:45")
        self.assertEqual(format_timestamp(95), "01:35")
        self.assertEqual(format_timestamp(3600), "01:00:00")
        self.assertEqual(format_timestamp(3665.8), "01:01:05")
        self.assertEqual(format_time_range(96.0, 155.0), "[01:36–02:35]")
        self.assertEqual(format_time_range(10.0, 10.0), "[00:10]")

    def test_precise_single_event_timestamp_retrieval(self):
        """Verify that a specific factual lookup retrieves the exact ground-truth timestamp."""
        res = self.skill.ask("When did they mention the Shinkansen bullet train?")

        self.assertTrue(len(res.citations) > 0, "Should return at least one citation")
        top_citation = res.citations[0]

        # Verify the Shinkansen event (ground truth 221.0s) falls within the retrieved citation window
        self.assertLessEqual(top_citation.start_seconds, 221.0)
        self.assertGreaterEqual(top_citation.end_seconds, 221.0)
        self.assertIn("05:10", top_citation.timestamp)

        # Verify text excerpt contains relevant terms
        self.assertIn("Shinkansen", top_citation.text_excerpt)
        self.assertGreater(res.confidence, 0.70)

    def test_multiple_events_chronological_ordering(self):
        """Verify that multi-event queries preserve strict chronological ordering across timeline."""
        res = self.skill.ask("what video about")

        self.assertEqual(res.classified_intent, "WHOLE_VIDEO_SUMMARY")
        self.assertTrue(len(res.citations) >= 3, "Whole video summary should cite multiple timeline anchors")

        # Verify strict ascending order of citations
        prev_start = -1.0
        for cite in res.citations:
            self.assertGreaterEqual(
                cite.start_seconds,
                prev_start,
                f"Citations must be chronologically sorted: {cite.start_seconds} < {prev_start}"
            )
            prev_start = cite.start_seconds

        # Verify time spread spans beginning and later parts of video
        first_cite = res.citations[0]
        last_cite = res.citations[-1]
        self.assertLess(first_cite.start_seconds, 120.0, "First anchor should be near video opening")
        self.assertGreater(last_cite.end_seconds, 250.0, "Last anchor should be towards video conclusion")

    def test_evidence_citation_substring_matching(self):
        """Verify every citation excerpt matches the source transcript full text."""
        res = self.skill.ask("What did the speaker say about the automobile industry?")

        self.assertTrue(len(res.citations) > 0)
        full_text = self.transcript.full_text

        for citation in res.citations:
            clean_excerpt = citation.text_excerpt.strip(".").strip()
            self.assertTrue(
                clean_excerpt in full_text,
                f"Citation excerpt '{clean_excerpt}' was not found in source transcript full text!"
            )

    def test_hallucinated_timestamp_rejection_by_guardrail(self):
        """Verify that synthesized citations with timestamps exceeding video bounds are pruned."""
        guardrail = SafetyGuardrailAgent()

        # Fabricate a state with citation outside the 421s video (e.g. 5999s)
        hallucinated_citations = [
            CitationItem(
                timestamp="[99:59–102:00]",
                start_seconds=5999.0,
                end_seconds=6120.0,
                text_excerpt="Completely fabricated future event.",
                relevance_score=0.95
            ),
            CitationItem(
                timestamp="[01:00–02:00]",
                start_seconds=60.0,
                end_seconds=120.0,
                text_excerpt="Legitimate historical event.",
                relevance_score=0.90
            )
        ]

        state = VideoQAState(
            query="Tell me about future plans",
            duration=421.0,
            draft_answer="Here is an event at [01:00] and another at [99:59].",
            citations=hallucinated_citations,
            verification=VerificationResult(supported=True, confidence=0.85)
        )

        out_state = guardrail.run(state)

        # Guardrail must prune the 5999s citation and keep only the 60s citation
        self.assertEqual(len(out_state.citations), 1, "Guardrail must prune citations exceeding video duration")
        self.assertEqual(out_state.citations[0].start_seconds, 60.0)

    def test_unverified_claims_penalize_confidence(self):
        """Verify that queries lacking transcript evidence are caught and marked unsupported."""
        verifier = EvidenceVerificationAgent()

        state = VideoQAState(
            query="When did the astronaut land on Mars?",
            duration=421.0,
            plan=QueryPlan(intent="FACTUAL_LOOKUP", original_query="When did the astronaut land on Mars?"),
            retrieved_chunks=[
                EvidenceChunk(
                    id="chunk_1",
                    text="The automobile industry in Japan saw rapid post-war growth.",
                    start_time=96.0,
                    end_time=155.0
                )
            ]
        )

        out_state = verifier.run(state)

        # Verification score must be 0.0 for missing concepts (astronaut, mars)
        self.assertFalse(out_state.verification.supported)
        self.assertEqual(out_state.verification.confidence, 0.0)
        self.assertIn("Missing concepts", out_state.audit_trail[-1])


if __name__ == "__main__":
    unittest.main()
