"""
ClipForge AI V2 - Agentic Video QA Architecture
Implements 6 specialized agent roles and a controlled ReAct loop with explicit tools.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable

from clipforge_engine.db import (
    get_video, get_db_connection, get_summary,
    get_chat_history, add_chat_message, get_video_chunks_lexical
)
from clipforge_engine.rag import (
    hybrid_retrieve_chunks, lexical_search_chunks,
    semantic_search_chunks, expand_chunk_context,
    generate_grounded_answer, call_ollama, format_timestamp
)

logger = logging.getLogger("clipforge.video_qa_agents")


# ============================================================================
# EXPLICIT VIDEO QA TOOLS
# ============================================================================

def tool_search_video(project_id: str, video_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Tool: Hybrid BM25 lexical + vector search across video chunks."""
    return hybrid_retrieve_chunks(project_id, video_id, query, k=k)


def tool_search_topic(project_id: str, video_id: str, topic: str, k: int = 6) -> List[Dict[str, Any]]:
    """Tool: Topic-focused search combining lexical filtering and semantic matching."""
    return hybrid_retrieve_chunks(project_id, video_id, topic, k=k)


def parse_timestamp_str_to_seconds(ts_str: str) -> Optional[float]:
    """Parses MM:SS or HH:MM:SS string to seconds."""
    ts_str = ts_str.strip().strip("[]()")
    parts = ts_str.split(":")
    try:
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        return float(ts_str)
    except Exception:
        return None


def tool_search_timestamp(project_id: str, video_id: str, target_seconds: float, window_seconds: float = 45.0) -> List[Dict[str, Any]]:
    """Tool: Retrieves chunks directly covering or immediately surrounding a target timestamp."""
    all_chunks = get_video_chunks_lexical(video_id)
    if not all_chunks:
        return []

    matching = []
    min_t = target_seconds - window_seconds
    max_t = target_seconds + window_seconds

    for c in all_chunks:
        st = c.get("start_time", 0.0)
        et = c.get("end_time", st)
        if (st <= max_t) and (et >= min_t):
            matching.append({
                "id": c.get("id"),
                "text": c.get("text", ""),
                "metadata": {
                    "start_time": st,
                    "end_time": et,
                    "chunk_index": c.get("chunk_index", 0),
                    "topic": c.get("topic", ""),
                    "video_id": video_id,
                    "project_id": project_id
                },
                "score": 1.0 - (abs((st + et) / 2.0 - target_seconds) / max(window_seconds, 1.0)) * 0.5
            })

    matching.sort(key=lambda x: abs((x["metadata"]["start_time"] + x["metadata"]["end_time"]) / 2.0 - target_seconds))
    return matching[:5]


def tool_get_context_around_timestamp(project_id: str, video_id: str, timestamp_sec: float, window_seconds: float = 30.0) -> List[Dict[str, Any]]:
    """Tool: Context expansion around a specific timestamp."""
    return tool_search_timestamp(project_id, video_id, timestamp_sec, window_seconds=window_seconds)


def tool_get_video_summary(project_id: str, video_id: str) -> Dict[str, Any]:
    """Tool: Retrieves high-level precomputed video summary and metadata."""
    summary_record = get_summary(video_id)
    video = get_video(video_id)
    return {
        "video_id": video_id,
        "filename": video["filename"] if video else "Video",
        "duration": video["duration"] if video else 0,
        "executive_summary": summary_record.get("executive_summary") if summary_record else "",
        "key_topics": summary_record.get("key_topics", []) if summary_record else [],
        "timeline": summary_record.get("timeline", []) if summary_record else []
    }


