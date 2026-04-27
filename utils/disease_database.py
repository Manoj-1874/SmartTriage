"""
Local Disease Database for SmartTriage
Strict Exact Matching + Statistics Support (v3.7)
"""

import sqlite3
import os

class LocalDiseaseDatabase:
    DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'diseases.db')

    DISEASES = {
        'malaria': {'severity': 'MEDIUM', 'category': 'Infectious'},
        'dengue': {'severity': 'MEDIUM', 'category': 'Viral'},
        'typhoid': {'severity': 'MEDIUM', 'category': 'Infectious'},
        'cholera': {'severity': 'HIGH', 'category': 'Infectious'},
        'pneumonia': {'severity': 'HIGH', 'category': 'Respiratory'},
        'asthma': {'severity': 'MEDIUM', 'category': 'Respiratory'},
        'diabetes': {'severity': 'MEDIUM', 'category': 'Metabolic'},
        'hypertension': {'severity': 'MEDIUM', 'category': 'Cardiac'},
        'cough': {'severity': 'LOW', 'category': 'Respiratory'},
        'fever': {'severity': 'LOW', 'category': 'General'},
        'fatigue': {'severity': 'LOW', 'category': 'General'},
        'sore throat': {'severity': 'LOW', 'category': 'ENT'},
        'headache': {'severity': 'LOW', 'category': 'Neurological'}
    }

    @classmethod
    def init_database(cls):
        os.makedirs(os.path.dirname(cls.DB_PATH), exist_ok=True)
        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS diseases')
        cursor.execute('''CREATE TABLE diseases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            severity TEXT NOT NULL,
            category TEXT NOT NULL
        )''')
        for name, data in cls.DISEASES.items():
            cursor.execute('INSERT INTO diseases (name, severity, category) VALUES (?, ?, ?)',
                         (name.lower(), data['severity'], data['category']))
        conn.commit()
        conn.close()
        print(f"✅ Local database initialized: {len(cls.DISEASES)} entries.")

    @classmethod
    def search_disease(cls, disease_name):
        if not os.path.exists(cls.DB_PATH): cls.init_database()
        disease_lower = str(disease_name).lower().strip()
        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT severity, category FROM diseases WHERE name = ?', (disease_lower,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {'severity': result[0], 'category': result[1], 'disease_name': disease_name}
        return None

    @classmethod
    def get_statistics(cls):
        """Returns database statistics for app startup logging (Fixed keys for app.py)"""
        if not os.path.exists(cls.DB_PATH): cls.init_database()
        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM diseases')
        total = cursor.fetchone()[0]
        cursor.execute('SELECT severity, COUNT(*) FROM diseases GROUP BY severity')
        by_sev = dict(cursor.fetchall())
        conn.close()
        # app.py expects 'total_diseases'
        return {'total_diseases': total, 'by_severity': by_sev}

if __name__ == '__main__':
    LocalDiseaseDatabase.init_database()
