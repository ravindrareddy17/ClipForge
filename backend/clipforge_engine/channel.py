"""
ClipForge AI V2 - YouTube Channel Ingestion & Multi-Video Discovery
Extracts videos from a YouTube channel URL without downloading media,
and dispatches independent processing pipelines.
"""

import os
import logging
import threading
import asyncio
from typing import List, Dict, Any, Optional

import yt_dlp
from clipforge_engine.db import create_video, get_videos, get_video
from clipforge_engine.pipeline import run_processing_pipeline
from clipforge_engine.rag import hybrid_retrieve_chunks, format_timestamp

logger = logging.getLogger("clipforge.channel")


def resolve_channel_videos(channel_url: str, max_videos: int = 10) -> List[Dict[str, Any]]:
    """
    Resolves video uploads from a YouTube channel URL using yt-dlp in flat extraction mode.
    Does NOT download video or audio streams.
    """
    clean_url = channel_url.strip()
    # If the user passed a channel home, ensure /videos tab is targeted for uploads
    if "@" in clean_url and not clean_url.endswith("/videos") and "/watch" not in clean_url and "/playlist" not in clean_url:
        target_url = clean_url.rstrip("/") + "/videos"
    else:
        target_url = clean_url

    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
        "playlist_items": f"1-{max_videos}",
        "socket_timeout": 15
    }

    results: List[Dict[str, Any]] = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if not info:
                return []

            entries = info.get("entries") or [info]
            for entry in entries:
                if not entry:
                    continue
                v_id = entry.get("id")
                v_title = entry.get("title", f"Video {v_id}")
                v_url = entry.get("url") or f"https://www.youtube.com/watch?v={v_id}"
                if not v_url.startswith("http"):
                    v_url = f"https://www.youtube.com/watch?v={v_id}"

                v_duration = entry.get("duration") or 0.0
                v_thumb = entry.get("thumbnail") or (
                    entry.get("thumbnails")[-1].get("url") if entry.get("thumbnails") else None
                )

                results.append({
                    "id": v_id,
                    "title": v_title,
                    "url": v_url,
                    "duration": float(v_duration) if v_duration else 0.0,
                    "thumbnail": v_thumb,
                    "view_count": entry.get("view_count", 0),
                    "channel": info.get("channel") or info.get("uploader") or "Channel"
                })

                if len(results) >= max_videos:
                    break

    except Exception as e:
        logger.error(f"Failed to resolve channel videos for {channel_url}: {e}")

    return results


def import_channel_videos(
    project_id: str,
    selected_videos: List[Dict[str, Any]],
    dispatch_pipeline: bool = True
) -> List[Dict[str, Any]]:
    """
    Creates video database records for selected channel videos and dispatches
    independent processing pipelines for each video.
    """
    imported = []

    for item in selected_videos:
        vid_title = item.get("title", "Imported Video")
        vid_url = item.get("url", "")
        if not vid_url:
            continue

        # Create distinct video record
        vid_id = create_video(
            project_id=project_id,
            filename=vid_title,
            file_path=vid_url
        )

        imported.append({
            "video_id": vid_id,
            "title": vid_title,
            "url": vid_url,
            "status": "pending"
        })

        if dispatch_pipeline:
            # Launch separate background processing pipeline
            threading.Thread(
                target=lambda v=vid_id: asyncio.run(run_processing_pipeline(v)),
                daemon=True
            ).start()

    return imported


def search_channel_library(
    project_id: str,
    query: str,
    video_ids: Optional[List[str]] = None,
    k: int = 6
) -> List[Dict[str, Any]]:
    """
    Searches across multiple videos in a channel workspace with citations
    preserving [Video Title | MM:SS].
    """
    all_videos = get_videos(project_id)
    if not all_videos:
        return []

    target_vids = [v for v in all_videos if not video_ids or v["id"] in video_ids]
    video_title_map = {v["id"]: v["filename"] for v in target_vids}

    all_hits = []
    for v in target_vids:
        try:
            hits = hybrid_retrieve_chunks(project_id, v["id"], query, k=max(2, k // len(target_vids) + 1))
            for h in hits:
                meta = h.get("metadata", {})
                st = meta.get("start_time", 0.0)
                h["video_title"] = video_title_map.get(v["id"], "Video")
                h["formatted_citation"] = f"[{h['video_title']} | {format_timestamp(st)}]"
                all_hits.append(h)
        except Exception as e:
            logger.warning(f"Error querying video {v['id']}: {e}")

    all_hits.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return all_hits[:k]
