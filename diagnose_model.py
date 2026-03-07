"""
Diagnostic script to analyze the XGBoost model and understand why it's failing
"""
import joblib
import numpy as np
import pandas as pd

# Load the model assets
MODEL_PATH = 'models/triage_assets_mingled.pkl'

print("="*70)
print("ANALYZING XGBOOST MODEL")
print("="*70)

assets = joblib.load(MODEL_PATH)
encoders = assets['encoders']
xgb_risk_model = assets['risk_model']
scaler = assets['scaler']
feature_names = assets['features']

print("\n1. FEATURE NAMES:")
print(feature_names)

print("\n2. ENCODER CLASSES:")
for key, encoder in encoders.items():
    print(f"\n{key}:")
    if hasattr(encoder, 'classes_'):
        print(f"  Classes: {list(encoder.classes_)}")
    else:
        print(f"  Type: {type(encoder)}")

print("\n3. SCALER STATISTICS:")
print(f"  Mean: {scaler.mean_}")
print(f"  Scale: {scaler.scale_}")
print(f"  Var: {scaler.var_}")

print("\n4. XGBOOST MODEL INFO:")
print(f"  Model type: {type(xgb_risk_model)}")
print(f"  Number of classes: {xgb_risk_model.n_classes_}")
print(f"  Number of features: {xgb_risk_model.n_features_in_}")

# Test with various vitals to understand the model behavior
print("\n5. TESTING VARIOUS VITAL SIGN COMBINATIONS:")
print("="*70)

test_cases = [
    # Perfect healthy vitals
    {
        'name': 'Perfect Healthy (120/80, HR 70, Temp 98.6)',
        'age': 30,
        'gender_idx': 0,  # Male
        'symptom_idx': 0,  # Will try first symptom in encoder
        'sys_bp': 120,
        'dia_bp': 80,
        'hr': 70,
        'temp': 98.6,
        'history_idx': 0  # Will try first history in encoder
    },
    # Try with different symptom/history indices
    {
        'name': 'Healthy with different encoding',
        'age': 30,
        'gender_idx': 0,
        'symptom_idx': 5,
        'sys_bp': 120,
        'dia_bp': 80,
        'hr': 70,
        'temp': 98.6,
        'history_idx': 5
    },
    # Low BP
    {
        'name': 'Low BP (90/60)',
        'age': 40,
        'gender_idx': 1,  # Female
        'symptom_idx': 0,
        'sys_bp': 90,
        'dia_bp': 60,
        'hr': 75,
        'temp': 98.5,
        'history_idx': 0
    },
    # High BP
    {
        'name': 'High BP (180/110)',
        'age': 55,
        'gender_idx': 0,
        'symptom_idx': 0,
        'sys_bp': 180,
        'dia_bp': 110,
        'hr': 95,
        'temp': 99.0,
        'history_idx': 1
    },
    # High fever
    {
        'name': 'High Fever (103F)',
        'age': 35,
        'gender_idx': 1,
        'symptom_idx': 0,
        'sys_bp': 125,
        'dia_bp': 82,
        'hr': 110,
        'temp': 103.0,
        'history_idx': 0
    }
]

risk_labels = encoders['Risk_Level'].classes_

for case in test_cases:
    patient_df = pd.DataFrame([[
        case['age'],
        case['gender_idx'],
        case['symptom_idx'],
        case['sys_bp'],
        case['dia_bp'],
        case['hr'],
        case['temp'],
        case['history_idx']
    ]], columns=feature_names)

    patient_scaled = scaler.transform(patient_df)
    xgb_probs = xgb_risk_model.predict_proba(patient_scaled)[0]
    xgb_risk = risk_labels[np.argmax(xgb_probs)]

    print(f"\n📋 {case['name']}")
    print(f"   Raw features: {patient_df.values[0]}")
    print(f"   Scaled features: {patient_scaled[0]}")
    print(f"   Probabilities: LOW={xgb_probs[0]:.2%}, MEDIUM={xgb_probs[1]:.2%}, HIGH={xgb_probs[2]:.2%}")
    print(f"   Prediction: {xgb_risk}")

# Check if scaler mean/variance suggests training data issues
print("\n6. SCALER DIAGNOSTICS:")
print("="*70)
print(f"Feature means (what model expects as 'average'):")
for i, (fname, mean_val) in enumerate(zip(feature_names, scaler.mean_)):
    print(f"  {fname}: {mean_val:.2f}")

print(f"\nFeature standard deviations:")
for i, (fname, std_val) in enumerate(zip(feature_names, scaler.scale_)):
    print(f"  {fname}: {std_val:.2f}")

# Reverse engineer what "normal" vitals are in the training data
print("\n7. ESTIMATED TRAINING DATA DISTRIBUTION:")
print("="*70)
print("Based on scaler statistics, the training data had these averages:")
for fname, mean_val in zip(feature_names, scaler.mean_):
    if 'Age' in fname:
        print(f"  Average age: {mean_val:.1f} years")
    elif 'Systolic' in fname:
        print(f"  Average systolic BP: {mean_val:.1f}")
    elif 'Diastolic' in fname:
        print(f"  Average diastolic BP: {mean_val:.1f}")
    elif 'Heart_Rate' in fname or 'HR' in fname or 'Pulse' in fname:
        print(f"  Average heart rate: {mean_val:.1f}")
    elif 'Temp' in fname:
        print(f"  Average temperature: {mean_val:.1f}°F")

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)
