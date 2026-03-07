"""
Test comprehensive scenarios to verify triage system accuracy
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import xgb_risk_model, encoders, scaler, feature_names, exp_brain
from utils.triage_override import should_override_to_low_risk
import pandas as pd
import numpy as np


def test_scenario(name, age, sys_bp, dia_bp, hr, temp_f, symptoms, history, expected_risk):
    """Test a single triage scenario"""
    print(f"\n{'='*70}")
    print(f"SCENARIO: {name}")
    print(f"{'='*70}")
    print(f"Age: {age}, Gender: Male")
    print(f"Vitals: BP={sys_bp}/{dia_bp}, HR={hr}, Temp={temp_f}°F")
    print(f"Symptoms: {symptoms}")
    print(f"History: {history}")
    print("-" * 70)

    # Step 1: Check override
    should_override, override_reason, health_score = should_override_to_low_risk(
        age, sys_bp, dia_bp, hr, temp_f, symptoms, history
    )

    if should_override:
        final_risk = "LOW"
        print(f"✅ OVERRIDE TRIGGERED: {override_reason}")
        print(f"   Health Score: {health_score}/100")
        print(f"   Final Risk: {final_risk}")
    else:
        print(f"⚙️  No override: {override_reason}")

        # Step 2: XGBoost prediction
        temp_c = (temp_f - 32) * 5 / 9
        gender_enc = encoders['Gender'].transform(['Male'])[0]
        symptom_enc = encoders['Symptoms'].transform([symptoms])[0] if symptoms in encoders['Symptoms'].classes_ else 0
        history_enc = encoders['Pre_Conditions'].transform([history])[0] if history in encoders['Pre_Conditions'].classes_ else 0

        patient_df = pd.DataFrame([[age, gender_enc, symptom_enc, sys_bp, dia_bp, hr, temp_c, history_enc]],
                                 columns=feature_names)
        patient_scaled = scaler.transform(patient_df)
        xgb_probs = xgb_risk_model.predict_proba(patient_scaled)[0]
        xgb_risk = encoders['Risk_Level'].inverse_transform([np.argmax(xgb_probs)])[0].upper()

        print(f"   XGBoost: {xgb_risk} (LOW={xgb_probs[0]:.1%}, MED={xgb_probs[1]:.1%}, HIGH={xgb_probs[2]:.1%})")

        # Step 3: BERT check
        bert_res = exp_brain(symptoms)[0]
        # Increased threshold from 0.5 to 0.55 to reduce over-escalation
        is_bert_emergency = (bert_res['label'] == 'LABEL_1' and bert_res['score'] > 0.55)
        critical_words = ['distress', 'hemorrhage', 'speech', 'crushing', 'chest pain', 'unconscious']
        semantic_emergency = any(word in symptoms.lower() for word in critical_words) or is_bert_emergency

        print(f"   BERT Emergency: {semantic_emergency} (label={bert_res['label']}, score={bert_res['score']:.1%})")

        # Step 4: Consensus
        if semantic_emergency and xgb_risk != "HIGH":
            final_risk = "HIGH (SAFETY OVERRIDE)"
        elif xgb_risk == "HIGH":
            final_risk = "HIGH"
        elif xgb_risk == "MEDIUM":
            final_risk = "MEDIUM"
        else:
            final_risk = "LOW"

        print(f"   Final Risk: {final_risk}")

    # Verify against expected
    if expected_risk in final_risk or final_risk in expected_risk:
        print(f"✅ PASS - Expected: {expected_risk}, Got: {final_risk}")
        return True
    else:
        print(f"❌ FAIL - Expected: {expected_risk}, Got: {final_risk}")
        return False


if __name__ == '__main__':
    print("\n" + "="*70)
    print("COMPREHENSIVE TRIAGE SYSTEM VALIDATION")
    print("="*70)

    scenarios = [
        # HEALTHY SCENARIOS (Should be LOW)
        {
            'name': '1. Perfect Health - Routine Checkup',
            'age': 30, 'sys_bp': 120, 'dia_bp': 80, 'hr': 70, 'temp_f': 98.6,
            'symptoms': 'Routine checkup', 'history': 'None',
            'expected_risk': 'LOW'
        },
        {
            'name': '2. Reports "Fever" but Normal Temperature',
            'age': 24, 'sys_bp': 120, 'dia_bp': 80, 'hr': 72, 'temp_f': 98.6,
            'symptoms': 'Fever and cough', 'history': 'None',
            'expected_risk': 'LOW'
        },
        {
            'name': '3. Mild Symptoms, Healthy Vitals',
            'age': 35, 'sys_bp': 118, 'dia_bp': 78, 'hr': 68, 'temp_f': 98.4,
            'symptoms': 'Mild headache and fatigue', 'history': 'None',
            'expected_risk': 'LOW'
        },

        # MODERATE CONCERN (Should be MEDIUM)
        {
            'name': '4. ACTUAL Fever (Low-Grade)',
            'age': 28, 'sys_bp': 125, 'dia_bp': 82, 'hr': 85, 'temp_f': 100.8,
            'symptoms': 'Fever and body aches', 'history': 'None',
            'expected_risk': 'MEDIUM'
        },
        {
            'name': '5. Elevated Blood Pressure',
            'age': 55, 'sys_bp': 150, 'dia_bp': 92, 'hr': 88, 'temp_f': 98.8,
            'symptoms': 'Dizziness and fatigue', 'history': 'Hypertension',
            'expected_risk': 'MEDIUM'
        },
        {
            'name': '6. ACTUAL High Fever',
            'age': 32, 'sys_bp': 135, 'dia_bp': 88, 'hr': 95, 'temp_f': 102.5,
            'symptoms': 'High fever and chills', 'history': 'None',
            'expected_risk': 'MEDIUM'
        },

        # EMERGENCY (Should be HIGH)
        {
            'name': '7. Chest Pain Emergency',
            'age': 58, 'sys_bp': 180, 'dia_bp': 110, 'hr': 120, 'temp_f': 99.5,
            'symptoms': 'Severe chest pain and shortness of breath', 'history': 'Heart Disease',
            'expected_risk': 'HIGH'
        },
        {
            'name': '8. Hemorrhage',
            'age': 42, 'sys_bp': 85, 'dia_bp': 55, 'hr': 130, 'temp_f': 97.2,
            'symptoms': 'Active hemorrhage from head injury', 'history': 'None',
            'expected_risk': 'HIGH'
        },
        {
            'name': '9. Unconscious Patient',
            'age': 65, 'sys_bp': 90, 'dia_bp': 60, 'hr': 110, 'temp_f': 96.5,
            'symptoms': 'Patient unconscious and unresponsive', 'history': 'Diabetes',
            'expected_risk': 'HIGH'
        },

        # EDGE CASES
        {
            'name': '10. Normal Vitals but Emergency Symptoms',
            'age': 45, 'sys_bp': 125, 'dia_bp': 80, 'hr': 75, 'temp_f': 98.6,
            'symptoms': 'Crushing chest pain radiating to left arm', 'history': 'None',
            'expected_risk': 'HIGH'
        },
    ]

    results = []
    for scenario in scenarios:
        passed = test_scenario(**scenario)
        results.append((scenario['name'], passed))

    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    passed = sum(1 for _, p in results if p)
    total = len(results)

    for name, passed_flag in results:
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"{status} - {name}")

    print("="*70)
    print(f"TOTAL: {passed}/{total} scenarios passed ({passed/total*100:.1f}%)")
    print("="*70 + "\n")

    if passed == total:
        print("🎉 All scenarios validated successfully!")
    else:
        print(f"⚠️  {total - passed} scenario(s) need attention")
