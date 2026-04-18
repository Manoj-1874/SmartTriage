#!/usr/bin/env python3
"""
Initialize the database with all tables
"""
import sys
import os

# Add parent directory to path so we can import from utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.database import DatabaseManager

# Initialize the database
db = DatabaseManager(db_type='sqlite', db_path='database.db')

print("Initializing database...")
db.init_database()
print("✅ Database initialized successfully!")

# Check if tables were created
conn = db.get_connection()
cursor = conn.cursor()

# Get list of tables
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f"\n✅ Created {len(tables)} tables:")
for table in tables:
    count = cursor.execute(f"SELECT COUNT(*) FROM {table[0]}").fetchone()[0]
    print(f"  - {table[0]} ({count} rows)")

conn.close()
print("\n✅ Database initialization complete!")
