import os
import shutil
import uuid
import traceback
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
    get_settings, update_setting, get_db_connection,
    add_chat_message, get_chat_history, clear_chat_history,
    get_pipeline_stages, get_summary
)
from clipforge_engine.pipeline import run_processing_pipeline
from clipforge_engine.services.video import render_clip, get_crop_coordinates
from clipforge_engine.services.subtitles import generate_ass_file
from clipforge_engine.services.ai import generate_titles, generate_metadata, generate_hooks
from clipforge_engine.rag import query_similar_chunks, generate_grounded_answer
from clipforge_engine.video_qa_agents import run_video_qa_pipeline
from clipforge_engine.channel import resolve_channel_videos, import_channel_videos, search_channel_library
import clipforge_engine.cse473_lab as cse473

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
app.mount("/static/temp", StaticFiles(directory=TEMP_DIR), name="temp")

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

# Helper to resolve clip on disk
def resolve_clip_file_path(clip: dict, video: dict = None) -> Optional[str]:
    raw_path = clip.get("file_path")
    if raw_path:
        norm = os.path.normpath(raw_path)
        if os.path.exists(norm) and os.path.getsize(norm) > 1000:
            return norm
        if raw_path.startswith("/static/clips/"):
            cand = os.path.join(CLIPS_DIR, os.path.basename(raw_path))
            if os.path.exists(cand):
                return cand
        elif raw_path.startswith("/static/temp/"):
            cand = os.path.join(TEMP_DIR, os.path.basename(raw_path))
            if os.path.exists(cand):
                return cand
        cand_temp = os.path.join(TEMP_DIR, os.path.basename(raw_path))
        if os.path.exists(cand_temp):
            return cand_temp
        cand_clip = os.path.join(CLIPS_DIR, os.path.basename(raw_path))
        if os.path.exists(cand_clip):
            return cand_clip

    # Check CLIPS_DIR for {clip_id}.mp4
    cand_clip = os.path.join(CLIPS_DIR, f"{clip['id']}.mp4")
    if os.path.exists(cand_clip):
        return cand_clip

    # Check TEMP_DIR for clip_{video_id[:8]}_{start}_{end}.mp4
    video_id = clip.get("video_id", "")
    cand_temp = os.path.join(TEMP_DIR, f"clip_{video_id[:8]}_{int(clip.get('start_time', 0))}_{int(clip.get('end_time', 0))}.mp4")
    if os.path.exists(cand_temp):
        return cand_temp

    # Fallback to source video if available
    if video and video.get("file_path"):
        v_norm = os.path.normpath(video["file_path"])
        if os.path.exists(v_norm):
            return v_norm

    return None

