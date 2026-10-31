"""
Unit tests for TranscriptNormalizer.
"""

import sys
import unittest
from pathlib import Path

# Ensure skill root is in sys.path
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from src.normalizer import TranscriptNormalizer, parse_timestamp_to_seconds

class TestTranscriptNormalizer(unittest.TestCase):

    def test_parse_timestamp_to_seconds(self):
        self.assertEqual(parse_timestamp_to_seconds("01:30"), 90.0)
        self.assertEqual(parse_timestamp_to_seconds("00:02:15"), 135.0)
        self.assertEqual(parse_timestamp_to_seconds("01:20.500"), 80.5)
        self.assertEqual(parse_timestamp_to_seconds("00:01:20,500"), 80.5)

    def test_normalize_dict_whisper(self):
        data = {
            "title": "Test Video",
            "duration": 120.0,
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 10.0,
                    "text": "Hello world and welcome to the show.",
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 0.5},
                        {"word": "world", "start": 0.5, "end": 1.0}
                    ]
                }
            ]
        }
        res = TranscriptNormalizer.normalize(data, video_id="v1")
        self.assertEqual(res.video_id, "v1")
        self.assertEqual(res.title, "Test Video")
        self.assertEqual(len(res.segments), 1)
        self.assertEqual(res.segments[0].text, "Hello world and welcome to the show.")
        self.assertIsNotNone(res.segments[0].words)
        self.assertEqual(len(res.segments[0].words), 2)

    def test_normalize_flat_word_list(self):
        data = [
            {"word": "First", "start": 0.0, "end": 0.4},
            {"word": "second", "start": 0.5, "end": 0.9},
            {"word": "third", "start": 1.0, "end": 1.5}
        ]
        res = TranscriptNormalizer.normalize(data, video_id="v_words")
        self.assertTrue(len(res.segments) >= 1)
        self.assertIn("First second third", res.full_text)

    def test_normalize_srt_text(self):
        srt = """1
00:00:01,000 --> 00:00:05,000
Welcome to this historic presentation.

2
00:00:06,500 --> 00:00:12,000
Today we discuss the industrial revolution.
"""
        res = TranscriptNormalizer.normalize(srt, video_id="srt_vid")
        self.assertEqual(len(res.segments), 2)
        self.assertEqual(res.segments[0].start, 1.0)
        self.assertEqual(res.segments[0].end, 5.0)
        self.assertIn("Welcome to this historic presentation.", res.segments[0].text)

    def test_normalize_bracket_timestamps(self):
        txt = "[01:15] The speaker enters the stage and introduces the thesis. [02:30] Next we examine data."
        res = TranscriptNormalizer.normalize(txt, video_id="bracket_vid")
        self.assertEqual(len(res.segments), 2)
        self.assertEqual(res.segments[0].start, 75.0)

if __name__ == "__main__":
    unittest.main()
