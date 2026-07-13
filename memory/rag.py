"""Retrieval-Augmented Generation (RAG) pipeline for Jarvis.

Chunks documents, generates embeddings, stores in vector DB,
and retrieves relevant context for LLM prompts.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import re

from jarvis.memory.embeddings import embedding_generator
from jarvis.memory.vector_store import vector_store
from jarvis.tools.filesystem import fs
from jarvis.tools.documents import document_manager
from jarvis.config import config
from jarvis.logger import logger


class RAGPipeline:
    """RAG pipeline for document indexing and retrieval."""

    def __init__(self) -> None:
        self.chunk_size = config.rag_chunk_size
        self.chunk_overlap = config.rag_chunk_overlap
        logger.info(f"RAG pipeline initialized (chunk_size={self.chunk_size}, overlap={self.chunk_overlap})")

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks at paragraph/sentence boundaries."""
        if not text:
            return []

        chunks = []
        # First split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)

        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 1 <= self.chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # If paragraph itself is too long, split by sentences
                if len(para) > self.chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    current_chunk = ""
                    for sent in sentences:
                        if len(current_chunk) + len(sent) + 1 <= self.chunk_size:
                            current_chunk += sent + " "
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = sent + " "
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
                else:
                    current_chunk = para + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    async def index_document(self, path: str) -> Dict[str, Any]:
        """Index a document into the vector store."""
        resolved = fs.resolve_path(path, must_exist=True)
        logger.info(f"Indexing document: {resolved}")

        # Extract text
        result = document_manager.extract_text(str(resolved))
        text = result.get("content", "")

        if not text:
            return {"path": path, "chunks": 0, "error": "No text extracted"}

        # Chunk
        chunks = self.chunk_text(text)
        logger.info(f"Document split into {len(chunks)} chunks")

        # Generate embeddings
        embeddings = await embedding_generator.generate_batch(chunks)

        # Store in vector DB
        metadatas = [
            {
                "source": str(resolved),
                "format": result.get("format", "unknown"),
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]

        ids = vector_store.add_batch(chunks, embeddings, metadatas)

        return {
            "path": path,
            "chunks": len(chunks),
            "ids": ids,
            "word_count": result.get("word_count", 0),
        }

    async def index_directory(
        self,
        directory: str = ".",
        file_pattern: str = "*.md",
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """Index all matching files in a directory."""
        resolved = fs.resolve_path(directory, must_exist=True)
        files = list(resolved.rglob(file_pattern)) if recursive else list(resolved.glob(file_pattern))

        results = []
        total_chunks = 0
        errors = 0

        for file_path in files:
            if not file_path.is_file():
                continue
            try:
                result = await self.index_document(str(file_path))
                results.append(result)
                total_chunks += result.get("chunks", 0)
            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")
                errors += 1

        return {
            "files_indexed": len(results),
            "total_chunks": total_chunks,
            "errors": errors,
            "results": results,
        }

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a query."""
        query_embedding = await embedding_generator.generate(query)
        results = vector_store.search(query_embedding, top_k, min_score)
        return results

    def get_context_for_prompt(self, results: List[Dict[str, Any]]) -> str:
        """Format retrieved results as context for an LLM prompt."""
        if not results:
            return ""

        lines = ["--- Retrieved Context ---"]
        for i, r in enumerate(results, 1):
            source = r.get("metadata", {}).get("source", "unknown")
            lines.append(f"\n[{i}] From: {source} (relevance: {r['score']})")
            lines.append(r["text"][:500])

        return "\n".join(lines)


# Global instance
rag = RAGPipeline()