import sqlite3

def get_schema():
    conn = sqlite3.connect('triage.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    for col in cursor.fetchall():
        print(col)
    conn.close()

if __name__ == '__main__':
    get_schema()
