"""
TranscriptNormalizer: Parses and normalizes various transcript formats
into a uniform NormalizedTranscript object.
Supports:
- Official OpenAI Whisper JSON / WhisperX
- Flat word-timestamp arrays
- YouTube Transcript API JSON (start, duration, text)
- SubRip (.srt) and WebVTT (.vtt) text
- Timestamped raw text ([MM:SS] Text)
"""

import re
import json
from typing import Union, List, Dict, Any, Optional

from .models import NormalizedTranscript, TranscriptSegment, WordItem


def parse_timestamp_to_seconds(ts_str: str) -> Optional[float]:
    """Converts strings like '01:23', '01:23.450', '00:01:23,450' into float seconds."""
    ts = ts_str.strip().replace(",", ".")
    parts = ts.split(":")
    try:
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        return float(ts)
    except Exception:
        return None


class TranscriptNormalizer:
    """Normalizes arbitrary transcript representations into a standard NormalizedTranscript."""

    @classmethod
    def normalize(
        cls,
        raw_data: Union[dict, list, str],
        video_id: str = "video_default",
        video_title: str = "Video"
    ) -> NormalizedTranscript:
        if isinstance(raw_data, str):
            # Check if JSON string
            stripped = raw_data.strip()
            if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
                try:
                    parsed = json.loads(stripped)
                    return cls.normalize(parsed, video_id=video_id, video_title=video_title)
                except Exception:
                    pass
            # Parse as SRT / VTT / Timestamped text
            return cls._parse_text_format(raw_data, video_id=video_id, video_title=video_title)

        elif isinstance(raw_data, dict):
            return cls._parse_dict_format(raw_data, video_id=video_id, video_title=video_title)

        elif isinstance(raw_data, list):
            return cls._parse_list_format(raw_data, video_id=video_id, video_title=video_title)

        # Fallback empty
        return NormalizedTranscript(video_id=video_id, title=video_title, duration=0.0)

    @classmethod
    def _parse_dict_format(cls, data: dict, video_id: str, video_title: str) -> NormalizedTranscript:
        vid_id = data.get("video_id", video_id)
        title = data.get("title", data.get("filename", video_title))
        duration = float(data.get("duration", 0.0))

        segments: List[TranscriptSegment] = []

        # Case 1: Standard Whisper JSON with 'segments'
        if "segments" in data and isinstance(data["segments"], list):
            for i, seg in enumerate(data["segments"]):
                st = max(0.0, float(seg.get("start", 0.0)))
                raw_et = float(seg.get("end", st + 1.0))
                et = max(st + 0.5, raw_et)
                text = str(seg.get("text", "")).strip()

                words_list: Optional[List[WordItem]] = None
                if "words" in seg and isinstance(seg["words"], list):
                    words_list = []
                    for w in seg["words"]:
                        w_word = str(w.get("word", "")).strip()
                        w_st = float(w.get("start", st))
                        w_et = float(w.get("end", w_st + 0.3))
                        if w_word:
                            words_list.append(WordItem(word=w_word, start=w_st, end=w_et))

                segments.append(TranscriptSegment(
                    id=seg.get("id", i),
                    start=st,
                    end=et,
                    text=text,
                    words=words_list
                ))

        # Case 2: Root 'words' list
        elif "words" in data and isinstance(data["words"], list):
            segments = cls._group_words_into_segments(data["words"])

        # Compute duration if missing
        if duration <= 0.0 and segments:
            duration = max(s.end for s in segments)

        full_text = " ".join(s.text for s in segments if s.text)
        if not full_text and "text" in data:
            full_text = str(data["text"]).strip()

        return NormalizedTranscript(
            video_id=vid_id,
            title=title,
            duration=round(duration, 2),
            segments=segments,
            full_text=full_text
        )

    @classmethod
    def _parse_list_format(cls, items: list, video_id: str, video_title: str) -> NormalizedTranscript:
        if not items:
            return NormalizedTranscript(video_id=video_id, title=video_title, duration=0.0)

        first = items[0]
        # Check if list of words
        if isinstance(first, dict) and "word" in first and "start" in first:
            segments = cls._group_words_into_segments(items)
        else:
            # List of segments or YouTube transcript dicts
            segments = []
            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                st = max(0.0, float(item.get("start", 0.0)))
                # YouTube transcript format has 'duration' instead of 'end'
                if "end" in item:
                    raw_et = float(item.get("end", st + 1.0))
                    et = max(st + 0.5, raw_et)
                elif "duration" in item:
                    et = st + max(0.5, float(item.get("duration", 1.0)))
                else:
                    et = st + 2.0
                text = str(item.get("text", "")).strip()
                segments.append(TranscriptSegment(id=item.get("id", i), start=st, end=et, text=text))

        duration = max((s.end for s in segments), default=0.0)
        full_text = " ".join(s.text for s in segments if s.text)

        return NormalizedTranscript(
            video_id=video_id,
            title=video_title,
            duration=round(duration, 2),
            segments=segments,
            full_text=full_text
        )

    @classmethod
    def _parse_text_format(cls, text: str, video_id: str, video_title: str) -> NormalizedTranscript:
        """Parses SRT, VTT, or timestamped plain text."""
        segments: List[TranscriptSegment] = []

        # Check for SRT / VTT timestamps: 00:01:20.000 --> 00:01:25.000
        srt_pattern = re.compile(
            r"(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\s*-->\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)",
            re.MULTILINE
        )
        matches = list(srt_pattern.finditer(text))

        if matches:
            for idx, match in enumerate(matches):
                st_sec = max(0.0, parse_timestamp_to_seconds(match.group(1)) or 0.0)
                raw_et_sec = parse_timestamp_to_seconds(match.group(2)) or (st_sec + 2.0)
                et_sec = max(st_sec + 0.5, raw_et_sec)
                # Text between current match end and next match start (or line boundaries)
                content_start = match.end()
                content_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
                sub_text = text[content_start:content_end]
                # Clean index numbers and empty lines
                cleaned_lines = [
                    line.strip() for line in sub_text.splitlines()
                    if line.strip() and not line.strip().isdigit() and "WEBVTT" not in line
                ]
                seg_text = " ".join(cleaned_lines)
                if seg_text:
                    segments.append(TranscriptSegment(id=idx, start=st_sec, end=et_sec, text=seg_text))
        else:
            # Check for bracketed timestamps: [01:23] Text or (01:23) Text
            bracket_pattern = re.compile(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*?)(?=\[\d{1,2}:\d{2}|\Z)", re.DOTALL)
            bracket_matches = list(bracket_pattern.finditer(text))

            if bracket_matches:
                for idx, bm in enumerate(bracket_matches):
                    st_sec = parse_timestamp_to_seconds(bm.group(1)) or 0.0
                    seg_text = bm.group(2).strip()
                    # Next start or +10 seconds
                    if idx + 1 < len(bracket_matches):
                        next_st = parse_timestamp_to_seconds(bracket_matches[idx + 1].group(1)) or (st_sec + 5.0)
                        et_sec = max(st_sec + 1.0, next_st)
                    else:
                        et_sec = st_sec + 10.0
                    segments.append(TranscriptSegment(id=idx, start=st_sec, end=et_sec, text=seg_text))
            else:
                # Plain unannotated text
                clean = text.strip()
                if clean:
                    segments.append(TranscriptSegment(id=0, start=0.0, end=60.0, text=clean))

        duration = max((s.end for s in segments), default=0.0)
        full_text = " ".join(s.text for s in segments if s.text)

        return NormalizedTranscript(
            video_id=video_id,
            title=video_title,
            duration=round(duration, 2),
            segments=segments,
            full_text=full_text
        )

    @classmethod
    def _group_words_into_segments(cls, words: list, words_per_segment: int = 25) -> List[TranscriptSegment]:
        segments: List[TranscriptSegment] = []
        current_words: List[WordItem] = []

        for w in words:
            if not isinstance(w, dict):
                continue
            word_str = str(w.get("word", "")).strip()
            if not word_str:
                continue
            st = float(w.get("start", 0.0))
            et = float(w.get("end", st + 0.3))
            current_words.append(WordItem(word=word_str, start=st, end=et))

            if len(current_words) >= words_per_segment:
                seg_text = " ".join(cw.word for cw in current_words)
                segments.append(TranscriptSegment(
                    id=len(segments),
                    start=current_words[0].start,
                    end=current_words[-1].end,
                    text=seg_text,
                    words=list(current_words)
                ))
                current_words = []

        if current_words:
            seg_text = " ".join(cw.word for cw in current_words)
            segments.append(TranscriptSegment(
                id=len(segments),
                start=current_words[0].start,
                end=current_words[-1].end,
                text=seg_text,
                words=list(current_words)
            ))

        return segments
