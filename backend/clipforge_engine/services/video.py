import subprocess
import json
import os
import cv2
import numpy as np
import urllib.request

def get_video_metadata(video_path):
    """
    Get video metadata (duration, width, height, fps) using ffprobe.
    """
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-show_entries", "format=duration:stream=width,height,r_frame_rate", 
        "-of", "json", 
        video_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(result.stdout)
        
        duration = float(data.get("format", {}).get("duration", 0.0))
        
        streams = data.get("streams", [])
        width, height, fps = 0, 0, 0.0
        if streams:
            stream = streams[0]
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))
            fps_str = stream.get("r_frame_rate", "30/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den) if float(den) > 0 else 30.0
            else:
                fps = float(fps_str)
                
        return {
            "duration": duration,
            "width": width,
            "height": height,
            "fps": fps
        }
    except Exception as e:
        print(f"Error reading metadata with ffprobe: {e}")
        # Fallback to OpenCV
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0.0
            cap.release()
            return {
                "duration": duration,
                "width": width,
                "height": height,
                "fps": fps
            }
        return {"duration": 0.0, "width": 0, "height": 0, "fps": 0.0}

def detect_scenes(video_path, threshold=0.6, min_scene_len=2.0):
    """
    Perform fast scene detection using HSV histogram differences.
    Reads frames at regular intervals to be extremely fast.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return [0.0]
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Sample every N frames to speed up (e.g. 5 frames)
    step = 5
    prev_hist = None
    scene_changes = [0.0]
    
    for frame_idx in range(0, total_frames, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break
            
        # Convert to HSV and calculate color histogram
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [8, 8], [0, 180, 0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        
        if prev_hist is not None:
            # Compare histograms using correlation
            diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
            # Correlation closer to 1 means identical, drops mean scene change
            if diff < threshold:
                timestamp = frame_idx / fps
                if timestamp - scene_changes[-1] >= min_scene_len:
                    scene_changes.append(timestamp)
                    
        prev_hist = hist
        
    cap.release()
    return scene_changes

def ensure_face_cascade():
    """
    Ensure the face cascade XML file is downloaded and cached in the data directory.
    """
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "assets")
    os.makedirs(assets_dir, exist_ok=True)
    xml_path = os.path.join(assets_dir, "haarcascade_frontalface_default.xml")
    
    if os.path.exists(xml_path) and os.path.getsize(xml_path) > 10000:
        return xml_path
        
    url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
    print(f"Downloading Haar cascade face detector XML from {url}...")
    try:
        urllib.request.urlretrieve(url, xml_path)
        print("Download successful!")
        return xml_path
    except Exception as e:
        print(f"WARNING: Failed to download face cascade XML: {e}")
        # Delete corrupt file if any
        if os.path.exists(xml_path):
            try:
                os.remove(xml_path)
            except Exception:
                pass
        return None

def get_crop_coordinates(video_path, start_time, end_time):
    """
    Analyze faces in the video segment to determine the speaker's horizontal position.
    Returns the ideal crop_x to crop the video to 9:16 vertical.
    """
    meta = get_video_metadata(video_path)
    width = meta["width"]
    height = meta["height"]
    fps = meta["fps"]
    
    if width <= 0 or height <= 0:
        return 0
        
    # Calculate crop width for 9:16 target aspect ratio
    crop_w = int(height * 9 / 16)
    # Ensure crop width is even for FFmpeg
    if crop_w % 2 != 0:
        crop_w -= 1
        
    # Default center crop position
    default_x = max(0, int((width - crop_w) / 2))
    
    # Check if video is already vertical or square
    if width / height <= 1.0:
        return 0 # No horizontal cropping needed
        
    # Detect faces
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return default_x
        
    # Setup Haar cascade face detector
    try:
        cascade_path = ensure_face_cascade()
        if cascade_path is None:
            raise Exception("Haar cascade XML not available (offline or download failed)")
        face_cascade = cv2.CascadeClassifier(cascade_path)
        if face_cascade.empty():
            raise Exception("Haar cascade loaded but classifier is empty")
    except Exception as e:
        print(f"Haar Cascade loading failed, falling back to center-crop: {e}")
        cap.release()
        return default_x
        
    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)
    
    # Sample 1 frame per second to speed up face detection
    sample_interval = max(1, int(fps))
    face_x_coords = []
    
    for frame_idx in range(start_frame, end_frame, sample_interval):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Downscale gray image to speed up face detection
        scale = 0.5
        small_gray = cv2.resize(gray, (0, 0), fx=scale, fy=scale)
        
        faces = face_cascade.detectMultiScale(small_gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30))
        
        if len(faces) > 0:
            # Get the largest face
            largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
            fx, fy, fw, fh = largest_face
            # Convert back to original resolution
            face_center_x = int((fx + fw / 2) / scale)
            face_x_coords.append(face_center_x)
            
    cap.release()
    
    if not face_x_coords:
        return default_x
        
    # Calculate average face X coordinate
    avg_face_x = sum(face_x_coords) / len(face_x_coords)
    
    # Calculate crop left position (x)
    crop_x = int(avg_face_x - crop_w / 2)
    # Clamp within video boundaries
    crop_x = max(0, min(width - crop_w, crop_x))
    # Ensure crop_x is even for FFmpeg
    if crop_x % 2 != 0:
        crop_x = max(0, crop_x - 1)
        
    return crop_x

def render_clip(input_path, output_path, start_time, end_time, crop_x=None, ass_subtitle_path=None):
    """
    Crop the video to 9:16 and burn in subtitles using FFmpeg.
    """
    meta = get_video_metadata(input_path)
    width = meta["width"]
    height = meta["height"]
    
    crop_w = int(height * 9 / 16)
    if crop_w % 2 != 0:
        crop_w -= 1
        
    if crop_x is None:
        crop_x = max(0, int((width - crop_w) / 2))
        
    # Build filtergraph
    filters = []
    
    # Only crop if the original video is landscape (wider than 9:16)
    if width / height > 9/16:
        filters.append(f"crop={crop_w}:{height}:{crop_x}:0")
    else:
        # Scale to standard vertical aspect ratio if needed
        filters.append(f"scale={crop_w}:{height}")
        
    if ass_subtitle_path:
        # On Windows, FFmpeg subtitles filter needs escaped backslashes and a double colon for drive letters
        # e.g., C\:/path/to/sub.ass
        abs_ass = os.path.abspath(ass_subtitle_path)
        escaped_ass = abs_ass.replace("\\", "/").replace(":", "\\:")
        filters.append(f"subtitles='{escaped_ass}'")
        
    filter_str = ",".join(filters)
    
    cmd = [
        "ffmpeg",
        "-y", # Overwrite output
        "-ss", f"{start_time:.3f}",
        "-to", f"{end_time:.3f}",
        "-i", input_path,
        "-vf", filter_str,
        "-c:v", "libx264",
        "-crf", "20",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]
    
    print(f"Running FFmpeg: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"FFmpeg failed with return code {result.returncode}")
        print(f"Stderr: {result.stderr}")
        raise Exception(f"FFmpeg error: {result.stderr}")
        
    return True
