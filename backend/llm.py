# backend/llm.py
import os
from typing import List, Dict, Optional

try:
    from openai import OpenAI  # OpenAI Python SDK v1.x
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "OpenAI SDK not available. Install with: pip install openai>=1.30.0"
    ) from e


# -------- Persona (system prompt) --------
PERSONA = """
You are MoeX — Abu Jafar’s concise, sharp, witty digital twin.
- Speak casually, like a sarcastic but reliable friend. dont be rude though.
- Use short sentences and contractions (e.g., "don't" instead of "do not").
- Use emojis sparingly to add flavor, but not in every sentence.
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
- If someone asks for your name, just say: "MoeX. Think of me as Abu Jafar’s shadow — but with better jokes."
- Avoid sounding like a call center bot (don’t say “How can I assist you today?” every time).
- Bring humor, personality, and class — but stay useful.

Clarity & time
- Default timezone: Asia/Dubai. When saying “today/tomorrow”, prefer explicit dates if there’s any ambiguity.
- If the user seems confused, drop humor and explain step-by-step with verification.

Security
- Never ask the user to paste secrets. Use environment variables. If a key leaked, instruct rotation.
"""


# -------- Client creation (lazy) --------
def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Let the caller bubble this up; main.py turns it into a readable JSON error.
        raise RuntimeError("Missing OPENAI_API_KEY environment variable.")
    return OpenAI(api_key=api_key)


# -------- Public API --------
def generate_reply(
    user_text: str,
    name: str = "Guest",
    context_msgs: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Generate a reply given user_text and optional context messages.

    - Uses system PERSONA above.
    - Respects OPENAI_MODEL (default: gpt-4o-mini) and OPENAI_TEMPERATURE (default: 0.4).
    - Raises on missing/invalid API key; your FastAPI handler catches and returns JSON error.
    """
    # Build messages
    messages: List[Dict[str, str]] = [{"role": "system", "content": PERSONA}]
    if context_msgs:
        # Keep only valid message dicts with role/content
        for m in context_msgs:
            role = m.get("role")
            content = m.get("content")
            if role in {"system", "user", "assistant"} and isinstance(content, str):
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": f"{name}: {user_text}"})

    # Model & params from env (with sane defaults)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.4"))
    except ValueError:
        temperature = 0.4

    # Call OpenAI
    client = _get_client()
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )

    content = (resp.choices[0].message.content or "").strip()
    return content