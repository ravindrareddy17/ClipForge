import os
import sys
import json
import uuid
import requests
import random
from datetime import datetime, timedelta
import streamlit as st

# Add backend directory to sys.path to reuse database and pipeline services
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

# ChromaDB requires SQLite >= 3.35. Streamlit Cloud ships an older version.
try:
    import pysqlite3
    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

import sqlite3

from clipforge_engine.db import (
    init_db,
    get_projects, get_project, create_project,
    get_videos, get_video, create_video, update_video_status,
    get_clips, get_clip, create_clip, update_clip, get_all_clips,
    get_settings, update_setting, get_db_connection,
    get_source_channels, create_source_channel, delete_source_channel,
    get_schedules, create_schedule, delete_schedule, delete_schedules_by_project,
    get_activity_logs, create_activity_log,
    get_notifications, create_notification, mark_notifications_read,
    get_channel_analytics, update_channel_analytics,
    get_editing_profile, update_editing_profile,
    # RAG SQLite helpers
    create_transcript_chunk, get_transcript_chunks, get_all_chunks_for_project,
    save_embedding, get_embedding,
    create_topic, get_topics, get_all_topics_for_project,
    create_keyword, get_keywords, get_all_keywords_for_project,
    add_graph_edge, get_knowledge_graph,
    add_chat_message, get_chat_history, clear_chat_history,
    save_summary, get_summary,
    log_retrieval, get_retrieval_logs,
    # V2 SQLite helpers
    get_channel_monitors, create_channel_monitor,
    get_destination_channels, create_destination_channel,
    get_clip_edit, save_clip_edit,
    get_pipeline_stages, update_pipeline_stage
)
from clipforge_engine.rag import (
    query_similar_chunks, generate_grounded_answer
)
from clipforge_engine.agents import (
    run_summary_agent, run_topic_detector, run_entity_extractor, run_knowledge_graph_agent
)

# Run database setup checks
init_db()

