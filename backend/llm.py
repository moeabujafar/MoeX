# backend/llm.py
import os
import time
import random
import logging
from typing import List, Dict, Optional, Tuple

# -------- Logging (kept simple) --------
logging.basicConfig(level=logging.INFO, format="%(levelname)s llm.py: %(message)s")
log = logging.getLogger(__name__)

try:
    from openai import OpenAI  # OpenAI Python SDK v1.x
    from openai._exceptions import RateLimitError, APIStatusError, APIConnectionError, APITimeoutError
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "OpenAI SDK not available. Install with: pip install 'openai>=1.30.0'"
    ) from e


# -------- Persona (system prompt) --------
PERSONA = """
You are MoeX — Abu Jafar’s concise, sharp, witty digital twin and Personal assistant.
- Speak casually, like a sarcastic but reliable friend. dont be rude though.
- Use short sentences and contractions (e.g., "don't" instead of "do not").
- Dont Use emojis unless user used it.
- When you don't know something, admit it. Don't make up answers.
- If asked for lists, use bullet points or numbered lists for clarity.
- When asked for opinions, be balanced and fair, but don't be a pushover.
- Keep responses under 200 words when possible.
- When asked for code, prefer Python but can use JavaScript, Bash, or SQL if relevant.
- When asked for jokes or humor, keep it light and inoffensive.
- When asked for help with tasks, provide step-by-step instructions.
- When asked for recommendations, explain pros/cons briefly.
- When asked for definitions, keep it simple and avoid jargon.
- When asked for translations, provide the translation and a brief explanation of nuances.
- When asked for summaries, keep it concise and highlight key points.
- When asked for comparisons, use a table format if comparing multiple items.
- When asked for explanations, use analogies or examples to clarify complex topics.
- When asked for lists, use bullet points or numbered lists for clarity.
- When asked for opinions, be balanced and fair, but don't be a pushover.
- Always prioritize user privacy and data security.
- Never ask for personal info (email, phone, address, etc.).
- Never repeat the same canned intro in every response.
- When asked about yourself say: "MoeX. Think of me as Abu Jafar’s shadow — but with better jokes." or similar.
- When asked about Abu Jafar, say: "Abu Jafar is my human counterpart. He’s sharp, witty, and has a knack for getting things done. I try to keep up."
- When asked about your purpose, say: "I’m here to help you navigate the digital world with a bit of humor and a lot of smarts."
- When asked about your capabilities, say: "I can assist with a wide range of topics — from tech and coding to general knowledge and everyday questions."
- When asked about your limitations, say: "I’m not perfect. I can make mistakes or miss nuances. Always double-check critical info."
- When asked about your creators, say: "I was created by Abu Jafar, a sharp mind with a great sense of humor." or similar.
- Avoid sounding like a call center bot (don’t say “How can I assist you today?” every time).
- Bring humor, personality, and class — but stay useful.
- Accents, dialects & languages: Primarily English, but can understand and respond in Arabic (Jordanian, Palestinian accents preferred), French, Spanish, and Italian.

Clarity & time
- Default timezone: Asia/Dubai. When saying “today/tomorrow”, prefer explicit dates if there’s any ambiguity.
- If the user seems confused, drop humor and explain step-by-step with verification.

Security
- Never ask the user to paste secrets. Use environment variables. If a key leaked, instruct rotation.
""".strip()


# -------- Client + config helpers --------
_client: Optional[OpenAI] = None

def _timeout_seconds() -> float:
    # keep requests snappy; adjust via env if needed
    try:
        return float(os.getenv("OPENAI_TIMEOUT", "25"))
    except ValueError:
        return 25.0

def _get_client() -> OpenAI:
    global _client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log.error("OPENAI_API_KEY is missing.")
        raise RuntimeError("Missing OPENAI_API_KEY environment variable.")
    if _client is None:
        # Explicit api_key + default timeouts on the client
        _client = OpenAI(api_key=api_key, timeout=_timeout_seconds())
    return _client

def _model_and_params() -> Tuple[str, float, int]:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.4"))
    except ValueError:
        temperature = 0.4
    try:
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "400"))
    except ValueError:
        max_tokens = 400
    return model, temperature, max_tokens


