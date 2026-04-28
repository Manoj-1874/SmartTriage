import sqlite3

def check_users():
    conn = sqlite3.connect('triage.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users);")
    columns = cursor.fetchall()
    print("Users table columns:")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_users()
