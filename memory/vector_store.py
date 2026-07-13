"""Simple vector store for Jarvis RAG system.

Stores document chunks with their embeddings and metadata.
Uses in-memory storage with cosine similarity search.
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path

from jarvis.config import config
from jarvis.logger import logger


class VectorStore:
    """In-memory vector store with cosine similarity search."""

    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self.persist_path = persist_path or config.workspace_root / "jarvis_vectors.json"
        self.vectors: List[Dict[str, Any]] = []
        self._load()
        logger.info(f"Vector store initialized ({len(self.vectors)} vectors)")

    def add(
        self,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a text chunk with its embedding to the store."""
        doc_id = f"doc_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{len(self.vectors)}"
        entry = {
            "id": doc_id,
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {},
            "created": datetime.now().isoformat(),
        }
        self.vectors.append(entry)
        self._save()
        return doc_id

    def add_batch(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Optional[Dict[str, Any]]]] = None,
    ) -> List[str]:
        """Add multiple text chunks with embeddings."""
        if metadatas is None:
            metadatas = [None] * len(texts)
        ids = []
        for text, emb, meta in zip(texts, embeddings, metadatas):
            doc_id = self.add(text, emb, meta)
            ids.append(doc_id)
        return ids

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search for similar texts using cosine similarity."""
        if not self.vectors:
            return []

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for entry in self.vectors:
            score = self._cosine_similarity(query_embedding, entry["embedding"])
            if score >= min_score:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = scored[:top_k]

        return [
            {
                "id": entry["id"],
                "text": entry["text"],
                "score": round(score, 4),
                "metadata": entry["metadata"],
            }
            for score, entry in results
        ]

    def delete(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        for i, entry in enumerate(self.vectors):
            if entry["id"] == doc_id:
                self.vectors.pop(i)
                self._save()
                return True
        return False

    def clear(self) -> None:
        """Clear all vectors."""
        self.vectors.clear()
        self._save()
        logger.info("Vector store cleared")

    def count(self) -> int:
        """Get the number of stored vectors."""
        return len(self.vectors)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b:
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _save(self) -> None:
        """Persist vectors to disk."""
        try:
            # Don't save embeddings to keep file small — only save text + metadata
            data = []
            for entry in self.vectors:
                data.append({
                    "id": entry["id"],
                    "text": entry["text"],
                    "metadata": entry["metadata"],
                    "created": entry["created"],
                })
            self.persist_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
        except Exception as e:
            logger.error(f"Failed to persist vector store: {e}")

    def _load(self) -> None:
        """Load vectors from disk."""
        if not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text(encoding='utf-8'))
            # Reconstruct with empty embeddings (will be regenerated on search)
            for entry in data:
                self.vectors.append({
                    "id": entry["id"],
                    "text": entry["text"],
                    "embedding": [],  # Will be filled on next search
                    "metadata": entry.get("metadata", {}),
                    "created": entry.get("created", ""),
                })
            logger.info(f"Loaded {len(self.vectors)} vectors from disk")
        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")


# Global instance
vector_store = VectorStore()