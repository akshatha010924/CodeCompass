import sqlite3


def save_record(record_id, items):
    """Persist a record's items in SQLite."""
    conn = sqlite3.connect("demo.db")
    conn.execute("CREATE TABLE IF NOT EXISTS records(id TEXT, item TEXT)")
    for item in items:
        conn.execute(f"INSERT INTO records VALUES('{record_id}', '{item}')")
    conn.commit()
