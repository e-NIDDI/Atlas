"""Main entry point for Jarvis AI Assistant."""

import sys

from jarvis.cli.app import main
from jarvis.logger import logger


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
