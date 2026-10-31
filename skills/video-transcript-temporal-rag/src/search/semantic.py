"""
Semantic Vector Search Adapter.
Optional ChromaDB client integration with graceful fallback if ChromaDB is not installed.
"""

import os
from typing import List, Optional
from ..models import EvidenceChunk

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class SemanticSearcher:
    """Optional vector searcher utilizing ChromaDB if installed and enabled."""

    def __init__(self, collection_name: str = "transcript_chunks", enabled: Optional[bool] = None):
        self.collection_name = collection_name
        # Only enable if explicitly requested or environment variable set
        if enabled is not None:
            self.enabled = enabled and CHROMADB_AVAILABLE
        else:
            self.enabled = os.getenv("ENABLE_CHROMA", "0") in ("1", "true", "True") and CHROMADB_AVAILABLE

        self.available = self.enabled
        self.client = None
        self.collection = None

        if self.available:
            try:
                self.client = chromadb.Client()
                self.collection = self.client.get_or_create_collection(name=collection_name)
            except Exception:
                self.available = False

    def index(self, chunks: List[EvidenceChunk]) -> bool:
        if not self.available or not self.collection or not chunks:
            return False

        try:
            ids = [c.id for c in chunks]
            documents = [c.text for c in chunks]
            metadatas = [
                {
                    "start_time": c.start_time,
                    "end_time": c.end_time,
                    "chunk_index": c.chunk_index,
                    "video_id": c.video_id
                }
                for c in chunks
            ]
            self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
            return True
        except Exception:
            return False

    def search(self, query: str, top_k: int = 5) -> List[EvidenceChunk]:
        if not self.available or not self.collection:
            return []

        try:
            results = self.collection.query(query_texts=[query], n_results=top_k)
            retrieved: List[EvidenceChunk] = []

            if results and "ids" in results and results["ids"]:
                ids = results["ids"][0]
                docs = results["documents"][0] if "documents" in results else []
                metas = results["metadatas"][0] if "metadatas" in results else []
                distances = results.get("distances", [[]])[0]

                for i, cid in enumerate(ids):
                    meta = metas[i] if i < len(metas) else {}
                    doc = docs[i] if i < len(docs) else ""
                    dist = distances[i] if i < len(distances) else 1.0
                    sim_score = max(0.0, 1.0 - dist)

                    retrieved.append(EvidenceChunk(
                        id=cid,
                        chunk_index=meta.get("chunk_index", 0),
                        text=doc,
                        start_time=meta.get("start_time", 0.0),
                        end_time=meta.get("end_time", 0.0),
                        video_id=meta.get("video_id", ""),
                        score=round(sim_score, 4)
                    ))

            return retrieved
        except Exception:
            return []
