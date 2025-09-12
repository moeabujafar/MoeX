CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, owner TEXT, due_date TEXT, priority TEXT, category TEXT, status TEXT, notes TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY, key TEXT, value TEXT, source TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS knowledge (id INTEGER PRIMARY KEY, title TEXT, chunk TEXT, tags TEXT, source_uri TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS humor (id INTEGER PRIMARY KEY, line TEXT, level TEXT, tag TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, ts TEXT, user_name TEXT, kind TEXT, tone TEXT, payload TEXT);
