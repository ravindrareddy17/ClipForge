import os
import asyncio
import traceback
import json
from clipforge_engine.db import get_video, update_video_status, create_clip, get_db_connection
from clipforge_engine.services.video import get_video_metadata, detect_scenes, get_crop_coordinates
from clipforge_engine.services.transcribe import extract_audio, transcribe_audio
from clipforge_engine.services.ai import detect_viral_moments, generate_metadata, generate_hooks

async def run_processing_pipeline(video_id: str):
    """
    Run the video import, transcribing, scene detection, and moment extraction pipeline.
    """
    try:
        video = get_video(video_id)
        if not video:
            print(f"Video {video_id} not found in database.")
            return
            
        print(f"Starting processing pipeline for video: {video['filename']} (ID: {video_id})")
        update_video_status(video_id, "processing")
        
        # 1. Read metadata
        meta = get_video_metadata(video["file_path"])
        print(f"Metadata read: {meta}")
        
        # Update video record with metadata
        conn = get_db_connection()
        conn.execute(
            "UPDATE videos SET duration = ?, width = ?, height = ?, fps = ? WHERE id = ?",
            (meta["duration"], meta["width"], meta["height"], meta["fps"], video_id)
        )
        conn.commit()
        conn.close()
        
        # Refresh local data
        duration = meta["duration"]
        
        # 2. Scene detection
        print("Detecting scenes...")
        scenes = detect_scenes(video["file_path"])
        print(f"Detected {len(scenes)} scene cuts: {scenes}")
        update_video_status(video_id, "processing", scenes=scenes)
        
        # 3. Audio Extraction & Transcription
        print("Extracting audio and transcribing...")
        # Save audio temporarily in backend/data/temp
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        audio_path = os.path.join(temp_dir, f"{video_id}.wav")
        
        extract_audio(video["file_path"], audio_path)
        
        # Get transcription (Whisper or mock fallback)
        transcript = transcribe_audio(audio_path, duration=duration)
        print(f"Transcription complete. Got {len(transcript)} segments.")
        update_video_status(video_id, "processing", transcript=transcript)
        
        # Clean up temp audio file
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass
                
        # 4. Detect viral moments
        print("Detecting viral moments...")
        clips = await detect_viral_moments(transcript, duration)
        print(f"Generated {len(clips)} clip proposals.")
        
        # 5. Populate and save clips to DB
        for clip in clips:
            # Generate face-tracked crop window
            crop_x = get_crop_coordinates(video["file_path"], clip["start_time"], clip["end_time"])
            
            # Subtitle style default config
            sub_style = {
                "font_family": "Montserrat",
                "font_size": 28,
                "primary_color": "#FFFFFF",
                "accent_color": "#FF0055",
                "outline_color": "#000000",
                "margin_v": 140
            }
            
            # Save proposed clip
            cid = create_clip(
                video_id=video_id,
                title=clip["title"],
                start_time=clip["start_time"],
                end_time=clip["end_time"],
                duration=clip["duration"],
                score=clip["score"],
                explanation=clip["explanation"],
                subtitles=clip["words"],
                subtitle_style=sub_style
            )
            
            # Set initial crop coordinates in the clip record
            conn = get_db_connection()
            # We will save crop_x in a settings column or custom column
            # For Phase 1, we can extend the clips table or store crop parameters in subtitle_style JSON
            sub_style["crop_x"] = crop_x
            conn.execute(
                "UPDATE clips SET subtitle_style = ? WHERE id = ?",
                (json.dumps(sub_style), cid)
            )
            conn.commit()
            conn.close()
            
            # We can also generate metadata (description, hooks) async in background
            # but we can do it on-demand to speed up video processing!
            
        update_video_status(video_id, "completed")
        print(f"Pipeline completed successfully for video {video_id}.")
        
    except Exception as e:
        print(f"Pipeline failed for video {video_id}: {e}")
        traceback.print_exc()
        update_video_status(video_id, "failed")
