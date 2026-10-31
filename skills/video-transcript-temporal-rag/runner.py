#!/usr/bin/env python3
"""
Agensi.io CLI Entrypoint for video-transcript-temporal-rag.
Accepts input JSON from STDIN or arguments, runs the 6-agent ReAct pipeline,
and outputs strict JSON matching schemas/output.schema.json to STDOUT.
Hardened against silent mock fallbacks and security violations.
"""

import sys
import json
import argparse
from pathlib import Path

# Ensure UTF-8 output on all operating systems (prevents cp1252 charmap errors on Windows)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add skill directory to sys.path
SKILL_ROOT = Path(__file__).resolve().parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from src.skill import VideoIntelligenceSkill
from src.security import SecurityError
from src.llm.exceptions import LLMProviderError


def parse_args():
    parser = argparse.ArgumentParser(description="Video Transcript Temporal RAG Skill Runner")
    parser.add_argument("--input", "-i", type=str, help="Path to input JSON payload")
    parser.add_argument("--transcript", "-t", type=str, help="Path to transcript JSON / text")
    parser.add_argument("--query", "-q", type=str, help="User query / question")
    parser.add_argument("--provider", "-p", type=str, default="groq", help="LLM provider (groq, gemini, ollama, openai, mock)")
    parser.add_argument("--model", "-m", type=str, help="LLM model name")
    parser.add_argument("--allow-mock", action="store_true", default=False, help="Explicitly enable MockProvider for offline testing")
    return parser.parse_args()


def main():
    args = parse_args()
    input_data = {}

    # Case 1: Read from file if --input provided
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            input_data = json.load(f)

    # Case 2: Read from direct CLI flags
    elif args.transcript and args.query:
        input_data = {
            "transcript": args.transcript,
            "query": args.query,
            "llm_config": {
                "provider": args.provider,
                "model": args.model,
                "allow_mock": args.allow_mock
            }
        }

    # Case 3: Read from STDIN if pipe exists
    elif not sys.stdin.isatty():
        raw_stdin = sys.stdin.read().strip()
        if raw_stdin:
            try:
                input_data = json.loads(raw_stdin)
            except Exception as e:
                error_res = {
                    "answer": f"Invalid JSON on STDIN: {e}",
                    "confidence": 0.0,
                    "classified_intent": "FACTUAL_LOOKUP",
                    "normalized_query": "",
                    "citations": [],
                    "audit_trail": [f"STDIN JSON parse error: {e}"]
                }
                print(json.dumps(error_res, indent=2))
                sys.exit(1)

    if not input_data or "transcript" not in input_data or "query" not in input_data:
        parser = argparse.ArgumentParser()
        parser.print_help()
        sys.exit(1)

    # Extract configuration
    transcript_src = input_data["transcript"]
    query = input_data["query"]
    video_title = input_data.get("video_title", "Video")
    video_id = input_data.get("video_id", "video_default")
    llm_cfg = input_data.get("llm_config", {})

    provider = llm_cfg.get("provider", args.provider)
    model = llm_cfg.get("model", args.model)
    api_key = llm_cfg.get("api_key")
    allow_mock = llm_cfg.get("allow_mock", args.allow_mock)

    try:
        skill = VideoIntelligenceSkill(
            provider=provider,
            model=model,
            api_key=api_key,
            allow_mock=allow_mock
        )
        skill.load_transcript(transcript_src, video_id=video_id, video_title=video_title)
        result = skill.ask(query)
        output_payload = result.model_dump()
        print(json.dumps(output_payload, indent=2))

    except (LLMProviderError, SecurityError, FileNotFoundError, Exception) as e:
        error_res = {
            "answer": f"Skill Execution Error: {e}",
            "confidence": 0.0,
            "classified_intent": "FACTUAL_LOOKUP",
            "normalized_query": query,
            "citations": [],
            "audit_trail": [f"Execution failed: {type(e).__name__}: {e}"]
        }
        print(json.dumps(error_res, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
