from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.llm import generate_reply
import os
import re

# --- minimal sanitizer ---
def sanitize(x: str) -> str:
    x = re.sub(r'(?im)^(teach:|sys:|system:|internal:|debug:|tl;dr|tldr).*$', '', x)
    x = re.sub(r'\n{3,}', '\n\n', x).strip()
    return x

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://abujafar.onrender.com",  # prod
        "*"  # relax now; tighten later
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- health & version ---
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/version")
def version():
    return {
        "commit": os.getenv("RENDER_GIT_COMMIT", "local"),
        "branch": os.getenv("RENDER_GIT_BRANCH", "local"),
        "api": "moex"
    }

# --- chat ---
@app.post("/chat")
async def chat(message: str = Form(...), name: str = Form("Guest")):
    raw = generate_reply(message, name=name)
    final = sanitize(raw)
    return JSONResponse({"reply": final})
