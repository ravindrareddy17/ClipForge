import os
import sys
import json
import uuid
import requests
from datetime import datetime
import streamlit as st

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

# Swap in pysqlite3 for Streamlit Cloud SQLite >= 3.35 compatibility
try:
    import pysqlite3
    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

import sqlite3

from clipforge_engine.db import (
    init_db,
    get_projects, create_project,
    get_videos, get_video, create_video, update_video_status,
    get_clips, create_clip, get_all_clips,
    get_settings, update_setting, get_db_connection,
    get_schedules, create_schedule, delete_schedule,
    add_chat_message, get_chat_history, clear_chat_history,
    get_pipeline_stages
)
from clipforge_engine.rag import (
    query_similar_chunks, generate_grounded_answer
)

# Run database setup
init_db()

# Page config
st.set_page_config(
    page_title="ClipForge AI — Viral Shorts & Video Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper to test connection to Ollama instance
def test_ollama_connection(url):
    try:
        headers = {"ngrok-skip-browser-warning": "1"}
        resp = requests.get(f"{url}/api/tags", headers=headers, timeout=5)
        if resp.status_code == 200:
            models_data = resp.json().get("models", [])
            models = [m["name"] for m in models_data]
            return True, models
    except Exception as e:
        return False, str(e)
    return False, "Failed to connect"

# Modern, High-Contrast Minimalist Dark Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* Base theme */
    .stApp {
        background-color: #090d16;
        color: #f1f5f9;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        letter-spacing: -0.02em;
    }
    
    /* Clean Dark Cards */
    div[data-testid="stVerticalBlockBorderDiv"] {
        background: #111827 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
        margin-bottom: 1.25rem !important;
    }
    div[data-testid="stVerticalBlockBorderDiv"]:hover {
        border-color: #374151 !important;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0d121f !important;
        border-right: 1px solid #1f2937 !important;
    }
    section[data-testid="stSidebar"] button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #94a3b8 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 12px 16px !important;
        margin: 4px 0 !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.15s ease !important;
    }
    section[data-testid="stSidebar"] button:hover {
        background: #1e293b !important;
        color: #60a5fa !important;
    }
    
    /* Input styling */
    div[data-testid="stTextInput"] input, 
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stSelectbox"] > div {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
    }
    
    /* Chat bubbles */
    div[data-testid="stChatMessage"] {
        background-color: #111827 !important;
        border: 1px solid #1f2937 !important;
        border-radius: 14px !important;
        padding: 14px 18px !important;
        margin-bottom: 10px !important;
    }
    div[data-testid="stChatMessage"][data-testid*="user"] {
        background-color: #1e293b !important;
        border-color: #334155 !important;
    }
    div[data-testid="stChatMessage"] p, div[data-testid="stChatMessage"] span, div[data-testid="stChatMessage"] li {
        color: #f1f5f9 !important;
        font-size: 0.95rem !important;
        line-height: 1.65 !important;
    }
    
    /* Status Badges */
    .status-pill {
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-block;
    }
    .pill-green { background: #064e3b; color: #34d399; border: 1px solid #059669; }
    .pill-blue { background: #1e3a5f; color: #60a5fa; border: 1px solid #2563eb; }
    .pill-yellow { background: #451a03; color: #f59e0b; border: 1px solid #b45309; }
    
    /* Primary Action Buttons */
    div.stButton > button[kind="primary"],
    div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
        transition: transform 0.1s ease !important;
    }
    div.stButton > button[kind="primary"]:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.45) !important;
    }
