"""Main entry point for Jarvis AI Assistant."""

import asyncio
import sys
from pathlib import Path

from jarvis.ui.app import JarvisApp
from jarvis.logger import logger
from jarvis.config import config


def main() -> None:
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Jarvis AI Assistant - Starting")
    logger.info("=" * 60)
    logger.info(f"Workspace: {config.workspace_root}")
    logger.info(f"Database: {config.db_path}")
    logger.info(f"Ollama URL: {config.ollama_url}")
    logger.info(f"Ollama Model: {config.ollama_model}")
    
    # Ensure workspace exists
    config.workspace_root.mkdir(parents=True, exist_ok=True)
    
    # Run the Textual app
    app = JarvisApp()
    app.run()
    
    logger.info("Jarvis AI Assistant - Shutdown complete")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)