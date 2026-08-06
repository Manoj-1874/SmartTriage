import sqlite3

conn = sqlite3.connect('smart_triage.db')
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS health_campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'Upcoming',
        beneficiaries INTEGER DEFAULT 0,
        start_date DATETIME,
        district TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

campaigns = [
    ('Polio Vaccination Drive', 'Annual polio vaccination for children under 5 across all blocks.', 'Active', 1250, '2026-08-01', 'Tirunelveli'),
    ('Maternal Nutrition Camp', 'Providing iron and folic acid supplements to pregnant women.', 'Active', 450, '2026-08-05', 'Tirunelveli'),
    ('Dengue Awareness & Fogging', 'Door to door awareness and fogging in high-risk zones.', 'Upcoming', 0, '2026-09-01', 'Tirunelveli'),
    ('Tuberculosis Screening', 'Active case finding and sputum collection drive.', 'Completed', 800, '2026-06-15', 'Tirunelveli')
]

c.executemany('''
    INSERT INTO health_campaigns (title, description, status, beneficiaries, start_date, district)
    VALUES (?, ?, ?, ?, ?, ?)
''', campaigns)

conn.commit()
conn.close()
print('Campaigns added successfully.')
