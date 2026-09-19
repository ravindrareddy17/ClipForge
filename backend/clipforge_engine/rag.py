import os
import json
import uuid
import requests
from datetime import datetime

# Setup local Chroma client (lazy initialization)
CHROMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "chromadb")
os.makedirs(CHROMA_DIR, exist_ok=True)

_chroma_client = None

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb
            _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        except Exception as e:
            print(f"ChromaDB initialization failed: {e}")
            _chroma_client = None
    return _chroma_client

def get_ollama_embedding(text, model="nomic-embed-text", base_url="http://localhost:11434"):
    """
    Retrieves embeddings from a local Ollama server.
    Supports both legacy /api/embeddings and standard /api/embed endpoints.
    """
    # Clean text
    text = text.replace("\n", " ").strip()
    if not text:
        return [0.0] * 768

    headers = {"ngrok-skip-browser-warning": "1"}

    # Try legacy embeddings first
    try:
        resp = requests.post(f"{base_url}/api/embeddings", json={"model": model, "prompt": text}, headers=headers, timeout=1.5)
        if resp.status_code == 200:
            data = resp.json()
            if "embedding" in data:
                return data["embedding"]
    except Exception:
        pass

    # Try standard embed endpoint
    try:
        resp = requests.post(f"{base_url}/api/embed", json={"model": model, "input": [text]}, headers=headers, timeout=1.5)
        if resp.status_code == 200:
            data = resp.json()
            if "embeddings" in data and data["embeddings"]:
                return data["embeddings"][0]
    except Exception as e:
        pass

    # Return empty representation matching nomic-embed-text dimensions
    return [0.0] * 768

def chunk_transcript(video_id, project_id, transcript_data):
    """
    Split transcripts into semantic text blocks of around 150 words.
    Attaches time segment info.
    """
    if isinstance(transcript_data, str):
        try:
            transcript_data = json.loads(transcript_data)
        except Exception:
            transcript_data = []

    segments = []
    if isinstance(transcript_data, dict):
        segments = transcript_data.get("segments", [])
    elif isinstance(transcript_data, list):
        segments = transcript_data

    chunks = []
    current_chunk = []
    current_word_count = 0
    chunk_start = 0.0

    for seg in segments:
        text = seg.get("text", "").strip()
        words = text.split()
        if not words:
            continue

        if not current_chunk:
            chunk_start = seg.get("start", 0.0)

        current_chunk.append(text)
        current_word_count += len(words)

        if current_word_count >= 150:
            chunk_text = " ".join(current_chunk)
            chunk_end = seg.get("end", chunk_start + 1.0)
            chunks.append({
                "video_id": video_id,
                "project_id": project_id,
                "start_time": chunk_start,
                "end_time": chunk_end,
                "text": chunk_text,
                "speaker": seg.get("speaker") or "Speaker 1",
                "keywords": ""
            })
            current_chunk = []
            current_word_count = 0

    if current_chunk:
        chunk_text = " ".join(current_chunk)
        chunk_end = segments[-1].get("end", chunk_start + 1.0) if segments else chunk_start + 1.0
        chunks.append({
            "video_id": video_id,
            "project_id": project_id,
            "start_time": chunk_start,
            "end_time": chunk_end,
            "text": chunk_text,
            "speaker": "Speaker 1",
            "keywords": ""
        })

    return chunks

def index_transcript_chunks(video_id, project_id, chunks, model="nomic-embed-text", base_url="http://localhost:11434"):
    """
    Indexes semantic chunks in local ChromaDB collection and saves references.
    """
    client = get_chroma_client()
    if client is None:
        print("ChromaDB not available. Skipping vector indexing.")
        return
    collection = client.get_or_create_collection(name=f"cf_project_{project_id}")
    
    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for idx, chunk in enumerate(chunks):
        chunk_id = chunk.get("id") or f"{video_id}_chunk_{idx}_{str(uuid.uuid4())[:8]}"
        text = chunk["text"]
        emb = get_ollama_embedding(text, model=model, base_url=base_url)

        ids.append(chunk_id)
        embeddings.append(emb)
        documents.append(text)
        metadatas.append({
            "video_id": video_id,
            "project_id": project_id,
            "start_time": float(chunk["start_time"]),
            "end_time": float(chunk["end_time"]),
            "speaker": chunk.get("speaker") or "Speaker 1",
            "keywords": chunk.get("keywords") or ""
        })

    if ids:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

