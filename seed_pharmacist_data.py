import sqlite3
from datetime import datetime, timedelta
import random

db_path = 'triage.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

phc_ids = [1, 2, 3, 4, 5, 6, 7]
items = [
    ('Paracetamol', 'Tablets', 800, 150),
    ('Amoxicillin 250mg', 'Capsules', 500, 100),
    ('Insulin (Regular)', 'Vials', 50, 10),
    ('Anti-Venom (ASV)', 'Vials', 15, 5),
    ('Oxytocin Inj', 'Ampoules', 100, 20),
    ('IV Fluids (NS)', 'Bottles', 200, 50),
    ('ORS Packets', 'Sachets', 300, 50),
    ('Disposable Syringes', 'Units', 500, 100)
]

print("Seeding PHC Inventory & Logs...")
for phc_id in phc_ids:
    for name, unit, qty, thresh in items:
        # Upsert inventory
        exists = c.execute("SELECT id FROM inventory WHERE item_name = ? AND phc_id = ?", (name, phc_id)).fetchone()
        if not exists:
            c.execute("""
                INSERT INTO inventory (item_name, category, quantity, min_threshold, phc_id, status)
                VALUES (?, ?, ?, ?, ?, 'ACTIVE')
            """, (name, unit, qty, thresh, phc_id))
        else:
            c.execute("UPDATE inventory SET quantity = ?, min_threshold = ? WHERE id = ?", (qty, thresh, exists[0]))
            
        # Add rich history for this item
        balance = qty
        # 10 historical dispenses
        for i in range(10, 0, -1):
            change = random.randint(-40, -5)
            balance += change
            c.execute("""
                INSERT INTO stock_logs (item_name, phc_id, action, quantity_changed, balance_after, staff_name, timestamp)
                VALUES (?, ?, 'DISPENSED', ?, ?, 'Pharmacist Auto-Sync', ?)
            """, (name, phc_id, change, balance, (datetime.now() - timedelta(hours=i*4)).isoformat()))

print("Seeding Waste Logs...")
for phc_id in phc_ids:
    for i in range(3):
        c.execute("""
            INSERT INTO waste_logs (phc_id, bag_color, weight, collected_by, timestamp)
            VALUES (?, ?, ?, 'Ramky Driver', ?)
        """, (phc_id, random.choice(['Yellow', 'Red', 'Blue', 'White']), round(random.uniform(2.5, 8.0), 1), (datetime.now() - timedelta(days=i*2)).isoformat()))

conn.commit()
conn.close()
print("Final Pharmacist data seeding complete.")