@app.get("/api/clips/{clip_id}/stream")
def api_stream_clip(clip_id: str):
    clip = get_clip(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    video = get_video(clip["video_id"])
    file_path = resolve_clip_file_path(clip, video)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")
    return FileResponse(file_path, media_type="video/mp4")

@app.get("/api/clips/{clip_id}/download")
def api_download_clip(clip_id: str):
    clip = get_clip(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    video = get_video(clip["video_id"])
    file_path = resolve_clip_file_path(clip, video)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")
    safe_title = "".join(c for c in clip.get("title", "clip") if c.isalnum() or c in (" ", "_", "-")).strip() or "clip"
    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=f"{safe_title}.mp4",
        content_disposition_type="attachment"
    )

@app.get("/api/videos/{video_id}/stream")
def api_stream_video(video_id: str):
    video = get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    vpath = video.get("file_path")
    if vpath:
        norm = os.path.normpath(vpath)
        if os.path.exists(norm) and not os.path.isdir(norm):
            return FileResponse(norm, media_type="video/mp4")
    # Check TEMP_DIR
    cand_temp = os.path.join(TEMP_DIR, f"{video_id}.mp4")
    if os.path.exists(cand_temp):
        return FileResponse(cand_temp, media_type="video/mp4")
    # Check IMPORTS_DIR
    for ext in [".mp4", ".mov", ".mkv", ".webm"]:
        cand_imp = os.path.join(IMPORTS_DIR, f"{video_id}{ext}")
        if os.path.exists(cand_imp):
            return FileResponse(cand_imp, media_type="video/mp4")
    raise HTTPException(status_code=404, detail="Source video file not found on disk")

@app.get("/api/videos/{video_id}/stages")
def api_get_video_stages(video_id: str):
    return get_pipeline_stages(video_id)

@app.post("/api/videos/{video_id}/process")
def api_process_video(video_id: str, background_tasks: BackgroundTasks):
    video = get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    background_tasks.add_task(run_processing_pipeline, video_id)
    return {"status": "processing_started", "video_id": video_id}

@app.get("/api/videos/{video_id}/summary")
def api_get_video_summary(video_id: str):
    summary = get_summary(video_id)
    return summary or {}

class SearchRequest(BaseModel):
    project_id: str
    query: str

@app.post("/api/videos/{video_id}/search")
def api_search_video(video_id: str, req: SearchRequest):
    settings = get_settings()
    ollama_url = settings.get("ollama_url", "http://localhost:11434")
    embed_model = settings.get("embedding_model", "nomic-embed-text")
    try:
        hits = query_similar_chunks(
            project_id=req.project_id,
            query_text=req.query,
            k=5,
            video_ids=[video_id],
            model=embed_model,
            base_url=ollama_url
        )
        return hits
    except Exception as e:
        print(f"Moment search error: {e}")
        return []

class ChatRequest(BaseModel):
    project_id: str
    session_id: Optional[str] = "default"
    video_id: Optional[str] = None
    query: str

@app.post("/api/chat")
def api_chat(req: ChatRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    add_chat_message(req.project_id, req.session_id, "user", req.query, video_id=req.video_id)
    
    settings = get_settings()
    ollama_model = settings.get("ollama_model", "qwen2.5:3b")
    
    try:
        if req.video_id:
            qa_res = run_video_qa_pipeline(
                project_id=req.project_id,
                video_id=req.video_id,
                query=req.query,
                session_id=req.session_id,
                model=ollama_model
            )
            answer = qa_res["answer"]
            retrieved = qa_res["retrieved_chunks"]
            citations = qa_res.get("citations", [])
            confidence = qa_res.get("confidence", 1.0)
        else:
            # Fallback across project videos
            from clipforge_engine.rag import hybrid_retrieve_chunks, generate_grounded_answer
            all_vids = get_videos(req.project_id)
            if all_vids:
                retrieved = hybrid_retrieve_chunks(req.project_id, all_vids[0]["id"], req.query, k=4)
                answer = generate_grounded_answer(req.project_id, req.query, retrieved, model=ollama_model)
                citations = []
                confidence = 0.8
            else:
                answer = "No videos available in this workspace to search."
                retrieved = []
                citations = []
                confidence = 0.0
    except Exception as err:
        print(f"Chat Multi-Agent RAG error: {err}")
        answer = f"I encountered an issue querying the video knowledge base: {str(err)}"
        retrieved = []
        citations = []
        confidence = 0.0
        
    add_chat_message(req.project_id, req.session_id, "assistant", answer, video_id=req.video_id)
    return {
        "answer": answer,
        "retrieved_chunks": retrieved,
        "citations": citations,
        "confidence": confidence
    }

@app.get("/api/chat/history")
def api_chat_history(project_id: str, session_id: Optional[str] = "default", video_id: Optional[str] = None):
    return get_chat_history(project_id, session_id, video_id=video_id)

@app.delete("/api/chat/history")
def api_clear_chat_history(project_id: str, session_id: Optional[str] = "default"):
    clear_chat_history(project_id, session_id)
    return {"status": "cleared"}

# --- YouTube Channel Endpoints ---
class ChannelResolveRequest(BaseModel):
    url: str
    max_videos: Optional[int] = 10

class ChannelImportRequest(BaseModel):
    project_id: str
    videos: List[Dict[str, Any]]

class ChannelSearchRequest(BaseModel):
    project_id: str
    query: str
    video_ids: Optional[List[str]] = None
    k: Optional[int] = 6

@app.post("/api/channels/resolve")
def api_resolve_channel(req: ChannelResolveRequest):
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="Channel URL is required")
    vids = resolve_channel_videos(req.url, max_videos=req.max_videos or 10)
    return {"videos": vids, "count": len(vids)}

@app.post("/api/channels/import")
def api_import_channel(req: ChannelImportRequest):
    if not req.videos:
        raise HTTPException(status_code=400, detail="No videos selected for import")
    res = import_channel_videos(req.project_id, req.videos, dispatch_pipeline=True)
    return {"imported": res, "count": len(res)}

@app.post("/api/channels/search")
def api_search_channel(req: ChannelSearchRequest):
    hits = search_channel_library(req.project_id, req.query, req.video_ids, k=req.k or 6)
    return hits

# --- CSE473 AI Lab Endpoints ---
class TokenizeRequest(BaseModel):
    text: str

class AttentionRequest(BaseModel):
    tokens: List[str]
    num_heads: Optional[int] = 2

class PromptCompareRequest(BaseModel):
    query: str
    context: Optional[str] = ""
    model: Optional[str] = "qwen2.5:3b"

class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class LoRARequest(BaseModel):
    d_in: Optional[int] = 1024
    d_out: Optional[int] = 1024
    rank: Optional[int] = 8

class QuantizationRequest(BaseModel):
    param_count_billions: Optional[float] = 3.0

class GridWorldRequest(BaseModel):
    grid_size: Optional[int] = 4
    episodes: Optional[int] = 150

class EvaluationRequest(BaseModel):
    video_id: str
    project_id: str

@app.post("/api/cse473/tokenize")
def api_cse473_tokenize(req: TokenizeRequest):
    return cse473.visualize_tokenization(req.text)

@app.post("/api/cse473/attention")
def api_cse473_attention(req: AttentionRequest):
    return cse473.compute_attention_weights(req.tokens, num_heads=req.num_heads or 2)

@app.post("/api/cse473/transformer_forward")
def api_cse473_transformer_forward(req: TokenizeRequest):
    return cse473.transformer_forward_pass_demo(req.text)

@app.post("/api/cse473/prompt_compare")
def api_cse473_prompt_compare(req: PromptCompareRequest):
    return cse473.compare_prompts(req.query, req.context or "", model=req.model or "qwen2.5:3b")

@app.post("/api/cse473/tool_call")
def api_cse473_tool_call(req: ToolCallRequest):
    return cse473.demonstrate_tool_calling(req.tool_name, req.arguments)

@app.post("/api/cse473/lora_demo")
def api_cse473_lora_demo(req: LoRARequest):
    return cse473.lora_adapter_demo(req.d_in or 1024, req.d_out or 1024, req.rank or 8)

@app.post("/api/cse473/quantization_benchmark")
def api_cse473_quantization_benchmark(req: QuantizationRequest):
    return cse473.quantization_benchmark(req.param_count_billions or 3.0)

@app.post("/api/cse473/gridworld_step")
def api_cse473_gridworld_step(req: GridWorldRequest):
    return cse473.simulate_gridworld_q_learning(req.grid_size or 4, req.episodes or 150)

@app.post("/api/cse473/prompt_injection_test")
def api_cse473_prompt_injection_test():
    return cse473.run_prompt_injection_safety_test()

@app.post("/api/cse473/evaluate_qa")
def api_cse473_evaluate_qa(req: EvaluationRequest):
    return cse473.run_comprehensive_evaluation_suite(req.video_id, req.project_id)

# Settings
@app.get("/api/settings")
def api_get_settings():
    return get_settings()

@app.post("/api/settings")
def api_update_settings(updates: List[SettingUpdate]):
    for update in updates:
        update_setting(update.key, update.value)
    return {"status": "settings updated"}
