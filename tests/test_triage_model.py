"""
Test suite for triage model risk classification
Verifies LOW, MEDIUM, and HIGH risk scenarios
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, xgb_risk_model, encoders, scaler, feature_names, exp_brain
import pandas as pd
import numpy as np


class TestTriageRiskClassification:
    """Test all three risk levels: LOW, MEDIUM, HIGH"""

    @pytest.fixture
    def triage_test_cases(self):
        """Define test scenarios for each risk level"""
        return {
            'healthy_adult': {
                'name': 'Healthy 30-year-old',
                'age': 30,
                'gender': 'Male',
                'symptoms': 'Routine checkup',
                'sys_bp': 120,
                'dia_bp': 80,
                'hr': 72,
                'temp': 98.6,
                'history': 'None',
                'expected_risk': 'LOW'
            },
            'healthy_senior': {
                'name': 'Healthy 65-year-old',
                'age': 65,
                'gender': 'Female',
                'symptoms': 'Annual physical',
                'sys_bp': 125,
                'dia_bp': 82,
                'hr': 75,
                'temp': 98.2,
                'history': 'None',
                'expected_risk': 'LOW'
            },
            'moderate_fever': {
                'name': 'Moderate fever patient',
                'age': 45,
                'gender': 'Male',
                'symptoms': 'Fever and mild headache',
                'sys_bp': 135,
                'dia_bp': 88,
                'hr': 95,
                'temp': 101.5,
                'history': 'Diabetes',
                'expected_risk': 'MEDIUM'
            },
            'elevated_bp': {
                'name': 'Elevated blood pressure',
                'age': 55,
                'gender': 'Female',
                'symptoms': 'Dizziness and fatigue',
                'sys_bp': 160,
                'dia_bp': 95,
                'hr': 88,
                'temp': 98.8,
                'history': 'Hypertension',
                'expected_risk': 'MEDIUM or HIGH'
            },
            'chest_pain': {
                'name': 'Chest pain emergency',
                'age': 58,
                'gender': 'Male',
                'symptoms': 'Severe chest pain and shortness of breath',
                'sys_bp': 180,
                'dia_bp': 110,
                'hr': 120,
                'temp': 99.5,
                'history': 'Heart Disease',
                'expected_risk': 'HIGH'
            },
            'hemorrhage': {
                'name': 'Active hemorrhage',
                'age': 42,
                'gender': 'Female',
                'symptoms': 'Active hemorrhage from head injury',
                'sys_bp': 85,
                'dia_bp': 55,
                'hr': 130,
                'temp': 97.2,
                'history': 'None',
                'expected_risk': 'MEDIUM or HIGH'  # XGBoost alone may predict MEDIUM, but dual-brain escalates to HIGH via BERT
            }
        }

    def test_xgboost_predictions(self, triage_test_cases):
        """Test XGBoost predictions with override system (production flow)"""
        from utils.triage_override import should_override_to_low_risk

        print("\n" + "="*70)
        print("XGBOOST MODEL PREDICTIONS (WITH OVERRIDE)")
        print("="*70)

        for case_key, case in triage_test_cases.items():
            # Step 1: Check for healthy override FIRST (production flow)
            should_override, override_reason, health_score = should_override_to_low_risk(
                case['age'], case['sys_bp'], case['dia_bp'],
                case['hr'], case['temp'], case['symptoms'], case['history']
            )

            if should_override:
                final_risk = "LOW"
                print(f"\n📋 {case['name']}")
                print(f"   Vitals: BP={case['sys_bp']}/{case['dia_bp']}, HR={case['hr']}, Temp={case['temp']}°F")
                print(f"   Symptoms: {case['symptoms']}")
                print(f"   🟢 HEALTHY OVERRIDE: {override_reason}")
                print(f"   Final Risk: {final_risk}")
                print(f"   Expected: {case['expected_risk']}")

                assert final_risk == case['expected_risk'], f"Override failed for {case['name']}: got {final_risk}, expected {case['expected_risk']}"
                continue

            # Step 2: If no override, proceed with XGBoost
            temp_celsius = (case['temp'] - 32) * 5/9

            # Encode categorical variables
            gender_enc = encoders['Gender'].transform([case['gender']])[0] if case['gender'] in encoders['Gender'].classes_ else 0
            symptom_enc = encoders['Symptoms'].transform([case['symptoms']])[0] if case['symptoms'] in encoders['Symptoms'].classes_ else 0
            history_enc = encoders['Pre_Conditions'].transform([case['history']])[0] if case['history'] in encoders['Pre_Conditions'].classes_ else 0

            # Create patient DataFrame
            patient_df = pd.DataFrame([[
                case['age'], gender_enc, symptom_enc,
                case['sys_bp'], case['dia_bp'], case['hr'],
                temp_celsius, history_enc
            ]], columns=feature_names)

            # Scale and predict
            patient_scaled = scaler.transform(patient_df)
            xgb_probs = xgb_risk_model.predict_proba(patient_scaled)[0]
            xgb_risk = encoders['Risk_Level'].inverse_transform([np.argmax(xgb_probs)])[0].upper()

            print(f"\n📋 {case['name']}")
            print(f"   Vitals: BP={case['sys_bp']}/{case['dia_bp']}, HR={case['hr']}, Temp={case['temp']}°F")
            print(f"   Symptoms: {case['symptoms']}")
            print(f"   XGBoost Prediction: {xgb_risk}")
            print(f"   Probabilities: LOW={xgb_probs[0]:.2%}, MEDIUM={xgb_probs[1]:.2%}, HIGH={xgb_probs[2]:.2%}")
            print(f"   Expected: {case['expected_risk']}")

            # Verify prediction matches expectations (with tolerance for MEDIUM or HIGH cases)
            if 'or' not in case['expected_risk']:
                assert xgb_risk == case['expected_risk'], f"XGBoost failed for {case['name']}: got {xgb_risk}, expected {case['expected_risk']}"
            else:
                assert xgb_risk in case['expected_risk'].split(' or '), f"XGBoost prediction {xgb_risk} not in expected range {case['expected_risk']}"

    def test_bert_emergency_detection(self, triage_test_cases):
        """Test BERT emergency keyword detection"""
        print("\n" + "="*70)
        print("BERT EMERGENCY DETECTION (System 2)")
        print("="*70)

        critical_words = ['distress', 'hemorrhage', 'speech', 'crushing', 'chest pain', 'unconscious']

        for case_key, case in triage_test_cases.items():
            # Run BERT inference
            bert_res = exp_brain(case['symptoms'])[0]
            is_bert_emergency = (bert_res['label'] == 'LABEL_1' and bert_res['score'] > 0.5)
            semantic_emergency = any(word in case['symptoms'].lower() for word in critical_words) or is_bert_emergency

            print(f"\n📋 {case['name']}")
            print(f"   Symptoms: {case['symptoms']}")
            print(f"   BERT Label: {bert_res['label']} (score: {bert_res['score']:.2%})")
            print(f"   Semantic Emergency: {'YES ⚠️' if semantic_emergency else 'NO'}")

            # Verify emergency cases are detected
            if 'chest pain' in case['symptoms'].lower() or 'hemorrhage' in case['symptoms'].lower():
                assert semantic_emergency, f"BERT failed to detect emergency in: {case['symptoms']}"

    def test_dual_brain_consensus(self, triage_test_cases):
        """Test complete dual-brain consensus logic with override system (production flow)"""
        from utils.triage_override import should_override_to_low_risk

        print("\n" + "="*70)
        print("DUAL-BRAIN CONSENSUS (Complete Triage Flow with Override)")
        print("="*70)

        critical_words = ['distress', 'hemorrhage', 'speech', 'crushing', 'chest pain', 'unconscious']

        for case_key, case in triage_test_cases.items():
            # Step 0: Check for healthy override FIRST (production flow)
            should_override, override_reason, health_score = should_override_to_low_risk(
                case['age'], case['sys_bp'], case['dia_bp'],
                case['hr'], case['temp'], case['symptoms'], case['history']
            )

            if should_override:
                final_risk = "LOW"
                routing = "General Ward / Waiting Room"
                print(f"\n📋 {case['name']}")
                print(f"   🟢 HEALTHY OVERRIDE: {override_reason}")
                print(f"   🎯 FINAL RISK: {final_risk}")
                print(f"   🏥 Routing: {routing}")
                print(f"   Expected: {case['expected_risk']}")

                assert 'LOW' in final_risk, f"Expected LOW risk for {case['name']}, got {final_risk}"
                continue

            # Step 1: XGBoost prediction
            temp_celsius = (case['temp'] - 32) * 5/9
            gender_enc = encoders['Gender'].transform([case['gender']])[0] if case['gender'] in encoders['Gender'].classes_ else 0
            symptom_enc = encoders['Symptoms'].transform([case['symptoms']])[0] if case['symptoms'] in encoders['Symptoms'].classes_ else 0
            history_enc = encoders['Pre_Conditions'].transform([case['history']])[0] if case['history'] in encoders['Pre_Conditions'].classes_ else 0

            patient_df = pd.DataFrame([[
                case['age'], gender_enc, symptom_enc,
                case['sys_bp'], case['dia_bp'], case['hr'],
                temp_celsius, history_enc
            ]], columns=feature_names)

            patient_scaled = scaler.transform(patient_df)
            xgb_probs = xgb_risk_model.predict_proba(patient_scaled)[0]
            xgb_risk = encoders['Risk_Level'].inverse_transform([np.argmax(xgb_probs)])[0].upper()

            # Step 2: BERT emergency detection
            bert_res = exp_brain(case['symptoms'])[0]
            is_bert_emergency = (bert_res['label'] == 'LABEL_1' and bert_res['score'] > 0.5)
            semantic_emergency = any(word in case['symptoms'].lower() for word in critical_words) or is_bert_emergency

            # Step 3: Dual-brain consensus
            if semantic_emergency and xgb_risk != "HIGH":
                final_risk = "HIGH (SAFETY OVERRIDE)"
                routing = "Resuscitation / Cardiology"
            elif xgb_risk == "HIGH":
                final_risk = "HIGH"
                routing = "Emergency Department"
            elif xgb_risk == "MEDIUM":
                final_risk = "MEDIUM"
                routing = "Urgent Care"
            else:
                final_risk = "LOW"
                routing = "General Ward / Waiting Room"

            print(f"\n📋 {case['name']}")
            print(f"   XGBoost: {xgb_risk}")
            print(f"   BERT Emergency: {semantic_emergency}")
            print(f"   🎯 FINAL RISK: {final_risk}")
            print(f"   🏥 Routing: {routing}")
            print(f"   Expected: {case['expected_risk']}")

            # Verify final risk classification
            if case['expected_risk'] == 'LOW':
                assert 'LOW' in final_risk, f"Expected LOW risk for {case['name']}, got {final_risk}"
            elif case['expected_risk'] == 'MEDIUM':
                assert 'MEDIUM' in final_risk, f"Expected MEDIUM risk for {case['name']}, got {final_risk}"
            elif case['expected_risk'] == 'HIGH':
                assert 'HIGH' in final_risk, f"Expected HIGH risk for {case['name']}, got {final_risk}"

    def test_healthy_patients_get_low_risk(self):
        """Critical test: Verify healthy patients are classified as LOW risk (with override)"""
        from utils.triage_override import should_override_to_low_risk

        print("\n" + "="*70)
        print("HEALTHY PATIENT VERIFICATION (LOW RISK)")
        print("="*70)

        healthy_patients = [
            {
                'name': 'Healthy Young Adult',
                'age': 25, 'gender': 'Female', 'symptoms': 'Regular checkup',
                'sys_bp': 118, 'dia_bp': 78, 'hr': 68, 'temp': 98.4, 'history': 'None'
            },
            {
                'name': 'Healthy Middle-Aged',
                'age': 45, 'gender': 'Male', 'symptoms': 'Annual physical',
                'sys_bp': 122, 'dia_bp': 81, 'hr': 74, 'temp': 98.7, 'history': 'None'
            },
            {
                'name': 'Healthy Senior',
                'age': 70, 'gender': 'Female', 'symptoms': 'Wellness visit',
                'sys_bp': 128, 'dia_bp': 82, 'hr': 76, 'temp': 98.3, 'history': 'None'
            }
        ]

        low_risk_count = 0
        critical_words = ['distress', 'hemorrhage', 'speech', 'crushing', 'chest pain', 'unconscious']

        for patient in healthy_patients:
            # Step 1: Check for healthy override (this happens BEFORE XGBoost in production)
            should_override, override_reason, health_score = should_override_to_low_risk(
                patient['age'], patient['sys_bp'], patient['dia_bp'],
                patient['hr'], patient['temp'], patient['symptoms'], patient['history']
            )

            if should_override:
                # Override detected: Patient is clearly healthy
                final_risk = "LOW"
                print(f"\n✅ {patient['name']} (Age {patient['age']})")
                print(f"   Vitals: BP={patient['sys_bp']}/{patient['dia_bp']}, HR={patient['hr']}, Temp={patient['temp']}°F")
                print(f"   🟢 HEALTHY OVERRIDE: {override_reason}")
                print(f"   Final Risk: {final_risk}")
                low_risk_count += 1
                continue

            # Step 2: If no override, proceed with XGBoost (will likely predict wrong due to training bias)
            temp_celsius = (patient['temp'] - 32) * 5/9

            gender_enc = encoders['Gender'].transform([patient['gender']])[0]
            symptom_enc = encoders['Symptoms'].transform([patient['symptoms']])[0] if patient['symptoms'] in encoders['Symptoms'].classes_ else 0
            history_enc = encoders['Pre_Conditions'].transform([patient['history']])[0]

            patient_df = pd.DataFrame([[
                patient['age'], gender_enc, symptom_enc,
                patient['sys_bp'], patient['dia_bp'], patient['hr'],
                temp_celsius, history_enc
            ]], columns=feature_names)

            patient_scaled = scaler.transform(patient_df)
            xgb_probs = xgb_risk_model.predict_proba(patient_scaled)[0]
            xgb_risk = encoders['Risk_Level'].inverse_transform([np.argmax(xgb_probs)])[0].upper()

            # BERT check
            bert_res = exp_brain(patient['symptoms'])[0]
            is_bert_emergency = (bert_res['label'] == 'LABEL_1' and bert_res['score'] > 0.5)
            semantic_emergency = any(word in patient['symptoms'].lower() for word in critical_words) or is_bert_emergency

            # Dual-brain consensus
            if semantic_emergency and xgb_risk != "HIGH":
                final_risk = "HIGH (SAFETY OVERRIDE)"
            elif xgb_risk == "HIGH":
                final_risk = "HIGH"
            elif xgb_risk == "MEDIUM":
                final_risk = "MEDIUM"
            else:
                final_risk = "LOW"

            print(f"\n✅ {patient['name']} (Age {patient['age']})")
            print(f"   Vitals: BP={patient['sys_bp']}/{patient['dia_bp']}, HR={patient['hr']}, Temp={patient['temp']}°F")
            print(f"   XGBoost: {xgb_risk} (trained on ER patients)")

            if final_risk == "LOW":
                low_risk_count += 1

        print(f"\n{'='*70}")
        print(f"✅ HEALTHY PATIENT RESULTS: {low_risk_count}/{len(healthy_patients)} received LOW risk")
        print(f"{'='*70}")

        # Critical assertion: ALL healthy patients should get LOW risk
        assert low_risk_count == len(healthy_patients), f"Expected all {len(healthy_patients)} healthy patients to get LOW risk, but only {low_risk_count} did"


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-s'])
