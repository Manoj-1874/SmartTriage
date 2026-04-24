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
from typing import Dict, Tuple, List, Optional
from utils.news2 import calculate_news2_score
from utils.universal_disease_knowledge import UniversalDiseaseRiskAssessment

logger = logging.getLogger(__name__)


class IntegratedDualBrainRisk:
    """
    Complete risk assessment pipeline:
    Disease Recognition → Symptom Extraction → BERT + XGBoost Fusion → Risk Output
    """

    def __init__(self, xgb_model=None, scaler=None, feature_names=None, bert_model=None, encoders=None):
        """
        Initialize with existing XGBoost + BERT models

        Args:
            xgb_model: Trained XGBoost model for numerical feature analysis
            scaler: Sklearn scaler for feature normalization
            feature_names: Feature names expected by XGBoost
            bert_model: BERT model for semantic analysis
            encoders: Label encoders for categorical features
        """
        self.xgb_model = xgb_model
        self.scaler = scaler
        self.feature_names = feature_names or []
        self.bert_model = bert_model
        self.encoders = encoders or {}
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
            symptoms=symptoms,
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
        
        # [ENHANCED] Fetch authoritative description from external research (Wiki/SNOMED)
        # and provide it to the semantic brain (BERT) for enriched analysis
        external_context = disease_info.get('description') or disease_info.get('reasoning', '')
        
        combined_symptoms = self._combine_symptoms(
            patient_symptoms=symptoms, 
            disease_symptoms=disease_symptoms,
            disease_description=external_context
        )

        result['disease_symptoms'] = disease_symptoms
        result['combined_symptoms'] = combined_symptoms

        # ===== STEP 3: BERT ANALYSIS (Semantic Understanding) =====
        logger.info(f"🧠 [DUAL-BRAIN] Step 1: Analyzing symptoms with BERT (Semantic Brain)...")
        bert_risk = self._analyze_symptoms_with_bert(combined_symptoms)
        result['bert_analysis'] = bert_risk
        logger.info(f"✅ [BERT-RESULT] Score: {bert_risk.get('risk_score', 0):.2%} | Label: {bert_risk.get('risk_label')}")

        # ===== STEP 4: XGBOOST ANALYSIS (Numerical Vitals) =====
        logger.info(f"🔢 [DUAL-BRAIN] Step 2: Analyzing vitals with XGBoost (Numerical Brain)...")
        xgb_risk = self._analyze_vitals_with_xgboost(
            age=age,
            gender=gender,
            symptoms=symptoms,
            sys_bp=sys_bp,
            dia_bp=dia_bp,
            hr=hr,
            temp_f=temp_f,
            pre_conditions=comorbidities
        )
        result['xgboost_analysis'] = xgb_risk
        logger.info(f"✅ [XGB-RESULT] Score: {xgb_risk.get('risk_score', 0):.2%} | Label: {xgb_risk.get('risk_label')}")

        # ===== STEP 5: DUAL-BRAIN FUSION =====
        logger.info(f"⚖️ [DUAL-BRAIN-v2.2-STABLE] Step 3: Fusing semantic + numerical insights...")
        final_assessment = self._fuse_dual_brain_results(
            bert_result=bert_risk,
            xgb_result=xgb_risk,
            disease_context=disease_info,
            age=age,
            sys_bp=sys_bp,
            dia_bp=dia_bp,
            hr=hr,
            temp_f=temp_f,
            spo2=spo2,
            respiration_rate=respiration_rate
        )

        # Add NEWS2 score for clinical baseline
        news2_val = calculate_news2_score(
            respiration_rate=respiration_rate,
            spo2=spo2,
            temp_f=temp_f,
            sys_bp=sys_bp,
            hr=hr
        )
        result['news2_score'] = news2_val
        result['final_risk'] = final_assessment
        
        logger.info(f"🎯 [FUSION-COMPLETE] Final Risk: {final_assessment.get('risk_category')} ({final_assessment.get('final_risk_score', 0):.2%}) | NEWS2: {news2_val}")

        logger.info(f"""
[INTEGRATED ASSESSMENT]
Disease: {disease_recognition.get('final_risk', {}).get('disease_identified', 'Unknown')}
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
        # Use str() and or "" to safely handle None values
        disease_name = str(disease_info.get('disease_identified') or "").lower()

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

    def _combine_symptoms(self, patient_symptoms: str, disease_symptoms: List[str], disease_description: str = None) -> str:
        """Merge patient-reported symptoms with disease-expected symptoms and external medical knowledge"""

        # Patient's own description
        combined = str(patient_symptoms or "")

        # Add authoritative medical description as high-priority context for BERT
        if disease_description:
            # Strip excessive length to stay within BERT token limits (approx 512 tokens)
            clean_desc = str(disease_description)[:800]
            if combined:
                combined += f" [Knowledge Base: {clean_desc}]"
            else:
                combined = f"Knowledge Base: {clean_desc}"

        # Add disease-expected symptoms as additional context
        if disease_symptoms:
            disease_symp_str = ', '.join(disease_symptoms)
            if combined:
                combined += f" (Clinical profile: {disease_symp_str})"
            else:
                combined = f"Clinical profile: {disease_symp_str}"

        return combined

    def _analyze_symptoms_with_bert(self, symptoms_text: str) -> Dict:
        """
        Use BERT to analyze symptom severity semantically
        """

        result = {
            'raw_text': symptoms_text,
            'risk_score': 0.5,  # Default
            'risk_label': 'MEDIUM',
            'confidence': 0.0,
        }

        if not symptoms_text or not symptoms_text.strip():
            result['risk_label'] = 'LOW'
            result['risk_score'] = 0.2
            return result

        if not self.bert_model:
            return result

        try:
            # Run BERT classification
            try:
                prediction = self.bert_model(symptoms_text, top_k=3)
            except Exception as e:
                if 'token_type_ids' in str(e):
                    # Manual keyword severity check as fallback
                    critical_keywords = ['severe', 'critical', 'emergency', 'intense', 'unbearable', 'bleeding', 'chest pain']
                    medium_keywords = ['moderate', 'fever', 'persistent', 'pain', 'vomiting', 'nausea']
                    
                    text_lower = symptoms_text.lower()
                    if any(word in text_lower for word in critical_keywords):
                        result['risk_label'] = 'CRITICAL'
                        result['risk_score'] = 0.88
                    elif any(word in text_lower for word in medium_keywords):
                        result['risk_label'] = 'MEDIUM'
                        result['risk_score'] = 0.55
                    
                    return result
                raise e

            if prediction and len(prediction) > 0:
                top = prediction[0]
                label = top.get('label', 'MEDIUM').upper()
                score = top.get('score', 0.5)

                result['bert_label'] = label
                result['confidence'] = score

                label_to_score = {
                    'CRITICAL': 0.95,
                    'HIGH': 0.80,
                    'MEDIUM': 0.55,
                    'LOW': 0.30,
                }

                result['risk_score'] = label_to_score.get(label, 0.55)
                result['risk_label'] = label

        except Exception as e:
            logger.error(f"BERT analysis error: {str(e)}")

        return result

    def _analyze_vitals_with_xgboost(
        self, age: int, gender: str, symptoms: str, sys_bp: int, dia_bp: int, 
        hr: int, temp_f: float, pre_conditions: List[str] = None,
    ) -> Dict:
        """
        Use XGBoost to analyze vital signs and patient profile
        """

        result = {
            'risk_score': 0.5,
            'risk_label': 'MEDIUM',
            'features_used': [],
        }

        if not self.xgb_model or not self.scaler:
            return result

        try:
            features = self._prepare_xgboost_features(
                age=age, gender=gender, symptoms=symptoms, 
                sys_bp=sys_bp, dia_bp=dia_bp, hr=hr, temp_f=temp_f, 
                pre_conditions=pre_conditions
            )

            result['features_used'] = features

            if len(features) > 0:
                features_array = np.array([features]).astype(float)
                features_scaled = self.scaler.transform(features_array) if self.scaler else features_array
                xgb_prediction = self.xgb_model.predict_proba(features_scaled)

                if len(xgb_prediction) > 0:
                    risk_prob = xgb_prediction[0]
                    high_risk_prob = risk_prob[2] if len(risk_prob) >= 3 else risk_prob[1] if len(risk_prob) == 2 else risk_prob[0]

                    result['risk_score'] = float(high_risk_prob)
                    if high_risk_prob >= 0.75: result['risk_label'] = 'HIGH'
                    elif high_risk_prob >= 0.50: result['risk_label'] = 'MEDIUM'
                    else: result['risk_label'] = 'LOW'

        except Exception as e:
            logger.error(f"XGBoost analysis error: {str(e)}")

        return result

    def _prepare_xgboost_features(
        self, age: int, gender: str, symptoms: str, sys_bp: int, dia_bp: int, 
        hr: int, temp_f: float, pre_conditions: List[str] = None
    ) -> list:
        """Prepare features for XGBoost model"""
        features = []
        features.append(float(age))
        
        gender_val = str(gender).capitalize()
        if 'Gender' in self.encoders:
            try: features.append(float(self.encoders['Gender'].transform([gender_val])[0]))
            except: features.append(1.0 if gender_val == 'Male' else 0.0)
        else: features.append(1.0 if gender_val == 'Male' else 0.0)

        symptom_val = str(symptoms).split(',')[0].strip().capitalize() if symptoms else "None"
        if 'Symptoms' in self.encoders:
            try: features.append(float(self.encoders['Symptoms'].transform([symptom_val])[0]))
            except: features.append(0.0)
        else: features.append(0.0)

        features.append(float(sys_bp))
        features.append(float(dia_bp))
        features.append(float(hr))
        
        temp_c = (float(temp_f) - 32) * 5 / 9
        features.append(temp_c)

        pre_cond_val = str(pre_conditions[0]).capitalize() if pre_conditions else "None"
        if 'Pre_Conditions' in self.encoders:
            try: features.append(float(self.encoders['Pre_Conditions'].transform([pre_cond_val])[0]))
            except: features.append(0.0)
        else: features.append(0.0)

        return features

    def _fuse_dual_brain_results(
        self, bert_result: Dict, xgb_result: Dict, disease_context: Dict,
        age: int, sys_bp: int, dia_bp: int, hr: int, temp_f: float,
        spo2: int = 95, respiration_rate: int = 16
    ) -> Dict:
        """
        Fuse BERT + XGBoost + Disease Context
        """

        bert_score = bert_result.get('risk_score', 0.5)
        xgb_score = xgb_result.get('risk_score', 0.5)

        disease_score = 0.5
        disease_multiplier = 1.0
        if disease_context.get('risk_score'):
            disease_score = disease_context.get('risk_score')
        if disease_context.get('comorbidity_adjustment'):
            disease_multiplier = disease_context.get('comorbidity_adjustment', 1.0)

        final_score = (xgb_score * 0.40 + bert_score * 0.35 + disease_score * 0.25) * disease_multiplier

        # Numerical Safety Layer
        vitals_multiplier = 1.0
        if sys_bp < 90 or dia_bp < 60:
            vitals_multiplier *= 1.3
            logger.warning(f"⚠️ [VITALS-ALERT] Low BP detected ({sys_bp}/{dia_bp}). Escalating risk.")
        elif sys_bp > 160 or dia_bp > 100:
            vitals_multiplier *= 1.25
            logger.warning(f"⚠️ [VITALS-ALERT] High BP detected ({sys_bp}/{dia_bp}). Escalating risk.")
            
        if hr > 110 or hr < 50:
            vitals_multiplier *= 1.15
            logger.warning(f"⚠️ [VITALS-ALERT] Abnormal heart rate detected ({hr} bpm).")
            
        if spo2 < 92:
            vitals_multiplier *= 1.4
            logger.warning(f"⚠️ [VITALS-ALERT] Low oxygen saturation detected ({spo2}%). Escalating risk.")
        elif spo2 < 95:
            vitals_multiplier *= 1.1
            
        if temp_f > 103.5:
            vitals_multiplier *= 1.3
            logger.warning(f"⚠️ [VITALS-ALERT] High fever detected ({temp_f:.1f}°F). Escalating risk.")
        elif temp_f < 95.0:
            vitals_multiplier *= 1.25
            logger.warning(f"⚠️ [VITALS-ALERT] Low body temperature detected ({temp_f:.1f}°F).")

        if respiration_rate > 30 or respiration_rate < 8:
            vitals_multiplier *= 1.35
            logger.warning(f"⚠️ [VITALS-ALERT] Critical respiratory rate detected ({respiration_rate} bpm).")
            
        final_score *= vitals_multiplier

        if age > 75: final_score *= 1.2
        elif age < 5: final_score *= 1.2

        final_score = min(1.0, max(0.0, final_score))

        if final_score >= 0.85:
            risk_category = 'CRITICAL'
            urgency = 'IMMEDIATE EMERGENCY - Life Threatening'
        elif final_score >= 0.70:
            risk_category = 'HIGH'
            urgency = 'URGENT - Go to ER'
        elif final_score >= 0.50:
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
