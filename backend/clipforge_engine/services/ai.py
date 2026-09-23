import httpx
import json
import re
from clipforge_engine.db import get_settings

def get_ollama_url():
    try:
        s = get_settings()
        return s.get("ollama_url") or "http://localhost:11434"
    except Exception:
        return "http://localhost:11434"

async def query_ollama(prompt, model="llama3:latest", system_prompt=None):
    """
    Query multi-provider LLM instance (Groq Cloud / Gemini / Local Ollama).
    """
    try:
        from clipforge_engine.llm_client import async_call_llm
        res = await async_call_llm(prompt=prompt, system=system_prompt, model=model)
        if res and res.strip():
            return res.strip()
    except Exception as e:
        print(f"Unified LLM query error: {e}")

    # Fallback to local Ollama directly
    base_url = get_ollama_url()
    url = f"{base_url}/api/generate"
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
        headers = {"ngrok-skip-browser-warning": "1"}
        async with httpx.AsyncClient(timeout=35.0, headers=headers) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                print(f"Ollama returned status {response.status_code}: {response.text}")
                return None
    except Exception as e:
        print(f"Ollama connection error (falling back to heuristics): {e}")
        return None

async def select_best_model():
    """
    Select available model from Ollama, prioritizing fast and accurate local models (qwen2.5:3b).
    """
    base_url = get_ollama_url()
    try:
        headers = {"ngrok-skip-browser-warning": "1"}
        async with httpx.AsyncClient(timeout=4.0, headers=headers) as client:
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                for preferred in ["qwen2.5:3b", "qwen3:4b", "llama3:latest", "llama3"]:
                    if preferred in models:
                        return preferred
                if models:
                    return models[0]
    except Exception:
        pass
    return "qwen2.5:3b"

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
            
    # Intelligent heuristic fallback if Ollama failed or returned no clips
    if not clips:
        print("Using intelligent anchor-based hook detection across video.")
        hook_triggers = [
            "how", "why", "what", "secret", "imagine", "universe", "billion",
            "incredible", "never", "always", "remember", "truth", "insane",
            "look", "discover", "first", "million", "massive", "danger"
        ]
        
        # 1. Score each segment as a potential hook starting point
        candidate_indices = []
        for idx, seg in enumerate(transcript_segments):
            text = seg.get("text", "").strip()
            text_lower = text.lower()
            score = 50
            
            # Boost for question or exclamation
            if "?" in text or "!" in text:
                score += 20
            # Boost for hook trigger words
            for ht in hook_triggers:
                if ht in text_lower:
                    score += 15
            # Boost for good sentence length
            if 6 <= len(text.split()) <= 25:
                score += 10
                
            candidate_indices.append((score, idx))
            
        # Sort candidates by hook score descending
        candidate_indices.sort(key=lambda x: x[0], reverse=True)
        
        # 2. Pick top diverse hook anchors spread throughout the video
        min_separation = max(45.0, min(90.0, duration_seconds / 6.0)) if duration_seconds > 60.0 else 20.0
        selected_starts = []
        for cand_score, cand_idx in candidate_indices:
            cand_start = transcript_segments[cand_idx]["start"]
            # Ensure not too close to the end of the video
            if cand_start + 18.0 > duration_seconds and duration_seconds > 30.0:
                continue
            # Ensure no overlapping start with existing clips
            if not any(abs(cand_start - s) < min_separation for s in selected_starts):
                selected_starts.append(cand_start)
                
                # Expand from cand_idx forward until natural pause or duration between 20s and 45s
                clip_segs = []
                cur_dur = 0.0
                j = cand_idx
                while j < len(transcript_segments) and cur_dur < 45.0:
                    s_item = transcript_segments[j]
                    s_len = s_item["end"] - s_item["start"]
                    clip_segs.append(s_item)
                    cur_dur += s_len
                    # Natural break on punctuation if reached good duration
                    if cur_dur >= 22.0 and any(s_item.get("text", "").strip().endswith(p) for p in [".", "?", "!"]):
                        break
                    if cur_dur >= 40.0:
                        break
                    j += 1
                    
                if not clip_segs:
                    continue
                    
                start_t = clip_segs[0]["start"]
                end_t = clip_segs[-1]["end"]
                
                # Compile word timestamps
                words_in_clip = []
                for s in clip_segs:
                    if "words" in s and s["words"]:
                        words_in_clip.extend(s["words"])
                    else:
                        w_list = s["text"].split()
                        w_dur = (s["end"] - s["start"]) / max(1, len(w_list))
                        for w_idx, w in enumerate(w_list):
                            words_in_clip.append({
                                "word": w,
                                "start": s["start"] + w_idx * w_dur,
                                "end": s["start"] + (w_idx + 1) * w_dur
                            })
                            
                # Generate a clean, punchy title from key words
                hook_sentence = clip_segs[0]["text"].strip()
                clean_words = [w for w in re.sub(r'[^\w\s]', '', hook_sentence).split() if len(w) > 2][:6]
                if clean_words:
                    title = " ".join(clean_words).title()
                else:
                    title = f"Viral Moment ({int(start_t)}s - {int(end_t)}s)"
                    
                virality = min(98, max(78, cand_score + 12))
                
                clips.append({
                    "title": title,
                    "start_time": start_t,
                    "end_time": end_t,
                    "duration": end_t - start_t,
                    "score": virality,
                    "explanation": f"High-retention segment: \"{hook_sentence[:70]}...\"",
                    "hook": hook_sentence[:45],
                    "words": words_in_clip
                })
                
                if len(clips) >= 5:
                    break
                    
        # Fallback if no candidate anchors matched
        if not clips and transcript_segments:
            seg = transcript_segments[0]
            clips.append({
                "title": f"Hook: \"{seg['text'][:30]}...\"",
                "start_time": seg["start"],
                "end_time": min(duration_seconds, seg["start"] + 35.0),
                "duration": min(duration_seconds - seg["start"], 35.0),
                "score": 85,
                "explanation": "Opening hook segment extracted from video introduction.",
                "hook": seg["text"][:40],
                "words": []
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