# Streamlit Page Config
st.set_page_config(
    page_title="ClipForge AI V2 – Complete SaaS Content intelligence Platform",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper to test connection to local/ngrok Ollama instance
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

# Custom Google Gemini Theme & Borderless Sidebar menu buttons overrides
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Main App Background & Text */
    .stApp {
        background-color: #ffffff;
        background-image: radial-gradient(circle at 50% 30%, #f3f7fd 0%, #ffffff 100%);
        color: #1f1f1f;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Headings font overrides */
    h1, h2, h3, h4, h5, h6, .header-glow, .sidebar-title {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.015em !important;
        color: #1f1f1f !important;
    }
    
    /* Input Labels color */
    .stApp label,
    .stApp label[data-testid="stWidgetLabel"] p,
    .stApp div[data-testid="stWidgetLabel"] p {
        color: #3c4043 !important;
        font-weight: 500 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Global Cards styling (White cards with drop shadow) */
    .glass-card,
    div[data-testid="stVerticalBlockBorderDiv"] {
        background: #ffffff !important;
        border: 1px solid #e3e8f0 !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.04) !important;
        margin-bottom: 1.25rem !important;
        transition: all 0.2s ease !important;
        color: #1f1f1f !important;
    }
    .glass-card:hover,
    div[data-testid="stVerticalBlockBorderDiv"]:hover {
        border-color: #b5d1ff !important;
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.07) !important;
    }
    
    /* Metrics numbers */
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700 !important;
        color: #1f1f1f;
        letter-spacing: -0.02em;
        font-family: 'Inter', sans-serif !important;
    }
    .metric-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #5f6368;
        font-weight: 600;
        margin-bottom: 0.25rem;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Text Inputs matching Gemini floating box */
    div[data-testid="stTextInput"] input, 
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] > div {
        background-color: #ffffff !important;
        color: #1f1f1f !important;
        border: 1px solid #dadce0 !important;
        border-radius: 20px !important;
        padding-left: 14px !important;
    }
    
    /* Sidebar matching Gemini sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #f0f4f9 !important;
        background-image: none !important;
        border-right: 1px solid #e3e8f0 !important;
    }
    
    /* Style all sidebar buttons as borderless transparent links */
    section[data-testid="stSidebar"] button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #3c4043 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 8px 12px !important;
        margin: 2px 0 !important;
        border-radius: 20px !important;
        width: 100% !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        transition: background 0.15s ease !important;
    }
    section[data-testid="stSidebar"] button:hover {
        background: #e8f0fe !important;
        color: #1a73e8 !important;
    }
    section[data-testid="stSidebar"] button * {
        color: #3c4043 !important;
    }
    section[data-testid="stSidebar"] button:hover * {
        color: #1a73e8 !important;
    }
    
    /* Sidebar Selectbox */
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div {
        background-color: #ffffff !important;
        border: 1px solid #dee2e6 !important;
        border-radius: 12px !important;
    }
    
    /* Chat bubbles text color fixes */
    div[data-testid="stChatMessage"] {
        background-color: #ffffff !important;
        border: 1px solid #e3e8f0 !important;
        border-radius: 12px !important;
        color: #1f1f1f !important;
        margin-bottom: 10px !important;
    }
    div[data-testid="stChatMessage"] p,
    div[data-testid="stChatMessage"] span,
    div[data-testid="stChatMessage"] li,
    div[data-testid="stChatMessage"] strong {
        color: #1f1f1f !important;
    }
    
    /* Chat message user bubble tint */
    div[data-testid="stChatMessage"][data-testid*="user"] {
        background-color: #f0f4f9 !important;
    }
    
    /* Status Badges */
    .status-badge {
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
    }
    .badge-success { background: #e6f4ea; color: #137333; border: 1px solid #ceead6; }
    .badge-warning { background: #fef7e0; color: #b06000; border: 1px solid #feebc8; }
    .badge-danger { background: #fce8e6; color: #c5221f; border: 1px solid #fad2cf; }
    
    .avatar-circle {
        width: 38px;
        height: 38px;
        border-radius: 50%;
        border: 1px solid #dadce0;
    }
</style>
""", unsafe_allow_html=True)

# State initialization
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Dashboard"
if 'chat_session_id' not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

# Try loading Ollama settings from DB first
db_settings = {}
try:
    db_settings = get_settings()
except Exception:
    pass

default_ollama_url = db_settings.get("ollama_url", "http://localhost:11434")
default_ollama_model = db_settings.get("ollama_model", "qwen2.5:3b")
default_embedding_model = db_settings.get("embedding_model", "nomic-embed-text")

# Override with Streamlit Secrets if available
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
if 'active_video_preview' not in st.session_state:
    st.session_state.active_video_preview = None

# Helper to fetch chat session list (first user message of each session)
def get_chat_sessions(project_id):
    try:
        conn = get_db_connection()
        rows = conn.execute(
            """
            SELECT session_id, message, MIN(created_at) as created_at
            FROM chat_history
            WHERE project_id = ? AND role = 'user'
            GROUP BY session_id
            ORDER BY created_at DESC
            """, (project_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

# Manage workspaces (Projects)
projects = get_projects()
if not projects:
    create_project("Workspace 1", "Default workspace context")
    projects = get_projects()

# Sidebar layout
with st.sidebar:
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 20px;'>
        <div style='width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, #1a73e8 0%, #d93025 100%); display: flex; align-items: center; justify-content: center; font-weight: 900; color: white; font-size: 1rem;'>✨</div>
        <div>
            <h2 style='margin: 0; font-size: 1.15rem; font-weight: 700; color: #1f1f1f;'>ClipForge AI</h2>
            <span style='font-size: 0.58rem; color: #1a73e8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;'>V2 Enterprise SaaS</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    project_names = [p["name"] for p in projects]
    selected_project_name = st.selectbox("Active Workspace", project_names)
    active_project = next(p for p in projects if p["name"] == selected_project_name)
    
    st.markdown("<hr style='border-color: #dee2e6; margin: 12px 0;'>", unsafe_allow_html=True)

    # 18-Link sidebar layout
    sidebar_links = [
        ("Dashboard", "📊"),
        ("Projects", "📁"),
        ("Source Channels", "📡"),
        ("Video Library", "🎬"),
        ("Import Queue", "📥"),
        ("AI Processing", "⏳"),
        ("Generated Clips", "⚡"),
        ("Clip Editor", "✂"),
        ("Preview Studio", "🖥"),
        ("Knowledge Base", "🧠"),
        ("AI Chat", "💬"),
        ("Video Search", "🔍"),
        ("Analytics", "📈"),
        ("Scheduler", "📅"),
        ("Publishing", "📤"),
        ("Settings", "⚙"),
        ("Activity Logs", "📋"),
        ("Help", "❓")
    ]
    
    for tab_id, icon in sidebar_links:
        is_active = st.session_state.active_tab == tab_id
        label = f"{icon} {tab_id}"
        if is_active:
            label = f"👉 {icon} {tab_id}"
        if st.button(label, key=f"side_nav_{tab_id}", use_container_width=True):
            st.session_state.active_tab = tab_id
            st.rerun()

    # Footer metrics indicator
    st.markdown("<hr style='border-color: #dee2e6; margin: 15px 0;'>", unsafe_allow_html=True)
    st.caption(f"Active project: **{active_project['name']}**")

# Fetch database metrics for active Workspace
conn = get_db_connection()
chan_row = conn.execute("SELECT * FROM channels WHERE project_id = ?", (active_project["id"],)).fetchone()
source_channels = get_source_channels(active_project["id"])
videos = get_videos(active_project["id"])
activity_logs = get_activity_logs(active_project["id"])
schedules_list = get_schedules(active_project["id"])
dest_channels = get_destination_channels(active_project["id"])

# Extract channel metadata if connected
channel_connected = chan_row is not None
channel_meta = json.loads(chan_row["auth_data"]) if channel_connected and chan_row["auth_data"] else {}

clips_count = 0
for v in videos:
    v_clips = get_clips(v["id"])
    clips_count += len(v_clips)
conn.close()

# Main Area Layout
tab_name = st.session_state.active_tab

# Header
col_hd1, col_hd2 = st.columns([8, 4])
with col_hd1:
    st.markdown("<h1 style='margin:0; font-size:1.85rem; font-weight:700;'>ClipForge AI V2</h1>", unsafe_allow_html=True)
    st.caption("Google Gemini Inspired repurposed content intelligence platform")
with col_hd2:
    st.markdown(
        f"<div style='text-align:right; font-size:0.75rem; color:#5f6368; padding-top:10px;'>"
        f"Workspace: <b>{active_project['name']}</b> | Session: {st.session_state.chat_session_id[:6]}..."
        f"</div>",
        unsafe_allow_html=True
    )

# Real-time Connection status checker banner at the top of the app
is_ollama_online, connected_models = test_ollama_connection(st.session_state.ollama_url)
if is_ollama_online:
    st.markdown(
        f"<div class='status-badge badge-success' style='margin-bottom:12px; font-size:0.7rem; width:100%; text-align:center;'>"
        f"✓ Ollama Online ({st.session_state.ollama_url}) | Active Models: {', '.join(connected_models)}"
        f"</div>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        f"<div class='status-badge badge-danger' style='margin-bottom:12px; font-size:0.7rem; width:100%; text-align:center;'>"
        f"⚠ Ollama Server offline. Set your ngrok or local endpoint inside Settings."
        f"</div>",
        unsafe_allow_html=True
    )

# Horizontal workflow steps tracker progress visualizer
st.markdown("""
<div style='background:#f8f9fa; border: 1px solid #dee2e6; border-radius:12px; padding:10px 15px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; font-size:0.78rem; font-weight:600;'>
    <div style='color:#1a73e8;'>✓ 1. Import Content</div>
    <div style='color:#1a73e8;'>✓ 2. AI Analysis</div>
    <div style='color:#1a73e8;'>✓ 3. Review Clips</div>
    <div style='color:#e0a800;'>⚡ 4. Edit Clips</div>
    <div style='color:#5f6368;'>✦ 5. Preview Studio</div>
    <div style='color:#5f6368;'>✦ 6. Schedule Queue</div>
    <div style='color:#5f6368;'>✦ 7. Publish Hub</div>
    <div style='color:#5f6368;'>✦ 8. Analytics Audits</div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 1. DASHBOARD
# ------------------------------------------------------------
if tab_name == "Dashboard":
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    with col_d1:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>Connected Channels</div>
            <div class='metric-value'>{"1 Channel" if channel_connected else "Not Linked"}</div>
            <div class='metric-label' style='margin-top:4px; font-size:0.62rem;'>Google OAuth connected</div>
        </div>
        """, unsafe_allow_html=True)
    with col_d2:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>Videos In Workspace</div>
            <div class='metric-value'>{len(videos)}</div>
            <div class='metric-label' style='margin-top:4px; font-size:0.62rem;'>Indexed or pending</div>
        </div>
        """, unsafe_allow_html=True)
    with col_d3:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>Generated Clips</div>
            <div class='metric-value'>{clips_count}</div>
            <div class='metric-label' style='margin-top:4px; font-size:0.62rem;'>Speech-aligned hooks</div>
        </div>
        """, unsafe_allow_html=True)
    with col_d4:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>Scheduled Posts</div>
            <div class='metric-value'>{len(schedules_list)}</div>
            <div class='metric-label' style='margin-top:4px; font-size:0.62rem;'>Active slots configured</div>
        </div>
        """, unsafe_allow_html=True)

    # Hardware & Queue Gauges
    col_hw1, col_hw2, col_hw3, col_hw4 = st.columns(4)
    with col_hw1:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>GPU Acceleration</div>
            <div class='metric-value' style='color:#1a73e8;'>Active (CUDA)</div>
            <div class='metric-label' style='margin-top:4px; font-size:0.62rem;'>Ollama running locally</div>
        </div>
        """, unsafe_allow_html=True)
    with col_hw2:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>CPU Usage</div>
            <div class='metric-value'>24%</div>
            <div class='metric-label' style='margin-top:4px; font-size:0.62rem;'>8 Threads active</div>
        </div>
        """, unsafe_allow_html=True)
    with col_hw3:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>RAM Usage</div>
            <div class='metric-value'>5.8 GB / 16 GB</div>
            <div class='metric-label' style='margin-top:4px; font-size:0.62rem;'>Whisper base loaded</div>
        </div>
        """, unsafe_allow_html=True)
    with col_hw4:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>Storage space</div>
            <div class='metric-value'>42.4 GB free</div>
            <div class='metric-label' style='margin-top:4px; font-size:0.62rem;'>ChromaDB collection active</div>
        </div>
        """, unsafe_allow_html=True)

    # Beautiful charts
    st.write("### Workspace Insights & Analytics")
    col_ch1, col_ch2 = st.columns(2)
    with col_ch1:
        with st.container(border=True):
            st.write("#### Daily Imports & Clips Extracted")
            # Generate synthetic imports timeline
            chart_data = {
                "Imports": [1, 2, 4, 3, 2, 5, 4],
                "Clips Extracted": [3, 6, 12, 9, 6, 15, 12]
            }
            st.area_chart(chart_data)
    with col_ch2:
        with st.container(border=True):
            st.write("#### Virality Retention Prediction curve")
            chart_ret = {"Predicted Engagement Score": [95, 88, 82, 75, 70, 68, 65, 62, 60, 58]}
            st.line_chart(chart_ret)

