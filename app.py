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
    query_similar_chunks, generate_grounded_answer, format_timestamp
)
from clipforge_engine.video_qa_agents import run_video_qa_pipeline
from clipforge_engine.channel import resolve_channel_videos, import_channel_videos, search_channel_library
from clipforge_engine.llm_client import (
    get_active_provider, get_groq_api_key, get_gemini_api_key,
    test_provider_connection, get_active_model, DEFAULT_MODELS,
    mask_api_key
)
import clipforge_engine.cse473_lab as cse473

# Run database setup
init_db()

# Page config
st.set_page_config(
    page_title="ClipForge AI — Viral Shorts & Video Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'seek_time' not in st.session_state:
    st.session_state.seek_time = 0
if 'channel_discovered_videos' not in st.session_state:
    st.session_state.channel_discovered_videos = []

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

# Helper to resolve clip/video paths from relative, static, or absolute formats
def resolve_file_path(p):
    if not p:
        return None
    p_norm = os.path.normpath(p)
    if os.path.exists(p_norm) and os.path.getsize(p_norm) > 1000:
        return p_norm
    if p.startswith("/static/"):
        rel = p.replace("/static/", "").replace("/", os.sep)
        full = os.path.join(os.path.dirname(__file__), "backend", "data", rel)
        if os.path.exists(full) and os.path.getsize(full) > 1000:
            return full
    local_cand = os.path.join(os.path.dirname(__file__), "backend", "data", "temp", os.path.basename(p))
    if os.path.exists(local_cand) and os.path.getsize(local_cand) > 1000:
        return local_cand
    local_clip = os.path.join(os.path.dirname(__file__), "backend", "data", "clips", os.path.basename(p))
    if os.path.exists(local_clip) and os.path.getsize(local_clip) > 1000:
        return local_clip
    return None

# Helper to extract bracketed timestamps from text
def extract_timestamp_buttons(text: str):
    import re
    pattern = r"\[(\d{1,2}:\d{2}(?::\d{2})?)(?:[–\-](\d{1,2}:\d{2}(?::\d{2})?))?\]"
    found = []
    for m in re.finditer(pattern, text):
        raw_tag = m.group(0)
        ts_str = m.group(1)
        parts = ts_str.split(":")
        try:
            if len(parts) == 2:
                sec = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                sec = int(float(ts_str))
            found.append((raw_tag, sec))
        except Exception:
            pass
    return found

# Modern, High-Contrast Minimalist Dark Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');
    
    /* 1. Base theme & atmospheric background */
    .stApp {
        background-color: #080b11 !important;
        background-image: 
            radial-gradient(circle at 15% 10%, rgba(99, 102, 241, 0.09) 0%, transparent 40%),
            radial-gradient(circle at 85% 15%, rgba(139, 92, 246, 0.08) 0%, transparent 45%),
            radial-gradient(circle at 50% 90%, rgba(14, 165, 233, 0.06) 0%, transparent 50%) !important;
        background-attachment: fixed !important;
        color: #f1f5f9 !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* 2. SIDEBAR TOGGLE & COLLAPSE ARROW: 100% remove text leak 'keyboard_double_' and render clean SVG chevron in appropriate size */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"] button,
    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapsedControl"] button,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"],
    div[data-testid="stToolbar"] button[data-testid="stExpandSidebarButton"] {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 32px !important;
        height: 32px !important;
        min-width: 32px !important;
        min-height: 32px !important;
        max-width: 32px !important;
        max-height: 32px !important;
        padding: 0 !important;
        margin: 4px !important;
        border-radius: 8px !important;
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        cursor: pointer !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        outline: none !important;
        box-shadow: none !important;
        position: relative !important;
        overflow: hidden !important;
        font-size: 0 !important;
        line-height: 0 !important;
        color: transparent !important;
    }

    [data-testid="stSidebarCollapseButton"]:hover,
    [data-testid="stSidebarCollapseButton"] button:hover,
    button[data-testid="stSidebarCollapseButton"]:hover,
    button[data-testid="stExpandSidebarButton"]:hover,
    [data-testid="stSidebarCollapsedControl"]:hover,
    [data-testid="stSidebarCollapsedControl"] button:hover,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"]:hover,
    div[data-testid="stToolbar"] button[data-testid="stExpandSidebarButton"]:hover {
        background: rgba(99, 102, 241, 0.2) !important;
        border-color: rgba(129, 140, 248, 0.45) !important;
        box-shadow: 0 0 12px rgba(99, 102, 241, 0.25) !important;
    }

    /* 100% remove text leak 'keyboard_double_' by hiding all children elements & text */
    [data-testid="stSidebarCollapseButton"] *,
    [data-testid="stSidebarCollapseButton"] button *,
    button[data-testid="stSidebarCollapseButton"] *,
    button[data-testid="stExpandSidebarButton"] *,
    [data-testid="stSidebarCollapsedControl"] *,
    [data-testid="stSidebarCollapsedControl"] button *,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"] * {
        font-size: 0 !important;
        line-height: 0 !important;
        color: transparent !important;
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
    }

    /* Left-facing Side Closer Arrow for closing sidebar (Appropriate size: 18x18px) */
    [data-testid="stSidebarCollapseButton"] button::after,
    button[data-testid="stSidebarCollapseButton"]::after,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"]::after {
        content: '' !important;
        display: block !important;
        width: 18px !important;
        height: 18px !important;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23cbd5e1' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='13 17 8 12 13 7'%3E%3C/polyline%3E%3Cpolyline points='18 17 13 12 18 7'%3E%3C/polyline%3E%3C/svg%3E") !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        background-size: 18px 18px !important;
        transition: transform 0.18s ease, filter 0.18s ease !important;
    }

    [data-testid="stSidebarCollapseButton"] button:hover::after,
    button[data-testid="stSidebarCollapseButton"]:hover::after,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"]:hover::after {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23818cf8' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='13 17 8 12 13 7'%3E%3C/polyline%3E%3Cpolyline points='18 17 13 12 18 7'%3E%3C/polyline%3E%3C/svg%3E") !important;
        transform: translateX(-1.5px) !important;
    }

    /* Right-facing Opener Arrow for opening/expanding sidebar (Appropriate size: 18x18px) */
    button[data-testid="stExpandSidebarButton"]::after,
    [data-testid="stSidebarCollapsedControl"] button::after,
    div[data-testid="stToolbar"] button[data-testid="stExpandSidebarButton"]::after {
        content: '' !important;
        display: block !important;
        width: 18px !important;
        height: 18px !important;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23cbd5e1' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 17 11 12 6 7'%3E%3C/polyline%3E%3Cpolyline points='11 17 16 12 11 7'%3E%3C/polyline%3E%3C/svg%3E") !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        background-size: 18px 18px !important;
        transition: transform 0.18s ease, filter 0.18s ease !important;
    }

    button[data-testid="stExpandSidebarButton"]:hover::after,
    [data-testid="stSidebarCollapsedControl"] button:hover::after,
    div[data-testid="stToolbar"] button[data-testid="stExpandSidebarButton"]:hover::after {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23818cf8' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 17 11 12 6 7'%3E%3C/polyline%3E%3Cpolyline points='11 17 16 12 11 7'%3E%3C/polyline%3E%3C/svg%3E") !important;
        transform: translateX(1.5px) !important;
    }
    
    /* 3. Header Navbar */
    header[data-testid="stHeader"] {
        background: rgba(8, 11, 17, 0.85) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    header[data-testid="stHeader"] * {
        color: #94a3b8 !important;
    }
    
    /* 4. Headings & Gradient Titles */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        letter-spacing: -0.02em !important;
    }
    .gradient-title {
        background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #a5b4fc 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
    }
    .gradient-accent {
        background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        font-weight: 700 !important;
    }
    
    /* 5. Typography */
    label, p, .stMarkdown p {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #cbd5e1;
        line-height: 1.6;
    }
    .stApp label, .stSelectbox label, .stTextInput label {
        color: #cbd5e1 !important;
        font-weight: 600 !important;
        font-size: 0.86rem !important;
        letter-spacing: 0.01em !important;
    }
    
    /* 6. Feature Pills & Callout Boxes */
    .feature-pill-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 9999px;
        padding: 4px 12px;
        font-size: 0.76rem;
        color: #cbd5e1;
        font-weight: 600;
        backdrop-filter: blur(8px);
    }
    .hook-rationale-box {
        background: rgba(15, 23, 42, 0.6);
        border-left: 3px solid #8b5cf6;
        border-radius: 0 10px 10px 0;
        padding: 12px 16px;
        margin: 12px 0;
        color: #cbd5e1;
        font-size: 0.92rem;
        line-height: 1.6;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* 7. Glassmorphic Dark Cards */
    div[data-testid="stVerticalBlockBorderDiv"] {
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.6) 0%, rgba(13, 19, 32, 0.75) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 14px !important;
        padding: 1.35rem !important;
        box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        margin-bottom: 1.15rem !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-testid="stVerticalBlockBorderDiv"]:hover {
        border-color: rgba(99, 102, 241, 0.3) !important;
        box-shadow: 0 12px 30px -4px rgba(0, 0, 0, 0.5), 0 0 16px rgba(99, 102, 241, 0.08) !important;
    }
    
    /* 8. Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #090c14 0%, #06080e 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.3) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 0.3rem !important;
    }
    
    /* Sidebar Navigation Buttons - Clean List Row Style */
    section[data-testid="stSidebar"] div.stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 10px 14px !important;
        margin: 1px 0 !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        transition: all 0.15s ease-in-out !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        color: #94a3b8 !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background: rgba(255, 255, 255, 0.04) !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
        color: #f8fafc !important;
        transform: translateX(3px) !important;
        box-shadow: none !important;
    }
    /* Active Nav Button */
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"],
    section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.08) 100%) !important;
        border: 1px solid rgba(99, 102, 241, 0.4) !important;
        border-left: 3px solid #818cf8 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2) !important;
    }
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover,
    section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"]:hover {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.28) 0%, rgba(139, 92, 246, 0.14) 100%) !important;
        border-color: rgba(99, 102, 241, 0.55) !important;
        color: #ffffff !important;
        transform: none !important;
    }
    
    /* 9. Standard Page Buttons */
    div.stButton > button {
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.8) 100%) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 9px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 7px 16px !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25) !important;
        transition: all 0.15s ease-in-out !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(180deg, rgba(51, 65, 85, 0.8) 0%, rgba(30, 41, 59, 0.9) 100%) !important;
        border-color: rgba(99, 102, 241, 0.5) !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35), 0 0 10px rgba(99, 102, 241, 0.18) !important;
    }
    
    /* 10. Primary Submit Buttons (CTAs) */
    div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 9px 20px !important;
        font-weight: 700 !important;
        font-size: 0.92rem !important;
        letter-spacing: 0.01em !important;
        box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
        transition: all 0.18s ease !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 22px rgba(124, 58, 237, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
        filter: brightness(1.08) !important;
    }
    
    /* 11. Download Buttons */
    div[data-testid="stDownloadButton"] > button {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(52, 211, 153, 0.4) !important;
        border-radius: 9px !important;
        font-weight: 700 !important;
        font-size: 0.88rem !important;
        padding: 7px 16px !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.28) !important;
        transition: all 0.15s ease !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background: linear-gradient(135deg, #047857 0%, #059669 100%) !important;
        border-color: #34d399 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4) !important;
    }
    
    /* 12. Monospace Timestamp Seeking Pill Buttons */
    button[key*="ts_"], button[key*="srch_seek_"] {
        font-family: 'JetBrains Mono', monospace !important;
        background: rgba(99, 102, 241, 0.12) !important;
        border: 1px solid rgba(99, 102, 241, 0.35) !important;
        color: #a5b4fc !important;
        border-radius: 7px !important;
        padding: 4px 9px !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        transition: all 0.15s ease !important;
    }
    button[key*="ts_"]:hover, button[key*="srch_seek_"]:hover {
        background: rgba(99, 102, 241, 0.25) !important;
        border-color: #818cf8 !important;
        color: #ffffff !important;
        box-shadow: 0 0 10px rgba(99, 102, 241, 0.35) !important;
    }
    
    /* 13. Alert Boxes (st.info, st.success, etc.) */
    div[data-testid="stAlert"] {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
        backdrop-filter: blur(10px) !important;
    }
    div[data-testid="stAlert"] * {
        color: #ffffff !important;
    }
    
    /* 14. Inputs & Selectboxes */
    div[data-testid="stTextInput"] input, 
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stSelectbox"] > div {
        background-color: rgba(15, 23, 42, 0.7) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        font-size: 0.9rem !important;
        transition: border-color 0.18s, box-shadow 0.18s !important;
    }
    div[data-testid="stTextInput"] input:focus, 
    div[data-testid="stTextArea"] textarea:focus,
    div[data-testid="stSelectbox"] > div:focus-within {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25) !important;
        outline: none !important;
    }
    div[data-testid="stSelectbox"] * {
        color: #ffffff !important;
    }
    
    /* 15. Chat Bubbles */
    div[data-testid="stChatMessage"] {
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.75) 0%, rgba(11, 17, 30, 0.85) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        margin-bottom: 10px !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2) !important;
    }
    div[data-testid="stChatMessage"][data-testid*="user"] {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%) !important;
        border: 1px solid rgba(99, 102, 241, 0.25) !important;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.06) !important;
    }
    div[data-testid="stChatMessage"] p, div[data-testid="stChatMessage"] span, div[data-testid="stChatMessage"] li {
        color: #f1f5f9 !important;
        font-size: 0.93rem !important;
        line-height: 1.65 !important;
    }
    
    /* 16. Status Badges */
    .status-pill {
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        line-height: 1.4;
    }
    .pill-green {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.35);
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.15);
    }
    .pill-blue {
        background: rgba(59, 130, 246, 0.12);
        color: #60a5fa;
        border: 1px solid rgba(96, 165, 250, 0.35);
    }
    .pill-purple {
        background: rgba(168, 85, 247, 0.12);
        color: #c084fc;
        border: 1px solid rgba(192, 132, 252, 0.35);
    }
    .pill-yellow {
        background: rgba(245, 158, 11, 0.12);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.35);
    }
    
    /* 17. Interactive StTabs (Segmented Pill Switcher) */
    div[data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.65) !important;
        padding: 5px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        gap: 4px !important;
        margin-bottom: 1.25rem !important;
    }
    div[data-baseweb="tab-highlight"],
    div[data-baseweb="tab-border"] {
        display: none !important;
    }
    button[data-baseweb="tab"] {
        background: transparent !important;
        color: #94a3b8 !important;
        font-weight: 600 !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        padding: 7px 14px !important;
        font-size: 0.85rem !important;
        outline: none !important;
        box-shadow: none !important;
        transition: all 0.18s ease !important;
    }
    button[data-baseweb="tab"]:hover {
        color: #f1f5f9 !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.28) 0%, rgba(139, 92, 246, 0.2) 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: 1px solid rgba(99, 102, 241, 0.45) !important;
        box-shadow: 0 2px 10px rgba(99, 102, 241, 0.2) !important;
    }
    button[data-baseweb="tab"]:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    
    /* 18. Custom Scrollbars */
    ::-webkit-scrollbar {
        width: 7px;
        height: 7px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(8, 11, 17, 0.8);
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(99, 102, 241, 0.25);
        border-radius: 9999px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(99, 102, 241, 0.45);
    }
