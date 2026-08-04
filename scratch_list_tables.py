import sqlite3
import pprint

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

print([t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()])
