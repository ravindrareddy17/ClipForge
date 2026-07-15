import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from clipforge_engine.db import (
    create_project, get_projects, get_project,
    create_video, get_videos, get_video,
    get_clips, get_clip, get_all_clips, update_clip,
    get_settings, update_setting
)
from clipforge_engine.pipeline import run_processing_pipeline
from clipforge_engine.services.video import render_clip, get_crop_coordinates
from clipforge_engine.services.subtitles import generate_ass_file
from clipforge_engine.services.ai import generate_titles, generate_metadata, generate_hooks

app = FastAPI(title="ClipForge AI API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder setup
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
IMPORTS_DIR = os.path.join(DATA_DIR, "imports")
CLIPS_DIR = os.path.join(DATA_DIR, "clips")
TEMP_DIR = os.path.join(DATA_DIR, "temp")

os.makedirs(IMPORTS_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Serve video directories statically
app.mount("/static/imports", StaticFiles(directory=IMPORTS_DIR), name="imports")
app.mount("/static/clips", StaticFiles(directory=CLIPS_DIR), name="clips")

# --- Schemas ---
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class ImportPathRequest(BaseModel):
    file_path: str

class ClipUpdate(BaseModel):
    title: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    subtitles: Optional[List[Dict[str, Any]]] = None
    subtitle_style: Optional[Dict[str, Any]] = None

class SettingUpdate(BaseModel):
    key: str
    value: Any

# --- Endpoints ---

# Projects
@app.post("/api/projects")
def api_create_project(project: ProjectCreate):
    pid = create_project(project.name, project.description)
    return {"id": pid, "name": project.name, "description": project.description}

@app.get("/api/projects")
def api_get_projects():
    return get_projects()

@app.get("/api/projects/{project_id}")
def api_get_project(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

# Videos (Imports)
@app.post("/api/projects/{project_id}/videos/upload")
async def api_upload_video(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a video file through form data.
    """
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    target_path = os.path.join(IMPORTS_DIR, f"{file_id}{ext}")
    
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    vid = create_video(
        project_id=project_id,
        filename=file.filename,
        file_path=target_path
    )
    
    # Start pipeline in the background
    background_tasks.add_task(run_processing_pipeline, vid)
    
    return {"id": vid, "filename": file.filename, "status": "pending"}

@app.post("/api/projects/{project_id}/videos/import-path")
def api_import_video_path(
    project_id: str,
    req: ImportPathRequest,
    background_tasks: BackgroundTasks
):
    """
    Import video by referencing a local path on the system.
    Copies it to the local imports directory.
    """
    source_path = req.file_path
    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail=f"Local path does not exist: {source_path}")
        
    file_id = str(uuid.uuid4())
    filename = os.path.basename(source_path)
    ext = os.path.splitext(filename)[1]
    target_path = os.path.join(IMPORTS_DIR, f"{file_id}{ext}")
    
    try:
        shutil.copy2(source_path, target_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to copy file: {str(e)}")
        
    vid = create_video(
        project_id=project_id,
        filename=filename,
        file_path=target_path
    )
    
    background_tasks.add_task(run_processing_pipeline, vid)
    
    return {"id": vid, "filename": filename, "status": "pending"}

@app.get("/api/projects/{project_id}/videos")
def api_get_project_videos(project_id: str):
    return get_videos(project_id)

@app.get("/api/videos/{video_id}")
def api_get_video_details(video_id: str):
    v = get_video(video_id)
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    return v

# Clips
@app.get("/api/videos/{video_id}/clips")
def api_get_video_clips(video_id: str):
    return get_clips(video_id)

@app.get("/api/clips")
def api_get_all_clips():
    return get_all_clips()

@app.get("/api/clips/{clip_id}")
def api_get_clip_details(clip_id: str):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")
    return c

@app.put("/api/clips/{clip_id}")
def api_update_clip(clip_id: str, data: ClipUpdate):
    c = get_clip(clip_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clip not found")
        
    update_clip(
        clip_id=clip_id,
        status="ready_to_render" if c["status"] == "failed" else None,
        subtitles=data.subtitles,
        subtitle_style=data.subtitle_style
    )
    
    # Update title or times in DB directly if provided
    conn = get_db_connection()
    updates = []
    params = []
    if data.title is not None:
        updates.append("title = ?")
        params.append(data.title)
    if data.start_time is not None:
        updates.append("start_time = ?")
        params.append(data.start_time)
    if data.end_time is not None:
        updates.append("end_time = ?")
        params.append(data.end_time)
        
    if updates:
        # Calculate duration
        c_ref = get_clip(clip_id)
        start = data.start_time if data.start_time is not None else c_ref["start_time"]
        end = data.end_time if data.end_time is not None else c_ref["end_time"]
        dur = end - start
        updates.append("duration = ?")
        params.append(dur)
        
        params.append(clip_id)
        conn.execute(f"UPDATE clips SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        
    conn.close()
    return {"status": "updated"}

@app.post("/api/clips/{clip_id}/render")
async def api_render_clip(clip_id: str, background_tasks: BackgroundTasks):
    """
    Render a clip by cropping it to 9:16 and burning in subtitles using FFmpeg.
    """
    clip = get_clip(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
        
    video = get_video(clip["video_id"])
    if not video:
        raise HTTPException(status_code=404, detail="Source video not found")
        
    # Update status to rendering
    update_clip(clip_id, status="rendering")
    
    # Process rendering as a background task
    async def render_task():
        try:
            # Parse style & configuration
            import json
            style_config = json.loads(clip["subtitle_style"]) if clip["subtitle_style"] else {}
            words = json.loads(clip["subtitles"]) if clip["subtitles"] else []
            
            # Generate temporary ASS subtitle file
            ass_path = os.path.join(TEMP_DIR, f"{clip_id}.ass")
            generate_ass_file(words, ass_path, style_config)
            
            # Target output path
            output_name = f"{clip_id}.mp4"
            output_path = os.path.join(CLIPS_DIR, output_name)
            
            # Re-calculate face tracking if crop_x is not in style_config or if start/end times changed
            crop_x = style_config.get("crop_x")
            if crop_x is None:
                crop_x = get_crop_coordinates(video["file_path"], clip["start_time"], clip["end_time"])
                
            # Perform render
            render_clip(
                input_path=video["file_path"],
                output_path=output_path,
                start_time=clip["start_time"],
                end_time=clip["end_time"],
                crop_x=crop_x,
                ass_subtitle_path=ass_path
            )
            
            # Update DB with rendered path
            relative_url_path = f"/static/clips/{output_name}"
            update_clip(clip_id, status="completed", file_path=relative_url_path)
            
            # Remove temp ASS file
            if os.path.exists(ass_path):
                os.remove(ass_path)
                
            print(f"Clip {clip_id} rendered successfully!")
        except Exception as e:
            print(f"Failed to render clip {clip_id}: {e}")
            traceback.print_exc()
            update_clip(clip_id, status="failed")
            
    background_tasks.add_task(render_task)
    return {"status": "rendering"}

@app.get("/api/clips/{clip_id}/metadata")
async def api_generate_clip_metadata(clip_id: str):
    """
    Generate alternative titles, hooks, and descriptions for a clip.
    """
    clip = get_clip(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
        
    import json
    words = json.loads(clip["subtitles"]) if clip["subtitles"] else []
    transcript_text = " ".join([w["word"] for w in words])
    
    if not transcript_text:
        transcript_text = "Hello world, this is a clip from ClipForge AI."
        
    # Generate metadata using Ollama (async queries)
    titles = await generate_titles(transcript_text)
    hooks = await generate_hooks(transcript_text)
    meta = await generate_metadata(transcript_text)
    
    return {
        "titles": titles,
        "hooks": hooks,
        "metadata": meta
    }

# Settings
@app.get("/api/settings")
def api_get_settings():
    return get_settings()

@app.post("/api/settings")
def api_update_settings(updates: List[SettingUpdate]):
    for update in updates:
        update_setting(update.key, update.value)
    return {"status": "settings updated"}
