import httpx
import json
import re

OLLAMA_URL = "http://localhost:11434"

async def query_ollama(prompt, model="llama3:latest", system_prompt=None):
    """
    Query local Ollama instance.
    """
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3
        }
    }
    if system_prompt:
        payload["system"] = system_prompt
        
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                print(f"Ollama returned status {response.status_code}: {response.text}")
                return None
    except Exception as e:
        print(f"Ollama connection error: {e}")
        return None

async def select_best_model():
    """
    Select available model from Ollama, default to llama3:latest or qwen2.5:3b.
    """
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                for preferred in ["llama3:latest", "llama3", "qwen2.5:3b", "qwen3:4b"]:
                    if preferred in models:
                        return preferred
                if models:
                    return models[0]
    except Exception:
        pass
    return "llama3:latest"

async def detect_viral_moments(transcript_segments, duration_seconds):
    """
    Send transcript to Ollama to detect the top engaging sections.
    Falls back to heuristics if Ollama is not available.
    """
    model = await select_best_model()
    
    # Format the transcript with line index and timestamps
    formatted_transcript = []
    for i, seg in enumerate(transcript_segments):
        formatted_transcript.append(
            f"[{i}] ({seg['start']:.1f}s - {seg['end']:.1f}s): {seg['text']}"
        )
    transcript_text = "\n".join(formatted_transcript)
    
    prompt = f"""
Analyze this video transcript and identify 3 to 5 highly engaging, self-contained clips (each between 15 and 60 seconds).
Look for hooks, high emotion, humor, valuable insights, or major transition points.

Transcript:
{transcript_text}

Output format:
Return ONLY a valid JSON list of objects, with no explanation or conversational text. Use this structure:
[
  {{
    "title": "Short catchy title for the clip",
    "start_segment_index": 0,
    "end_segment_index": 5,
    "score": 92,
    "explanation": "Why this is viral/engaging",
    "hook_overlay": "Engaging hook text to overlay on the screen"
  }}
]
"""
    
    system_prompt = "You are a professional social media editor specializing in TikTok, Reels, and Shorts. You only output valid JSON arrays."
    
    response_text = await query_ollama(prompt, model=model, system_prompt=system_prompt)
    
    clips = []
    if response_text:
        try:
            # Extract JSON array
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                raw_clips = json.loads(json_str)
                
                for rc in raw_clips:
                    start_idx = int(rc["start_segment_index"])
                    end_idx = int(rc["end_segment_index"])
                    
                    # Clamp indices
                    start_idx = max(0, min(len(transcript_segments)-1, start_idx))
                    end_idx = max(start_idx, min(len(transcript_segments)-1, end_idx))
                    
                    start_time = transcript_segments[start_idx]["start"]
                    end_time = transcript_segments[end_idx]["end"]
                    
                    # Collect words in range
                    words_in_clip = []
                    for seg in transcript_segments[start_idx:end_idx + 1]:
                        if "words" in seg:
                            words_in_clip.extend(seg["words"])
                        else:
                            # If word level is missing, split text roughly
                            words = seg["text"].split()
                            seg_dur = seg["end"] - seg["start"]
                            word_dur = seg_dur / max(1, len(words))
                            for idx, w in enumerate(words):
                                words_in_clip.append({
                                    "word": w,
                                    "start": seg["start"] + idx * word_dur,
                                    "end": seg["start"] + (idx + 1) * word_dur
                                })
                                
                    clips.append({
                        "title": rc.get("title", f"Viral Moment {start_time:.1f}s"),
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": end_time - start_time,
                        "score": int(rc.get("score", 85)),
                        "explanation": rc.get("explanation", "High-interest conversation segment."),
                        "hook": rc.get("hook_overlay", "You don't want to miss this"),
                        "words": words_in_clip
                    })
        except Exception as e:
            print(f"Failed to parse Ollama output: {e}. Output was:\n{response_text}")
            
    # Heuristic fallback if Ollama failed or returned no clips
    if not clips:
        print("Using heuristic fallback for viral moment detection.")
        # Divide into ~30 second chunks
        chunk_size = 30.0
        num_chunks = int(duration_seconds // chunk_size)
        if num_chunks == 0:
            num_chunks = 1
            chunk_size = duration_seconds
            
        for i in range(num_chunks):
            start_t = i * chunk_size
            end_t = min(duration_seconds, (i + 1) * chunk_size)
            
            # Map words in range
            words_in_clip = []
            for seg in transcript_segments:
                for w in seg.get("words", []):
                    if start_t <= w["start"] <= end_t:
                        words_in_clip.append(w)
                        
            # Basic fallback words if none mapped
            if not words_in_clip:
                for seg in transcript_segments:
                    if start_t <= seg["start"] <= end_t:
                        words = seg["text"].split()
                        seg_dur = seg["end"] - seg["start"]
                        word_dur = seg_dur / max(1, len(words))
                        for idx, w in enumerate(words):
                            words_in_clip.append({
                                "word": w,
                                "start": seg["start"] + idx * word_dur,
                                "end": seg["start"] + (idx + 1) * word_dur
                            })
                            
            clips.append({
                "title": f"Clip Spotlight #{i+1}",
                "start_time": start_t,
                "end_time": end_t,
                "duration": end_t - start_t,
                "score": 85 - i * 5,
                "explanation": "Segment selected based on timeline division.",
                "hook": "This will change your perspective...",
                "words": words_in_clip
            })
            
    # Sort clips by score descending
    clips.sort(key=lambda x: x["score"], reverse=True)
    return clips

async def generate_titles(clip_transcript_text):
    """
    Generate viral titles with SEO and CTR scores.
    """
    model = await select_best_model()
    prompt = f"""
Based on this transcription snippet, write 5 highly engaging short-form titles (suitable for YouTube Shorts or TikTok).
Keep them under 60 characters, use uppercase words for emphasis, and add relevant emojis.

Transcript snippet:
"{clip_transcript_text}"

Output format:
Return ONLY a JSON list of objects:
[
  {{
    "title": "TITLE HERE",
    "ctr_score": 95,
    "seo_score": 88
  }}
]
"""
    response_text = await query_ollama(prompt, model=model)
    if response_text:
        try:
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception:
            pass
            
    # Fallback titles
    return [
        {"title": "The SECRET they don't tell you! 🤫", "ctr_score": 93, "seo_score": 85},
        {"title": "Everyone missed this ONE detail... 🤯", "ctr_score": 91, "seo_score": 82},
        {"title": "Why this changes EVERYTHING! 🚀", "ctr_score": 88, "seo_score": 80},
        {"title": "How to unlock this hack today! 💡", "ctr_score": 85, "seo_score": 87},
        {"title": "Stop making this huge mistake! ❌", "ctr_score": 94, "seo_score": 79}
    ]

async def generate_metadata(clip_transcript_text):
    """
    Generate description, hashtags, and keywords.
    """
    model = await select_best_model()
    prompt = f"""
Based on this transcription snippet, write a short description, key tags/keywords, and 5 viral hashtags.

Transcript snippet:
"{clip_transcript_text}"

Output format:
Return ONLY a JSON object:
{{
  "description": "Short description here",
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "tags": "tag1, tag2, tag3",
  "pinned_comment": "Pinned engagement comment suggestion"
}}
"""
    response_text = await query_ollama(prompt, model=model)
    if response_text:
        try:
            json_match = re.search(r'\{\s*".*"\s*:\s*.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception:
            pass
            
    return {
        "description": "Check out this incredible breakdown! Hit subscribe for daily clips and hacks.",
        "hashtags": ["#viral", "#shorts", "#trending", "#fyp", "#contentcreator"],
        "tags": "clips, shorts, trending, highlights, viral",
        "pinned_comment": "What did you think of this? Drop a comment below! 👇"
    }

async def generate_hooks(clip_transcript_text):
    """
    Generate alternative hook suggestions.
    """
    model = await select_best_model()
    prompt = f"""
Provide 3 alternative viral hook ideas for the beginning of this clip.
A hook is a 3-second opening sentence that stops scroll.

Transcript snippet:
"{clip_transcript_text}"

Output format:
Return ONLY a JSON list of strings:
["Hook 1", "Hook 2", "Hook 3"]
"""
    response_text = await query_ollama(prompt, model=model)
    if response_text:
        try:
            json_match = re.search(r'\[\s*".*"\s*\]', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception:
            pass
            
    return [
        "This is why everything you knew was wrong...",
        "I was shocked when I found this out...",
        "If you do this one thing, you win instantly..."
    ]