</style>
""", unsafe_allow_html=True)

# State initialization
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Create Clips"
if 'chat_session_id' not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

# Load settings from DB or Secrets
db_settings = {}
try:
    db_settings = get_settings()
except Exception:
    pass

default_ollama_url = db_settings.get("ollama_url", "http://localhost:11434")
default_ollama_model = db_settings.get("ollama_model", "qwen2.5:3b")
default_embedding_model = db_settings.get("embedding_model", "nomic-embed-text")

try:
    if "OLLAMA_URL" in st.secrets:
        default_ollama_url = st.secrets["OLLAMA_URL"]
    if "OLLAMA_MODEL" in st.secrets:
        default_ollama_model = st.secrets["OLLAMA_MODEL"]
    if "OLLAMA_EMBEDDING_MODEL" in st.secrets:
        default_embedding_model = st.secrets["OLLAMA_EMBEDDING_MODEL"]
except Exception:
    pass

if 'ollama_url' not in st.session_state:
    st.session_state.ollama_url = default_ollama_url
if 'ollama_model' not in st.session_state:
    st.session_state.ollama_model = default_ollama_model
if 'embedding_model' not in st.session_state:
    st.session_state.embedding_model = default_embedding_model

# Ensure at least 1 workspace
projects = get_projects()
if not projects:
    create_project("Workspace 1", "Default workspace")
    projects = get_projects()

# Sidebar: Simple 3-Tab Navigation
with st.sidebar:
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 24px; padding-top: 4px;'>
        <div style='width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%); display: flex; align-items: center; justify-content: center; font-weight: 900; color: white; font-size: 1.25rem; box-shadow: 0 4px 14px rgba(37,99,235,0.4);'>⚡</div>
        <div>
            <h2 style='margin: 0; font-size: 1.25rem; font-weight: 800; color: #ffffff;'>ClipForge AI</h2>
            <span style='font-size: 0.68rem; color: #60a5fa; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;'>Video Repurposing</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    project_names = [p["name"] for p in projects]
    selected_project_name = st.selectbox("Active Workspace", project_names)
    active_project = next(p for p in projects if p["name"] == selected_project_name)

    st.markdown("<hr style='border-color: #1f2937; margin: 16px 0;'>", unsafe_allow_html=True)

    # Clean 3 Navigation Tabs
    nav_tabs = [
        ("Create Clips", "⚡"),
        ("AI Video Chat", "💬"),
        ("Library & Settings", "⚙️")
    ]

    for tab_name, icon in nav_tabs:
        is_active = st.session_state.active_tab == tab_name
        label = f"{icon}  {tab_name}" if not is_active else f"👉 {icon}  {tab_name}"
        if st.button(label, key=f"nav_{tab_name}", use_container_width=True):
            st.session_state.active_tab = tab_name
            st.rerun()

    st.markdown("<hr style='border-color: #1f2937; margin: 20px 0;'>", unsafe_allow_html=True)
    
    # Simple Ollama Status Badge
    is_online, models_list = test_ollama_connection(st.session_state.ollama_url)
    if is_online:
        st.markdown(f"<span class='status-pill pill-green'>● Ollama Online ({len(models_list)} models)</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"<span class='status-pill pill-yellow'>● Ollama Offline (Local Mode)</span>", unsafe_allow_html=True)

# Fetch database records for active workspace
videos = get_videos(active_project["id"])
tab = st.session_state.active_tab

# ============================================================
# TAB 1: CREATE CLIPS (The Core Repurposing Engine)
# ============================================================
if tab == "Create Clips":
    col_t1, col_t2 = st.columns([9, 3])
    with col_t1:
        st.markdown("<h1 style='margin:0; font-size:1.85rem;'>⚡ Create Viral Shorts</h1>", unsafe_allow_html=True)
        st.caption("Paste any YouTube link or video file to automatically extract engaging vertical clips with subtitles.")
    with col_t2:
        if st.button("🔄 Refresh Page", use_container_width=True):
            st.rerun()

    # Input Box: Simple, Clean, Prominent
    with st.container(border=True):
        st.write("### 📥 Ingest Video")
        with st.form("simple_import_form", clear_on_submit=True):
            col_in1, col_in2 = st.columns([9, 3])
            with col_in1:
                url_input = st.text_input(
                    "Video Link or File Path:",
                    placeholder="e.g. https://www.youtube.com/watch?v=dQw4w9WgXcQ or sample.mp4",
                    label_visibility="collapsed"
                )
            with col_in2:
                submit_btn = st.form_submit_button("⚡ Generate Viral Clips", use_container_width=True)

            if submit_btn and url_input:
                target = url_input.strip()
                clean_name = target.split("?")[0].split("/")[-1]
                
                # Create video record and CAPTURE its real ID
                vid_id = create_video(
                    project_id=active_project["id"],
                    filename=f"Video: {clean_name}",
                    file_path=target
                )
                
                # Launch background processing pipeline
                from clipforge_engine.pipeline import run_processing_pipeline
                import threading
                import asyncio
                threading.Thread(target=lambda: asyncio.run(run_processing_pipeline(vid_id))).start()
                
                st.success(f"Processing started! Extracting speech, scenes, and viral hooks in the background.")
                st.rerun()

    # If videos exist, show active video selector & its clips
    if not videos:
        st.info("No videos in this workspace yet. Paste a YouTube link above to create your first set of clips.")
    else:
        vid_options = {v["filename"]: v["id"] for v in videos}
        selected_vid_title = st.selectbox("Select Video:", list(vid_options.keys()))
        selected_vid_id = vid_options[selected_vid_title]
        current_video = next(v for v in videos if v["id"] == selected_vid_id)

        # Processing status banner
        if current_video["status"] in ["pending", "processing"]:
            st.info(f"⏳ **{current_video['filename']}** is currently processing in the background. Generating audio, transcribing with Whisper, and scoring hooks...")
            col_rf1, col_rf2 = st.columns([3, 9])
            with col_rf1:
                if st.button("🔄 Check Status Now", use_container_width=True):
                    st.rerun()

        # Load clips for this video
        conn = get_db_connection()
        clips = conn.execute("SELECT * FROM clips WHERE video_id = ? ORDER BY score DESC", (selected_vid_id,)).fetchall()
        conn.close()

        if not clips and current_video["status"] == "completed":
            st.warning("No clips were extracted. The video audio may have been too short or silent.")
            if st.button("⚡ Re-Run Extraction Pipeline"):
                from clipforge_engine.pipeline import run_processing_pipeline
                import threading
                import asyncio
                threading.Thread(target=lambda: asyncio.run(run_processing_pipeline(selected_vid_id))).start()
                st.rerun()
        elif clips:
            st.markdown(f"### 🔥 Extracted Viral Moments ({len(clips)} Ready)")
            
            # Display clips cleanly
            for c in clips:
                with st.container(border=True):
                    col_c1, col_c2 = st.columns([7, 5])
                    with col_c1:
                        st.markdown(f"<h3 style='margin:0 0 6px 0;'>{c['title']}</h3>", unsafe_allow_html=True)
                        st.markdown(
                            f"<span class='status-pill pill-green'>🔥 {c['score']}% VIRAL SCORE</span> &nbsp; "
                            f"<span style='color:#94a3b8; font-size:0.85rem;'>⏱ Duration: <b>{int(c['duration'])}s</b> ({int(c['start_time'])}s - {int(c['end_time'])}s)</span>",
                            unsafe_allow_html=True
                        )
                        st.markdown(f"<p style='color:#cbd5e1; margin-top:12px; font-size:0.92rem;'><b>Hook Rationale:</b> {c['explanation']}</p>", unsafe_allow_html=True)
                        
                        col_bt1, col_bt2 = st.columns(2)
                        with col_bt1:
                            if st.button("⬇ Download Clip", key=f"dl_{c['id']}", use_container_width=True):
                                st.info("Clip ready for download.")
                        with col_bt2:
                            if st.button("📅 Schedule Post", key=f"sch_{c['id']}", use_container_width=True):
                                create_schedule(active_project["id"], "Monday", "18:00")
                                st.success("Added to publishing queue!")
                    with col_c2:
                        # Video preview seeking directly to start_time
                        st.video(current_video["file_path"], start_time=int(c["start_time"]))

# ============================================================
# TAB 2: AI VIDEO CHAT (Grounded RAG Intelligence)
# ============================================================
elif tab == "AI Video Chat":
    st.markdown("<h1 style='margin:0; font-size:1.85rem;'>💬 AI Video Chatbot</h1>", unsafe_allow_html=True)
    st.caption("Ask questions about your video transcripts with timestamp-grounded citations.")

    if not videos:
        st.info("No videos available. Ingest a video in 'Create Clips' first.")
    else:
        vid_options = {v["filename"]: v["id"] for v in videos}
        selected_vid_title = st.selectbox("Video Context:", list(vid_options.keys()))
        selected_vid_id = vid_options[selected_vid_title]

        with st.container(border=True):
            # Render conversation
            history = get_chat_history(active_project["id"], st.session_state.chat_session_id)
            if not history:
                st.caption("No messages yet. Ask anything about what was said in this video!")
            else:
                for msg in history:
                    with st.chat_message(msg["role"]):
                        st.write(msg["message"])

            # Input form
            with st.form("chat_form_clean", clear_on_submit=True):
                col_ch1, col_ch2 = st.columns([10, 2])
                with col_ch1:
                    user_query = st.text_input("Ask a question:", placeholder="e.g. What is the main idea of this video? What was discussed about SpaceX?", label_visibility="collapsed")
                with col_ch2:
                    send_btn = st.form_submit_button("Send", use_container_width=True)

                if send_btn and user_query:
                    add_chat_message(active_project["id"], st.session_state.chat_session_id, "user", user_query)
                    
                    try:
                        # Retrieve matching chunks (ChromaDB + SQLite fallback)
                        retrieved = query_similar_chunks(
                            project_id=active_project["id"],
                            query_text=user_query,
                            k=4,
                            video_ids=[selected_vid_id],
                            model=st.session_state.embedding_model,
                            base_url=st.session_state.ollama_url
                        )
                        # Grounded answer generation (Ollama + Extractive fallback)
                        answer = generate_grounded_answer(
                            project_id=active_project["id"],
                            query=user_query,
                            retrieved_chunks=retrieved,
                            model=st.session_state.ollama_model,
                            base_url=st.session_state.ollama_url
                        )
                    except Exception as err:
                        answer = f"Error processing query: {str(err)}"

                    add_chat_message(active_project["id"], st.session_state.chat_session_id, "assistant", answer)
                    st.rerun()

            col_cl1, col_cl2 = st.columns([3, 9])
            with col_cl1:
                if st.button("🗑 Clear Chat History", use_container_width=True):
                    clear_chat_history(active_project["id"], st.session_state.chat_session_id)
                    st.rerun()

        # Quick Instant Scene Search
        with st.container(border=True):
            st.write("### 🔍 Search Video by Keyword or Topic")
            search_term = st.text_input("Find exact moment:", placeholder="e.g. pricing, artificial intelligence, revenue", label_visibility="collapsed")
            if search_term:
                hits = query_similar_chunks(
                    project_id=active_project["id"],
                    query_text=search_term,
                    k=3,
                    video_ids=[selected_vid_id],
                    model=st.session_state.embedding_model,
                    base_url=st.session_state.ollama_url
                )
                if not hits:
                    st.caption("No matching moments found for this keyword.")
                else:
                    for h in hits:
                        meta = h.get("metadata", {})
                        st_sec = float(meta.get("start_time", 0.0))
                        hours = int(st_sec // 3600)
                        mins = int((st_sec % 3600) // 60)
                        secs = int(st_sec % 60)
                        st.markdown(f"• **[{hours:02d}:{mins:02d}:{secs:02d}]**: *\"{h['text']}\"*")

# ============================================================
# TAB 3: LIBRARY & SETTINGS
# ============================================================
elif tab == "Library & Settings":
    st.markdown("<h1 style='margin:0; font-size:1.85rem;'>⚙️ Video Library & Settings</h1>", unsafe_allow_html=True)
    st.caption("Manage your video archive, Ollama AI model endpoints, and workspaces.")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        with st.container(border=True):
            st.write("### 🎬 Video Library")
            if not videos:
                st.caption("No videos imported yet.")
            else:
                for v in videos:
                    col_vi1, col_vi2 = st.columns([8, 2])
                    with col_vi1:
                        st.write(f"**{v['filename']}**")
                        st.caption(f"Status: **{v['status'].upper()}** | Added: {v['created_at'][:10]}")
                    with col_vi2:
                        if st.button("Delete", key=f"del_{v['id']}", use_container_width=True):
                            conn = get_db_connection()
                            conn.execute("DELETE FROM videos WHERE id = ?", (v["id"],))
                            conn.execute("DELETE FROM clips WHERE video_id = ?", (v["id"],))
                            conn.commit()
                            conn.close()
                            st.rerun()
                    st.markdown("<hr style='margin:6px 0; border-color:#1f2937;'>", unsafe_allow_html=True)

    with col_s2:
        with st.container(border=True):
            st.write("### 🤖 Local Ollama Connection")
            st.session_state.ollama_url = st.text_input("Ollama Server URL:", value=st.session_state.ollama_url)
            st.session_state.ollama_model = st.text_input("LLM Model Name:", value=st.session_state.ollama_model)
            st.session_state.embedding_model = st.text_input("Embedding Model:", value=st.session_state.embedding_model)

            col_tst1, col_tst2 = st.columns(2)
            with col_tst1:
                if st.button("🔍 Test Connection", use_container_width=True):
                    ok, m_list = test_ollama_connection(st.session_state.ollama_url)
                    if ok:
                        st.success(f"Connected! Models: {', '.join(m_list)}")
                    else:
                        st.error(f"Cannot connect to Ollama: {m_list}")
            with col_tst2:
                if st.button("💾 Save Settings", use_container_width=True):
                    update_setting("ollama_url", st.session_state.ollama_url)
                    update_setting("ollama_model", st.session_state.ollama_model)
                    update_setting("embedding_model", st.session_state.embedding_model)
                    st.success("Settings saved!")
                    st.rerun()

        with st.container(border=True):
            st.write("### 📁 Workspace Manager")
            with st.form("create_workspace_form", clear_on_submit=True):
                new_name = st.text_input("New Workspace Name:")
                if st.form_submit_button("Create Workspace", use_container_width=True) and new_name:
                    create_project(new_name, "")
                    st.success(f"Workspace '{new_name}' created!")
                    st.rerun()
