"""
Unit tests for TranscriptChunker, LexicalSearcher, and Reciprocal Rank Fusion.
"""

import sys
import unittest
from pathlib import Path

# Ensure skill root is in sys.path
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from src.models import NormalizedTranscript, TranscriptSegment, EvidenceChunk
from src.chunker import TranscriptChunker
from src.search.lexical import LexicalSearcher
from src.search.fusion import reciprocal_rank_fusion, expand_chunk_context

class TestChunkerAndSearch(unittest.TestCase):

    def setUp(self):
        segments = []
        for i in range(10):
            st = i * 20.0
            et = st + 18.0
            text = f"Segment {i} discusses economic growth, industrial policy, and trade regulations in great detail. " * 3
            segments.append(TranscriptSegment(id=i, start=st, end=et, text=text))

        self.transcript = NormalizedTranscript(
            video_id="test_vid",
            title="Economic Analysis",
            duration=200.0,
            segments=segments,
            full_text=" ".join(s.text for s in segments)
        )

    def test_chunking(self):
        chunker = TranscriptChunker(target_words=50, overlap_pct=0.2)
        chunks = chunker.chunk(self.transcript)
        self.assertTrue(len(chunks) >= 2)
        self.assertEqual(chunks[0].start_time, 0.0)
        self.assertTrue(chunks[-1].end_time > chunks[0].end_time)

    def test_lexical_search_bm25(self):
        chunker = TranscriptChunker(target_words=50)
        chunks = chunker.chunk(self.transcript)

        # Inject a unique keyword into chunk 1
        chunks[1].text += " Unusual keyword zephyr_engine was highlighted."

        searcher = LexicalSearcher()
        hits = searcher.search("zephyr_engine", chunks, top_k=3)
        self.assertTrue(len(hits) >= 1)
        self.assertEqual(hits[0].id, chunks[1].id)
        self.assertIn("zephyr_engine", hits[0].text)

    def test_rrf_fusion(self):
        c1 = EvidenceChunk(id="c1", chunk_index=0, text="First chunk", start_time=0.0, end_time=10.0)
        c2 = EvidenceChunk(id="c2", chunk_index=1, text="Second chunk", start_time=10.0, end_time=20.0)
        c3 = EvidenceChunk(id="c3", chunk_index=2, text="Third chunk", start_time=20.0, end_time=30.0)

        list1 = [c1, c2, c3]
        list2 = [c2, c1, c3]

        fused = reciprocal_rank_fusion([list1, list2], top_n=2)
        self.assertEqual(len(fused), 2)
        fused_ids = {c.id for c in fused}
        self.assertIn("c1", fused_ids)
        self.assertIn("c2", fused_ids)

    def test_expand_chunk_context(self):
        chunks = [
            EvidenceChunk(id=f"c{i}", chunk_index=i, text=f"Chunk {i}", start_time=i*10.0, end_time=(i+1)*10.0)
            for i in range(5)
        ]
        seed = [chunks[2]]
        expanded = expand_chunk_context(chunks, seed, window_chunks=1)
        indices = [c.chunk_index for c in expanded]
        self.assertEqual(indices, [1, 2, 3])

if __name__ == "__main__":
    unittest.main()
