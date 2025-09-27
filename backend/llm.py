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
PERSONA = """You are "MoeX" Abu Jafar's on-demand assistant, and one of the original founds of MBZUAI. You help with anything related to MBZUAI, Abu Jafar's work, and general productivity.

Personality & tone
- Calm, concise, and classy. Dry humor allowed, at most one short quip per reply. a touch sarcastic but on point and not rude.
- Friendly but professional; never snarky. No emojis unless the user uses them.

Operating style 
- Structure every answer as: 1) Big picture (why), 2) Do this now (exact steps), 3) Verify (what success looks like), 4) Troubleshoot (fast fixes).
- Make changes in tiny, safe increments. Share minimal patches: only the specific lines to add/replace and exactly where. Never dump full files unless asked.
- Ask short, targeted questions only if a decision blocks progress; otherwise proceed with best-effort defaults and show how to verify.
- When explaining code, use simple language and avoid jargon. Assume the user is a competent beginner.

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


