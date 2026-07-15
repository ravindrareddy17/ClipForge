import os
import sys
import json
import uuid
import sqlite3
from datetime import datetime
import streamlit as st

# Add backend directory to sys.path to reuse database and pipeline services
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

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
    get_editing_profile, update_editing_profile
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

# Google OAuth Connection Dialog
@st.dialog("Google Account Chooser (OAuth 2.0)")
def open_oauth_dialog(project_id):
    st.write("Grant ClipForge SaaS permissions to upload videos and retrieve channel analytics:")
    account_email = st.selectbox("Select Account:", ["pasam.vignesh@gmail.com", "vignesh.creator@shorts.co"])
    st.caption("Permissions requested:\\n✓ Manage your YouTube videos\\n✓ Retrieve channels data")
    
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

# State initialization
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Dashboard"

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
            <h2 style='margin: 0; font-size: 1.2rem; font-weight: 900; color: white;'>ClipForge</h2>
            <span style='font-size: 0.62rem; color: #00f0ff; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em;'>Enterprise Engine</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    project_names = [p["name"] for p in projects]
    selected_project_name = st.selectbox("Destination Workspace", project_names)
    active_project = next(p for p in projects if p["name"] == selected_project_name)
    
    st.markdown("<hr style='border-color: rgba(255, 255, 255, 0.05); margin: 15px 0;'>", unsafe_allow_html=True)

    # 5 Simple tabs navigation
    tabs = [
        "Dashboard",
        "Destination Channels",
        "Source Channels & Videos",
        "AI Clip Generator & Editor",
        "Posting Scheduler"
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
st.subheader(f"{tab_name}")
st.caption(f"Workspace Context: {active_project['name']}")

# 1. DASHBOARD OVERVIEW
if tab_name == "Dashboard":
    # 4 Simple Metric Cards
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
                st.session_state.active_tab = "Destination Channels"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_d2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Posting Automation Mode")
        mode = st.radio("Upload triggers config:", ["Manual Approval Gated", "Fully Automatic AI scheduler"])
        st.caption("✓ **Manual**: Clips must be checked, custom crop bounds applied, and manually sent to queue.")
        st.caption("✓ **Automatic**: Monitored channels imports are auto-transcribed, cut, captioned, and queued.")
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

# 2. DESTINATION CHANNELS & WORKSPACES
elif tab_name == "Destination Channels":
    col_c1, col_c2 = st.columns([7, 5])
    
    with col_c1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Linked Destination Channels")
        if channel_connected:
            col_av, col_tx, col_bt = st.columns([1, 6, 3])
            with col_av:
                st.markdown(f"<img src='{channel_meta.get('avatar', 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=100&auto=format&fit=crop')}' class='avatar-circle'>", unsafe_allow_html=True)
            with col_tx:
                st.markdown(f"**{chan_row['name']}**")
                st.caption(f"Channel ID: {channel_meta.get('channel_id')} | Subscribers: {channel_meta.get('subscribers', 0):,}")
                st.caption(f"Last Sync: {channel_meta.get('last_sync')} | Token Health: Healthy")
            with col_bt:
                if st.button("Disconnect Channel", key="disconnect_chan"):
                    conn = get_db_connection()
                    conn.execute("DELETE FROM channels WHERE project_id = ?", (active_project["id"],))
                    conn.commit()
                    conn.close()
                    st.success("Channel disconnected.")
                    st.rerun()
        else:
            st.info("No destination channel linked yet. Connect a channel using OAuth below.")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_c2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Connect Channel (Google OAuth)")
        st.write("Authorize ClipForge to publish shorts directly to your YouTube channel:")
        
        if st.button("Connect New Channel (Google OAuth)"):
            open_oauth_dialog(active_project["id"])
            
        st.markdown("</div>", unsafe_allow_html=True)

# 3. SOURCE CHANNELS & VIDEOS
elif tab_name == "Source Channels & Videos":
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.write("### Import Content / Monitor Sources")
    
    with st.form("source_form"):
        source_input = st.text_input("Paste YouTube Video Link or Channel Handle:", placeholder="e.g. https://www.youtube.com/watch?v=dQw4w9WgXcQ or @NASA")
        submit_btn = st.form_submit_button("Add Source")
        
        if submit_btn and source_input:
            source_input = source_input.strip()
            conn = get_db_connection()
            
            # Check if it is a video link
            if "youtube.com" in source_input or "youtu.be" in source_input:
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
            # Otherwise assume channel handle
            else:
                handle = source_input if source_input.startswith("@") else f"@{source_input}"
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
                            # Update video status to completed and seed 3 clips
                            conn = get_db_connection()
                            conn.execute("UPDATE videos SET status = 'completed' WHERE id = ?", (v["id"],))
                            
                            # Seed 3 clips
                            clips_mock = [
                                ("Mindblowing Moment #1", 12.0, 42.0, 94, "Highly engaging sequence explaining target goals."),
                                ("Interesting Focus #2", 110.0, 135.0, 88, "Clear visual speaker engagement sequence."),
                                ("Outro Hook #3", 240.0, 290.0, 79, "Viral final hook call to action details.")
                            ]
                            for title, start, end, score, exp in clips_mock:
                                conn.execute(
                                    """INSERT INTO clips (id, video_id, title, start_time, end_time, duration, score, explanation, status, created_at) 
                                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?)""",
                                    (str(uuid.uuid4()), v["id"], title, start, end, end - start, score, exp, datetime.utcnow().isoformat())
                                )
                            # Log action
                            conn.execute(
                                "INSERT INTO activity_log (id, project_id, action_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
                                (str(uuid.uuid4()), active_project["id"], "AI Clips Generated", f"Extracted 3 clips for imported video {v['id'][:8]}.", datetime.utcnow().isoformat())
                            )
                            conn.commit()
                            conn.close()
                            st.success("AI clips generated successfully!")
                            st.rerun()
                    else:
                        st.caption("✓ Clips Generated")
                st.markdown("<hr style='border-color:rgba(255,255,255,0.03); margin:8px 0;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# 4. AI CLIP GENERATOR & EDITOR
elif tab_name == "AI Clip Generator & Editor":
    if not videos:
        st.info("No videos in library. Go to 'Source Channels & Videos' to import content.")
    else:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Select Video File")
        vid_options = {v["file_path"]: v["id"] for v in videos}
        selected_vid_path = st.selectbox("Imported Video Target:", list(vid_options.keys()))
        selected_vid_id = vid_options[selected_vid_path]
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Load clips
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
                            # Add to schedules queue
                            conn = get_db_connection()
                            # Select random day/time to post
                            conn.execute(
                                "INSERT INTO schedules (id, project_id, day_of_week, time_of_day, is_active) VALUES (?, ?, 'Monday', '12:00', 1)",
                                (str(uuid.uuid4()), active_project["id"])
                            )
                            # Log action
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

# 5. POSTING SCHEDULER
elif tab_name == "Posting Scheduler":
    col_sc1, col_sc2 = st.columns([5, 7])
    
    with col_sc1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Queue Auto-Posting Slots")
        
        with st.form("slot_form"):
            day = st.selectbox("Day of Week:", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            time_val = st.text_input("Time of Day (24h format):", placeholder="e.g. 18:30")
            add_slot_btn = st.form_submit_button("Add Posting Slot")
            
            if add_slot_btn and time_val:
                create_schedule(active_project["id"], day, time_val)
                # Log action
                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO activity_log (id, project_id, action_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), active_project["id"], "Added Time Slot", f"Added posting slot: {day} at {time_val}", datetime.utcnow().isoformat())
                )
                conn.commit()
                conn.close()
                st.success("New posting slot added!")
                st.rerun()
                
        st.write("#### Scheduled Auto-Upload Slots")
        if not schedules_list:
            st.caption("No schedule timeslots added yet.")
        else:
            for s in schedules_list:
                col_srow1, col_srow2 = st.columns([8, 2])
                with col_srow1:
                    st.write(f"✦ **{s['day_of_week']}** at **{s['time_of_day']}**")
                with col_srow2:
                    if st.button("Delete", key=f"del_s_{s['id']}"):
                        delete_schedule(s["id"])
                        st.rerun()
                st.markdown("<hr style='border-color:rgba(255,255,255,0.03); margin:8px 0;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_sc2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.write("### Published Queue Status")
        
        if not channel_connected:
            st.warning("Destination Channel not linked yet. Connect a channel to manage posting states.")
        else:
            st.info("Smart auto-posting optimizer is active. Clip uploads are gated according to slot rules.")
            
            st.write("#### Scheduled Uploads Pipeline")
            st.markdown("""
            | Clip Title | Target Date | Platform | Status |
            | :--- | :--- | :--- | :--- |
            | Mindblowing Moment #1 | Monday 12:00 | YouTube Shorts | <span style='color:#fbbf24; font-weight:700;'>Scheduled</span> |
            | MrBeast Focus Cut | Wednesday 13:00 | YouTube Shorts | <span style='color:#22d3ee; font-weight:700;'>Published</span> |
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
