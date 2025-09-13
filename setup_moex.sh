#!/bin/bash
set -euo pipefail

echo "== MoeX setup: lock structure to 'backend/' package =="

# Ensure package folders
touch backend/__init__.py
mkdir -p backend/middleware
touch backend/middleware/__init__.py

# Remove accidental leftovers
rm -rf backend/app 2>/dev/null || true

# Sanitizer
cat > backend/middleware/sanitizer.py <<'PY'
import re
_BLOCK_LINES = re.compile(r'(?im)^(?:\s*)(teach:|sys:|system:|internal:|debug:|tl;dr|tldr)\b.*?$')
_BAN_WORDS   = re.compile(r'(?i)\b(prompt|system\s*instructions?|developer\s*note|policy|hidden\s*rule)\b')
_SPACES      = re.compile(r'\n{3,}')
def sanitize(text: str) -> str:
    x = _BLOCK_LINES.sub('', text or '')
    x = _BAN_WORDS.sub(' ', x)
    x = _SPACES.sub('\n\n', x).strip()
    return x
PY

# Humor anti-repeat
cat > backend/middleware/humor.py <<'PY'
import sqlite3, time
from typing import Optional
DB_PATH = "backend/moex.db"  # works when uvicorn starts from project root
def pick_fresh_joke(db_path: str = DB_PATH) -> Optional[str]:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""
        SELECT id, line
        FROM humor
        ORDER BY COALESCE(use_count,0) ASC, RANDOM()
        LIMIT 1
    """)
    row = cur.fetchone()
    if not row:
        con.close()
        return None
    _id, line = row
    cur.execute("""
        UPDATE humor
        SET use_count = COALESCE(use_count,0)+1,
            last_used_at = ?
        WHERE id = ?
    """, (time.strftime("%Y-%m-%d %H:%M:%S"), _id))
    con.commit(); con.close()
    return line.strip()
PY

# Finalize helper (sanitize + optional joke)
cat > backend/middleware/finalize.py <<'PY'
from backend.middleware.sanitizer import sanitize
from backend.middleware.humor import pick_fresh_joke
def finalize_reply(text: str, with_joke: bool = True) -> str:
    out = sanitize(text or "")
    if with_joke:
        joke = pick_fresh_joke()
        if joke:
            out += f"\n\n(P.S. {joke})"
    return out
PY

# Ensure DB file and schema
[ -f backend/moex.db ] || : > backend/moex.db
[ -f backend/schema.sql ] && sqlite3 backend/moex.db < backend/schema.sql || true

# Add tracking columns (idempotent)
sqlite3 backend/moex.db 'CREATE TABLE IF NOT EXISTS humor (id INTEGER PRIMARY KEY, line TEXT, level TEXT, tag TEXT, created_at TEXT, use_count INTEGER DEFAULT 0, last_used_at TEXT);'
sqlite3 backend/moex.db 'ALTER TABLE humor ADD COLUMN use_count INTEGER DEFAULT 0;' 2>/dev/null || true
sqlite3 backend/moex.db 'ALTER TABLE humor ADD COLUMN last_used_at TEXT;' 2>/dev/null || true

# Seed jokes (only if missing)
sqlite3 backend/moex.db "INSERT INTO humor(line, level, tag, created_at) SELECT 'Deadlines don’t move; they just watch you sweat.','sharp','nudge',datetime('now') WHERE NOT EXISTS (SELECT 1 FROM humor WHERE line='Deadlines don’t move; they just watch you sweat.');"
sqlite3 backend/moex.db "INSERT INTO humor(line, level, tag, created_at) SELECT 'This isn’t wine — it won’t improve with time.','sharp','nudge',datetime('now') WHERE NOT EXISTS (SELECT 1 FROM humor WHERE line='This isn’t wine — it won’t improve with time.');"
sqlite3 backend/moex.db "INSERT INTO humor(line, level, tag, created_at) SELECT 'Let’s make this painless-ish.','light','soft',datetime('now') WHERE NOT EXISTS (SELECT 1 FROM humor WHERE line='Let’s make this painless-ish.');"
sqlite3 backend/moex.db "INSERT INTO humor(line, level, tag, created_at) SELECT 'We’ll keep it classy; chaos is so last quarter.','dry','style',datetime('now') WHERE NOT EXISTS (SELECT 1 FROM humor WHERE line='We’ll keep it classy; chaos is so last quarter.');"

# Patch backend/main.py to use finalize_reply for the returned text
if [ -f backend/main.py ]; then
  python3 - <<'PY'
from pathlib import Path
import re
p = Path("backend/main.py")
src = p.read_text(encoding="utf-8")

import_line = "from backend.middleware.finalize import finalize_reply"
if import_line not in src:
    lines = src.splitlines()
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    lines.insert(insert_at, import_line)
    src = "\n".join(lines)

def repl(m):
    inner = m.group(1)
    return f'return {{"reply": finalize_reply({inner})}}'
src2, n = re.subn(r'return\s*\{\s*"reply"\s*:\s*(.+?)\}', repl, src)
if n == 0 and 'finalize_reply(' not in src:
    src2 = src + "\n\n# NOTE: finalize_reply is available. Wrap your reply like:\n# return {\"reply\": finalize_reply(reply_text)}\n"

p.write_text(src2, encoding="utf-8")
print("Patched backend/main.py; return blocks updated:", n)
PY
else
  echo "WARNING: backend/main.py not found; patch skipped."
fi

echo "== Setup complete =="
echo "Run locally:"
echo "  uvicorn backend.main:app --host 0.0.0.0 --port 8030"
echo "Then test in your browser with frontend/index.html (API=http://localhost:8030)."

