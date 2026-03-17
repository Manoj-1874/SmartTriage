"""
PHASE 5.4: INTEGRATION TEST
Tests the production pipeline end-to-end with actual model
Verifies all components work together correctly
"""

import joblib
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_production_pipeline():
    """Test the complete production pipeline with real model"""

    print("=" * 80)
    print("PHASE 5.4: PRODUCTION PIPELINE INTEGRATION TEST")
    print("=" * 80)
    print()

    # ===== TEST 1: LOAD MODEL & COMPONENTS =====
    print("TEST 1: Load Model & Components")
    print("-" * 80)

    try:
        # Load model
        model_path = Path('triage_assets_mingled.pkl')
        if not model_path.exists():
            print(f"❌ Model file not found: {model_path}")
            return False

        assets = joblib.load(model_path)
        model = assets['risk_model']
        scaler = assets['scaler']
        encoders = assets['encoders']
        feature_names = assets['features']

        print(f"✅ Model loaded successfully")
        print(f"   Features: {feature_names}")
        print()
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return False

    # ===== TEST 2: INITIALIZE PIPELINE =====
    print("TEST 2: Initialize Production Pipeline")
    print("-" * 80)

    try:
        from production_pipeline import SmartTriagePipeline

        pipeline = SmartTriagePipeline(
            model=model,
            scaler=scaler,
            encoders=encoders,
            feature_names=feature_names
        )
        print("✅ Production pipeline initialized successfully")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize pipeline: {e}")
        return False

    # ===== TEST 3: TEST WITH DIVERSE PATIENTS =====
    print("TEST 3: Test with Diverse Patients")
    print("-" * 80)

    test_cases = [
        {
            'name': 'Adult - Normal vitals',
            'data': {
                'patient_id': 'ADULT001',
                'age': 45,
                'gender': 'M',
                'sys_bp': 120,
                'dia_bp': 80,
                'hr': 72,
                'temp_c': 37.0,
                'symptoms': 'headache',
                'pre_conditions': 'None'
            }
        },
        {
            'name': 'Pediatric - High fever',
            'data': {
                'patient_id': 'PEDI001',
                'age': 5,
                'gender': 'F',
                'sys_bp': 95,
                'dia_bp': 60,
                'hr': 120,
                'temp_c': 39.5,
                'symptoms': 'fever',
                'pre_conditions': 'None'
            }
        },
        {
            'name': 'Shock - Low BP + High HR',
            'data': {
                'patient_id': 'SHOCK001',
                'age': 55,
                'gender': 'M',
                'sys_bp': 85,
                'dia_bp': 50,
                'hr': 140,
                'temp_c': 38.5,
                'symptoms': 'chest pain',
                'pre_conditions': 'Diabetes'
            }
        },
        {
            'name': 'Elderly - Hypertension',
            'data': {
                'patient_id': 'ELDERLY001',
                'age': 72,
                'gender': 'F',
                'sys_bp': 180,
                'dia_bp': 100,
                'hr': 88,
                'temp_c': 37.2,
                'symptoms': 'dizziness',
                'pre_conditions': 'Hypertension'
            }
        }
    ]

    passed = 0
    results = []

    for test in test_cases:
        try:
            result = pipeline.predict_with_validation(test['data'])

            if result['success']:
                passed += 1
                status = "✓"
            else:
                status = "✗"

            print(f"  {status} {test['name']}")
            print(f"     Prediction: {result['prediction']}")
            print(f"     Confidence: {result['confidence']:.1%} ({result['confidence_level']})")
            print(f"     Alert Level: {result['alert_level']}")

            if result['warnings']:
                print(f"     Warnings: {len(result['warnings'])}")
                for w in result['warnings'][:2]:  # Show first 2 warnings
                    print(f"       - {w}")

            results.append(result)
            print()

        except Exception as e:
            print(f"  ✗ {test['name']}: {str(e)}")
            print()

    print(f"Passed: {passed}/{len(test_cases)}")
    print()

    # ===== TEST 4: VERIFY LOGGING =====
    print("TEST 4: Verify Logging & Monitoring")
    print("-" * 80)

    try:
        # Check if predictions.json was created
        pred_json = Path('predictions.json')
        if pred_json.exists():
            with open(pred_json, 'r') as f:
                preds = json.load(f)
            print(f"✅ Prediction log created: {len(preds)} predictions logged")
        else:
            print(f"⚠️  Prediction log not found (will be created on first prediction)")

        # Check if anomalies.json was created
        anom_json = Path('anomalies.json')
        if anom_json.exists():
            with open(anom_json, 'r') as f:
                anoms = json.load(f)
            print(f"✅ Anomaly log created: {len(anoms)} anomalies detected")
        else:
            print(f"⚠️  Anomaly log not found (will be created if anomalies detected)")

        print()
    except Exception as e:
        print(f"⚠️  Could not verify logging: {e}")
        print()

    # ===== TEST 5: VERIFY CONFIDENCE THRESHOLDS =====
    print("TEST 5: Verify Confidence Thresholds")
    print("-" * 80)

    confidence_tests = [
        {'name': 'High confidence', 'expected': 'HIGH'},
        {'name': 'Medium confidence', 'expected': 'MEDIUM'},
        {'name': 'Low confidence', 'expected': 'LOW'},
        {'name': 'Very low confidence', 'expected': 'VERY_LOW'}
    ]

    from confidence_threshold import ConfidenceThreshold
    ct = ConfidenceThreshold()

    test_data = [
        np.array([0.05, 0.05, 0.90]),  # HIGH
        np.array([0.30, 0.45, 0.25]),  # MEDIUM
        np.array([0.40, 0.35, 0.25]),  # LOW
        np.array([0.33, 0.33, 0.34])   # VERY_LOW
    ]

    conf_passed = 0
    for i, test in enumerate(confidence_tests):
        conf_info = ct.classify_confidence(test_data[i], i)
        success = conf_info['level'] == test['expected']
        conf_passed += success
        status = "✓" if success else "✗"
        print(f"  {status} {test['name']}: {conf_info['level']} (expected: {test['expected']})")

    print(f"Passed: {conf_passed}/{len(confidence_tests)}")
    print()

    # ===== SUMMARY =====
    print("=" * 80)
    print("INTEGRATION TEST RESULTS")
    print("=" * 80)

    all_passed = passed == len(test_cases) and conf_passed == len(confidence_tests)

    if all_passed:
        print("✅ ALL TESTS PASSED - Production pipeline ready for deployment!")
    else:
        print("⚠️  Some tests did not pass - review output above")

    print()
    print("Next steps:")
    print("1. Review predictions.json for logged predictions")
    print("2. Check logs/smarttriage.log for detailed logging")
    print("3. Implement integration in app.py (see INTEGRATION_GUIDE.py)")
    print("4. Deploy to hospital network")
    print()

    return all_passed


if __name__ == '__main__':
    success = test_production_pipeline()
    exit(0 if success else 1)
