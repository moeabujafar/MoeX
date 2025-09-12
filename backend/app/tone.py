from .db import DB_INSTANCE as DB

def classify_context(message: str, meta: dict) -> str:
    msg = (message or "").lower()
    if meta.get("external") or any(w in msg for w in ["vendor","auditor","board","policy","procedure","process","sop"]):
        return "policy"
    if meta.get("overdue"):
        return "overdue"
    if meta.get("repeat"):
        return "repeat_question"
    if any(w in msg for w in ["task","remind","what tasks","my tasks","mark done","status"]):
        return "task_nudge"
    return "routine"

def pick_tone(context: str) -> str:
    if context in ("policy","process","external"):
        return "professional"
    if context in ("overdue","repeat_question"):
        return "sharp"
    if context in ("task_nudge","routine"):
        return "playful"
    return "professional"

def envelope_response(tone: str, body: str, is_policy: bool=False) -> str:
    if tone == "professional" or is_policy:
        return body
    if tone == "playful":
        add = DB.pick_humor("playful") or "It won’t finish itself — shocking, I know."
        return f"{body}\n\n(P.S. {add})"
    if tone == "sharp":
        add = DB.pick_humor("sharp") or "Even Oracle’s patch cycles move faster."
        return f"{body}\n\n({add})"
    return body
