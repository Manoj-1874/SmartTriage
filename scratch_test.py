import sqlite3

conn = sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row

monthly = conn.execute("""
    SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
    FROM users
    WHERE role = 'patient'
    GROUP BY strftime('%Y-%m', created_at)
    ORDER BY month DESC
    LIMIT 12
""").fetchall()

disease = conn.execute("""
    SELECT recommended_specialist, COUNT(*) as count
    FROM patient_logs
    WHERE recommended_specialist IS NOT NULL AND recommended_specialist != ''
    GROUP BY recommended_specialist
    ORDER BY count DESC
    LIMIT 10
""").fetchall()

print(f"Monthly stats: {len(monthly)}")
print(f"Disease stats: {len(disease)}")

for row in monthly:
    print(dict(row))

for row in disease:
    print(dict(row))

conn.close()
