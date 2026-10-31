"""
Quickstart demo: Using VideoIntelligenceSkill with a sample Whisper transcript.
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on all operating systems
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure skill root is in sys.path
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from src.skill import VideoIntelligenceSkill

SAMPLE_DIR = Path(__file__).resolve().parent
TRANSCRIPT_PATH = SAMPLE_DIR / "sample_whisper.json"

def main():
    # Initialize skill (explicitly authorizing 'mock' provider for offline demo)
    skill = VideoIntelligenceSkill(provider="mock", allow_mock=True)

    # Load and index transcript
    print("[1] Loading sample Whisper transcript...")
    transcript = skill.load_transcript(TRANSCRIPT_PATH)
    print(f"    Loaded '{transcript.title}' ({transcript.duration}s, {len(transcript.segments)} segments)")

    # Test 1: Informal Whole-Video Summary Query
    print("\n[2] Testing Informal Summary Query: 'what video about'")
    res1 = skill.ask("what video about")
    print(f"    Classified Intent: {res1.classified_intent}")
    print(f"    Confidence: {res1.confidence}")
    print(f"    Normalized Query: '{res1.normalized_query}'")
    print(f"\nAnswer:\n{res1.answer}")

    # Test 2: Specific Fact Lookup
    print("\n[3] Testing Factual Lookup: 'What did the speaker say about the automobile industry?'")
    res2 = skill.ask("What did the speaker say about the automobile industry?")
    print(f"    Classified Intent: {res2.classified_intent}")
    print(f"    Confidence: {res2.confidence}")
    print(f"\nAnswer:\n{res2.answer}")
    if res2.citations:
        print(f"    Top Citation: {res2.citations[0].timestamp} -> {res2.citations[0].text_excerpt}")

    # Test 3: Out-of-scope query
    print("\n[4] Testing Negative Control: 'What did they say about cryptocurrency?'")
    res3 = skill.ask("What did they say about cryptocurrency?")
    print(f"    Classified Intent: {res3.classified_intent}")
    print(f"    Confidence: {res3.confidence}")
    print(f"\nAnswer:\n{res3.answer}")

if __name__ == "__main__":
    main()
