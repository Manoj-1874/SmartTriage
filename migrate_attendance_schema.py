import sqlite3

db_path = 'triage.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 1. Get original schema
schema = c.execute("SELECT sql FROM sqlite_master WHERE name='staff_attendance'").fetchone()[0]
print("Current Schema:", schema)

# 2. To change a constraint in SQLite, we need to recreate the table
# But first, let's try a simpler way: if it's just a CHECK constraint, we might need to migrate.
# However, if I change the API to just use 'Present' for now, it's safer.
# BUT 'Completed' is better.

# Let's do a proper migration:
# - Rename old table
# - Create new table without the strict constraint
# - Copy data
# - Drop old table

try:
    c.execute("ALTER TABLE staff_attendance RENAME TO staff_attendance_old")
    
    # Create new table with expanded constraint (or no constraint)
    new_table_sql = """
    CREATE TABLE staff_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        phc_id INTEGER NOT NULL,
        check_in_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'Present' CHECK (status IN ('Present', 'Absent', 'Late', 'Completed', 'On Leave')),
        geo_location TEXT,
        check_out_time TEXT,
        method TEXT,
        remarks TEXT,
        lat TEXT,
        lon TEXT,
        auth_method TEXT,
        ai_confidence INTEGER
    )
    """
    c.execute(new_table_sql)
    
    # Copy data
    c.execute('''
        INSERT INTO staff_attendance (id, user_id, phc_id, check_in_time, status, geo_location, check_out_time, method, remarks, lat, lon, auth_method, ai_confidence)
        SELECT id, user_id, phc_id, check_in_time, status, geo_location, check_out_time, method, remarks, lat, lon, auth_method, ai_confidence 
        FROM staff_attendance_old
    ''')
    
    c.execute("DROP TABLE staff_attendance_old")
    conn.commit()
    print("Migration successful: Status constraint expanded.")
except Exception as e:
    conn.rollback()
    print("Migration failed:", e)
finally:
    conn.close()
