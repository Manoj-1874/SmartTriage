import sqlite3

def migrate_db():
    conn = sqlite3.connect('triage.db')
    cursor = conn.cursor()
    
    # Add missing columns to ambulances table
    try:
        cursor.execute("ALTER TABLE ambulances ADD COLUMN driver_name TEXT;")
        print("Added driver_name column")
    except sqlite3.OperationalError:
        print("driver_name column already exists or table error")
        
    try:
        cursor.execute("ALTER TABLE ambulances ADD COLUMN driver_contact TEXT;")
        print("Added driver_contact column")
    except sqlite3.OperationalError:
        print("driver_contact column already exists")
        
    try:
        cursor.execute("ALTER TABLE ambulances ADD COLUMN location TEXT;")
        print("Added location column")
    except sqlite3.OperationalError:
        print("location column already exists")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate_db()
