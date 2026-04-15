"""
DISEASE-AWARE RISK ASSESSMENT SYSTEM
Handles disease names, recognizes severity, understands complications
"""

import logging
from typing import Tuple, Dict, List

logger = logging.getLogger(__name__)

# ============================================================================
# COMPREHENSIVE MEDICAL DISEASE DATABASE
# Maps disease names to severity, complications, and risk profiles
# ============================================================================

DISEASE_KNOWLEDGE_BASE = {
    # RARE CONNECTIVE TISSUE DISORDERS
    'ehlers-danlos syndrome': {
        'severity': 'HIGH',
        'category': 'Genetic/Connective Tissue',
        'base_risk': 0.70,
        'symptoms': ['joint hypermobility', 'skin fragility', 'bleeding', 'organ rupture risk'],
        'complications': ['aortic rupture', 'internal hemorrhage', 'structural failure'],
        'specialist': 'Rheumatology/Genetics',
        'acuity': 'Chronic Progressive',
        'requires_specialist': True,
        'dangerous_variants': ['vascular EDS', 'kyphoscoliotic EDS']
    },

    # METABOLIC DISORDERS
    'ribose-5-phosphate isomerase deficiency': {
        'severity': 'MEDIUM-HIGH',
        'category': 'Metabolic/Enzymatic',
        'base_risk': 0.65,
        'symptoms': ['ataxia', 'developmental delay', 'seizures', 'metabolic acidosis'],
        'complications': ['progressive neurological decline', 'organ damage'],
        'specialist': 'Metabolic Disease/Neurology',
        'acuity': 'Chronic Degenerative',
        'requires_specialist': True,
        'rare': True
    },

    # CARDIOVASCULAR EMERGENCIES
    'myocardial infarction': {
        'severity': 'CRITICAL',
        'category': 'Cardiovascular Emergency',
        'base_risk': 0.95,
        'symptoms': ['chest pain', 'shortness of breath', 'diaphoresis'],
        'complications': ['cardiogenic shock', 'arrhythmia', 'cardiac arrest'],
        'specialist': 'Cardiology/ER',
        'acuity': 'EMERGENCY',
        'requires_immediate_er': True
    },

    # AUTOIMMUNE DISORDERS
    'systemic lupus erythematosus': {
        'severity': 'HIGH',
        'category': 'Autoimmune',
        'base_risk': 0.65,
        'symptoms': ['rash', 'joint pain', 'fatigue', 'mouth ulcers'],
        'complications': ['kidney damage', 'CNS involvement', 'thrombosis'],
        'specialist': 'Rheumatology',
        'acuity': 'Chronic Flare-prone',
        'requires_specialist': True
    },

    # RESPIRATORY DISEASES
    'idiopathic pulmonary fibrosis': {
        'severity': 'HIGH',
        'category': 'Respiratory',
        'base_risk': 0.75,
        'symptoms': ['progressive dyspnea', 'persistent cough', 'hypoxia'],
        'complications': ['respiratory failure', 'core pulmonale', 'premature death'],
        'specialist': 'Pulmonology',
        'acuity': 'Progressive',
        'requires_specialist': True
    },

    # NEUROLOGICAL DISORDERS
    'retinitis pigmentosa': {
        'severity': 'MEDIUM',
        'category': 'Genetic/Vision',
        'base_risk': 0.55,
        'symptoms': ['night blindness', 'peripheral vision loss', 'photopsia'],
        'complications': ['complete blindness', 'hearing loss (in some)', 'cardiac complications'],
        'specialist': 'Ophthalmology/Genetics',
        'acuity': 'Chronic Progressive',
        'requires_specialist': True,
        'rare': True
    },

    # ENDOCRINE EMERGENCIES
    'diabetic ketoacidosis': {
        'severity': 'CRITICAL',
        'category': 'Endocrine Emergency',
        'base_risk': 0.90,
        'symptoms': ['rapid breathing', 'fruity breath', 'confusion', 'abdominal pain'],
        'complications': ['cerebral edema', 'cardiac arrhythmia', 'death'],
        'specialist': 'Endocrinology/ER',
        'acuity': 'EMERGENCY',
        'requires_immediate_er': True
    },

    # HEMATOLOGIC DISORDERS
    'hemolytic anemia': {
        'severity': 'MEDIUM-HIGH',
        'category': 'Hematologic',
        'base_risk': 0.65,
        'symptoms': ['dark urine', 'jaundice', 'fatigue', 'abdominal pain'],
        'complications': ['acute kidney injury', 'cardiac complications', 'organ failure'],
        'specialist': 'Hematology',
        'acuity': 'Acute/Chronic',
        'requires_specialist': True
    },

    # GI EMERGENCIES
    'acute appendicitis': {
        'severity': 'HIGH',
        'category': 'Surgical Emergency',
        'base_risk': 0.80,
        'symptoms': ['sudden abdominal pain', 'fever', 'nausea', 'vomiting'],
        'complications': ['perforation', 'sepsis', 'death'],
        'specialist': 'Surgery/ER',
        'acuity': 'EMERGENCY',
        'requires_immediate_er': True
    },

    # INFECTIOUS DISEASES
    'meningitis': {
        'severity': 'CRITICAL',
        'category': 'Infectious Emergency',
        'base_risk': 0.92,
        'symptoms': ['severe headache', 'fever', 'neck stiffness', 'altered mental status'],
        'complications': ['sepsis', 'brain damage', 'death'],
        'specialist': 'ER/Infectious Disease',
        'acuity': 'EMERGENCY',
        'requires_immediate_er': True
    },

    # GENETIC DISORDERS
    'cystic fibrosis': {
        'severity': 'HIGH',
        'category': 'Genetic',
        'base_risk': 0.70,
        'symptoms': ['persistent cough', 'thick secretions', 'failure to thrive'],
        'complications': ['respiratory failure', 'pancreatic insufficiency', 'diabetes'],
        'specialist': 'Pulmonology/Genetics',
        'acuity': 'Chronic Progressive',
        'requires_specialist': True
    },

    # HYPERTENSIVE CRISIS
    'hypertensive emergency': {
        'severity': 'CRITICAL',
        'category': 'Cardiovascular Emergency',
        'base_risk': 0.85,
        'symptoms': ['severely elevated BP', 'severe headache', 'chest pain', 'vision changes'],
        'complications': ['stroke', 'MI', 'organ failure'],
        'specialist': 'Cardiology/ER',
        'acuity': 'EMERGENCY',
        'requires_immediate_er': True
    },
}

