"""
INTEGRATION: Connecting to Medical Knowledge Sources for UNLIMITED Disease Recognition
v3.7 - 'And' Tokenization + Priority Boosting
"""

import requests
import json
from typing import Dict, List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

logger = logging.getLogger(__name__)

class EmergencyManifest:
    """Zero-Latency Priority Manifest"""
    PRIORITY_MAP = {
        'stroke': ('Cerebrovascular Accident', 0.98, 'CRITICAL'),
        'cerebrovascular accident': ('Cerebrovascular Accident', 0.98, 'CRITICAL'),
        'heart attack': ('Myocardial Infarction', 0.98, 'CRITICAL'),
        'myocardial infarction': ('Myocardial Infarction', 0.98, 'CRITICAL'),
        'alkaptonuria': ('Alkaptonuria (Metabolic Disorder)', 0.85, 'HIGH'),
        'ochronosis': ('Ochronosis (Metabolic Manifestation)', 0.85, 'HIGH'),
        'morquio syndrome': ('Morquio Syndrome (Mucopolysaccharidosis)', 0.90, 'CRITICAL'),
        'pulmonary hypertension': ('Pulmonary Arterial Hypertension', 0.88, 'CRITICAL'),
        'idiopathic pulmonary arterial hypertension': ('IPAH', 0.92, 'CRITICAL'),
        'hypertension': ('Hypertension', 0.65, 'MEDIUM'),
        'heart failure': ('Congestive Heart Failure', 0.90, 'CRITICAL'),
        'pulmonary embolism': ('Pulmonary Embolism', 0.95, 'CRITICAL'),
        'aneurysm': ('Aortic Aneurysm', 0.92, 'CRITICAL'),
        'sepsis': ('Sepsis / Septic Shock', 0.96, 'CRITICAL'),
        'ventricular fibrillation': ('Ventricular Fibrillation', 0.99, 'CRITICAL'),
        'acute aortic dissection': ('Acute Aortic Dissection', 0.99, 'CRITICAL'),
        'myocardial rupture': ('Myocardial Rupture', 0.99, 'CRITICAL'),
        'cholangiocarcinoma': ('Bile Duct Cancer', 0.88, 'CRITICAL'),
        'bile duct cancer': ('Bile Duct Cancer', 0.88, 'CRITICAL'),
        'ecclampsia': ('Pre-eclampsia / Eclampsia', 0.95, 'CRITICAL'), # Maternal Emergency
        'post-partum hemorrhage': ('PPH', 0.96, 'CRITICAL'), # Maternal Emergency
        'pph': ('PPH', 0.96, 'CRITICAL'),
        'active labour': ('Active Labour', 0.75, 'HIGH'),
        'obstructed labour': ('Obstructed Labour', 0.94, 'CRITICAL'),
        'snake bite': ('Snake Venom Poisoning', 0.95, 'CRITICAL'),
        'rabies': ('Rabies Infection', 0.98, 'CRITICAL'),
        'dengue hemorrhagic fever': ('DHF', 0.92, 'CRITICAL')
    }

    @staticmethod
    def check(term: str) -> Optional[Dict]:
        term_l = term.lower().strip()
        for key, (name, score, cat) in EmergencyManifest.PRIORITY_MAP.items():
            if key in term_l:
                return {
                    'disease_identified': name, 'risk_score': score, 'risk_category': cat,
                    'description': f"Priority Clinical Finding: {name} (Manifest)",
                    'source': 'Priority Manifest', 'term': term
                }
        return None

class SNOMEDIntegration:
    @staticmethod
    def search_disease(disease_name: str) -> Dict:
        if not disease_name: return {'found': False}
        try:
            # Replaced broken SNOMED with robust NIH Clinical Tables API
            url = "https://clinicaltables.nlm.nih.gov/api/conditions/v3/search"
            params = {'terms': disease_name, 'maxList': 1}
            resp = requests.get(url, params=params, timeout=2.5)
            if resp.status_code == 200:
                data = resp.json()
                if data[0] > 0 and len(data) >= 4 and len(data[3]) > 0:
                    matched_term = data[3][0][0]
                    return {
                        'found': True,
                        'preferred_term': matched_term,
                        'source': 'NIH Clinical Database'
                    }
        except:
            pass
        return {'found': False}

