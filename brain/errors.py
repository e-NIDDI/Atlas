"""User-friendly Ollama error messages."""


def format_ollama_error(raw_error: str) -> str:
    """Turn raw Ollama errors into actionable messages."""
    error = raw_error.strip()

    if "signal: killed" in error or "terminated" in error:
        return (
            "The model ran out of memory and was killed by your system.\n\n"
            "7B models need ~6GB+ RAM. You have ~5.5GB, so they won't load reliably.\n\n"
            "Fix options:\n"
            "  1. Use a smaller model:\n"
            "       ollama pull tinyllama\n"
            "       jarvis -m tinyllama\n"
            "     or:\n"
            "       ollama pull llama3.2:3b\n"
            "       jarvis -m llama3.2:3b\n"
            "  2. Free RAM — close browsers, IDEs, other apps\n"
            "  3. Unload models: ollama stop llama2"
        )

    if "not found" in error.lower() or "does not exist" in error.lower():
        return f"Model not found: {error}\nRun: ollama pull <model-name>"

    if "connection refused" in error.lower():
        return "Cannot reach Ollama. Start it with: ollama serve"

    return f"Ollama error: {error}"


def is_error_response(text: str) -> bool:
    """Check if a response string is an error from Ollama or our client."""
    if not text:
        return True
    markers = (
        "ran out of memory",
        "Ollama error:",
        "Error:",
        "Cannot reach Ollama",
        "Model not found",
        "Request to Ollama timed out",
        "Invalid response from Ollama",
    )
    return any(m in text for m in markers)