# ============================================================================
# FUNCTION: Disease-Aware Risk Assessment
# ============================================================================

def assess_disease_risk(
    disease_name: str = '',
    symptoms: str = '',
    age: int = 30,
    sys_bp: int = 120,
    dia_bp: int = 80,
    hr: int = 80,
    temp_f: float = 98.6
) -> Tuple[str, float, Dict]:
    """
    Assess risk by disease NAME + symptoms + vitals

    Handles:
    1. Known diseases (in knowledge base) → Uses known severity
    2. Unknown diseases → Uses semantic analysis of disease name + symptoms
    3. Pure symptoms (no disease) → Uses symptom semantic analysis

    Args:
        disease_name: Disease name (e.g., "Ehlers-Danlos Syndrome")
        symptoms: Patient symptom description
        age, sys_bp, dia_bp, hr, temp_f: Patient vitals

    Returns:
        (risk_level: str, confidence: float, analysis_details: dict)
    """

    details = {
        'original_disease': disease_name,
        'original_symptoms': symptoms,
        'disease_recognized': False,
        'disease_match_score': 0.0,
        'risk_factors': [],
        'reasoning': [],
        'recommendation': '',
    }

    disease_lower = (disease_name or '').lower().strip()
    symptoms_lower = (symptoms or '').lower().strip()

    # ===== STEP 1: CHECK IF DISEASE IS IN KNOWLEDGE BASE =====
    matched_disease = None
    match_score = 0.0

    for known_disease, disease_info in DISEASE_KNOWLEDGE_BASE.items():
        # Exact match
        if disease_lower == known_disease:
            matched_disease = disease_info
            match_score = 1.0
            details['disease_recognized'] = True
            details['disease_match_score'] = 1.0
            details['reasoning'].append(f"✅ Disease recognized: {disease_name}")
            break

        # Fuzzy match (substring contains)
        elif disease_lower in known_disease or known_disease in disease_lower:
            if match_score < 0.8:
                matched_disease = disease_info
                match_score = 0.8
                details['disease_recognized'] = True
                details['disease_match_score'] = 0.8
                details['reasoning'].append(f"⚠️  Partial match: {known_disease}")

    # ===== STEP 2: RISK CALCULATION =====

    if matched_disease:
        # Known disease - use established risk + vital/symptom modifiers
        base_risk = matched_disease.get('base_risk', 0.50)

        details['reasoning'].append(f"Disease severity: {matched_disease.get('severity', 'UNKNOWN')}")
        details['reasoning'].append(f"Category: {matched_disease.get('category', 'Unknown')}")
        details['disease_info'] = matched_disease

        # Check for emergency indicators
        is_emergency = matched_disease.get('requires_immediate_er', False)
        if is_emergency:
            risk_score = 0.95
            details['reasoning'].append("🚨 EMERGENCY CONDITION - Requires immediate ER")
        else:
            # START WITH BASE RISK (disease severity itself matters)
            risk_score = base_risk

            # Escalation 1: If disease is CRITICAL category
            if 'CRITICAL' in matched_disease.get('severity', ''):
                risk_score = min(1.0, risk_score + 0.15)
                details['reasoning'].append("⚠️  CRITICAL disease category - risk escalated")

            # Escalation 2: If disease is HIGH severity, boost risk minimum
            if matched_disease.get('severity') == 'HIGH':
                risk_score = max(risk_score, 0.65)  # Minimum 65% risk for HIGH diseases
                details['reasoning'].append("⚠️  HIGH SEVERITY disease - minimum risk 65%")

            # Escalation 3: If disease is MEDIUM-HIGH
            if 'MEDIUM-HIGH' in matched_disease.get('severity', ''):
                risk_score = max(risk_score, 0.55)  # Minimum 55% risk
                details['reasoning'].append("⚠️  MEDIUM-HIGH SEVERITY - minimum risk 55%")

            # Escalation 4: If disease is rare
            if matched_disease.get('rare', False):
                risk_score = min(1.0, risk_score + 0.15)
                details['reasoning'].append("⚠️  RARE DISEASE - Requires specialist evaluation (+15% risk)")

            # Escalation 5: Check vitals match disease symptoms (vital risk INCREASES score)
            vital_risk = _calculate_vital_risk_for_disease(
                matched_disease,
                sys_bp, dia_bp, hr, temp_f
            )
            if vital_risk > 0:
                risk_score = min(1.0, risk_score + vital_risk)
                details['reasoning'].append(f"⚠️  Vitals indicate disease complications (+{vital_risk:.0%} risk)")

            # Escalation 6: Age-based risk
            if age < 5 or age > 75:
                risk_score = min(1.0, risk_score + 0.10)
                details['reasoning'].append(f"⚠️  High-risk age group (+10% risk)")

    else:
        # Unknown disease - try semantic analysis of disease name + symptoms
        details['reasoning'].append(f"⚠️  Disease not in knowledge base: {disease_name}")
        details['reasoning'].append("Analyzing disease name and symptoms semantically...")

        combined_text = f"{disease_name} {symptoms}"
        risk_score = _semantic_disease_analysis(combined_text, age, sys_bp, dia_bp, hr, temp_f)

        details['reasoning'].append(f"Semantic analysis risk score: {risk_score:.2f}")
        details['reasoning'].append("❓ Unknown disease - recommend specialist evaluation")

    # ===== STEP 3: CLASSIFY INTO RISK BINS =====
    if risk_score >= 0.80:
        risk_level = 'HIGH'
        recommendation = 'URGENT: Immediate specialist or ER evaluation required'
    elif risk_score >= 0.55:
        risk_level = 'MEDIUM'
        recommendation = 'Priority: Specialist appointment needed within 24-48 hours'
    else:
        risk_level = 'LOW'
        recommendation = 'Monitor: Schedule routine specialist follow-up'

    if matched_disease and matched_disease.get('requires_specialist'):
        specialist = matched_disease.get('specialist', 'Specialist')
        recommendation = f"Refer to: {specialist}"

    details['recommendation'] = recommendation
    details['final_risk_score'] = risk_score

    logger.info(f"[DISEASE ASSESSMENT] {disease_name} → Risk: {risk_level} ({risk_score:.3f})")

    return risk_level, risk_score, details