class MedicalDiseaseAPI:
    @staticmethod
    def get_disease_from_web(disease_name: str) -> Dict:
        try:
            headers = {
                'User-Agent': 'SmartTriageBot/1.0 (https://smarttriage.phc; admin@smarttriage.phc) requests/2.25.1',
                'Accept': 'application/json'
            }
            # 1. Search Wikipedia for closest matching article
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {'action': 'query', 'list': 'search', 'srsearch': disease_name, 'utf8': '', 'format': 'json', 'srlimit': 1}
            search_resp = requests.get(search_url, params=params, headers=headers, timeout=3.0)
            
            if search_resp.status_code == 200:
                search_data = search_resp.json()
                results = search_data.get('query', {}).get('search', [])
                if results:
                    best_title = results[0]['title']
                    
                    # 2. Get Summary for the matched article
                    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{best_title.replace(' ', '_')}"
                    sum_resp = requests.get(summary_url, headers=headers, timeout=3.0)
                    if sum_resp.status_code == 200:
                        data = sum_resp.json()
                        extract = data.get('extract', '')
                        
                        # Extract specialist using keyword heuristics on the summary
                        specialist = "General Physician"
                        text_lower = extract.lower()
                        if any(w in text_lower for w in ['heart', 'cardiac', 'myocardial', 'cardiology', 'arrhythmia']): specialist = "Cardiologist"
                        elif any(w in text_lower for w in ['brain', 'neuro', 'stroke', 'seizure']): specialist = "Neurologist"
                        elif any(w in text_lower for w in ['lung', 'respiratory', 'pulmonary', 'asthma']): specialist = "Pulmonologist"
                        elif any(w in text_lower for w in ['cancer', 'tumor', 'oncology', 'malignant']): specialist = "Oncologist"
                        elif any(w in text_lower for w in ['bone', 'orthopedic', 'fracture', 'joint']): specialist = "Orthopedic Surgeon"
                        elif any(w in text_lower for w in ['skin', 'dermatology', 'rash', 'lesion']): specialist = "Dermatologist"
                        elif any(w in text_lower for w in ['stomach', 'gastric', 'gastro', 'liver', 'bowel']): specialist = "Gastroenterologist"
                        elif any(w in text_lower for w in ['kidney', 'renal', 'nephrology']): specialist = "Nephrologist"
                        elif any(w in text_lower for w in ['pregnancy', 'maternal', 'obgyn', 'obstetrics', 'gynecology']): specialist = "OB/GYN Specialist"
                        elif any(w in text_lower for w in ['eye', 'vision', 'ophthalmology', 'retina']): specialist = "Ophthalmologist"
                        elif any(w in text_lower for w in ['children', 'pediatric', 'infant']): specialist = "Pediatrician"
                        elif any(w in text_lower for w in ['diabetes', 'thyroid', 'endocrine', 'metabolic']): specialist = "Endocrinologist"
                        elif any(w in text_lower for w in ['infection', 'virus', 'bacteria', 'sepsis']): specialist = "Infectious Disease Specialist"
                        elif any(w in text_lower for w in ['blood', 'anemia', 'leukemia']): specialist = "Hematologist"
                        
                        return {
                            'source': 'Wikipedia', 
                            'description': extract,
                            'suggested_specialist': specialist
                        }
        except Exception as e:
            logger.error(f"Wikipedia API error for {disease_name}: {e}")
        return None

