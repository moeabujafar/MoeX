-- People (trusted users)
CREATE TABLE IF NOT EXISTS people (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE,
  handle TEXT UNIQUE,
  tags TEXT,
  secret_salt BLOB,
  secret_hash BLOB,
  is_enabled INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Sessions (issued after secret-word check)
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY,
  person_id INTEGER NOT NULL,
  token TEXT UNIQUE NOT NULL,
  trusted_until TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(person_id) REFERENCES people(id)
);

-- Chat logs (history)
CREATE TABLE IF NOT EXISTS chats (
  id INTEGER PRIMARY KEY,
  person_id INTEGER,
  role TEXT NOT NULL,   -- 'user' | 'assistant'
  text TEXT NOT NULL,
  ts TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(person_id) REFERENCES people(id)
);
-- Index for faster retrieval of chat history
CREATE INDEX IF NOT EXISTS idx_chats_person_id ON chats(person_id); 

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    due_date TEXT,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (person_id) REFERENCES people(id)
);
