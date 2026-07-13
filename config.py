"""Jarvis configuration settings."""

import os
from pathlib import Path
from dataclasses import dataclass, field


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
        default_factory=lambda: os.environ.get("OLLAMA_MODEL", "tinyllama")
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
