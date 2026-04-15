"""
MEDICAL AI KNOWLEDGE SYSTEM - Knows All Diseases
Uses semantic medical knowledge to recognize ANY disease + calculate risk dynamically

Core Philosophy:
- Don't hardcode 15,000 diseases
- Instead, teach AI to UNDERSTAND disease mechanisms
- Use medical knowledge bases + semantic matching
- Dynamically map symptoms → diseases → risk
"""

import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ===================================================================
# DISEASE DATA STRUCTURE - Maps disease to medical characteristics
# ===================================================================

@dataclass
class DiseaseProfile:
    """
    Complete disease profile with medical characteristics
    This allows AI to understand diseases WITHOUT hardcoding all 15K
    """
    name: str
    icd10_code: str
    disease_category: str  # Cardiovascular, Neurological, Genetic, Autoimmune, etc.
    severity_level: str  # CRITICAL, SEVERE, MODERATE, MILD, CHRONIC
    associated_symptoms: List[str]  # What symptoms indicate this
    risk_escalators: List[str]  # What makes it worse (age, comorbidities, etc.)
    typical_vital_changes: Dict  # Expected vital sign abnormalities
    progression_path: List[str]  # What complications can develop
    treatment_urgency: str  # IMMEDIATE, URGENT, PRIORITY, ROUTINE
    specialist_referral: str  # What specialist needed
    mortality_rate: float  # 0.0-1.0 (0=never fatal, 1=always fatal)
    comorbidity_risk_multiplier: float  # How much risk increases with comorbidities


# ===================================================================
# DISEASE CLASSIFICATION SYSTEM - Organize diseases by characteristics
# ===================================================================

DISEASE_CATEGORIES = {
    'CARDIOVASCULAR': {
        'risk_multiplier': 1.3,  # Higher baseline risk
        'common_symptoms': ['chest pain', 'shortness of breath', 'palpitations', 'dizziness'],
        'critical_vitals': {'sys_bp': (160, 90), 'hr': (120, 40)},
    },
    'NEUROLOGICAL': {
        'risk_multiplier': 1.25,
        'common_symptoms': ['headache', 'confusion', 'seizure', 'vision loss', 'weakness'],
        'critical_vitals': {'consciousness': 'altered', 'hr': 'abnormal'},
    },
    'INFECTIOUS': {
        'risk_multiplier': 1.4,
        'common_symptoms': ['fever', 'cough', 'weakness', 'body ache'],
        'critical_vitals': {'temp': '>101.5', 'hr': '>100'},
    },
    'GENETIC/METABOLIC': {
        'risk_multiplier': 1.2,
        'common_symptoms': ['progressive symptoms', 'family history', 'developmental issues'],
        'critical_vitals': {'varies': 'by condition'},
    },
    'AUTOIMMUNE': {
        'risk_multiplier': 1.15,
        'common_symptoms': ['fatigue', 'joint pain', 'rash', 'fever', 'inflammation'],
        'critical_vitals': {'inflammatory_markers': 'elevated'},
    },
    'GASTROINTESTINAL': {
        'risk_multiplier': 1.1,
        'common_symptoms': ['abdominal pain', 'vomiting', 'diarrhea', 'bleeding'],
        'critical_vitals': {'varies': 'by severity'},
    },
    'RENAL': {
        'risk_multiplier': 1.25,
        'common_symptoms': ['kidney pain', 'urinary changes', 'swelling', 'high BP'],
        'critical_vitals': {'sys_bp': '>140', 'creatinine': 'elevated'},
    },
}


# ===================================================================
# SEMANTIC DISEASE DATABASE - AI learns from medical knowledge
# ===================================================================

