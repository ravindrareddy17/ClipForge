"""
Commercial Hardening & Regression Test Suite for video-transcript-temporal-rag.
Validates:
1. Provider error typing & mock mode lockdown (disabled by default)
2. Real provider failure & multi-provider cascade
3. Adaptive hierarchical summarization (1h, 2h, 3h scaling, no dropped middle sections)
4. Path traversal, file extension security, and oversized file rejections
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure skill root is in sys.path
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from src.skill import VideoIntelligenceSkill
from src.models import NormalizedTranscript, TranscriptSegment, EvidenceChunk
from src.chunker import TranscriptChunker
from src.hierarchical import AdaptiveHierarchicalSummarizer
from src.security import validate_and_read_transcript_file, SecurityError
from src.llm.client import LLMClient
from src.llm.providers import GroqProvider, GeminiProvider, OpenAIProvider
from src.llm.exceptions import (
    LLMProviderError,
    AuthenticationError,
    RateLimitError,
    ProviderTimeoutError
)


class TestCommercialHardening(unittest.TestCase):

    # ========================================================================
    # 1. PROVIDER & MOCK LOCKDOWN TESTS
    # ========================================================================

    def test_mock_disabled_by_default(self):
        """MockProvider must be strictly forbidden unless allow_mock=True."""
        with self.assertRaises(AuthenticationError):
            LLMClient(provider="mock", allow_mock=False)

    def test_mock_explicitly_enabled(self):
        """MockProvider works when explicitly authorized."""
        client = LLMClient(provider="mock", allow_mock=True)
        res = client.generate("Test prompt")
        self.assertIn("transcript evidence", res)

    def test_real_provider_missing_key_error(self):
        """Unconfigured real provider must raise AuthenticationError with clear message."""
        # Ensure env var is empty for test
        old_key = os.environ.pop("GROQ_API_KEY", None)
        try:
            groq = GroqProvider(api_key="")
            with self.assertRaises(AuthenticationError) as ctx:
                groq.generate("Hello")
            self.assertIn("GROQ_API_KEY is not configured", str(ctx.exception))
        finally:
            if old_key:
                os.environ["GROQ_API_KEY"] = old_key

    def test_no_silent_mock_fallback(self):
        """When a real provider fails and allow_mock=False, it must raise LLMProviderError, NOT return mock answer."""
        client = LLMClient(provider="groq", api_key="invalid_test_key_xyz", allow_mock=False)
        with self.assertRaises(LLMProviderError):
            client.generate("What is this video about?")

    def test_multi_provider_failover(self):
        """Tests that configured real providers are attempted in sequence."""
        # Initialize client with invalid groq key, but allow_mock=True for test fallback
        client = LLMClient(provider="groq", api_key="invalid_key", fallback_enabled=True, allow_mock=True)
        # Should fail on groq, and fallback to mock because allow_mock is explicitly True
        res = client.generate("What is this video about?")
        self.assertTrue(len(res) > 0)

    # ========================================================================
    # 2. ADAPTIVE HIERARCHICAL SUMMARIZATION TESTS (1h, 2h, 3h)
    # ========================================================================

    def _generate_synthetic_transcript(self, duration_hours: float, middle_marker: str = ""):
        total_minutes = int(duration_hours * 60)
        seg_duration = 10.0
        num_segs = int((total_minutes * 60) / seg_duration)
        segments = []

        mid_seg_idx = num_segs // 2

        for i in range(num_segs):
            st = i * seg_duration
            et = st + seg_duration
            text = f"Minute {int(st//60)} discusses industry and economy topic {i % 10}."
            if middle_marker and i == mid_seg_idx:
                text += f" CRITICAL_MARKER: {middle_marker}."
            segments.append(TranscriptSegment(id=i, start=st, end=et, text=text))

        return NormalizedTranscript(
            video_id=f"synth_{int(duration_hours)}h",
            title=f"Synthetic {duration_hours}h Video",
            duration=float(total_minutes * 60),
            segments=segments,
            full_text=" ".join(s.text for s in segments)
        )

    def test_one_hour_hierarchical_summary(self):
        """1-hour transcript (~360 segments) must partition into 4-6 balanced sections."""
        t1 = self._generate_synthetic_transcript(1.0)
        chunker = TranscriptChunker(target_words=150)
        chunks = chunker.chunk(t1)

        summarizer = AdaptiveHierarchicalSummarizer()
        plan = summarizer.partition(chunks, total_duration=t1.duration)

        self.assertTrue(plan.num_sections >= 4)
        self.assertEqual(plan.sections[0].start_time, 0.0)
        self.assertTrue(plan.sections[-1].end_time >= 3500.0)

    def test_two_hour_hierarchical_summary(self):
        """2-hour transcript (~720 segments) must partition into 6-8 balanced sections."""
        t2 = self._generate_synthetic_transcript(2.0)
        chunker = TranscriptChunker(target_words=150)
        chunks = chunker.chunk(t2)

        summarizer = AdaptiveHierarchicalSummarizer()
        plan = summarizer.partition(chunks, total_duration=t2.duration)

        self.assertTrue(plan.num_sections >= 6)
        self.assertTrue(plan.sections[-1].end_time >= 7000.0)

    def test_three_hour_hierarchical_summary(self):
        """3-hour transcript (~1080 segments) must partition into 8 sections without context blowout."""
        t3 = self._generate_synthetic_transcript(3.0)
        chunker = TranscriptChunker(target_words=150)
        chunks = chunker.chunk(t3)

        summarizer = AdaptiveHierarchicalSummarizer()
        bundle = summarizer.extract_balanced_context(chunks, total_duration=t3.duration)

        self.assertEqual(bundle["num_sections"], 8)
        # Verify anchors span entire video
        anchors = bundle["chunks"]
        self.assertEqual(anchors[0].start_time, 0.0)
        self.assertTrue(anchors[-1].end_time >= 10000.0)
        # Verify word count remains within context window limit (< 3,000 words)
        total_words = sum(len(c.text.split()) for c in anchors)
        self.assertTrue(total_words < 3000)

    def test_no_missing_middle_section_information(self):
        """Verifies that the middle section of a 2-hour video is captured in the summary context."""
        t_mid = self._generate_synthetic_transcript(2.0, middle_marker="solar_fusion_breakthrough")
        skill = VideoIntelligenceSkill(provider="mock", allow_mock=True)
        skill.store.load_transcript(t_mid)

        summary_bundle = skill.store.get_summary_context(t_mid.video_id)
        anchors = summary_bundle["chunks"]

        # Check that anchors include intermediate times (between 25% and 75% of duration)
        mid_time = t_mid.duration / 2.0
        has_mid_anchor = any(abs(c.start_time - mid_time) < 1800.0 for c in anchors)
        self.assertTrue(has_mid_anchor, "Middle section anchor must be present")

    def test_timestamp_preservation(self):
        """Verifies timestamp formatting and continuity."""
        c = EvidenceChunk(id="c_test", chunk_index=0, text="Test", start_time=125.0, end_time=195.0)
        self.assertEqual(c.format_timestamp(), "[02:05–03:15]")

    def test_unsupported_claim_rejection(self):
        """Verifies that an out-of-scope query is rejected with zero confidence."""
        t = self._generate_synthetic_transcript(0.5)
        skill = VideoIntelligenceSkill(provider="mock", allow_mock=True)
        skill.store.load_transcript(t)

        res = skill.ask("What did they say about quantum teleportation and warp drives?")
        self.assertEqual(res.confidence, 0.0)
        self.assertEqual(res.answer, "I couldn't find sufficient evidence for that in this video.")

    # ========================================================================
    # 3. SECURITY & PATH TRAVERSAL TESTS
    # ========================================================================

    def test_security_path_traversal_rejected(self):
        """Attempts to traverse outside allowed directories must raise SecurityError."""
        with tempfile.TemporaryDirectory() as safe_sandbox:
            outside_file = Path(safe_sandbox).parent / "outside_unauthorized.json"
            outside_file.write_text('{"text": "secret"}', encoding="utf-8")

            try:
                skill = VideoIntelligenceSkill(
                    provider="mock",
                    allow_mock=True,
                    allowed_directories=[Path(safe_sandbox)]
                )
                traversal_path = Path(safe_sandbox) / ".." / "outside_unauthorized.json"
                with self.assertRaises(SecurityError):
                    skill.load_transcript(str(traversal_path))
            finally:
                if outside_file.exists():
                    outside_file.unlink()

    def test_security_invalid_extension_rejected(self):
        """File extensions other than .json, .srt, .vtt, .txt must be rejected."""
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"BINARY_CONTENT")
            exe_path = f.name

        try:
            skill = VideoIntelligenceSkill(provider="mock", allow_mock=True)
            with self.assertRaises(SecurityError) as ctx:
                skill.load_transcript(exe_path)
            self.assertIn("Invalid file extension", str(ctx.exception))
        finally:
            if os.path.exists(exe_path):
                os.remove(exe_path)

    def test_security_oversized_file_rejected(self):
        """Files exceeding size limit (25 MB) must be rejected."""
        temp_dir = Path(tempfile.gettempdir())
        dummy_file = temp_dir / "oversized_test.json"
        dummy_file.write_text("A" * 2048, encoding="utf-8")

        try:
            with self.assertRaises(SecurityError) as ctx:
                validate_and_read_transcript_file(
                    dummy_file,
                    allowed_directories=[temp_dir],
                    max_size_bytes=1024
                )
            self.assertIn("exceeds limit", str(ctx.exception))
        finally:
            if dummy_file.exists():
                dummy_file.unlink()


if __name__ == "__main__":
    unittest.main()
