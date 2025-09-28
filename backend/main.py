# backend/main.py
from datetime import datetime, timedelta, timezone
import os, secrets, hashlib, re, traceback
from fastapi import FastAPI, Cookie, Response, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from backend import db
from backend import llm
from backend.llm import generate_reply  # kept for compatibility if used elsewhere

# ----------------- App Setup -----------------
app = FastAPI(title="MoeX API")

TRUST_DAYS = int(os.getenv("MOEX_TRUST_DAYS", "14"))
# Allow guest chats if no session cookie present (default: true)
ALLOW_GUESTS = os.getenv("ALLOW_GUESTS", "true").lower() == "true"

@app.on_event("startup")
def _startup():
    db.init_db()

# ----------------- Helpers -----------------
def _hash_secret(secret: str, salt: bytes | None = None):
    if salt is None:
        salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, 120_000)
    return salt, h

def _verify_secret(secret: str, salt: bytes, secret_hash: bytes) -> bool:
    test = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, 120_000)
    return secrets.compare_digest(test, secret_hash)

def _now_utc():
    return datetime.now(timezone.utc)

def _iso(dt: datetime):
    return dt.astimezone(timezone.utc).isoformat()

def person_from_session(token: str | None):
    if not token:
        return None, None
    s = db.one("SELECT * FROM sessions WHERE token=?", (token,))
    if not s:
        return None, None
    if datetime.fromisoformat(s["trusted_until"]) < _now_utc():
        return None, None
    p = db.one("SELECT * FROM people WHERE id=? AND is_enabled=1", (s["person_id"],))
    return p, s

def log_chat(person_id, role, text):
    db.execute(
        "INSERT INTO chats(person_id, role, text) VALUES(?,?,?)",
        (person_id, role, text)
    )

def sanitize(x: str) -> str:
    """Minimal sanitizer to strip unwanted patterns."""
    x = re.sub(r'(?im)^(teach:|sys:|system:|internal:|debug:|tl;dr|tldr).*$', '', x)
    x = re.sub(r'\n{3,}', '\n\n', x).strip()
    return x

# ----------------- Middleware -----------------
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

# ----------------- Health Routes -----------------
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

# ----------------- Models -----------------
class ChatInput(BaseModel):
    message: str

class PersonCreate(BaseModel):
    name: str
    email: EmailStr | None = None
    handle: str | None = None
    tags: str | None = None
    secret_word: str

class ClaimRequest(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    handle: str | None = None

class VerifyRequest(BaseModel):
    person_id: int
    secret_word: str

# ----------------- Chat Endpoint -----------------
@app.post("/chat")
def chat(body: ChatInput, moex_session: str | None = Cookie(default=None)):
    try:
        person, sess = person_from_session(moex_session)
        user_text = body.message

        # Log user message (person may be None for guests)
        log_chat(person["id"] if person else None, "user", user_text)

        # If user not identified by session:
        if not person:
            if ALLOW_GUESTS:
                # Proceed as Guest
                identity_context = {"name": "Guest"}
                raw = llm.respond(user_text, identity_context=identity_context)
                final = sanitize(raw)
                log_chat(None, "assistant", final)
                # Keep shape stable for your UI (uses 'reply'); mark guest explicitly
                return {"authenticated": False, "guest": True, "reply": final}
            else:
                # Original behavior: ask to identify
                assistant = "Hey—who am I speaking to? (name or work email)"
                log_chat(None, "assistant", assistant)
                return {"authenticated": False, "reply": assistant, "next": "POST /auth/claim"}

        # Identified user path
        identity_context = {
            "name": person["name"],
            "email": person["email"],
            "tags": person["tags"]
        }
        raw = llm.respond(user_text, identity_context=identity_context)
        final = sanitize(raw)
        log_chat(person["id"], "assistant", final)
        return {"authenticated": True, "reply": final}

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"{type(e).__name__}: {e}"}
        )

# ----------------- Auth Endpoints -----------------
@app.post("/people")
def create_person(p: PersonCreate):
    salt, h = _hash_secret(p.secret_word)
    person_id = db.execute(
        """INSERT INTO people(name,email,handle,tags,secret_salt,secret_hash,is_enabled)
           VALUES(?,?,?,?,?,?,1)""",
        (p.name, p.email, p.handle, p.tags, salt, h),
    )
    return {"ok": True, "person_id": person_id}

@app.post("/auth/claim")
def auth_claim(body: ClaimRequest):
    person = None
    if body.email:
        person = db.one("SELECT * FROM people WHERE email=? AND is_enabled=1", (body.email,))
    if not person and body.handle:
        person = db.one("SELECT * FROM people WHERE handle=? AND is_enabled=1", (body.handle,))
    if not person and body.name:
        person = db.one("SELECT * FROM people WHERE name=? AND is_enabled=1", (body.name,))
    if not person:
        return {
            "status": "not_found",
            "message": "I don’t see you on Moe’s list yet. Guest mode?",
            "needs_secret": False
        }
    return {
        "status": "found",
        "person_id": person["id"],
        "needs_secret": True,
        "prompt": "What’s the secret word?"
    }

@app.post("/auth/verify")
def auth_verify(body: VerifyRequest, response: Response):
    person = db.one("SELECT * FROM people WHERE id=? AND is_enabled=1", (body.person_id,))
    if not person:
        raise HTTPException(404, "Person not found")
    if not _verify_secret(body.secret_word, person["secret_salt"], person["secret_hash"]):
        return {"verified": False, "message": "That doesn’t match. Try again or continue as guest."}

    token = secrets.token_urlsafe(32)
    trusted_until = _iso(_now_utc() + timedelta(days=TRUST_DAYS))
    db.execute(
        "INSERT INTO sessions(person_id, token, trusted_until) VALUES(?,?,?)",
        (person["id"], token, trusted_until)
    )
    response.set_cookie(
        "moex_session", token, httponly=True, secure=True,
        samesite="lax", max_age=TRUST_DAYS * 24 * 3600
    )
    return {
        "verified": True,
        "trusted_until": trusted_until,
        "person_id": person["id"]
    }

@app.get("/me")
def me(moex_session: str | None = Cookie(default=None)):
    person, sess = person_from_session(moex_session)
    if not person:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "person": {
            "id": person["id"],
            "name": person["name"],
            "email": person["email"],
            "tags": person["tags"]
        },
        "trusted_until": sess["trusted_until"]
    }
