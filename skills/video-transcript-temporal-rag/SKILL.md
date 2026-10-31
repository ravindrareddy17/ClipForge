---
name: video-transcript-temporal-rag
description: High-precision 6-agent video Q&A and whole-video summarization engine with exact timestamp citations.
version: 1.0.0
author: ClipForge AI
category: video-intelligence
tags:
  - video-intelligence
  - rag
  - transcripts
  - whisper
  - timestamps
  - multi-agent
  - react-loop
  - groq
runtime: python3.10+
entrypoint: runner.py
input_schema: schemas/input.schema.json
output_schema: schemas/output.schema.json
license: Apache-2.0
---

# ClipForge Video Intelligence (`video-transcript-temporal-rag`)

A specialized, commercial AI skill for rigorous, evidence-grounded question answering and whole-video summarization over long-form video transcripts.

## Overview

Unlike generic RAG implementations that blindly dump arbitrary text chunks into an LLM prompt, **ClipForge Video Intelligence** executes a controlled **6-Agent ReAct pipeline** designed specifically for temporal media. Every factual assertion is verified against transcript chunks, and every point is anchored with verifiable `[MM:SS]` timestamp citations.

```
User Query / Command
       │
       ▼
1. QueryPlannerAgent        ──> Intent classification & query normalization
       │
       ▼
2. RetrievalAgent           ──> Adaptive hierarchical sampling OR hybrid BM25 search
       │
       ▼
3. TimelineAgent            ──> Chronological alignment & sequence validation
       │
       ▼
4. EvidenceVerificationAgent──> Factual grounding check & numerical confidence (0.0-1.0)
       │
       ▼
5. AnswerSynthesisAgent     ──> Structured markdown with verified [MM:SS] timestamp links
       │
       ▼
6. SafetyGuardrailAgent     ──> Intercepts hallucinations & out-of-scope claims
       │
       ▼
Grounded Response + Verified Citations
```

---

## Key Features

1. **Informal Query Normalizer:** Resolves short, conversational, or malformed queries (e.g., `"what video about"` $\to$ `"What is this video about?"`) before intent routing.
2. **Adaptive Hierarchical Summaries:** Dynamic timeline partitioning (3–8 sections) ensuring full narrative coverage across 1h, 2h, and 3h transcripts without top-k truncation.
3. **Structured Summary Guarantee:** Every video-level summary follows a 3-part layout:
   - 1–2 sentence overarching overview.
   - 3–7 numbered key points with exact `[MM:SS]` timestamps.
   - Identifiable conclusion.
4. **Verifiable Citations:** Returns structured `CitationItem` objects detailing start/end seconds and centered text excerpts.
5. **Anti-Hallucination Guardrails:** Automatically detects out-of-scope queries (confidence $< 0.20$) and returns an honest, grounded refusal: *"I couldn't find sufficient evidence for that in this video."*
6. **Path Traversal Sandboxing:** Validates file extensions (`.json`, `.srt`, `.vtt`, `.txt`), enforces canonical paths within authorized directories, and rejects payloads $> 25\text{ MB}$.
7. **Zero Heavy Media Dependencies:** Decoupled from FFmpeg, OpenCV, and Whisper. Consumes standard JSON transcripts directly. Runs in < 10ms in-memory.

---

## Supported Input Formats

The built-in `TranscriptNormalizer` auto-detects and parses:
- **Official OpenAI Whisper JSON** (`{"segments": [{"start": 0.0, "end": 4.5, "text": "...", "words": [...]}]}`)
- **Flat Word Arrays** (`[{"word": "Hello", "start": 0.0, "end": 0.5}]`)
- **YouTube Transcript API JSON** (`[{"text": "...", "start": 0.0, "duration": 4.5}]`)
- **SubRip (.srt) and WebVTT (.vtt)** subtitles
- **Timestamped Plain Text** (`[01:23] Speaker begins discussion...`)

---

## Quickstart

### Python SDK

```python
from src.skill import VideoIntelligenceSkill

# Initialize skill (supports 'groq', 'gemini', 'ollama', 'openai', 'mock')
skill = VideoIntelligenceSkill(provider="groq")

# Load any transcript file or dictionary
skill.load_transcript("podcast_whisper.json")

# 1. Ask for a whole-video summary
response = skill.ask("what video about")
print(response.answer)

# 2. Ask a specific factual question
response = skill.ask("When did they discuss the automobile industry?")
print(f"Timestamp: {response.citations[0].timestamp}")
```

### Agensi CLI Runner

```bash
# Pass JSON input through STDIN
cat input.json | python runner.py > output.json

# Or pass CLI arguments directly
python runner.py --transcript sample.json --query "what video about" --provider groq
```

---

## Configuration & LLM Providers

| Provider | Environment Variable | Default Model | Notes |
| :--- | :--- | :--- | :--- |
| **Groq** (Default) | `GROQ_API_KEY` | `openai/gpt-oss-20b` | High-speed, cost-effective reasoning model. |
| **Google Gemini** | `GEMINI_API_KEY` | `gemini-2.5-flash` | Ultra-fast multimodal and long-context engine. |
| **Ollama** | Local daemon | `qwen2.5:3b` | 100% offline private execution. |
| **OpenAI** | `OPENAI_API_KEY` | `gpt-4o-mini` | Production cloud fallback. |
| **Mock** | None required | Deterministic | Explicit offline testing (`allow_mock=True`). |

---

## Technical Specifications

- **Execution Latency (In-Memory BM25):** 6 ms
- **Package Footprint:** < 500 KB (Zero torch/opencv/ffmpeg requirements)
- **Memory Footprint:** < 15 MB in memory
- **License:** Apache-2.0
- **Automated Tests:** 46 passing tests in `tests/`
