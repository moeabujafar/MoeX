import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def generate_reply(prompt: str, system: str = "") -> str:
    if not OPENAI_API_KEY:
        return "TL;DR: " + (prompt[:180] + ("…" if len(prompt) > 180 else ""))
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        msg = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
            temperature=0.4,
        )
        return msg.choices[0].message.content
    except Exception as e:
        return f"(LLM error: {e})\n\n{prompt}"

def tts(text: str) -> bytes:
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            speech = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice=os.getenv("MOEX_VOICE","alloy"),
                input=text,
            )
            return speech.read()
        except Exception:
            pass
    return b""
