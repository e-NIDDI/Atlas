"""Jarvis configuration settings."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Application configuration."""
    
    # Workspace settings
    workspace_root: Path = field(
        default_factory=lambda: Path.home() / "JarvisWorkspace"
    )
    
    # Ollama settings
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    
    # Database settings
    db_path: Path = field(
        default_factory=lambda: Path.home() / "JarvisWorkspace" / "jarvis.db"
    )
    
    # Logging settings
    log_dir: Path = field(
        default_factory=lambda: Path(__file__).parent / "logs"
    )
    log_level: str = "INFO"
    
    # UI settings
    theme: str = "dark"
    
    def __post_init__(self) -> None:
        """Ensure directories exist."""
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure db_path is absolute
        if not self.db_path.is_absolute():
            self.db_path = self.workspace_root / self.db_path


# Global configuration instance
config = Config()