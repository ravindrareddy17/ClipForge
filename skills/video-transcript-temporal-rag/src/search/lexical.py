"""
Pure Python BM25-like lexical search engine.
Computes token matching, term frequencies, token coverage, and phrase density
with zero external dependencies.
"""

import re
import math
from typing import List, Dict, Set, Tuple, Optional
from ..models import EvidenceChunk

DEFAULT_STOP_WORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "to", "for", "with", "by", "of", "from",
    "is", "was", "are", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "can", "could", "should", "would", "will", "shall",
    "what", "when", "where", "which", "who", "whom", "how", "why",
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "video", "speaker", "talk", "discuss", "mention", "say", "said"
}


class LexicalSearcher:
    """Performs BM25-style lexical keyword retrieval over EvidenceChunks."""

    def __init__(self, stop_words: Optional[Set[str]] = None, k1: float = 1.5, b: float = 0.75):
        self.stop_words = stop_words or DEFAULT_STOP_WORDS
        self.k1 = k1
        self.b = b

    def tokenize(self, text: str) -> List[str]:
        """Extracts lowercase alphabetic and alphanumeric tokens."""
        return [w for w in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(w) >= 2]

    def search(self, query: str, chunks: List[EvidenceChunk], top_k: int = 5) -> List[EvidenceChunk]:
        if not chunks or not query.strip():
            return []

        query_tokens = [t for t in self.tokenize(query) if t not in self.stop_words]
        if not query_tokens:
            # Fall back to all tokens if all were stop words
            query_tokens = self.tokenize(query)
            if not query_tokens:
                return chunks[:top_k]

        # Calculate average document length
        avg_doc_len = sum(len(self.tokenize(c.text)) for c in chunks) / max(len(chunks), 1)

        # Inverted index & Document frequencies
        df: Dict[str, int] = {}
        doc_tokens_list: List[List[str]] = []
        for c in chunks:
            tokens = self.tokenize(c.text)
            doc_tokens_list.append(tokens)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                df[t] = df.get(t, 0) + 1

        num_docs = len(chunks)
        scored_chunks: List[Tuple[float, EvidenceChunk]] = []

        query_lower = query.lower().strip()

        for idx, chunk in enumerate(chunks):
            doc_tokens = doc_tokens_list[idx]
            doc_len = len(doc_tokens)
            if doc_len == 0:
                continue

            # Term frequencies in this document
            tf: Dict[str, int] = {}
            for t in doc_tokens:
                tf[t] = tf.get(t, 0) + 1

            score = 0.0
            matched_query_tokens = 0

            for q_term in query_tokens:
                if q_term in tf:
                    matched_query_tokens += 1
                    term_tf = tf[q_term]
                    doc_freq = df.get(q_term, 1)

                    # Standard BM25 IDF with smoothing
                    idf = math.log(1.0 + (num_docs - doc_freq + 0.5) / (doc_freq + 0.5))
                    idf = max(idf, 0.1)

                    # BM25 TF component
                    tf_component = (term_tf * (self.k1 + 1.0)) / (
                        term_tf + self.k1 * (1.0 - self.b + self.b * (doc_len / max(avg_doc_len, 1.0)))
                    )
                    score += idf * tf_component

            # Query coverage boost
            coverage_ratio = matched_query_tokens / max(len(query_tokens), 1)
            score *= (0.5 + 0.5 * coverage_ratio)

            # Exact phrase bonus
            chunk_lower = chunk.text.lower()
            if query_lower in chunk_lower:
                score += 3.0

            if score > 0.0:
                chunk_copy = chunk.model_copy()
                chunk_copy.score = round(score, 4)
                scored_chunks.append((score, chunk_copy))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored_chunks[:top_k]]
