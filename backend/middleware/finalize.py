from backend.middleware.sanitizer import sanitize

def finalize_reply(text: str, with_joke: bool = False) -> str:
    """Sanitize LLM text. Joke disabled by default so it works without DB."""
    out = sanitize(text or "")
    # If you later add humor picker, flip with_joke=True and append it here.
    return out
