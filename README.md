# ClipForge AI V2 ⚡

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.42+-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io)
[![React](https://img.shields.io/badge/React-19.0-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An enterprise-grade, privacy-first **Video Intelligence, Repurposing, and Multi-Agent RAG Platform** with deep timeline reasoning, YouTube channel library ingestion, clickable timestamp navigation, and an interactive **CSE473 AI Lab Studio**.

ClipForge AI V2 operates seamlessly in both **offline local compute** (via Ollama & Whisper) and **blazing-fast cloud inference** (via Groq Cloud, Google Gemini, and AWS Bedrock).

---

## 📑 Table of Contents

- [Key Capabilities](#-key-capabilities)
- [System Architecture](#-system-architecture)
- [Multi-LLM & Cloud Providers](#-multi-llm--cloud-providers)
- [Repository Structure](#-repository-structure)
- [Prerequisites & Installation](#-prerequisites--installation)
- [Quick Start Guide](#-quick-start-guide)
  - [1. Streamlit Dashboard](#1-streamlit-dashboard-primary-gui)
  - [2. FastAPI Backend Engine](#2-fastapi-backend-engine)
  - [3. React 19 Frontend](#3-react-19-modern-web-ui)
- [Core Engines Deep Dive](#-core-engines-deep-dive)
  - [Multi-Agent Video QA Engine](#1-multi-agent-video-qa-engine)
  - [Whole-Video Summarization & Intent Routing](#2-whole-video-summarization--intent-routing)
  - [Hybrid RAG Retrieval Foundation](#3-hybrid-rag-retrieval-foundation)
  - [YouTube Channel Library Ingestion](#4-youtube-channel-library-ingestion)
  - [Interactive CSE473 AI Lab Studio](#5-interactive-cse473-ai-lab-studio)
- [FastAPI REST API Reference](#-fastapi-rest-api-reference)
- [Automated Testing & Verification](#-automated-testing--verification)
- [Security & Secrets Management](#-security--secrets-management)
- [Technical Documentation](#-technical-documentation)
- [License](#-license)
- [Project Status & Ongoing Improvements](#-project-status--ongoing-improvements)

---

## 🌟 Key Capabilities

- **Multi-Agent Video QA**: 6 specialized ReAct agents coordinate query planning, hybrid search, timeline expansion, factual verification, grounded synthesis, and prompt-injection safety.
- **Whole-Video Summaries with Jump Timestamps**: Handles informal queries (e.g., *"what video about"*), assembling executive summaries and balanced timeline anchors with clickable `[MM:SS]` jump links.
- **Hybrid RAG (BM25 + Dense ChromaDB)**: Reciprocal Rank Fusion (RRF) combines BM25 lexical precision with 768-dimensional `nomic-embed-text` dense vectors.
- **Flexible Multi-LLM Runtime**: Seamlessly switch between local offline models (Ollama `qwen2.5:3b`, `llama3.2`) and high-speed cloud providers (Groq `openai/gpt-oss-20b`, Google Gemini `gemini-2.5-flash`, AWS Bedrock).
- **Automated Video Repurposing**: Speech transcription (`openai-whisper`), hook detection, sentiment scoring, viral shorts detection, and 9:16 vertical video re-framing.
- **YouTube Channel Ingestion**: Batch video discovery and indexing via `yt-dlp` with cross-video library semantic search.
- **Dual Modern Interfaces**: Streamlit Pro Studio (:8501) for rich analysis & timeline playback, plus a standalone React 19 + Vite frontend (:5173).
- **Interactive AI Lab (CSE473)**: Built-in visual simulators for Transformer attention heatmaps, 6 prompt engineering paradigms, LoRA rank decomposition, quantization, and RL GridWorld.

---

## 🏗️ System Architecture

```
                              ┌───────────────────────────────────────────────┐
                              │                 USER INTERFACES               │
                              │  Streamlit Studio (8501) | React 19 (5173)    │
                              └───────────────────────┬───────────────────────┘
                                                      │ HTTP / REST / SSE
                                                      ▼
                              ┌───────────────────────────────────────────────┐
                              │              FASTAPI ENGINE (8000)            │
                              │         backend/clipforge_engine/main.py      │
                              └───────┬───────────────────────────────┬───────┘
                                      │                               │
                        ┌─────────────▼──────────────┐  ┌─────────────▼──────────────┐
                        │   MULTI-AGENT VIDEO QA     │  │   CSE473 AI LAB ENGINE     │
                        │  video_qa_agents.py        │  │   cse473_lab.py            │
                        │  • QueryPlannerAgent       │  │  • Unit I: Transformers     │
                        │  • RetrievalAgent          │  │  • Unit II: Prompt Eng      │
                        │  • TimelineAgent           │  │  • Unit III: LoRA & RL     │
                        │  • EvidenceVerification    │  │  • Unit VI: Safety & Eval   │
                        │  • AnswerSynthesisAgent    │  └────────────────────────────┘
                        │  • SafetyGuardrailAgent    │
                        └─────────────┬──────────────┘
                                      │
                        ┌─────────────▼──────────────┐
                        │     HYBRID RAG RETRIEVAL   │
                        │  rag.py                    │
                        │  • Segment-Aware Chunks    │
                        │  • BM25 Lexical Ranking    │
                        │  • ChromaDB Dense Vectors  │
                        │  • Reciprocal Rank Fusion  │
                        │  • Chronological Expansion │
                        └───────┬────────────────────┘
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
       ┌──────────────────┐          ┌──────────────────┐
       │   INFERENCE LLM  │          │    PERSISTENCE   │
       │  • Groq Cloud    │          │  • SQLite DB     │
       │  • Google Gemini │          │    (clipforge.db)│
       │  • Ollama Local  │          │  • ChromaDB      │
       │  • AWS Bedrock   │          │    (Dense Vectors)
       └──────────────────┘          └──────────────────┘
```

---

## ⚡ Multi-LLM & Cloud Providers

ClipForge AI V2 features a unified, fault-tolerant LLM client (`backend/clipforge_engine/llm_client.py`) supporting multiple execution backends:

| Provider | Default Model | Fallback Models | Best For |
|---|---|---|---|
| **Groq Cloud** | `openai/gpt-oss-20b` | `qwen/qwen3.8-27b`, `llama-3.3-70b-versatile` | Ultra-fast agent reasoning & synthesis (< 1.5s) |
| **Google Gemini** | `gemini-2.5-flash` | `gemini-flash-latest`, `gemini-2.5-flash-lite` | Large-context multimodal processing |
| **Ollama (Local)**| `qwen2.5:3b` | `llama3.2:latest`, `mistral:latest` | 100% offline, privacy-first private compute |
| **AWS Bedrock** | `anthropic.claude-3-haiku` | `anthropic.claude-3-5-sonnet` | Enterprise cloud deployments |

> **Reasoning Model Support**: Built-in support for reasoning models (`gpt-oss-20b`, `deepseek`, `qwen`) allocating a 1500+ token buffer to prevent thinking tokens from truncating final answers.

---

## 📁 Repository Structure

```text
ai forge/
├── app.py                             # Streamlit Main Application (Dashboard, Video Chat, Lab)
├── requirements.txt                   # Unified Python dependencies
├── packages.txt                       # System dependencies (FFmpeg)
├── backend/
│   └── clipforge_engine/
│       ├── main.py                    # FastAPI application & REST routing
│       ├── video_qa_agents.py         # 6-Agent ReAct loop & query normalization
│       ├── rag.py                     # Hybrid RAG (BM25 + ChromaDB + RRF)
│       ├── llm_client.py              # Multi-provider LLM client (Groq, Gemini, Ollama)
│       ├── channel.py                 # YouTube channel batch ingestion & search
│       ├── db.py                      # SQLite database schema, chunks, and metadata
│       ├── cse473_lab.py              # CSE473 AI Lab simulation modules
│       ├── video_processor.py         # Video downloading, frame extraction, clipping
│       └── whisper_transcriber.py     # Local Whisper transcription engine
├── frontend/                          # React 19 + Vite Modern Frontend
│   ├── src/
│   │   ├── components/                # Glassmorphic UI, Chat, Timestamps, Channels
│   │   ├── App.tsx                    # React Root Component
│   │   └── main.tsx                   # Entry point
│   ├── package.json                   # Frontend dependencies
│   └── vite.config.ts                 # Vite bundler configuration
├── tests/
│   ├── test_clipforge_v2.py           # 20-Point Regression & Safety Test Suite
│   └── test_video_summary_intent.py   # Video summary intent & routing test battery
└── docs/                              # Detailed Technical Documentation
    ├── ARCHITECTURE.md                # System layers & data pipelines
    ├── RAG.md                         # Hybrid retrieval & RRF mathematical formulation
    ├── AGENTS.md                      # ReAct agent specifications & tool definitions
    ├── EVALUATION.md                  # Evaluation rubric & benchmark battery
    ├── SECURITY.md                    # Prompt injection & adversarial defense
    └── CSE473_RPL_MAPPING.md          # Academic syllabus topic mapping
```

---

## 🛠️ Prerequisites & Installation

### 1. System Requirements
- **Python**: 3.10 to 3.12
- **Node.js**: v18+ (required for React frontend)
- **FFmpeg & FFprobe**: Must be installed and present on system `PATH`
  - *Windows*: `winget install Gyan.FFmpeg`
  - *Ubuntu/Debian*: `sudo apt-get install ffmpeg`
  - *macOS*: `brew install ffmpeg`

### 2. Python Virtual Environment Setup

```bash
# Clone the repository
git clone https://github.com/ravindrareddy17/ClipForge.git
cd ClipForge

# Create and activate virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. (Optional) Local Ollama Models for Offline Inference

If you wish to run 100% offline without cloud API keys:
```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

---

## 🚀 Quick Start Guide

### 1. Streamlit Dashboard (Primary GUI)
Launch the comprehensive studio featuring video ingestion, player seeking, clip repurposing, AI video chat, and the CSE473 Lab:

```bash
streamlit run app.py --server.port 8501
```
Open **`http://localhost:8501`** in your browser.

### 2. FastAPI Backend Engine
Launch the headless high-performance REST API with interactive Swagger docs:

```bash
# Set PYTHONPATH to include backend
# Windows PowerShell:
$env:PYTHONPATH='backend'; python -m uvicorn clipforge_engine.main:app --host 0.0.0.0 --port 8000 --reload

# Linux / macOS:
PYTHONPATH=backend python -m uvicorn clipforge_engine.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation available at: **`http://localhost:8000/docs`**

### 3. React 19 Modern Web UI
Launch the lightweight, modern glassmorphic web application:

```bash
cd frontend
npm install
npm run dev -- --port 5173
```
Open **`http://localhost:5173`** in your browser.

---

## 🔬 Core Engines Deep Dive

### 1. Multi-Agent Video QA Engine
Located in `backend/clipforge_engine/video_qa_agents.py`, the system implements a bounded ($\le 3$ iterations) ReAct loop orchestrated across 6 specialized agent personas:

1. **`QueryPlannerAgent`**: Normalizes informal queries, classifies user intent (`video_summary`, `factual_lookup`, `chronology`, `comparison`, `timestamp_search`), and plans search strategies.
2. **`RetrievalAgent`**: Executes hybrid BM25 + dense ChromaDB retrieval with Reciprocal Rank Fusion (RRF).
3. **`TimelineAgent`**: Aligns chronological context, inspecting $\pm 1$ neighbor windows and resolving relative temporal references (*"what happened after X"*).
4. **`EvidenceVerificationAgent`**: Validates whether retrieved chunks contain semantic evidence. Computes confidence scores and rejects unsupported claims.
5. **`AnswerSynthesisAgent`**: Generates structured, timestamp-cited answers strictly formatted with bracketed timecodes (`[MM:SS]` or `[MM:SS–MM:SS]`).
6. **`SafetyGuardrailAgent`**: Enforces strict boundaries against out-of-domain queries, sanitizes malicious prompt injections embedded in audio transcripts, and prevents hallucinations.

---

### 2. Whole-Video Summarization & Intent Routing
Standard vector search fails on queries like *"what video about"* or *"summarize this"* because broad questions lack specific semantic keywords. ClipForge AI V2 solves this via:

- **Informal Query Normalization**: Automatically converts `"what video about"`, `"explain video"`, and `"summary"` into canonical queries.
- **Dedicated `tool_assemble_video_summary_context`**: Deterministically samples balanced timeline anchors:
  - Video title and total duration
  - Precomputed executive summary
  - Opening thesis chunks (minutes 0:00–2:00)
  - Chronological middle anchors (sampled at 25%, 50%, and 75% duration)
  - Closing conclusion chunks (final minutes)
- **Clickable Timestamp Buttons**: Both Streamlit and React interfaces parse timestamps like `[02:15]` into interactive buttons that immediately seek the embedded video player to that exact second.

---

### 3. Hybrid RAG Retrieval Foundation
Located in `backend/clipforge_engine/rag.py`:

- **Segment-Aware Chunking**: Chunks text at 120–180 words with a 15–20% sliding word overlap, preserving sentence boundaries and millisecond-level time offsets.
- **Dense Vector Search**: Embeds chunks using `nomic-embed-text` into 768-dimensional vectors stored in project-isolated ChromaDB collections.
- **Lexical BM25 Ranking**: Fast full-text search with token normalization and stop-word filtering over SQLite transcript chunks.
- **Reciprocal Rank Fusion (RRF)**:
  $$\text{RRF}(d) = \sum_{m \in \{\text{Dense}, \text{BM25}\}} \frac{1}{60 + \text{rank}_m(d)}$$
- **Chronological Expansion**: Automatically pulls adjacent chunks ($\pm 1$) for top hits to ensure complete context.

---

### 4. YouTube Channel Library Ingestion
Located in `backend/clipforge_engine/channel.py`:

- Resolves channel handles, URLs, and playlists using `yt-dlp` flat-extraction.
- Discovers and tracks multi-video libraries without requiring video downloads upfront.
- Enables **cross-video library semantic search**, answering queries like *"Which video discussed quantum computing?"* with video title and timestamp citations: `[Video Title | MM:SS]`.

---

### 5. Interactive CSE473 AI Lab Studio
Located in `backend/clipforge_engine/cse473_lab.py`:

- **Unit I: Transformer Fundamentals**:
  - Scaled Dot-Product Attention Heatmaps: $\text{Attention}(Q,K,V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$
  - BPE Subword Tokenization & compression ratio analyzer
  - Feedforward projection and dimension tracer ($d_{\text{model}} \to d_{\text{ff}} \to d_{\text{model}}$)
- **Unit II: Prompt Engineering & Tool Calling**:
  - 6-Paradigm Prompt Benchmark: Zero-shot, Few-shot, Chain-of-Thought (CoT), Directional, Self-Consistency, and Least-to-Most
  - JSON Tool Calling Schema validation and parameter extraction
- **Unit III: Fine-Tuning & Reinforcement Learning**:
  - LoRA (Low-Rank Adaptation) Matrix Decomposition: $\Delta W = B \times A$ with rank $r$ parameter savings calculator
  - Multi-Precision Quantization Calculator: VRAM & memory bandwidth analysis across FP32, FP16, INT8, and INT4
  - GridWorld Q-Learning RL convergence simulator
- **Unit VI: Safety, Robustness & Evaluation**:
  - 4-Vector Prompt Injection Neutralization Test (direct override, base64 payload, roleplay jailbreak, system prompt extraction)
  - 20-Question Automated Evaluation Battery with accuracy, groundedness, and citation verification metrics

---

## 📡 FastAPI REST API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | `GET` | Health check, active LLM provider, database status |
| `/api/chat` | `POST` | Multi-agent grounded Video QA with timestamp citations |
| `/api/channels/resolve` | `POST` | Extract video list and metadata from YouTube channel URL |
| `/api/channels/import` | `POST` | Batch import channel videos into indexing pipeline |
| `/api/channels/search` | `POST` | Cross-video channel library semantic search |
| `/api/cse473/attention-heatmaps` | `GET` | Unit I: Multi-head self-attention matrix generator |
| `/api/cse473/tokenizer-comparison` | `POST` | Unit I: Tokenizer comparison & compression ratio |
| `/api/cse473/transformer-forward` | `POST` | Unit I: Full forward-pass dimension tracer |
| `/api/cse473/prompt-engineering-compare` | `POST` | Unit II: 6-paradigm prompt benchmark |
| `/api/cse473/tool-calling-validate` | `POST` | Unit II: JSON tool schema enforcement tester |
| `/api/cse473/lora-decomposition` | `POST` | Unit III: LoRA rank $r$ parameter & memory reduction |
| `/api/cse473/quantization-benchmark` | `POST` | Unit III: FP32 vs FP16 vs INT8 vs INT4 trade-offs |
| `/api/cse473/rl-gridworld-policy` | `POST` | Unit III: Q-learning policy convergence simulator |
| `/api/cse473/prompt-injection-safety` | `POST` | Unit VI: 4-vector adversarial injection tester |
| `/api/cse473/evaluation-benchmark` | `POST` | Unit VI: 20-question evaluation battery runner |

---

## 🧪 Automated Testing & Verification

ClipForge AI V2 includes comprehensive automated test suites to ensure zero regressions:

### 1. Video Summary & Intent Routing Suite
Tests informal query normalization, intent classification, whole-video sampling, and diagnostics:
```bash
python -m unittest tests/test_video_summary_intent.py -v
```
```text
test_01_query_normalization ... ok
test_02_intent_classification_variants ... ok
test_03_detailed_questions_intent_routing ... ok
test_04_whole_video_evidence_assembly ... ok
test_05_unindexed_video_diagnostic ... ok
test_06_video_summary_full_pipeline_execution ... ok
----------------------------------------------------------------------
Ran 6 tests in 2.133s - ALL PASS
```

### 2. Full System Regression & Safety Battery
20-point test battery covering ChromaDB isolation, RRF scoring, ReAct loops, prompt injections, and deep-video retrieval:
```bash
python -m unittest tests/test_clipforge_v2.py -v
```
```text
Ran 20 tests in 145.898s - ALL PASS (20/20)
```

---

## 🔐 Security & Secrets Management

ClipForge AI strictly enforces security and privacy safeguards:
- **API Key Masking**: All API keys (Groq, Gemini, Bedrock) are scrubbed and masked (`••••••••`) across logs, error traces, and user interfaces.
- **Flexible Secret Resolution**: Keys are resolved in order from:
  1. Streamlit Secrets (`st.secrets`) or `.streamlit/secrets.toml`
  2. Operating System Environment Variables (`GROQ_API_KEY`, `GEMINI_API_KEY`)
  3. Local encrypted SQLite configuration table
- **Adversarial Audio Sanitization**: Transcripts are passed through defensive safety guardrails to neutralize indirect prompt injection payloads hidden within video speech.

---

## 📚 Technical Documentation

For in-depth architectural and mathematical specifications, refer to the `docs/` directory:
- [System Architecture Specification](docs/ARCHITECTURE.md)
- [Hybrid RAG & RRF Retrieval Engine](docs/RAG.md)
- [Multi-Agent Reasoning & Tool Registry](docs/AGENTS.md)
- [Evaluation Metrics & Benchmark Rubric](docs/EVALUATION.md)
- [Security & Prompt Injection Defense](docs/SECURITY.md)
- [CSE473 Academic Syllabus Mapping](docs/CSE473_RPL_MAPPING.md)

---

## 📄 License

This project is licensed under the **MIT License**. Developed for high-performance video intelligence, multimodal RAG research, and enterprise repurposing.

---

## 🚧 Project Status & Ongoing Improvements

> [!NOTE]
> **Active Development & Evolution**: ClipForge AI V2 is under active, continuous development. While core functionalities—including Multi-Agent Video QA, whole-video summarization, hybrid RAG retrieval, YouTube channel ingestion, and the CSE473 AI Lab Studio—are operational and rigorously tested, this project is continually evolving and still undergoing improvements.

### 🔮 Planned Enhancements & Changes Needed

1. **Multimodal Visual & OCR RAG**:
   - Integrating vision-language models (e.g., CLIP, VideoLLaMA, Qwen2-VL) to index visual frames, slides, charts, on-screen text/code, and scene transitions alongside spoken audio transcripts.

2. **Animated Subtitles & Automated B-Roll Insertion**:
   - Implementing word-by-word karaoke-style animated captions and automated semantic stock B-roll insertion for generated 9:16 vertical shorts.

3. **Asynchronous Distributed Processing**:
   - Adding background task queues (Celery / Redis / RQ) for high-throughput batch video ingestion, distributed Whisper GPU transcription, and background clip rendering.

4. **UI/UX Polish & Responsive Theming**:
   - Refining component color schemes, improving accessibility and contrast ratios, adding mobile-responsive layouts, and integrating custom waveform audio scrubbers.

5. **Direct Social Media Export**:
   - One-click publishing and scheduled export to YouTube Shorts, Instagram Reels, and TikTok via official developer APIs.

6. **Expanded Multilingual Translation & Synchronized Dubbing**:
   - Cross-lingual transcript translation and AI voice dubbing to repurpose video content across multiple languages seamlessly.

7. **Collaborative Multi-User Workspaces**:
   - Introducing team projects, role-based access control (RBAC), and shared video knowledge bases.

---
Contributions, feedback, and issue reports are welcome as we actively shape and expand ClipForge AI!