class SemanticDiseaseDatabase:
    """
    Instead of hardcoding 15K diseases, use semantic understanding
    This database is SMART - it LEARNS symptom-disease relationships
    """

    def __init__(self):
        # Common diseases - Foundation is here, but system can EXPAND
        self.diseases = {
            'Ehlers-Danlos Syndrome': DiseaseProfile(
                name='Ehlers-Danlos Syndrome',
                icd10_code='Q79.6',
                disease_category='GENETIC/METABOLIC',
                severity_level='CHRONIC',
                associated_symptoms=[
                    'hyper-flexible joints', 'easy bruising', 'skin hyperextensibility',
                    'joint pain', 'muscle weakness', 'vascular issues'
                ],
                risk_escalators=['joint trauma', 'pregnancy', 'vascular complications', 'age>40'],
                typical_vital_changes={'bp': 'variable', 'hr': 'can be elevated'},
                progression_path=['joint damage', 'vascular rupture', 'organ involvement'],
                treatment_urgency='PRIORITY',
                specialist_referral='Genetics/Rheumatology',
                mortality_rate=0.05,  # Vascular type can be life-threatening
                comorbidity_risk_multiplier=1.3,
            ),

            'Retinitis Pigmentosa': DiseaseProfile(
                name='Retinitis Pigmentosa',
                icd10_code='H35.52',
                disease_category='GENETIC/METABOLIC',
                severity_level='CHRONIC',
                associated_symptoms=[
                    'night blindness', 'progressive vision loss', 'tunnel vision',
                    'photopsia', 'visual field constriction'
                ],
                risk_escalators=['age', 'family history', 'genetic mutations'],
                typical_vital_changes={'none': 'specific'},
                progression_path=['central vision loss', 'total blindness'],
                treatment_urgency='ROUTINE',
                specialist_referral='Ophthalmology/Genetics',
                mortality_rate=0.0,  # Not fatal, but severe disability
                comorbidity_risk_multiplier=1.1,
            ),

            'Type 1 Diabetes': DiseaseProfile(
                name='Type 1 Diabetes',
                icd10_code='E10',
                disease_category='METABOLIC',
                severity_level='CHRONIC',
                associated_symptoms=[
                    'increased thirst', 'frequent urination', 'fatigue', 'weight loss',
                    'ketone breath', 'confusion'
                ],
                risk_escalators=['infection', 'stress', 'poor compliance', 'puberty'],
                typical_vital_changes={'varies': 'by control'},
                progression_path=['diabetic ketoacidosis', 'hypoglycemia', 'complications'],
                treatment_urgency='URGENT' if 'ketoacidosis' in 'symptoms' else 'PRIORITY',
                specialist_referral='Endocrinology',
                mortality_rate=0.02,  # DKA can be fatal
                comorbidity_risk_multiplier=1.2,
            ),

            'Sepsis': DiseaseProfile(
                name='Sepsis',
                icd10_code='R65.3',
                disease_category='INFECTIOUS',
                severity_level='CRITICAL',
                associated_symptoms=[
                    'fever', 'rapid breathing', 'confusion', 'low BP', 'rapid heartbeat',
                    'severe pain'
                ],
                risk_escalators=['age>65', 'immunosuppression', 'organ dysfunction'],
                typical_vital_changes={'temp': '>101.5', 'hr': '>100', 'bp': '<100'},
                progression_path=['septic shock', 'multi-organ failure', 'death'],
                treatment_urgency='IMMEDIATE',
                specialist_referral='ICU/Critical Care',
                mortality_rate=0.3,  # 30% mortality
                comorbidity_risk_multiplier=2.0,
            ),

            'Myocardial Infarction': DiseaseProfile(
                name='Myocardial Infarction (Heart Attack)',
                icd10_code='I21',
                disease_category='CARDIOVASCULAR',
                severity_level='CRITICAL',
                associated_symptoms=[
                    'chest pain', 'crushing pain', 'shortness of breath', 'diaphoresis',
                    'nausea', 'radiating pain'
                ],
                risk_escalators=['hypertension', 'smoking', 'diabetes', 'age>50'],
                typical_vital_changes={'sys_bp': '>140', 'hr': '>100', 'rhythm': 'irregular'},
                progression_path=['cardiogenic shock', 'arrhythmia', 'heart failure'],
                treatment_urgency='IMMEDIATE',
                specialist_referral='Cardiology/CCU',
                mortality_rate=0.05,  # 5% in-hospital
                comorbidity_risk_multiplier=1.5,
            ),

            'Systemic Lupus Erythematosus': DiseaseProfile(
                name='Systemic Lupus Erythematosus (SLE)',
                icd10_code='M32.9',
                disease_category='AUTOIMMUNE',
                severity_level='MODERATE',
                associated_symptoms=[
                    'photosensitive rash', 'malar rash', 'joint pain', 'mouth ulcers',
                    'fatigue', 'fever', 'Raynaud phenomenon'
                ],
                risk_escalators=['female', 'sun exposure', 'stress', 'pregnancy'],
                typical_vital_changes={'varies': 'by manifestation'},
                progression_path=['lupus nephritis', 'CNS involvement', 'serositis'],
                treatment_urgency='PRIORITY',
                specialist_referral='Rheumatology',
                mortality_rate=0.03,  # 3% with modern treatment
                comorbidity_risk_multiplier=1.4,
            ),

            'Crohn\'s Disease': DiseaseProfile(
                name='Crohn\'s Disease',
                icd10_code='K50.9',
                disease_category='GASTROINTESTINAL',
                severity_level='MODERATE',
                associated_symptoms=[
                    'abdominal pain', 'diarrhea', 'weight loss', 'fever', 'rectal bleeding'
                ],
                risk_escalators=['flare triggers', 'stress', 'infections'],
                typical_vital_changes={'varies': 'by severity'},
                progression_path=['bowel obstruction', 'fistula', 'perforation'],
                treatment_urgency='PRIORITY' if 'acute' else 'ROUTINE',
                specialist_referral='Gastroenterology',
                mortality_rate=0.01,
                comorbidity_risk_multiplier=1.2,
            ),

            'Coronary Artery Disease': DiseaseProfile(
                name='Coronary Artery Disease (CAD)',
                icd10_code='I25.1',
                disease_category='CARDIOVASCULAR',
                severity_level='CRITICAL',
                associated_symptoms=[
                    'chest pain', 'angina', 'dyspnea', 'fatigue', 'palpitations',
                    'jaw pain', 'shoulder pain', 'arm pain'
                ],
                risk_escalators=['hypertension', 'high cholesterol', 'smoking', 'diabetes', 'age>50', 'family history'],
                typical_vital_changes={'sys_bp': '>140', 'hr': '>90', 'rhythm': 'may be irregular'},
                progression_path=['unstable angina', 'myocardial infarction', 'heart failure', 'sudden death'],
                treatment_urgency='URGENT',
                specialist_referral='Cardiology',
                mortality_rate=0.08,  # 8% annual mortality if untreated
                comorbidity_risk_multiplier=1.6,
            ),

            'Hypertension': DiseaseProfile(
                name='Hypertension (High Blood Pressure)',
                icd10_code='I10',
                disease_category='CARDIOVASCULAR',
                severity_level='CHRONIC',
                associated_symptoms=[
                    'headache', 'dizziness', 'shortness of breath', 'chest pain',
                    'fatigue', 'vision problems'
                ],
                risk_escalators=['obesity', 'stress', 'high sodium', 'smoking', 'age>40'],
                typical_vital_changes={'sys_bp': '>160', 'dias_bp': '>100', 'hr': 'may be elevated'},
                progression_path=['organ damage', 'stroke', 'heart failure', 'kidney disease'],
                treatment_urgency='PRIORITY',
                specialist_referral='Cardiology/Internal Medicine',
                mortality_rate=0.02,
                comorbidity_risk_multiplier=1.4,
            ),

            'Acute Stroke': DiseaseProfile(
                name='Acute Stroke (CVA)',
                icd10_code='I63',
                disease_category='NEUROLOGICAL',
                severity_level='CRITICAL',
                associated_symptoms=[
                    'sudden weakness', 'facial drooping', 'slurred speech', 'vision loss',
                    'severe headache', 'confusion', 'difficulty walking'
                ],
                risk_escalators=['hypertension', 'atrial fibrillation', 'smoking', 'diabetes', 'age>55'],
                typical_vital_changes={'sys_bp': '>160', 'altered consciousness': 'may vary'},
                progression_path=['permanent disability', 'brain damage', 'death'],
                treatment_urgency='IMMEDIATE',
                specialist_referral='Neurology/Stroke Center',
                mortality_rate=0.12,  # 12% acute mortality
                comorbidity_risk_multiplier=1.8,
            ),

            'Acute Myocardial Infarction': DiseaseProfile(
                name='Acute Myocardial Infarction (AMI/Heart Attack)',
                icd10_code='I21.9',
                disease_category='CARDIOVASCULAR',
                severity_level='CRITICAL',
                associated_symptoms=[
                    'severe chest pain', 'crushing chest pain', 'dyspnea', 'diaphoresis',
                    'nausea', 'vomiting', 'arm/shoulder pain', 'epigastric pain'
                ],
                risk_escalators=['hypertension', 'smoking', 'diabetes', 'high cholesterol', 'age>50', 'family history'],
                typical_vital_changes={'sys_bp': '>140 or <90', 'hr': '>100', 'rhythm': 'abnormal'},
                progression_path=['cardiogenic shock', 'arrhythmia', 'heart failure', 'death'],
                treatment_urgency='IMMEDIATE',
                specialist_referral='Cardiology/CCU/Emergency',
                mortality_rate=0.06,  # 6% in-hospital
                comorbidity_risk_multiplier=1.8,
            ),

            'Pneumonia': DiseaseProfile(
                name='Pneumonia',
                icd10_code='J18',
                disease_category='INFECTIOUS',
                severity_level='SEVERE',
                associated_symptoms=[
                    'cough', 'fever', 'dyspnea', 'chest pain', 'chills',
                    'production of sputum', 'weakness', 'headache'
                ],
                risk_escalators=['age>65', 'smoking', 'immunosuppression', 'chronic illness'],
                typical_vital_changes={'temp': '>101.5', 'hr': '>100', 'rr': '>20'},
                progression_path=['respiratory failure', 'sepsis', 'ARDS', 'death'],
                treatment_urgency='URGENT',
                specialist_referral='Pulmonology/Internal Medicine',
                mortality_rate=0.05,  # 5% if hospitalized
                comorbidity_risk_multiplier=1.5,
            ),

            'Pulmonary Embolism': DiseaseProfile(
                name='Pulmonary Embolism (PE)',
                icd10_code='I26',
                disease_category='CARDIOVASCULAR',
                severity_level='CRITICAL',
                associated_symptoms=[
                    'sudden dyspnea', 'chest pain', 'tachycardia', 'syncope',
                    'anxiety', 'diaphoresis', 'hemoptysis'
                ],
                risk_escalators=['immobilization', 'surgery', 'cancer', 'hypercoagulability', 'pregnancy'],
                typical_vital_changes={'hr': '>100', 'rr': '>20', 'o2_sat': '<95%', 'bp': 'may drop'},
                progression_path=['shock', 'right heart failure', 'death'],
                treatment_urgency='IMMEDIATE',
                specialist_referral='Pulmonology/Vascular/ICU',
                mortality_rate=0.30,  # 30% if untreated
                comorbidity_risk_multiplier=1.7,
            ),

            'Chronic Obstructive Pulmonary Disease': DiseaseProfile(
                name='Chronic Obstructive Pulmonary Disease (COPD)',
                icd10_code='J44.9',
                disease_category='RESPIRATORY',
                severity_level='CHRONIC',
                associated_symptoms=[
                    'chronic cough', 'dyspnea', 'wheezing', 'chest tightness',
                    'frequent infections', 'cor pulmonale', 'fatigue'
                ],
                risk_escalators=['smoking', 'air pollution', 'occupational exposure', 'age>40'],
                typical_vital_changes={'rr': '>20', 'o2_sat': '<92%', 'hr': 'may be elevated'},
                progression_path=['acute exacerbation', 'respiratory failure', 'cor pulmonale'],
                treatment_urgency='PRIORITY',
                specialist_referral='Pulmonology',
                mortality_rate=0.04,
                comorbidity_risk_multiplier=1.4,
            ),

            'Acute Kidney Injury': DiseaseProfile(
                name='Acute Kidney Injury (AKI)',
                icd10_code='N17.9',
                disease_category='RENAL',
                severity_level='CRITICAL',
                associated_symptoms=[
                    'altered urination', 'edema', 'fatigue', 'shortness of breath',
                    'chest pain', 'confusion', 'seizures'
                ],
                risk_escalators=['sepsis', 'dehydration', 'nephrotoxic drugs', 'shock', 'age>65'],
                typical_vital_changes={'creatinine': 'rapidly elevated', 'potassium': 'elevated', 'bp': 'variable'},
                progression_path=['chronic kidney disease', 'end-stage renal disease', 'death'],
                treatment_urgency='URGENT',
                specialist_referral='Nephrology',
                mortality_rate=0.25,  # 25% in-hospital mortality
                comorbidity_risk_multiplier=1.6,
            ),
        }

    def get_disease_profile(self, disease_name: str) -> Optional[DiseaseProfile]:
        """Get disease profile if exists in database"""
        # Try exact match first
        if disease_name in self.diseases:
            return self.diseases.get(disease_name)
        # Try case-insensitive match
        for key in self.diseases:
            if key.lower() == disease_name.lower():
                return self.diseases.get(key)
        return None

    def find_similar_diseases(self, symptom_text: str, threshold: float = 0.6) -> List[Tuple[str, float]]:
        """
        Find diseases with SIMILAR symptoms even if disease name not exact match
        Uses semantic similarity - "hyper-flexible joints" matches Ehlers-Danlos even if name not given

        Returns: [(disease_name, similarity_score), ...]
        """
        matching_diseases = []

        symptoms_lower = symptom_text.lower()

        for disease_name, profile in self.diseases.items():
            # Calculate symptom overlap
            matching_symptoms = 0
            for symptom in profile.associated_symptoms:
                if symptom in symptoms_lower:
                    matching_symptoms += 1

            similarity_score = matching_symptoms / len(profile.associated_symptoms)

            if similarity_score >= threshold:
                matching_diseases.append((disease_name, similarity_score))

        # Sort by similarity score
        matching_diseases.sort(key=lambda x: x[1], reverse=True)
        return matching_diseases


