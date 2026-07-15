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

    # 1. transcript_chunks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transcript_chunks (
        id TEXT PRIMARY KEY,
        video_id TEXT NOT NULL,
        project_id TEXT NOT NULL,
        start_time REAL NOT NULL,
        end_time REAL NOT NULL,
        text TEXT NOT NULL,
        speaker TEXT,
        keywords TEXT,
        metadata_json TEXT,
        FOREIGN KEY (video_id) REFERENCES videos(id),
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # 2. embeddings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id TEXT PRIMARY KEY,
        chunk_id TEXT NOT NULL,
        embedding_json TEXT NOT NULL,
        FOREIGN KEY (chunk_id) REFERENCES transcript_chunks(id)
    )
    """)

    # 3. topics table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id TEXT PRIMARY KEY,
        video_id TEXT NOT NULL,
        name TEXT NOT NULL,
        start_time REAL NOT NULL,
        end_time REAL NOT NULL,
        summary TEXT,
        FOREIGN KEY (video_id) REFERENCES videos(id)
    )
    """)

    # 4. keywords table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keywords (
        id TEXT PRIMARY KEY,
        video_id TEXT NOT NULL,
        word TEXT NOT NULL,
        category TEXT NOT NULL,
        count INTEGER DEFAULT 1,
        FOREIGN KEY (video_id) REFERENCES videos(id)
    )
    """)

    # 5. knowledge_graph table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_graph (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        source TEXT NOT NULL,
        target TEXT NOT NULL,
        relationship TEXT NOT NULL,
        weight REAL DEFAULT 1.0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # 6. chat_history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # 7. summaries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS summaries (
        id TEXT PRIMARY KEY,
        video_id TEXT NOT NULL,
        executive_summary TEXT,
        key_topics TEXT,
        important_quotes TEXT,
        timeline TEXT,
        action_items TEXT,
        main_ideas TEXT,
        FOREIGN KEY (video_id) REFERENCES videos(id)
    )
    """)

    # 8. retrieval_logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS retrieval_logs (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        query TEXT NOT NULL,
        retrieved_chunks_json TEXT NOT NULL,
        generated_response TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # 9. channel_monitors table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channel_monitors (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        channel_id TEXT NOT NULL,
        sync_interval TEXT NOT NULL,
        auto_sync INTEGER DEFAULT 1,
        last_check TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # 10. destination_channels table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS destination_channels (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        platform TEXT NOT NULL,
        name TEXT NOT NULL,
        caption_template TEXT,
        hashtags TEXT,
        schedule_time TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    """)

    # 11. clip_edits table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clip_edits (
        id TEXT PRIMARY KEY,
        clip_id TEXT NOT NULL,
        trim_start REAL,
        trim_end REAL,
        crop_x INTEGER,
        crop_y INTEGER,
        crop_w INTEGER,
        crop_h INTEGER,
        face_tracking INTEGER DEFAULT 1,
        font_family TEXT,
        font_color TEXT,
        font_size INTEGER,
        bg_music_volume REAL DEFAULT 0.5,
        created_at TEXT NOT NULL,
        FOREIGN KEY (clip_id) REFERENCES clips(id)
    )
    """)

    # 12. pipeline_stages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pipeline_stages (
        id TEXT PRIMARY KEY,
        video_id TEXT NOT NULL,
        stage_name TEXT NOT NULL,
        status TEXT NOT NULL,
        elapsed_time REAL DEFAULT 0.0,
        log_text TEXT,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (video_id) REFERENCES videos(id)
    )
    """)

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

# RAG Knowledge Engine helpers
def create_transcript_chunk(video_id, project_id, start_time, end_time, text, speaker=None, keywords=None, metadata_json=None):
    cid = str(uuid.uuid4())
    conn = get_db_connection()
    meta_str = json.dumps(metadata_json) if metadata_json else None
    conn.execute(
        """INSERT INTO transcript_chunks (id, video_id, project_id, start_time, end_time, text, speaker, keywords, metadata_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (cid, video_id, project_id, start_time, end_time, text, speaker, keywords, meta_str)
    )
    conn.commit()
    conn.close()
    return cid

