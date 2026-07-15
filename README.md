# ClipForge AI ⚡

An AI-Powered Content Repurposing Platform to automatically transform long-form videos into viral Shorts, Reels, and TikTok clips.

ClipForge AI is a local-first application, utilizing your local machine's GPU/CPU power for transcribing, scene parsing, face tracking, and language model scoring, keeping your content secure and processing free.

> [!NOTE]
> **Active Development Notice**: ClipForge AI is under ongoing development. New features, enhancements, and processing pipeline upgrades are being introduced regularly.
>
> Official Repository: [github.com/ravindrareddy17/ClipForge](https://github.com/ravindrareddy17/ClipForge.git)

---

## Technical Workflow

```
Import Video ──► Scene Detection ──► Whisper Sync ──► Ollama Moment Scoring
                                                             │
                                                             ▼
                                                    Auto Face-Track Crop
                                                             │
                                                             ▼
                                                    Burn Dynamic Subtitles
                                                             │
                                                             ▼
                                                      Auto Publisher
```

1. **Scene Detection**: Detects scene cuts based on HSV color histogram deviations.
2. **Transcription**: Extracts audio track and generates word-by-word timestamps using `openai-whisper`.
3. **Viral Moment Valuation**: Evaluates transcripts using local Ollama LLMs (`llama3`, `qwen2.5:3b`, etc.) to rank highlights.
4. **Face Tracking Vertical Crop**: Scans frames to find speakers' face coordinates using OpenCV and shifts the 9:16 crop window to center them.
5. **Subtitles Burn**: Renders karaoke-style word-by-word highlighting captions using FFmpeg and ASS (Advanced Substation Alpha) filters.

---

## Step-by-Step Installation

### Prerequisites

1. **FFmpeg**: Ensure `ffmpeg` and `ffprobe` are installed and available on your system environment `PATH`.
2. **Ollama**: Download and install [Ollama](https://ollama.com). Pull at least one language model for virality scoring:
   ```bash
   ollama pull llama3
   # OR
   ollama pull qwen2.5:3b
   ```

### 1. Initialize Virtual Environment (with `uv`)

Initialize a clean Python virtual environment using the `uv` package manager:
```bash
uv venv
```

### 2. Install Dependencies

Install the unified requirements:
```bash
uv pip install -r requirements.txt
```

### 3. Run Ollama Local Models

Ensure Ollama is running locally and pull the target chat and embedding models:
```bash
ollama serve
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

### 4. Run ClipForge AI Dashboard

Launch the Streamlit user interface:
```bash
.venv\Scripts\streamlit run app.py
```
*The dashboard will automatically open at http://localhost:8501*

---

## Local RAG Engine & Pipeline Architecture

ClipForge AI processes video files using a fully offline Retrieval-Augmented Generation (RAG) pipeline:

```
Import Video ──► Whisper Transcription ──► Semantic Chunks ──► local nomic-embed-text ──► ChromaDB Persistent Client
                                                                                                     │
                                                                                                     ▼
Grounded QA response ◄── local qwen2.5:3b ◄── Context Compile ◄── Vector Similarity Query ◄── User Chat Question
```

### Folder Structure

```
ClipForge/
├── app.py                      # Streamlit Multi-Page dashboard interface
├── backend/
│   ├── data/
│   │   ├── clipforge.db        # Relational SQLite database
│   │   └── chromadb/           # ChromaDB vector store directory
│   └── clipforge_engine/
│       ├── db.py               # SQLite database schemas and query helpers
│       ├── pipeline.py         # Background media processing pipeline orchestration
│       ├── rag.py              # Local RAG client, semantic chunking, Chroma integration
│       └── agents.py           # NLP extraction agents (Summary, SEO, Graph, Keyword, Scheduler)
└── README.md                   # Platform documentation
```

---

## User Features & Guides

- **Dashboard**: Track connected distribution accounts and recent pipeline operations.
- **Projects**: Switch or create independent workspaces.
- **Video Library**: Paste video links or monitored channel handles to fetch media.
- **AI Processing**: Live pipeline progress monitor (Whisper, semantic chunking, and vectors mapping).
- **Generated Clips**: Viral moment highlights editor with vertical OpenCV face tracking and dynamic ASS captions.
- **Knowledge Base**: Executive summaries, timelines, keyword tables, and gravity-simulated visual knowledge graphs.
- **AI Chat**: Conversational RAG interface with multi-video comparing, single clip filtering, citations, and clickable timestamps.
- **Video Search**: Natural language semantic query tool with preview link shortcuts.
- **Topics**: Timeline chapters list.
- **Analytics**: Subscriber count, CTR, and watch time daily analytics graphs.
- **Scheduler & Publishing**: Posting slots setup grid and scheduled publication logs.
- **Settings & Logs**: Configure local Ollama ports and inspect raw workflow logs.

---

## Troubleshooting

- **Ollama Offline Error**: Make sure your local server is active on `http://localhost:11434` and the configured model choice exists (`ollama list`).
- **ChromaDB SQLite version errors**: ChromaDB requires SQLite 3.35+. ClipForge automatically uses your local Python virtual environment's built-in libraries.


