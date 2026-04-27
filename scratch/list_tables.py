import sqlite3

db_path = r'e:\Nilal_thiruvila\SmartTriage_Dashboard\triage.db'

def list_tables():
    conn = sqlite3.connect(db_path)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for t in tables:
        print(t[0])
    conn.close()

if __name__ == "__main__":
    list_tables()
