import sqlite3

db_path = r'e:\Nilal_thiruvila\SmartTriage_Dashboard\triage.db'

def inspect_resources():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = ['phc_inventory', 'resources', 'phc_resources', 'medical_supplies']
    for t in tables:
        res = cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{t}'").fetchone()
        if res:
            print(f"--- TABLE: {t} ---")
            print(res[0])
            
    conn.close()

if __name__ == "__main__":
    inspect_resources()
