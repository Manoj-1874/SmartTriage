import sys
import app
from utils.integrated_dual_brain_risk import IntegratedDualBrainRisk

print("Loading models...")
encoders, xgb_risk_model, scaler, feature_names, exp_brain = app.load_models_locally()

risk_engine = IntegratedDualBrainRisk(
    xgb_model=xgb_risk_model,
    scaler=scaler,
    feature_names=feature_names,
    bert_model=exp_brain,
    encoders=encoders
)

scenarios = [
    {
        "name": "Healthy 20yo (Routine)",
        "age": 20, "gender": "Male", "sys_bp": 120, "dia_bp": 80, "hr": 72, "temp_f": 98.6, "spo2": 98, "rr": 16,
        "symptoms": "Mild headache", "disease_input": ""
    },
    {
        "name": "Textbook Heart Attack (Critical)",
        "age": 55, "gender": "Male", "sys_bp": 160, "dia_bp": 100, "hr": 110, "temp_f": 99.0, "spo2": 92, "rr": 24,
        "symptoms": "crushing chest pain radiating to jaw", "disease_input": ""
    },
    {
        "name": "Maternal Emergency (Eclampsia)",
        "age": 28, "gender": "Female", "sys_bp": 180, "dia_bp": 115, "hr": 95, "temp_f": 98.6, "spo2": 97, "rr": 20,
        "symptoms": "pregnancy, severe headache, blurry vision, ecclampsia", "disease_input": "OBGYN"
    },
    {
        "name": "Silent Hypoxia (Vitals only alarm)",
        "age": 45, "gender": "Male", "sys_bp": 110, "dia_bp": 70, "hr": 90, "temp_f": 99.5, "spo2": 85, "rr": 28,
        "symptoms": "feeling a bit tired", "disease_input": ""
    },
    {
        "name": "Social Risk / Hidden Priority",
        "age": 16, "gender": "Female", "sys_bp": 115, "dia_bp": 75, "hr": 80, "temp_f": 98.6, "spo2": 99, "rr": 16,
        "symptoms": "teenage pregnancy, dropout, feeling weak", "disease_input": ""
    },
    {
        "name": "User Screenshot Case (Chest/Shoulder Pain)",
        "age": 20, "gender": "Male", "sys_bp": 110, "dia_bp": 70, "hr": 80, "temp_f": 99.0, "spo2": 99, "rr": 18,
        "symptoms": "Slightly pain near the chest, shoulder pain", "disease_input": ""
    }
]

print("\n| Scenario | Symptoms | Vitals | BERT | XGB | Final Risk (Score) | Target |")
print("|----------|----------|--------|------|-----|-------------------|--------|")

for s in scenarios:
    res = risk_engine.assess_patient_with_disease_context(
        disease_input=s['disease_input'],
        symptoms=s['symptoms'],
        age=s['age'], gender=s['gender'],
        sys_bp=s['sys_bp'], dia_bp=s['dia_bp'], hr=s['hr'], temp_f=s['temp_f'],
        spo2=s['spo2'], respiration_rate=s['rr'],
        pain_intensity=5, symptom_duration_hours=24, comorbidities=""
    )
    
    bert = res['bert_analysis']['risk_label']
    xgb = res['xgboost_analysis']['risk_label']
    final = res['final_risk']['risk_category']
    score = res['final_risk']['final_risk_score'] * 100
    target = res['final_risk']['referral_target']
    
    vitals_str = f"BP:{s['sys_bp']}/{s['dia_bp']} HR:{s['hr']} SpO2:{s['spo2']}"
    
    print(f"| {s['name']} | {s['symptoms'][:30]}... | {vitals_str} | {bert} | {xgb} | **{final}** ({score:.0f}) | {target} |")