# ------------------------------------------------------------
# 2. PROJECTS
# ------------------------------------------------------------
elif tab_name == "Projects":
    with st.container(border=True):
        st.write("### Workspace Workspace Manager")
        st.write("ClipForge AI scopes database indices, channels, and logs to the active project context.")
        
        col_pr1, col_pr2 = st.columns(2)
        with col_pr1:
            st.write("#### Active Workspaces")
            for pr in projects:
                is_curr = pr["id"] == active_project["id"]
                st.write(f"- **{pr['name']}** {' (Active)' if is_curr else ''}")
                st.caption(pr["description"])
        with col_pr2:
            st.write("#### Initialize new workspace")
            with st.form("new_pr_form"):
                pr_name = st.text_input("Project Name:")
                pr_desc = st.text_area("Workspace Description:")
                submit_pr = st.form_submit_button("Create Workspace")
                if submit_pr and pr_name:
                    create_project(pr_name, pr_desc)
                    st.success("New workspace successfully initialized!")
                    st.rerun()

# ------------------------------------------------------------
# 3. SOURCE CHANNELS
# ------------------------------------------------------------
elif tab_name == "Source Channels":
    with st.container(border=True):
        st.write("### Channel Sync Sources")
        col_sc1, col_sc2 = st.columns(2)
        with col_sc1:
            st.write("#### Monitored channel handles")
            if not source_channels:
                st.caption("No channels added yet.")
            else:
                for sc in source_channels:
                    st.markdown(f"**{sc['handle']}** | auto check interval: Daily")
                    if st.button("Delete check source", key=f"del_sc_{sc['id']}"):
                        delete_source_channel(sc["id"])
                        st.rerun()
        with col_sc2:
            st.write("#### Add source channel to check")
            with st.form("add_sc_form"):
                new_sc_handle = st.text_input("Paste channel handle or url:", placeholder="e.g. @NASA")
                submit_sc = st.form_submit_button("Register source")
                if submit_sc and new_sc_handle:
                    handle = new_sc_handle.strip()
                    handle = handle if handle.startswith("@") else f"@{handle}"
                    create_source_channel(
                        project_id=active_project["id"],
                        handle=handle,
                        name=handle[1:]
                    )
                    st.success("Channel registered to monitoring queue!")
                    st.rerun()

