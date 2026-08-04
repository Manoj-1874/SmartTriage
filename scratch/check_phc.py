import sqlite3
conn=sqlite3.connect('triage.db')
f=conn.execute('SELECT id FROM phc_facilities WHERE name="Govt PHC Karur - Branch 3"').fetchone()
print('Facility:', f[0] if f else 'None')
if f:
 u=conn.execute('SELECT username, password FROM users WHERE role="pharmacist" AND phc_id=?', (f[0],)).fetchone()
 print('User:', u)