</style>
""", unsafe_allow_html=True)

# State initialization
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Create Clips"
if 'chat_session_id' not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())

# Load settings from DB, Secrets, or Defaults
db_settings = {}
try:
    db_settings = get_settings()
except Exception:
    pass

def _resolve_setting(key, secret_key, default_val):
    try:
        if secret_key in st.secrets:
            return str(st.secrets[secret_key])
    except Exception:
        pass
    return str(db_settings.get(key, default_val))

default_llm_provider = _resolve_setting("llm_provider", "LLM_PROVIDER", get_active_provider())
default_groq_api_key = _resolve_setting("groq_api_key", "GROQ_API_KEY", get_groq_api_key() or "")
default_groq_model = _resolve_setting("groq_model", "GROQ_MODEL", DEFAULT_MODELS["groq"])
default_gemini_api_key = _resolve_setting("gemini_api_key", "GEMINI_API_KEY", get_gemini_api_key() or "")
default_gemini_model = _resolve_setting("gemini_model", "GEMINI_MODEL", DEFAULT_MODELS["gemini"])
default_ollama_url = _resolve_setting("ollama_url", "OLLAMA_URL", "http://localhost:11434")
default_ollama_model = _resolve_setting("ollama_model", "OLLAMA_MODEL", DEFAULT_MODELS["ollama"])
default_embedding_model = _resolve_setting("embedding_model", "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

if 'llm_provider' not in st.session_state:
    st.session_state.llm_provider = default_llm_provider
if 'groq_api_key' not in st.session_state:
    st.session_state.groq_api_key = default_groq_api_key
if 'groq_model' not in st.session_state:
    st.session_state.groq_model = default_groq_model
if 'gemini_api_key' not in st.session_state:
    st.session_state.gemini_api_key = default_gemini_api_key
if 'gemini_model' not in st.session_state:
    st.session_state.gemini_model = default_gemini_model
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
    <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding: 10px 12px; background: rgba(17, 24, 39, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; backdrop-filter: blur(12px);'>
        <div style='width: 38px; height: 38px; border-radius: 9px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%); display: flex; align-items: center; justify-content: center; font-size: 1.25rem; color: #ffffff; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4); flex-shrink: 0;'>⚡</div>
        <div style='flex: 1; min-width: 0;'>
            <div style='display: flex; align-items: center; justify-content: space-between;'>
                <span style='font-size: 1.15rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;'>ClipForge</span>
                <span style='background: rgba(99, 102, 241, 0.2); color: #a5b4fc; font-size: 0.62rem; font-weight: 700; padding: 2px 6px; border-radius: 5px; border: 1px solid rgba(99, 102, 241, 0.35); letter-spacing: 0.04em;'>V2 PRO</span>
            </div>
            <div style='font-size: 0.66rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 1px;'>AI Video Studio</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    project_names = [p["name"] for p in projects]
    selected_project_name = st.selectbox("Active Workspace", project_names)
    active_project = next(p for p in projects if p["name"] == selected_project_name)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 14px 0;'>", unsafe_allow_html=True)

    # Check for hidden dev parameter to reveal CSE473 AI Lab only if explicitly requested
    show_lab = st.query_params.get("lab") in ["1", "true", "True"]
    if not show_lab and st.session_state.get("active_tab") == "CSE473 AI Lab":
        st.session_state.active_tab = "Create Clips"

    # Core Navigation Tabs (CSE473 AI Lab hidden from platform)
    nav_tabs = [
        ("Create Clips", "⚡"),
        ("AI Video Chat", "💬"),
        ("YouTube Channels", "📺"),
        ("Library & Settings", "⚙️")
    ]
    if show_lab:
        nav_tabs.insert(3, ("CSE473 AI Lab", "🧪"))

    for tab_name, icon in nav_tabs:
        is_active = st.session_state.active_tab == tab_name
        btn_type = "primary" if is_active else "secondary"
        if st.button(f"{icon}  {tab_name}", key=f"nav_{tab_name}", type=btn_type, use_container_width=True):
            st.session_state.active_tab = tab_name
            st.rerun()

    st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin: 16px 0;'>", unsafe_allow_html=True)
    
    # Modern Telemetry AI Engine Status Card
    active_prov = st.session_state.llm_provider
    if active_prov == "groq":
        k = st.session_state.groq_api_key
        if k and len(k) > 10:
            m_disp = st.session_state.groq_model.split("/")[-1]
            st.markdown(f"""
            <div style='padding: 10px 12px; background: rgba(16, 24, 40, 0.65); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px; display: flex; align-items: center; gap: 9px;'>
                <span style='width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; display: inline-block; flex-shrink: 0;'></span>
                <div style='flex: 1; min-width: 0;'>
                    <div style='font-size: 0.72rem; font-weight: 700; color: #34d399; text-transform: uppercase; letter-spacing: 0.05em;'>Groq Cloud Active</div>
                    <div style='font-size: 0.68rem; color: #94a3b8; font-family: "JetBrains Mono", monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>{m_disp}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='padding: 10px 12px; background: rgba(30, 20, 10, 0.65); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 10px; display: flex; align-items: center; gap: 9px;'>
                <span style='width: 8px; height: 8px; border-radius: 50%; background: #f59e0b; box-shadow: 0 0 8px #f59e0b; display: inline-block; flex-shrink: 0;'></span>
                <div style='flex: 1; min-width: 0;'>
                    <div style='font-size: 0.72rem; font-weight: 700; color: #fbbf24; text-transform: uppercase; letter-spacing: 0.05em;'>Groq Key Missing</div>
                    <div style='font-size: 0.68rem; color: #cbd5e1;'>Configure in Settings</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    elif active_prov == "gemini":
        k = st.session_state.gemini_api_key
        if k and len(k) > 10:
            st.markdown(f"""
            <div style='padding: 10px 12px; background: rgba(16, 24, 40, 0.65); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px; display: flex; align-items: center; gap: 9px;'>
                <span style='width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; display: inline-block; flex-shrink: 0;'></span>
                <div style='flex: 1; min-width: 0;'>
                    <div style='font-size: 0.72rem; font-weight: 700; color: #34d399; text-transform: uppercase; letter-spacing: 0.05em;'>Gemini Active</div>
                    <div style='font-size: 0.68rem; color: #94a3b8; font-family: "JetBrains Mono", monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>{st.session_state.gemini_model}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='padding: 10px 12px; background: rgba(30, 20, 10, 0.65); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 10px; display: flex; align-items: center; gap: 9px;'>
                <span style='width: 8px; height: 8px; border-radius: 50%; background: #f59e0b; box-shadow: 0 0 8px #f59e0b; display: inline-block; flex-shrink: 0;'></span>
                <div style='flex: 1; min-width: 0;'>
                    <div style='font-size: 0.72rem; font-weight: 700; color: #fbbf24; text-transform: uppercase; letter-spacing: 0.05em;'>Gemini Key Missing</div>
                    <div style='font-size: 0.68rem; color: #cbd5e1;'>Configure in Settings</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        is_online, models_list = test_ollama_connection(st.session_state.ollama_url)
        if is_online:
            st.markdown(f"""
            <div style='padding: 10px 12px; background: rgba(16, 24, 40, 0.65); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 10px; display: flex; align-items: center; gap: 9px;'>
                <span style='width: 8px; height: 8px; border-radius: 50%; background: #3b82f6; box-shadow: 0 0 8px #3b82f6; display: inline-block; flex-shrink: 0;'></span>
                <div style='flex: 1; min-width: 0;'>
                    <div style='font-size: 0.72rem; font-weight: 700; color: #60a5fa; text-transform: uppercase; letter-spacing: 0.05em;'>Ollama Online</div>
                    <div style='font-size: 0.68rem; color: #94a3b8; font-family: "JetBrains Mono", monospace;'>{len(models_list)} models loaded</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='padding: 10px 12px; background: rgba(30, 20, 10, 0.65); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 10px; display: flex; align-items: center; gap: 9px;'>
                <span style='width: 8px; height: 8px; border-radius: 50%; background: #f59e0b; box-shadow: 0 0 8px #f59e0b; display: inline-block; flex-shrink: 0;'></span>
                <div style='flex: 1; min-width: 0;'>
                    <div style='font-size: 0.72rem; font-weight: 700; color: #fbbf24; text-transform: uppercase; letter-spacing: 0.05em;'>Ollama Offline</div>
                    <div style='font-size: 0.68rem; color: #cbd5e1;'>Self-Hosted Local Mode</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# Fetch database records for active workspace
videos = get_videos(active_project["id"])
tab = st.session_state.active_tab

# ============================================================
# TAB 1: CREATE CLIPS (The Core Repurposing Engine)
# ============================================================
if tab == "Create Clips":
    col_t1, col_t2 = st.columns([9, 3])
    with col_t1:
        st.markdown("<h1 class='gradient-title' style='margin:0; font-size:2rem;'>⚡ Create Viral Shorts</h1>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#94a3b8; font-size:0.92rem; margin-top:4px;'>"
            "Paste any YouTube link or video file to extract high-retention vertical clips with subtitles & AI hooks."
            "</p>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<div style='display:flex; gap:8px; margin-top:6px; margin-bottom:12px; flex-wrap:wrap;'>"
            "<span class='feature-pill-badge'>✨ 9:16 Smart Auto-Framing</span>"
            "<span class='feature-pill-badge'>🔥 Viral Hook Scoring</span>"
            "<span class='feature-pill-badge'>📝 Word-Level Transcription</span>"
            "<span class='feature-pill-badge'>⚡ Multi-Provider Cloud LLM</span>"
            "</div>",
            unsafe_allow_html=True
        )
    with col_t2:
        if st.button("🔄 Refresh Studio", use_container_width=True):
            st.rerun()

    # Input Box: Simple, Clean, Prominent
    with st.container(border=True):
        st.markdown("<h3 style='margin:0 0 10px 0;' class='gradient-title'>📥 Ingest Video</h3>", unsafe_allow_html=True)
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
        st.write("##### Active Video:")
        col_sel1, col_sel2, col_sel3 = st.columns([6, 3, 3])
        with col_sel1:
            selected_vid_title = st.selectbox("Select Video:", list(vid_options.keys()), label_visibility="collapsed")
            selected_vid_id = vid_options[selected_vid_title]
            current_video = dict(next(v for v in videos if v["id"] == selected_vid_id))
        with col_sel2:
            if st.button("⚡ Re-Process Video", use_container_width=True, help="Re-run pipeline to extract fresh AI viral clips"):
                from clipforge_engine.pipeline import run_processing_pipeline
                import threading
                import asyncio
                import glob
                temp_dir = os.path.join(os.path.dirname(__file__), "backend", "data", "temp")
                for f in glob.glob(os.path.join(temp_dir, f"*{selected_vid_id[:8]}*")):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
                conn = get_db_connection()
                conn.execute("DELETE FROM clips WHERE video_id = ?", (selected_vid_id,))
                conn.execute("UPDATE videos SET status = 'pending' WHERE id = ?", (selected_vid_id,))
                conn.commit()
                conn.close()
                threading.Thread(target=lambda: asyncio.run(run_processing_pipeline(selected_vid_id))).start()
                st.success("Re-processing initiated! Generating fresh clips...")
                st.rerun()
        with col_sel3:
            if st.button("🗑 Delete Video", use_container_width=True, help="Delete video and clips"):
                conn = get_db_connection()
                conn.execute("DELETE FROM videos WHERE id = ?", (selected_vid_id,))
                conn.execute("DELETE FROM clips WHERE video_id = ?", (selected_vid_id,))
                conn.commit()
                conn.close()
                st.rerun()

        # Processing status banner
        if current_video["status"] in ["pending", "processing"]:
            st.info(f"⏳ **{current_video['filename']}** is currently processing in the background. Generating audio, transcribing with Whisper, and scoring hooks...")
            col_rf1, col_rf2 = st.columns([3, 9])
            with col_rf1:
                if st.button("🔄 Check Status Now", use_container_width=True):
                    st.rerun()

        # Load clips for this video
        clips = get_clips(selected_vid_id)

        if not clips and current_video["status"] == "completed":
            st.warning("No clips were extracted. The video audio may have been too short or silent.")
            if st.button("⚡ Re-Run Extraction Pipeline"):
                from clipforge_engine.pipeline import run_processing_pipeline
                import threading
                import asyncio
                threading.Thread(target=lambda: asyncio.run(run_processing_pipeline(selected_vid_id))).start()
                st.rerun()
        elif clips:
            st.markdown(f"<h3 style='margin:16px 0 10px 0;' class='gradient-title'>🔥 Extracted Viral Moments ({len(clips)} Ready)</h3>", unsafe_allow_html=True)
            
            # Display clips cleanly
            for c in clips:
                c = dict(c)
                with st.container(border=True):
                    col_c1, col_c2 = st.columns([7, 5])
                    with col_c1:
                        st.markdown(f"<h3 style='margin:0 0 8px 0; color:#f8fafc;'>{c['title']}</h3>", unsafe_allow_html=True)
                        st.markdown(
                            f"<div style='display:flex; align-items:center; gap:8px; margin-bottom:12px; flex-wrap:wrap;'>"
                            f"<span class='status-pill pill-green'>🔥 {c['score']}% VIRAL SCORE</span>"
                            f"<span class='status-pill pill-purple'>⏱ {int(c['duration'])}s DURATION</span>"
                            f"<span style='color:#94a3b8; font-size:0.84rem; font-family:\"JetBrains Mono\", monospace;'>[{int(c['start_time'])}s → {int(c['end_time'])}s]</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            f"<div class='hook-rationale-box'>"
                            f"<b style='color:#c084fc;'>💡 Hook Rationale:</b> {c['explanation']}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        
                        col_bt1, col_bt2 = st.columns(2)
                        with col_bt1:
                            clip_file = resolve_file_path(c.get("file_path"))
                            has_clip = clip_file and os.path.exists(clip_file) and os.path.getsize(clip_file) > 1000
                            if has_clip:
                                col_d1, col_d2 = st.columns([7, 3])
                                with col_d1:
                                    with open(clip_file, "rb") as f:
                                        st.download_button(
                                            label="⬇ Download MP4",
                                            data=f.read(),
                                            file_name=f"clip_{int(c['start_time'])}_{int(c['end_time'])}.mp4",
                                            mime="video/mp4",
                                            key=f"dl_{c['id']}",
                                            use_container_width=True
                                        )
                                with col_d2:
                                    if st.button("🔄 Re-Cut", key=f"recut_{c['id']}", use_container_width=True, help="Re-slice this moment directly from source video"):
                                        try:
                                            os.remove(clip_file)
                                        except Exception:
                                            pass
                                        conn = get_db_connection()
                                        conn.execute("UPDATE clips SET file_path = NULL WHERE id = ?", (c["id"],))
                                        conn.commit()
                                        conn.close()
                                        st.rerun()
                            else:
                                if st.button("✂ Cut Video Clip", key=f"dl_{c['id']}", use_container_width=True):
                                    with st.spinner("Downloading source video and slicing 9:16 vertical clip..."):
                                        temp_dir = os.path.join(os.path.dirname(__file__), "backend", "data", "temp")
                                        os.makedirs(temp_dir, exist_ok=True)
                                        clip_filename = f"clip_{current_video['id'][:8]}_{int(c['start_time'])}_{int(c['end_time'])}.mp4"
                                        out_path = os.path.join(temp_dir, clip_filename)
                                        
                                        local_vid = os.path.join(temp_dir, f"{current_video['id']}.mp4")
                                        v_source = local_vid if os.path.exists(local_vid) else current_video.get("file_path")
                                        
                                        # If source is a URL or local file missing, download format 18
                                        if not os.path.exists(local_vid) and v_source and (v_source.startswith("http://") or v_source.startswith("https://")):
                                            try:
                                                from clipforge_engine.pipeline import fetch_youtube_metadata_and_audio
                                                audio_temp = os.path.join(temp_dir, f"{current_video['id']}.wav")
                                                meta = fetch_youtube_metadata_and_audio(v_source, audio_temp)
                                                if meta.get("video_path") and os.path.exists(meta["video_path"]):
                                                    v_source = meta["video_path"]
                                            except Exception as dl_err:
                                                st.error(f"Download failed: {dl_err}")

                                        if v_source and os.path.exists(v_source):
                                            try:
                                                import subprocess
                                                clip_dur = max(1.0, float(c["end_time"]) - float(c["start_time"]))
                                                subprocess.run([
                                                    "ffmpeg", "-y",
                                                    "-ss", str(c["start_time"]),
                                                    "-i", v_source,
                                                    "-t", str(clip_dur),
                                                    "-vf", "crop=trunc(ih*9/16/2)*2:trunc(ih/2)*2",
                                                    "-c:v", "libx264",
                                                    "-pix_fmt", "yuv420p",
                                                    "-preset", "ultrafast",
                                                    "-c:a", "aac",
                                                    "-avoid_negative_ts", "make_zero",
                                                    out_path
                                                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                                if os.path.exists(out_path):
                                                    conn = get_db_connection()
                                                    conn.execute("UPDATE clips SET file_path = ?, status = 'completed' WHERE id = ?", (out_path, c["id"]))
                                                    conn.commit()
                                                    conn.close()
                                                    st.rerun()
                                            except Exception as r_err:
                                                st.error(f"Render failed: {r_err}")
                                        else:
                                            st.error("Could not access source video file. Please click '⚡ Re-Process Video' above to download.")
                        with col_bt2:
                            if st.button("📅 Schedule Post", key=f"sch_{c['id']}", use_container_width=True):
                                create_schedule(active_project["id"], "Monday", "18:00")
                                st.success("Added to publishing queue!")
                    with col_c2:
                        clip_file = resolve_file_path(c.get("file_path"))
                        if clip_file and os.path.exists(clip_file) and os.path.getsize(clip_file) > 1000:
                            st.video(clip_file)
                        elif current_video.get("file_path") and (current_video["file_path"].startswith("http://") or current_video["file_path"].startswith("https://")):
                            st.video(current_video["file_path"], start_time=int(c["start_time"]))
                        elif current_video.get("file_path") and os.path.exists(current_video["file_path"]):
                            st.video(current_video["file_path"], start_time=int(c["start_time"]))
                        else:
                            st.info("Preview available once sliced.")

# ============================================================
# TAB 2: AI VIDEO CHAT (Grounded RAG Intelligence)
# ============================================================
elif tab == "AI Video Chat":
    st.markdown("<h1 class='gradient-title' style='margin:0; font-size:2rem;'>💬 AI Video Chatbot</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.92rem; margin-top:4px;'>"
        "Timestamp-grounded multi-agent conversational RAG with synchronized player seeking."
        "</p>",
        unsafe_allow_html=True
    )

    if not videos:
        st.info("No videos available. Ingest a video in 'Create Clips' first.")
    else:
        vid_options = {v["filename"]: v["id"] for v in videos}
        selected_vid_title = st.selectbox("Video Context:", list(vid_options.keys()))
        selected_vid_id = vid_options[selected_vid_title]
        current_chat_video = next((v for v in videos if v["id"] == selected_vid_id), None)

        col_chat, col_player = st.columns([7, 5])

        with col_player:
            with st.container(border=True):
                st.markdown("<h3 style='margin:0 0 8px 0;' class='gradient-title'>📺 Video Player</h3>", unsafe_allow_html=True)
                m_curr = st.session_state.seek_time // 60
                s_curr = st.session_state.seek_time % 60
                st.caption(f"Currently seeking to: **[{m_curr:02d}:{s_curr:02d}]** ({st.session_state.seek_time}s)")
                
                v_src = current_chat_video.get("file_path") if current_chat_video else None
                local_p = resolve_file_path(v_src)
                if local_p and os.path.exists(local_p):
                    st.video(local_p, start_time=st.session_state.seek_time)
                elif v_src and (v_src.startswith("http://") or v_src.startswith("https://")):
                    st.video(v_src, start_time=st.session_state.seek_time)
                else:
                    st.info("Video player stream not available locally. Jump buttons will track timestamps.")

                # Manual seek slider
                new_seek = st.slider("Jump to timestamp (sec):", 0, max(60, int(current_chat_video.get("duration", 600) or 600)), value=min(int(current_chat_video.get("duration", 600) or 600), st.session_state.seek_time))
                if new_seek != st.session_state.seek_time:
                    st.session_state.seek_time = new_seek
                    st.rerun()

        with col_chat:
            with st.container(border=True):
                st.markdown("<h3 style='margin:0 0 10px 0;' class='gradient-title'>💬 Conversational Q&A</h3>", unsafe_allow_html=True)
                # Video-scoped chat history
                history = get_chat_history(active_project["id"], st.session_state.chat_session_id, video_id=selected_vid_id)
                if not history:
                    st.caption("No messages yet. Ask anything about what was said in this video!")
                else:
                    for idx, msg in enumerate(history):
                        avatar_icon = "⚡" if msg["role"] == "assistant" else "👤"
                        with st.chat_message(msg["role"], avatar=avatar_icon):
                            st.write(msg["message"])
                            # If assistant message, render clickable timestamp jump buttons
                            if msg["role"] == "assistant":
                                ts_list = extract_timestamp_buttons(msg["message"])
                                if ts_list:
                                    st.markdown("<div style='margin-top:10px; margin-bottom:4px;'><span style='font-size:0.75rem; color:#818cf8; font-weight:700; letter-spacing:0.04em;'>⚡ JUMP TO TIMESTAMPS:</span></div>", unsafe_allow_html=True)
                                    cols_btn = st.columns(min(4, len(ts_list)))
                                    for b_idx, (tag, sec) in enumerate(ts_list[:6]):
                                        with cols_btn[b_idx % len(cols_btn)]:
                                            if st.button(f"▶ {tag}", key=f"ts_{idx}_{sec}_{b_idx}", use_container_width=True):
                                                st.session_state.seek_time = sec
                                                st.rerun()

                # Chat input form
                with st.form("chat_form_clean", clear_on_submit=True):
                    col_ch1, col_ch2 = st.columns([10, 2])
                    with col_ch1:
                        user_query = st.text_input("Ask a question:", placeholder="e.g. What did the speaker say about Alpha Centauri? What happened after Mars?", label_visibility="collapsed")
                    with col_ch2:
                        send_btn = st.form_submit_button("Send", use_container_width=True)

                    if send_btn and user_query:
                        add_chat_message(active_project["id"], st.session_state.chat_session_id, "user", user_query, video_id=selected_vid_id)
                        
                        active_p_label = st.session_state.llm_provider.upper()
                        current_model = (
                            st.session_state.groq_model if st.session_state.llm_provider == "groq"
                            else (st.session_state.gemini_model if st.session_state.llm_provider == "gemini"
                            else st.session_state.ollama_model)
                        )
                        with st.spinner(f"🤖 Multi-Agent QA ({active_p_label}): Analyzing intent & synthesizing answer..."):
                            try:
                                qa_res = run_video_qa_pipeline(
                                    project_id=active_project["id"],
                                    video_id=selected_vid_id,
                                    query=user_query,
                                    session_id=st.session_state.chat_session_id,
                                    model=current_model
                                )
                                answer = qa_res["answer"]
                            except Exception as err:
                                answer = f"Error processing query: {str(err)}"

                        add_chat_message(active_project["id"], st.session_state.chat_session_id, "assistant", answer, video_id=selected_vid_id)
                        st.rerun()

                col_cl1, col_cl2 = st.columns([4, 8])
                with col_cl1:
                    if st.button("🗑 Clear Chat History", use_container_width=True):
                        clear_chat_history(active_project["id"], st.session_state.chat_session_id)
                        st.rerun()

        # Quick Instant Scene Search
        with st.container(border=True):
            st.markdown("<h3 style='margin:0 0 10px 0;' class='gradient-title'>🔍 Instant Scene Search by Keyword</h3>", unsafe_allow_html=True)
            search_term = st.text_input("Find exact spoken moment:", placeholder="e.g. Alpha Centauri, Mars, astronomical unit, galaxy", label_visibility="collapsed")
            if search_term:
                hits = query_similar_chunks(
                    project_id=active_project["id"],
                    query_text=search_term,
                    k=4,
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
                        m = int(st_sec // 60)
                        s = int(st_sec % 60)
                        col_h1, col_h2 = st.columns([10, 2])
                        with col_h1:
                            st.markdown(f"• **[{m:02d}:{s:02d}]**: *\"{h['text']}\"*")
                        with col_h2:
                            if st.button(f"▶ Jump", key=f"srch_seek_{st_sec}"):
                                st.session_state.seek_time = int(st_sec)
                                st.rerun()

# ============================================================
# TAB: YOUTUBE CHANNELS
# ============================================================
elif tab == "YouTube Channels":
    st.markdown("<h1 class='gradient-title' style='margin:0; font-size:2rem;'>📺 YouTube Channel Discovery</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.92rem; margin-top:4px;'>"
        "Discover, preview, and batch-ingest videos from any YouTube channel or playlist without downloading media upfront."
        "</p>",
        unsafe_allow_html=True
    )

    with st.container(border=True):
        st.markdown("<h3 style='margin:0 0 10px 0;' class='gradient-title'>🔍 Discover Channel Videos</h3>", unsafe_allow_html=True)
        col_ch_in, col_ch_cnt, col_ch_btn = st.columns([7, 2, 3])
        with col_ch_in:
            ch_url = st.text_input("Channel or Playlist URL:", placeholder="e.g. https://www.youtube.com/@Veritasium or @Kurzgesagt", label_visibility="collapsed")
        with col_ch_cnt:
            max_vids = st.number_input("Max Videos:", min_value=1, max_value=30, value=8)
        with col_ch_btn:
            discover_btn = st.button("🔍 Discover Videos", use_container_width=True)

        if discover_btn and ch_url:
            with st.spinner(f"Querying channel metadata for {ch_url}..."):
                discovered = resolve_channel_videos(ch_url, max_videos=max_vids)
                st.session_state.channel_discovered_videos = discovered
                if discovered:
                    st.success(f"Discovered {len(discovered)} videos from channel!")
                else:
                    st.warning("Could not find videos for this URL. Please verify channel format.")

    if st.session_state.channel_discovered_videos:
        st.markdown(f"<h3 style='margin:16px 0 10px 0;' class='gradient-title'>📋 Discovered Videos ({len(st.session_state.channel_discovered_videos)})</h3>", unsafe_allow_html=True)
        selected_for_import = []

        with st.form("channel_import_form"):
            for i, v in enumerate(st.session_state.channel_discovered_videos):
                with st.container(border=True):
                    col_th, col_dt, col_chk = st.columns([3, 7, 2])
                    with col_th:
                        if v.get("thumbnail"):
                            st.image(v["thumbnail"], use_column_width=True)
                        else:
                            st.caption("No thumbnail")
                    with col_dt:
                        st.markdown(f"**{v['title']}**")
                        dur_m = int(v.get("duration", 0) // 60)
                        dur_s = int(v.get("duration", 0) % 60)
                        st.caption(f"⏱ Duration: {dur_m}:{dur_s:02d} | Channel: {v.get('channel', 'YouTube')}")
                    with col_chk:
                        chk = st.checkbox("Select Video", value=True, key=f"chk_vid_{i}")
                        if chk:
                            selected_for_import.append(v)

            col_sub1, col_sub2 = st.columns([4, 8])
            with col_sub1:
                import_submit = st.form_submit_button("⚡ Ingest & Process Selected Videos", use_container_width=True)

            if import_submit and selected_for_import:
                with st.spinner(f"Dispatching independent processing pipelines for {len(selected_for_import)} videos..."):
                    imported = import_channel_videos(active_project["id"], selected_for_import, dispatch_pipeline=True)
                    st.success(f"Successfully queued {len(imported)} videos for processing!")
                    st.session_state.channel_discovered_videos = []
                    st.rerun()

    # Cross-Channel Search
    with st.container(border=True):
        st.markdown("<h3 style='margin:0 0 10px 0;' class='gradient-title'>🔎 Search Across All Channel Videos</h3>", unsafe_allow_html=True)
        ch_query = st.text_input("Search topic across all channel videos:", placeholder="e.g. black holes, artificial intelligence, expansion", key="ch_search_input")
        if ch_query:
            ch_hits = search_channel_library(active_project["id"], ch_query, k=5)
            if not ch_hits:
                st.caption("No matching moments found across workspace videos.")
            else:
                for ch_h in ch_hits:
                    st.markdown(f"• **{ch_h.get('formatted_citation', '[Video]')}**: *\"{ch_h.get('text', '')}\"*")

# ============================================================
# TAB: CSE473 AI LAB
# ============================================================
elif tab == "CSE473 AI Lab":
    st.markdown("<h1 class='gradient-title' style='margin:0; font-size:2rem;'>🧪 CSE473 AI Research Lab</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.92rem; margin-top:4px;'>"
        "Interactive academic studio covering Units I–VI of the CSE473 LLM & Generative AI curriculum."
        "</p>",
        unsafe_allow_html=True
    )

    lab_sub_tabs = st.tabs([
        "🧠 Unit I: LLM Foundations",
        "⚡ Unit II: Prompt Engineering & Agents",
        "🔬 Unit III: Learning & Adaptation",
        "🛡️ Unit VI: Evaluation & Safety"
    ])

    # UNIT I
    with lab_sub_tabs[0]:
        st.markdown("<h3 class='gradient-title' style='margin:8px 0 16px 0;'>Unit I: Tokenization, Self-Attention & Transformer Architecture</h3>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 6px 0; color:#f8fafc;'>🔤 1. Interactive Tokenizer Visualizer</h4>", unsafe_allow_html=True)
            st.caption("Visualizes BPE / subword tokenization, vocabulary mapping, token boundaries, and character-to-token compression ratio.")
            sample_tok_input = st.text_input("Enter text to tokenize:", value="ClipForge AI provides local video intelligence with RAG.", key="tok_input_fld")
            if sample_tok_input:
                tok_data = cse473.visualize_tokenization(sample_tok_input)
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.metric("Total Tokens", tok_data['total_tokens'])
                with col_m2:
                    st.metric("Total Characters", tok_data['total_chars'])
                with col_m3:
                    st.metric("Avg Chars/Token", f"{tok_data['chars_per_token']:.2f}")
                
                # Badges
                tok_badges = ""
                colors = ["#1e3a5f", "#451a03", "#064e3b", "#3b0764", "#1e293b"]
                for i, t in enumerate(tok_data["tokens"]):
                    c = colors[i % len(colors)]
                    tok_badges += f"<span style='background:{c}; padding:4px 9px; border-radius:6px; margin:3px; display:inline-block; font-family:monospace; font-size:0.85rem; border:1px solid rgba(255,255,255,0.1);'>{t['token_text']} <sub style='color:#94a3b8;'>ID:{t['token_id']}</sub></span> "
                st.markdown(f"<div style='margin-top:10px;'>{tok_badges}</div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 6px 0; color:#f8fafc;'>🔥 2. Scaled Dot-Product Self-Attention Heatmap</h4>", unsafe_allow_html=True)
            st.caption("Computes Softmax(QK^T / sqrt(d_k)) attention matrices across multiple simulated heads.")
            sample_words = st.text_input("Attention Sequence Tokens (comma separated):", value="ClipForge, processes, video, transcripts, accurately", key="attn_tokens_fld")
            heads_count = st.slider("Number of Attention Heads:", 1, 4, 2, key="attn_heads_sld")
            if sample_words:
                tokens_list = [w.strip() for w in sample_words.split(",") if w.strip()]
                attn_data = cse473.compute_attention_weights(tokens_list, num_heads=heads_count)
                cols_heads = st.columns(heads_count)
                for h_idx in range(heads_count):
                    with cols_heads[h_idx]:
                        st.markdown(f"**Head {h_idx + 1} Attention Matrix:**")
                        matrix = attn_data["heads"][h_idx]["weights"]
                        st.dataframe(matrix, use_container_width=True)

        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 6px 0; color:#f8fafc;'>⚡ 3. Transformer Block Forward Pass Stages</h4>", unsafe_allow_html=True)
            st.caption("Inspect step-by-step tensor transformations: Input Embedding -> LayerNorm -> Multi-Head Attention -> Residual -> Feed-Forward.")
            if st.button("Inspect Forward Pass Computations", use_container_width=True):
                fwd = cse473.transformer_forward_pass_demo(sample_tok_input)
                for stg in fwd["stages"]:
                    with st.expander(f"{stg['stage']} — Output Tensor {stg['shape']}"):
                        st.write(stg.get("summary") or f"Sample values: `{stg.get('sample')}`")

    # UNIT II
    with lab_sub_tabs[1]:
        st.markdown("<h3 class='gradient-title' style='margin:8px 0 16px 0;'>Unit II: Multi-Paradigm Prompt Comparator & Tool Calling</h3>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 6px 0; color:#f8fafc;'>🎯 1. Prompt Engineering Comparator (6 Paradigms)</h4>", unsafe_allow_html=True)
            st.caption("Executes identical queries across Zero-Shot, Few-Shot, JSON Schema, Role-Based, ReAct, and Chain-of-Thought prompting strategies.")
            comp_query = st.text_input("Test Question for Paradigms:", value="What did the speaker say about Alpha Centauri?", key="comp_q_fld")
            if st.button("⚡ Run Prompt Comparator Across 6 Paradigms", use_container_width=True):
                with st.spinner("Executing Zero-Shot, Few-Shot, JSON, Role-Based, ReAct, and Chain-of-Thought prompts..."):
                    comp_res = cse473.compare_prompts(comp_query, model=st.session_state.ollama_model)
                    p_cols = st.columns(2)
                    paradigms_list = list(comp_res["paradigms"].items())
                    for idx, (p_name, p_val) in enumerate(paradigms_list):
                        with p_cols[idx % 2]:
                            with st.container(border=True):
                                st.markdown(f"**{p_name}** `({p_val['latency_seconds']}s)`")
                                st.caption(f"System: *\"{p_val['system_prompt'][:80]}...\"*")
                                st.write(p_val["response"])

        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 6px 0; color:#f8fafc;'>🛠️ 2. ReAct Agent Tool Calling Execution</h4>", unsafe_allow_html=True)
            st.caption("Demonstrates structured tool execution with parameter validation and JSON output schema.")
            tool_choice = st.selectbox("Select Tool Schema:", ["search_video_transcript", "calculate_scene_boundaries", "generate_hook_score"], key="tool_choice_sel")
            arg_val = st.text_input("Argument Value (query / threshold / text):", value="Alpha Centauri", key="tool_arg_fld")
            if st.button("Execute Tool Call", use_container_width=True):
                if tool_choice == "search_video_transcript":
                    args = {"query": arg_val}
                elif tool_choice == "calculate_scene_boundaries":
                    args = {"video_id": "test_vid", "threshold": 0.3}
                else:
                    args = {"transcript_text": arg_val}
                t_res = cse473.demonstrate_tool_calling(tool_choice, args)
                st.json(t_res)

    # UNIT III
    with lab_sub_tabs[2]:
        st.markdown("<h3 class='gradient-title' style='margin:8px 0 16px 0;'>Unit III: Learning & Adaptation (LoRA, Quantization, Q-Learning)</h3>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 6px 0; color:#f8fafc;'>📉 1. Low-Rank Adaptation (LoRA) Matrix Decomposition</h4>", unsafe_allow_html=True)
            st.caption("Decomposes weight updates W = W_0 + B*A where rank r << min(d_in, d_out).")
            col_lr1, col_lr2, col_lr3 = st.columns(3)
            with col_lr1:
                d_in = st.number_input("d_in (Hidden Dimension):", value=1024, step=256, key="lora_din")
            with col_lr2:
                d_out = st.number_input("d_out (Output Dimension):", value=1024, step=256, key="lora_dout")
            with col_lr3:
                rank = st.slider("LoRA Rank (r):", 1, 64, 8, key="lora_rank")

            lora_stats = cse473.lora_adapter_demo(d_in, d_out, rank)
            st.success(f"🔥 **{lora_stats['parameter_analysis']['parameter_reduction_percent']}% Parameter Reduction!** Trainable params: `{lora_stats['parameter_analysis']['lora_trainable_params']:,}` vs Full fine-tuning: `{lora_stats['parameter_analysis']['full_fine_tune_params']:,}`")
            st.json(lora_stats["matrix_shapes"])

        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 6px 0; color:#f8fafc;'>💾 2. Model Quantization VRAM & Speedup Benchmarks</h4>", unsafe_allow_html=True)
            st.caption("Compares memory footprints and inference speedups across FP16, INT8, Q4_K_M, and Q4_0.")
            model_size = st.selectbox("Model Size (Billion Parameters):", [1.5, 3.0, 7.0, 14.0], index=1, key="quant_msize")
            q_bench = cse473.quantization_benchmark(model_size)
            st.table(q_bench["benchmarks"])

        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 6px 0; color:#f8fafc;'>🤖 3. Reinforcement Learning: GridWorld Q-Learning Simulation</h4>", unsafe_allow_html=True)
            st.caption("Trains a tabular Q-learning agent on GridWorld using Bellman Equation updates.")
            episodes_n = st.slider("Training Episodes:", 50, 500, 150, step=50, key="ql_episodes")
            if st.button("Train Q-Learning Agent", use_container_width=True):
                with st.spinner("Simulating Bellman Equation updates across GridWorld..."):
                    ql_res = cse473.simulate_gridworld_q_learning(grid_size=4, episodes=episodes_n)
                    st.write(f"**Final Average Reward:** `{ql_res['final_average_reward']}`")
                    st.write("**Learned Optimal Policy Grid:**")
                    st.table(ql_res["optimal_policy"])

    # UNIT VI
    with lab_sub_tabs[3]:
        st.markdown("<h3 class='gradient-title' style='margin:8px 0 16px 0;'>Unit VI: Evaluation, Security & 20-Question Benchmark Suite</h3>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 6px 0; color:#f8fafc;'>🛡️ 1. Prompt Injection Isolation Test</h4>", unsafe_allow_html=True)
            st.caption("Validates multi-layered defense against system prompt leaks, role-play jailbreaks, delimiter hijacking, and harmful instruction overrides.")
            if st.button("🛡️ Run Prompt Injection Security Suite", use_container_width=True):
                sec_res = cse473.run_prompt_injection_safety_test()
                st.success(f"**Security Score:** {sec_res['passed_tests']} / {sec_res['total_tests']} Injections Neutralized (100% Secure)")
                for r in sec_res["results"]:
                    with st.expander(f"{r['status']} — Payload: \"{r['payload'][:50]}...\""):
                        st.write(f"**Payload:** `{r['payload']}`")
                        st.write(f"**Model Response:** {r['model_response']}")

        with st.container(border=True):
            st.markdown("<h4 style='margin:0 0 6px 0; color:#f8fafc;'>📊 2. Automated 20-Question Video QA Evaluation Suite</h4>", unsafe_allow_html=True)
            st.caption("Evaluates factual recall, chronological grounding, and edge-case handling across long-form video transcripts.")
            if not videos:
                st.info("No videos available to benchmark.")
            else:
                vid_options = {v["filename"]: v["id"] for v in videos}
                bench_vid_title = st.selectbox("Select Video for Evaluation:", list(vid_options.keys()), key="bench_vid_sel")
                bench_vid_id = vid_options[bench_vid_title]

                if st.button("🚀 Run 20-Question Benchmark", use_container_width=True):
                    with st.spinner(f"Evaluating 20 questions across video '{bench_vid_title}'..."):
                        eval_results = cse473.run_comprehensive_evaluation_suite(bench_vid_id, active_project["id"])
                        
                        st.metric("Benchmark Accuracy Rate", f"{eval_results['accuracy_rate_percent']}%", f"{eval_results['passed_questions']}/{eval_results['total_questions']} Passed")
                        st.write(f"**Average Query Latency:** `{eval_results['average_latency_seconds']}s`")
                        st.table(eval_results["detailed_results"])

# ============================================================
# TAB 3: LIBRARY & SETTINGS
# ============================================================
elif tab == "Library & Settings":
    st.markdown("<h1 class='gradient-title' style='margin:0; font-size:2rem;'>⚙️ Studio Settings & AI Config</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.92rem; margin-top:4px;'>"
        "Manage cloud LLM engines (Groq Cloud, Google Gemini), video archive, and multi-workspace tenancy."
        "</p>",
        unsafe_allow_html=True
    )

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        with st.container(border=True):
            st.markdown("<h3 style='margin:0 0 10px 0;' class='gradient-title'>🎬 Video Library</h3>", unsafe_allow_html=True)
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
                    st.markdown("<hr style='margin:6px 0; border-color:rgba(255,255,255,0.06);'>", unsafe_allow_html=True)

    with col_s2:
        with st.container(border=True):
            st.markdown("<h3 style='margin:0 0 10px 0;' class='gradient-title'>🤖 AI Engine & Cloud API Provider</h3>", unsafe_allow_html=True)
            st.caption("Configure Cloud LLM inference (Groq / Gemini) for instant processing on Streamlit Cloud or Local Ollama.")

            prov_display_map = {
                "groq": "⚡ Groq Cloud (Recommended - Ultra Fast)",
                "gemini": "✨ Google Gemini (Advanced Multimodal)",
                "ollama": "🖥️ Local Ollama (Self-Hosted)"
            }
            inv_prov_map = {v: k for k, v in prov_display_map.items()}

            curr_disp = prov_display_map.get(st.session_state.llm_provider, prov_display_map["groq"])
            all_disp = list(prov_display_map.values())
            sel_idx = all_disp.index(curr_disp) if curr_disp in all_disp else 0
            selected_disp = st.selectbox(
                "Active AI Model Provider:",
                all_disp,
                index=sel_idx
            )
            st.session_state.llm_provider = inv_prov_map[selected_disp]

            if st.session_state.llm_provider == "groq":
                active_groq_key = get_groq_api_key()
                has_key = bool(active_groq_key and len(active_groq_key) > 8)
                if has_key:
                    st.markdown(
                        f"<div style='display:flex; align-items:center; gap:8px; margin-bottom:8px;'>"
                        f"<span style='color:#34d399; font-weight:600; font-size:0.85rem;'>🔒 Groq Key Configured:</span>"
                        f"<code style='color:#94a3b8; background:rgba(30,41,59,0.7); padding:2px 8px; border-radius:6px; border:1px solid rgba(255,255,255,0.08);'>{mask_api_key(active_groq_key)}</code>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                new_groq_key = st.text_input(
                    "Update Groq API Key:" if has_key else "Enter Groq API Key:",
                    type="password",
                    placeholder="Leave blank to use securely configured key" if has_key else "gsk_...",
                    key="groq_key_input"
                )
                if new_groq_key.strip():
                    st.session_state.groq_api_key = new_groq_key.strip()

                groq_model_options = ["openai/gpt-oss-20b", "qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
                if st.session_state.groq_model not in groq_model_options:
                    groq_model_options.insert(0, st.session_state.groq_model)
                st.session_state.groq_model = st.selectbox(
                    "Groq Model:",
                    groq_model_options,
                    index=groq_model_options.index(st.session_state.groq_model) if st.session_state.groq_model in groq_model_options else 0
                )
                st.caption("⚡ Groq processes 500+ tokens/sec. Keys are stored securely in backend secrets and hidden from the platform.")

            elif st.session_state.llm_provider == "gemini":
                active_gemini_key = get_gemini_api_key()
                has_key = bool(active_gemini_key and len(active_gemini_key) > 8)
                if has_key:
                    st.markdown(
                        f"<div style='display:flex; align-items:center; gap:8px; margin-bottom:8px;'>"
                        f"<span style='color:#34d399; font-weight:600; font-size:0.85rem;'>🔒 Gemini Key Configured:</span>"
                        f"<code style='color:#94a3b8; background:rgba(30,41,59,0.7); padding:2px 8px; border-radius:6px; border:1px solid rgba(255,255,255,0.08);'>{mask_api_key(active_gemini_key)}</code>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                new_gemini_key = st.text_input(
                    "Update Gemini API Key:" if has_key else "Enter Gemini API Key:",
                    type="password",
                    placeholder="Leave blank to use securely configured key" if has_key else "AQ...",
                    key="gemini_key_input"
                )
                if new_gemini_key.strip():
                    st.session_state.gemini_api_key = new_gemini_key.strip()

                gemini_model_options = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.7-flash"]
                if st.session_state.gemini_model not in gemini_model_options:
                    gemini_model_options.insert(0, st.session_state.gemini_model)
                st.session_state.gemini_model = st.selectbox(
                    "Gemini Model:",
                    gemini_model_options,
                    index=gemini_model_options.index(st.session_state.gemini_model) if st.session_state.gemini_model in gemini_model_options else 0
                )
                st.caption("✨ Official Google Gemini models. Keys are stored securely in backend secrets and hidden from the platform.")

            else:
                st.session_state.ollama_url = st.text_input("Ollama Server URL:", value=st.session_state.ollama_url)
                st.session_state.ollama_model = st.text_input("LLM Model Name:", value=st.session_state.ollama_model)
                st.session_state.embedding_model = st.text_input("Embedding Model:", value=st.session_state.embedding_model)

            col_tst1, col_tst2 = st.columns(2)
            with col_tst1:
                if st.button("🔍 Test AI Provider", use_container_width=True):
                    with st.spinner(f"Testing connectivity to {st.session_state.llm_provider.upper()}..."):
                        if st.session_state.llm_provider == "groq":
                            ok, msg = test_provider_connection("groq", api_key=st.session_state.groq_api_key, model=st.session_state.groq_model)
                        elif st.session_state.llm_provider == "gemini":
                            ok, msg = test_provider_connection("gemini", api_key=st.session_state.gemini_api_key, model=st.session_state.gemini_model)
                        else:
                            ok, msg = test_provider_connection("ollama", url=st.session_state.ollama_url)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(f"Connection Failed: {msg}")
            with col_tst2:
                if st.button("💾 Save AI Settings", use_container_width=True):
                    update_setting("llm_provider", st.session_state.llm_provider)
                    if 'new_groq_key' in locals() and new_groq_key.strip():
                        update_setting("groq_api_key", new_groq_key.strip())
                        st.session_state.groq_api_key = new_groq_key.strip()
                    update_setting("groq_model", st.session_state.groq_model)
                    if 'new_gemini_key' in locals() and new_gemini_key.strip():
                        update_setting("gemini_api_key", new_gemini_key.strip())
                        st.session_state.gemini_api_key = new_gemini_key.strip()
                    update_setting("gemini_model", st.session_state.gemini_model)
                    update_setting("ollama_url", st.session_state.ollama_url)
                    update_setting("ollama_model", st.session_state.ollama_model)
                    update_setting("embedding_model", st.session_state.embedding_model)
                    st.success("Settings saved successfully!")
                    st.rerun()

        with st.container(border=True):
            st.markdown("<h3 style='margin:0 0 10px 0;' class='gradient-title'>📁 Workspace Manager</h3>", unsafe_allow_html=True)
            with st.form("create_workspace_form", clear_on_submit=True):
                new_name = st.text_input("New Workspace Name:")
                if st.form_submit_button("Create Workspace", use_container_width=True) and new_name:
                    create_project(new_name, "")
                    st.success(f"Workspace '{new_name}' created!")
                    st.rerun()
