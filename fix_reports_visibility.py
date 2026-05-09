import sqlite3
import os

db_path = 'triage.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("Redistributing patient data across all PHCs...")

# 1. Get all patients
patients = c.execute("SELECT id FROM users WHERE role='patient'").fetchall()
phc_ids = [1, 2, 3, 4, 5, 6, 7]

for i, p in enumerate(patients):
    phc_id = phc_ids[i % len(phc_ids)]
    # Update user's PHC
    c.execute("UPDATE users SET phc_id = ? WHERE id = ?", (phc_id, p[0]))
    # Update user's logs
    c.execute("UPDATE patient_logs SET phc_id = ? WHERE user_id = ?", (phc_id, p[0]))

conn.commit()
conn.close()
print("Data redistribution complete. All PHCs now have active reports.")
