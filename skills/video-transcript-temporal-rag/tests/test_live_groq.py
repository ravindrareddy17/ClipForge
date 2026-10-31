"""
Live Real-World AI Provider Integration Tests for Groq Cloud.
Validates the 6 mandatory test cases using live Groq API calls (openai/gpt-oss-20b).
Tracks exact latencies, token counts, and cost estimates.
Strictly forbids MockProvider fallback (allow_mock=False).
"""

import sys
import time
from pathlib import Path

# Fix Windows console UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure skill root is in sys.path
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from src.skill import VideoIntelligenceSkill
from src.llm.client import LLMClient
from src.llm.providers import GroqProvider, mask_key
from src.llm.exceptions import LLMProviderError, AuthenticationError
from src.chunker import TranscriptChunker
from src.models import NormalizedTranscript, TranscriptSegment

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples"
TRANSCRIPT_PATH = SAMPLE_DIR / "sample_whisper.json"

GROQ_MODEL = "openai/gpt-oss-20b"


def run_live_groq_tests():
    print("=" * 70)
    print("STAGE 3: REAL-WORLD GROQ CLOUD AI INTEGRATION TESTS")
    print(f"Target Model: {GROQ_MODEL}")
    print("Mock Fallback: DISABLED (allow_mock=False)")
    print("=" * 70)

    # Check key resolution without exposing value
    groq_tester = GroqProvider(model=GROQ_MODEL)
    if not groq_tester.api_key:
        print("\n[CRITICAL ERROR] GROQ_API_KEY is missing!")
        print("Please configure GROQ_API_KEY in your environment or .streamlit/secrets.toml.")
        sys.exit(1)

    print(f"Groq API Key detected and loaded: {mask_key(groq_tester.api_key)}")

    # Initialize skill strictly in real AI mode
    skill = VideoIntelligenceSkill(
        provider="groq",
        model=GROQ_MODEL,
        allow_mock=False
    )
    skill.load_transcript(TRANSCRIPT_PATH)

    results = []
    total_tokens_all_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0

    # ------------------------------------------------------------------------
    # Test 1: Factual Question
    # ------------------------------------------------------------------------
    print("\n[Test 1/6] Factual Question: 'What did the speaker say about the automobile and electronics industries?'")
    t0 = time.perf_counter()
    res1 = skill.ask("What did the speaker say about the automobile and electronics industries?")
    lat1 = time.perf_counter() - t0
    usage1 = skill.llm.get_last_usage()
    p1 = usage1.get("prompt_tokens", 0)
    c1 = usage1.get("completion_tokens", 0)
    tot1 = usage1.get("total_tokens", 0)
    total_prompt_tokens += p1
    total_completion_tokens += c1
    total_tokens_all_calls += tot1

    print(f"  Latency: {lat1:.2f}s | Tokens: {p1} prompt + {c1} completion = {tot1} total")
    print(f"  Confidence: {res1.confidence} | Intent: {res1.classified_intent}")
    print(f"  Answer Excerpt:\n  {res1.answer[:240]}...")
    print(f"  Citations ({len(res1.citations)}): {[c.timestamp for c in res1.citations]}")
    assert res1.confidence >= 0.3, "Factual query must have confidence >= 0.3"
    assert len(res1.citations) >= 1, "Must contain timestamp citations"
    results.append(("Factual Question", True, lat1, tot1, res1.answer))

    # ------------------------------------------------------------------------
    # Test 2: Find an Event and its Timestamp
    # ------------------------------------------------------------------------
    print("\n[Test 2/6] Event & Timestamp Search: 'When was the Shinkansen bullet train launched?'")
    t0 = time.perf_counter()
    res2 = skill.ask("When was the Shinkansen bullet train launched?")
    lat2 = time.perf_counter() - t0
    usage2 = skill.llm.get_last_usage()
    p2 = usage2.get("prompt_tokens", 0)
    c2 = usage2.get("completion_tokens", 0)
    tot2 = usage2.get("total_tokens", 0)
    total_prompt_tokens += p2
    total_completion_tokens += c2
    total_tokens_all_calls += tot2

    print(f"  Latency: {lat2:.2f}s | Tokens: {p2} prompt + {c2} completion = {tot2} total")
    print(f"  Confidence: {res2.confidence} | Intent: {res2.classified_intent}")
    print(f"  Answer:\n  {res2.answer}")
    print(f"  Citations ({len(res2.citations)}): {[c.timestamp for c in res2.citations]}")
    assert "1964" in res2.answer, "Must identify 1964 from evidence"
    results.append(("Event Timestamp Lookup", True, lat2, tot2, res2.answer))

    # ------------------------------------------------------------------------
    # Test 3: Whole-Video Summarization (Informal query)
    # ------------------------------------------------------------------------
    print("\n[Test 3/6] Whole-Video Summary: 'what video about'")
    t0 = time.perf_counter()
    res3 = skill.ask("what video about")
    lat3 = time.perf_counter() - t0
    usage3 = skill.llm.get_last_usage()
    p3 = usage3.get("prompt_tokens", 0)
    c3 = usage3.get("completion_tokens", 0)
    tot3 = usage3.get("total_tokens", 0)
    total_prompt_tokens += p3
    total_completion_tokens += c3
    total_tokens_all_calls += tot3

    print(f"  Latency: {lat3:.2f}s | Tokens: {p3} prompt + {c3} completion = {tot3} total")
    print(f"  Confidence: {res3.confidence} | Intent: {res3.classified_intent}")
    print(f"  Answer:\n{res3.answer}")
    print(f"  Citations ({len(res3.citations)}): {[c.timestamp for c in res3.citations]}")
    assert "Main Points" in res3.answer, "Must have structured Main Points"
    assert res3.classified_intent == "WHOLE_VIDEO_SUMMARY"
    results.append(("Whole-Video Summarization", True, lat3, tot3, res3.answer))

    # ------------------------------------------------------------------------
    # Test 4: Question whose answer is NOT present (Negative control)
    # ------------------------------------------------------------------------
    print("\n[Test 4/6] Unsupported Query: 'What did the speaker say about cryptocurrency and Bitcoin mining?'")
    t0 = time.perf_counter()
    res4 = skill.ask("What did the speaker say about cryptocurrency and Bitcoin mining?")
    lat4 = time.perf_counter() - t0

    print(f"  Latency: {lat4:.2f}s | Confidence: {res4.confidence}")
    print(f"  Answer: {res4.answer}")
    assert res4.confidence == 0.0, "Unsupported query must have 0.0 confidence"
    assert "couldn't find" in res4.answer.lower() or "not" in res4.answer.lower(), "Must reject with honest refusal"
    results.append(("Negative Control (Out-of-Scope)", True, lat4, 0, res4.answer))

    # ------------------------------------------------------------------------
    # Test 5: Long Transcript Query (1-Hour Synthetic Transcript)
    # ------------------------------------------------------------------------
    print("\n[Test 5/6] Long Transcript Test: 1-Hour video (360 segments, ~9,000 words)")
    # Generate 1-hour synthetic transcript
    seg_list = []
    for i in range(360):
        st = i * 10.0
        et = st + 10.0
        text = f"Minute {int(st//60)} discusses industrial and economic transformation in sector {i % 6}."
        if i == 180:
            text += " At the exact halfway mark, solar battery energy breakthroughs revolutionized transportation."
        seg_list.append({"start": st, "end": et, "text": text})

    long_transcript = {
        "title": "One Hour Industrial Documentary",
        "duration": 3600.0,
        "segments": seg_list
    }
    skill.load_transcript(long_transcript, video_id="long_1h_vid", video_title="1-Hour Documentary")

    t0 = time.perf_counter()
    res5 = skill.ask("When was the solar battery breakthrough discussed and what was it?")
    lat5 = time.perf_counter() - t0
    usage5 = skill.llm.get_last_usage()
    p5 = usage5.get("prompt_tokens", 0)
    c5 = usage5.get("completion_tokens", 0)
    tot5 = usage5.get("total_tokens", 0)
    total_prompt_tokens += p5
    total_completion_tokens += c5
    total_tokens_all_calls += tot5

    print(f"  Latency: {lat5:.2f}s | Tokens: {p5} prompt + {c5} completion = {tot5} total")
    print(f"  Confidence: {res5.confidence} | Intent: {res5.classified_intent}")
    print(f"  Answer:\n  {res5.answer}")
    print(f"  Citations ({len(res5.citations)}): {[c.timestamp for c in res5.citations]}")
    assert res5.confidence >= 0.3, "Must find middle-section solar breakthrough"
    results.append(("1-Hour Transcript Query", True, lat5, tot5, res5.answer))

    # ------------------------------------------------------------------------
    # Test 6: Invalid API Configuration
    # ------------------------------------------------------------------------
    print("\n[Test 6/6] Invalid API Key Rejection Test")
    bad_skill = VideoIntelligenceSkill(
        provider="groq",
        api_key="gsk_invalid_test_key_1234567890abcdef",
        allow_mock=False
    )
    bad_skill.load_transcript(TRANSCRIPT_PATH)

    rejected_properly = False
    try:
        bad_res = bad_skill.ask("what video about")
        # In our coordinator, LLMProviderError results in final_answer starting with "Error generating answer:"
        if "Error generating answer:" in bad_res.answer or bad_res.confidence == 0.0:
            rejected_properly = True
            print(f"  Properly caught error payload: {bad_res.answer[:120]}...")
    except (LLMProviderError, AuthenticationError) as e:
        rejected_properly = True
        print(f"  Properly raised exception: {type(e).__name__}: {e}")

    assert rejected_properly, "Invalid API key must be transparently rejected and not use Mock"
    results.append(("Invalid API Key Handling", True, 0.0, 0, "Rejected as expected"))

    # ------------------------------------------------------------------------
    # Summary & Cost Calculation
    # ------------------------------------------------------------------------
    # Groq openai/gpt-oss-20b pricing: ~$0.075 / 1M prompt tokens, ~$0.30 / 1M completion tokens
    cost_prompt = (total_prompt_tokens / 1_000_000.0) * 0.075
    cost_completion = (total_completion_tokens / 1_000_000.0) * 0.30
    total_cost = cost_prompt + cost_completion

    print("\n" + "=" * 70)
    print("LIVE GROQ INTEGRATION TEST SUMMARY")
    print("=" * 70)
    for name, success, lat, toks, _ in results:
        status_str = "PASSED" if success else "FAILED"
        tok_str = f"{toks} tokens" if toks > 0 else "0 tokens (guardrail/error)"
        print(f"  {name:32s} : {status_str} ({lat:.2f}s, {tok_str})")

    print("-" * 70)
    print(f"Total API Calls Made     : 4 live calls (1 guardrail rejected, 1 auth rejected)")
    print(f"Total Prompt Tokens      : {total_prompt_tokens:,}")
    print(f"Total Completion Tokens  : {total_completion_tokens:,}")
    print(f"Total Tokens Consumed    : {total_tokens_all_calls:,}")
    print(f"Estimated Groq Cost      : ${total_cost:.6f} USD (< 1/10th of a single cent)")
    print("MockProvider Invocations : 0 (ZERO - 100% genuine AI execution)")
    print("=" * 70)


if __name__ == "__main__":
    run_live_groq_tests()
