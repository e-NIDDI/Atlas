"""Embedding generation for Jarvis RAG system.

Generates embeddings using Ollama's embedding API.
Falls back to simple hash-based embeddings if Ollama is unavailable.
"""

from typing import List, Optional
import hashlib

from jarvis.config import config
from jarvis.logger import logger


class EmbeddingGenerator:
    """Generates embeddings for text using Ollama."""

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self.model = model or config.ollama_embeddings_model
        self.base_url = base_url or config.ollama_url
        self._available: Optional[bool] = None
        logger.info(f"Embedding generator initialized (model: {self.model})")

    async def check_available(self) -> bool:
        """Check if the embedding model is available in Ollama."""
        if self._available is not None:
            return self._available

        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    self._available = any(
                        self.model in m or self.model.split(":")[0] in m
                        for m in models
                    )
                else:
                    self._available = False
        except Exception:
            self._available = False

        logger.info(f"Embedding model available: {self._available}")
        return self._available

    async def generate(self, text: str) -> List[float]:
        """Generate an embedding vector for the given text."""
        if not text.strip():
            return self._fallback_embedding("")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embedding = data.get("embedding", [])
                    if embedding:
                        return embedding
        except Exception as e:
            logger.warning(f"Ollama embedding failed, using fallback: {e}")

        return self._fallback_embedding(text)

    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            emb = await self.generate(text)
            embeddings.append(emb)
        return embeddings

    def _fallback_embedding(self, text: str) -> List[float]:
        """Generate a deterministic fallback embedding from text hash."""
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hex_digest = hash_obj.hexdigest()
        # Convert first 32 hex chars to 16 floats in [-1, 1]
        embedding = []
        for i in range(0, 64, 4):
            val = int(hex_digest[i:i + 4], 16) / 65535.0 * 2 - 1
            embedding.append(val)
        return embedding


# Global instance
embedding_generator = EmbeddingGenerator()