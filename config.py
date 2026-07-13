"""Jarvis configuration settings."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    """Application configuration."""

    # Workspace settings
    workspace_root: Path = field(
        default_factory=lambda: Path(
            os.environ.get("JARVIS_WORKSPACE", str(Path.home()))
        ).expanduser()
    )

    # Ollama settings
    ollama_url: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
    )
    ollama_embeddings_model: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_EMBEDDINGS_MODEL", "nomic-embed-text")
    )

    # Database settings
    db_path: Path = field(
        default_factory=lambda: Path.home() / "jarvis.db"
    )

    # Logging settings
    log_dir: Path = field(
        default_factory=lambda: Path(__file__).parent / "logs"
    )
    log_level: str = field(
        default_factory=lambda: os.environ.get("JARVIS_LOG_LEVEL", "INFO")
    )

    # Ollama runtime options (lower = less RAM)
    ollama_num_ctx: int = field(
        default_factory=lambda: int(os.environ.get("OLLAMA_NUM_CTX", "2048"))
    )

    # Safe directories — user can add more
    safe_directories: List[str] = field(
        default_factory=lambda: os.environ.get(
            "JARVIS_SAFE_DIRS", ""
        ).split(",") if os.environ.get("JARVIS_SAFE_DIRS") else []
    )

    # RAG settings
    rag_enabled: bool = field(
        default_factory=lambda: os.environ.get("JARVIS_RAG_ENABLED", "false").lower() == "true"
    )
    rag_chunk_size: int = field(
        default_factory=lambda: int(os.environ.get("JARVIS_RAG_CHUNK_SIZE", "512"))
    )
    rag_chunk_overlap: int = field(
        default_factory=lambda: int(os.environ.get("JARVIS_RAG_CHUNK_OVERLAP", "32"))
    )

    # Max file size for reading (MB)
    max_file_size_mb: int = field(
        default_factory=lambda: int(os.environ.get("JARVIS_MAX_FILE_SIZE_MB", "50"))
    )

    def __post_init__(self) -> None:
        """Ensure directories exist."""
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.workspace_root / "jarvis.db"

    @property
    def ollama_options(self) -> dict:
        """Ollama request options tuned for lower memory use."""
        return {"num_ctx": self.ollama_num_ctx}


# Global configuration instance
config = Config()