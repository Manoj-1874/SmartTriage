import sys
import random
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import app
from utils.integrated_dual_brain_risk import IntegratedDualBrainRisk

# 1. Generate 1000 synthetic scenarios
symptom_pool = {
    'routine': ['mild headache', 'runny nose', 'mild cough', 'slight fatigue', 'itchy skin', 'sore throat'],
    'priority': ['fever and chills', 'moderate abdominal pain', 'vomiting', 'dizziness', 'joint pain', 'blurred vision'],
    'high': ['teenage pregnancy', 'severe chronic pain', 'blood in urine', 'persistent vomiting', 'severe weakness'],
    'critical': ['crushing chest pain', 'unbearable stomach pain', 'active bleeding', 'sudden weakness in left arm', 'unable to breathe', 'seizures']
}

def generate_patient(i):
    # Randomly pick a severity profile to generate realistic vitals/symptoms
    profile = random.choices(['routine', 'priority', 'high', 'critical'], weights=[40, 30, 20, 10])[0]
    
    if profile == 'routine':
        sys_bp, dia_bp = random.randint(100, 130), random.randint(60, 85)
        hr = random.randint(60, 90)
        spo2 = random.randint(96, 100)
        temp = round(random.uniform(97.0, 99.2), 1)
        rr = random.randint(12, 18)
    elif profile == 'priority':
        sys_bp, dia_bp = random.randint(120, 150), random.randint(80, 95)
        hr = random.randint(80, 110)
        spo2 = random.randint(94, 98)
        temp = round(random.uniform(98.5, 102.0), 1)
        rr = random.randint(16, 22)
    elif profile == 'high':
        sys_bp, dia_bp = random.randint(140, 180), random.randint(90, 110)
        hr = random.randint(100, 130)
        spo2 = random.randint(90, 95)
        temp = round(random.uniform(99.0, 104.0), 1)
        rr = random.randint(20, 28)
    else: # critical
        sys_bp, dia_bp = random.choices([(random.randint(60, 90), random.randint(40, 60)), (random.randint(180, 220), random.randint(110, 130))])[0]
        hr = random.choices([random.randint(40, 55), random.randint(120, 160)])[0]
        spo2 = random.randint(75, 90)
        temp = round(random.uniform(96.0, 105.0), 1)
        rr = random.choices([random.randint(8, 10), random.randint(28, 40)])[0]

    return {
        'id': i,
        'profile': profile,
        'age': random.randint(1, 99),
        'gender': random.choice(['Male', 'Female']),
        'sys_bp': sys_bp, 'dia_bp': dia_bp, 'hr': hr, 'spo2': spo2, 'temp_f': temp, 'rr': rr,
        'symptoms': random.choice(symptom_pool[profile]),
        'disease_input': ''
    }

patients = [generate_patient(i) for i in range(10000)]

# Load models
print("Loading core models for mass testing...")

import logging
logging.getLogger().setLevel(logging.WARNING)

encoders, xgb_risk_model, scaler, feature_names, exp_brain = app.load_models_locally()
risk_engine = IntegratedDualBrainRisk(xgb_model=xgb_risk_model, scaler=scaler, feature_names=feature_names, bert_model=exp_brain, encoders=encoders)

# Mock network calls to avoid rate limits / 30 min runtime
from utils.universal_disease_knowledge import MedicalDiseaseAPI, SNOMEDIntegration
original_web = MedicalDiseaseAPI.get_disease_from_web
original_snomed = SNOMEDIntegration.search_disease

def mock_web(term): return None
def mock_snomed(term): return {'found': False}

MedicalDiseaseAPI.get_disease_from_web = mock_web
SNOMEDIntegration.search_disease = mock_snomed

print("Running 10000 scenarios through Dual-Brain Risk Engine...")
start_time = time.time()
results = []

def evaluate(p):
    res = risk_engine.assess_patient_with_disease_context(
        disease_input=p['disease_input'], symptoms=p['symptoms'], age=p['age'], gender=p['gender'],
        sys_bp=p['sys_bp'], dia_bp=p['dia_bp'], hr=p['hr'], temp_f=p['temp_f'], spo2=p['spo2'], respiration_rate=p['rr'],
        pain_intensity=5, symptom_duration_hours=24, comorbidities=""
    )
    p['final_risk'] = res['final_risk']['risk_category']
    p['final_score'] = res['final_risk']['final_risk_score']
    p['target'] = res['final_risk']['referral_target']
    p['bert_score'] = res['bert_analysis'].get('risk_score', 0)
    p['xgb_score'] = res['xgboost_analysis'].get('risk_score', 0)
    return p

# Thread pool for fast evaluation
with ThreadPoolExecutor(max_workers=16) as executor:
    results = list(executor.map(evaluate, patients))

time_taken = time.time() - start_time
print(f"Completed 10000 evaluations in {time_taken:.2f} seconds.")

df = pd.DataFrame(results)

# Analysis
total = len(df)
critical = len(df[df['final_risk'] == 'CRITICAL'])
high = len(df[df['final_risk'] == 'HIGH'])
medium = len(df[df['final_risk'] == 'MEDIUM'])
low = len(df[df['final_risk'] == 'LOW'])

# Edge cases check
# Critical profile patients that were marked as LOW or MEDIUM
missed_criticals = df[(df['profile'] == 'critical') & (df['final_risk'].isin(['LOW', 'MEDIUM']))]
# Routine profile patients that were marked as CRITICAL (False positives)
false_alarms = df[(df['profile'] == 'routine') & (df['final_risk'] == 'CRITICAL')]

report = f"""
# 10000-Scenario Edge Case Deep Scan
**Time Taken:** {time_taken:.2f} seconds

## Overall Classification Distribution
- **CRITICAL:** {critical} ({(critical/total)*100:.1f}%)
- **HIGH:** {high} ({(high/total)*100:.1f}%)
- **MEDIUM:** {medium} ({(medium/total)*100:.1f}%)
- **LOW:** {low} ({(low/total)*100:.1f}%)

## Edge Case Analysis

### 1. Missed Criticals (False Negatives)
**Count:** {len(missed_criticals)} / {len(df[df['profile'] == 'critical'])}
These are patients with objectively critical vitals (e.g. SpO2 < 90, Sys BP > 180) or severe symptoms that the model incorrectly classified as LOW or MEDIUM.
"""

if not missed_criticals.empty:
    report += "\n" + missed_criticals[['sys_bp', 'hr', 'spo2', 'symptoms', 'final_risk']].to_markdown() + "\n"
else:
    report += "\n*Excellent: Zero missed critical emergencies detected!*\n"

report += f"""
### 2. False Alarms (Routine marked as Critical)
**Count:** {len(false_alarms)} / {len(df[df['profile'] == 'routine'])}
These are patients with perfect vitals and mild symptoms that the model aggressively marked as CRITICAL.
"""

if not false_alarms.empty:
    report += "\n" + false_alarms[['sys_bp', 'hr', 'spo2', 'symptoms', 'final_risk']].to_markdown() + "\n"
else:
    report += "\n*Excellent: Zero false alarms detected!*\n"

# Save to artifact
artifact_path = r"C:\Users\HP\.gemini\antigravity-ide\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\stress_test_report_10000.md"
with open(artifact_path, 'w') as f:
    f.write(report)

print(f"Report saved to {artifact_path}")
