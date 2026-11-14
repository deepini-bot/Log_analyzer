"""SQLite persistence for incidents, investigations, feedback and knowledge chunks."""
import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from .config import settings

DB_PATH = Path(settings.data_dir) / "logmind.db"

@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA journal_mode=WAL")
        yield db
        db.commit()
    finally:
        db.close()

def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS incidents (
          incident_id TEXT PRIMARY KEY, title TEXT NOT NULL, severity TEXT,
          start_time TEXT, end_time TEXT, payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS investigations (
          id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT NOT NULL,
          payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(incident_id) REFERENCES incidents(incident_id));
        CREATE TABLE IF NOT EXISTS feedback (
          id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT NOT NULL,
          hypothesis TEXT NOT NULL, verdict TEXT NOT NULL, notes TEXT DEFAULT '',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(incident_id) REFERENCES incidents(incident_id));
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
          chunk_id TEXT PRIMARY KEY, source TEXT NOT NULL, source_type TEXT NOT NULL,
          content TEXT NOT NULL, metadata TEXT DEFAULT '{}', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS idx_incident_start ON incidents(start_time);
        CREATE INDEX IF NOT EXISTS idx_feedback_incident ON feedback(incident_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge_chunks(source);
        ''')

def save_incident(incident):
    with connect() as db:
        db.execute('''INSERT INTO incidents(incident_id,title,severity,start_time,end_time,payload)
          VALUES(?,?,?,?,?,?) ON CONFLICT(incident_id) DO UPDATE SET
          title=excluded.title,severity=excluded.severity,start_time=excluded.start_time,
          end_time=excluded.end_time,payload=excluded.payload''',
          (incident['incident_id'], incident['title'], incident.get('severity'),
           incident.get('start_time'), incident.get('end_time'), json.dumps(incident)))

def get_incident(incident_id):
    with connect() as db:
        row = db.execute('SELECT payload FROM incidents WHERE incident_id=?', (incident_id,)).fetchone()
    return json.loads(row['payload']) if row else None

def list_incidents(limit=200):
    with connect() as db:
        rows = db.execute('SELECT payload FROM incidents ORDER BY (start_time IS NULL), start_time DESC, created_at DESC LIMIT ?', (limit,)).fetchall()
    return [json.loads(r['payload']) for r in rows]

def save_investigation(incident_id, investigation):
    with connect() as db:
        db.execute('INSERT INTO investigations(incident_id,payload) VALUES(?,?)', (incident_id, json.dumps(investigation)))
        row = db.execute('SELECT payload FROM incidents WHERE incident_id=?', (incident_id,)).fetchone()
        if row:
            incident = json.loads(row['payload']); incident['investigation'] = investigation
            db.execute('UPDATE incidents SET payload=? WHERE incident_id=?', (json.dumps(incident), incident_id))

def add_feedback(incident_id, hypothesis, verdict, notes=''):
    with connect() as db:
        cur = db.execute('INSERT INTO feedback(incident_id,hypothesis,verdict,notes) VALUES(?,?,?,?)',
                         (incident_id, hypothesis, verdict, notes))
        return cur.lastrowid

def list_feedback(incident_id):
    with connect() as db:
        rows = db.execute('SELECT id,hypothesis,verdict,notes,created_at FROM feedback WHERE incident_id=? ORDER BY id DESC', (incident_id,)).fetchall()
    return [dict(r) for r in rows]

def upsert_knowledge(chunk):
    with connect() as db:
        db.execute('''INSERT INTO knowledge_chunks(chunk_id,source,source_type,content,metadata)
          VALUES(?,?,?,?,?) ON CONFLICT(chunk_id) DO UPDATE SET content=excluded.content,metadata=excluded.metadata''',
          (chunk['chunk_id'], chunk['source'], chunk['source_type'], chunk['content'], json.dumps(chunk.get('metadata', {}))))

def list_knowledge():
    with connect() as db:
        rows = db.execute('SELECT chunk_id,source,source_type,content,metadata FROM knowledge_chunks').fetchall()
    return [{**dict(r), 'metadata': json.loads(r['metadata'] or '{}')} for r in rows]

init_db()
