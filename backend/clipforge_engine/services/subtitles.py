import os

def hex_to_ass_color(hex_color):
    """
    Convert standard #RRGGBB or RRGGBB hex color to ASS format &H00BBGGRR&
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return "&H00FFFFFF&" # Default white
    r = hex_color[0:2]
    g = hex_color[2:4]
    b = hex_color[4:6]
    return f"&H00{b}{g}{r}&"

def format_ass_time(seconds):
    """
    Format seconds (float) into ASS timestamp format: H:MM:SS.cs (centiseconds)
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds % 1) * 100))
    if cs == 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_ass_file(words, output_path, style_config=None):
    """
    Generate an ASS subtitle file from a list of words with word-by-word highlights.
    
    words: list of dicts with {"word": str, "start": float, "end": float}
    style_config: dict containing font_family, font_size, primary_color, accent_color, position
    """
    if style_config is None:
        style_config = {}
        
    font_name = style_config.get("font_family", "Montserrat")
    font_size = style_config.get("font_size", 28)
    primary_color = hex_to_ass_color(style_config.get("primary_color", "#FFFFFF")) # White
    accent_color = hex_to_ass_color(style_config.get("accent_color", "#00FFFF")) # Yellow/Cyan
    outline_color = hex_to_ass_color(style_config.get("outline_color", "#000000")) # Black
    
    # MarginV controls vertical position. 10 is bottom, 100+ is higher.
    # For vertical 9:16 content, middle height is best (e.g. margin_v = 140)
    margin_v = style_config.get("margin_v", 140)
    
    # ASS Header
    ass_content = f"""[Script Info]
Title: ClipForge AI Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 640
PlayResY: 1138

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},{accent_color},{outline_color},&H00000000&,-1,0,0,0,100,100,0,0,1,3,1,5,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    if not words:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
        return
        
    # Group words into lines/phrases (max 3 words per phrase for quick reading)
    phrases = []
    current_phrase = []
    
    for word_info in words:
        current_phrase.append(word_info)
        # Check if we should end the phrase (punctuation or max length)
        word_text = word_info["word"].strip()
        has_punctuation = any(char in word_text for char in [".", ",", "!", "?", ";"])
        
        if len(current_phrase) >= 3 or has_punctuation:
            phrases.append(current_phrase)
            current_phrase = []
            
    if current_phrase:
        phrases.append(current_phrase)
        
    # Generate Dialogue lines
    for phrase in phrases:
        phrase_start = phrase[0]["start"]
        phrase_end = phrase[-1]["end"]
        
        # We will create sub-intervals for each word in the phrase
        for i, active_word_info in enumerate(phrase):
            word_start = active_word_info["start"]
            
            # Sub-interval end is the start of the next word, or the end of the phrase
            if i < len(phrase) - 1:
                word_end = phrase[i + 1]["start"]
            else:
                word_end = phrase_end
                
            # Fallback if timings are overlapping or zero
            if word_end <= word_start:
                word_end = word_start + 0.1
                
            # Build text highlighting the active word
            formatted_words = []
            for j, w in enumerate(phrase):
                clean_word = w["word"].strip()
                if j == i:
                    # Color it in the accent color
                    formatted_words.append(f"{{\\c{accent_color}}}{clean_word}{{\\c{primary_color}}}")
                else:
                    formatted_words.append(clean_word)
                    
            text_line = " ".join(formatted_words)
            
            start_str = format_ass_time(word_start)
            end_str = format_ass_time(word_end)
            
            ass_content += f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text_line}\n"
            
    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
        
    return output_path
