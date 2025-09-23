from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.llm import generate_reply
import os
import re
import traceback

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
        "https://abujafar.onrender.com",
        "*",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 👇 Add this root route
@app.get("/")
def root():
    return {"message": "MoeX is alive"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/version")
def version():
    return {
        "commit": os.getenv("RENDER_GIT_COMMIT", "local"),
        "branch": os.getenv("RENDER_GIT_BRANCH", "local"),
    }

@app.post("/chat")
async def chat(message: str = Form(...), name: str = Form("Guest")):
    try:
        raw = generate_reply(message, name=name)
        final = sanitize(raw)
        return JSONResponse({"reply": final})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"{type(e).__name__}: {e}"}
        )