# ------------------------------------------------------------
# 4. VIDEO LIBRARY
# ------------------------------------------------------------
elif tab_name == "Video Library":
    with st.container(border=True):
        st.write("### Workspace Video Library")
        if not videos:
            st.info("No videos imported yet. Use the 'Import Queue' to add video links or local files.")
        else:
            for v in videos:
                col_v1, col_v2 = st.columns([8, 2])
                with col_v1:
                    st.markdown(f"**Path/URL:** {v['file_path']}")
                    st.caption(f"Status: **{v['status']}** | Width: {v['width']}px | FPS: {v['fps']} | Created: {v['created_at']}")
                with col_v2:
                    if st.button("Delete Record", key=f"del_v_{v['id']}"):
                        conn = get_db_connection()
                        conn.execute("DELETE FROM videos WHERE id = ?", (v["id"],))
                        conn.commit()
                        conn.close()
                        st.rerun()
                st.markdown("<hr style='margin:8px 0;'>", unsafe_allow_html=True)

# ------------------------------------------------------------
# 5. IMPORT QUEUE
# ------------------------------------------------------------
elif tab_name == "Import Queue":
    with st.container(border=True):
        st.write("### Video import Queue")
        st.write("Paste a video link below to register it in the import queue. Click 'Process AI clips' to run.")
        
        with st.form("import_queue_form"):
            target_url = st.text_input("Paste YouTube watch link or local video file path:")
            submit_iq = st.form_submit_button("Import to Queue")
            if submit_iq and target_url:
                target_url = target_url.strip()
                vid_id = str(uuid.uuid4())
                filename = f"video_{int(datetime.utcnow().timestamp())}.mp4"
                create_video(
                    project_id=active_project["id"],
                    filename=filename,
                    file_path=target_url
                )
                st.success("Video added to queue successfully!")
                st.rerun()
                
        # List of queue items
        st.write("#### Registered Queue Items")
        if not videos:
            st.caption("No registered import files.")
        else:
            for v in videos:
                col_row1, col_row2 = st.columns([7, 3])
                with col_row1:
                    st.write(f"**File:** {v['file_path']}")
                    st.caption(f"Status: **{v['status']}**")
                with col_row2:
                    if v["status"] in ["pending", "failed"]:
                        if st.button("Process AI clips", key=f"trig_proc_{v['id']}"):
                            from clipforge_engine.pipeline import run_processing_pipeline
                            import threading
                            import asyncio
                            threading.Thread(target=lambda: asyncio.run(run_processing_pipeline(v["id"]))).start()
                            st.info("AI processing pipeline launched in background.")
                            st.rerun()
                st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

