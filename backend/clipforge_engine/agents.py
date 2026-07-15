import os
import json
import re
import requests
from datetime import datetime

def get_ollama_base_url():
    try:
        from clipforge_engine.db import get_settings
        settings = get_settings()
        return settings.get("ollama_url", "http://localhost:11434")
    except Exception:
        return "http://localhost:11434"

def call_ollama_completion(prompt, system_instruction=None, model="qwen2.5:3b"):
    """
    Calls local Ollama API to get simple text completion responses.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    if system_instruction:
        payload["system"] = system_instruction
        
    try:
        base_url = get_ollama_base_url()
        headers = {"ngrok-skip-browser-warning": "1"}
        resp = requests.post(f"{base_url}/api/generate", json=payload, headers=headers, timeout=40)
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"Ollama complete agent call failed: {e}")
    return ""

def call_ollama_json(prompt, system_instruction=None, model="qwen2.5:3b"):
    """
    Calls local Ollama requesting JSON outputs.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    if system_instruction:
        payload["system"] = system_instruction
        
    try:
        base_url = get_ollama_base_url()
        headers = {"ngrok-skip-browser-warning": "1"}
        resp = requests.post(f"{base_url}/api/generate", json=payload, headers=headers, timeout=40)
        if resp.status_code == 200:
            raw = resp.json().get("response", "").strip()
            # Clean markdown JSON wrapping if present
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            raw = raw.strip()
            try:
                return json.loads(raw)
            except Exception:
                # Regex match fallback
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
    except Exception as e:
        print(f"Ollama JSON agent call failed: {e}")
    return {}

# 1. SUMMARY AGENT
def run_summary_agent(transcript_text, model="qwen2.5:3b"):
    """
    Generates structured summaries, key topics, quotes, timeline, action items, and main ideas.
    """
    prompt = (
        "Generate a complete analytical summary of the following transcript. "
        "Your response MUST be a JSON object containing these exact fields:\n"
        "- 'executive_summary': A clear paragraph outlining the video core message.\n"
        "- 'key_topics': A list of string topics covered.\n"
        "- 'important_quotes': A list of key memorable quotes.\n"
        "- 'timeline': A list of dicts with keys 'time_stamp' (format MM:SS) and 'event_name' describing segment transitions.\n"
        "- 'action_items': A list of key takeaways or actions.\n"
        "- 'main_ideas': A list of secondary concepts discussed.\n\n"
        f"Transcript text:\n{transcript_text[:6000]}"
    )
    
    res = call_ollama_json(
        prompt, 
        system_instruction="You are a professional video summarizing agent. You only respond in JSON.", 
        model=model
    )
    
    # Fallbacks if fields are missing
    if not res:
        res = {
            "executive_summary": "Auto summary generated from local Whisper transcript.",
            "key_topics": ["General Discussion"],
            "important_quotes": [],
            "timeline": [{"time_stamp": "00:00", "event_name": "Video Introduction"}],
            "action_items": ["Review transcript details"],
            "main_ideas": ["Discussion context overview"]
        }
    return res

# 2. TOPIC DETECTOR
def run_topic_detector(transcript_segments, model="qwen2.5:3b"):
    """
    Scans transcript segments and builds list of topic boundaries.
    """
    # Sample text with timestamps
    sample_lines = []
    for s in transcript_segments[:100]: # Limit to prevent context overload
        start_t = s.get("start", 0.0)
        text = s.get("text", "")
        sample_lines.append(f"[{start_t:.1f}s] {text}")
    sample_text = "\n".join(sample_lines)
    
    prompt = (
        "Determine the top-level topics or chapters in this transcript. "
        "Return a JSON object containing a 'topics' list, where each topic is a dict containing:\n"
        "- 'name': Short topic title.\n"
        "- 'start_time': Numeric start timestamp (in seconds).\n"
        "- 'end_time': Numeric end timestamp (in seconds).\n"
        "- 'summary': Brief description of this topic segment.\n\n"
        f"Transcripts:\n{sample_text}"
    )
    
    res = call_ollama_json(
        prompt,
        system_instruction="You are an expert video segmentation agent. Return only JSON.",
        model=model
    )
    return res.get("topics", [])

# 3. KEYWORD & ENTITY EXTRACTOR
def run_entity_extractor(transcript_text, model="qwen2.5:3b"):
    """
    Extracts named entities sorted into People, Companies, Technologies, Products, and Organizations.
    """
    prompt = (
        "Extract named entities from this text. Group them into distinct categories. "
        "Return a JSON object containing these lists:\n"
        "- 'People': Names of individuals.\n"
        "- 'Companies': Business names.\n"
        "- 'Technologies': Technical concepts or software.\n"
        "- 'Products': Specific brands or tools.\n"
        "- 'Organizations': Group names, agencies, or institutes.\n\n"
        f"Transcript:\n{transcript_text[:4000]}"
    )
    
    res = call_ollama_json(
        prompt,
        system_instruction="You are an expert NLP entity extraction agent. Return only JSON lists.",
        model=model
    )
    return res

