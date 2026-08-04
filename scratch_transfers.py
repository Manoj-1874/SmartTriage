import sqlite3
import pprint

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

# Let's find pending transfers for branch3
print("=== PENDING TRANSFERS ===")
transfers = conn.execute("SELECT * FROM phc_stock_transfers WHERE status = 'PENDING'").fetchall()
for t in transfers:
    print(dict(t))

# Let's also find the user branch3_pharmacist@phc.in
print("\n=== USER ===")
user = conn.execute("SELECT * FROM users WHERE email = 'branch3_pharmacist@phc.in'").fetchone()
if user:
    print(dict(user))