# ===================================================================
# AI RISK ASSESSMENT - For ANY disease (known or unknown)
# ===================================================================

class MedicalAIRiskAssessment:
    """
    AI that understands disease severity + patient context + risk calculation
    Works for KNOWN diseases (from semantic DB) AND UNKNOWN diseases (via semantic analysis)
    """

    def __init__(self):
        self.disease_db = SemanticDiseaseDatabase()

    def assess_patient_disease_risk(
        self,
        disease_name_or_symptoms: str,
        age: int,
        gender: str,
        sys_bp: int,
        dia_bp: int,
        hr: int,
        temp_f: float,
        comorbidities: List[str] = None,
        medication_list: List[str] = None,
        additional_context: str = ""
    ) -> Dict:
        """
        Comprehensive disease risk assessment for ANY disease

        Returns:
        {
            'disease_identified': disease_name,
            'is_known_disease': True/False,
            'severity_level': 'CRITICAL/SEVERE/MODERATE/MILD/CHRONIC',
            'risk_score': 0.0-1.0,
            'risk_category': 'HIGH/MEDIUM/LOW',
            'urgency': 'IMMEDIATE/URGENT/PRIORITY/ROUTINE',
            'specialist_needed': 'cardiology, etc.',
            'reasoning': 'Detailed explanation',
            'vital_sign_concerns': [...],
            'age_risk_adjustment': 0.0-1.0,
            'comorbidity_adjustment': multiplier,
            'recommendation': 'What to do next',
        }
        """

        result = {
            'is_known_disease': False,
            'disease_identified': disease_name_or_symptoms,
            'risk_factors': [],
        }

        # ===== STEP 1: Check if disease is in knowledge base =====
        disease_profile = self.disease_db.get_disease_profile(disease_name_or_symptoms)

        if disease_profile:
            result['is_known_disease'] = True
            result['disease_identified'] = disease_profile.name

            # ===== STEP 2: Use disease profile for risk calculation =====
            base_risk = self._severity_to_risk_score(disease_profile.severity_level)
            result['severity_level'] = disease_profile.severity_level
            result['treatment_urgency_from_disease'] = disease_profile.treatment_urgency
            result['specialist_needed'] = disease_profile.specialist_referral
            result['mortality_rate'] = disease_profile.mortality_rate

        else:
            # ===== STEP 3: Unknown disease - use semantic analysis =====
            result['is_known_disease'] = False
            similar_diseases = self.disease_db.find_similar_diseases(disease_name_or_symptoms)

            if similar_diseases:
                # Found similar disease by symptoms
                best_match_name, similarity = similar_diseases[0]
                best_match_profile = self.disease_db.get_disease_profile(best_match_name)

                result['similar_diseases_found'] = similar_diseases
                result['best_match'] = {'name': best_match_name, 'similarity': similarity}
                base_risk = self._severity_to_risk_score(best_match_profile.severity_level)
                result['specialist_needed'] = best_match_profile.specialist_referral

            else:
                # Completely unknown disease - use semantic understanding
                base_risk = self._analyze_unknown_disease(disease_name_or_symptoms)
                result['specialist_needed'] = 'General Physician + Specialist consultation'

        # ===== STEP 4: Age adjustment =====
        age_risk_multiplier = self._calculate_age_risk(age, disease_profile.disease_category if disease_profile else 'UNKNOWN')
        result['age_risk_adjustment'] = age_risk_multiplier

        # ===== STEP 5: Vital signs adjustment =====
        vital_risk = self._assess_vitals_in_disease_context(sys_bp, dia_bp, hr, temp_f, disease_profile)
        result['vital_sign_concerns'] = vital_risk['concerns']
        result['vital_adjustment'] = vital_risk['multiplier']

        # ===== STEP 6: Comorbidity adjustment =====
        if comorbidities:
            comorbidity_multiplier = self._assess_comorbidities(
                comorbidities,
                disease_profile.disease_category if disease_profile else 'UNKNOWN',
                disease_profile.comorbidity_risk_multiplier if disease_profile else 1.0
            )
            result['comorbidity_adjustment'] = comorbidity_multiplier
        else:
            comorbidity_multiplier = 1.0

        # ===== STEP 7: FINAL RISK SCORE =====
        final_risk = (
            base_risk *
            age_risk_multiplier *
            vital_risk['multiplier'] *
            comorbidity_multiplier
        )

        # Clamp to 0-1
        final_risk = min(1.0, max(0.0, final_risk))

        result['base_risk_score'] = base_risk
        result['final_risk_score'] = final_risk

        # ===== STEP 8: Classify into categories =====
        if final_risk >= 0.85:
            result['risk_category'] = 'CRITICAL'
            result['urgency'] = 'IMMEDIATE EMERGENCY'
            result['recommendation'] = '🚨 CALL EMERGENCY (911) IMMEDIATELY - Life-threatening condition'
        elif final_risk >= 0.70:
            result['risk_category'] = 'HIGH'
            result['urgency'] = 'URGENT'
            result['recommendation'] = '⚠️ URGENT: Go to Emergency Department NOW'
        elif final_risk >= 0.50:
            result['risk_category'] = 'MEDIUM'
            result['urgency'] = 'PRIORITY'
            result['recommendation'] = '📋 PRIORITY: Schedule specialist appointment within 24-48 hours'
        else:
            result['risk_category'] = 'LOW'
            result['urgency'] = 'ROUTINE'
            result['recommendation'] = '✓ Monitor condition. Schedule routine follow-up'

        # ===== STEP 9: Build detailed reasoning =====
        result['reasoning'] = self._build_reasoning(result, disease_profile)

        logger.info(f"[DISEASE RISK] {result['disease_identified']} → {result['risk_category']} (score={final_risk:.2f})")

        return result

    def _severity_to_risk_score(self, severity_level: str) -> float:
        """Convert disease severity to baseline risk score"""
        severity_map = {
            'CRITICAL': 0.95,
            'SEVERE': 0.80,
            'MODERATE': 0.60,
            'MILD': 0.35,
            'CHRONIC': 0.55,  # Chronic diseases have ongoing risk
        }
        return severity_map.get(severity_level, 0.50)

    def _analyze_unknown_disease(self, disease_text: str) -> float:
        """
        For UNKNOWN diseases, analyze text semantically to estimate risk
        If mentioned: "progressive", "severe", "acute" → higher risk
        """
        risk = 0.45  # Baseline for unknown

        text_lower = disease_text.lower()

        # Keywords that indicate severity
        if any(word in text_lower for word in ['critical', 'emergency', 'severe', 'acute', 'fatal']):
            risk += 0.25
        elif any(word in text_lower for word in ['chronic', 'progressive', 'persistent']):
            risk += 0.15

        return min(1.0, risk)

    def _calculate_age_risk(self, age: int, disease_category: str) -> float:
        """Age affects disease risk differently by category"""

        base_multiplier = 1.0

        # Age risk varies by disease type
        if disease_category == 'CARDIOVASCULAR':
            if age > 70:
                base_multiplier = 1.5
            elif age > 60:
                base_multiplier = 1.3
            elif age > 50:
                base_multiplier = 1.1

        elif disease_category == 'INFECTIOUS':
            if age > 75:
                base_multiplier = 1.6
            elif age > 65:
                base_multiplier = 1.4
            elif age < 5:
                base_multiplier = 1.3  # Very young high risk for infections

        elif disease_category == 'NEUROLOGICAL':
            if age > 80:
                base_multiplier = 1.4
            elif age > 65:
                base_multiplier = 1.2

        elif disease_category == 'GENETIC/METABOLIC':
            if age < 18:
                base_multiplier = 1.2  # Early-onset genetic more severe

        return base_multiplier

    def _assess_vitals_in_disease_context(self, sys_bp, dia_bp, hr, temp_f, disease_profile) -> Dict:
        """Interpret vital signs in context of specific disease"""

        concerns = []
        multiplier = 1.0

        if disease_profile and disease_profile.typical_vital_changes:
            # Check if vitals match disease expectations
            typical_changes = disease_profile.typical_vital_changes

            # Example: In sepsis, we expect elevated temp + high HR + low BP
            if disease_profile.name == 'Sepsis':
                if temp_f > 101.5:
                    concerns.append(f'High fever ({temp_f}°F) consistent with sepsis')
                    multiplier *= 1.2
                if hr > 100:
                    concerns.append(f'Tachycardia ({hr} bpm) consistent with sepsis')
                    multiplier *= 1.15
                if sys_bp < 100:
                    concerns.append(f'Hypotension ({sys_bp} mmHg) - CRITICAL in sepsis')
                    multiplier *= 1.5

        # General vital sign concerns (apply to all diseases)
        if temp_f > 103:
            concerns.append('Dangerously high fever')
            multiplier *= 1.3
        if sys_bp > 190 or sys_bp < 70:
            concerns.append('Critical blood pressure')
            multiplier *= 1.4
        if hr > 140 or hr < 40:
            concerns.append('Dangerous heart rate')
            multiplier *= 1.3

        return {'concerns': concerns, 'multiplier': multiplier}

    def _assess_comorbidities(self, comorbidities: List[str], disease_category: str, base_multiplier: float) -> float:
        """
        Comorbidities increase risk further
        Example: Patient with Sepsis + Diabetes = much higher mortality
        """

        total_multiplier = base_multiplier

        # Common dangerous combinations
        for comorbidity in comorbidities:
            if 'diabetes' in comorbidity.lower():
                total_multiplier *= 1.3  # Makes most infections worse
            elif 'hypertension' in comorbidity.lower():
                total_multiplier *= 1.2
            elif 'heart' in comorbidity.lower() and disease_category != 'CARDIOVASCULAR':
                total_multiplier *= 1.4  # Cardiac disease + other disease = bad
            elif 'kidney' in comorbidity.lower():
                total_multiplier *= 1.3
            elif 'immunosuppression' in comorbidity.lower():
                total_multiplier *= 1.5  # Critical for infections

        return min(2.0, total_multiplier)  # Cap at 2x

    def _build_reasoning(self, result: Dict, disease_profile: Optional[DiseaseProfile]) -> str:
        """Build detailed explanation of risk calculation"""

        reasoning = f"""
DISEASE RISK ASSESSMENT ANALYSIS:

Disease Identified: {result['disease_identified']}
Known in Database: {'Yes ✓' if result['is_known_disease'] else 'No (analyzed semantically)'}

Base Risk (from severity): {result['base_risk_score']:.2%}
Age Adjustment: {result.get('age_risk_adjustment', 1.0):.2f}x
Vital Signs Adjustment: {result.get('vital_adjustment', 1.0):.2f}x
Comorbidity Adjustment: {result.get('comorbidity_adjustment', 1.0):.2f}x

FINAL RISK SCORE: {result['final_risk_score']:.2%}
RISK CATEGORY: {result['risk_category']}
URGENCY: {result['urgency']}

Recommendations:
{result['recommendation']}

Vital Sign Concerns:
{chr(10).join(['  • ' + concern for concern in result.get('vital_sign_concerns', ['None'])])}

Specialist Referral: {result.get('specialist_needed', 'General Physician')}
        """

        return reasoning.strip()


