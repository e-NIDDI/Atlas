"""Detect and fix bad responses from small models."""

import re
from typing import Optional

from jarvis.logger import logger


# Casual chat — no tools needed
_CASUAL_RE = re.compile(
    r"^(hi|hey|hello|yo|sup|hiya|howdy|greetings|good\s+(morning|afternoon|evening|night)"
    r"|what'?s\s+up|how\s+are\s+you|how'?s\s+it\s+going|hi\s+dude|hey\s+dude)[\s!.?]*$",
    re.IGNORECASE,
)

_HELP_RE = re.compile(
    r"(what can you|what do you|how can you|help me|what are you|who are you|what can i)",
    re.IGNORECASE,
)

_ACTION_WORDS = {
    "create", "make", "new", "list", "show", "read", "write", "delete",
    "remove", "search", "find", "rename", "run", "test", "project", "file",
    "folder", "directory", "git", "status",
}

# Signs the model is regurgitating the system prompt
_REGURGITATION_MARKERS = [
    "great questions",
    "here are some",
    "more examples",
    "examples of how",
    "follow exactly",
    "never repeat",
    "available tools:",
    "important rules:",
]


def is_casual_chat(message: str) -> bool:
    """True if the user is just chatting, not requesting an action."""
    text = message.strip()
    if not text:
        return True
    if _CASUAL_RE.match(text):
        return True
    if _HELP_RE.search(text):
        return True
    words = text.lower().split()
    if len(words) <= 5 and not any(w in _ACTION_WORDS for w in words):
        return True
    return False


def is_help_question(message: str) -> bool:
    """True if user is asking what Jarvis can do."""
    return bool(_HELP_RE.search(message.strip()))


def is_prompt_regurgitation(response: str) -> bool:
    """True if the model echoed instructions/examples instead of answering."""
    if not response or len(response) < 80:
        return False

    lower = response.lower()

    marker_hits = sum(1 for m in _REGURGITATION_MARKERS if m in lower)
    if marker_hits >= 1:
        return True

    # Numbered fake example conversations: "1. ... User: ... You: ..."
    if re.search(r"\d+\.\s+.+\bUser:\s*\"", response):
        return True
    if response.count('"type": "tool"') >= 2:
        return True
    if response.count("User:") >= 2 and response.count("You:") >= 2:
        return True

    return False


def sanitize_response(response: str, user_message: str) -> str:
    """
    Clean up bad model output.

    Returns the original response if fine, otherwise a sensible fallback.
    """
    if not is_prompt_regurgitation(response):
        return response

    logger.warning("Detected prompt regurgitation — using fallback response")

    if is_help_question(user_message):
        from jarvis.brain.intent import casual_help_response
        return casual_help_response()

    if is_casual_chat(user_message):
        return (
            "Hey! I'm Jarvis, your local workspace assistant. "
            "I can help you manage projects and files. What's up?"
        )

    return (
        "I got a bit confused there. Could you rephrase what you'd like me to do? "
        "For example: \"list my projects\" or \"create a project called my-app\"."
    )


def should_buffer_response(model: Optional[str] = None) -> bool:
    """Small models should buffer so we can sanitize before displaying."""
    from jarvis.brain.prompts import is_small_model
    return is_small_model(model)
