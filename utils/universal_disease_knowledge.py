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
        'morquio syndrome': ('Morquio Syndrome (Mucopolysaccharidosis)', 0.90, 'CRITICAL')
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
    SNOMED_APIS = ["https://browser.ihtsdotools.org/snowstorm/snomed-ct", "https://snowstorm.ihtsdotools.org/snowstorm/snomed-ct"]
    LATEST_BRANCHES = ["MAIN", "SNOMEDCT-US"]

    @staticmethod
    def search_disease(disease_name: str) -> Dict:
        if not disease_name: return {'found': False}
        params = {'term': disease_name, 'activeFilter': 'true', 'limit': 1}
        headers = {'User-Agent': 'SmartTriage/2.5', 'Accept': 'application/json'}
        for server in SNOMEDIntegration.SNOMED_APIS:
            for branch in SNOMEDIntegration.LATEST_BRANCHES:
                try:
                    url = f"{server.rstrip('/')}/browser/{branch}/descriptions"
                    resp = requests.get(url, params=params, headers=headers, timeout=2.5)
                    if resp.status_code == 200:
                        items = resp.json().get('items', [])
                        if items:
                            match = items[0]
                            return {
                                'found': True,
                                'preferred_term': match.get('concept', {}).get('pt', {}).get('term') or match.get('term'),
                                'source': f'SNOMED-CT ({branch})'
                            }
                except: continue
        return {'found': False}

class MedicalDiseaseAPI:
    @staticmethod
    def get_disease_from_web(disease_name: str) -> Dict:
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{disease_name.replace(' ', '_')}"
            resp = requests.get(url, timeout=2.5)
            if resp.status_code == 200:
                return {'source': 'Wikipedia', 'description': resp.json().get('extract', '')}
        except: pass
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
            clean = p.strip()
            if len(clean) > 3 and clean.lower() not in ['none', 'null', 'nan', 'unknown']:
                if clean not in potential_terms: potential_terms.append(clean)
        
        if not potential_terms: potential_terms = ["General Symptoms"]
        logger.info(f"[INFERENCE] Parallel investigation of {len(potential_terms)} terms: {potential_terms}")

        all_findings = []

        def investigate_term(term):
            # Step 0: Priority Manifest
            pri_hit = EmergencyManifest.check(term)
            if pri_hit: return pri_hit

            # Step 1: Local
            local_hit = self.local_db.search_disease(term)
            if local_hit:
                return {
                    'disease_identified': local_hit['disease_name'],
                    'risk_score': 0.80 if local_hit['severity'] == 'HIGH' else 0.55,
                    'risk_category': local_hit['severity'],
                    'description': f"Local Diagnosis: {local_hit['severity']}",
                    'source': 'Local AI', 'term': term
                }

            # Step 2: SNOMED
            if term.lower() not in ['fatigue', 'pain', 'fever', 'cough']:
                snomed = SNOMEDIntegration.search_disease(term)
                if snomed.get('found'):
                    return {
                        'disease_identified': snomed['preferred_term'], 'risk_score': 0.65, 'risk_category': 'MEDIUM',
                        'description': f"Clinical Match via {snomed['source']}",
                        'source': 'SNOMED-CT', 'term': term
                    }

            # Step 3: Web
            web = MedicalDiseaseAPI.get_disease_from_web(term)
            if web:
                return {
                    'disease_identified': term, 'risk_score': 0.60, 'risk_category': 'MEDIUM',
                    'description': 'Description from Wikipedia.',
                    'source': 'Wikipedia', 'term': term
                }
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(investigate_term, t): t for t in potential_terms}
            for f in as_completed(futures):
                res = f.result()
                if res: all_findings.append(res)

        result['all_findings'] = all_findings
        if all_findings:
            all_findings.sort(key=lambda x: x['risk_score'], reverse=True)
            best_hit = all_findings[0]
            result.update({'source_used': best_hit['source'], 'final_risk': best_hit})
            return result

        result.update({'source_used': 'Symptomatic AI', 'final_risk': {'disease_identified': 'General Symptoms', 'risk_score': 0.5, 'risk_category': 'MEDIUM', 'description': 'No clinical match.'}})
        return result
