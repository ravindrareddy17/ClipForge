import os
import asyncio
import traceback
import json
from clipforge_engine.db import (
    get_video, update_video_status, create_clip, get_db_connection,
    create_transcript_chunk, save_embedding, create_topic, create_keyword,
    add_graph_edge, save_summary
)
from clipforge_engine.services.video import get_video_metadata, detect_scenes, get_crop_coordinates
from clipforge_engine.services.transcribe import extract_audio, transcribe_audio
from clipforge_engine.services.ai import detect_viral_moments, generate_metadata, generate_hooks
from clipforge_engine.rag import chunk_transcript, index_transcript_chunks
from clipforge_engine.agents import (
    run_summary_agent, run_topic_detector, run_entity_extractor, run_knowledge_graph_agent
)

def fetch_youtube_metadata_and_audio(url, output_wav_path):
    import yt_dlp
    base_path, _ = os.path.splitext(output_wav_path)
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': base_path + '.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        duration = float(info.get("duration", 0.0) or 300.0)
        width = int(info.get("width", 1920) or 1920)
        height = int(info.get("height", 1080) or 1080)
        fps = float(info.get("fps", 30.0) or 30.0)
        
    if not os.path.exists(output_wav_path):
        actual_wav = base_path + '.wav'
        if os.path.exists(actual_wav):
            os.rename(actual_wav, output_wav_path)
            
    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps
    }

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
        
        # Check if the path is a URL
        is_url = video["file_path"].startswith("http://") or video["file_path"].startswith("https://")
        
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        audio_path = os.path.join(temp_dir, f"{video_id}.wav")
        
        if is_url:
            print("Video source is a URL. Downloading audio and metadata using yt-dlp...")
            try:
                meta = fetch_youtube_metadata_and_audio(video["file_path"], audio_path)
                has_audio = True
            except Exception as dl_err:
                print(f"yt-dlp download failed: {dl_err}. Falling back to mock transcript/metadata.")
                meta = {"duration": 180.0, "width": 1920, "height": 1080, "fps": 30.0}
                has_audio = False
            scenes = [0.0]
        else:
            # 1. Read metadata
            meta = get_video_metadata(video["file_path"])
            print(f"Metadata read: {meta}")
            has_audio = True
            
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
        
        if not is_url:
            # 2. Scene detection
            print("Detecting scenes...")
            scenes = detect_scenes(video["file_path"])
            print(f"Detected {len(scenes)} scene cuts: {scenes}")
            
        update_video_status(video_id, "processing", scenes=scenes)
        
        # 3. Audio Extraction & Transcription
        print("Extracting audio and transcribing...")
        if not is_url:
            extract_audio(video["file_path"], audio_path)
        
        # Get transcription (Whisper or mock fallback)
        transcript = []
        if has_audio and os.path.exists(audio_path):
            try:
                transcript = transcribe_audio(audio_path, duration=duration)
            except Exception as tr_err:
                print(f"Transcription failed: {tr_err}")
                transcript = []
                
        if not transcript:
            print("No transcription generated. Generating mock transcription fallback.")
            from clipforge_engine.services.transcribe import generate_mock_transcript
            transcript = generate_mock_transcript(duration)
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
            
        # RAG pipeline integration
        try:
            print("Running RAG Chunking and Indexing...")
            # Convert transcript object to text
            transcript_text = " ".join([seg.get("text", "") for seg in transcript])
            
            # 1. Generate semantic chunks
            chunks = chunk_transcript(video_id, video["project_id"], transcript)
            print(f"Generated {len(chunks)} semantic chunks.")
            
            # 2. Save chunks to SQLite and index in ChromaDB
            for idx, chk in enumerate(chunks):
                cid = create_transcript_chunk(
                    video_id=video_id,
                    project_id=video["project_id"],
                    start_time=chk["start_time"],
                    end_time=chk["end_time"],
                    text=chk["text"],
                    speaker=chk["speaker"],
                    keywords=chk["keywords"]
                )
                chk["id"] = cid # Save the database ID
            
            # Index in ChromaDB
            index_transcript_chunks(video_id, video["project_id"], chunks)
            print("ChromaDB indexing complete.")
            
            # 3. Run AI Agents for intelligence processing
            print("Running Summary Agent...")
            summary_data = run_summary_agent(transcript_text)
            save_summary(
                video_id=video_id,
                executive_summary=summary_data.get("executive_summary", ""),
                key_topics=summary_data.get("key_topics"),
                important_quotes=summary_data.get("important_quotes"),
                timeline=summary_data.get("timeline"),
                action_items=summary_data.get("action_items"),
                main_ideas=summary_data.get("main_ideas")
            )
            
            print("Running Topic Detector Agent...")
            detected_topics = run_topic_detector(transcript)
            for tp in detected_topics:
                create_topic(
                    video_id=video_id,
                    name=tp.get("name", "Topic"),
                    start_time=float(tp.get("start_time", 0.0)),
                    end_time=float(tp.get("end_time", 1.0)),
                    summary=tp.get("summary", "")
                )
                
            print("Running Keyword Entity Extractor Agent...")
            entities = run_entity_extractor(transcript_text)
            if entities:
                for cat, list_words in entities.items():
                    if isinstance(list_words, list):
                        for word in list_words:
                            create_keyword(video_id, word, cat)
                            
            print("Running Knowledge Graph Builder Agent...")
            relations = run_knowledge_graph_agent(transcript_text)
            for rel in relations:
                add_graph_edge(
                    project_id=video["project_id"],
                    source=rel.get("source", ""),
                    target=rel.get("target", ""),
                    relationship=rel.get("relationship", ""),
                    weight=float(rel.get("weight", 1.0))
                )
                
        except Exception as rag_err:
            print(f"RAG processing pipeline encountered an issue (Ollama might be offline): {rag_err}")
            traceback.print_exc()
            
        update_video_status(video_id, "completed")
        print(f"Pipeline completed successfully for video {video_id}.")
        
    except Exception as e:
        print(f"Pipeline failed for video {video_id}: {e}")
        traceback.print_exc()
        update_video_status(video_id, "failed")
