"""SQLite persistence: repos, chat history, retrieval log + feedback."""
import json, sqlite3
from contextlib import contextmanager
from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS repos(id TEXT PRIMARY KEY, name TEXT, source TEXT, overview TEXT, created REAL);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, repo_id TEXT, role TEXT, content TEXT, citations TEXT);
CREATE TABLE IF NOT EXISTS retrievals(id INTEGER PRIMARY KEY, repo_id TEXT, question TEXT, top_score REAL,
  files TEXT, feedback INTEGER);
"""


@contextmanager
def conn():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def save_repo(rid, name, source, overview, created):
    with conn() as c:
        c.execute("REPLACE INTO repos VALUES(?,?,?,?,?)", (rid, name, source, json.dumps(overview), created))


def list_repos():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT id,name,source,created FROM repos ORDER BY created DESC")]


def get_repo(rid):
    with conn() as c:
        r = c.execute("SELECT * FROM repos WHERE id=?", (rid,)).fetchone()
    return None if r is None else {**dict(r), "overview": json.loads(r["overview"])}


def add_message(rid, role, content, citations=None):
    with conn() as c:
        c.execute("INSERT INTO messages(repo_id,role,content,citations) VALUES(?,?,?,?)",
                  (rid, role, content, json.dumps(citations or [])))


def history(rid, limit=8):
    with conn() as c:
        rows = c.execute("SELECT role,content FROM messages WHERE repo_id=? ORDER BY id DESC LIMIT ?",
                         (rid, limit)).fetchall()
    return [dict(r) for r in reversed(rows)]


def log_retrieval(rid, question, top_score, files):
    with conn() as c:
        return c.execute("INSERT INTO retrievals(repo_id,question,top_score,files) VALUES(?,?,?,?)",
                         (rid, question, top_score, json.dumps(files))).lastrowid


def set_feedback(retrieval_id, value):
    with conn() as c:
        c.execute("UPDATE retrievals SET feedback=? WHERE id=?", (value, retrieval_id))


def metrics(rid):
    with conn() as c:
        r = c.execute("SELECT COUNT(*) n, AVG(top_score) s, SUM(feedback=1) up, SUM(feedback=-1) down "
                      "FROM retrievals WHERE repo_id=?", (rid,)).fetchone()
    return {"queries": r["n"], "avg_top_score": r["s"], "helpful": r["up"] or 0, "not_helpful": r["down"] or 0}
