import sqlite3

db_path = 'triage.db'
conn = sqlite3.connect(db_path)
print("Auditing stock_logs for Paracetamol...")
logs = conn.execute("SELECT DISTINCT item_name, phc_id FROM stock_logs WHERE item_name LIKE 'Paracetamol%'").fetchall()
for l in logs:
    print(f"Found: {l[0]} in PHC {l[1]}")

print("\nChecking waste_logs schema...")
info = conn.execute("PRAGMA table_info(waste_logs)").fetchall()
for i in info:
    print(i)
conn.close()
