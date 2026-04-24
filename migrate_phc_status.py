"""
Database Migration: Add PHC Status Tracking
Migrates existing triage.db to support PHC status (ACTIVE/INACTIVE/MAINTENANCE)
"""

import sqlite3
import sys

def migrate_phc_status():
    """Add status column to phc_facilities table if it doesn't exist"""

    db_path = 'triage.db'
    print(f"Connecting to {db_path}...")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        # Check if status column already exists
        existing_columns = c.execute('PRAGMA table_info(phc_facilities)').fetchall()
        column_names = [col[1] for col in existing_columns]

        print(f"\nCurrent phc_facilities columns: {column_names}")

        if 'status' not in column_names:
            print("\n[MIGRATION] Adding 'status' column to phc_facilities...")
            c.execute('ALTER TABLE phc_facilities ADD COLUMN status TEXT DEFAULT "ACTIVE" CHECK(status IN ("ACTIVE", "INACTIVE", "MAINTENANCE"))')
            print("✅ Added 'status' column")
        else:
            print("✅ 'status' column already exists")

        if 'created_at' not in column_names:
            print("\n[MIGRATION] Adding 'created_at' column to phc_facilities...")
            c.execute('ALTER TABLE phc_facilities ADD COLUMN created_at DATETIME')
            # Update all existing rows with current timestamp
            c.execute('UPDATE phc_facilities SET created_at = datetime("now") WHERE created_at IS NULL')
            print("✅ Added 'created_at' column")
        else:
            print("✅ 'created_at' column already exists")

        if 'updated_at' not in column_names:
            print("\n[MIGRATION] Adding 'updated_at' column to phc_facilities...")
            c.execute('ALTER TABLE phc_facilities ADD COLUMN updated_at DATETIME')
            # Update all existing rows with current timestamp
            c.execute('UPDATE phc_facilities SET updated_at = datetime("now") WHERE updated_at IS NULL')
            print("✅ 'updated_at' column already exists")

        conn.commit()

        # Verify migration
        print("\n[VERIFICATION] Checking migration...")
        new_columns = c.execute('PRAGMA table_info(phc_facilities)').fetchall()
        new_column_names = [col[1] for col in new_columns]
        print(f"Updated columns: {new_column_names}")

        # Check current PHC facilities
        phcs = c.execute('SELECT id, name, location, status FROM phc_facilities').fetchall()
        print(f"\nCurrent PHC Facilities ({len(phcs)} total):")
        print("-" * 80)
        for phc in phcs:
            print(f"  PHC {phc['id']}: {phc['name']:<20} | {phc['location']:<30} | Status: {phc['status']}")

        conn.close()
        print("\n✅ Migration completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.close()
        return False

if __name__ == '__main__':
    success = migrate_phc_status()
    sys.exit(0 if success else 1)
