from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import io

from .db import DB_INSTANCE as DB
from .tone import classify_context, pick_tone, envelope_response
from .rag import search as rag_search
from .llm import generate_reply, tts

app = FastAPI(title="MoeX — Team SLM")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://abujafar.onrender.com"],  # tighten later to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = (
    "You are MoeX. Speak naturally and briefly like a human, not a template. "
    "Do NOT use labels like 'TL;DR', 'Actions', or bullet lists unless the user asks. "
    "For policy/process or external topics, keep it straightforward and professional (no jokes). "
    "Otherwise feel free to be lightly witty and personable. "
    "Match the user's language (Arabic or English)."
)


@app.get("/health")
def health():
    return {"ok": True}

@app.post("/register")
def register(name: str = Form(...)):
    DB.ensure_user(name)
    return {"ok": True, "name": name}

@app.post("/teach")
def teach(line: str = Form(...), level: str = Form("playful"), tag: str = Form("generic"), name: str = Form("Admin")):
    DB.add_humor(line=line.strip(), level=level.strip(), tag=tag.strip())
    DB.audit(name, "teach", level, {"line": line, "tag": tag})
    return {"ok": True, "saved": {"line": line, "level": level, "tag": tag}}

@app.post("/chat")
def chat(message: str = Form(...), name: str = Form("Guest")):
    DB.ensure_user(name)
    lower = message.lower().strip()
    meta = {"external": any(w in lower for w in ["vendor","auditor","board","bot","external"])}

    if lower.startswith("teach:"):
        try:
            head, line = message.split("|", 1)
            parts = head.split()
            level = next((p.split("=")[1] for p in parts if p.startswith("level=")), "playful").strip()
            tag = next((p.split("=")[1] for p in parts if p.startswith("tag=")), "generic").strip()
            DB.add_humor(line=line.strip(), level=level, tag=tag)
            DB.audit(name, "teach", level, {"line": line.strip(), "tag": tag})
            return {"reply": f"Saved a {level} line under tag '{tag}'."}
        except Exception:
            return {"reply": "Format: teach: level=playful tag=task | your witty line"}

    if lower.startswith("remember:"):
        try:
            _, rest = message.split(":", 1)
            key, value = rest.split("=", 1)
            DB.save_memory(key.strip(), value.strip(), source=name)
            DB.audit(name, "teach", "professional", {"memory_key": key.strip()})
            return {"reply": f"Noted. I'll remember {key.strip()}."}
        except Exception:
            return {"reply": "Format: remember: key = value"}

    if lower.startswith("canon:"):
        try:
            head, text = message.split("|", 1)
            _, title = head.split(":", 1)
            DB.add_knowledge(title=title.strip(), chunk=text.strip(), tags="canon", source_uri=f"chat:{name}")
            DB.audit(name, "teach", "professional", {"canon": title.strip()})
            return {"reply": f"Added canonical note: {title.strip()}"}
        except Exception:
            return {"reply": "Format: canon: Title | Authoritative content"}

    if any(q in lower for q in ["what tasks do i have", "my tasks", "show my tasks"]):
        tasks = DB.list_tasks(owner=name)
        body = "TL;DR: You have {} task(s).\n".format(len(tasks))
        for t in tasks:
            body += f"- [{t['status']}] {t['title']} – due {t['due_date'] or '—'} (prio {t['priority']}, {t['category']})\n"
        tone = pick_tone("task_nudge")
        DB.audit(name, "chat", tone, {"message": message, "result": body})
        return {"reply": envelope_response(tone, body)}

    matches = rag_search(message, top_k=4)
    context = "\n\n".join([f"Source: {m[0]}\n{m[1][:600]}" for m in matches]) if matches else ""
    prompt = (
        f"User: {name}\n\nQuestion: {message}\n\n"
        + (f"Context (may cite):\n{context}\n" if context else "")
        + "\nAnswer naturally in a few sentences. If you cite uploaded material, mention the Source title(s)."
    )

    context_class = classify_context(message, meta)
    tone = pick_tone(context_class)
    raw = generate_reply(prompt, system=SYSTEM_PROMPT)
    final = envelope_response(tone, raw, is_policy=(tone=="professional"))
    DB.audit(name, "chat", tone, {"message": message, "result": final, "context": context_class})
    return {"reply": final}

@app.post("/upload")
async def upload(file: UploadFile = File(...), name: str = Form("Admin")):
    content = (await file.read()).decode(errors="ignore")
    title = file.filename
    chunks = [content[i:i+1800] for i in range(0, len(content), 1800)] or [content]
    for c in chunks:
        DB.add_knowledge(title=title, chunk=c, tags="policy", source_uri=title)
    DB.audit(name, "upload", "professional", {"title": title, "chunks": len(chunks)})
    return {"ok": True, "title": title, "chunks": len(chunks)}

@app.post("/tts")
async def speak(text: str = Form(...)):
    audio = tts(text)
    if not audio:
        return JSONResponse({"ok": False, "error": "No audio available in current config."}, status_code=400)
    return StreamingResponse(io.BytesIO(audio), media_type="audio/mpeg")
