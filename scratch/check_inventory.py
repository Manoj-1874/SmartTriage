import sqlite3

db_path = r'e:\Nilal_thiruvila\SmartTriage_Dashboard\triage.db'

def check_inventory():
    conn = sqlite3.connect(db_path)
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='inventory'").fetchone()[0]
    print(schema)
    conn.close()

if __name__ == "__main__":
    check_inventory()
