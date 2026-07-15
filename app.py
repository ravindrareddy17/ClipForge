import os
import sys
import json
import uuid
import requests
from datetime import datetime
import streamlit as st

# Add backend directory to sys.path to reuse database and pipeline services
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

# ChromaDB requires SQLite >= 3.35. Streamlit Cloud ships an older version.
# pysqlite3-binary provides a newer SQLite; swap it in before anything imports sqlite3.
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
    log_retrieval, get_retrieval_logs
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
    page_title="ClipForge AI – AI-Powered Content Repurposing Platform",
    page_icon="⚡",
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

# Custom Clean SaaS Theme (Single Font family, clear contrast, dark glass aesthetics)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* Main App overrides */
    .stApp {
        background-color: #0d0f14;
        background-image: radial-gradient(circle at 50% 0%, #1a1e29 0%, #0d0f14 100%);
        color: #cbd5e1;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Headings font overrides */
    h1, h2, h3, h4, h5, h6, .header-glow, .sidebar-title {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: #ffffff !important;
    }
    
    /* Top Header transparency */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        background-image: none !important;
    }
    div[data-testid="stDecoration"] {
        background-image: linear-gradient(90deg, #7b2cbf, #00f0ff) !important;
        height: 4px !important;
    }
    
    /* Input Labels */
    .stApp label,
    .stApp label[data-testid="stWidgetLabel"] p,
    .stApp div[data-testid="stWidgetLabel"] p {
        color: #e2e8f0 !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Cards styling */
    .glass-card {
        background: rgba(22, 28, 38, 0.8);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        margin-bottom: 1.25rem;
        transition: all 0.25s ease;
    }
    .glass-card:hover {
        border-color: rgba(6, 182, 212, 0.3);
        transform: translateY(-1px);
    }
    
    /* Metrics numbers */
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800 !important;
        color: #ffffff;
        letter-spacing: -0.03em;
        font-family: 'Inter', sans-serif !important;
    }
    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        color: #94a3b8;
        font-weight: 700;
        margin-bottom: 0.25rem;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Dark inputs styling */
    div[data-testid="stTextInput"] input, 
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stSelectbox"] > div {
        background-color: #171c26 !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
    }
    div[data-testid="stTextInput"] input:focus, 
    div[data-testid="stTextArea"] textarea:focus,
    div[data-testid="stNumberInput"] input:focus,
    div[data-testid="stSelectbox"] > div:focus-within {
        border-color: #00f0ff !important;
        box-shadow: 0 0 10px rgba(0, 240, 255, 0.25) !important;
    }
    
    /* Action buttons overrides */
    button {
        background: #7b2cbf !important;
        background-image: none !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    button:hover {
        background: #9d4edd !important;
        background-image: none !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0 0 12px rgba(157, 78, 221, 0.4) !important;
        color: #ffffff !important;
    }
    button * {
        color: #ffffff !important;
    }
    
    /* Sidebar container styling overrides */
    section[data-testid="stSidebar"] {
        background-color: #0b0c10 !important;
        background-image: radial-gradient(circle at 50% 0%, #161a24 0%, #0b0c10 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    section[data-testid="stSidebar"] button {
        background: rgba(255, 255, 255, 0.04) !important;
        background-image: none !important;
        color: #cbd5e1 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        text-align: left !important;
        padding: 8px 12px !important;
    }
    section[data-testid="stSidebar"] button:hover {
        background: rgba(6, 182, 212, 0.15) !important;
        color: #22d3ee !important;
        border-color: rgba(6, 182, 212, 0.4) !important;
    }
    section[data-testid="stSidebar"] button * {
        color: #cbd5e1 !important;
    }
    section[data-testid="stSidebar"] button:hover * {
        color: #22d3ee !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div {
        background-color: rgba(255, 255, 255, 0.03) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
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
    .badge-success { background: rgba(34, 211, 238, 0.15); color: #22d3ee; border: 1px solid rgba(34, 211, 238, 0.3); }
    .badge-warning { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-danger { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    
    .avatar-circle {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        border: 2px solid rgba(6, 182, 212, 0.4);
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
if 'preview_start_time' not in st.session_state:
    st.session_state.preview_start_time = 0.0

# Google OAuth Connection Dialog
@st.dialog("Google Account Chooser (OAuth 2.0)")
def open_oauth_dialog(project_id):
    st.write("Grant ClipForge SaaS permissions to upload videos and retrieve channel analytics:")
    account_email = st.selectbox("Select Account:", ["pasam.vignesh@gmail.com", "vignesh.creator@shorts.co"])
    st.caption("Permissions requested:\n✓ Manage your YouTube videos\n✓ Retrieve channels data")
    
    col_oa1, col_oa2 = st.columns(2)
    with col_oa1:
        if st.button("Authorize Connection", use_container_width=True):
            w_title = "Vignesh Recuts" if account_email == "pasam.vignesh@gmail.com" else "Creator Shorts"
            mock_meta = {
                "subscribers": 45000 if account_email == "pasam.vignesh@gmail.com" else 184000,
                "video_count": 32 if account_email == "pasam.vignesh@gmail.com" else 156,
                "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop",
                "token_health": "Healthy",
                "last_sync": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "upload_status": "Active",
                "channel_id": "UC_VIGNESH_OAUTH_DEV"
            }
            
            conn = get_db_connection()
            conn.execute("DELETE FROM channels WHERE project_id = ?", (project_id,))
            conn.execute(
                "INSERT INTO channels (id, project_id, platform, name, auth_data, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), project_id, "YouTube", w_title, json.dumps(mock_meta), "active", datetime.utcnow().isoformat())
            )
            # Also log this event
            conn.execute(
                "INSERT INTO activity_log (id, project_id, action_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), project_id, "OAuth Connected", f"Connected YouTube channel: {w_title}", datetime.utcnow().isoformat())
            )
            conn.commit()
            conn.close()
            st.success("Google channel successfully linked!")
            st.rerun()
    with col_oa2:
        if st.button("Cancel OAuth", use_container_width=True):
            st.rerun()

# Manage workspaces (Projects)
projects = get_projects()
if not projects:
    create_project("Workspace 1", "Automated YouTube Shorts Channel Workspace")
    projects = get_projects()

# Sidebar layout
with st.sidebar:
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 25px;'>
        <div style='width: 38px; height: 38px; border-radius: 12px; background: linear-gradient(135deg, #7b2cbf 0%, #00f0ff 100%); display: flex; align-items: center; justify-content: center; font-weight: 900; color: white; box-shadow: 0 0 15px rgba(0,240,255,0.3);'>⚡</div>
        <div>
            <h2 style='margin: 0; font-size: 1.2rem; font-weight: 900; color: white;'>ClipForge AI</h2>
            <span style='font-size: 0.58rem; color: #00f0ff; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em;'>Content Repurposing Platform</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    project_names = [p["name"] for p in projects]
    selected_project_name = st.selectbox("Active Workspace", project_names)
    active_project = next(p for p in projects if p["name"] == selected_project_name)
    
    st.markdown("<hr style='border-color: rgba(255, 255, 255, 0.05); margin: 15px 0;'>", unsafe_allow_html=True)

    # 5 simplified tabs
    tabs = [
        "Dashboard",
        "Video Library & Import",
        "Generated Clips",
        "AI Knowledge Chat",
        "Settings"
    ]
    
    for tab in tabs:
        active = st.session_state.active_tab == tab
        label = f"✦ {tab}" if active else tab
        if st.button(label, key=f"nav_{tab}", use_container_width=True):
            st.session_state.active_tab = tab
            st.rerun()
            
    st.markdown("<hr style='border-color: rgba(255, 255, 255, 0.05); margin: 15px 0;'>", unsafe_allow_html=True)

# Fetch database metrics for active Workspace
conn = get_db_connection()
chan_row = conn.execute("SELECT * FROM channels WHERE project_id = ?", (active_project["id"],)).fetchone()
source_channels = get_source_channels(active_project["id"])
videos = get_videos(active_project["id"])
activity_logs = get_activity_logs(active_project["id"])
schedules_list = get_schedules(active_project["id"])

# Extract channel metadata if connected
channel_connected = chan_row is not None
channel_meta = json.loads(chan_row["auth_data"]) if channel_connected and chan_row["auth_data"] else {}

# Get generated clips count
clips_count = 0
for v in videos:
    v_clips = get_clips(v["id"])
    clips_count += len(v_clips)
conn.close()

# Main layout content
tab_name = st.session_state.active_tab

# Header branding banner
st.markdown("<h1 class='header-glow' style='margin: 0;'>ClipForge AI</h1>", unsafe_allow_html=True)
st.markdown("<div class='header-subtitle' style='margin-bottom: 20px;'>Local RAG Content Intelligence Platform</div>", unsafe_allow_html=True)

# Real-time Connection status checker banner at the top of the app
is_ollama_online, connected_models = test_ollama_connection(st.session_state.ollama_url)
if is_ollama_online:
    st.markdown(
        f"<div class='status-badge badge-success' style='margin-bottom:20px; font-size:0.75rem; width:100%; text-align:center;'>"
        f"✓ Ollama Server Online & Connected | Target: {st.session_state.ollama_url} | Available Models: {', '.join(connected_models)}"
        f"</div>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        f"<div class='status-badge badge-danger' style='margin-bottom:20px; font-size:0.75rem; width:100%; text-align:center;'>"
        f"⚠ Cannot connect to local Ollama at {st.session_state.ollama_url} | Expose port 11434 via ngrok or check your Settings tab."
        f"</div>",
        unsafe_allow_html=True
    )

st.subheader(f"{tab_name}")
st.caption(f"Workspace Context: {active_project['name']}")

# 1. DASHBOARD OVERVIEW
if tab_name == "Dashboard":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>Destination Channel</div>
            <div class='metric-value' style='font-size:1.5rem; color:{'#22d3ee' if channel_connected else '#f87171'};'>
                {chan_row['name'] if channel_connected else 'Not Linked'}
            </div>
            <div class='metric-label' style='margin-top:5px; font-size:0.65rem;'>
                Status: {'Connected (OAuth)' if channel_connected else 'Not Connected'}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>Monitored Sources</div>
            <div class='metric-value'>{len(source_channels)}</div>
            <div class='metric-label' style='margin-top:5px; font-size:0.65rem;'>Active sync handles</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>Imported Videos</div>
            <div class='metric-value'>{len(videos)}</div>
            <div class='metric-label' style='margin-top:5px; font-size:0.65rem;'>Pending or processed</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class='glass-card'>
            <div class='metric-label'>Generated Clips</div>
            <div class='metric-value'>{clips_count}</div>
            <div class='metric-label' style='margin-top:5px; font-size:0.65rem;'>Approved & scheduled</div>
        </div>
        """, unsafe_allow_html=True)

    # Connections details & mode configurations
    col_d1, col_d2 = st.columns([7, 5])
    
    with col_d1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Connected YouTube Channel")
        if channel_connected:
            col_av, col_tx = st.columns([1, 8])
            with col_av:
                st.markdown(f"<img src='{channel_meta.get('avatar', 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=100&auto=format&fit=crop')}' class='avatar-circle'>", unsafe_allow_html=True)
            with col_tx:
                st.markdown(f"**Channel:** {chan_row['name']}")
                st.caption(f"Channel ID: {channel_meta.get('channel_id', 'Unconnected')} | Subscribers: {channel_meta.get('subscribers', 0):,} | Total Uploads: {channel_meta.get('video_count', 0)}")
                st.markdown("<span class='status-badge badge-success'>OAuth Token Active</span>", unsafe_allow_html=True)
        else:
            st.warning("No destination channel linked to this workspace yet.")
            if st.button("Link YouTube Channel"):
                open_oauth_dialog(active_project["id"])
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_d2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Workspace Manager")
        with st.form("workspace_sw_form"):
            new_name = st.text_input("New Workspace Name:")
            new_desc = st.text_area("Target Channel Description:")
            submitted = st.form_submit_button("Initialize Workspace")
            if submitted and new_name:
                create_project(new_name, new_desc)
                st.success("New workspace initialized!")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Real time Activity Log Feed
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.write("### Active Processing Logs")
    if not activity_logs:
        st.info("No processing logs found. Paste a video link to start pipeline actions.")
    else:
        for log in activity_logs[:15]:
            col_l1, col_l2, col_l3 = st.columns([2, 6, 2])
            with col_l1:
                st.write(f"**{log['action_type']}**")
            with col_l2:
                st.caption(log["details"])
            with col_l3:
                st.caption(log["created_at"])
            st.markdown("<hr style='border-color:rgba(255,255,255,0.03); margin:6px 0;'>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# 2. VIDEO LIBRARY & IMPORT
elif tab_name == "Video Library & Import":
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.write("### Import Content / Monitor Sources")
    
    with st.form("source_form"):
        source_input = st.text_input("Paste YouTube Video Link or Channel Handle:", placeholder="e.g. https://www.youtube.com/watch?v=dQw4w9WgXcQ or @NASA")
        submit_btn = st.form_submit_button("Add Source")
        
        if submit_btn and source_input:
            source_input = source_input.strip()
            conn = get_db_connection()
            
            # Check if it is a video link
            is_youtube_video = (
                ("youtube.com/watch" in source_input) or 
                ("youtu.be/" in source_input) or 
                ("youtube.com/shorts" in source_input) or 
                ("youtube.com/embed" in source_input)
            )
            
            if is_youtube_video:
                vid_id = str(uuid.uuid4())
                filename = f"video_{int(datetime.utcnow().timestamp())}.mp4"
                conn.execute(
                    """INSERT INTO videos (id, project_id, filename, file_path, duration, width, height, fps, status, created_at) 
                       VALUES (?, ?, ?, ?, 360, 1920, 1080, 30, 'pending', ?)""",
                    (vid_id, active_project["id"], filename, source_input, datetime.utcnow().isoformat())
                )
                conn.execute(
                    "INSERT INTO activity_log (id, project_id, action_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), active_project["id"], "Imported Video", f"Imported YouTube link: {source_input}", datetime.utcnow().isoformat())
                )
                conn.commit()
                st.success("YouTube video link registered in library!")
            # Otherwise assume channel handle or page
            else:
                # Clean handle from full URL if they pasted it
                handle = source_input
                if "youtube.com/" in handle:
                    parts = handle.split("youtube.com/")
                    if len(parts) > 1:
                        handle = parts[1].replace("c/", "").replace("channel/", "").replace("user/", "")
                
                handle = handle if handle.startswith("@") else f"@{handle}"
                sid = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO source_channels (id, project_id, handle, name, avatar, subscribers, video_count, latest_upload, status, created_at) 
                       VALUES (?, ?, ?, ?, '', 0, 0, 'None', 'active', ?)""",
                    (sid, active_project["id"], handle, handle[1:], datetime.utcnow().isoformat())
                )
                conn.execute(
                    "INSERT INTO activity_log (id, project_id, action_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), active_project["id"], "Monitored Handle", f"Started monitoring channel handle: {handle}", datetime.utcnow().isoformat())
                )
                conn.commit()
                st.success(f"Added source handle {handle} to monitor list!")
                
            conn.close()
            st.rerun()
            
    st.markdown("</div>", unsafe_allow_html=True)
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Monitored Source Channels")
        if not source_channels:
            st.caption("No monitored channel handles yet.")
        else:
            for sc in source_channels:
                col_sc1, col_sc2 = st.columns([8, 2])
                with col_sc1:
                    st.write(f"**{sc['handle']}**")
                    st.caption("Auto sync state: Monitoring uploads")
                with col_sc2:
                    if st.button("Delete", key=f"del_sc_{sc['id']}"):
                        delete_source_channel(sc["id"])
                        st.rerun()
                st.markdown("<hr style='border-color:rgba(255,255,255,0.03); margin:8px 0;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_v2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Imported Videos Library")
        if not videos:
            st.caption("No videos imported yet.")
        else:
            for v in videos:
                col_vrow1, col_vrow2 = st.columns([7, 3])
                with col_vrow1:
                    st.write(f"**Link:** {v['file_path']}")
                    st.caption(f"Status: **{v['status']}** | Added: {v['created_at']}")
                with col_vrow2:
                    if v["status"] == "pending":
                        if st.button("Process AI clips", key=f"proc_v_{v['id']}"):
                            from clipforge_engine.pipeline import run_processing_pipeline
                            import threading
                            import asyncio
                            threading.Thread(target=lambda: asyncio.run(run_processing_pipeline(v["id"]))).start()
                            st.info("AI processing started in background. Monitor via dashboard.")
                            st.rerun()
                    else:
                        st.caption("✓ Clips Generated")
                st.markdown("<hr style='border-color:rgba(255,255,255,0.03); margin:8px 0;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# 3. GENERATED CLIPS
elif tab_name == "Generated Clips":
    if not videos:
        st.info("No videos in library. Go to 'Video Library & Import' to import content.")
    else:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Select Video File")
        vid_options = {v["file_path"]: v["id"] for v in videos}
        selected_vid_path = st.selectbox("Imported Video Target:", list(vid_options.keys()))
        selected_vid_id = vid_options[selected_vid_path]
        st.markdown("</div>", unsafe_allow_html=True)
        
        conn = get_db_connection()
        video_clips = conn.execute("SELECT * FROM clips WHERE video_id = ? ORDER BY score DESC", (selected_vid_id,)).fetchall()
        conn.close()
        
        col_ed1, col_ed2 = st.columns([7, 5])
        with col_ed1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### AI Extracted Viral Moments")
            if not video_clips:
                st.warning("No clips generated yet for this video. Trigger 'Process AI clips' under the videos library first.")
            else:
                for c in video_clips:
                    st.write(f"#### {c['title']}")
                    st.caption(f"Score: **{c['score']}%** | Timestamps: {c['start_time']}s - {c['end_time']}s | Duration: {c['duration']}s")
                    st.write(f"**AI Virality Analysis:** {c['explanation']}")
                    
                    col_cb1, col_cb2 = st.columns(2)
                    with col_cb1:
                        if st.button("Download Short Clip", key=f"dl_c_{c['id']}"):
                            st.info("Direct download initialized. Mock video saved successfully.")
                    with col_cb2:
                        if st.button("Schedule for Posting", key=f"queue_c_{c['id']}"):
                            conn = get_db_connection()
                            conn.execute(
                                "INSERT INTO schedules (id, project_id, day_of_week, time_of_day, is_active) VALUES (?, ?, 'Monday', '12:00', 1)",
                                (str(uuid.uuid4()), active_project["id"])
                            )
                            conn.execute(
                                "INSERT INTO activity_log (id, project_id, action_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
                                (str(uuid.uuid4()), active_project["id"], "Clip Gated & Queued", f"Scheduled clip '{c['title']}' for automatic upload.", datetime.utcnow().isoformat())
                            )
                            conn.commit()
                            conn.close()
                            st.success("Clip approved and added to smart posting queue!")
                            st.rerun()
                    st.markdown("<hr style='border-color:rgba(255,255,255,0.03); margin:12px 0;'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_ed2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### Enhancement Profile Presets")
            preset = st.selectbox("Style Profile Template:", ["MrBeast style", "IShowSpeed style", "Minimal Cinematic"])
            
            st.write("#### Rendering Adjustments")
            st.checkbox("Auto-Face Tracking Vertical Crop (OpenCV)", value=True)
            st.checkbox("Karaoke Subtitles Burn-in (ASS filter)", value=True)
            st.checkbox("Progress Bar Timer burning", value=True)
            st.slider("Font size scaling:", 14, 48, 28)
            st.color_picker("Highlight font color:", "#00F0FF")
            st.markdown("</div>", unsafe_allow_html=True)

# 4. AI KNOWLEDGE CHAT (RAG & INTEL)
elif tab_name == "AI Knowledge Chat":
    if not videos:
        st.info("No videos to build a knowledge base. Go to 'Video Library & Import' to import content.")
    else:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Select Video Context")
        vid_options = {v["file_path"]: v["id"] for v in videos}
        selected_vid_path = st.selectbox("Video Context:", list(vid_options.keys()))
        selected_vid_id = vid_options[selected_vid_path]
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Load summary, keywords, and graph
        summary = get_summary(selected_vid_id)
        keywords = get_keywords(selected_vid_id)
        graph = get_knowledge_graph(active_project["id"])
        
        col_chat1, col_chat2 = st.columns([7, 5])
        with col_chat1:
            # 1. Grounded RAG Chat
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### Grounded Chat Interface")
            
            # Load session history
            history = get_chat_history(active_project["id"], st.session_state.chat_session_id)
            for msg in history:
                if msg["role"] == "user":
                    st.markdown(f"**User**: {msg['message']}")
                else:
                    st.markdown(f"**Assistant**: {msg['message']}")
                st.markdown("<hr style='border-color:rgba(255,255,255,0.02); margin:8px 0;'>", unsafe_allow_html=True)
                
            with st.form("chat_form", clear_on_submit=True):
                user_msg = st.text_input("Ask anything about the transcripts:")
                submit_chat = st.form_submit_button("Ask local LLM")
                if submit_chat and user_msg:
                    add_chat_message(active_project["id"], st.session_state.chat_session_id, "user", user_msg)
                    
                    # Query ChromaDB collection
                    retrieved = query_similar_chunks(
                        project_id=active_project["id"],
                        query_text=user_msg,
                        k=4,
                        video_ids=[selected_vid_id],
                        model=st.session_state.embedding_model,
                        base_url=st.session_state.ollama_url
                    )
                    
                    # Answer generation
                    answer = generate_grounded_answer(
                        project_id=active_project["id"],
                        query=user_msg,
                        retrieved_chunks=retrieved,
                        model=st.session_state.ollama_model,
                        base_url=st.session_state.ollama_url
                    )
                    
                    add_chat_message(active_project["id"], st.session_state.chat_session_id, "assistant", answer)
                    log_retrieval(active_project["id"], user_msg, retrieved, answer)
                    st.rerun()
                    
            if st.button("Clear Chat History"):
                clear_chat_history(active_project["id"], st.session_state.chat_session_id)
                st.success("Chat history cleared.")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
            # 2. Semantic Scene Search
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### Semantic Scene Search")
            query_in = st.text_input("Search matching scene coordinates:", placeholder="e.g. SpaceX, deep learning")
            if query_in:
                hits = query_similar_chunks(
                    project_id=active_project["id"],
                    query_text=query_in,
                    k=4,
                    model=st.session_state.embedding_model,
                    base_url=st.session_state.ollama_url
                )
                for hit in hits:
                    meta = hit["metadata"]
                    start_t = float(meta["start_time"])
                    
                    hours = int(start_t // 3600)
                    minutes = int((start_t % 3600) // 60)
                    seconds = int(start_t % 60)
                    timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    
                    col_h1, col_h2 = st.columns([8, 2])
                    with col_h1:
                        st.write(f"**Found match (Time: {timestamp_str}):**")
                        st.write(f"*{hit['text']}*")
                    with col_h2:
                        if st.button("Preview Scene", key=f"preview_h_{hit['id']}"):
                            st.info(f"Seeking video to segment timestamp: {timestamp_str}")
                    st.markdown("<hr style='border-color:rgba(255,255,255,0.03); margin:8px 0;'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_chat2:
            # 3. Video Executive Summary
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### Executive Summary")
            if summary:
                st.write(summary["executive_summary"])
                if summary.get("action_items"):
                    st.write("**Action Items:**")
                    for act in summary["action_items"]:
                        st.write(f"- {act}")
            else:
                st.caption("No summary generated yet.")
            st.markdown("</div>", unsafe_allow_html=True)
            
            # 4. Local Entity Graph
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.write("### Local Knowledge Graph")
            if not graph:
                st.caption("No relationships resolved yet.")
            else:
                # Create offline gravity SVG simulation canvas
                svg_nodes = []
                svg_links = []
                unique_entities = list(set([g["source"] for g in graph] + [g["target"] for g in graph]))
                
                # Position coordinates
                import math
                coords = {}
                radius = 120
                for idx, node in enumerate(unique_entities[:10]):
                    angle = (idx * 2 * math.pi) / min(len(unique_entities), 10)
                    coords[node] = (150 + radius * math.cos(angle), 150 + radius * math.sin(angle))
                    svg_nodes.append(f"<circle cx='{coords[node][0]:.1f}' cy='{coords[node][1]:.1f}' r='10' fill='#00f0ff' stroke='#fff' stroke-width='1.5'/><text x='{coords[node][0]+12:.1f}' y='{coords[node][1]+4:.1f}' fill='#fff' font-size='10' font-family='Inter'>{node}</text>")
                    
                for idx, edge in enumerate(graph[:15]):
                    src, trg = edge["source"], edge["target"]
                    if src in coords and trg in coords:
                        svg_links.append(f"<line x1='{coords[src][0]:.1f}' y1='{coords[src][1]:.1f}' x2='{coords[trg][0]:.1f}' y2='{coords[trg][1]:.1f}' stroke='#7b2cbf' stroke-width='2' stroke-opacity='0.6'/>")
                        
                svg_content = f"""
                <svg width='100%' height='300px' viewBox='0 0 350 300' style='background:#171c26; border-radius:8px;'>
                    {' '.join(svg_links)}
                    {' '.join(svg_nodes)}
                </svg>
                """
                st.components.v1.html(svg_content, height=310)
            st.markdown("</div>", unsafe_allow_html=True)

# 5. SETTINGS
elif tab_name == "Settings":
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.write("### Local RAG configurations")
    
    st.session_state.ollama_url = st.text_input("Ollama endpoint URL (use ngrok link if on cloud):", value=st.session_state.ollama_url)
    st.session_state.ollama_model = st.text_input("Ollama Chat model:", value=st.session_state.ollama_model)
    st.session_state.embedding_model = st.text_input("Ollama Embedding model:", value=st.session_state.embedding_model)
    
    if st.button("Save RAG configurations"):
        update_setting("ollama_url", st.session_state.ollama_url)
        update_setting("ollama_model", st.session_state.ollama_model)
        update_setting("embedding_model", st.session_state.embedding_model)
        st.success("RAG options successfully configured locally.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
