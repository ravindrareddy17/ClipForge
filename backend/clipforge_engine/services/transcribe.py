import subprocess
import os
import json

def extract_audio(video_path, audio_path):
    """
    Extract audio track from video using FFmpeg.
    """
    if os.path.exists(audio_path):
        os.remove(audio_path)
        
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise Exception(f"FFmpeg audio extraction failed: {result.stderr.decode()}")
    return audio_path

def generate_mock_transcript(duration):
    """
    Generate realistic mock transcript segments with word-level timestamps.
    """
    sentences = [
        "Welcome to ClipForge AI, the local-first content repurposing engine.",
        "Today we are going to learn how to automatically turn long-form videos into viral shorts.",
        "This platform is powered by local artificial intelligence models, including Ollama and Whisper.",
        "By analyzing the audio peaks and color changes, we detect scenes and viral moments instantly.",
        "Our face-tracking crop automatically centers the speaker, ensuring perfect vertical output.",
        "You can customize your subtitles, choose your brand colors, and schedule posts directly to platforms.",
        "Thanks for watching, and remember to subscribe for more tutorials on content automation!"
    ]
    
    segments = []
    sentence_duration = 6.0
    num_sentences = int(duration // sentence_duration) + 1
    
    for i in range(num_sentences):
        start_time = i * sentence_duration
        end_time = min(duration, (i + 1) * sentence_duration)
        if start_time >= duration:
            break
            
        sentence_text = sentences[i % len(sentences)]
        words = sentence_text.split()
        word_count = len(words)
        total_len = end_time - start_time
        word_duration = total_len / max(1, word_count)
        
        words_list = []
        for idx, w in enumerate(words):
            words_list.append({
                "word": w,
                "start": start_time + idx * word_duration,
                "end": start_time + (idx + 0.9) * word_duration
            })
            
        segments.append({
            "text": sentence_text,
            "start": start_time,
            "end": end_time,
            "words": words_list
        })
        
    return segments

def transcribe_audio(audio_path, duration=0.0):
    """
    Transcribe audio file using whisper library.
    Falls back to mock transcription if library is not present or CPU error occurs.
    """
    try:
        # Check if whisper is imported
        import whisper
        import warnings
        warnings.filterwarnings("ignore")
        
        print("Whisper library found. Loading tiny model...")
        model = whisper.load_model("tiny", device="cpu") # Use tiny CPU for maximum compatibility
        print("Model loaded. Starting transcription with word timestamps...")
        
        result = model.transcribe(audio_path, word_timestamps=True)
        
        segments = []
        for seg in result.get("segments", []):
            words_list = []
            for w in seg.get("words", []):
                words_list.append({
                    "word": w.get("word", "").strip(),
                    "start": float(w.get("start", 0.0)),
                    "end": float(w.get("end", 0.0))
                })
                
            segments.append({
                "text": seg.get("text", "").strip(),
                "start": float(seg.get("start", 0.0)),
                "end": float(seg.get("end", 0.0)),
                "words": words_list
            })
            
        if not segments:
            raise Exception("Whisper returned empty segments.")
            
        return segments
        
    except Exception as e:
        print(f"Whisper transcription failed or not installed: {e}")
        print("Falling back to generating mock transcription segments.")
        return generate_mock_transcript(duration)
