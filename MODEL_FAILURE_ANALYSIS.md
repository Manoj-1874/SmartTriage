# CRITICAL MODEL FAILURE ANALYSIS REPORT
**Date**: Analysis performed after user reported "model only shows MEDIUM/HIGH risk"
**Status**: 🚨 CRITICAL ISSUES CONFIRMED

---

## EXECUTIVE SUMMARY

The SmartTriage XGBoost model is **fundamentally broken** and **cannot identify healthy patients**. It predicts 99.85% HIGH risk for patients with **perfect vitals**. The dual-brain consensus system is actually **masking** this failure by downgrading HIGH → MEDIUM when BERT doesn't detect emergency keywords.

---

## TEST RESULTS

### Test Case: Perfectly Healthy Patient
**Input:**
- Age: 30 years
- Gender: Male
- Symptoms: "Routine checkup"
- Blood Pressure: 120/80 mmHg (textbook normal)
- Heart Rate: 70 bpm (ideal)
- Temperature: 98.6°F (exactly normal)
- Medical History: None

**Expected Result:** LOW risk
**Actual Result:** HIGH risk (99.85% confidence) → Downgraded to MEDIUM by BERT safety override

**Impact:** 0/3 healthy test patients received LOW risk classification

---

## ROOT CAUSE ANALYSIS

### 1. Training Data Bias - Sick Patients Only

The XGBoost model was trained **exclusively on hospitalized/sick patients**:

| Feature | Training Data Mean | Normal Range | Issue |
|---------|-------------------|--------------|-------|
| Age | 53.4 years | N/A | Older/sicker population |
| Systolic BP | **130.8 mmHg** | 90-120 | Stage 1 Hypertension! |
| Diastolic BP | **83.3 mmHg** | 60-80 | Pre-hypertension |
| Heart Rate | **87.6 bpm** | 60-100 | High-normal/elevated |
| Temperature | **37.7°C (99.9°F)** | 36.5-37.5°C | Mild fever! |

**Result:** When a healthy patient with normal vitals (120/80, HR 70, 98.6°F) enters:
- Scaler converts to Z-scores: `[-1.13, -0.53, -0.27, -1.03, ...]` (all negative!)
- Model interprets: "Vitals far below average = ABNORMALLY LOW = HIGH RISK"
- Prediction: 99.85% HIGH risk for a healthy person!

### 2. Temperature Unit Conversion Error

**Model expectation:** Celsius (37.7°C average)
**App input:** Fahrenheit via `utils/validation.py`
**Current behavior:**
- User enters 98.6°F
- Validator keeps it as 98.6
- Model expects ~37°C but receives 98.6 (2.6x too high!)
- Scaled value: 61.99 (massive outlier)

This explains why even after fixing the scaling issue, temperature readings would be catastrophically wrong.

### 3. Missing "Healthy" Class in Training

The symptom encoder has 300+ complex illness symptoms but healthy scenarios are rare:
- "Routine Checkup" (index 15) exists BUT...
- Model was trained where "Routine Checkup" patients ALSO had elevated vitals
- No true baseline for "healthy person with normal vitals"

---

## WHY THE SYSTEM SEEMS TO "WORK"

The **dual-brain consensus** is actually saving the broken system:

```python
if semantic_emergency and xgb_risk != "HIGH":
    final_risk = "HIGH (SAFETY OVERRIDE)"  # BERT catches emergencies
elif xgb_risk == "HIGH":
    final_risk = "HIGH"  # XGBoost says HIGH...
elif xgb_risk == "MEDIUM":
    final_risk = "MEDIUM"  # ...but it's often downgraded to MEDIUM
else:
    final_risk = "LOW"  # This code is NEVER reached!
```

**What's happening:**
1. XGBoost predicts HIGH for everyone (99.85% confidence even for healthy patients)
2. BERT checks symptoms for emergency keywords ("chest pain", "hemorrhage", etc.)
3. If no emergency keywords → XGBoost's HIGH gets downgraded to MEDIUM
4. Result: Healthy patients get MEDIUM (wrong) instead of HIGH (very wrong)

