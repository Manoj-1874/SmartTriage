import logging
import sys
import os
import joblib
from transformers import pipeline

# Configure logging to see what the model does
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    stream=sys.stdout
)

# Set the project root in sys.path
sys.path.append(os.getcwd())

from utils.integrated_dual_brain_risk import IntegratedDualBrainRisk

def load_actual_models():
    """Attempt to load real models for the test"""
    print("[INIT] Loading real AI brains...")
    
    xgb_model = None
    scaler = None
    feature_names = []
    bert_model = None
    encoders = {}
    
    # Load XGBoost & Scaler & Encoders
    try:
        model_assets = joblib.load("models/triage_assets_mingled.pkl")
        xgb_model = model_assets.get('xgb_model') or model_assets.get('model')
        scaler = model_assets.get('scaler')
        feature_names = model_assets.get('feature_names') or model_assets.get('features', [])
        encoders = model_assets.get('encoders', {})
        print("[OK] XGBoost Brain Online")
    except Exception as e:
        print(f"[WARN] XGBoost load failed: {e}")
        
    # Load BERT
    try:
        # Note: This might take a few seconds
        bert_model = pipeline("text-classification", model="models/experimental_brain", tokenizer="models/experimental_brain")
        print("[OK] BERT Brain Online")
    except Exception as e:
        print(f"[WARN] BERT load failed: {e}")
        
    return xgb_model, scaler, feature_names, bert_model, encoders

def run_test_assessment(assessment_system, disease_name, symptoms, vitals):
    print("\n" + "="*80)
    print(f"--- TESTING ASSESSMENT FOR: {disease_name or 'Unknown Disease'} ---")
    print("="*80)
    
    try:
        result = assessment_system.assess_patient_with_disease_context(
            disease_input=disease_name,
            symptoms=symptoms,
            age=vitals['age'],
            gender=vitals['gender'],
            sys_bp=vitals['sys_bp'],
            dia_bp=vitals['dia_bp'],
            hr=vitals['hr'],
            temp_f=vitals['temp_f'],
            spo2=vitals['spo2'],
            respiration_rate=vitals['rr'],
            pain_intensity=vitals['pain'],
            symptom_duration_hours=vitals['duration']
        )
        
        print("\n--- FINAL RESULTS ---")
        print(f"Identified Disease: {result['disease_recognition']['final_risk'].get('disease_identified')}")
        print(f"Source Used: {result['disease_recognition'].get('source_used')}")
        print(f"Risk Category: {result['final_risk'].get('risk_category')}")
        print(f"Urgency: {result['final_risk'].get('urgency')}")
        print("\n--- REASONING ---")
        print(result['final_risk'].get('reasoning'))
        
    except Exception as e:
        print(f"Error during assessment: {str(e)}")

if __name__ == "__main__":
    # Load real brains
    xgb_m, scl, feat, bert_m, encs = load_actual_models()
    
    # Initialize system
    system = IntegratedDualBrainRisk(
        xgb_model=xgb_m,
        scaler=scl,
        feature_names=feat,
        bert_model=bert_m,
        encoders=encs
    )

    # Test Case 1: Known Disease
    run_test_assessment(
        system,
        disease_name="Sepsis",
        symptoms="Extremely high fever, shivering, and rapid breathing",
        vitals={
            'age': 72, 'gender': 'Male', 'sys_bp': 85, 'dia_bp': 55,
            'hr': 130, 'temp_f': 104.1, 'spo2': 91, 'rr': 28,
            'pain': 8, 'duration': 6
        }
    )

    # Test Case 2: Rare Disease (Wikipedia Fallback)
    run_test_assessment(
        system,
        disease_name="Takotsubo cardiomyopathy",
        symptoms="Intense chest pain and shortness of breath after extreme emotional stress",
        vitals={
            'age': 58, 'gender': 'Female', 'sys_bp': 105, 'dia_bp': 65,
            'hr': 95, 'temp_f': 98.8, 'spo2': 97, 'rr': 20,
            'pain': 9, 'duration': 1
        }
    )