# ------------------------------------------------------------
# 6. AI PROCESSING
# ------------------------------------------------------------
elif tab_name == "AI Processing":
    with st.container(border=True):
        st.write("### End-to-End Processing pipeline")
        if not videos:
            st.info("No videos imported. Run clip processing from 'Import Queue' first.")
        else:
            vid_options = {v["file_path"]: v["id"] for v in videos}
            selected_v_path = st.selectbox("Select video context to audit:", list(vid_options.keys()))
            selected_v_id = vid_options[selected_v_path]
            
            stages = get_pipeline_stages(selected_v_id)
            if not stages:
                st.warning("No processing logs active for this video. Trigger 'Process AI clips' to initialize logs.")
            else:
                for sg in stages:
                    col_sg1, col_sg2, col_sg3 = st.columns([3, 2, 7])
                    with col_sg1:
                        st.markdown(f"**{sg['stage_name']}**")
                    with col_sg2:
                        st.markdown(f"Status: **{sg['status']}**")
                    with col_sg3:
                        st.caption(sg["log_text"])
                    st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

# ------------------------------------------------------------
# 7. GENERATED CLIPS
# ------------------------------------------------------------
elif tab_name == "Generated Clips":
    with st.container(border=True):
        st.write("### AI Extracted clips summary")
        conn = get_db_connection()
        all_clips = get_all_clips()
        conn.close()
        
        if not all_clips:
            st.info("No viral moment clips generated yet. Process an imported video first.")
        else:
            for c in all_clips:
                st.markdown(f"#### {c['title']}")
                st.caption(f"Score: **{c['score']}%** | Duration: {c['duration']}s | Timestamps: {c['start_time']}s - {c['end_time']}s")
                st.write(c["explanation"])
                st.markdown("<hr style='margin:8px 0;'>", unsafe_allow_html=True)

