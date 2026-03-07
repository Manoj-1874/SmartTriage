"""
Test with realistic patient data across all risk levels
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import xgb_risk_model, encoders, scaler, feature_names, exp_brain
from utils.triage_override import should_override_to_low_risk
import pandas as pd
import numpy as np


def test_real_patient(name, age, gender, sys_bp, dia_bp, hr, temp_f, symptoms, history, expected_category):
    """Test a realistic patient scenario"""
    print(f"\n{'='*70}")
    print(f"PATIENT: {name}")
    print(f"{'='*70}")
    print(f"Demographics: {age}yo {gender}")
    print(f"Vitals: BP={sys_bp}/{dia_bp} mmHg, HR={hr} bpm, Temp={temp_f}°F")
    print(f"Symptoms: {symptoms}")
    print(f"History: {history}")
    print(f"Expected Category: {expected_category}")
    print("-" * 70)

    # Step 1: Check override
    should_override, override_reason, health_score = should_override_to_low_risk(
        age, sys_bp, dia_bp, hr, temp_f, symptoms, history
    )

    if should_override:
        final_risk = "LOW"
        score = health_score
        print(f"✅ OVERRIDE: {override_reason}")
        print(f"   Health Score: {score}/100")
        print(f"   Risk Level: {final_risk}")
    else:
        # XGBoost prediction
        temp_c = (temp_f - 32) * 5 / 9
        gender_enc = encoders['Gender'].transform([gender])[0] if gender in encoders['Gender'].classes_ else 0
        symptom_enc = encoders['Symptoms'].transform([symptoms])[0] if symptoms in encoders['Symptoms'].classes_ else 0
        history_enc = encoders['Pre_Conditions'].transform([history])[0] if history in encoders['Pre_Conditions'].classes_ else 0

        patient_df = pd.DataFrame([[age, gender_enc, symptom_enc, sys_bp, dia_bp, hr, temp_c, history_enc]],
                                 columns=feature_names)
        patient_scaled = scaler.transform(patient_df)
        xgb_probs = xgb_risk_model.predict_proba(patient_scaled)[0]
        xgb_risk = encoders['Risk_Level'].inverse_transform([np.argmax(xgb_probs)])[0].upper()

        # BERT check
        bert_res = exp_brain(symptoms)[0]
        is_bert_emergency = (bert_res['label'] == 'LABEL_1' and bert_res['score'] > 0.55)
        critical_words = ['distress', 'hemorrhage', 'speech', 'crushing', 'chest pain', 'unconscious', 'confusion', 'bleeding']
        semantic_emergency = any(word in symptoms.lower() for word in critical_words) or is_bert_emergency

        # XGBoost HIGH Downgrade Logic
        if xgb_risk == "HIGH" and not semantic_emergency:
            is_critically_high_bp = sys_bp >= 160 or dia_bp >= 100
            is_critically_high_hr = hr >= 110
            is_critically_high_temp = temp_f >= 103

            if not (is_critically_high_bp or is_critically_high_hr or is_critically_high_temp):
                xgb_risk = "MEDIUM"

        # Consensus
        if semantic_emergency and xgb_risk != "HIGH":
            final_risk = "HIGH (SAFETY OVERRIDE)"
        elif xgb_risk == "HIGH":
            final_risk = "HIGH"
        elif xgb_risk == "MEDIUM":
            final_risk = "MEDIUM"
        else:
            final_risk = "LOW"

        print(f"   XGBoost: {xgb_risk}")
        print(f"   BERT: {'Emergency' if semantic_emergency else 'No Emergency'} (score={bert_res['score']:.1%})")
        print(f"   Risk Level: {final_risk}")

    # Verify
    is_correct = expected_category.upper() in final_risk.upper()
    status = "✅ CORRECT" if is_correct else "❌ INCORRECT"
    print(f"\n{status}")
    return is_correct


if __name__ == '__main__':
    print("\n" + "="*70)
    print("REAL-WORLD PATIENT VALIDATION TEST")
    print("="*70)

    patients = [
        # === LOW RISK PATIENTS ===
        {
            'name': 'Sarah - Annual Physical',
            'age': 32, 'gender': 'Female',
            'sys_bp': 118, 'dia_bp': 76, 'hr': 68, 'temp_f': 98.3,
            'symptoms': 'Annual checkup, no complaints',
            'history': 'None',
            'expected_category': 'LOW'
        },
        {
            'name': 'Mike - Thinks He Has Fever',
            'age': 28, 'gender': 'Male',
            'sys_bp': 122, 'dia_bp': 80, 'hr': 75, 'temp_f': 98.9,
            'symptoms': 'Feeling warm and tired',
            'history': 'None',
            'expected_category': 'LOW'
        },
        {
            'name': 'Emma - Mild Cold',
            'age': 25, 'gender': 'Female',
            'sys_bp': 115, 'dia_bp': 75, 'hr': 70, 'temp_f': 98.6,
            'symptoms': 'Runny nose and mild cough',
            'history': 'None',
            'expected_category': 'LOW'
        },
        {
            'name': 'John - Post-Workout Checkup',
            'age': 35, 'gender': 'Male',
            'sys_bp': 125, 'dia_bp': 82, 'hr': 78, 'temp_f': 98.8,
            'symptoms': 'Just checking vitals after gym',
            'history': 'None',
            'expected_category': 'LOW'
        },

        # === MEDIUM RISK PATIENTS ===
        {
            'name': 'Lisa - Actual Low Fever',
            'age': 29, 'gender': 'Female',
            'sys_bp': 128, 'dia_bp': 84, 'hr': 88, 'temp_f': 100.9,
            'symptoms': 'Fever, body aches, weakness',
            'history': 'None',
            'expected_category': 'MEDIUM'
        },
        {
            'name': 'Robert - Flu Symptoms',
            'age': 45, 'gender': 'Male',
            'sys_bp': 135, 'dia_bp': 88, 'hr': 92, 'temp_f': 101.8,
            'symptoms': 'High fever, chills, severe body aches',
            'history': 'None',
            'expected_category': 'MEDIUM'
        },
        {
            'name': 'Maria - Diabetic with Elevated Sugar',
            'age': 52, 'gender': 'Female',
            'sys_bp': 142, 'dia_bp': 90, 'hr': 85, 'temp_f': 99.2,
            'symptoms': 'Excessive thirst and frequent urination',
            'history': 'Diabetes',
            'expected_category': 'MEDIUM'
        },
        {
            'name': 'David - Persistent Vomiting',
            'age': 38, 'gender': 'Male',
            'sys_bp': 132, 'dia_bp': 86, 'hr': 95, 'temp_f': 99.5,
            'symptoms': 'Vomiting for 24 hours, dehydrated',
            'history': 'None',
            'expected_category': 'MEDIUM'
        },

        # === HIGH RISK PATIENTS ===
        {
            'name': 'James - Severe Chest Pain',
            'age': 62, 'gender': 'Male',
            'sys_bp': 175, 'dia_bp': 105, 'hr': 115, 'temp_f': 98.9,
            'symptoms': 'Crushing chest pain radiating to jaw',
            'history': 'Hypertension',
            'expected_category': 'HIGH'
        },
        {
            'name': 'Patricia - Stroke Symptoms',
            'age': 68, 'gender': 'Female',
            'sys_bp': 165, 'dia_bp': 98, 'hr': 88, 'temp_f': 98.4,
            'symptoms': 'Sudden weakness on left side, slurred speech',
            'history': 'Hypertension',
            'expected_category': 'HIGH'
        },
        {
            'name': 'Carlos - Head Injury Bleeding',
            'age': 41, 'gender': 'Male',
            'sys_bp': 88, 'dia_bp': 58, 'hr': 125, 'temp_f': 97.5,
            'symptoms': 'Head injury with active bleeding, dizzy',
            'history': 'None',
            'expected_category': 'HIGH'
        },
        {
            'name': 'Linda - Severe Allergic Reaction',
            'age': 34, 'gender': 'Female',
            'sys_bp': 95, 'dia_bp': 62, 'hr': 118, 'temp_f': 98.2,
            'symptoms': 'Severe swelling, difficulty breathing, hives',
            'history': 'Allergies',
            'expected_category': 'HIGH'
        },
        {
            'name': 'Thomas - Diabetic Emergency',
            'age': 56, 'gender': 'Male',
            'sys_bp': 92, 'dia_bp': 60, 'hr': 108, 'temp_f': 97.8,
            'symptoms': 'Confusion, sweating, shaking - low blood sugar',
            'history': 'Diabetes',
            'expected_category': 'HIGH'
        },

        # === EDGE CASES ===
        {
            'name': 'Elderly Grace - Normal for Age',
            'age': 78, 'gender': 'Female',
            'sys_bp': 138, 'dia_bp': 88, 'hr': 82, 'temp_f': 98.4,
            'symptoms': 'Routine checkup',
            'history': 'Hypertension (controlled)',
            'expected_category': 'LOW'
        },
        {
            'name': 'Pregnant Anna - Normal Pregnancy',
            'age': 30, 'gender': 'Female',
            'sys_bp': 128, 'dia_bp': 82, 'hr': 88, 'temp_f': 98.9,
            'symptoms': 'Routine prenatal checkup',
            'history': 'None',
            'expected_category': 'LOW'
        },
    ]

    results = []
    for patient in patients:
        correct = test_real_patient(**patient)
        results.append((patient['name'], patient['expected_category'], correct))

    # Summary by category
    print("\n" + "="*70)
    print("SUMMARY BY RISK CATEGORY")
    print("="*70)

    low_correct = sum(1 for name, cat, passed in results if cat == 'LOW' and passed)
    low_total = sum(1 for name, cat, passed in results if cat == 'LOW')

    medium_correct = sum(1 for name, cat, passed in results if cat == 'MEDIUM' and passed)
    medium_total = sum(1 for name, cat, passed in results if cat == 'MEDIUM')

    high_correct = sum(1 for name, cat, passed in results if cat == 'HIGH' and passed)
    high_total = sum(1 for name, cat, passed in results if cat == 'HIGH')

    print(f"LOW RISK:    {low_correct}/{low_total} correct ({low_correct/low_total*100:.1f}%)")
    print(f"MEDIUM RISK: {medium_correct}/{medium_total} correct ({medium_correct/medium_total*100:.1f}%)")
    print(f"HIGH RISK:   {high_correct}/{high_total} correct ({high_correct/high_total*100:.1f}%)")

    print("\n" + "="*70)
    print("OVERALL RESULTS")
    print("="*70)

    total_correct = sum(1 for _, _, passed in results if passed)
    total = len(results)

    for name, category, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name} ({category})")

    print("="*70)
    print(f"TOTAL: {total_correct}/{total} patients correctly triaged ({total_correct/total*100:.1f}%)")
    print("="*70 + "\n")

    if total_correct == total:
        print("🎉 Perfect! All patients correctly triaged!")
    elif total_correct / total >= 0.9:
        print("✅ Excellent performance! System is working well.")
    elif total_correct / total >= 0.8:
        print("⚠️  Good performance, minor adjustments may help.")
    else:
        print("❌ System needs improvement.")