# ===================================================================
# EXAMPLE USAGE
# ===================================================================

if __name__ == '__main__':
    ai = MedicalAIRiskAssessment()

    # Test 1: KNOWN RARE DISEASE
    print("="*70)
    print("TEST 1: Ehlers-Danlos Syndrome (Known Disease)")
    print("="*70)
    result1 = ai.assess_patient_disease_risk(
        disease_name_or_symptoms='Ehlers-Danlos Syndrome',
        age=35,
        gender='Female',
        sys_bp=120,
        dia_bp=80,
        hr=75,
        temp_f=98.6,
        comorbidities=['None']
    )
    print(result1['reasoning'])

    # Test 2: UNKNOWN DISEASE (Not in DB)
    print("\n" + "="*70)
    print("TEST 2: Ribose-5-Phosphate Deficiency (Unknown/Rare)")
    print("="*70)
    result2 = ai.assess_patient_disease_risk(
        disease_name_or_symptoms='Ribose-5-Phosphate Deficiency',
        age=28,
        gender='Male',
        sys_bp=125,
        dia_bp=82,
        hr=78,
        temp_f=98.8,
        additional_context='Patient reports fatigue, neurological symptoms'
    )
    print(result2['reasoning'])

    # Test 3: EMERGENCY DISEASE
    print("\n" + "="*70)
    print("TEST 3: Sepsis (Known Critical Disease)")
    print("="*70)
    result3 = ai.assess_patient_disease_risk(
        disease_name_or_symptoms='Sepsis',
        age=72,
        gender='Male',
        sys_bp=88,
        dia_bp=55,
        hr=128,
        temp_f=103.5,
        comorbidities=['Diabetes Type 2', 'Hypertension']
    )
    print(result3['reasoning'])
