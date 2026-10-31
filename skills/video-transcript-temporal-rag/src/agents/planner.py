"""
Agent 1: QueryPlannerAgent
Normalizes informal queries, classifies query intent, extracts temporal constraints,
and plans targeted sub-queries.
"""

import re
from typing import Dict, Any, Optional

from .base import BaseAgent
from ..models import VideoQAState, QueryPlan
from ..normalizer import parse_timestamp_to_seconds


def normalize_query(query: str) -> str:
    """
    Normalizes informal, short, or fragmented queries before intent classification.
    E.g. 'what video about' -> 'What is this video about?'
    """
    if not query:
        return ""
    q = query.strip()
    q_clean = re.sub(r"[?!.,;]+$", "", q).strip().lower()

    # Exact mappings for informal video-level summary variants
    informal_summary_map = {
        "what video about": "What is this video about?",
        "what is video about": "What is this video about?",
        "what this video about": "What is this video about?",
        "what the video about": "What is the video about?",
        "tell me about this video": "Tell me about this video.",
        "tell about video": "Tell me about this video.",
        "tell me about video": "Tell me about this video.",
        "summarize this video": "Summarize this video.",
        "summarize video": "Summarize this video.",
        "summary of video": "Summarize this video.",
        "video summary": "Summarize this video.",
        "give me a summary": "Give me a summary of this video.",
        "give summary": "Give me a summary of this video.",
        "what are the main points": "What are the main points of this video?",
        "what are main points": "What are the main points of this video?",
        "main points": "What are the main points of this video?",
        "main points?": "What are the main points of this video?",
        "explain the video": "Explain the video.",
        "explain video": "Explain the video.",
        "give me an overview": "Give me an overview of this video.",
        "overview": "Give me an overview of this video.",
        "what does this video discuss": "What does this video discuss?",
        "what is discussed in this video": "What is discussed in this video?",
        "what discuss in video": "What does this video discuss?",
        "what is discussed": "What is discussed in this video?",
        "what happens in this video": "What happens in this video?",
        "about video": "What is this video about?",
        "video about": "What is this video about?"
    }

    if q_clean in informal_summary_map:
        return informal_summary_map[q_clean]

    # Regex normalization for short/fragmented queries missing copulas or articles
    if re.fullmatch(r"what\s+(?:the\s+|this\s+)?video\s+(?:is\s+)?about", q_clean):
        return "What is this video about?"
    if re.fullmatch(r"summar(?:ize|y)\s+(?:the\s+|this\s+)?video", q_clean):
        return "Summarize this video."
    if re.fullmatch(r"explain\s+(?:the\s+|this\s+)?video", q_clean):
        return "Explain the video."
    if re.fullmatch(r"main\s+points?", q_clean):
        return "What are the main points of this video?"

    return q


class QueryPlannerAgent(BaseAgent):
    """Agent 1: Plans query routing, sub-queries, and intent taxonomy."""

    def __init__(self):
        super().__init__(name="QueryPlannerAgent")

    def run(self, state: VideoQAState) -> VideoQAState:
        normalized_q = normalize_query(state.query)
        state.normalized_query = normalized_q
        q_lower = normalized_q.lower()

        intent = "FACTUAL_LOOKUP"
        sub_queries = [normalized_q]
        temporal_marker = None
        target_timestamp = None

        # 1. Timestamp Search
        ts_match = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?)", normalized_q)
        if ts_match:
            intent = "TIMESTAMP_SEARCH"
            target_timestamp = parse_timestamp_to_seconds(ts_match.group(1))

        # 2. Whole Video Summary Intent
        summary_triggers = [
            "what is this video about",
            "what video about",
            "what is the video about",
            "what this video about",
            "tell me about this video",
            "summarize this video",
            "give me a summary",
            "what are the main points",
            "what are main points",
            "explain the video",
            "give me an overview",
            "what does this video discuss",
            "what is discussed in this video",
            "what is discussed",
            "main points",
            "summarize",
            "summary",
            "overview",
            "main ideas",
            "whole video",
            "entire video",
            "video about"
        ]
        summary_regex = r"\b(what\s+(is\s+)?(this\s+|the\s+)?video\s+about|tell\s+me\s+about\s+(this\s+|the\s+)?video|summarize|summary|overview|main\s+points?|explain\s+(this\s+|the\s+)?video|what\s+does\s+(this\s+|the\s+)?video\s+discuss|what\s+is\s+discussed)\b"

        if any(trig in q_lower for trig in summary_triggers) or re.search(summary_regex, q_lower):
            intent = "WHOLE_VIDEO_SUMMARY"
            sub_queries = [
                normalized_q,
                "video opening introduction overview",
                "conclusion final thoughts closing"
            ]
        elif any(k in q_lower for k in ["compare", "difference between", "beginning and end", "start and finish", "versus"]):
            intent = "COMPARATIVE_ANALYSIS"
            sub_queries = [
                normalized_q,
                "beginning start opening early",
                "ending conclusion final last"
            ]
        elif any(k in q_lower for k in ["after", "following", "next", "then"]):
            intent = "TIMELINE_RECONSTRUCTION"
            temporal_marker = "after"
            match = re.search(r"after\s+(passing\s+|the\s+)?([a-zA-Z0-9\s]+?)(?:\?|$)", normalized_q, re.IGNORECASE)
            if match:
                sub_queries = [normalized_q, match.group(2).strip()]
        elif any(k in q_lower for k in ["before", "prior to", "earlier"]):
            intent = "TIMELINE_RECONSTRUCTION"
            temporal_marker = "before"
        elif any(k in q_lower for k in ["when", "at what time", "timestamp", "which minute"]):
            intent = "TIMESTAMP_SEARCH"

        plan = QueryPlan(
            intent=intent,
            sub_queries=sub_queries,
            temporal_marker=temporal_marker,
            target_timestamp=target_timestamp,
            original_query=state.query,
            normalized_query=normalized_q
        )
        state.plan = plan
        state.log(f"[{self.name}] Query normalized to '{normalized_q}'. Intent classified as: {intent}.")
        return state
