import sqlite3
from datetime import datetime, timedelta

def seed_pharmacy():
    db_path = 'triage.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    rows = cursor.execute("SELECT DISTINCT phc_id FROM users WHERE phc_id IS NOT NULL AND phc_id != ''").fetchall()
    phc_ids = [r[0] for r in rows]
    print(f'Seeding for {len(phc_ids)} PHC IDs...')

    for phc_id in phc_ids:
        cursor.execute('DELETE FROM inventory WHERE phc_id = ?', (phc_id,))
        today = datetime.now()
        items = [
            ('Paracetamol 500mg', 450, 100, 'Medicine', 'TN-4411', (today + timedelta(days=400)).strftime('%Y-%m-%d'), phc_id),
            ('Amoxicillin 500mg', 50, 100, 'Medicine', 'TN-4029', (today + timedelta(days=20)).strftime('%Y-%m-%d'), phc_id),
            ('Cetirizine 10mg', 200, 50, 'Medicine', 'TN-9922', (today + timedelta(days=600)).strftime('%Y-%m-%d'), phc_id),
            ('Dicyclomine', 150, 40, 'Medicine', 'TN-3030', (today + timedelta(days=300)).strftime('%Y-%m-%d'), phc_id),
            ('Ranitidine 150mg', 80, 50, 'Medicine', 'TN-7711', (today - timedelta(days=5)).strftime('%Y-%m-%d'), phc_id),
            ('Metformin 500mg', 12, 100, 'Medicine', 'TN-8812', (today + timedelta(days=45)).strftime('%Y-%m-%d'), phc_id),
            ('Ondansetron 4mg', 300, 60, 'Medicine', 'TN-2211', (today + timedelta(days=500)).strftime('%Y-%m-%d'), phc_id),
            ('Anti-Venom (ASV)', 4, 10, 'Medicine', 'TN-EMERG-1', (today + timedelta(days=120)).strftime('%Y-%m-%d'), phc_id),
        ]
        for item in items:
            cursor.execute('''
                INSERT INTO inventory (item_name, quantity, min_threshold, category, batch_id, expiry_date, phc_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', item)

        cursor.execute('DELETE FROM waste_logs WHERE phc_id = ?', (phc_id,))
        waste_items = [
            (phc_id, 'Yellow', 4.5, 'Ramky Driver A'),
            (phc_id, 'Red', 8.2, 'Ramky Driver B'),
            (phc_id, 'White', 1.2, 'Ramky Driver A')
        ]
        for item in waste_items:
            cursor.execute('INSERT INTO waste_logs (phc_id, bag_color, weight, collected_by) VALUES (?, ?, ?, ?)', item)

        cursor.execute('DELETE FROM stock_logs WHERE phc_id = ?', (phc_id,))
        stock_log_items = [
            (phc_id, 'Paracetamol 500mg', 'SUBTRACT', -45, 450, 'Digital Assistant'),
            (phc_id, 'Amoxicillin 500mg', 'SUBTRACT', -20, 50, 'Digital Assistant'),
            (phc_id, 'Cetirizine 10mg', 'SUBTRACT', -35, 200, 'Digital Assistant')
        ]
        for log in stock_log_items:
            cursor.execute('''
                INSERT INTO stock_logs (phc_id, item_name, action, quantity_changed, balance_after, staff_name, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ''', log)

    conn.commit()
    conn.close()
    print('Pharmacy seeded successfully!')

if __name__ == '__main__':
    seed_pharmacy()

