"""Terminal display helpers for Jarvis CLI."""

import sys
from typing import Optional

from jarvis.config import config


# ANSI colors
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def supports_color() -> bool:
    """Check if stdout supports ANSI colors."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def c(text: str, code: str) -> str:
    """Wrap text in ANSI color if supported."""
    if supports_color():
        return f"{code}{text}{RESET}"
    return text


def print_banner() -> None:
    """Print startup banner."""
    print(c("╔══════════════════════════════════════════════════╗", CYAN))
    print(c("║", CYAN) + c("  Jarvis", BOLD) + " — Local AI Workspace Assistant" + c("       ║", CYAN))
    print(c("╚══════════════════════════════════════════════════╝", CYAN))
    print(f"  Workspace: {config.workspace_root}")
    print(f"  Model:     {config.ollama_model}")
    print(f"  Ollama:    {config.ollama_url}")
    print()


def print_user(message: str) -> None:
    """Print a user message."""
    print(c("You:", BOLD + CYAN) + f" {message}")


def print_assistant(message: str) -> None:
    """Print an assistant message."""
    print(c("Jarvis:", BOLD + GREEN) + f" {message}")


def print_system(message: str) -> None:
    """Print a system message."""
    print(c("System:", BOLD + YELLOW) + f" {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(c("Error:", BOLD + RED) + f" {message}", file=sys.stderr)


def print_thinking() -> None:
    """Print thinking indicator."""
    print(c("Jarvis:", BOLD + GREEN) + c(" thinking...", DIM), end="", flush=True)


def clear_thinking() -> None:
    """Clear the thinking line."""
    if supports_color():
        print("\r\033[K", end="", flush=True)
    else:
        print()


def print_stream_start() -> None:
    """Start streaming assistant output."""
    print(c("Jarvis:", BOLD + GREEN) + " ", end="", flush=True)


def print_stream_chunk(chunk: str) -> None:
    """Print a streaming chunk."""
    print(chunk, end="", flush=True)


def print_stream_end() -> None:
    """End streaming output."""
    print()


def print_help() -> None:
    """Print help text."""
    print(c("\nCommands:", BOLD))
    print("  /help      Show this help")
    print("  /clear     Clear conversation history")
    print("  /projects  List workspace projects")
    print("  /tools     List available tools")
    print("  /status    Check Ollama connection and model")
    print("  /quit      Exit Jarvis")
    print()
    print(c("Tips:", BOLD))
    print("  • Ask naturally: \"Create a project called my-app\"")
    print("  • Read files: \"Read README.md in my-app\"")
    print("  • Dangerous actions will prompt for approval")
    print()
