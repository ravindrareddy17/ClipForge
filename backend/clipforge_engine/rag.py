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

_installed_models = None

def get_installed_ollama_models(base_url="http://localhost:11434"):
    global _installed_models
    if _installed_models is None:
        try:
            headers = {"ngrok-skip-browser-warning": "1"}
            resp = requests.get(f"{base_url}/api/tags", headers=headers, timeout=2)
            if resp.status_code == 200:
                _installed_models = [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            _installed_models = []
    return _installed_models or []

def get_ollama_embedding(text, model="nomic-embed-text", base_url="http://localhost:11434"):
    """
    Retrieves embeddings from a local Ollama server if the model is installed.
    """
    text = text.replace("\n", " ").strip()
    if not text:
        return [0.0] * 768

    # Skip remote call if embedding model is not present in local Ollama
    available = get_installed_ollama_models(base_url)
    if available and model not in available and f"{model}:latest" not in available:
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
    except Exception:
        pass

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
    Semantic search querying the project ChromaDB collection or SQLite transcript chunks.
    """
    parsed = []
    
    # 1. Try ChromaDB if available
    try:
        client = get_chroma_client()
        if client is not None:
            collection = client.get_or_create_collection(name=f"cf_project_{project_id}")
            query_emb = get_ollama_embedding(query_text, model=model, base_url=base_url)

            where_clause = {}
            if video_ids:
                if len(video_ids) == 1:
                    where_clause = {"video_id": video_ids[0]}
                else:
                    where_clause = {"video_id": {"$in": video_ids}}

            results = collection.query(
                query_embeddings=[query_emb],
                n_results=k,
                where=where_clause if video_ids else None
            )

            if results and "ids" in results and results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    parsed.append({
                        "id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else 0.0
                    })
    except Exception as chroma_err:
        pass

    # 2. Robust Fallback: Query SQLite transcript chunks or video transcript directly
    if not parsed:
        try:
            from clipforge_engine.db import get_db_connection
            conn = get_db_connection()
            
            # Common query stopwords that should not restrict search
            STOPWORDS = {
                "what", "is", "the", "a", "an", "of", "in", "on", "at", "to", "for", "with",
                "about", "video", "videos", "tell", "tells", "telling", "told", "talk", "talks",
                "talking", "talked", "say", "says", "saying", "said", "explain", "explains",
                "explained", "show", "shows", "shown", "showing", "give", "gives", "given",
                "giving", "me", "you", "we", "they", "it", "this", "that", "these", "those",
                "can", "could", "would", "should", "will", "do", "does", "did", "how", "why",
                "who", "when", "where", "please", "summarize", "summary", "main", "idea",
                "ideas", "point", "points", "discuss", "discussed"
            }
            
            clean_words = [w.lower().strip("?,.!'\":;") for w in query_text.split()]
            content_words = [w for w in clean_words if len(w) > 2 and w not in STOPWORDS]
            
            # Fetch candidate chunks from SQLite
            if video_ids:
                sql = f"SELECT * FROM transcript_chunks WHERE project_id = ? AND video_id IN ({','.join(['?']*len(video_ids))}) ORDER BY start_time ASC"
                params = [project_id] + list(video_ids)
            else:
                sql = "SELECT * FROM transcript_chunks WHERE project_id = ? ORDER BY start_time ASC"
                params = [project_id]
                
            rows = conn.execute(sql, params).fetchall()
            
            if rows:
                if content_words:
                    matched_rows = []
                    for r in rows:
                        r_dict = dict(r)
                        text_lower = r_dict["text"].lower()
                        score = sum(text_lower.count(w) for w in content_words)
                        if score > 0:
                            matched_rows.append((score, r_dict))
                    
                    matched_rows.sort(key=lambda x: x[0], reverse=True)
                    if matched_rows:
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
                
                # If no specific keyword matched, or query is general (like 'what is video tells about'),
                # return the opening and overview chunks of the video!
                if not parsed:
                    for r in rows[:k]:
                        r_dict = dict(r)
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

            # 3. Direct videos.transcript fallback if transcript_chunks was empty
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

def generate_grounded_answer(project_id, query, retrieved_chunks, model="qwen2.5:3b", base_url="http://localhost:11434"):
    """
    Queries local Ollama using system-prompt grounding for context QA.
    """
    # If no chunks provided, fetch top chunks for project directly from SQLite
    if not retrieved_chunks:
        try:
            from clipforge_engine.db import get_db_connection
            conn = get_db_connection()
            rows = conn.execute("SELECT * FROM transcript_chunks WHERE project_id = ? ORDER BY start_time ASC LIMIT 4", (project_id,)).fetchall()
            if not rows:
                v_row = conn.execute("SELECT transcript, id FROM videos WHERE project_id = ? LIMIT 1", (project_id,)).fetchone()
                if v_row and v_row["transcript"]:
                    tx_data = json.loads(v_row["transcript"])
                    segments = tx_data if isinstance(tx_data, list) else tx_data.get("segments", [])
                    for seg in segments[:4]:
                        retrieved_chunks.append({
                            "id": f"seg_{seg.get('start', 0)}",
                            "text": seg.get("text", ""),
                            "metadata": {
                                "video_id": v_row["id"],
                                "project_id": project_id,
                                "start_time": float(seg.get("start", 0.0)),
                                "end_time": float(seg.get("end", 0.0)),
                                "speaker": "Speaker"
                            }
                        })
            else:
                for r in rows:
                    r_dict = dict(r)
                    retrieved_chunks.append({
                        "id": r_dict["id"],
                        "text": r_dict["text"],
                        "metadata": {
                            "video_id": r_dict["video_id"],
                            "project_id": r_dict["project_id"],
                            "start_time": float(r_dict["start_time"]),
                            "end_time": float(r_dict["end_time"]),
                            "speaker": r_dict.get("speaker") or "Speaker 1"
                        }
                    })
            conn.close()
        except Exception as e:
            print(f"Fallback chunk load error: {e}")

    context_str = ""
    for idx, rc in enumerate(retrieved_chunks):
        meta = rc.get("metadata", {})
        start_t = meta.get("start_time", 0.0)
        
        hours = int(start_t // 3600)
        minutes = int((start_t % 3600) // 60)
        seconds = int(start_t % 60)
        timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        context_str += f"[Timestamp: {timestamp_str}]: \"{rc['text']}\"\n\n"

    system_prompt = (
        "You are ClipForge AI, an expert video intelligence assistant. "
        "The user is asking a question about a video. Below are the transcribed spoken segments from the video with timestamps.\n"
        "Answer the user's question clearly, informatively, and accurately based on what was spoken in the video.\n"
        "Reference timestamps (e.g. [00:12]) whenever discussing specific points or quotes from the video.\n\n"
        f"--- VIDEO TRANSCRIPT SEGMENTS ---\n{context_str}\n"
    )

    # Detect real available models in Ollama, prioritizing fast local models
    target_model = model
    try:
        headers = {"ngrok-skip-browser-warning": "1"}
        tags_resp = requests.get(f"{base_url}/api/tags", headers=headers, timeout=2)
        if tags_resp.status_code == 200:
            available = [m["name"] for m in tags_resp.json().get("models", [])]
            if "qwen2.5:3b" in available:
                target_model = "qwen2.5:3b"
            elif target_model not in available and available:
                match = next((m for m in available if "qwen" in m.lower()), available[0])
                target_model = match
    except Exception:
        pass

    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        "options": {
            "num_predict": 220,
            "temperature": 0.3
        },
        "stream": False
    }

    try:
        headers = {"ngrok-skip-browser-warning": "1"}
        resp = requests.post(f"{base_url}/api/chat", json=payload, headers=headers, timeout=50)
        if resp.status_code == 200:
            content = resp.json().get("message", {}).get("content", "")
            if content.strip():
                return content.strip()
    except Exception as e:
        print(f"Ollama chat error/timeout: {e}")

    # Smart fallback: if Ollama is unreachable, busy, or errored, synthesize directly from retrieved chunks
    if retrieved_chunks:
        findings = []
        for rc in retrieved_chunks[:4]:
            meta = rc.get("metadata", {})
            start_t = float(meta.get("start_time", 0.0))
            hours = int(start_t // 3600)
            minutes = int((start_t % 3600) // 60)
            seconds = int(start_t % 60)
            timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            findings.append(f"• **[{timestamp_str}]**: *\"{rc['text'].strip()}\"*")
        
        response = (
            f"**Transcript Highlights from this video:**\n\n"
            + "\n\n".join(findings)
            + f"\n\n*(Analysis synthesized directly from video transcript timestamps.)*"
        )
        return response

    return f"I could not locate transcript segments for this query. Please check if the video has been transcribed in the Create Clips tab."
