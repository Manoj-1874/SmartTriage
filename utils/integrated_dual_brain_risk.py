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

# Real-world PHC Departments for DDHS Reporting (13 Departments)
PHC_DEPARTMENTS = {
    'Medicine': ['fever', 'cough', 'headache', 'body ache', 'vomiting', 'diarrhea', 'infection', 'diabetes', 'hypertension'],
    'Surgery': ['wound', 'fracture', 'injury', 'accident', 'abscess', 'burn', 'swelling', 'appendicitis'],
    'OBGYN': ['pregnancy', 'anc', 'pnc', 'delivery', 'labour', 'menstrual', 'maternal', 'abortion', 'fetal'],
    'Paediatrics': ['child', 'infant', 'baby', 'newborn', 'rbsk', 'immunization', 'growth'],
    'Dental': ['tooth', 'gum', 'mouth', 'dental', 'cavity'],
    'ENT': ['ear', 'nose', 'throat', 'sinus', 'tonsil'],
    'Eye': ['vision', 'eye', 'blindness', 'cataract', 'redness'],
    'TB': ['tuberculosis', 'chronic cough', 'weight loss', 'sputum', 'dots'],
    'Leprosy': ['skin patch', 'numbness', 'leprosy'],
    'Family Planning': ['contraception', 'sterilization', 'copper-t', 'birth control'],
    'Immunization': ['vaccine', 'polio', 'bcg', 'measles', 'dpt'],
    'Lab': ['blood test', 'urine test', 'screening', 'biopsy'],
    'Pharmacy': ['refill', 'medication', 'dispensing']
}


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

        # ===== STEP 5: PHC-SPECIFIC CLASSIFICATION (FOR DDHS REPORTING) =====
        dept = self._classify_phc_department(disease_input, combined_symptoms)
        result['phc_department'] = dept

        # ===== STEP 6: DUAL-BRAIN FUSION & REFERRAL LOGIC =====
        logger.info(f"[DUAL-BRAIN-v3.2-REAL-WORLD] Fusing insights for {dept} department...")
        final_assessment = self._fuse_dual_brain_results(
            bert_result=bert_risk,
            xgb_result=xgb_risk,
            disease_context=primary_disease,
            age=age,
            sys_bp=sys_bp,
            dia_bp=dia_bp,
            hr=hr,
            temp_f=temp_f,
            spo2=spo2,
            respiration_rate=respiration_rate
        )

        # Add Referral Logic based on PHC tiers (Vellode vs Chennimalai)
        referral = self._generate_phc_referral(final_assessment, dept, combined_symptoms)
        final_assessment.update(referral)

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
        
        logger.info(f"[FUSION-COMPLETE] Final Risk: {final_assessment.get('risk_category')} | Dept: {dept} | Referral: {final_assessment.get('referral_target')}")

        return result

    def _classify_phc_department(self, disease_name: str, symptoms: str) -> str:
        """Map the case to one of the 13 official PHC departments for DDHS reporting"""
        text = f"{disease_name} {symptoms}".lower()
        
        # High-priority detection for OBGYN (ANC/PNC)
        if any(k in text for k in ['pregnancy', 'anc', 'pnc', 'delivery', 'maternal', 'abortion']):
            return 'OBGYN'
        
        for dept, keywords in PHC_DEPARTMENTS.items():
            if any(k in text for k in keywords):
                return dept
        
        return 'Medicine' # Default

    def _generate_phc_referral(self, assessment: Dict, dept: str, symptoms: str, available_inventory: Optional[List[str]] = None) -> Dict:
        """
        Generate referral targets based on the 3-tier system from field visit.
        REAL-WORLD LOGIC:
        - Vellode/P.Kas PHC -> mid-level nodes
        - CHC Chennimalai -> Upgraded center
        - GH Erode -> Tertiary
        """
        risk_cat = assessment.get('risk_category')
        text = symptoms.lower()
        
        # 1. Detection of "Social Risk" (Secret Diary cases)
        social_risk = any(k in text for k in ['dropout', 'teenage', 'unmarried', 'safe abortion', 'social stigma'])
        
        # 2. Maternal Health Context (PICME 2.0 / RCH)
        is_maternal = dept == 'OBGYN' or any(k in text for k in ['pregnancy', 'anc', 'pnc', 'rch', 'picme'])
        is_high_risk_mother = is_maternal and (risk_cat in ['HIGH', 'CRITICAL'] or 'eclampsia' in text or 'pph' in text)
        
        target = "Primary Health Centre" # Default
        instruction = "Routine follow-up."

        # 3. Inventory-Aware Override (e.g., if ASV is needed but missing)
        inventory_missing = False
        if 'snake' in text or 'venom' in text:
            if available_inventory and 'ASV' not in available_inventory:
                inventory_missing = True
                logger.warning("[INVENTORY-ALERT] Critical Item ASV missing! Redirecting to CHC/GH.")

        # 4. Triage Logic
        if risk_cat == 'CRITICAL' or is_high_risk_mother or inventory_missing:
            target = "District General Hospital / Medical College"
            instruction = "IMMEDIATE AMBULANCE TRANSFER (108). Notify DDHS instantly."
            if is_high_risk_mother:
                instruction += " [Maternal Emergency: PICME Protocol Triggered]"
            if inventory_missing:
                instruction += " [INVENTORY DEFICIT: PHC lacks critical emergency drugs]"
        elif risk_cat == 'HIGH' or social_risk:
            target = "Upgraded PHC (CHC Chennimalai)"
            instruction = "Refer to Specialist / OT facilities. Track via Referral Handshake."
            if social_risk:
                instruction += " [SOCIAL REFERRAL: Handle with Privacy / Secret Diary Protocol]"
        elif risk_cat == 'LOW' and dept in ['Immunization', 'Family Planning', 'Paediatrics']:
            target = "Sub-Centre (HSC / VHN)"
            instruction = "Refer to Village Health Nurse for community follow-up and field screening."

        return {
            'referral_target': target,
            'referral_instruction': instruction,
            'maternal_risk': is_maternal,
            'is_field_case': 'field' in text or 'vhn' in text,
            'ncd_screening': any(k in text for k in ['sugar', 'bp', 'urination', 'thirst', 'vision'])
        }

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
            if category in disease_name or (category == 'respiratory' and 'pulmonary' in disease_name) or (category == 'cardiovascular' and 'arterial' in disease_name):
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
        try:
            # 1. KEYWORD-BASED SEMANTIC OVERRIDE (Real-world PHC keywords)
            text_lower = symptoms_text.lower()
            critical_keywords = [
                'emergency', 'critical', 'unbearable', 'severe bleeding', 'crushing chest pain', 'chest pain',
                'stroke', 'cardiac arrest', 'failure', 'aortic dissection',
                'active labour', 'ecclampsia', 'post-partum hemorrhage', 'pph' # Added Maternal Emergencies
            ]
            high_keywords = [
                'cancer', 'carcinoma', 'malignant', 'tumor', 'progressive', 'severe', 'chronic', 
                'high risk pregnancy', 'anc complication', 'dropout', 'teenage pregnancy', # Added Rural/Social risks
                'tb', 'leprosy', 'xanthomatosis', 'fibrosis', 'sclerosis', 'cystic',
                'infant', 'baby', 'newborn', 'neonatal', 'child' # Pediatric risks
            ]
            
            # 2. AI MODEL PREDICTION (if available - check for latency)
            if self.bert_model:
                try:
                    prediction = self.bert_model(symptoms_text, top_k=3)
                    if prediction:
                        top = prediction[0]
                        label = top.get('label', 'MEDIUM').upper()
                        
                        # Map HuggingFace generic labels
                        if label == 'LABEL_0': label = 'LOW'
                        elif label == 'LABEL_1': label = 'MEDIUM'
                        elif label == 'LABEL_2': label = 'HIGH'
                        elif label == 'LABEL_3': label = 'CRITICAL'

                        # Map internal labels to risk
                        score = {'CRITICAL': 0.95, 'HIGH': 0.80, 'MEDIUM': 0.55, 'LOW': 0.30}.get(label, 0.55)
                        result.update({'risk_label': label, 'confidence': top.get('score', 0.5), 'risk_score': score})
                except Exception as e:
                    logger.warning(f"BERT AI model failed, falling back to keywords: {e}")

            # 3. APPLY KEYWORD BOOST (Overrides AI if keywords are more severe)
            if any(k in text_lower for k in critical_keywords):
                if result['risk_score'] < 0.90:
                    result.update({'risk_label': 'CRITICAL', 'risk_score': 0.92, 'confidence': 0.99})
            elif any(k in text_lower for k in high_keywords):
                if result['risk_score'] < 0.75:
                    result.update({'risk_label': 'HIGH', 'risk_score': 0.82, 'confidence': 0.95})
                    
        except Exception as e:
            logger.error(f"Semantic analysis error: {str(e)}")
        return result

    def _analyze_vitals_with_xgboost(self, age, gender, symptoms, sys_bp, dia_bp, hr, temp_f, pre_conditions=None) -> Dict:
        """Use XGBoost to analyze vitals"""
        result = {'risk_score': 0.5, 'risk_label': 'MEDIUM', 'features_used': []}
        if not self.xgb_model or not self.scaler: return result
        try:
            features = self._prepare_xgboost_features(age, gender, symptoms, sys_bp, dia_bp, hr, temp_f, pre_conditions)
            result['features_used'] = features
            xgb_prediction = self.xgb_model.predict_proba(self.scaler.transform(np.array([features])))[0]
            
            # Correctly handle 3-class (0: LOW, 1: MEDIUM, 2: HIGH)
            if len(xgb_prediction) >= 3:
                # Weighted risk score: 20% for LOW, 55% for MEDIUM, 85% for HIGH
                risk_prob = (xgb_prediction[0] * 0.20) + (xgb_prediction[1] * 0.55) + (xgb_prediction[2] * 0.85)
                
                # Determine label by taking the max probability class
                max_class = int(np.argmax(xgb_prediction))
                label = 'HIGH' if max_class == 2 else 'MEDIUM' if max_class == 1 else 'LOW'
            else:
                risk_prob = xgb_prediction[1] if len(xgb_prediction) > 1 else 0.5
                label = 'HIGH' if risk_prob >= 0.75 else 'MEDIUM' if risk_prob >= 0.50 else 'LOW'
                
            result['risk_score'] = float(risk_prob)
            result['risk_label'] = label
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
        
        # Acute Event Prioritization (Knowledge or Symptom detection)
        is_emergency = (disease_context.get('risk_category') == 'CRITICAL' or disease_score >= 0.85 or bert_result.get('risk_label') == 'CRITICAL')
        is_priority = (disease_context.get('risk_category') == 'HIGH' or disease_score >= 0.75 or bert_result.get('risk_label') == 'HIGH')

        # DYNAMIC WEIGHTING: If any brain detects a crisis, ignore "normal" vitals
        if is_emergency:
            # Shift weight heavily (60% Knowledge/Symptoms, 20% Vitals, 20% Max of any brain)
            final_score = (max(disease_score, bert_score) * 0.70 + xgb_score * 0.30)
        elif is_priority:
            # Shift weight moderately
            final_score = (max(disease_score, bert_score) * 0.60 + xgb_score * 0.40)
        else:
            # Standard fusion
            final_score = (xgb_score * 0.40 + bert_score * 0.35 + disease_score * 0.25)
        
        # Vitals multipliers (Physical instability ALWAYS boosts risk)
        v_mult = 1.0
        if sys_bp < 90 or sys_bp > 180 or dia_bp < 60 or dia_bp > 110: v_mult *= 1.3
        if spo2 < 92: v_mult *= 1.4
        elif spo2 < 95: v_mult *= 1.2
        if temp_f > 103.5 or temp_f < 95.0: v_mult *= 1.3
        if hr > 120 or hr < 50: v_mult *= 1.3
        if respiration_rate > 24 or respiration_rate < 10: v_mult *= 1.3
        
        # Safety Floor: If Knowledge OR Symptoms detect a crisis, result MUST NOT be LOW
        if is_emergency:
            final_score = max(final_score, 0.90)
        elif is_priority:
            final_score = max(final_score, 0.70) # Floor at HIGH
        
        final_score = min(1.0, max(0.0, final_score * v_mult))
        
        if final_score >= 0.85 or is_emergency: cat, urg = 'CRITICAL', 'IMMEDIATE EMERGENCY'
        elif final_score >= 0.70: cat, urg = 'HIGH', 'URGENT'
        elif final_score >= 0.50: cat, urg = 'MEDIUM', 'PRIORITY'
        else: cat, urg = 'LOW', 'ROUTINE'

        # SPECIALIST MAPPING
        disease_name = str(disease_context.get('disease_identified', '')).lower()
        specialist = disease_context.get('suggested_specialist')
        if not specialist or specialist == "General Physician":
            specialist = "General Physician"
            if any(k in disease_name for k in ['stroke', 'neurological', 'brain', 'seizure']): specialist = "Neurologist"
            elif any(k in disease_name for k in ['pulmonary', 'respiratory', 'lung', 'bronchitis', 'asthma']): specialist = "Pulmonologist"
            elif any(k in disease_name for k in ['heart', 'infarction', 'cardiac', 'hypertension', 'bp']): specialist = "Cardiologist"
            elif any(k in disease_name for k in ['alkaptonuria', 'ochronosis', 'metabolic']): specialist = "Endocrinologist"
            elif any(k in disease_name for k in ['diabetes', 'thyroid']): specialist = "Endocrinologist"
            elif any(k in disease_name for k in ['malaria', 'dengue', 'sepsis']): specialist = "Infectious Disease Specialist"
            elif any(k in disease_name for k in ['cancer', 'tumor', 'oncology']): specialist = "Oncologist"
            elif any(k in disease_name for k in ['pregnancy', 'maternal', 'obgyn']): specialist = "OB/GYN Specialist"

        return {
            'final_risk_score': final_score, 'risk_category': cat, 'urgency': urg,
            'suggested_specialist': specialist,
            'reasoning': f"Consolidated Risk: {final_score:.2%} | Category: {cat} | Recommended: {specialist} | Primary Context: {disease_context.get('source', 'Symptomatic')} ({disease_context.get('disease_identified', 'Unknown')})"
        }
