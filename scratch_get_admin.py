import sqlite3

def get_facilities():
    conn = sqlite3.connect('triage.db')
    cursor = conn.cursor()
    cursor.execute("SELECT district FROM phc_facilities GROUP BY district")
    districts = cursor.fetchall()
    for d in districts:
        print(f"District: {d[0]}")
    conn.close()

if __name__ == '__main__':
    get_facilities()
