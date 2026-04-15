"""
INTEGRATED DUAL-BRAIN RISK ASSESSMENT
Connects: Disease Recognition → Symptom Extraction → BERT + XGBoost → Final Risk

Flow:
1. Disease input (patient types disease name)
2. Check DB → External sources (get disease + symptoms)
3. BERT analyzes symptoms semantically
4. XGBoost analyzes numerical vitals (BP, temp, HR, pain intensity, duration)
5. Combine both → Show final risk
"""

import numpy as np
import logging
from typing import Dict, Tuple, List
from utils.universal_disease_knowledge import UniversalDiseaseRiskAssessment

logger = logging.getLogger(__name__)


class IntegratedDualBrainRisk:
    """
    Complete risk assessment pipeline:
    Disease Recognition → Symptom Extraction → BERT + XGBoost Fusion → Risk Output
    """

    def __init__(self, xgb_model=None, scaler=None, feature_names=None, bert_model=None):
        """
        Initialize with existing XGBoost + BERT models

        Args:
            xgb_model: Trained XGBoost model for numerical feature analysis
            scaler: Sklearn scaler for feature normalization
            feature_names: Feature names expected by XGBoost
            bert_model: BERT model for semantic analysis
        """
        self.xgb_model = xgb_model
        self.scaler = scaler
        self.feature_names = feature_names or []
        self.bert_model = bert_model
        self.disease_system = UniversalDiseaseRiskAssessment()

    def assess_patient_with_disease_context(
        self,
        disease_input: str,  # Disease name or description
        symptoms: str,  # Patient's symptom description
        age: int,
        gender: str,
        sys_bp: int,
        dia_bp: int,
        hr: int,
        temp_f: float,
        spo2: int = 98,
        respiration_rate: int = 16,
        pain_intensity: int = 5,  # 0-10 scale
        symptom_duration_hours: int = 24,
        comorbidities: List[str] = None,
    ) -> Dict:
        """
        Complete integrated assessment using:
        1. Disease recognition (external sources)
        2. Symptom extraction (from disease profile)
        3. BERT semantic analysis (symptom understanding)
        4. XGBoost numerical analysis (vital signs)
        5. Dual-brain fusion (combined risk)

        Returns: Complete risk assessment with reasoning
        """

        result = {
            'disease_input': disease_input,
            'risk_assessment': None,
            'bert_analysis': None,
            'xgboost_analysis': None,
            'final_risk': None,
        }

        # ===== STEP 1: DISEASE RECOGNITION =====
        # Check local DB → SNOMED-CT → External APIs
        disease_recognition = self.disease_system.assess_disease_risk_universal(
            disease_input=disease_input,
            age=age,
            gender=gender,
            sys_bp=sys_bp,
            dia_bp=dia_bp,
            hr=hr,
            temp_f=temp_f,
            comorbidities=comorbidities,
        )

        result['disease_recognition'] = disease_recognition
        disease_info = disease_recognition.get('final_risk', {})

        # ===== STEP 2: EXTRACT SYMPTOMS FROM DISEASE + PATIENT INPUT =====
        disease_symptoms = self._extract_symptoms_from_disease(disease_info)
        combined_symptoms = self._combine_symptoms(symptoms, disease_symptoms)

        result['disease_symptoms'] = disease_symptoms
        result['combined_symptoms'] = combined_symptoms

        # ===== STEP 3: BERT ANALYSIS (Semantic Understanding) =====
        bert_risk = self._analyze_symptoms_with_bert(combined_symptoms)
        result['bert_analysis'] = bert_risk

        # ===== STEP 4: XGBOOST ANALYSIS (Numerical Vitals) =====
        xgb_risk = self._analyze_vitals_with_xgboost(
            age=age,
            sys_bp=sys_bp,
            dia_bp=dia_bp,
            hr=hr,
            temp_f=temp_f,
            spo2=spo2,
            respiration_rate=respiration_rate,
            pain_intensity=pain_intensity,
            symptom_duration_hours=symptom_duration_hours,
        )
        result['xgboost_analysis'] = xgb_risk

        # ===== STEP 5: DUAL-BRAIN FUSION =====
        final_assessment = self._fuse_dual_brain_results(
            bert_result=bert_risk,
            xgb_result=xgb_risk,
            disease_context=disease_info,
            age=age,
        )

        result['final_risk'] = final_assessment

        logger.info(f"""
[INTEGRATED ASSESSMENT]
Disease: {disease_input}
BERT risk: {bert_risk.get('risk_score', 0):.2f}
XGBoost risk: {xgb_risk.get('risk_score', 0):.2f}
FINAL risk: {final_assessment.get('final_risk_score', 0):.2f}
Category: {final_assessment.get('risk_category')}
        """)

        return result

    def _extract_symptoms_from_disease(self, disease_info: Dict) -> List[str]:
        """Extract symptoms from disease profile"""

        symptoms = []

        # Get from disease profile if available
        if disease_info.get('symptoms_from_snomed'):
            symptoms.extend(disease_info.get('symptoms_from_snomed', []))

        # Map disease category to typical symptoms
        disease_name = disease_info.get('disease_identified', '').lower()

        category_symptoms = {
            'cardiovascular': ['chest pain', 'shortness of breath', 'palpitations', 'dizziness'],
            'neurological': ['headache', 'confusion', 'weakness', 'vision changes'],
            'infectious': ['fever', 'cough', 'fatigue', 'body ache'],
            'respiratory': ['cough', 'shortness of breath', 'chest pain'],
            'gastrointestinal': ['abdominal pain', 'nausea', 'vomiting'],
            'renal': ['kidney pain', 'urinary changes', 'swelling'],
            'autoimmune': ['joint pain', 'fatigue', 'rash', 'inflammation'],
            'metabolic': ['fatigue', 'weakness', 'neurological symptoms'],
        }

        for category, category_symp in category_symptoms.items():
            if category in disease_name:
                symptoms.extend(category_symp)
                break

        return list(set(symptoms))  # Remove duplicates

    def _combine_symptoms(self, patient_symptoms: str, disease_symptoms: List[str]) -> str:
        """Merge patient-reported symptoms with disease-expected symptoms"""

        # Patient's own description
        combined = patient_symptoms

        # Add disease-expected symptoms as context
        if disease_symptoms:
            disease_symp_str = ', '.join(disease_symptoms)
            combined += f" (Disease profile: {disease_symp_str})"

        return combined

    def _analyze_symptoms_with_bert(self, symptoms_text: str) -> Dict:
        """
        Use BERT to analyze symptom severity semantically

        BERT scores:
        - HIGH_RISK (label "CRITICAL", "HIGH")
        - MEDIUM_RISK (label "MEDIUM")
        - LOW_RISK (label "LOW")
        """

        result = {
            'raw_text': symptoms_text,
            'risk_score': 0.5,  # Default
            'risk_label': 'MEDIUM',
            'confidence': 0.0,
        }

        if not self.bert_model:
            logger.warning("BERT model not loaded, using default scoring")
            return result

        try:
            # Run BERT classification
            prediction = self.bert_model(symptoms_text, top_k=3)

            # Get top prediction
            if prediction and len(prediction) > 0:
                top = prediction[0]
                label = top.get('label', 'MEDIUM').upper()
                score = top.get('score', 0.5)

                result['bert_label'] = label
                result['confidence'] = score

                # Map label to risk score (0-1)
                label_to_score = {
                    'CRITICAL': 0.95,
                    'HIGH': 0.80,
                    'MEDIUM': 0.55,
                    'LOW': 0.30,
                }

                result['risk_score'] = label_to_score.get(label, 0.55)
                result['risk_label'] = label

                logger.info(f"BERT classification: {label} ({score:.2%})")

        except Exception as e:
            logger.error(f"BERT analysis error: {str(e)}")

        return result

    def _analyze_vitals_with_xgboost(
        self,
        age: int,
        sys_bp: int,
        dia_bp: int,
        hr: int,
        temp_f: float,
        spo2: int,
        respiration_rate: int,
        pain_intensity: int,
        symptom_duration_hours: int,
    ) -> Dict:
        """
        Use XGBoost to analyze numerical vital signs

        Features analyzed:
        - Age, BP (sys/dia), HR, Temperature
        - SpO2, Respiration Rate
        - Pain intensity (0-10), symptom duration
        """

        result = {
            'risk_score': 0.5,  # Default
            'risk_label': 'MEDIUM',
            'features_used': [],
        }

        if not self.xgb_model or not self.scaler:
            logger.warning("XGBoost model not loaded, using default scoring")
            return result

        try:
            # Prepare features for XGBoost
            features = self._prepare_xgboost_features(
                age=age,
                sys_bp=sys_bp,
                dia_bp=dia_bp,
                hr=hr,
                temp_f=temp_f,
                spo2=spo2,
                respiration_rate=respiration_rate,
                pain_intensity=pain_intensity,
                symptom_duration_hours=symptom_duration_hours,
            )

            result['features_used'] = features

            if len(features) > 0:
                # Normalize features
                features_array = np.array([features]).astype(float)

                # Handle scaling if scaler is available
                if self.scaler:
                    try:
                        features_scaled = self.scaler.transform(features_array)
                    except:
                        features_scaled = features_array
                else:
                    features_scaled = features_array

                # Get XGBoost prediction
                xgb_prediction = self.xgb_model.predict_proba(features_scaled)

                # Get risk score (probability of HIGH risk class)
                if len(xgb_prediction) > 0:
                    risk_prob = xgb_prediction[0]

                    # Assume model outputs probabilities for [LOW, MEDIUM, HIGH]
                    if len(risk_prob) >= 3:
                        high_risk_prob = risk_prob[2]  # HIGH class
                    elif len(risk_prob) == 2:
                        high_risk_prob = risk_prob[1]  # Binary: assume second class is HIGH
                    else:
                        high_risk_prob = risk_prob[0]

                    result['risk_score'] = float(high_risk_prob)

                    # Classify
                    if high_risk_prob >= 0.75:
                        result['risk_label'] = 'HIGH'
                    elif high_risk_prob >= 0.50:
                        result['risk_label'] = 'MEDIUM'
                    else:
                        result['risk_label'] = 'LOW'

                    logger.info(f"XGBoost prediction: {result['risk_label']} ({high_risk_prob:.2%})")

        except Exception as e:
            logger.error(f"XGBoost analysis error: {str(e)}")

        return result

    def _prepare_xgboost_features(
        self, age: int, sys_bp: int, dia_bp: int, hr: int, temp_f: float,
        spo2: int, respiration_rate: int, pain_intensity: int,
        symptom_duration_hours: int
    ) -> list:
        """Prepare features for XGBoost model"""

        features = []

        # Add features in the order XGBoost expects
        features.append(age)
        features.append(sys_bp)
        features.append(dia_bp)
        features.append(hr)
        features.append(temp_f)
        features.append(spo2)
        features.append(respiration_rate)
        features.append(pain_intensity)
        features.append(symptom_duration_hours)

        # Add pulse pressure
        pulse_pressure = sys_bp - dia_bp
        features.append(pulse_pressure)

        # Add mean arterial pressure
        map_val = (sys_bp + 2 * dia_bp) / 3
        features.append(map_val)

        return features

    def _fuse_dual_brain_results(
        self,
        bert_result: Dict,
        xgb_result: Dict,
        disease_context: Dict,
        age: int,
    ) -> Dict:
        """
        Fuse BERT (semantic) + XGBoost (numerical) results
        Apply disease-specific risk multipliers

        Weighting:
        - XGBoost: 40% (vital signs are critical)
        - BERT: 35% (symptom severity matters)
        - Disease Context: 25% (disease knowledge)
        """

        # Extract scores
        bert_score = bert_result.get('risk_score', 0.5)
        xgb_score = xgb_result.get('risk_score', 0.5)

        # Disease base score
        disease_score = 0.5
        disease_multiplier = 1.0
        if disease_context.get('risk_score'):
            disease_score = disease_context.get('risk_score')
        if disease_context.get('comorbidity_adjustment'):
            disease_multiplier = disease_context.get('comorbidity_adjustment', 1.0)

        # Weighted fusion
        final_score = (
            xgb_score * 0.40 +      # Vital signs: 40%
            bert_score * 0.35 +     # Symptoms: 35%
            disease_score * 0.25    # Disease knowledge: 25%
        )

        # Apply disease-specific multiplier
        final_score *= disease_multiplier

        # Age-based adjustment
        if age > 75:
            final_score *= 1.2
        elif age > 65:
            final_score *= 1.1
        elif age < 5:
            final_score *= 1.2

        # Cap at 0-1
        final_score = min(1.0, max(0.0, final_score))

        # Classify
        if final_score >= 0.80:
            risk_category = 'HIGH'
            urgency = 'URGENT - Go to ER'
        elif final_score >= 0.60:
            risk_category = 'MEDIUM'
            urgency = 'PRIORITY - Specialist within 24-48h'
        else:
            risk_category = 'LOW'
            urgency = 'ROUTINE - Monitor and follow up'

        return {
            'xgb_score': xgb_score,
            'bert_score': bert_score,
            'disease_score': disease_score,
            'disease_multiplier': disease_multiplier,
            'final_risk_score': final_score,
            'risk_category': risk_category,
            'urgency': urgency,
            'reasoning': f"""
Dual-Brain Analysis Results:
• XGBoost (Vital Signs): {xgb_score:.2%}
• BERT (Symptoms): {bert_score:.2%}
• Disease Context: {disease_score:.2%}
• Comorbidity Adjustment: {disease_multiplier:.2f}x

Weighted Fusion (40% XGBoost + 35% BERT + 25% Disease):
Final Risk Score: {final_score:.2%}
Risk Category: {risk_category}
Urgency: {urgency}
            """.strip(),
        }