def _calculate_vital_risk_for_disease(disease_info: dict, sys_bp: int, dia_bp: int,
                                      hr: int, temp_f: float) -> float:
    """Calculate how vitals match the disease's expected patterns"""

    risk = 0.0
    disease_symptoms = disease_info.get('symptoms', [])

    # Check if current vitals match disease symptoms
    if any('breathing' in s or 'dyspnea' in s for s in disease_symptoms):
        if hr > 100 or temp_f > 100:  # Respiratory + fever/tachycardia = worse
            risk += 0.25

    if any('bleeding' in s or 'hemorrhage' in s for s in disease_symptoms):
        if sys_bp < 100 or hr > 120:  # Bleeding + low BP = critical
            risk += 0.35

    if any('fever' in s or 'temperature' in s for s in disease_symptoms):
        if temp_f > 101:  # Very high fever with fever-related disease
            risk += 0.20

    if any('pain' in s for s in disease_symptoms):
        # Pain diseases shouldn't have abnormal vitals
        if sys_bp > 150 or hr > 110:
            risk += 0.15

    return min(1.0, risk)


def _semantic_disease_analysis(text: str, age: int, sys_bp: int, dia_bp: int,
                              hr: int, temp_f: float) -> float:
    """
    Analyze unknown disease by looking at keywords and severity indicators
    """

    risk = 0.3  # Baseline for unknown disease

    # Keywords that suggest serious diseases
    serious_keywords = {
        'syndrome': 0.15,           # Generic syndrome = unknown severity
        'insufficiency': 0.20,      # Organ failure
        'failure': 0.25,            # Complete failure
        'deficiency': 0.15,         # Missing something important
        'atrophy': 0.20,            # Tissue wasting
        'degeneration': 0.25,       # Progressive decline
        'fibrosis': 0.25,           # Scarring/organ damage
        'dystrophy': 0.25,          # Muscle/tissue wasting
        'sclerosis': 0.30,          # Hardening/degeneration
        'necrosis': 0.35,           # Tissue death
        'carcinoma': 0.40,          # Cancer
        'sarcoma': 0.40,            # Cancer
        'lymphoma': 0.40,           # Cancer
        'rupture': 0.30,            # Break/burst of organ
        'hemorrhage': 0.35,         # Internal bleeding
        'embolism': 0.40,           # Blood clot emergency
        'thrombosis': 0.35,         # Blood clot
        'aneurysm': 0.40,           # Vascular rupture risk
    }

    for keyword, weight in serious_keywords.items():
        if keyword in text:
            risk = min(1.0, risk + weight)

    # Keywords that suggest genetic/congenital (needs specialist)
    genetic_keywords = ['hereditary', 'congenital', 'genetic', 'familial']
    if any(kw in text for kw in genetic_keywords):
        risk = min(1.0, risk + 0.20)

    # Keywords that suggest emergency
    emergency_keywords = ['acute', 'emergency', 'critical', 'severe', 'sudden']
    if any(kw in text for kw in emergency_keywords):
        risk = min(1.0, risk + 0.25)

    # Vitals confirmation
    if sys_bp > 180 or sys_bp < 80 or hr > 130 or hr < 40 or temp_f > 104:
        risk = min(1.0, risk + 0.20)

    return min(1.0, risk)


