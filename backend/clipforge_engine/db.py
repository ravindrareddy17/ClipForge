import sqlite3
import os
import json
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "clipforge.db")

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Projects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL
    )
    """)
    
    # Videos table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        duration REAL,
        width INTEGER,
        height INTEGER,
        fps REAL,
        status TEXT NOT NULL,
        transcript TEXT,
        scenes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)
    
    # Clips table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clips (
        id TEXT PRIMARY KEY,
        video_id TEXT NOT NULL,
        title TEXT NOT NULL,
        start_time REAL NOT NULL,
        end_time REAL NOT NULL,
        duration REAL NOT NULL,
        score INTEGER,
        explanation TEXT,
        status TEXT NOT NULL,
        file_path TEXT,
        subtitles TEXT,
        subtitle_style TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (video_id) REFERENCES videos(id)
    )
    """)
    
    # Channels table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        platform TEXT NOT NULL,
        name TEXT NOT NULL,
        auth_data TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # Source channels table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS source_channels (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        handle TEXT NOT NULL,
        name TEXT NOT NULL,
        avatar TEXT,
        subscribers INTEGER,
        video_count INTEGER,
        latest_upload TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # Scheduling timeslots table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        day_of_week TEXT NOT NULL,
        time_of_day TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # Activity feed logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_log (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        details TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # Notification center table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        project_id TEXT,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # Channel Analytics daily tracking table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channel_analytics (
        project_id TEXT PRIMARY KEY,
        views INTEGER DEFAULT 0,
        subscribers INTEGER DEFAULT 0,
        watch_time REAL DEFAULT 0.0,
        ctr REAL DEFAULT 0.0,
        retention REAL DEFAULT 0.0,
        chart_data TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # Editing profiles presets
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS editing_profiles (
        project_id TEXT PRIMARY KEY,
        profile_name TEXT NOT NULL,
        enhancements_json TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)
    
    # Settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    
    # Default settings
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (
        "brand_presets",
        json.dumps({
            "logo": "",
            "watermark": "",
            "outro": "",
            "brand_colors": ["#FF0055", "#00F0FF", "#000000"],
            "font_family": "Montserrat"
        })
    ))
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (
        "export_settings",
        json.dumps({
            "resolution": "1080x1920",
            "fps": 30,
            "bitrate": "5M",
            "codec": "libx264",
            "quality": "high"
        })
    ))

    conn.commit()
    conn.close()