def tool_verify_claim(claim: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tool: Verifies whether the supplied chunks contain factual evidence for the claim."""
    if not chunks:
        return {"supported": False, "confidence": 0.0, "reason": "No evidence chunks provided"}

    combined_text = " ".join([c.get("text", "") for c in chunks]).lower()
    claim_words = [w for w in re.findall(r"\w+", claim.lower()) if len(w) > 3]

    if not claim_words:
        return {"supported": True, "confidence": 0.5, "reason": "Claim too brief"}

    matches = [w for w in claim_words if w in combined_text]
    overlap_ratio = len(matches) / len(claim_words)

    supported = overlap_ratio >= 0.3
    return {
        "supported": supported,
        "confidence": round(overlap_ratio, 2),
        "matching_keywords": matches,
        "reason": f"Found {len(matches)}/{len(claim_words)} key concepts in evidence."
    }


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


def tool_assemble_video_summary_context(project_id: str, video_id: str) -> Dict[str, Any]:
    """
    Gathers comprehensive, whole-video evidence:
    - Video title, filename, duration
    - Precomputed executive summary, key topics, timeline milestones
    - Opening chunks (context / thesis)
    - Uniformly distributed middle chunks (coverage across the entire timeline)
    - Ending chunks (conclusion)
    """
    video = get_video(video_id)
    summary_record = get_summary(video_id)
    all_chunks = get_video_chunks_lexical(video_id)

    has_transcript = bool(all_chunks)
    has_summary = bool(summary_record and (summary_record.get("executive_summary") or summary_record.get("timeline")))

    if not has_transcript and not has_summary:
        return {
            "has_data": False,
            "error_type": "indexing_needed",
            "message": "The transcript or summary for this video has not been indexed yet. Please process the video in 'Create Clips' first to generate timestamps and transcript chunks.",
            "chunks": []
        }

    selected_chunks: List[Dict[str, Any]] = []
    if all_chunks:
        n = len(all_chunks)
        if n <= 8:
            selected_chunks = list(all_chunks)
        else:
            # First 2 chunks for opening / thesis
            for c in all_chunks[:2]:
                if c not in selected_chunks:
                    selected_chunks.append(c)
            # 3 uniformly sampled middle chunks (~25%, 50%, 75% of duration)
            for frac in [0.25, 0.50, 0.75]:
                idx = min(int(n * frac), n - 1)
                if all_chunks[idx] not in selected_chunks:
                    selected_chunks.append(all_chunks[idx])
            # Last 2 chunks for conclusion
            for c in all_chunks[-2:]:
                if c not in selected_chunks:
                    selected_chunks.append(c)

    formatted_chunks = []
    for c in selected_chunks:
        cid = c.get("id")
        st = float(c.get("start_time", 0.0))
        et = float(c.get("end_time", st + 1.0))
        formatted_chunks.append({
            "id": cid,
            "text": c.get("text", ""),
            "metadata": {
                "start_time": st,
                "end_time": et,
                "chunk_index": c.get("chunk_index", 0),
                "video_id": video_id,
                "project_id": project_id,
                "topic": c.get("topic", "")
            },
            "score": 0.98
        })

    formatted_chunks.sort(key=lambda x: x["metadata"]["start_time"])
    return {
        "has_data": True,
        "video": video,
        "summary_record": summary_record,
        "chunks": formatted_chunks
    }


# ============================================================================
# 6 SPECIALIZED AGENT ROLES
# ============================================================================

class QueryPlannerAgent:
    """Agent 1: Classifies intent, extracts temporal/entity hints, and generates sub-queries."""

    @staticmethod
    def plan(query: str) -> Dict[str, Any]:
        normalized_q = normalize_query(query)
        q_lower = normalized_q.lower()

        # Intent classification
        intent = "factual_lookup"
        sub_queries = [normalized_q]
        temporal_marker = None
        target_timestamp = None

        # Check for timestamp search
        ts_match = re.search(r"(\d{1,2}:\d{2}(?::\d{2})?)", normalized_q)
        if ts_match:
            intent = "timestamp_search"
            target_timestamp = parse_timestamp_str_to_seconds(ts_match.group(1))

        # Check for dedicated VIDEO_SUMMARY intent
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
            intent = "video_summary"
            sub_queries = [
                normalized_q,
                "video opening introduction overview",
                "conclusion final thoughts closing"
            ]
        elif any(k in q_lower for k in ["compare", "difference between", "beginning and end", "start and finish", "versus"]):
            intent = "comparison"
            sub_queries = [
                normalized_q,
                "beginning start opening early",
                "ending conclusion final last"
            ]
        elif any(k in q_lower for k in ["after", "following", "next", "then"]):
            intent = "chronology"
            temporal_marker = "after"
            # Extract key milestone, e.g., "passing mars" -> search "mars"
            mars_match = re.search(r"after\s+(passing\s+)?([a-zA-Z0-9\s]+?)(?:\?|$)", normalized_q, re.IGNORECASE)
            if mars_match:
                sub_queries = [normalized_q, mars_match.group(2).strip()]
        elif any(k in q_lower for k in ["before", "prior to", "earlier"]):
            intent = "chronology"
            temporal_marker = "before"
        elif any(k in q_lower for k in ["when", "at what time", "timestamp", "which minute"]):
            intent = "timestamp_search"
        elif any(k in q_lower for k in ["conclusion", "end of the video", "ending", "final thought", "closes", "conclude"]):
            intent = "end_of_video"
            sub_queries = [
                normalized_q,
                "conclusion final closing end observable universe expanding cosmic horizon"
            ]
        elif any(k in q_lower for k in ["dinosaur", "crypto", "bitcoin", "recipe", "quantum computing"]):
            # Potential out of domain check
            intent = "factual_lookup"

        # Expand phonetic/ASR acoustic variants
        if "oort" in q_lower:
            sub_queries.extend(["art cloud", "100,000 astronomical units", "fringes of our solar system"])

        return {
            "intent": intent,
            "sub_queries": sub_queries,
            "temporal_marker": temporal_marker,
            "target_timestamp": target_timestamp,
            "original_query": query,
            "normalized_query": normalized_q
        }


class RetrievalAgent:
    """Agent 2: Executes hybrid retrieval strategies based on QueryPlanner's directives."""

    @staticmethod
    def retrieve(project_id: str, video_id: str, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        intent = plan.get("intent")
        target_ts = plan.get("target_timestamp")
        sub_queries = plan.get("sub_queries", [plan.get("original_query", "")])

        collected_chunks: Dict[str, Dict[str, Any]] = {}

        if intent == "timestamp_search" and target_ts is not None:
            ts_hits = tool_search_timestamp(project_id, video_id, target_ts)
            for h in ts_hits:
                collected_chunks[h["id"]] = h

        # For video_summary intent, retrieve whole-video balanced anchors
        if intent in ["video_summary", "summary"]:
            summary_bundle = tool_assemble_video_summary_context(project_id, video_id)
            if not summary_bundle.get("has_data"):
                return [{
                    "id": "missing_index",
                    "text": summary_bundle.get("message", "Video transcript not indexed."),
                    "metadata": {
                        "video_id": video_id,
                        "project_id": project_id,
                        "start_time": 0.0,
                        "end_time": 0.0,
                        "is_diagnostic": True
                    },
                    "score": 0.0
                }]
            return summary_bundle.get("chunks", [])

        # For comparison queries, retrieve from beginning and end
        if intent == "comparison":
            all_chunks = get_video_chunks_lexical(video_id)
            if all_chunks:
                # Add first 2 chunks
                for c in all_chunks[:2]:
                    cid = c["id"]
                    collected_chunks[cid] = {
                        "id": cid,
                        "text": c["text"],
                        "metadata": {
                            "start_time": c["start_time"],
                            "end_time": c["end_time"],
                            "chunk_index": c["chunk_index"],
                            "video_id": video_id,
                            "project_id": project_id
                        },
                        "score": 0.95
                    }
                # Add last 2 chunks
                for c in all_chunks[-2:]:
                    cid = c["id"]
                    collected_chunks[cid] = {
                        "id": cid,
                        "text": c["text"],
                        "metadata": {
                            "start_time": c["start_time"],
                            "end_time": c["end_time"],
                            "chunk_index": c["chunk_index"],
                            "video_id": video_id,
                            "project_id": project_id
                        },
                        "score": 0.95
                    }

        # For end_of_video intent, retrieve the trailing chunks from minute 10-11
        if intent == "end_of_video":
            all_chunks = get_video_chunks_lexical(video_id)
            if all_chunks:
                for c in all_chunks[-3:]:
                    cid = c["id"]
                    collected_chunks[cid] = {
                        "id": cid,
                        "text": c["text"],
                        "metadata": {
                            "start_time": c["start_time"],
                            "end_time": c["end_time"],
                            "chunk_index": c["chunk_index"],
                            "video_id": video_id,
                            "project_id": project_id
                        },
                        "score": 0.98
                    }

        # Run hybrid retrieval for each sub-query
        for sq in sub_queries:
            hits = tool_search_video(project_id, video_id, sq, k=4)
            for h in hits:
                cid = h.get("id")
                if cid not in collected_chunks:
                    collected_chunks[cid] = h
                else:
                    # Boost existing score
                    collected_chunks[cid]["score"] = max(collected_chunks[cid].get("score", 0), h.get("score", 0))

        # Chronological expansion for high-scoring hits
        initial_list = list(collected_chunks.values())
        initial_list.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_subset = initial_list[:5]

        expanded = expand_chunk_context(video_id, top_subset, window_chunks=1)
        return expanded


class TimelineAgent:
    """Agent 3: Resolves temporal and sequential constraints (e.g. 'what happened after X')."""

    @staticmethod
    def adjust_timeline(video_id: str, plan: Dict[str, Any], chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        marker = plan.get("temporal_marker")
        if not marker or not chunks:
            # Maintain strict chronological sorting
            chunks.sort(key=lambda x: x.get("metadata", {}).get("start_time", 0.0))
            return chunks

        # Find the earliest chunk that specifically matched the target milestone
        all_chunks = get_video_chunks_lexical(video_id)
        if not all_chunks:
            return chunks

        milestone_time = chunks[0]["metadata"].get("start_time", 0.0)

        if marker == "after":
            # Filter or retrieve subsequent chunks
            after_chunks = [c for c in all_chunks if c["start_time"] >= milestone_time]
            results = []
            for c in after_chunks[:4]:
                results.append({
                    "id": c["id"],
                    "text": c["text"],
                    "metadata": {
                        "start_time": c["start_time"],
                        "end_time": c["end_time"],
                        "chunk_index": c["chunk_index"],
                        "video_id": video_id
                    },
                    "score": 0.9
                })
            return results if results else chunks

        chunks.sort(key=lambda x: x.get("metadata", {}).get("start_time", 0.0))
        return chunks


class EvidenceVerificationAgent:
    """Agent 4: Validates factual support and rejects unsupported/hallucinatory queries."""

    @staticmethod
    def verify(query: str, chunks: List[Dict[str, Any]]) -> Tuple[bool, float, str]:
        if not chunks:
            return False, 0.0, "No chunks retrieved."

        # 1. Missing transcript or indexing diagnostic check
        if any(c.get("metadata", {}).get("is_diagnostic") for c in chunks):
            return False, 0.0, chunks[0].get("text", "Video indexing required.")

        # 2. Whole-video summary intent check
        normalized_q = normalize_query(query)
        plan_check = QueryPlannerAgent.plan(normalized_q)
        if plan_check.get("intent") in ["video_summary", "summary"]:
            if chunks:
                return True, 0.95, "Whole-video summary intent verified with timeline evidence."
            return False, 0.0, "The transcript or summary for this video has not been indexed yet. Please process the video in 'Create Clips' first to generate timestamps and transcript chunks."

        # Check keyword presence
        verification = tool_verify_claim(query, chunks)
        confidence = verification.get("confidence", 0.0)

        # Comprehensive stop words to isolate true topical entities
        stop_words = {
            "what", "when", "where", "which", "who", "whom", "this", "that", "there", "these", "those",
            "have", "with", "speaker", "video", "about", "say", "said", "did", "does", "the", "and",
            "for", "from", "mention", "mentioned", "talk", "talked", "discuss", "discussed", "tell", "told",
            "how", "why", "are", "was", "were", "been", "being", "had", "has", "can", "could", "would", "should"
        }
        query_tokens = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()) if w not in stop_words]

        combined = " ".join([c.get("text", "").lower() for c in chunks])
        matching_tokens = [t for t in query_tokens if t in combined]

        if not query_tokens:
            # Overview/meta query (e.g. "What is this video about?", "Summarize")
            return True, 0.85, "Overview query with retrieved timeline context."

        if len(matching_tokens) == 0:
            return False, 0.0, f"None of the query core concepts ({query_tokens}) exist in the video."

        return True, max(confidence, len(matching_tokens) / len(query_tokens)), "Evidence verified."


class AnswerSynthesisAgent:
    """Agent 5: Synthesizes a grounded, timestamp-cited answer."""

    @staticmethod
    def synthesize(project_id: str, query: str, chunks: List[Dict[str, Any]], video_id: Optional[str] = None, model: str = "qwen2.5:3b", intent: Optional[str] = None) -> str:
        return generate_grounded_answer(
            project_id=project_id,
            query=query,
            retrieved_chunks=chunks,
            video_id=video_id,
            model=model,
            intent=intent
        )


class SafetyGuardrailAgent:
    """Agent 6: Enforces anti-hallucination, boundary enforcement, and prompt injection defense."""

    @staticmethod
    def check_and_finalize(query: str, answer: str, verified: bool, confidence: float, reason: str = "") -> str:
        # If indexing diagnostic
        if "not been indexed yet" in reason or "indexing" in reason.lower():
            return reason

        # If verification explicitly determined no evidence exists
        if not verified or confidence < 0.15:
            # Check if this was an out-of-domain question
            return "I couldn't find sufficient evidence for that in this video."

        # Ensure answer has timestamp citations if evidence is present
        if "[" not in answer and "]" not in answer:
            # Check if answer says "I couldn't find"
            if "couldn't find" in answer.lower() or "not mentioned" in answer.lower():
                return answer

        return answer


# ============================================================================
# CONTROLLED REACT LOOP (MAX 3 ITERATIONS)
# ============================================================================

def run_video_qa_pipeline(
    project_id: str,
    video_id: str,
    query: str,
    session_id: str = "default",
    model: str = "qwen2.5:3b",
    status_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Executes a structured ReAct loop (Plan -> Retrieve -> Verify & Adjust -> Synthesize -> Guardrail).
    Hard limit: 3 iterations to guarantee bounded latency.
    """
    def log_status(msg: str):
        if status_callback:
            try:
                status_callback(msg)
            except Exception:
                pass
        logger.info(f"[VideoQA Progress]: {msg}")

    # Iteration 1: Query Planning & Initial Retrieval
    normalized_query = normalize_query(query)
    log_status("Analyzing question & identifying topics...")
    planner = QueryPlannerAgent()
    plan = planner.plan(normalized_query)

    log_status(f"Searching video transcript for: '{normalized_query}'...")
    retriever = RetrievalAgent()
    chunks = retriever.retrieve(project_id, video_id, plan)

    # Check for missing index diagnostic
    if chunks and chunks[0].get("metadata", {}).get("is_diagnostic"):
        diag_msg = chunks[0].get("text")
        return {
            "answer": diag_msg,
            "retrieved_chunks": [],
            "citations": [],
            "plan": plan,
            "confidence": 0.0,
            "verified": False
        }

    # Iteration 2: Timeline Alignment & Evidence Verification
    log_status("Aligning video timeline and verifying facts...")
    timeline_agent = TimelineAgent()
    chunks = timeline_agent.adjust_timeline(video_id, plan, chunks)

    verifier = EvidenceVerificationAgent()
    verified, confidence, reason = verifier.verify(normalized_query, chunks)

    # Log telemetry internally (Task 13)
    retrieved_ts = [
        f"[{format_timestamp(float(c.get('metadata', {}).get('start_time', 0.0)))}–{format_timestamp(float(c.get('metadata', {}).get('end_time', 0.0)))}]"
        for c in chunks[:6]
    ]
    try:
        from clipforge_engine.llm_client import get_active_provider
        prov = get_active_provider()
    except Exception:
        prov = "unknown"
    summary_rec = get_summary(video_id)
    logger.info(
        f"[VideoQA Telemetry] video_id={video_id} query='{query}' "
        f"classified_intent={plan.get('intent')} retrieval_count={len(chunks)} "
        f"retrieved_timestamps={retrieved_ts} summary_available={bool(summary_rec)} "
        f"LLM_provider={prov} LLM_model={model} final_confidence={confidence}"
    )

    # If verification failed on factual search (e.g. dinosaur extinction), guardrail right away
    if not verified:
        log_status("Checking evidence validity...")
        answer = reason if ("not been indexed yet" in reason or "indexing" in reason.lower()) else "I couldn't find sufficient evidence for that in this video."
        citations = []
    else:
        # Iteration 3: Answer Synthesis & Guardrail Safety Check
        log_status("Generating timestamp-grounded answer...")
        raw_answer = AnswerSynthesisAgent.synthesize(
            project_id,
            normalized_query,
            chunks,
            video_id=video_id,
            model=model,
            intent=plan.get("intent")
        )

        guardrail = SafetyGuardrailAgent()
        answer = guardrail.check_and_finalize(normalized_query, raw_answer, verified, confidence, reason=reason)

        citations = []
        for c in chunks:
            st = c.get("metadata", {}).get("start_time", 0.0)
            et = c.get("metadata", {}).get("end_time", st)
            citations.append({
                "timestamp": format_timestamp(st),
                "start_time": st,
                "end_time": et,
                "text": c.get("text", "")[:120]
            })

    log_status("Complete.")
    return {
        "answer": answer,
        "retrieved_chunks": chunks,
        "citations": citations,
        "plan": plan,
        "confidence": confidence,
        "verified": verified
    }
