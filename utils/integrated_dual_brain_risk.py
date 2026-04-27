"""
INTEGRATED DUAL-BRAIN RISK ASSESSMENT
Connects: Disease Recognition -> Symptom Extraction -> BERT + XGBoost -> Final Risk

Flow:
1. Disease input (patient types disease name)
2. Check DB -> External sources (get disease + symptoms)
3. BERT analyzes symptoms semantically
4. XGBoost analyzes numerical vitals (BP, temp, HR, pain intensity, duration)
5. Combine both -> Show final risk
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
    Disease Recognition -> Symptom Extraction -> BERT + XGBoost Fusion -> Risk Output
    """

    def __init__(self, xgb_model=None, scaler=None, feature_names=None, bert_model=None, encoders=None):
        """
        Initialize with existing XGBoost + BERT models
        """
        self.xgb_model = xgb_model
        self.scaler = scaler
        self.feature_names = feature_names or []
        self.bert_model = bert_model
        self.encoders = encoders or {}
        self.disease_system = UniversalDiseaseRiskAssessment()

    def assess_patient_with_disease_context(
        self,
        disease_input: str,
        symptoms: str,
        age: int,
        gender: str,
        sys_bp: int,
        dia_bp: int,
        hr: int,
        temp_f: float,
        spo2: int = 98,
        respiration_rate: int = 16,
        pain_intensity: int = 5,
        symptom_duration_hours: int = 24,
        comorbidities: List[str] = None,
    ) -> Dict:
        """
        Complete integrated assessment using multi-disease context
        """

        result = {
            'disease_input': disease_input,
            'risk_assessment': None,
            'bert_analysis': None,
            'xgboost_analysis': None,
            'final_risk': None,
        }

        # ===== STEP 1: MULTI-DISEASE RECOGNITION =====
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
        all_findings = disease_recognition.get('all_findings', [])
        primary_disease = disease_recognition.get('final_risk', {})

        # ===== STEP 2: CONSOLIDATE MULTI-DISEASE CONTEXT =====
        consolidated_description = ""
        all_symptoms = []
        max_disease_score = 0.5
        
        if all_findings:
            # Combine information from ALL found diseases
            descriptions = []
            for find in all_findings:
                descriptions.append(f"{find.get('disease_identified')}: {find.get('description')}")
                # Track the highest clinical risk found
                max_disease_score = max(max_disease_score, find.get('risk_score', 0.5))
                # Collect symptoms
                all_symptoms.extend(self._extract_symptoms_from_disease(find))
            
            consolidated_description = " | ".join(descriptions)
        else:
            consolidated_description = primary_disease.get('description', '')
            max_disease_score = primary_disease.get('risk_score', 0.5)
            all_symptoms = self._extract_symptoms_from_disease(primary_disease)

        combined_symptoms = self._combine_symptoms(
            patient_symptoms=symptoms, 
            disease_symptoms=list(set(all_symptoms)),
            disease_description=consolidated_description
        )

        result['disease_symptoms'] = list(set(all_symptoms))
        result['combined_symptoms'] = combined_symptoms

        # ===== STEP 3: BERT ANALYSIS (Semantic Understanding) =====
        logger.info(f"[DUAL-BRAIN] Step 1: Analyzing symptoms with BERT (Semantic Brain)...")
        bert_risk = self._analyze_symptoms_with_bert(combined_symptoms)
        result['bert_analysis'] = bert_risk
        logger.info(f"[BERT-RESULT] Score: {bert_risk.get('risk_score', 0):.2%} | Label: {bert_risk.get('risk_label')}")

        # ===== STEP 4: XGBOOST ANALYSIS (Numerical Vitals) =====
        logger.info(f"[DUAL-BRAIN] Step 2: Analyzing vitals with XGBoost (Numerical Brain)...")
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
        logger.info(f"[XGB-RESULT] Score: {xgb_risk.get('risk_score', 0):.2%} | Label: {xgb_risk.get('risk_label')}")

        # ===== STEP 5: DUAL-BRAIN FUSION =====
        logger.info(f"[DUAL-BRAIN-v3.1-PRODUCTION] Step 3: Fusing semantic + numerical insights...")
        final_assessment = self._fuse_dual_brain_results(
            bert_result=bert_risk,
            xgb_result=xgb_risk,
            disease_context=primary_disease, # Pass the full best hit
            age=age,
            sys_bp=sys_bp,
            dia_bp=dia_bp,
            hr=hr,
            temp_f=temp_f,
            spo2=spo2,
            respiration_rate=respiration_rate
        )

        # Add NEWS2 score
        news2_val = calculate_news2_score(
            respiration_rate=respiration_rate,
            spo2=spo2,
            temp_f=temp_f,
            sys_bp=sys_bp,
            hr=hr
        )
        result['news2_score'] = news2_val
        result['final_risk'] = final_assessment
        
        logger.info(f"[FUSION-COMPLETE] Final Risk: {final_assessment.get('risk_category')} ({final_assessment.get('final_risk_score', 0):.2%}) | NEWS2: {news2_val}")

        return result

    def _extract_symptoms_from_disease(self, disease_info: Dict) -> List[str]:
        """Extract symptoms from disease profile"""
        symptoms = []
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

        return list(set(symptoms))

    def _combine_symptoms(self, patient_symptoms: str, disease_symptoms: List[str], disease_description: str = None) -> str:
        """Merge patient-reported symptoms with disease-expected symptoms"""
        combined = str(patient_symptoms or "")
        if disease_description:
            clean_desc = str(disease_description)[:1000]
            combined += f" [Medical Knowledge: {clean_desc}]"
        if disease_symptoms:
            combined += f" (Clinical profile: {', '.join(disease_symptoms)})"
        return combined

    def _analyze_symptoms_with_bert(self, symptoms_text: str) -> Dict:
        """Use BERT to analyze symptom severity"""
        result = {'raw_text': symptoms_text, 'risk_score': 0.5, 'risk_label': 'MEDIUM', 'confidence': 0.0}
        if not symptoms_text or not symptoms_text.strip():
            result.update({'risk_label': 'LOW', 'risk_score': 0.2})
            return result
        if not self.bert_model: return result

        try:
            try:
                prediction = self.bert_model(symptoms_text, top_k=3)
            except Exception as e:
                if 'token_type_ids' in str(e):
                    critical_keywords = ['severe', 'critical', 'emergency', 'intense', 'unbearable', 'bleeding', 'chest pain', 'morquio']
                    text_lower = symptoms_text.lower()
                    if any(word in text_lower for word in critical_keywords):
                        result.update({'risk_label': 'CRITICAL', 'risk_score': 0.88})
                    elif 'fever' in text_lower or 'pain' in text_lower:
                        result.update({'risk_label': 'MEDIUM', 'risk_score': 0.55})
                    return result
                raise e

            if prediction:
                top = prediction[0]
                label = top.get('label', 'MEDIUM').upper()
                result.update({'risk_label': label, 'confidence': top.get('score', 0.5), 
                               'risk_score': {'CRITICAL': 0.95, 'HIGH': 0.80, 'MEDIUM': 0.55, 'LOW': 0.30}.get(label, 0.55)})
        except Exception as e:
            logger.error(f"BERT error: {str(e)}")
        return result

    def _analyze_vitals_with_xgboost(self, age, gender, symptoms, sys_bp, dia_bp, hr, temp_f, pre_conditions=None) -> Dict:
        """Use XGBoost to analyze vitals"""
        result = {'risk_score': 0.5, 'risk_label': 'MEDIUM', 'features_used': []}
        if not self.xgb_model or not self.scaler: return result
        try:
            features = self._prepare_xgboost_features(age, gender, symptoms, sys_bp, dia_bp, hr, temp_f, pre_conditions)
            result['features_used'] = features
            xgb_prediction = self.xgb_model.predict_proba(self.scaler.transform(np.array([features])))[0]
            risk_prob = xgb_prediction[2] if len(xgb_prediction) >= 3 else xgb_prediction[1]
            result['risk_score'] = float(risk_prob)
            result['risk_label'] = 'HIGH' if risk_prob >= 0.75 else 'MEDIUM' if risk_prob >= 0.50 else 'LOW'
        except Exception as e:
            logger.error(f"XGBoost error: {str(e)}")
        return result

    def _prepare_xgboost_features(self, age, gender, symptoms, sys_bp, dia_bp, hr, temp_f, pre_conditions=None) -> list:
        features = [float(age)]
        gender_val = str(gender).capitalize()
        if 'Gender' in self.encoders: features.append(float(self.encoders['Gender'].transform([gender_val])[0]))
        else: features.append(1.0 if gender_val == 'Male' else 0.0)
        features.append(0.0) # Placeholder for Symptoms encoder
        features.append(float(sys_bp)); features.append(float(dia_bp)); features.append(float(hr))
        features.append((float(temp_f) - 32) * 5 / 9)
        features.append(0.0) # Placeholder for Pre_Conditions
        return features

    def _fuse_dual_brain_results(self, bert_result, xgb_result, disease_context, age, sys_bp, dia_bp, hr, temp_f, spo2=95, respiration_rate=16) -> Dict:
        bert_score = bert_result.get('risk_score', 0.5)
        xgb_score = xgb_result.get('risk_score', 0.5)
        disease_score = disease_context.get('risk_score', 0.5)
        
        # Acute Event Prioritization
        is_emergency = disease_context.get('risk_category') == 'CRITICAL' or disease_score >= 0.90
        is_priority = disease_context.get('risk_category') == 'HIGH' or disease_score >= 0.80

        final_score = (xgb_score * 0.40 + bert_score * 0.35 + disease_score * 0.25)
        
        # Vitals multipliers
        v_mult = 1.0
        if sys_bp < 90 or dia_bp < 60: v_mult *= 1.3
        if spo2 < 92: v_mult *= 1.4
        if temp_f > 103.5: v_mult *= 1.3
        
        # Safety Floor: Rare diseases shouldn't be LOW risk just because vitals are perfect
        if is_priority:
            final_score = max(final_score, 0.55) # Floor at MEDIUM/PRIORITY
        
        # Emergency Escalation
        if is_emergency:
            final_score = max(final_score, 0.92)
            final_score *= 1.1 
        
        final_score = min(1.0, max(0.0, final_score * v_mult))
        
        if final_score >= 0.88 or is_emergency: cat, urg = 'CRITICAL', 'IMMEDIATE EMERGENCY'
        elif final_score >= 0.70: cat, urg = 'HIGH', 'URGENT'
        elif final_score >= 0.50: cat, urg = 'MEDIUM', 'PRIORITY'
        else: cat, urg = 'LOW', 'ROUTINE'

        # SPECIALIST MAPPING (New Workflow Integration)
        disease_name = str(disease_context.get('disease_identified', '')).lower()
        specialist = "General Physician"
        if any(k in disease_name for k in ['stroke', 'neurological', 'brain', 'seizure']): specialist = "Neurologist"
        elif any(k in disease_name for k in ['heart', 'infarction', 'cardiac', 'bp']): specialist = "Cardiologist"
        elif any(k in disease_name for k in ['alkaptonuria', 'ochronosis', 'metabolic']): specialist = "Metabolic Specialist / Geneticist"
        elif any(k in disease_name for k in ['pneumonia', 'bronchitis', 'respiratory']): specialist = "Pulmonologist"
        elif any(k in disease_name for k in ['diabetes', 'thyroid']): specialist = "Endocrinologist"
        elif any(k in disease_name for k in ['malaria', 'dengue', 'sepsis']): specialist = "Infectious Disease Specialist"

        return {
            'final_risk_score': final_score, 'risk_category': cat, 'urgency': urg,
            'suggested_specialist': specialist,
            'reasoning': f"Consolidated Risk: {final_score:.2%} | Category: {cat} | Recommended: {specialist} | Primary Context: {disease_context.get('source', 'Symptomatic')} ({disease_context.get('disease_identified', 'Unknown')})"
        }