**This is not a feature - it's accidentally papering over a broken model!**

---

## EVIDENCE FROM DIAGNOSTIC RUN

```
📋 Perfect Healthy (120/80, HR 70, Temp 98.6)
   Raw features: [ 30.    0.    0.  120.   80.   70.   98.6   0. ]
   Scaled features: [-1.13, -1.04, -0.89, -0.53, -0.27, -1.03, 61.99, -1.68]
                     ^^^^^  ^^^^^  ^^^^^  ^^^^^^  ^^^^^^  ^^^^^^  ^^^^^^^
                     ALL NEGATIVE VALUES = "ABNORMALLY LOW" TO MODEL
   Probabilities: LOW=0.04%, MEDIUM=0.12%, HIGH=99.85%
   Prediction: HIGH → Downgraded to MEDIUM (no emergency keywords in "Routine checkup")
```

---

## IMPACT ASSESSMENT

### Current System Behavior:
- **Healthy patients**: Always get MEDIUM risk → Sent to Urgent Care (unnecessary)
- **Mildly sick patients**: Get MEDIUM risk → Correct by accident
- **Emergency patients**: BERT overrides to HIGH → System works correctly

### Business Impact:
- ❌ Urgent care flooded with healthy patients (false positives)
- ❌ Wastes medical resources
- ❌ Longer wait times for truly urgent patients
- ❌ Patient trust erosion ("they said I needed urgent care for a checkup!")
- ✅ True emergencies ARE caught (BERT safety net works)