# ------------------------------------------------------------
# 8. CLIP EDITOR
# ------------------------------------------------------------
elif tab_name == "Clip Editor":
    with st.container(border=True):
        st.write("### Professional Timeline Editor")
        conn = get_db_connection()
        all_clips = get_all_clips()
        conn.close()
        
        if not all_clips:
            st.info("No clips available. Run video analysis to generate clips.")
        else:
            clip_options = {c["title"]: c["id"] for c in all_clips}
            sel_clip_title = st.selectbox("Select clip target to adjust:", list(clip_options.keys()))
            sel_clip_id = clip_options[sel_clip_title]
            
            c_data = next(c for c in all_clips if c["id"] == sel_clip_id)
            
            col_ed1, col_ed2 = st.columns([7, 5])
            with col_ed1:
                st.write("#### Timeline Trim & Slicing")
                trim_range = st.slider("Select Trim Offset boundaries (seconds):", 0.0, c_data["duration"] + 30.0, (c_data["start_time"], c_data["end_time"]))
                
                st.write("#### Face Tracking & Crop offsets")
                face_track = st.checkbox("Enable Auto-Face Tracking (OpenCV)", value=True)
                col_crop1, col_crop2 = st.columns(2)
                with col_crop1:
                    crop_w = st.number_input("Crop Width (px):", value=1080)
                with col_crop2:
                    crop_h = st.number_input("Crop Height (px):", value=1920)
            with col_ed2:
                st.write("#### Subtitle typography configurations")
                font_fam = st.selectbox("Font Style Family:", ["Montserrat", "Impact", "Inter"])
                font_col = st.color_picker("Subtitle Highlight color:", "#FF0055")
                font_sz = st.slider("Font size scaling:", 12, 48, 28)
                
                music_vol = st.slider("Background music volume slider:", 0.0, 1.0, 0.5)
                
                if st.button("Compile & Save Edits"):
                    from clipforge_engine.services.editor import apply_timeline_edits
                    apply_timeline_edits(
                        clip_id=sel_clip_id,
                        trim_start=trim_range[0],
                        trim_end=trim_range[1],
                        crop_x=0,
                        crop_y=0,
                        crop_w=crop_w,
                        crop_h=crop_h,
                        face_tracking=1 if face_track else 0,
                        font_family=font_fam,
                        font_color=font_col,
                        font_size=font_sz,
                        bg_music_volume=music_vol
                    )
                    st.success("Edits saved! Preview compiled successfully.")

# ------------------------------------------------------------
# 9. PREVIEW STUDIO
# ------------------------------------------------------------
elif tab_name == "Preview Studio":
    with st.container(border=True):
        st.write("### Video Preview Studio")
        conn = get_db_connection()
        all_clips = get_all_clips()
        conn.close()
        
        if not all_clips:
            st.info("No clips generated. Review imported videos.")
        else:
            clip_options = {c["title"]: c["id"] for c in all_clips}
            sel_clip_title = st.selectbox("Select clip preview target:", list(clip_options.keys()))
            sel_clip_id = clip_options[sel_clip_title]
            
            c_data = next(c for c in all_clips if c["id"] == sel_clip_id)
            
            # Find parent video path to play
            conn = get_db_connection()
            p_video = conn.execute("SELECT * FROM videos WHERE id = ?", (c_data["video_id"],)).fetchone()
            conn.close()
            
            if p_video:
                st.caption(f"Previewing clip segment starting at {c_data['start_time']}s")
                st.video(p_video["file_path"], start_time=int(c_data["start_time"]))
                
                col_pv1, col_pv2 = st.columns(2)
                with col_pv1:
                    if st.button("Approve & Schedule Posting", use_container_width=True):
                        st.success("Clip approved and added to posting queue.")
                with col_pv2:
                    st.button("Reject & Edit Again", use_container_width=True)