def query_similar_chunks(project_id, query_text, k=5, video_ids=None, model="nomic-embed-text", base_url="http://localhost:11434"):
    """
    Semantic search querying the project ChromaDB collection.
    """
    client = get_chroma_client()
    if client is None:
        print("ChromaDB not available. Returning empty results.")
        return []
    collection = client.get_or_create_collection(name=f"cf_project_{project_id}")
    query_emb = get_ollama_embedding(query_text, model=model, base_url=base_url)

    where_clause = {}
    if video_ids:
        # ChromaDB syntax: {"video_id": {"$in": video_ids}} or {"video_id": val}
        if len(video_ids) == 1:
            where_clause = {"video_id": video_ids[0]}
        else:
            where_clause = {"video_id": {"$in": video_ids}}

    results = collection.query(
        query_embeddings=[query_emb],
        n_results=k,
        where=where_clause if video_ids else None
    )

    parsed = []
    if results and "ids" in results and results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            parsed.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if "distances" in results else 0.0
            })

    # Robust fallback: If ChromaDB returned empty results, query SQLite transcript chunks or video transcript directly
    if not parsed:
        try:
            from clipforge_engine.db import get_db_connection
            conn = get_db_connection()
            query_words = [w.lower() for w in query_text.split() if len(w) > 2]
            
            # Check transcript_chunks in SQLite
            if video_ids:
                sql = f"SELECT * FROM transcript_chunks WHERE project_id = ? AND video_id IN ({','.join(['?']*len(video_ids))})"
                params = [project_id] + list(video_ids)
            else:
                sql = "SELECT * FROM transcript_chunks WHERE project_id = ?"
                params = [project_id]
            
            rows = conn.execute(sql, params).fetchall()
            matched_rows = []
            for r in rows:
                r_dict = dict(r)
                text_lower = r_dict["text"].lower()
                score = sum(1 for w in query_words if w in text_lower) if query_words else 1
                if score > 0 or not query_words:
                    matched_rows.append((score, r_dict))
                    
            matched_rows.sort(key=lambda x: x[0], reverse=True)
            for _, r_dict in matched_rows[:k]:
                parsed.append({
                    "id": r_dict["id"],
                    "text": r_dict["text"],
                    "metadata": {
                        "video_id": r_dict["video_id"],
                        "project_id": r_dict["project_id"],
                        "start_time": float(r_dict["start_time"]),
                        "end_time": float(r_dict["end_time"]),
                        "speaker": r_dict.get("speaker") or "Speaker 1"
                    },
                    "distance": 0.0
                })
                
            # If still no chunks, check videos.transcript directly
            if not parsed and video_ids:
                v_row = conn.execute("SELECT transcript FROM videos WHERE id = ?", (video_ids[0],)).fetchone()
                if v_row and v_row["transcript"]:
                    try:
                        tx_data = json.loads(v_row["transcript"])
                        segments = tx_data if isinstance(tx_data, list) else tx_data.get("segments", [])
                        for seg in segments[:k]:
                            parsed.append({
                                "id": f"seg_{seg.get('start', 0)}",
                                "text": seg.get("text", ""),
                                "metadata": {
                                    "video_id": video_ids[0],
                                    "project_id": project_id,
                                    "start_time": float(seg.get("start", 0.0)),
                                    "end_time": float(seg.get("end", 0.0)),
                                    "speaker": "Speaker"
                                },
                                "distance": 0.0
                            })
                    except Exception:
                        pass
            conn.close()
        except Exception as fallback_err:
            print(f"SQLite transcript search fallback error: {fallback_err}")

    return parsed

def generate_grounded_answer(project_id, query, retrieved_chunks, model="llama3.2", base_url="http://localhost:11434"):
    """
    Queries local Ollama using system-prompt grounding for context QA.
    """
    context_str = ""
    for idx, rc in enumerate(retrieved_chunks):
        meta = rc.get("metadata", {})
        start_t = meta.get("start_time", 0.0)
        end_t = meta.get("end_time", 0.0)
        
        # Convert start time to HH:MM:SS format
        hours = int(start_t // 3600)
        minutes = int((start_t % 3600) // 60)
        seconds = int(start_t % 60)
        timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        context_str += f"[Source {idx+1}] (Time: {timestamp_str}): {rc['text']}\n\n"

    system_prompt = (
        "You are an expert Content Intelligence Assistant. Answer the user's question based strictly on the provided transcript sources.\n"
        "Always cite the source number (e.g. [Source 1], [Source 2]) when stating facts.\n"
        "Reference specific timestamps to ground your reply.\n\n"
        f"--- TRANSCRIPT SOURCES ---\n{context_str}\n"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        "stream": False
    }

    try:
        headers = {"ngrok-skip-browser-warning": "1"}
        resp = requests.post(f"{base_url}/api/chat", json=payload, headers=headers, timeout=2.5)
        if resp.status_code == 200:
            return resp.json()["message"]["content"]
    except Exception as e:
        pass

    # Smart fallback: if Ollama is unreachable or errored, synthesize directly from retrieved chunks
    if retrieved_chunks:
        findings = []
        for idx, rc in enumerate(retrieved_chunks[:3]):
            meta = rc.get("metadata", {})
            start_t = float(meta.get("start_time", 0.0))
            hours = int(start_t // 3600)
            minutes = int((start_t % 3600) // 60)
            seconds = int(start_t % 60)
            timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            findings.append(f"• **[{timestamp_str}]**: {rc['text'].strip()}")
        
        response = (
            f"**Transcript Highlights matching your query:**\n\n"
            + "\n\n".join(findings)
            + f"\n\n*(💡 Tip: Local Ollama LLM is currently unreachable at `{base_url}`. The exact transcript moments above were retrieved directly from your video vector index.)*"
        )
        return response

    return f"No transcript segments found matching '{query}'. Please verify your video index or try another query."