# ============================================================================
# TESTING: What happens with Ehlers-Danlos Syndrome?
# ============================================================================

if __name__ == '__main__':
    print("="*80)
    print("TEST 1: Ehlers-Danlos Syndrome (Known Rare Disease)")
    print("="*80)

    risk_level, confidence, details = assess_disease_risk(
        disease_name='Ehlers-Danlos Syndrome',
        symptoms='Joint hypermobility, skin bruising easily, family history of EDS',
        age=28,
        sys_bp=120,
        dia_bp=80,
        hr=85,
        temp_f=98.6
    )

    print(f"\n✅ Disease Recognized: {details['disease_recognized']}")
    print(f"🎯 Risk Level: {risk_level}")
    print(f"📊 Confidence: {confidence:.2f}")
    print(f"💡 Reasoning: {' → '.join(details['reasoning'])}")
    print(f"📋 Recommendation: {details['recommendation']}")

    print("\n" + "="*80)
    print("TEST 2: Ribose-5-Phosphate Isomerase Deficiency (Rare Metabolic)")
    print("="*80)

    risk_level, confidence, details = assess_disease_risk(
        disease_name='Ribose-5-Phosphate Isomerase Deficiency',
        symptoms='Ataxia, developmental delay, seizures, metabolic acidosis',
        age=5,
        sys_bp=110,
        dia_bp=70,
        hr=95,
        temp_f=98.8
    )

    print(f"\n✅ Disease Recognized: {details['disease_recognized']}")
    print(f"🎯 Risk Level: {risk_level}")
    print(f"📊 Confidence: {confidence:.2f}")
    print(f"💡 Reasoning: {' → '.join(details['reasoning'])}")
    print(f"📋 Recommendation: {details['recommendation']}")

    print("\n" + "="*80)
    print("TEST 3: Unknown Disease (Not in Database)")
    print("="*80)

    risk_level, confidence, details = assess_disease_risk(
        disease_name='Rare Genetic Syndrome XYZ-123',
        symptoms='Progressive weakness, neurological decline, family history',
        age=35,
        sys_bp=130,
        dia_bp=85,
        hr=92,
        temp_f=98.7
    )

    print(f"\n⚠️  Disease Recognized: {details['disease_recognized']}")
    print(f"🎯 Risk Level: {risk_level}")
    print(f"📊 Confidence: {confidence:.2f}")
    print(f"💡 Reasoning: {' → '.join(details['reasoning'])}")
    print(f"📋 Recommendation: {details['recommendation']}")

    print("\n" + "="*80)
    print("TEST 4: Emergency Disease (Myocardial Infarction)")
    print("="*80)

    risk_level, confidence, details = assess_disease_risk(
        disease_name='Myocardial Infarction',
        symptoms='Crushing chest pain, shortness of breath, diaphoresis',
        age=55,
        sys_bp=165,
        dia_bp=95,
        hr=118,
        temp_f=98.9
    )

    print(f"\n✅ Disease Recognized: {details['disease_recognized']}")
    print(f"🎯 Risk Level: {risk_level}")
    print(f"📊 Confidence: {confidence:.2f}")
    print(f"💡 Reasoning: {' → '.join(details['reasoning'])}")
    print(f"📋 Recommendation: {details['recommendation']}")
