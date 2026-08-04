import sqlite3
conn=sqlite3.connect('triage.db')
conn.row_factory = sqlite3.Row
print('Referrals:')
for r in conn.execute('SELECT * FROM referrals WHERE patient_id="STOCK_TRANSFER"').fetchall():
    print(dict(r))
print('\nInventory 163:')
for r in conn.execute('SELECT * FROM inventory WHERE phc_id=163').fetchall():
    print(dict(r))
