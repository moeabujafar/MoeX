from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.llm import generate_reply

# minimal sanitizer (optional; expand later)
import re
def sanitize(x: str) -> str:
    x = re.sub(r'(?im)^(teach:|sys:|system:|internal:|debug:|tl;dr|tldr).*$', '', x)
    x = re.sub(r'\n{3,}', '\n\n', x).strip()
    return x

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500","http://127.0.0.1:5500","*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/chat")
async def chat(message: str = Form(...), name: str = Form("Guest")):
    raw = generate_reply(message, name=name)
    final = sanitize(raw)
    return JSONResponse({"reply": final})
