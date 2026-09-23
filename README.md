# ClipForge AI V2 ⚡

An enterprise-grade, offline-first Video Intelligence, Repurposing, and Agentic RAG Platform with deep timeline reasoning, YouTube channel library ingestion, clickable timestamp navigation, and an interactive **CSE473 AI Lab Studio**.

ClipForge AI V2 operates locally, utilizing local GPU/CPU compute for transcription (`openai-whisper`), dense semantic embedding (`nomic-embed-text`, 768 dimensions), vector search (`ChromaDB`), and agentic reasoning (`qwen2.5:3b` via Ollama).

---

## 🏗️ Architecture Overview

```
                      ┌───────────────────────────────────────────────┐
                      │                 USER INTERFACES               │
                      │  Streamlit Dashboard (8501) | React 19 (5173) │
                      └───────────────────────┬───────────────────────┘
                                              │ HTTP / REST
                                              ▼
                      ┌───────────────────────────────────────────────┐
                      │              FASTAPI ENGINE (8000)            │
                      │  backend/clipforge_engine/main.py             │
                      └───────┬───────────────────────────────┬───────┘
                              │                               │
                ┌─────────────▼──────────────┐  ┌─────────────▼──────────────┐
                │   MULTI-AGENT VIDEO QA     │  │   CSE473 AI LAB ENGINE     │
                │  video_qa_agents.py        │  │   cse473_lab.py            │
                │  • QueryPlannerAgent       │  │  • Unit I: Transformers     │
                │  • RetrievalAgent          │  │  • Unit II: Prompt Eng & Tools
                │  • TimelineAgent           │  │  • Unit III: LoRA & RL     │
                │  • EvidenceVerification    │  │  • Unit VI: Safety & Eval   │
                │  • AnswerSynthesisAgent    │  └────────────────────────────┘
                │  • SafetyGuardrailAgent    │
                └─────────────┬──────────────┘
                              │
                ┌─────────────▼──────────────┐
                │     HYBRID RAG RETRIEVAL   │
                │  rag.py                    │
                │  • Segment-Aware Chunking  │
                │  • BM25 Lexical Scoring    │
                │  • ChromaDB Dense Vectors  │
                │  • Reciprocal Rank Fusion  │
                │  • Chronological Expansion │
                └───────┬────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
┌──────────────────┐          ┌──────────────────┐
│  OLLAMA RUNTIME  │          │  SQLITE STORAGE  │
│  • qwen2.5:3b    │          │  clipforge.db    │
│  • nomic-embed   │          │  • projects/vids │
│    (dim: 768)    │          │  • chunks/memory │
└──────────────────┘          └──────────────────┘
```

---

## 🚀 Key Upgrades in V2

### 1. Multi-Agent Video QA Engine (`backend/clipforge_engine/video_qa_agents.py`)
Replaces naive opening-chunk retrieval with a bounded ($\le 3$ iterations) ReAct loop orchestrated across 6 specialized agent personas:
1. **QueryPlannerAgent**: Analyzes question intent (`factual_lookup`, `chronology`, `summary`, `comparison`, `timestamp_search`), extracts time codes, and plans sub-queries.
2. **RetrievalAgent**: Executes hybrid BM25 + dense vector search with Reciprocal Rank Fusion (RRF).
3. **TimelineAgent**: Aligns video chronological context ($\pm 1$ adjacent chunk window, forward scans for "after" queries).
4. **EvidenceVerificationAgent**: Validates semantic relevance, cross-checks keywords against retrieved transcripts, and rejects unsupported queries.
5. **AnswerSynthesisAgent**: Synthesizes structured, objective answers citing `[MM:SS]` or `[MM:SS–MM:SS]` timestamps.
6. **SafetyGuardrailAgent**: Prevents hallucinations, neutralizes prompt injection payloads embedded in transcript audio, and enforces refusal on ungrounded queries.

