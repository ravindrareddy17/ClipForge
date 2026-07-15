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

### 3. Run ClipForge AI Dashboard

Launch the Streamlit user interface:
```bash
.venv\Scripts\streamlit run app.py
```
*The dashboard will automatically open at http://localhost:8501*

---

## User Features & Guides

- **Dashboard**: Track imported files, processing status, and storage parameters.
- **Projects**: Switch and manage distinct media workspace folders.
- **Video Library**: Drag and drop long videos or type an absolute file path on your hard drive for instant scanning.
- **AI Processing**: Live pipeline progress monitor.
- **Generated Clips / Editor**: Review viral segments, adjust crop margins, select custom font/color settings, edit words spelling, and render clips using FFmpeg.
- **Scheduler**: Drag and drop calendar block publisher.
- **Automation Flowchart**: Visual pipeline switchboard.

---

## Technical Concept: Main Channel to User Channels

ClipForge AI handles content repurposing by connecting your **Main Source Channel** (long-form content inputs) to multiple targeted **User Distribution Channels** (short-form distribution outputs):

1. **Main Source Channel Input**: Under **Video Library**, you import long-form podcast or landscape video content which you have rights to repurpose.
2. **AI Analysis & Splitting**: ClipForge AI uses local speech transcription and scene cuts to extract the most engaging standalone segments.
3. **User Channel Publishing**: Under **Channels**, you link individual short-form target channels (such as YouTube Shorts, TikTok, and Instagram Reels). These destinations are designated as the **User Channels** that receive the scheduled clips automatically.