def get_transcript_chunks(video_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM transcript_chunks WHERE video_id = ? ORDER BY start_time ASC", (video_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_chunks_for_project(project_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM transcript_chunks WHERE project_id = ? ORDER BY start_time ASC", (project_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_embedding(chunk_id, embedding):
    eid = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT OR REPLACE INTO embeddings (id, chunk_id, embedding_json) VALUES (?, ?, ?)",
        (eid, chunk_id, json.dumps(embedding))
    )
    conn.commit()
    conn.close()
    return eid

def get_embedding(chunk_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM embeddings WHERE chunk_id = ?", (chunk_id,)).fetchone()
    conn.close()
    return json.loads(row["embedding_json"]) if row else None

def create_topic(video_id, name, start_time, end_time, summary=""):
    tid = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO topics (id, video_id, name, start_time, end_time, summary) VALUES (?, ?, ?, ?, ?, ?)",
        (tid, video_id, name, start_time, end_time, summary)
    )
    conn.commit()
    conn.close()
    return tid

def get_topics(video_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM topics WHERE video_id = ? ORDER BY start_time ASC", (video_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_topics_for_project(project_id):
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT topics.* FROM topics 
           JOIN videos ON topics.video_id = videos.id 
           WHERE videos.project_id = ? ORDER BY topics.start_time ASC""",
        (project_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_keyword(video_id, word, category, count=1):
    kid = str(uuid.uuid4())
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM keywords WHERE video_id = ? AND word = ? AND category = ?", (video_id, word, category)).fetchone()
    if row:
        conn.execute("UPDATE keywords SET count = count + ? WHERE id = ?", (count, row["id"]))
    else:
        conn.execute(
            "INSERT INTO keywords (id, video_id, word, category, count) VALUES (?, ?, ?, ?, ?)",
            (kid, video_id, word, category, count)
        )
    conn.commit()
    conn.close()
    return kid

def get_keywords(video_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM keywords WHERE video_id = ? ORDER BY count DESC", (video_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_keywords_for_project(project_id):
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT keywords.* FROM keywords 
           JOIN videos ON keywords.video_id = videos.id 
           WHERE videos.project_id = ? ORDER BY keywords.count DESC""",
        (project_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_graph_edge(project_id, source, target, relationship, weight=1.0):
    gid = str(uuid.uuid4())
    conn = get_db_connection()
    # Check if exists
    row = conn.execute(
        "SELECT * FROM knowledge_graph WHERE project_id = ? AND source = ? AND target = ? AND relationship = ?",
        (project_id, source, target, relationship)
    ).fetchone()
    if row:
        conn.execute("UPDATE knowledge_graph SET weight = weight + ? WHERE id = ?", (weight, row["id"]))
    else:
        conn.execute(
            "INSERT INTO knowledge_graph (id, project_id, source, target, relationship, weight) VALUES (?, ?, ?, ?, ?, ?)",
            (gid, project_id, source, target, relationship, weight)
        )
    conn.commit()
    conn.close()
    return gid

def get_knowledge_graph(project_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM knowledge_graph WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_chat_message(project_id, session_id, role, message):
    cid = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO chat_history (id, project_id, session_id, role, message, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (cid, project_id, session_id, role, message, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return cid

def get_chat_history(project_id, session_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM chat_history WHERE project_id = ? AND session_id = ? ORDER BY created_at ASC",
        (project_id, session_id)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_chat_history(project_id, session_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM chat_history WHERE project_id = ? AND session_id = ?", (project_id, session_id))
    conn.commit()
    conn.close()

def save_summary(video_id, executive_summary, key_topics=None, important_quotes=None, timeline=None, action_items=None, main_ideas=None):
    sid = str(uuid.uuid4())
    conn = get_db_connection()
    
    # Check if exists
    row = conn.execute("SELECT * FROM summaries WHERE video_id = ?", (video_id,)).fetchone()
    if row:
        conn.execute(
            """UPDATE summaries SET 
               executive_summary = ?, key_topics = ?, important_quotes = ?, timeline = ?, action_items = ?, main_ideas = ?
               WHERE video_id = ?""",
            (executive_summary, json.dumps(key_topics) if key_topics else None, json.dumps(important_quotes) if important_quotes else None,
             json.dumps(timeline) if timeline else None, json.dumps(action_items) if action_items else None, json.dumps(main_ideas) if main_ideas else None, video_id)
        )
    else:
        conn.execute(
            """INSERT INTO summaries (id, video_id, executive_summary, key_topics, important_quotes, timeline, action_items, main_ideas)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sid, video_id, executive_summary, json.dumps(key_topics) if key_topics else None, json.dumps(important_quotes) if important_quotes else None,
             json.dumps(timeline) if timeline else None, json.dumps(action_items) if action_items else None, json.dumps(main_ideas) if main_ideas else None)
        )
    conn.commit()
    conn.close()
    return sid

def get_summary(video_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM summaries WHERE video_id = ?", (video_id,)).fetchone()
    conn.close()
    if row:
        res = dict(row)
        res["key_topics"] = json.loads(res["key_topics"]) if res["key_topics"] else None
        res["important_quotes"] = json.loads(res["important_quotes"]) if res["important_quotes"] else None
        res["timeline"] = json.loads(res["timeline"]) if res["timeline"] else None
        res["action_items"] = json.loads(res["action_items"]) if res["action_items"] else None
        res["main_ideas"] = json.loads(res["main_ideas"]) if res["main_ideas"] else None
        return res
    return None

def log_retrieval(project_id, query, retrieved_chunks, response=None):
    rid = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO retrieval_logs (id, project_id, query, retrieved_chunks_json, generated_response, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (rid, project_id, query, json.dumps(retrieved_chunks), response, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return rid

def get_retrieval_logs(project_id, limit=50):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM retrieval_logs WHERE project_id = ? ORDER BY created_at DESC LIMIT ?", (project_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_channel_monitors(project_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM channel_monitors WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_channel_monitor(project_id, channel_id, sync_interval, auto_sync=1):
    mid = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO channel_monitors (id, project_id, channel_id, sync_interval, auto_sync, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (mid, project_id, channel_id, sync_interval, auto_sync, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return mid

def get_destination_channels(project_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM destination_channels WHERE project_id = ?", (project_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_destination_channel(project_id, platform, name, caption_template=None, hashtags=None, schedule_time=None):
    did = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO destination_channels (id, project_id, platform, name, caption_template, hashtags, schedule_time, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (did, project_id, platform, name, caption_template, hashtags, schedule_time, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return did

def get_clip_edit(clip_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM clip_edits WHERE clip_id = ?", (clip_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def save_clip_edit(clip_id, trim_start, trim_end, crop_x, crop_y, crop_w, crop_h, face_tracking=1, font_family="Montserrat", font_color="#FFFFFF", font_size=24, bg_music_volume=0.5):
    eid = str(uuid.uuid4())
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM clip_edits WHERE clip_id = ?", (clip_id,)).fetchone()
    if row:
        conn.execute(
            """UPDATE clip_edits SET trim_start = ?, trim_end = ?, crop_x = ?, crop_y = ?, crop_w = ?, crop_h = ?,
               face_tracking = ?, font_family = ?, font_color = ?, font_size = ?, bg_music_volume = ?
               WHERE clip_id = ?""",
            (trim_start, trim_end, crop_x, crop_y, crop_w, crop_h, face_tracking, font_family, font_color, font_size, bg_music_volume, clip_id)
        )
    else:
        conn.execute(
            """INSERT INTO clip_edits (id, clip_id, trim_start, trim_end, crop_x, crop_y, crop_w, crop_h, face_tracking, font_family, font_color, font_size, bg_music_volume, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (eid, clip_id, trim_start, trim_end, crop_x, crop_y, crop_w, crop_h, face_tracking, font_family, font_color, font_size, bg_music_volume, datetime.utcnow().isoformat())
        )
    conn.commit()
    conn.close()
    return eid

def get_pipeline_stages(video_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM pipeline_stages WHERE video_id = ?", (video_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_pipeline_stage(video_id, stage_name, status, elapsed_time=0.0, log_text=None):
    sid = str(uuid.uuid4())
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM pipeline_stages WHERE video_id = ? AND stage_name = ?", (video_id, stage_name)).fetchone()
    if row:
        conn.execute(
            "UPDATE pipeline_stages SET status = ?, elapsed_time = ?, log_text = ?, updated_at = ? WHERE id = ?",
            (status, elapsed_time, log_text, datetime.utcnow().isoformat(), row["id"])
        )
    else:
        conn.execute(
            "INSERT INTO pipeline_stages (id, video_id, stage_name, status, elapsed_time, log_text, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sid, video_id, stage_name, status, elapsed_time, log_text, datetime.utcnow().isoformat())
        )
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()