### 2. Segment-Aware Hybrid RAG Foundation (`backend/clipforge_engine/rag.py`)
- **Overlapping Chunking**: Target 120–180 words per chunk with 15–20% word overlap. Preserves sentence boundaries and exact start/end timestamps.
- **Dense Vector Search**: Powered by `nomic-embed-text` with validated 768-dimensional float embeddings stored in ChromaDB collections per project.
- **BM25 Lexical Search**: Full-text BM25 index over SQLite transcript chunks with stopword filtering.
- **Reciprocal Rank Fusion (RRF)**: $RRF(d) = \sum \frac{1}{60 + \text{rank}(d)}$, combining lexical precision with dense semantic recall.
- **Chronological Expansion**: Automatically retrieves preceding and succeeding chunks ($\pm 1$) to provide surrounding narrative context.

### 3. YouTube Channel Ingestion (`backend/clipforge_engine/channel.py`)
- Multi-video discovery using flat metadata extraction via `yt-dlp`.
- Batch video ingestion into independent SQLite video records with isolated ChromaDB chunks.
- Channel-wide semantic library search with `[Video Title | MM:SS]` citations.

### 4. Clickable Timestamps
- Real-time regex timestamp extraction (`[MM:SS]` / `[HH:MM:SS]`).
- **Streamlit**: Clickable timestamp buttons that seek the embedded video player (`start_time=st.session_state.seek_time`).
- **React 19 / Vite**: Interactive seek badges under assistant messages with smooth timeline jumping.

### 5. Interactive CSE473 AI Lab Studio (`backend/clipforge_engine/cse473_lab.py`)
Comprehensive educational and laboratory simulator covering:
- **Unit I**: Transformer Attention Heatmaps (softmax dot-product scaling), Subword BPE Tokenization, Feedforward Projection.
- **Unit II**: 6-Paradigm Prompt Engineering Benchmark (Zero-shot, Few-shot, Chain-of-Thought, Directional, Self-Consistency, Least-to-Most), Tool Calling Schema Validator.
- **Unit III**: Low-Rank Adaptation (LoRA) Weight Decomposition ($\Delta W = B \times A$), Multi-Precision Quantization Calculator (FP32, FP16, INT8, INT4), GridWorld Q-Learning RL Simulator.
- **Unit VI**: Automated 20-Question Evaluation Benchmark, Adversarial Prompt Injection Neutralization Test.

---

## 🛠️ Step-by-Step Installation

### Prerequisites
- **Python**: 3.10 to 3.12
- **Node.js**: v18+ (for React Vite frontend)
- **FFmpeg & FFprobe**: Installed and available on system `PATH`
- **Ollama**: Installed and running locally

### 1. Pull Ollama Local Models
```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

### 2. Setup Python Virtual Environment
```bash
# Using uv (recommended) or standard venv
uv venv .venv
.\.venv\Scripts\activate

