"""
ClipForge AI V2 - 20-Point Automated Test Suite
Verifies data integrity, RAG engine, multi-agent QA architecture,
channel ingestion, safety guardrails, and syllabus mapping.
"""

import os
import sys
import unittest
import uuid
import re

# Ensure backend is on sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from clipforge_engine.db import (
    init_db, create_project, get_project,
    create_video, get_video, get_videos,
    get_db_connection, upsert_transcript_chunk,
    get_video_chunks_lexical, add_chat_message,
    get_chat_history, migrate_project_id_consistency
)
import clipforge_engine.rag as rag
from clipforge_engine.video_qa_agents import (
    QueryPlannerAgent, RetrievalAgent, TimelineAgent,
    EvidenceVerificationAgent, AnswerSynthesisAgent,
    SafetyGuardrailAgent, run_video_qa_pipeline,
    tool_search_timestamp, tool_verify_claim
)
from clipforge_engine.channel import resolve_channel_videos, import_channel_videos
import clipforge_engine.cse473_lab as cse473


class TestClipForgeV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.project_id = "test_proj_" + str(uuid.uuid4())[:8]
        cls.test_video_id = "test_vid_" + str(uuid.uuid4())[:8]
        
        # Real universe video if available
        cls.real_video_id = "01ee5ba6-12ea-419f-9618-be90b4fcf1c1"
        cls.real_project_id = "488ae794-b83c-4ee1-babb-3400eec64e7b"
        
        # Create a sample multi-segment transcript for testing
        cls.sample_transcript = [
            {"start": 0.0, "end": 15.0, "text": "Welcome to our cosmic journey across the observable universe from planet Earth."},
            {"start": 15.0, "end": 45.0, "text": "Leaving Earth behind, light travels to the Moon in about 1.3 seconds."},
            {"start": 45.0, "end": 131.0, "text": "Passing Mars at 4 light minutes, we enter the asteroid belt before Jupiter."},
            {"start": 131.0, "end": 264.0, "text": "Beyond Neptune lies the Kuiper belt and the vast Oort cloud reaching 100,000 AU."},
            {"start": 308.0, "end": 397.0, "text": "Our next point of interest is Alpha Centauri, located 4.24 light years away from our solar system."},
            {"start": 397.0, "end": 600.0, "text": "Galaxies group into clusters and cosmic filaments stretching billions of light years."},
            {"start": 600.0, "end": 669.0, "text": "In conclusion, the observable universe is vast and continuously expanding into the cosmic horizon."}
        ]

        # Index sample chunks into database
        cls.chunks = rag.chunk_transcript(cls.test_video_id, cls.project_id, cls.sample_transcript, target_words=20, overlap_words=5)
        rag.index_transcript_chunks(cls.test_video_id, cls.project_id, cls.chunks)

    # 1. Project ID consistency
    def test_01_project_id_consistency(self):
        migrate_project_id_consistency()
        chunks = get_video_chunks_lexical(self.test_video_id, project_id=self.project_id)
        self.assertGreater(len(chunks), 0)
        for c in chunks:
            self.assertEqual(c["project_id"], self.project_id)

    # 2. Embedding health check
    def test_02_embedding_health(self):
        health = rag.check_embedding_health()
        self.assertIn("status", health)
        if health["status"] == "healthy":
            self.assertEqual(health["dimension"], 768)
            self.assertFalse(health["is_zero_vector"])

    # 3. Chunk creation with overlap
    def test_03_chunk_creation_with_overlap(self):
        chunks = rag.chunk_transcript(self.test_video_id, self.project_id, self.sample_transcript, target_words=25, overlap_words=5)
        self.assertGreaterEqual(len(chunks), 2)
        # Ensure timestamps are strictly increasing
        for i in range(len(chunks) - 1):
            self.assertLessEqual(chunks[i]["start_time"], chunks[i]["end_time"])
            self.assertLessEqual(chunks[i]["start_time"], chunks[i+1]["start_time"])

    # 4. Idempotent indexing
    def test_04_idempotent_indexing(self):
        count_before = len(get_video_chunks_lexical(self.test_video_id, project_id=self.project_id))
        # Re-index same chunks
        rag.index_transcript_chunks(self.test_video_id, self.project_id, self.chunks)
        count_after = len(get_video_chunks_lexical(self.test_video_id, project_id=self.project_id))
        self.assertEqual(count_before, count_after)

    # 5. Vector retrieval
    def test_05_vector_retrieval(self):
        hits = rag.semantic_search_chunks(self.project_id, self.test_video_id, "observable universe and space", k=3)
        self.assertIsInstance(hits, list)

    # 6. Lexical retrieval
    def test_06_lexical_retrieval(self):
        hits = rag.lexical_search_chunks(self.test_video_id, self.project_id, "Alpha Centauri", k=2)
        self.assertGreater(len(hits), 0)
        top_text = hits[0][1]["text"]
        self.assertIn("Alpha Centauri", top_text)

    # 7. Hybrid retrieval RRF
    def test_07_hybrid_retrieval_rrf(self):
        hits = rag.hybrid_retrieve_chunks(self.project_id, self.test_video_id, "Alpha Centauri light years", k=3)
        self.assertGreater(len(hits), 0)
        texts = [h["text"] for h in hits]
        self.assertTrue(any("Alpha Centauri" in t for t in texts))

    # 8. Timestamp accuracy
    def test_08_timestamp_accuracy(self):
        chunks = get_video_chunks_lexical(self.test_video_id, project_id=self.project_id)
        for c in chunks:
            self.assertGreaterEqual(c["end_time"], c["start_time"])
            self.assertGreaterEqual(c["start_time"], 0.0)

    # 9. Video isolation
    def test_09_video_isolation(self):
        other_vid = "other_vid_" + str(uuid.uuid4())[:8]
        other_chunks = rag.chunk_transcript(other_vid, self.project_id, [{"start": 0.0, "end": 10.0, "text": "Secret recipe for chocolate cake."}])
        rag.index_transcript_chunks(other_vid, self.project_id, other_chunks)

        hits_for_test = rag.hybrid_retrieve_chunks(self.project_id, self.test_video_id, "chocolate cake", k=3)
        for h in hits_for_test:
            self.assertNotEqual(h["metadata"].get("video_id"), other_vid)

    # 10. Conversation memory
    def test_10_conversation_memory(self):
        session_id = "test_sess_" + str(uuid.uuid4())[:8]
        add_chat_message(self.project_id, session_id, "user", "What is step 1?", video_id=self.test_video_id)
        add_chat_message(self.project_id, session_id, "assistant", "Step 1 is start [00:15].", video_id=self.test_video_id)

        history = get_chat_history(self.project_id, session_id, video_id=self.test_video_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")

    # 11. Evidence verification
    def test_11_evidence_verification(self):
        mock_chunks = [{"text": "Alpha Centauri is four light years away from Earth."}]
        res_supported = tool_verify_claim("Alpha Centauri distance", mock_chunks)
        self.assertTrue(res_supported["supported"])

        res_unsupported = tool_verify_claim("Extinction of Tyrannosaurus Rex dinosaurs", mock_chunks)
        self.assertFalse(res_unsupported["supported"])

    # 12. Unsupported question handling
    def test_12_unsupported_question_handling(self):
        # Query dinosaur extinction against universe video
        target_vid = self.real_video_id if get_video(self.real_video_id) else self.test_video_id
        target_proj = self.real_project_id if get_video(self.real_video_id) else self.project_id
        
        qa_res = run_video_qa_pipeline(target_proj, target_vid, "What did the speaker say about the extinction of dinosaurs?")
        self.assertIn("couldn't find sufficient evidence", qa_res["answer"].lower())

    # 13. Prompt injection protection
    def test_13_prompt_injection_protection(self):
        sec_res = cse473.run_prompt_injection_safety_test()
        self.assertEqual(sec_res["passed_tests"], sec_res["total_tests"])

    # 14. Channel video separation
    def test_14_channel_video_separation(self):
        mock_items = [
            {"title": "Channel Video 1", "url": "https://www.youtube.com/watch?v=mock1", "duration": 120.0},
            {"title": "Channel Video 2", "url": "https://www.youtube.com/watch?v=mock2", "duration": 180.0}
        ]
        imported = import_channel_videos(self.project_id, mock_items, dispatch_pipeline=False)
        self.assertEqual(len(imported), 2)
        self.assertNotEqual(imported[0]["video_id"], imported[1]["video_id"])
        v1 = get_video(imported[0]["video_id"])
        v2 = get_video(imported[1]["video_id"])
        self.assertIsNotNone(v1)
        self.assertIsNotNone(v2)
        self.assertEqual(v1["filename"], "Channel Video 1")
        self.assertEqual(v2["filename"], "Channel Video 2")

    # 15. Agent workflow sequence
    def test_15_agent_workflow(self):
        plan = QueryPlannerAgent.plan("What happened after passing Mars?")
        self.assertEqual(plan["intent"], "chronology")
        self.assertEqual(plan["temporal_marker"], "after")

    # 16. Tool selection
    def test_16_tool_selection(self):
        ts_hits = tool_search_timestamp(self.project_id, self.test_video_id, 308.0)
        self.assertIsInstance(ts_hits, list)
        self.assertGreater(len(ts_hits), 0)

    # 17. ReAct loop bounded execution
    def test_17_react_loop_limits(self):
        # Must execute and return without infinite loop
        qa_res = run_video_qa_pipeline(self.project_id, self.test_video_id, "Summarize the beginning")
        self.assertIn("answer", qa_res)
        self.assertIn("confidence", qa_res)

    # 18. Citation generation
    def test_18_citation_generation(self):
        answer = AnswerSynthesisAgent.synthesize(
            self.project_id,
            "What did the speaker say about Alpha Centauri?",
            self.chunks,
            video_id=self.test_video_id
        )
        # Verify presence of bracketed citation
        self.assertTrue("[" in answer and "]" in answer)

    # 19. End of video retrieval
    def test_19_end_of_video_retrieval(self):
        # Query conclusion
        hits = rag.hybrid_retrieve_chunks(self.project_id, self.test_video_id, "In conclusion cosmic horizon expansion", k=3)
        self.assertGreater(len(hits), 0)
        last_chunk = hits[-1]
        self.assertGreaterEqual(last_chunk["metadata"]["start_time"], 300.0)

    # 20. Beginning vs ending comparison
    def test_20_beginning_vs_ending_comparison(self):
        plan = QueryPlannerAgent.plan("Compare the discussion at the beginning and end.")
        self.assertEqual(plan["intent"], "comparison")
        chunks = RetrievalAgent.retrieve(self.project_id, self.test_video_id, plan)
        start_times = [c["metadata"]["start_time"] for c in chunks]
        # Must contain chunk near start (< 60s) and near end (> 300s)
        self.assertTrue(any(t < 60.0 for t in start_times))
        self.assertTrue(any(t > 300.0 for t in start_times))


if __name__ == "__main__":
    unittest.main()