class UniversalDiseaseRiskAssessment:
    def __init__(self):
        from utils.disease_database import LocalDiseaseDatabase
        self.local_db = LocalDiseaseDatabase()

    def assess_disease_risk_universal(self, disease_input, symptoms, **kwargs) -> Dict:
        result = {'input': f"{disease_input} | {symptoms}", 'all_findings': [], 'final_risk': None}
        
        # 1. PARSE EVERYTHING (Split by , . and the word "and")
        raw_text = f"{disease_input or ''}, {symptoms or ''}"
        # Tokenize using regex to split by commas, dots, and the word 'and'
        potential_terms = []
        for p in re.split(r'[,.]|\band\b', raw_text, flags=re.IGNORECASE):
            # Clean: Remove parentheses and content inside if dangling, or just strip them
            clean = re.sub(r'\(.*?\)', '', p).strip().strip('()[]{}')
            # Handle cases like "Disease (CTX" where parenthesis is not closed
            clean = clean.replace('(', '').replace(')', '').strip()
            
            if len(clean) > 3 and clean.lower() not in ['none', 'null', 'nan', 'unknown']:
                if clean not in potential_terms: potential_terms.append(clean)
        
        if not potential_terms: potential_terms = ["General Symptoms"]
        logger.info(f"[INFERENCE] Parallel investigation of {len(potential_terms)} terms: {potential_terms}")

        all_findings = []

        for term in potential_terms:
            # Step 0: Priority Manifest
            pri_hit = EmergencyManifest.check(term)
            if pri_hit:
                all_findings.append(pri_hit)

            # Step 1: Local
            local_hit = self.local_db.search_disease(term)
            if local_hit:
                all_findings.append({
                    'disease_identified': local_hit['disease_name'],
                    'risk_score': 0.80 if local_hit['severity'] == 'HIGH' else 0.55,
                    'risk_category': local_hit['severity'],
                    'description': f"Local Diagnosis: {local_hit['severity']}",
                    'source': 'Local AI', 'term': term
                })

            # Step 2: SNOMED
            if term.lower() not in ['fatigue', 'pain', 'fever', 'cough']:
                snomed = SNOMEDIntegration.search_disease(term)
                if snomed.get('found'):
                    snomed_term = snomed['preferred_term'].lower()
                    score, cat = 0.65, 'MEDIUM'
                    
                    # CRITICAL KEYWORDS BOOSTER
                    critical_keywords = ['failure', 'infarction', 'stroke', 'hemorrhage', 'rupture', 'sepsis', 'shock', 'arrest', 'acute', 'ischemia', 'embolism', 'aneurysm', 'ecclampsia', 'poisoning', 'snake']
                    high_keywords = ['cancer', 'carcinoma', 'malignant', 'tumor', 'toxicity', 'metabolic', 'genetic', 'storage', 'fibrosis', 'sclerosis', 'cystic', 'pulmonary', 'leukemia', 'lymphoma', 'myeloma', 'amyotrophic', 'anc', 'pnc', 'maternal', 'pregnancy']
                    
                    if any(w in snomed_term for w in critical_keywords):
                        score, cat = 0.90, 'CRITICAL'
                    elif any(w in snomed_term for w in high_keywords):
                        score, cat = 0.82, 'HIGH'
                        
                    all_findings.append({
                        'disease_identified': snomed['preferred_term'], 'risk_score': score, 'risk_category': cat,
                        'description': f"Clinical Match via {snomed['source']}",
                        'source': 'SNOMED-CT', 'term': term
                    })

            # Step 3: Web
            search_term = term
            if 'snomed' in locals() and snomed.get('found'):
                search_term = snomed['preferred_term']
                
            web = MedicalDiseaseAPI.get_disease_from_web(search_term)
            if web:
                desc = web.get('description', '').lower()
                # Dynamic severity boost based on description
                score, cat = 0.60, 'MEDIUM'
                
                # CRITICAL DESCRIPTOR BOOSTER
                critical_desc = ['fatal', 'emergency', 'life-threatening', 'sudden death', 'critical', 'organ failure', 'severe hemorrhage', 'respiratory failure', 'aortic dissection', 'snake bite', 'poisoning', 'myocardial infarction', 'heart attack']
                high_desc = ['cancer', 'carcinoma', 'malignant', 'tumor', 'metabolic', 'genetic', 'storage', 'fibrosis', 'sclerosis', 'cystic', 'pulmonary', 'leukemia', 'lymphoma', 'myeloma', 'amyotrophic', 'pregnancy risk', 'high risk anc']
                
                if any(w in desc for w in critical_desc):
                    score, cat = 0.92, 'CRITICAL'
                elif any(w in desc for w in high_desc):
                    score, cat = 0.80, 'HIGH'
                    
                all_findings.append({
                    'disease_identified': search_term, 'risk_score': score, 'risk_category': cat,
                    'description': web.get('description', 'Medical knowledge result.')[:150] + "...",
                    'suggested_specialist': web.get('suggested_specialist', 'General Physician'),
                    'source': 'Wikipedia Knowledge', 'term': term
                })

        result['all_findings'] = all_findings
        if all_findings:
            all_findings.sort(key=lambda x: x['risk_score'], reverse=True)
            best_hit = all_findings[0]
            result.update({'source_used': best_hit['source'], 'final_risk': best_hit})
            return result

        result.update({'source_used': 'Symptomatic AI', 'final_risk': {'disease_identified': 'General Symptoms', 'risk_score': 0.5, 'risk_category': 'MEDIUM', 'description': 'No clinical match.'}})
        return result
