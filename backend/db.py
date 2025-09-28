import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "moex.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if SCHEMA_PATH.exists():
        with get_conn() as conn, open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    else:
        # minimal bootstrap so things don’t crash without schema.sql
        with get_conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS people (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT, email TEXT, tags TEXT,
              is_enabled INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS chats (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              person_id INTEGER, role TEXT, text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

def all(sql, params=()):
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

def one(sql, params=()):
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

def query(sql, params=()):
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

def execute(sql, params=()):
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid

def list_people():
    return all("SELECT id,name,email,tags FROM people WHERE is_enabled=1")

def list_tasks(person_id: int):
    return all("SELECT id,title,due_date,status FROM tasks WHERE person_id=?", (person_id,))

if __name__ == "__main__":
    init_db()
    print("DB ready:", DB_PATH)
