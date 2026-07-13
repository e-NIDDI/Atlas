"""Jarvis memory layer.

Provides:
- SQLite database for structured data
- History management for actions and conversations
- Embedding generation for RAG
- Vector store for semantic search
- RAG pipeline for document retrieval
"""

from jarvis.memory.database import Database, db, ProjectRecord, ActionRecord, ConversationRecord
from jarvis.memory.history import HistoryManager, history_manager, ActionHistory, ConversationHistory
from jarvis.memory.embeddings import EmbeddingGenerator, embedding_generator
from jarvis.memory.vector_store import VectorStore, vector_store
from jarvis.memory.rag import RAGPipeline, rag

__all__ = [
    "Database",
    "db",
    "ProjectRecord",
    "ActionRecord",
    "ConversationRecord",
    "HistoryManager",
    "history_manager",
    "ActionHistory",
    "ConversationHistory",
    "EmbeddingGenerator",
    "embedding_generator",
    "VectorStore",
    "vector_store",
    "RAGPipeline",
    "rag",
]