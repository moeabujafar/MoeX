import sqlite3, os, json, datetime

DB_PATH = os.getenv("MOEX_DB", "moex.db")

def now():
    return datetime.datetime.utcnow().isoformat()

class DB:
    def __init__(self, path: str = DB_PATH):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())
            self.conn.commit()

    def ensure_user(self, name: str):
        cur = self.conn.execute("SELECT id FROM users WHERE name=?", (name,))
        row = cur.fetchone()
        if not row:
            self.conn.execute("INSERT INTO users(name, created_at) VALUES (?, ?)", (name, now()))
            self.conn.commit()
        return True

    def create_task(self, title, owner, due_date=None, priority="Normal", category="Admin", status="To-Do", notes=""):
        self.conn.execute(
            "INSERT INTO tasks(title, owner, due_date, priority, category, status, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (title, owner, due_date, priority, category, status, notes, now(), now())
        )
        self.conn.commit()

    def list_tasks(self, owner=None, status=None):
        q = "SELECT * FROM tasks WHERE 1=1"
        params = []
        if owner:
            q += " AND owner=?"; params.append(owner)
        if status:
            q += " AND status=?"; params.append(status)
        q += " ORDER BY COALESCE(due_date, '9999') ASC, priority DESC"
        cur = self.conn.execute(q, params)
        return [dict(r) for r in cur.fetchall()]

    def update_task(self, task_id, **fields):
        if not fields:
            return
        sets = ", ".join([f"{k}=?" for k in fields.keys()])
        params = list(fields.values()) + [task_id]
        self.conn.execute(f"UPDATE tasks SET {sets}, updated_at=? WHERE id=?", params[:-1] + [now(), params[-1]])
        self.conn.commit()

    def add_knowledge(self, title, chunk, tags="", source_uri=""):
        self.conn.execute(
            "INSERT INTO knowledge(title, chunk, tags, source_uri, created_at) VALUES (?,?,?,?,?)",
            (title, chunk, tags, source_uri, now())
        )
        self.conn.commit()

    def all_knowledge(self):
        cur = self.conn.execute("SELECT id, title, chunk, tags FROM knowledge ORDER BY id DESC LIMIT 500")
        return [dict(r) for r in cur.fetchall()]

    def save_memory(self, key, value, source="user"):
        self.conn.execute(
            "INSERT INTO memory(key, value, source, created_at) VALUES (?,?,?,?)",
            (key, value, source, now())
        )
        self.conn.commit()

    def add_humor(self, line: str, level: str = "playful", tag: str = "generic"):
        self.conn.execute(
            "INSERT INTO humor(line, level, tag, created_at) VALUES (?,?,?,?)",
            (line, level, tag, now())
        )
        self.conn.commit()

    def pick_humor(self, level: str = "playful", tag: str | None = None) -> str | None:
        if tag:
            cur = self.conn.execute(
                "SELECT line FROM humor WHERE level=? AND tag=? ORDER BY RANDOM() LIMIT 1",
                (level, tag)
            )
        else:
            cur = self.conn.execute(
                "SELECT line FROM humor WHERE level=? ORDER BY RANDOM() LIMIT 1",
                (level,)
            )
        row = cur.fetchone()
        return row[0] if row else None

    def audit(self, user_name, kind, tone, payload: dict):
        self.conn.execute(
            "INSERT INTO audit(ts, user_name, kind, tone, payload) VALUES (?,?,?,?,?)",
            (now(), user_name, kind, tone, json.dumps(payload, ensure_ascii=False))
        )
        self.conn.commit()

DB_INSTANCE = DB()