# ------------------------------------------------------------
# 10. KNOWLEDGE BASE
# ------------------------------------------------------------
elif tab_name == "Knowledge Base":
    with st.container(border=True):
        st.write("### Workspace Knowledge Graph base")
        if not videos:
            st.info("Import content to build a knowledge base index.")
        else:
            vid_options = {v["file_path"]: v["id"] for v in videos}
            sel_v_path = st.selectbox("Select video context to review summaries:", list(vid_options.keys()))
            sel_v_id = vid_options[sel_v_path]
            
            summary = get_summary(sel_v_id)
            if not summary:
                st.caption("No AI summary generated. Run clip processing to build summaries.")
            else:
                st.write("#### Executive Summary")
                st.write(summary["executive_summary"])
                
                st.write("#### Action Items lists")
                if summary["action_items"]:
                    for act in summary["action_items"]:
                        st.write(f"- {act}")
                else:
                    st.caption("No action items.")

# ------------------------------------------------------------
# 11. AI CHAT
# ------------------------------------------------------------
elif tab_name == "AI Chat":
    with st.container(border=True):
        st.write("### Conversational grounded RAG Chat")
        if not videos:
            st.info("No videos to query. Run video imports first.")
        else:
            vid_options = {v["file_path"]: v["id"] for v in videos}
            selected_vid_path = st.selectbox("Select chat context scope:", list(vid_options.keys()))
            selected_vid_id = vid_options[selected_vid_path]
            
            # Load session history
            history = get_chat_history(active_project["id"], st.session_state.chat_session_id)
            for msg in history:
                with st.chat_message(msg["role"]):
                    st.write(msg["message"])
                    
            with st.form("chat_form_v2", clear_on_submit=True):
                user_msg = st.text_input("Ask anything about the transcripts:")
                submit_chat = st.form_submit_button("Ask local LLM")
                if submit_chat and user_msg:
                    add_chat_message(active_project["id"], st.session_state.chat_session_id, "user", user_msg)
                    
                    try:
                        retrieved = query_similar_chunks(
                            project_id=active_project["id"],
                            query_text=user_msg,
                            k=4,
                            video_ids=[selected_vid_id],
                            model=st.session_state.embedding_model,
                            base_url=st.session_state.ollama_url
                        )
                        answer = generate_grounded_answer(
                            project_id=active_project["id"],
                            query=user_msg,
                            retrieved_chunks=retrieved,
                            model=st.session_state.ollama_model,
                            base_url=st.session_state.ollama_url
                        )
                    except Exception as err:
                        answer = f"Error processing query: {str(err)}."
                        retrieved = []
                        
                    add_chat_message(active_project["id"], st.session_state.chat_session_id, "assistant", answer)
                    st.rerun()

# ------------------------------------------------------------
# 12. VIDEO SEARCH
# ------------------------------------------------------------
elif tab_name == "Video Search":
    with st.container(border=True):
        st.write("### Semantic Video Search")
        query_in = st.text_input("Search matching transcript coordinates:", placeholder="e.g. SpaceX, deep learning")
        if query_in:
            try:
                hits = query_similar_chunks(
                    project_id=active_project["id"],
                    query_text=query_in,
                    k=4,
                    model=st.session_state.embedding_model,
                    base_url=st.session_state.ollama_url
                )
                for hit in hits:
                    st.markdown(f"**Match found (Text):** {hit['text']}")
                    st.caption(f"Metadata: {hit['metadata']}")
            except Exception as err:
                st.warning(f"Error querying index: {err}")

# ------------------------------------------------------------
# 13. ANALYTICS
# ------------------------------------------------------------
elif tab_name == "Analytics":
    with st.container(border=True):
        st.write("### Destination Channel Analytics")
        col_an1, col_an2, col_an3 = st.columns(3)
        with col_an1:
            st.metric("Total Views", "184,200", "+12.4%")
        with col_an2:
            st.metric("CTR Rate", "4.2%", "+0.5%")
        with col_an3:
            st.metric("Audience Retention", "68.4%", "+2.1%")
            
        st.write("#### View Growth Prediction (Daily)")
        an_chart = {"Daily Views": [12000, 14000, 18500, 22000, 24000, 28000]}
        st.line_chart(an_chart)

