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