# CRUD helpers
def create_project(name, description=""):
    pid = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO projects (id, name, description, created_at) VALUES (?, ?, ?, ?)",
        (pid, name, description, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return pid

def get_projects():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_project(pid):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_video(project_id, filename, file_path, duration=0.0, width=0, height=0, fps=0.0):
    vid = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO videos (id, project_id, filename, file_path, duration, width, height, fps, status, created_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (vid, project_id, filename, file_path, duration, width, height, fps, "pending", datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return vid

def update_video_status(video_id, status, transcript=None, scenes=None):
    conn = get_db_connection()
    if transcript is not None:
        tx_str = json.dumps(transcript) if isinstance(transcript, (dict, list)) else transcript
        conn.execute("UPDATE videos SET status = ?, transcript = ? WHERE id = ?", (status, tx_str, video_id))
    elif scenes is not None:
        sc_str = json.dumps(scenes) if isinstance(scenes, (dict, list)) else scenes
        conn.execute("UPDATE videos SET status = ?, scenes = ? WHERE id = ?", (status, sc_str, video_id))
    else:
        conn.execute("UPDATE videos SET status = ? WHERE id = ?", (status, video_id))
    conn.commit()
    conn.close()

def get_videos(project_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM videos WHERE project_id = ? ORDER BY created_at DESC", (project_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_video(video_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_clip(video_id, title, start_time, end_time, duration, score=0, explanation="", subtitles=None, subtitle_style=None):
    cid = str(uuid.uuid4())
    conn = get_db_connection()
    sub_str = json.dumps(subtitles) if subtitles else None
    sty_str = json.dumps(subtitle_style) if subtitle_style else None
    conn.execute(
        """INSERT INTO clips (id, video_id, title, start_time, end_time, duration, score, explanation, status, subtitles, subtitle_style, created_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (cid, video_id, title, start_time, end_time, duration, score, explanation, "rendering", sub_str, sty_str, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return cid

def update_clip(clip_id, status=None, file_path=None, subtitles=None, subtitle_style=None):
    conn = get_db_connection()
    updates = []
    params = []
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if file_path is not None:
        updates.append("file_path = ?")
        params.append(file_path)
    if subtitles is not None:
        updates.append("subtitles = ?")
        params.append(json.dumps(subtitles) if isinstance(subtitles, (dict, list)) else subtitles)
    if subtitle_style is not None:
        updates.append("subtitle_style = ?")
        params.append(json.dumps(subtitle_style) if isinstance(subtitle_style, (dict, list)) else subtitle_style)
        
    if updates:
        params.append(clip_id)
        conn.execute(f"UPDATE clips SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()

def get_clips(video_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM clips WHERE video_id = ? ORDER BY score DESC", (video_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_clips():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM clips ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_clip(clip_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM clips WHERE id = ?", (clip_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_settings():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return {r["key"]: json.loads(r["value"]) for r in rows}

def update_setting(key, value):
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(value)))
    conn.commit()
    conn.close()

# Source Channels helpers
def get_source_channels(project_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM source_channels WHERE project_id = ? ORDER BY created_at DESC", (project_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_source_channel(project_id, handle, name, avatar="", subscribers=0, video_count=0, latest_upload="", status="active"):
    sid = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO source_channels (id, project_id, handle, name, avatar, subscribers, video_count, latest_upload, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sid, project_id, handle, name, avatar, subscribers, video_count, latest_upload, status, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return sid

def delete_source_channel(sid):
    conn = get_db_connection()
    conn.execute("DELETE FROM source_channels WHERE id = ?", (sid,))
    conn.commit()
    conn.close()

# Schedules helpers
def get_schedules(project_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM schedules WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_schedule(project_id, day_of_week, time_of_day, is_active=1):
    sid = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO schedules (id, project_id, day_of_week, time_of_day, is_active) VALUES (?, ?, ?, ?, ?)",
        (sid, project_id, day_of_week, time_of_day, is_active)
    )
    conn.commit()
    conn.close()
    return sid

def delete_schedule(sid):
    conn = get_db_connection()
    conn.execute("DELETE FROM schedules WHERE id = ?", (sid,))
    conn.commit()
    conn.close()

def delete_schedules_by_project(project_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM schedules WHERE project_id = ?", (project_id,))
    conn.commit()
    conn.close()

# Activity Log helpers
def get_activity_logs(project_id, limit=50):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM activity_log WHERE project_id = ? ORDER BY created_at DESC LIMIT ?", (project_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_activity_log(project_id, action_type, details=""):
    aid = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO activity_log (id, project_id, action_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
        (aid, project_id, action_type, details, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return aid

# Notifications helpers
def get_notifications(project_id=None, limit=20):
    conn = get_db_connection()
    if project_id:
        rows = conn.execute("SELECT * FROM notifications WHERE project_id = ? ORDER BY created_at DESC LIMIT ?", (project_id, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_notification(project_id, type_str, title, message):
    nid = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO notifications (id, project_id, type, title, message, is_read, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
        (nid, project_id, type_str, title, message, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return nid

def mark_notifications_read(project_id=None):
    conn = get_db_connection()
    if project_id:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE project_id = ?", (project_id,))
    else:
        conn.execute("UPDATE notifications SET is_read = 1")
    conn.commit()
    conn.close()

# Analytics helpers
def get_channel_analytics(project_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM channel_analytics WHERE project_id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_channel_analytics(project_id, views, subscribers, watch_time, ctr, retention, chart_data=None):
    conn = get_db_connection()
    cd_str = json.dumps(chart_data) if chart_data else None
    conn.execute(
        """INSERT OR REPLACE INTO channel_analytics (project_id, views, subscribers, watch_time, ctr, retention, chart_data)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (project_id, views, subscribers, watch_time, ctr, retention, cd_str)
    )
    conn.commit()
    conn.close()

# Editing Profile helpers
def get_editing_profile(project_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM editing_profiles WHERE project_id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_editing_profile(project_id, profile_name, enhancements):
    conn = get_db_connection()
    enh_str = json.dumps(enhancements) if enhancements else None
    conn.execute(
        "INSERT OR REPLACE INTO editing_profiles (project_id, profile_name, enhancements_json) VALUES (?, ?, ?)",
        (project_id, profile_name, enh_str)
    )
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()