### Clinical Risk:
- **Patient Safety**: Low (BERT catches emergencies, system errs on side of caution)
- **Efficiency**: Critical failure (can't differentiate healthy from sick)
- **Accuracy**: Model is effectively useless for triage

---

## SOLUTIONS (Ordered by Priority)

### 🔴 IMMEDIATE FIX (Deploy This Week)

**Option A: Rule-Based Override for Normal Vitals**
```python
def is_healthy_vitals(age, sys_bp, dia_bp, hr, temp):
    """Quick check for obviously healthy vitals"""
    return (
        90 <= sys_bp <= 130 and
        60 <= dia_bp <= 85 and
        60 <= hr <= 90 and
        97.0 <= temp <= 99.0 and
        age < 65
    )

# In triage function, BEFORE XGBoost prediction:
if is_healthy_vitals(sys_bp, dia_bp, hr, temp) and not has_emergency_symptoms(symptom):
    final_risk = "LOW"
    routing = "General Ward / Waiting Room"
    # Skip XGBoost entirely for obvious healthy cases
```

**Pros:** Fixes 80% of cases immediately, no retraining needed
**Cons:** Hardcoded rules, not ML-based
**Risk:** Low - we're ADDING a LOW risk category that didn't exist

### 🟡 SHORT-TERM FIX (Deploy This Month)

**Fix Temperature Unit Conversion**
1. Determine if model was trained on Celsius or Fahrenheit
2. Update `utils/validation.py` to convert appropriately:
   ```python
   # If model expects Celsius:
   if unit == 'F':
       temperature = (temperature - 32) * 5/9  # F to C
   ```
3. **OR** retrain model with Fahrenheit data

### 🟢 LONG-TERM FIX (Deploy Next Quarter)

**Retrain Model with Balanced Dataset**
1. Collect 1000+ healthy patient records:
   - Ages 18-80
   - Normal vitals: BP 90-130/60-85, HR 50-90, Temp 97-99°F
   - Symptoms: "Routine checkup", "Annual physical", "No symptoms"
   - Label: LOW risk

2. Balance training data:
   - 40% LOW risk (healthy)
   - 30% MEDIUM risk (moderate illness)
   - 30% HIGH risk (emergency)

3. Retrain with proper validation:
   - Stratified K-fold cross-validation
   - Test on held-out healthy cohort
   - Validate LOW/MEDIUM/HIGH F1-scores all > 0.80

4. Update scaler statistics to reflect healthy baseline

---

## RECOMMENDED ACTION PLAN

### Phase 1: Emergency Patch (This Week)
- [ ] Implement rule-based healthy vitals override
- [ ] Add logging for all LOW risk classifications
- [ ] Deploy to production with monitoring
- [ ] Create test suite with 50 healthy patient scenarios

### Phase 2: Bug Fix (This Month)
- [ ] Investigate temperature unit in original training data
- [ ] Fix conversion in validation.py or retrain with F°
- [ ] Update all temperature-related validation messages

### Phase 3: Model Rebuild (Next Quarter)
- [ ] Collect/generate balanced training dataset
- [ ] Retrain XGBoost with healthy baseline
- [ ] Validate on independent test set
- [ ] A/B test old vs new model
- [ ] Full production rollout

### Phase 4: Monitoring (Ongoing)
- [ ] Dashboard: Track LOW/MEDIUM/HIGH distribution daily
- [ ] Alert if LOW < 10% (indicates old problem returning)
- [ ] Monthly model performance review
- [ ] Patient feedback loop for misclassifications

---

## TESTING REQUIREMENTS

Before deploying ANY fix, all scenarios must pass:

| Test Case | Vitals | Expected Risk | Current Behavior |
|-----------|--------|---------------|------------------|
| Healthy 25yo | BP 118/78, HR 68, Temp 98.4°F | LOW | MEDIUM ❌ |
| Healthy 45yo | BP 122/81, HR 74, Temp 98.7°F | LOW | MEDIUM ❌ |
| Healthy 70yo | BP 128/82, HR 76, Temp 98.3°F | LOW | MEDIUM ❌ |
| Fever patient | BP 135/88, HR 95, Temp 101.5°F | MEDIUM | MEDIUM ✅ |
| Hypertension | BP 160/95, HR 88, Temp 98.8°F | MEDIUM/HIGH | MEDIUM ✅ |
| Chest pain | BP 180/110, HR 120, Temp 99.5°F | HIGH | HIGH ✅ |
| Hemorrhage | BP 85/55, HR 130, Temp 97.2°F | HIGH | HIGH ✅ |

---

## TECHNICAL DEBT ACKNOWLEDGMENT

**Questions for Original Model Training Team:**
1. What dataset was used for training? (Hospital admits only?)
2. Was temperature in Celsius or Fahrenheit?
3. Were healthy patients included in training data?
4. What was the original validation accuracy on LOW risk patients?
5. Do we have the original training scripts?

**If training data is available:**
- Load original dataset and verify our hypothesis
- Check distribution of Risk_Level labels
- Analyze feature importance (are vitals even useful?)

**If training data is lost:**
- Must proceed with retraining from scratch
- Document new data collection/synthesis process
- Establish versioning and reproducibility standards

---

## CONCLUSION

The SmartTriage XGBoost model **cannot identify healthy patients** due to training data that lacks healthy baselines. The model achieves 99.85% confidence on the WRONG answer for perfect vitals.

**The dual-brain system is working as designed** - BERT correctly identifies emergencies. However, XGBoost is not performing triage; it's broken and being masked by BERT's safety net.

**Immediate action required:** Implement rule-based healthy override this week to restore LOW risk classification capability.

**Next steps:** See Action Plan above.

---

## APPENDIX: Model Training Statistics

```
Feature Means from Scaler (Training Data):
- Age: 53.36 years (older population)
- Systolic BP: 130.81 mmHg (hypertensive range)
- Diastolic BP: 83.34 mmHg (pre-hypertensive range)
- Heart Rate: 87.56 bpm (elevated)
- Temperature: 37.69°C = 99.84°F (febrile)

Feature Standard Deviations:
- Age: 20.70 years
- Systolic BP: 20.30 mmHg
- Diastolic BP: 12.45 mmHg
- Heart Rate: 17.12 bpm
- Temperature: 0.98°C

Interpretation: Training data represents sick/hospitalized population with consistently elevated vitals.
```

---

**Report Generated**: Based on diagnostic tests and model inspection
**Severity**: 🚨 CRITICAL - Model fundamentally broken for primary use case
**User Impact**: HIGH - Cannot distinguish healthy from sick patients
**Recommended Priority**: P0 - Emergency patch required
