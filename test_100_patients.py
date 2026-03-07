"""
Comprehensive test with 100 realistic patient scenarios
Testing accuracy across LOW, MEDIUM, and HIGH risk categories
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import xgb_risk_model, encoders, scaler, feature_names, exp_brain
from utils.triage_override import should_override_to_low_risk
import pandas as pd
import numpy as np


def test_patient(name, age, gender, sys_bp, dia_bp, hr, temp_f, symptoms, history, expected_category):
    """Test a patient scenario and return if correct"""

    # Step 1: Check override
    should_override, override_reason, health_score = should_override_to_low_risk(
        age, sys_bp, dia_bp, hr, temp_f, symptoms, history
    )

    if should_override:
        final_risk = "LOW"
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
            final_risk = "HIGH"
        elif xgb_risk == "HIGH":
            final_risk = "HIGH"
        elif xgb_risk == "MEDIUM":
            final_risk = "MEDIUM"
        else:
            final_risk = "LOW"

    # Verify
    is_correct = expected_category.upper() in final_risk.upper()
    return is_correct, final_risk, expected_category


if __name__ == '__main__':
    print("\n" + "="*70)
    print("100 PATIENT COMPREHENSIVE VALIDATION TEST")
    print("="*70)

    patients = [
        # ==================== LOW RISK PATIENTS (40) ====================

        # Routine checkups
        {'name': 'P001', 'age': 28, 'gender': 'Female', 'sys_bp': 118, 'dia_bp': 76, 'hr': 68, 'temp_f': 98.3, 'symptoms': 'Annual checkup, no complaints', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P002', 'age': 35, 'gender': 'Male', 'sys_bp': 122, 'dia_bp': 78, 'hr': 72, 'temp_f': 98.6, 'symptoms': 'Routine physical exam', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P003', 'age': 42, 'gender': 'Female', 'sys_bp': 115, 'dia_bp': 75, 'hr': 70, 'temp_f': 98.4, 'symptoms': 'Wellness visit', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P004', 'age': 31, 'gender': 'Male', 'sys_bp': 120, 'dia_bp': 80, 'hr': 75, 'temp_f': 98.7, 'symptoms': 'Preventive screening', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P005', 'age': 26, 'gender': 'Female', 'sys_bp': 112, 'dia_bp': 72, 'hr': 65, 'temp_f': 98.2, 'symptoms': 'Follow-up checkup', 'history': 'None', 'expected_category': 'LOW'},

        # Post-workout/exercise
        {'name': 'P006', 'age': 29, 'gender': 'Male', 'sys_bp': 125, 'dia_bp': 82, 'hr': 78, 'temp_f': 98.8, 'symptoms': 'Just checking vitals after gym', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P007', 'age': 33, 'gender': 'Male', 'sys_bp': 128, 'dia_bp': 84, 'hr': 80, 'temp_f': 99.0, 'symptoms': 'Post-workout checkup', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P008', 'age': 27, 'gender': 'Female', 'sys_bp': 124, 'dia_bp': 80, 'hr': 85, 'temp_f': 98.9, 'symptoms': 'After exercise vitals check', 'history': 'None', 'expected_category': 'LOW'},

        # Thinks they have fever but don't
        {'name': 'P009', 'age': 24, 'gender': 'Female', 'sys_bp': 120, 'dia_bp': 78, 'hr': 74, 'temp_f': 98.8, 'symptoms': 'Feeling warm and tired', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P010', 'age': 30, 'gender': 'Male', 'sys_bp': 118, 'dia_bp': 76, 'hr': 72, 'temp_f': 98.9, 'symptoms': 'Think I have fever', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P011', 'age': 36, 'gender': 'Female', 'sys_bp': 116, 'dia_bp': 74, 'hr': 70, 'temp_f': 99.0, 'symptoms': 'Feeling feverish but not sure', 'history': 'None', 'expected_category': 'LOW'},

        # Mild cold/cough
        {'name': 'P012', 'age': 25, 'gender': 'Female', 'sys_bp': 115, 'dia_bp': 75, 'hr': 70, 'temp_f': 98.6, 'symptoms': 'Runny nose and mild cough', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P013', 'age': 32, 'gender': 'Male', 'sys_bp': 120, 'dia_bp': 78, 'hr': 73, 'temp_f': 98.5, 'symptoms': 'Minor cold symptoms', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P014', 'age': 28, 'gender': 'Female', 'sys_bp': 118, 'dia_bp': 76, 'hr': 71, 'temp_f': 98.7, 'symptoms': 'Slight sore throat', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P015', 'age': 34, 'gender': 'Male', 'sys_bp': 122, 'dia_bp': 80, 'hr': 75, 'temp_f': 98.6, 'symptoms': 'Mild headache and tired', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P016', 'age': 27, 'gender': 'Female', 'sys_bp': 117, 'dia_bp': 75, 'hr': 69, 'temp_f': 98.4, 'symptoms': 'Sniffles and minor fatigue', 'history': 'None', 'expected_category': 'LOW'},

        # Minor aches/pains
        {'name': 'P017', 'age': 38, 'gender': 'Male', 'sys_bp': 124, 'dia_bp': 82, 'hr': 76, 'temp_f': 98.7, 'symptoms': 'Minor muscle ache', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P018', 'age': 29, 'gender': 'Female', 'sys_bp': 116, 'dia_bp': 74, 'hr': 68, 'temp_f': 98.5, 'symptoms': 'Slight back pain', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P019', 'age': 33, 'gender': 'Male', 'sys_bp': 121, 'dia_bp': 79, 'hr': 74, 'temp_f': 98.6, 'symptoms': 'Minor joint pain', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P020', 'age': 26, 'gender': 'Female', 'sys_bp': 114, 'dia_bp': 72, 'hr': 67, 'temp_f': 98.3, 'symptoms': 'Mild fatigue only', 'history': 'None', 'expected_category': 'LOW'},

        # Pregnant - normal prenatal
        {'name': 'P021', 'age': 30, 'gender': 'Female', 'sys_bp': 128, 'dia_bp': 82, 'hr': 88, 'temp_f': 98.9, 'symptoms': 'Routine prenatal checkup', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P022', 'age': 27, 'gender': 'Female', 'sys_bp': 126, 'dia_bp': 80, 'hr': 86, 'temp_f': 98.8, 'symptoms': 'Prenatal visit, feeling well', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P023', 'age': 32, 'gender': 'Female', 'sys_bp': 124, 'dia_bp': 78, 'hr': 84, 'temp_f': 98.7, 'symptoms': 'Regular pregnancy checkup', 'history': 'None', 'expected_category': 'LOW'},

        # Elderly - normal for age
        {'name': 'P024', 'age': 72, 'gender': 'Female', 'sys_bp': 135, 'dia_bp': 86, 'hr': 80, 'temp_f': 98.5, 'symptoms': 'Routine checkup', 'history': 'Hypertension (controlled)', 'expected_category': 'LOW'},
        {'name': 'P025', 'age': 68, 'gender': 'Male', 'sys_bp': 138, 'dia_bp': 88, 'hr': 78, 'temp_f': 98.4, 'symptoms': 'Annual visit', 'history': 'Hypertension (controlled)', 'expected_category': 'LOW'},
        {'name': 'P026', 'age': 75, 'gender': 'Female', 'sys_bp': 136, 'dia_bp': 84, 'hr': 76, 'temp_f': 98.6, 'symptoms': 'Regular checkup, feeling good', 'history': 'Diabetes (controlled)', 'expected_category': 'LOW'},
        {'name': 'P027', 'age': 70, 'gender': 'Male', 'sys_bp': 134, 'dia_bp': 82, 'hr': 74, 'temp_f': 98.3, 'symptoms': 'Wellness visit', 'history': 'None', 'expected_category': 'LOW'},

        # Young adults - healthy
        {'name': 'P028', 'age': 22, 'gender': 'Male', 'sys_bp': 118, 'dia_bp': 76, 'hr': 66, 'temp_f': 98.5, 'symptoms': 'College health check', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P029', 'age': 21, 'gender': 'Female', 'sys_bp': 112, 'dia_bp': 70, 'hr': 64, 'temp_f': 98.2, 'symptoms': 'School physical', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P030', 'age': 23, 'gender': 'Male', 'sys_bp': 120, 'dia_bp': 78, 'hr': 68, 'temp_f': 98.4, 'symptoms': 'Sports physical exam', 'history': 'None', 'expected_category': 'LOW'},

        # Minor allergies
        {'name': 'P031', 'age': 31, 'gender': 'Female', 'sys_bp': 118, 'dia_bp': 76, 'hr': 72, 'temp_f': 98.5, 'symptoms': 'Mild seasonal allergies', 'history': 'Allergies', 'expected_category': 'LOW'},
        {'name': 'P032', 'age': 28, 'gender': 'Male', 'sys_bp': 122, 'dia_bp': 80, 'hr': 74, 'temp_f': 98.6, 'symptoms': 'Minor allergy symptoms', 'history': 'None', 'expected_category': 'LOW'},

        # Preventive care
        {'name': 'P033', 'age': 40, 'gender': 'Female', 'sys_bp': 120, 'dia_bp': 78, 'hr': 70, 'temp_f': 98.5, 'symptoms': 'Blood pressure check', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P034', 'age': 45, 'gender': 'Male', 'sys_bp': 124, 'dia_bp': 82, 'hr': 75, 'temp_f': 98.7, 'symptoms': 'Cholesterol screening follow-up', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P035', 'age': 38, 'gender': 'Female', 'sys_bp': 116, 'dia_bp': 74, 'hr': 68, 'temp_f': 98.3, 'symptoms': 'Diabetes screening', 'history': 'None', 'expected_category': 'LOW'},

        # Medication refill visits
        {'name': 'P036', 'age': 52, 'gender': 'Male', 'sys_bp': 128, 'dia_bp': 84, 'hr': 76, 'temp_f': 98.6, 'symptoms': 'Medication refill checkup', 'history': 'Hypertension (controlled)', 'expected_category': 'LOW'},
        {'name': 'P037', 'age': 48, 'gender': 'Female', 'sys_bp': 126, 'dia_bp': 82, 'hr': 74, 'temp_f': 98.5, 'symptoms': 'Prescription renewal visit', 'history': 'Asthma (controlled)', 'expected_category': 'LOW'},

        # Very healthy
        {'name': 'P038', 'age': 35, 'gender': 'Male', 'sys_bp': 115, 'dia_bp': 72, 'hr': 60, 'temp_f': 98.4, 'symptoms': 'Feeling great, routine check', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P039', 'age': 29, 'gender': 'Female', 'sys_bp': 110, 'dia_bp': 70, 'hr': 62, 'temp_f': 98.2, 'symptoms': 'No complaints, annual visit', 'history': 'None', 'expected_category': 'LOW'},
        {'name': 'P040', 'age': 32, 'gender': 'Male', 'sys_bp': 118, 'dia_bp': 75, 'hr': 65, 'temp_f': 98.5, 'symptoms': 'Checkup only', 'history': 'None', 'expected_category': 'LOW'},

        # ==================== MEDIUM RISK PATIENTS (30) ====================

        # Actual fevers - low grade
        {'name': 'P041', 'age': 29, 'gender': 'Female', 'sys_bp': 128, 'dia_bp': 84, 'hr': 88, 'temp_f': 100.4, 'symptoms': 'Fever and body aches', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P042', 'age': 34, 'gender': 'Male', 'sys_bp': 130, 'dia_bp': 86, 'hr': 90, 'temp_f': 100.8, 'symptoms': 'Low fever, feeling weak', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P043', 'age': 25, 'gender': 'Female', 'sys_bp': 126, 'dia_bp': 82, 'hr': 86, 'temp_f': 101.2, 'symptoms': 'Fever and chills', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P044', 'age': 38, 'gender': 'Male', 'sys_bp': 132, 'dia_bp': 88, 'hr': 92, 'temp_f': 100.6, 'symptoms': 'Fever with sore throat', 'history': 'None', 'expected_category': 'MEDIUM'},

        # Flu/viral infections
        {'name': 'P045', 'age': 45, 'gender': 'Male', 'sys_bp': 135, 'dia_bp': 88, 'hr': 92, 'temp_f': 101.8, 'symptoms': 'High fever, chills, severe body aches', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P046', 'age': 31, 'gender': 'Female', 'sys_bp': 130, 'dia_bp': 85, 'hr': 90, 'temp_f': 101.5, 'symptoms': 'Flu-like symptoms, fever', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P047', 'age': 28, 'gender': 'Male', 'sys_bp': 128, 'dia_bp': 84, 'hr': 88, 'temp_f': 102.0, 'symptoms': 'High fever, cough, fatigue', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P048', 'age': 36, 'gender': 'Female', 'sys_bp': 133, 'dia_bp': 87, 'hr': 91, 'temp_f': 101.3, 'symptoms': 'Fever, headache, muscle pain', 'history': 'None', 'expected_category': 'MEDIUM'},

        # Respiratory infections (non-emergency)
        {'name': 'P049', 'age': 42, 'gender': 'Male', 'sys_bp': 136, 'dia_bp': 88, 'hr': 88, 'temp_f': 100.2, 'symptoms': 'Productive cough, low fever', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P050', 'age': 29, 'gender': 'Female', 'sys_bp': 130, 'dia_bp': 84, 'hr': 86, 'temp_f': 99.8, 'symptoms': 'Persistent cough for 5 days', 'history': 'Asthma', 'expected_category': 'MEDIUM'},
        {'name': 'P051', 'age': 35, 'gender': 'Male', 'sys_bp': 132, 'dia_bp': 86, 'hr': 90, 'temp_f': 100.5, 'symptoms': 'Chest congestion, cough', 'history': 'None', 'expected_category': 'MEDIUM'},

        # GI issues
        {'name': 'P052', 'age': 38, 'gender': 'Male', 'sys_bp': 132, 'dia_bp': 86, 'hr': 95, 'temp_f': 99.5, 'symptoms': 'Vomiting for 24 hours, dehydrated', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P053', 'age': 27, 'gender': 'Female', 'sys_bp': 128, 'dia_bp': 82, 'hr': 92, 'temp_f': 99.8, 'symptoms': 'Nausea and vomiting', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P054', 'age': 33, 'gender': 'Male', 'sys_bp': 130, 'dia_bp': 84, 'hr': 90, 'temp_f': 100.1, 'symptoms': 'Diarrhea for 2 days', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P055', 'age': 41, 'gender': 'Female', 'sys_bp': 134, 'dia_bp': 88, 'hr': 94, 'temp_f': 99.6, 'symptoms': 'Abdominal pain and nausea', 'history': 'None', 'expected_category': 'MEDIUM'},

        # Diabetic management
        {'name': 'P056', 'age': 52, 'gender': 'Female', 'sys_bp': 142, 'dia_bp': 90, 'hr': 85, 'temp_f': 99.2, 'symptoms': 'Excessive thirst and frequent urination', 'history': 'Diabetes', 'expected_category': 'MEDIUM'},
        {'name': 'P057', 'age': 58, 'gender': 'Male', 'sys_bp': 145, 'dia_bp': 92, 'hr': 88, 'temp_f': 98.8, 'symptoms': 'Blood sugar feels high, thirsty', 'history': 'Diabetes', 'expected_category': 'MEDIUM'},
        {'name': 'P058', 'age': 48, 'gender': 'Female', 'sys_bp': 140, 'dia_bp': 88, 'hr': 82, 'temp_f': 99.1, 'symptoms': 'Diabetic symptoms, tired', 'history': 'Diabetes', 'expected_category': 'MEDIUM'},

        # Hypertension - elevated
        {'name': 'P059', 'age': 55, 'gender': 'Male', 'sys_bp': 148, 'dia_bp': 94, 'hr': 84, 'temp_f': 98.6, 'symptoms': 'Headache, BP feels high', 'history': 'Hypertension', 'expected_category': 'MEDIUM'},
        {'name': 'P060', 'age': 60, 'gender': 'Female', 'sys_bp': 152, 'dia_bp': 96, 'hr': 86, 'temp_f': 98.7, 'symptoms': 'Dizziness, elevated blood pressure', 'history': 'Hypertension', 'expected_category': 'MEDIUM'},
        {'name': 'P061', 'age': 50, 'gender': 'Male', 'sys_bp': 146, 'dia_bp': 92, 'hr': 82, 'temp_f': 98.5, 'symptoms': 'High BP reading at home', 'history': 'Hypertension', 'expected_category': 'MEDIUM'},

        # Moderate pain
        {'name': 'P062', 'age': 44, 'gender': 'Female', 'sys_bp': 135, 'dia_bp': 88, 'hr': 88, 'temp_f': 98.8, 'symptoms': 'Moderate back pain for 3 days', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P063', 'age': 39, 'gender': 'Male', 'sys_bp': 138, 'dia_bp': 90, 'hr': 90, 'temp_f': 98.9, 'symptoms': 'Knee pain and swelling', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P064', 'age': 47, 'gender': 'Female', 'sys_bp': 133, 'dia_bp': 86, 'hr': 84, 'temp_f': 98.7, 'symptoms': 'Persistent shoulder pain', 'history': 'None', 'expected_category': 'MEDIUM'},

        # UTI/Infections
        {'name': 'P065', 'age': 32, 'gender': 'Female', 'sys_bp': 130, 'dia_bp': 84, 'hr': 86, 'temp_f': 100.3, 'symptoms': 'Painful urination, low fever', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P066', 'age': 40, 'gender': 'Female', 'sys_bp': 132, 'dia_bp': 86, 'hr': 88, 'temp_f': 100.7, 'symptoms': 'Urinary tract infection symptoms', 'history': 'None', 'expected_category': 'MEDIUM'},

        # Asthma exacerbation (mild-moderate)
        {'name': 'P067', 'age': 28, 'gender': 'Male', 'sys_bp': 130, 'dia_bp': 84, 'hr': 94, 'temp_f': 98.8, 'symptoms': 'Wheezing, using inhaler more', 'history': 'Asthma', 'expected_category': 'MEDIUM'},
        {'name': 'P068', 'age': 35, 'gender': 'Female', 'sys_bp': 128, 'dia_bp': 82, 'hr': 92, 'temp_f': 98.9, 'symptoms': 'Asthma flare-up, short of breath', 'history': 'Asthma', 'expected_category': 'MEDIUM'},

        # Moderate injuries
        {'name': 'P069', 'age': 26, 'gender': 'Male', 'sys_bp': 134, 'dia_bp': 86, 'hr': 90, 'temp_f': 98.6, 'symptoms': 'Sprained ankle, swollen', 'history': 'None', 'expected_category': 'MEDIUM'},
        {'name': 'P070', 'age': 31, 'gender': 'Female', 'sys_bp': 128, 'dia_bp': 82, 'hr': 86, 'temp_f': 98.7, 'symptoms': 'Wrist injury from fall', 'history': 'None', 'expected_category': 'MEDIUM'},

        # ==================== HIGH RISK PATIENTS (30) ====================

        # Chest pain - cardiac
        {'name': 'P071', 'age': 62, 'gender': 'Male', 'sys_bp': 175, 'dia_bp': 105, 'hr': 115, 'temp_f': 98.9, 'symptoms': 'Crushing chest pain radiating to jaw', 'history': 'Hypertension', 'expected_category': 'HIGH'},
        {'name': 'P072', 'age': 58, 'gender': 'Male', 'sys_bp': 180, 'dia_bp': 110, 'hr': 120, 'temp_f': 99.1, 'symptoms': 'Severe chest pain, shortness of breath', 'history': 'Hypertension', 'expected_category': 'HIGH'},
        {'name': 'P073', 'age': 65, 'gender': 'Female', 'sys_bp': 170, 'dia_bp': 102, 'hr': 112, 'temp_f': 98.7, 'symptoms': 'Chest pain radiating to arm', 'history': 'Diabetes', 'expected_category': 'HIGH'},
        {'name': 'P074', 'age': 55, 'gender': 'Male', 'sys_bp': 168, 'dia_bp': 108, 'hr': 118, 'temp_f': 99.2, 'symptoms': 'Crushing pressure in chest', 'history': 'Heart disease', 'expected_category': 'HIGH'},

        # Stroke symptoms
        {'name': 'P075', 'age': 68, 'gender': 'Female', 'sys_bp': 165, 'dia_bp': 98, 'hr': 88, 'temp_f': 98.4, 'symptoms': 'Sudden weakness on left side, slurred speech', 'history': 'Hypertension', 'expected_category': 'HIGH'},
        {'name': 'P076', 'age': 72, 'gender': 'Male', 'sys_bp': 172, 'dia_bp': 104, 'hr': 92, 'temp_f': 98.6, 'symptoms': 'Facial drooping, cannot speak clearly', 'history': 'Hypertension', 'expected_category': 'HIGH'},
        {'name': 'P077', 'age': 64, 'gender': 'Female', 'sys_bp': 168, 'dia_bp': 100, 'hr': 90, 'temp_f': 98.5, 'symptoms': 'Sudden severe headache, vision problems', 'history': 'None', 'expected_category': 'HIGH'},
        {'name': 'P078', 'age': 70, 'gender': 'Male', 'sys_bp': 178, 'dia_bp': 106, 'hr': 94, 'temp_f': 98.8, 'symptoms': 'Slurred speech, arm weakness', 'history': 'Diabetes', 'expected_category': 'HIGH'},

        # Severe respiratory distress
        {'name': 'P079', 'age': 48, 'gender': 'Male', 'sys_bp': 155, 'dia_bp': 95, 'hr': 125, 'temp_f': 102.5, 'symptoms': 'Severe shortness of breath, cannot complete sentences', 'history': 'Asthma', 'expected_category': 'HIGH'},
        {'name': 'P080', 'age': 56, 'gender': 'Female', 'sys_bp': 162, 'dia_bp': 98, 'hr': 118, 'temp_f': 101.8, 'symptoms': 'Respiratory distress, gasping for air', 'history': 'None', 'expected_category': 'HIGH'},
        {'name': 'P081', 'age': 42, 'gender': 'Male', 'sys_bp': 148, 'dia_bp': 92, 'hr': 122, 'temp_f': 102.2, 'symptoms': 'Cannot breathe properly, wheezing badly', 'history': 'Asthma', 'expected_category': 'HIGH'},

        # Trauma/Bleeding
        {'name': 'P082', 'age': 41, 'gender': 'Male', 'sys_bp': 88, 'dia_bp': 58, 'hr': 125, 'temp_f': 97.5, 'symptoms': 'Head injury with active bleeding, dizzy', 'history': 'None', 'expected_category': 'HIGH'},
        {'name': 'P083', 'age': 35, 'gender': 'Female', 'sys_bp': 92, 'dia_bp': 60, 'hr': 120, 'temp_f': 97.8, 'symptoms': 'Severe hemorrhage from leg wound', 'history': 'None', 'expected_category': 'HIGH'},
        {'name': 'P084', 'age': 28, 'gender': 'Male', 'sys_bp': 85, 'dia_bp': 55, 'hr': 130, 'temp_f': 97.2, 'symptoms': 'Uncontrolled bleeding, accident', 'history': 'None', 'expected_category': 'HIGH'},
        {'name': 'P085', 'age': 38, 'gender': 'Female', 'sys_bp': 90, 'dia_bp': 58, 'hr': 128, 'temp_f': 97.6, 'symptoms': 'Head trauma, severe bleeding', 'history': 'None', 'expected_category': 'HIGH'},

        # Severe allergic reactions
        {'name': 'P086', 'age': 34, 'gender': 'Female', 'sys_bp': 95, 'dia_bp': 62, 'hr': 118, 'temp_f': 98.2, 'symptoms': 'Severe swelling, difficulty breathing, hives', 'history': 'Allergies', 'expected_category': 'HIGH'},
        {'name': 'P087', 'age': 29, 'gender': 'Male', 'sys_bp': 88, 'dia_bp': 56, 'hr': 122, 'temp_f': 98.1, 'symptoms': 'Anaphylaxis, throat swelling', 'history': 'Allergies', 'expected_category': 'HIGH'},
        {'name': 'P088', 'age': 42, 'gender': 'Female', 'sys_bp': 92, 'dia_bp': 60, 'hr': 115, 'temp_f': 98.3, 'symptoms': 'Allergic reaction, cannot breathe well', 'history': 'Allergies', 'expected_category': 'HIGH'},

        # Diabetic emergencies
        {'name': 'P089', 'age': 56, 'gender': 'Male', 'sys_bp': 92, 'dia_bp': 60, 'hr': 108, 'temp_f': 97.8, 'symptoms': 'Confusion, sweating, shaking - low blood sugar', 'history': 'Diabetes', 'expected_category': 'HIGH'},
        {'name': 'P090', 'age': 62, 'gender': 'Female', 'sys_bp': 95, 'dia_bp': 62, 'hr': 112, 'temp_f': 98.0, 'symptoms': 'Disoriented, diabetic emergency', 'history': 'Diabetes', 'expected_category': 'HIGH'},
        {'name': 'P091', 'age': 54, 'gender': 'Male', 'sys_bp': 88, 'dia_bp': 58, 'hr': 118, 'temp_f': 97.5, 'symptoms': 'Altered mental status, diabetes issue', 'history': 'Diabetes', 'expected_category': 'HIGH'},

        # Severe infections
        {'name': 'P092', 'age': 45, 'gender': 'Female', 'sys_bp': 165, 'dia_bp': 100, 'hr': 115, 'temp_f': 103.5, 'symptoms': 'High fever, severe infection signs', 'history': 'None', 'expected_category': 'HIGH'},
        {'name': 'P093', 'age': 52, 'gender': 'Male', 'sys_bp': 170, 'dia_bp': 105, 'hr': 120, 'temp_f': 104.2, 'symptoms': 'Fever above 104, sepsis concern', 'history': 'None', 'expected_category': 'HIGH'},
        {'name': 'P094', 'age': 38, 'gender': 'Female', 'sys_bp': 172, 'dia_bp': 102, 'hr': 118, 'temp_f': 103.8, 'symptoms': 'Very high fever, chills, severe pain', 'history': 'None', 'expected_category': 'HIGH'},

        # Unconscious/Unresponsive
        {'name': 'P095', 'age': 47, 'gender': 'Male', 'sys_bp': 180, 'dia_bp': 110, 'hr': 125, 'temp_f': 99.5, 'symptoms': 'Found unconscious, not responding', 'history': 'None', 'expected_category': 'HIGH'},
        {'name': 'P096', 'age': 55, 'gender': 'Female', 'sys_bp': 175, 'dia_bp': 108, 'hr': 130, 'temp_f': 99.8, 'symptoms': 'Unresponsive, possible overdose', 'history': 'None', 'expected_category': 'HIGH'},

        # Severe abdominal emergency
        {'name': 'P097', 'age': 51, 'gender': 'Male', 'sys_bp': 168, 'dia_bp': 102, 'hr': 115, 'temp_f': 102.8, 'symptoms': 'Severe abdominal pain, distress', 'history': 'None', 'expected_category': 'HIGH'},
        {'name': 'P098', 'age': 44, 'gender': 'Female', 'sys_bp': 172, 'dia_bp': 105, 'hr': 120, 'temp_f': 103.2, 'symptoms': 'Excruciating abdominal pain, vomiting blood', 'history': 'None', 'expected_category': 'HIGH'},

        # Hypertensive crisis
        {'name': 'P099', 'age': 60, 'gender': 'Male', 'sys_bp': 195, 'dia_bp': 115, 'hr': 110, 'temp_f': 99.0, 'symptoms': 'Severe headache, vision problems', 'history': 'Hypertension', 'expected_category': 'HIGH'},
        {'name': 'P100', 'age': 58, 'gender': 'Female', 'sys_bp': 188, 'dia_bp': 112, 'hr': 115, 'temp_f': 99.2, 'symptoms': 'Hypertensive emergency, chest pressure', 'history': 'Hypertension', 'expected_category': 'HIGH'},
    ]

    print("\n🏥 Loading SmartTriage Dual-Brain Engine...")

    # Test all patients
    results = []
    for p in patients:
        is_correct, actual, expected = test_patient(
            p['name'], p['age'], p['gender'], p['sys_bp'], p['dia_bp'],
            p['hr'], p['temp_f'], p['symptoms'], p['history'], p['expected_category']
        )
        results.append({
            'name': p['name'],
            'expected': expected,
            'actual': actual,
            'correct': is_correct
        })

    # Calculate statistics
    print("\n" + "="*70)
    print("RESULTS BY RISK CATEGORY")
    print("="*70)

    low_results = [r for r in results if r['expected'] == 'LOW']
    medium_results = [r for r in results if r['expected'] == 'MEDIUM']
    high_results = [r for r in results if r['expected'] == 'HIGH']

    low_correct = sum(1 for r in low_results if r['correct'])
    medium_correct = sum(1 for r in medium_results if r['correct'])
    high_correct = sum(1 for r in high_results if r['correct'])

    print(f"\nLOW RISK:")
    print(f"  Total: {len(low_results)} patients")
    print(f"  Correct: {low_correct}")
    print(f"  Accuracy: {(low_correct/len(low_results)*100):.1f}%")

    print(f"\nMEDIUM RISK:")
    print(f"  Total: {len(medium_results)} patients")
    print(f"  Correct: {medium_correct}")
    print(f"  Accuracy: {(medium_correct/len(medium_results)*100):.1f}%")

    print(f"\nHIGH RISK:")
    print(f"  Total: {len(high_results)} patients")
    print(f"  Correct: {high_correct}")
    print(f"  Accuracy: {(high_correct/len(high_results)*100):.1f}%")

    total_correct = low_correct + medium_correct + high_correct
    total_patients = len(results)
    overall_accuracy = (total_correct / total_patients * 100)

    print("\n" + "="*70)
    print("OVERALL ACCURACY")
    print("="*70)
    print(f"Total Patients: {total_patients}")
    print(f"Correct Predictions: {total_correct}")
    print(f"Overall Accuracy: {overall_accuracy:.2f}%")
    print("="*70)

    # Show failed cases
    failed = [r for r in results if not r['correct']]
    if failed:
        print(f"\n❌ FAILED CASES ({len(failed)}):")
        for f in failed:
            print(f"  {f['name']}: Expected {f['expected']}, Got {f['actual']}")
    else:
        print("\n🎉 Perfect score! All patients correctly triaged!")

    print()
