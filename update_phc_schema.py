
import sqlite3
import os

def update_schema():
    db_path = 'triage.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- Updating Schema for Real-World PHC Features ---")

    try:
        # 1. Update patient_logs for Departmental Reporting & Social Risk
        cursor.execute("PRAGMA table_info(patient_logs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'phc_department' not in columns:
            print("Adding 'phc_department' to patient_logs...")
            cursor.execute("ALTER TABLE patient_logs ADD COLUMN phc_department TEXT DEFAULT 'Medicine'")
            
        if 'is_social_risk' not in columns:
            print("Adding 'is_social_risk' to patient_logs...")
            cursor.execute("ALTER TABLE patient_logs ADD COLUMN is_social_risk INTEGER DEFAULT 0")

        # 2. Create REFERRALS Table for the "Digital Handshake"
        print("Creating 'referrals' table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                source_phc_id TEXT NOT NULL,
                target_phc_id TEXT NOT NULL,
                referral_reason TEXT,
                urgency TEXT,
                status TEXT DEFAULT 'PENDING', -- PENDING, IN_TRANSIT, ARRIVED, COMPLETED
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                arrived_at TIMESTAMP,
                clinical_notes TEXT
            )
        ''')

        # 3. Create INVENTORY Table for the "Digital Bin Card"
        print("Creating 'inventory' table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phc_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                current_stock INTEGER DEFAULT 0,
                min_stock_level INTEGER DEFAULT 10,
                unit TEXT DEFAULT 'Tablets',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 4. Create SOCIAL_VAULT Table (The "Secret Diary")
        # Note: This has extra encryption/privacy considerations in the app logic
        print("Creating 'social_vault' table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_vault (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                category TEXT, -- Teenage Pregnancy, School Dropout, etc.
                notes_encrypted TEXT,
                authorized_mo_id TEXT, -- The Medical Officer who recorded it
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        print("--- Schema Update Complete ---")

    except Exception as e:
        print(f"Error updating schema: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_schema()