# Install unified requirements
uv pip install -r requirements.txt
```

### 3. Run the Services

**Option A: FastAPI Engine (Port 8000)**
```bash
.\.venv\Scripts\python.exe -m uvicorn clipforge_engine.main:app --host 0.0.0.0 --port 8000 --reload
```

**Option B: Streamlit Dashboard (Port 8501)**
```bash
.\.venv\Scripts\streamlit.exe run app.py --server.port 8501
```

**Option C: React 19 Frontend (Port 5173)**
```bash
cd frontend
npm install
npm run dev -- --port 5173
```

---

## 📡 API Reference (FastAPI Backend)

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health status, database check, embedding status |
| `/api/chat` | POST | Multi-agent grounded Video QA with timestamp citations |
| `/api/channels/resolve` | POST | Extract video list from YouTube channel URL/handle |
| `/api/channels/import` | POST | Batch import channel videos into pipeline |
| `/api/channels/search` | POST | Cross-video channel library semantic search |
| `/api/cse473/attention-heatmaps` | GET | Unit I: Multi-head self-attention matrix simulator |
| `/api/cse473/tokenizer-comparison` | POST | Unit I: Tokenizer comparison & compression ratio |
| `/api/cse473/transformer-forward` | POST | Unit I: Full forward-pass dimension tracer |
| `/api/cse473/prompt-engineering-compare` | POST | Unit II: 6-paradigm prompt benchmark |
| `/api/cse473/tool-calling-validate` | POST | Unit II: JSON tool schema enforcement tester |
| `/api/cse473/lora-decomposition` | POST | Unit III: LoRA rank $r$ parameter & memory reduction |
| `/api/cse473/quantization-benchmark` | POST | Unit III: FP32 vs FP16 vs INT8 vs INT4 trade-offs |
| `/api/cse473/rl-gridworld-policy` | POST | Unit III: Q-learning policy convergence simulator |
| `/api/cse473/prompt-injection-safety` | POST | Unit VI: 4-vector adversarial injection tester |
| `/api/cse473/evaluation-benchmark` | POST | Unit VI: 20-question evaluation battery runner |

---

## 🧪 Automated Test Suite

A rigorous 20-point test suite validates database integrity, hybrid RAG retrieval, multi-agent workflows, safety guardrails, and syllabus mapping:

```bash
.\.venv\Scripts\python.exe -m unittest tests/test_clipforge_v2.py -v
```

### Verified Test Cases
1. `test_01_project_id_consistency`: Verifies foreign key consistency between videos, chunks, and projects.
2. `test_02_embedding_health`: Asserts `nomic-embed-text` is healthy with true 768-dim vectors.
3. `test_03_zero_vector_rejection`: Asserts all-zero embeddings are rejected.
4. `test_04_chunking_overlap`: Validates 15–20% word overlap across consecutive chunks.
5. `test_05_timestamp_monotonicity`: Enforces strictly non-decreasing timestamps across all chunks.
6. `test_06_bm25_retrieval`: Validates exact lexical matching over SQLite transcript chunks.
7. `test_07_chromadb_retrieval`: Validates dense semantic vector similarity retrieval.
8. `test_08_rrf_scoring`: Validates reciprocal rank fusion score computation.
9. `test_09_context_expansion`: Validates chronological expansion ($\pm 1$ neighbor chunks).
10. `test_10_conversation_memory`: Validates video-isolated multi-turn conversation memory.
11. `test_11_evidence_verification`: Validates factual claim verification against transcript data.
12. `test_12_unsupported_question_handling`: Asserts graceful refusal on topics absent from video.
13. `test_13_prompt_injection_protection`: Validates complete neutralization of adversarial injection attacks.
14. `test_14_channel_video_separation`: Validates multi-video metadata and chunk isolation.
15. `test_15_agent_workflow`: Validates full end-to-end multi-agent Video QA execution.
16. `test_16_tool_selection`: Validates targeted tool invocation (e.g., timestamp search).
17. `test_17_react_loop_limits`: Validates bounded ReAct execution ($\le 3$ iterations).
18. `test_18_citation_generation`: Validates generation of bracketed timestamp citations `[MM:SS]`.
19. `test_19_end_of_video_retrieval`: Validates deep-video retrieval at minute 10+.
20. `test_20_beginning_vs_ending_comparison`: Validates multi-part comparison query retrieval.

---

## 📚 Technical Documentation

Detailed architectural and design specifications are available in `docs/`:
- [System Architecture](docs/ARCHITECTURE.md): Multi-layer design, database schema, data flow diagrams.
- [Hybrid RAG Engine](docs/RAG.md): Chunking algorithms, BM25, ChromaDB, RRF fusion, chronological expansion.
- [Multi-Agent Reasoning](docs/AGENTS.md): 6 specialized personas, ReAct loop, tool registry.
- [Evaluation & Benchmarks](docs/EVALUATION.md): 20-question battery, scoring rubric, acceptance criteria.
- [Security & Prompt Defense](docs/SECURITY.md): Threat model, transcript sanitization, prompt injection isolation.
- [CSE473 Syllabus Mapping](docs/CSE473_RPL_MAPPING.md): 40 topics across Units I through VI mapped to exact source files.

---

## 📄 License
MIT License. Developed for advanced video intelligence and research.
