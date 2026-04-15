"""
Local Disease Database for SmartTriage
Pre-loaded with common diseases and their severity classifications
Built for offline-first, zero-latency disease recognition
"""

import sqlite3
import os
from datetime import datetime

class LocalDiseaseDatabase:
    """Manages local SQLite database of diseases for offline-first lookups"""

    DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'diseases.db')

    # Comprehensive disease database with severity classifications
    DISEASES = {
        # ==================== CRITICAL (Emergency) ====================
        'heart attack': {'severity': 'CRITICAL', 'confidence': 0.99, 'category': 'Cardiac'},
        'myocardial infarction': {'severity': 'CRITICAL', 'confidence': 0.99, 'category': 'Cardiac'},
        'stroke': {'severity': 'CRITICAL', 'confidence': 0.99, 'category': 'Neurological'},
        'cerebral infarction': {'severity': 'CRITICAL', 'confidence': 0.99, 'category': 'Neurological'},
        'pulmonary embolism': {'severity': 'CRITICAL', 'confidence': 0.99, 'category': 'Respiratory'},
        'aortic dissection': {'severity': 'CRITICAL', 'confidence': 0.99, 'category': 'Cardiac'},
        'meningitis': {'severity': 'CRITICAL', 'confidence': 0.98, 'category': 'Neurological'},
        'encephalitis': {'severity': 'CRITICAL', 'confidence': 0.98, 'category': 'Neurological'},
        'sepsis': {'severity': 'CRITICAL', 'confidence': 0.98, 'category': 'Systemic'},
        'anaphylaxis': {'severity': 'CRITICAL', 'confidence': 0.99, 'category': 'Allergic'},
        'status epilepticus': {'severity': 'CRITICAL', 'confidence': 0.98, 'category': 'Neurological'},
        'acute respiratory distress syndrome': {'severity': 'CRITICAL', 'confidence': 0.98, 'category': 'Respiratory'},
        'ards': {'severity': 'CRITICAL', 'confidence': 0.98, 'category': 'Respiratory'},

        # Cancers (CRITICAL)
        'cancer': {'severity': 'CRITICAL', 'confidence': 0.95, 'category': 'Oncology'},
        'mesothelioma': {'severity': 'CRITICAL', 'confidence': 0.95, 'category': 'Oncology'},
        'lymphoma': {'severity': 'CRITICAL', 'confidence': 0.95, 'category': 'Oncology'},
        'leukemia': {'severity': 'CRITICAL', 'confidence': 0.95, 'category': 'Oncology'},
        'pancreatic cancer': {'severity': 'CRITICAL', 'confidence': 0.95, 'category': 'Oncology'},
        'lung cancer': {'severity': 'CRITICAL', 'confidence': 0.95, 'category': 'Oncology'},
        'brain tumor': {'severity': 'CRITICAL', 'confidence': 0.95, 'category': 'Oncology'},
        'glioblastoma': {'severity': 'CRITICAL', 'confidence': 0.95, 'category': 'Oncology'},

        # ==================== HIGH (Urgent Care) ====================
        'pneumonia': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'Respiratory'},
        'severe pneumonia': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'Respiratory'},
        'acute coronary syndrome': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'Cardiac'},
        'acs': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'Cardiac'},
        'cardiac arrhythmia': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Cardiac'},
        'atrial fibrillation': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Cardiac'},
        'afib': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Cardiac'},
        'acute kidney injury': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Renal'},
        'acute renal failure': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Renal'},
        'hypertensive crisis': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Cardiac'},
        'diabetic ketoacidosis': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'Endocrine'},
        'dka': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'Endocrine'},
        'hypoglycemic emergency': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Endocrine'},
        'severe asthma': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Respiratory'},
        'asthma attack': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Respiratory'},
        'status asthmaticus': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'Respiratory'},
        'acute bronchitis': {'severity': 'HIGH', 'confidence': 0.75, 'category': 'Respiratory'},
        'hemorrhage': {'severity': 'HIGH', 'confidence': 0.95, 'category': 'Trauma'},
        'internal bleeding': {'severity': 'HIGH', 'confidence': 0.95, 'category': 'Trauma'},
        'gastrointestinal bleeding': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'GI'},
        'gi bleed': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'GI'},
        'acute abdomen': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'GI'},
        'appendicitis': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'GI'},
        'cholecystitis': {'severity': 'HIGH', 'confidence': 0.80, 'category': 'GI'},
        'pancreatitis': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'GI'},
        'acute pancreatitis': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'GI'},
        'peritonitis': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'GI'},
        'liver failure': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'Hepatic'},
        'hepatic encephalopathy': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Hepatic'},
        'severe head injury': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'Trauma'},
        'traumatic brain injury': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'Trauma'},
        'tbi': {'severity': 'HIGH', 'confidence': 0.90, 'category': 'Trauma'},
        'spinal cord injury': {'severity': 'HIGH', 'confidence': 0.95, 'category': 'Trauma'},

        # ==================== MEDIUM (Urgent but not Emergency) ====================
        'influenza': {'severity': 'MEDIUM', 'confidence': 0.85, 'category': 'Viral'},
        'flu': {'severity': 'MEDIUM', 'confidence': 0.85, 'category': 'Viral'},
        'covid-19': {'severity': 'MEDIUM', 'confidence': 0.85, 'category': 'Viral'},
        'coronavirus': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Viral'},
        'dengue fever': {'severity': 'MEDIUM', 'confidence': 0.85, 'category': 'Viral'},
        'dengue': {'severity': 'MEDIUM', 'confidence': 0.85, 'category': 'Viral'},
        'malaria': {'severity': 'MEDIUM', 'confidence': 0.85, 'category': 'Infectious'},
        'typhoid': {'severity': 'MEDIUM', 'confidence': 0.85, 'category': 'Infectious'},
        'urinary tract infection': {'severity': 'MEDIUM', 'confidence': 0.75, 'category': 'Infectious'},
        'uti': {'severity': 'MEDIUM', 'confidence': 0.75, 'category': 'Infectious'},
        'pyelonephritis': {'severity': 'MEDIUM', 'confidence': 0.85, 'category': 'Renal'},
        'bronchitis': {'severity': 'MEDIUM', 'confidence': 0.70, 'category': 'Respiratory'},
        'sinusitis': {'severity': 'MEDIUM', 'confidence': 0.60, 'category': 'ENT'},
        'otitis media': {'severity': 'MEDIUM', 'confidence': 0.60, 'category': 'ENT'},
        'ear infection': {'severity': 'MEDIUM', 'confidence': 0.60, 'category': 'ENT'},
        'tonsillitis': {'severity': 'MEDIUM', 'confidence': 0.65, 'category': 'ENT'},
        'pharyngitis': {'severity': 'MEDIUM', 'confidence': 0.65, 'category': 'ENT'},
        'gastroenteritis': {'severity': 'MEDIUM', 'confidence': 0.70, 'category': 'GI'},
        'food poisoning': {'severity': 'MEDIUM', 'confidence': 0.75, 'category': 'GI'},
        'hepatitis': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Hepatic'},
        'hepatitis a': {'severity': 'MEDIUM', 'confidence': 0.75, 'category': 'Hepatic'},
        'hepatitis b': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Hepatic'},
        'hepatitis c': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Hepatic'},
        'cirrhosis': {'severity': 'MEDIUM', 'confidence': 0.85, 'category': 'Hepatic'},
        'inflammatory bowel disease': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'GI'},
        'crohn\'s disease': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'GI'},
        'ulcerative colitis': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'GI'},
        'celiac disease': {'severity': 'MEDIUM', 'confidence': 0.70, 'category': 'GI'},
        'migraine': {'severity': 'MEDIUM', 'confidence': 0.60, 'category': 'Neurological'},
        'severe headache': {'severity': 'MEDIUM', 'confidence': 0.65, 'category': 'Neurological'},
        'epilepsy': {'severity': 'MEDIUM', 'confidence': 0.75, 'category': 'Neurological'},
        'seizure': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Neurological'},
        'Parkinson\'s disease': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Neurological'},
        'Alzheimer\'s disease': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Neurological'},
        'multiple sclerosis': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Neurological'},
        'ms': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Neurological'},
        'amyotrophic lateral sclerosis': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Neurological'},
        'als': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Neurological'},
        'hereditary spastic paraplegia': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Neurological'},
        'hsp': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Neurological'},
        'myocardial infarction': {'severity': 'CRITICAL', 'confidence': 0.99, 'category': 'Cardiac'},
        'endocarditis': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Cardiac'},
        'myocarditis': {'severity': 'HIGH', 'confidence': 0.85, 'category': 'Cardiac'},
        'pericarditis': {'severity': 'MEDIUM', 'confidence': 0.75, 'category': 'Cardiac'},
        'heart failure': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Cardiac'},
        'congestive heart failure': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Cardiac'},
        'chf': {'severity': 'MEDIUM', 'confidence': 0.80, 'category': 'Cardiac'},
        'hypertension': {'severity': 'MEDIUM', 'confidence': 0.70, 'category': 'Cardiac'},
        'high blood pressure': {'severity': 'MEDIUM', 'confidence': 0.70, 'category': 'Cardiac'},
        'diabetes': {'severity': 'MEDIUM', 'confidence': 0.75, 'category': 'Endocrine'},
        'type 1 diabetes': {'severity': 'MEDIUM', 'confidence': 0.75, 'category': 'Endocrine'},
        'type 2 diabetes': {'severity': 'MEDIUM', 'confidence': 0.70, 'category': 'Endocrine'},
        'thyroid disease': {'severity': 'MEDIUM', 'confidence': 0.65, 'category': 'Endocrine'},
        'hyperthyroidism': {'severity': 'MEDIUM', 'confidence': 0.65, 'category': 'Endocrine'},
        'hypothyroidism': {'severity': 'MEDIUM', 'confidence': 0.60, 'category': 'Endocrine'},
        'arthritis': {'severity': 'MEDIUM', 'confidence': 0.65, 'category': 'Rheumatological'},
        'rheumatoid arthritis': {'severity': 'MEDIUM', 'confidence': 0.70, 'category': 'Rheumatological'},
        'osteoarthritis': {'severity': 'MEDIUM', 'confidence': 0.60, 'category': 'Rheumatological'},
        'systemic lupus erythematosus': {'severity': 'MEDIUM', 'confidence': 0.75, 'category': 'Rheumatological'},
        'sle': {'severity': 'MEDIUM', 'confidence': 0.75, 'category': 'Rheumatological'},

        # ==================== LOW (Routine) ====================
        'common cold': {'severity': 'LOW', 'confidence': 0.90, 'category': 'Viral'},
        'cold': {'severity': 'LOW', 'confidence': 0.90, 'category': 'Viral'},
        'cough': {'severity': 'LOW', 'confidence': 0.65, 'category': 'Respiratory'},
        'sore throat': {'severity': 'LOW', 'confidence': 0.75, 'category': 'ENT'},
        'headache': {'severity': 'LOW', 'confidence': 0.70, 'category': 'Neurological'},
        'fever': {'severity': 'LOW', 'confidence': 0.70, 'category': 'General'},
        'body ache': {'severity': 'LOW', 'confidence': 0.60, 'category': 'General'},
        'fatigue': {'severity': 'LOW', 'confidence': 0.55, 'category': 'General'},
        'nausea': {'severity': 'LOW', 'confidence': 0.65, 'category': 'GI'},
        'vomiting': {'severity': 'LOW', 'confidence': 0.70, 'category': 'GI'},
        'diarrhea': {'severity': 'LOW', 'confidence': 0.65, 'category': 'GI'},
        'constipation': {'severity': 'LOW', 'confidence': 0.60, 'category': 'GI'},
        'skin rash': {'severity': 'LOW', 'confidence': 0.65, 'category': 'Dermatological'},
        'acne': {'severity': 'LOW', 'confidence': 0.70, 'category': 'Dermatological'},
        'eczema': {'severity': 'LOW', 'confidence': 0.60, 'category': 'Dermatological'},
        'psoriasis': {'severity': 'LOW', 'confidence': 0.65, 'category': 'Dermatological'},
        'allergies': {'severity': 'LOW', 'confidence': 0.70, 'category': 'Allergic'},
        'hay fever': {'severity': 'LOW', 'confidence': 0.75, 'category': 'Allergic'},
        'seasonal allergies': {'severity': 'LOW', 'confidence': 0.70, 'category': 'Allergic'},
        'anxiety': {'severity': 'LOW', 'confidence': 0.75, 'category': 'Psychiatric'},
        'depression': {'severity': 'MEDIUM', 'confidence': 0.75, 'category': 'Psychiatric'},
        'insomnia': {'severity': 'LOW', 'confidence': 0.70, 'category': 'Psychiatric'},
        'back pain': {'severity': 'LOW', 'confidence': 0.65, 'category': 'Musculoskeletal'},
        'neck pain': {'severity': 'LOW', 'confidence': 0.60, 'category': 'Musculoskeletal'},
        'muscle strain': {'severity': 'LOW', 'confidence': 0.70, 'category': 'Musculoskeletal'},
        'sprain': {'severity': 'LOW', 'confidence': 0.70, 'category': 'Musculoskeletal'},
        'fracture': {'severity': 'MEDIUM', 'confidence': 0.85, 'category': 'Musculoskeletal'},
        'osteoporosis': {'severity': 'MEDIUM', 'confidence': 0.70, 'category': 'Musculoskeletal'},
    }

    @classmethod
    def init_database(cls):
        """Initialize SQLite database with disease data"""
        os.makedirs(os.path.dirname(cls.DB_PATH), exist_ok=True)

        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()

        # Create diseases table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diseases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                severity TEXT NOT NULL,
                confidence REAL NOT NULL,
                category TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Insert diseases
        for disease_name, disease_data in cls.DISEASES.items():
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO diseases (name, severity, confidence, category)
                    VALUES (?, ?, ?, ?)
                ''', (
                    disease_name.lower(),
                    disease_data['severity'],
                    disease_data['confidence'],
                    disease_data['category']
                ))
            except sqlite3.IntegrityError:
                pass  # Disease already exists

        conn.commit()
        conn.close()
        print(f"✅ Local disease database initialized with {len(cls.DISEASES)} entries")

    @classmethod
    def search_disease(cls, disease_name):
        """
        Search for disease in local database
        Returns: {'severity': ..., 'confidence': ..., 'category': ...} or None if not found
        """
        if not os.path.exists(cls.DB_PATH):
            cls.init_database()

        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()

        disease_lower = disease_name.lower().strip()

        cursor.execute('''
            SELECT severity, confidence, category FROM diseases WHERE name = ?
        ''', (disease_lower,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'severity': result[0],
                'confidence': result[1],
                'category': result[2],
                'source': 'LOCAL_DB',
                'disease_name': disease_name
            }

        return None

    @classmethod
    def search_disease_keywords(cls, disease_name):
        """
        Search for disease using STRICT keyword matching with stop-word filtering
        Only returns matches where core clinical terms match (not generic words)

        Filters out: syndrome, disease, disorder, patient, complains, symptoms, related, etc.
        Requires: At least one meaningful clinical word to match
        """
        # STOP WORDS: Generic medical/sentence words to ignore
        STOP_WORDS = {
            'syndrome', 'disease', 'disorder', 'condition', 'illness',
            'patient', 'complains', 'symptoms', 'related', 'signs',
            'of', 'the', 'to', 'a', 'an', 'and', 'or', 'is', 'are',
            'with', 'in', 'on', 'at', 'by', 'from', 'for', 'has', 'have',
            'about', 'as', 'his', 'her', 'their', 'my', 'your',
            'presents', 'presents', 'present', 'experiencing', 'experience',
            'suffers', 'suffer', 'suffering', 'diagnosed', 'diagnosis',
            'acute', 'chronic', 'severe', 'mild', 'moderate'
        }

        if not os.path.exists(cls.DB_PATH):
            cls.init_database()

        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()

        disease_lower = disease_name.lower().strip()

        # Split input into keywords
        all_keywords = disease_lower.split()

        # Filter out stop words - keep only meaningful clinical terms
        clinical_keywords = [kw for kw in all_keywords if kw not in STOP_WORDS and len(kw) > 2]

        print(f"[KEYWORD-ANALYSIS] Input: '{disease_name}'")
        print(f"[KEYWORD-ANALYSIS] Raw keywords: {all_keywords}")
        print(f"[KEYWORD-ANALYSIS] Clinical keywords (after filtering): {clinical_keywords}")

        # If all keywords were stop words, return no matches (trigger Layer 2)
        if not clinical_keywords:
            print(f"[KEYWORD-ANALYSIS] ⚠️ No clinical keywords found - returning None to trigger Layer 2 (Wikipedia API)")
            conn.close()
            return {}  # Empty dict = no match, fall through to API

        # Score matches based on clinical keyword presence
        matches = []
        for keyword in clinical_keywords:
            cursor.execute('''
                SELECT name, severity, confidence, category FROM diseases
                WHERE name LIKE ?
            ''', (f'%{keyword}%',))
            matches.extend(cursor.fetchall())

        conn.close()

        # Strict filtering: Only return HIGH confidence matches where clinical terms align
        unique_matches = {}
        for name, severity, confidence, category in matches:
            if name not in unique_matches:
                # Calculate match strength: how many clinical keywords are in the disease name?
                clinical_matches = sum(1 for kw in clinical_keywords if kw in name or name in kw)
                match_strength = clinical_matches / len(clinical_keywords) if clinical_keywords else 0

                # STRICT: Only accept if >60% of clinical keywords match disease name
                if match_strength >= 0.6:
                    unique_matches[name] = {
                        'severity': severity,
                        'confidence': confidence,
                        'category': category,
                        'source': 'LOCAL_DB_KEYWORD',
                        'disease_name': name,
                        'match_strength': match_strength
                    }
                    print(f"[KEYWORD-ANALYSIS] ✅ Match strength {match_strength:.0%}: '{name}' ({severity})")
                else:
                    print(f"[KEYWORD-ANALYSIS] ❌ Rejected (strength {match_strength:.0%}): '{name}' - needs {clinical_keywords} match")

        if not unique_matches:
            print(f"[KEYWORD-ANALYSIS] ⚠️ No strict matches found - returning empty dict to trigger Layer 2 (Wikipedia API)")

        return unique_matches

    @classmethod
    def get_statistics(cls):
        """Get database statistics"""
        if not os.path.exists(cls.DB_PATH):
            cls.init_database()

        conn = sqlite3.connect(cls.DB_PATH)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM diseases')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT severity, COUNT(*) FROM diseases GROUP BY severity')
        by_severity = dict(cursor.fetchall())

        conn.close()

        return {
            'total_diseases': total,
            'by_severity': by_severity
        }


# Initialize database on module load
if __name__ == '__main__':
    LocalDiseaseDatabase.init_database()
    stats = LocalDiseaseDatabase.get_statistics()
    print(f"Database Statistics: {stats}")