# 4. KNOWLEDGE GRAPH BUILDER
def run_knowledge_graph_agent(transcript_text, model="qwen2.5:3b"):
    """
    Builds relationships (source -> target) from the transcript details.
    """
    prompt = (
        "Analyze the transcript and discover relationships between entities. "
        "Return a JSON object containing a 'relationships' list, where each relationship is a dict containing:\n"
        "- 'source': Entity A.\n"
        "- 'target': Entity B.\n"
        "- 'relationship': Action or relation linking them (e.g. 'founded', 'announced', 'part of').\n"
        "- 'weight': Float value from 0.5 to 2.0 estimating strength/importance of connection.\n\n"
        f"Transcript text:\n{transcript_text[:4000]}"
    )
    
    res = call_ollama_json(
        prompt,
        system_instruction="You are an expert Knowledge Graph agent. Return only JSON lists of semantic links.",
        model=model
    )
    return res.get("relationships", [])

# 5. SEO AGENT
def run_seo_agent(transcript_summary, model="qwen2.5:3b"):
    """
    Generates video titles, metadata description, and hashtags.
    """
    prompt = (
        "Generate a list of titles, a descriptive metadata block, and hashtags to optimize this video clip. "
        "Return a JSON object with these fields:\n"
        "- 'titles': A list of 5 clickable title hooks.\n"
        "- 'description': An optimized SEO paragraph descriptions.\n"
        "- 'hashtags': A list of 10 relevant hashtags.\n\n"
        f"Video summary context:\n{transcript_summary}"
    )
    
    res = call_ollama_json(
        prompt,
        system_instruction="You are an expert SEO Optimization Agent. Return only JSON configurations.",
        model=model
    )
    if not res:
        res = {
            "titles": ["Mindblowing Clip", "Must-Watch Moment"],
            "description": "Optimized description generated locally by ClipForge AI.",
            "hashtags": ["#shorts", "#trending"]
        }
    return res

# 6. THUMBNAIL AGENT
def run_thumbnail_agent(transcript_summary, model="qwen2.5:3b"):
    """
    Generates text and background overlays suggestions for video thumbnail hooks.
    """
    prompt = (
        "Suggest text overlays and style recommendations for visual YouTube thumbnails. "
        "Return a JSON object with these fields:\n"
        "- 'overlay_text': A list of 3 short, punchy 3-4 word titles suitable for thumbnails.\n"
        "- 'style_recommendation': A brief description of visual placement, colors, and layout hooks.\n\n"
        f"Video Context:\n{transcript_summary}"
    )
    
    res = call_ollama_json(
        prompt,
        system_instruction="You are a graphic design thumbnail optimizer agent. Return only JSON recommendations.",
        model=model
    )
    if not res:
        res = {
            "overlay_text": ["WAIT FOR IT", "DO NOT MISS"],
            "style_recommendation": "Use bright contrasting colors like red and yellow."
        }
    return res

# 7. CLIP AGENT
def run_clip_agent(segments, model="qwen2.5:3b"):
    """
    Scans transcripts with timestamps and identifies viral highlights.
    """
    # Sample text with timestamps
    sample_lines = []
    for s in segments[:120]:
        sample_lines.append(f"[{s.get('start', 0.0):.1f}s - {s.get('end', 0.0):.1f}s]: {s.get('text', '')}")
    sample_text = "\n".join(sample_lines)

    prompt = (
        "Analyze the following video transcript with timestamps. "
        "Find the most engaging, viral segments (duration 15-60 seconds) suitable for YouTube Shorts or Reels. "
        "Return a JSON object containing a 'clips' list. Each clip is a dict containing:\n"
        "- 'title': An engaging, clicky title for the Short.\n"
        "- 'start_time': Numeric start timestamp (in seconds).\n"
        "- 'end_time': Numeric end timestamp (in seconds).\n"
        "- 'score': A numeric score from 50 to 100 indicating virality potential.\n"
        "- 'explanation': A short sentence explaining why this clip is viral.\n\n"
        f"Transcript text:\n{sample_text}"
    )
    
    res = call_ollama_json(
        prompt,
        system_instruction="You are a media viral evaluator agent. Return only JSON lists of clip segments.",
        model=model
    )
    return res.get("clips", [])

# 8. SCHEDULER AGENT
def run_scheduler_agent(channel_history_summary, model="qwen2.5:3b"):
    """
    Suggests ideal schedule times slots.
    """
    prompt = (
        "Recommend optimal days of the week and times to publish content to maximize viral views. "
        "Return a JSON object containing a 'slots' list of dicts, with fields:\n"
        "- 'day': Day of week (e.g. 'Monday').\n"
        "- 'time': Time in 24h format (e.g. '18:30').\n"
        "- 'reason': Why this slot is recommended.\n\n"
        f"Channel history overview:\n{channel_history_summary}"
    )
    
    res = call_ollama_json(
        prompt,
        system_instruction="You are a social media scheduler consultant agent. Return only JSON slots.",
        model=model
    )
    return res.get("slots", [])