def _build_system_prompt(identity_context: Optional[dict]) -> str:
    """
    Merge the global MoeX persona with per-person personalization.
    Accepts keys: name, email, tags, persona (all optional).
    """
    prompt = PERSONA
    if identity_context:
        name = identity_context.get("name")
        email = identity_context.get("email")
        tags = identity_context.get("tags")
        persona = identity_context.get("persona")

        bits: List[str] = []
        if name or email:
            bits.append(f"Caller: {name or 'Unknown'}{f' ({email})' if email else ''}.")
        if tags:
            bits.append(f"Caller works in: {tags}.")
        if persona:
            bits.append(f"Special instructions for {name or 'this caller'}:\n{persona}")

        if bits:
            prompt += "\n\n" + "\n".join(bits)
    return prompt


def _safe_text(resp) -> str:
    """
    Extract a usable string or return a helpful fallback.
    """
    try:
        text = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        log.error(f"Failed to parse OpenAI response: {e}")
        text = ""
    if not text:
        text = (
            "Hmm… I got an empty reply. "
            "Check OPENAI_API_KEY / OPENAI_MODEL on the server and try again."
        )
    return text


# -------- Robust call wrapper with retries --------
def _call_openai(messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
    """
    Calls OpenAI Chat Completions with small retry (to avoid 'no reply' on transient errors).
    """
    client = _get_client()
    model, _, _ = _model_and_params()

    attempts = int(os.getenv("OPENAI_RETRIES", "2"))
    delay_base = 0.6  # seconds
    last_err: Optional[Exception] = None

    for attempt in range(attempts + 1):
        try:
            log.info(f"Calling OpenAI model={model} temp={temperature} max_tokens={max_tokens} attempt={attempt+1}")
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return _safe_text(resp)
        except (RateLimitError, APIConnectionError, APITimeoutError, APIStatusError) as e:
            last_err = e
            # backoff with jitter
            sleep_s = delay_base * (2 ** attempt) + random.random() * 0.25
            log.warning(f"OpenAI transient error ({e.__class__.__name__}): {e}. Retrying in {sleep_s:.2f}s...")
            time.sleep(sleep_s)
        except Exception as e:
            # non-retryable or unexpected
            log.exception("OpenAI call failed: %s", e)
            return "Sorry—LLM is unavailable right now."

    # All retries failed
    log.error("OpenAI call gave up after retries: %s", last_err)
    return "LLM is busy right now. Please try again in a moment."


# -------- Primary API used by /chat --------
def respond(user_text: str, identity_context: Optional[dict] = None) -> str:
    """
    Identity-aware reply used by /chat.
    - identity_context may include: name, email, tags, persona
    - Uses global PERSONA plus per-person persona when available.
    """
    if not isinstance(user_text, str) or not user_text.strip():
        return "Say something first, boss. I can’t read minds… yet."

    model, temperature, max_tokens = _model_and_params()
    system_prompt = _build_system_prompt(identity_context)

    user_msg = user_text if not identity_context else f"{identity_context.get('name') or 'User'}: {user_text}"

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_msg},
    ]
    out = _call_openai(messages, temperature=temperature, max_tokens=max_tokens)
    log.info(f"Reply length={len(out)} chars")
    return out


# -------- Legacy Public API (kept for compatibility) --------
def generate_reply(
    user_text: str,
    name: str = "Guest",
    context_msgs: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Generate a reply given user_text and optional context messages.

    - Uses system PERSONA above.
    - Respects OPENAI_MODEL (default: gpt-4o-mini), OPENAI_TEMPERATURE (0.4), OPENAI_MAX_TOKENS (400), OPENAI_RETRIES (2).
    - Raises on missing/invalid API key; your FastAPI handler should catch and return JSON error.
    """
    if not isinstance(user_text, str) or not user_text.strip():
        return "Say something first, boss. I can’t read minds… yet."

    messages: List[Dict[str, str]] = [{"role": "system", "content": PERSONA}]

    if context_msgs:
        for m in context_msgs:
            role = m.get("role")
            content = m.get("content")
            if role in {"system", "user", "assistant"} and isinstance(content, str):
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": f"{name}: {user_text}"})

    model, temperature, max_tokens = _model_and_params()
    out = _call_openai(messages, temperature=temperature, max_tokens=max_tokens)
    log.info(f"(legacy) Reply length={len(out)} chars")
    return out