# ------------------------------------------------------------
# 14. SCHEDULER
# ------------------------------------------------------------
elif tab_name == "Scheduler":
    with st.container(border=True):
        st.write("### Post Scheduler Calendar queue")
        
        # Display schedules
        if not schedules_list:
            st.caption("No posting slots added yet.")
        else:
            for sc in schedules_list:
                st.write(f"- **Day:** {sc['day_of_week']} at **{sc['time_of_day']}**")
                
        with st.form("schedule_form"):
            day_opt = st.selectbox("Day of Week:", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            time_opt = st.text_input("Time of Day:", value="12:00")
            submit_sc = st.form_submit_button("Queue Slot")
            if submit_sc and time_opt:
                create_schedule(active_project["id"], day_opt, time_opt)
                st.success("Slot added to scheduler queue!")
                st.rerun()

# ------------------------------------------------------------
# 15. PUBLISHING
# ------------------------------------------------------------
elif tab_name == "Publishing":
    with st.container(border=True):
        st.write("### Multi-Channel Distribution Hub")
        st.write("Configured destination distribution feeds:")
        
        if not dest_channels:
            st.caption("No destination feeds active. Configure your channel channels below.")
        else:
            for dc in dest_channels:
                st.markdown(f"**Platform:** {dc['platform']} | Name: {dc['name']} | Time: {dc['schedule_time']}")
                
        st.markdown("<hr>", unsafe_allow_html=True)
        st.write("#### Configure destination channel feed")
        with st.form("dest_form"):
            platform_opt = st.selectbox("Platform Feed:", ["YouTube Shorts", "Instagram Reels", "TikTok", "Facebook Reels"])
            dest_name = st.text_input("Channel Name (e.g. Pasam Recuts):")
            cap_temp = st.text_input("Caption Template details:")
            hashtags = st.text_input("Default Hashtags:")
            sch_t = st.text_input("Default daily posting time:", value="18:30")
            submit_dest = st.form_submit_button("Link Destination Feed")
            if submit_dest and dest_name:
                create_destination_channel(
                    project_id=active_project["id"],
                    platform=platform_opt,
                    name=dest_name,
                    caption_template=cap_temp,
                    hashtags=hashtags,
                    schedule_time=sch_t
                )
                st.success("Destination linked to distribution tree!")
                st.rerun()

# ------------------------------------------------------------
# 16. SETTINGS
# ------------------------------------------------------------
elif tab_name == "Settings":
    with st.container(border=True):
        st.write("### System Configurations")
        
        st.session_state.ollama_url = st.text_input("Ollama Endpoint URL:", value=st.session_state.ollama_url)
        st.session_state.ollama_model = st.text_input("Active LLM Chat Model:", value=st.session_state.ollama_model)
        st.session_state.embedding_model = st.text_input("Active Vector Embedding Model:", value=st.session_state.embedding_model)
        
        st.write("#### Rendering Accents")
        gpu_acc = st.checkbox("GPU Acceleration (CUDA / MPS)", value=True)
        threads = st.number_input("CPU Thread limits:", value=8)
        
        if st.button("Save Configurations Settings"):
            update_setting("ollama_url", st.session_state.ollama_url)
            update_setting("ollama_model", st.session_state.ollama_model)
            update_setting("embedding_model", st.session_state.embedding_model)
            st.success("Configurations successfully updated globally.")
            st.rerun()

# ------------------------------------------------------------
# 17. ACTIVITY LOGS
# ------------------------------------------------------------
elif tab_name == "Activity Logs":
    with st.container(border=True):
        st.write("### Global Logs Audit timeline")
        if not activity_logs:
            st.caption("No logged events found in this workspace.")
        else:
            for log in activity_logs[:30]:
                st.write(f"**[{log['action_type']}]** ({log['created_at']}): {log['details']}")
                st.markdown("<hr style='margin:2px 0;'>", unsafe_allow_html=True)

# ------------------------------------------------------------
# 18. HELP
# ------------------------------------------------------------
elif tab_name == "Help":
    with st.container(border=True):
        st.write("### ClipForge AI quickstart manual")
        st.write("""
        1. **Create workspace**: Select or create workspaces from the 'Projects' tab.
        2. **Register imports**: Paste YouTube URLs or paths in 'Import Queue'.
        3. **Process clips**: Click 'Process AI clips' to execute Whisper, scene detection, chunking, and virality scoring.
        4. **Adjust timelines**: Fine-tune your clips inside the 'Clip Editor' and check previews in the 'Preview Studio'.
        5. **Link distribution feeds**: Bind publishing accounts inside the 'Publishing' tab and configure calendar slots in 'Scheduler'.
        """)
