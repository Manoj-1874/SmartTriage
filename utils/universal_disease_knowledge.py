"""
INTEGRATION: Connecting to Medical Knowledge Sources for UNLIMITED Disease Recognition

You can't hardcode millions of diseases, but you CAN query medical APIs/databases.
This shows how to expand from local database to WORLD medical knowledge.
"""

import requests
import json
from typing import Dict, List, Optional
import logging
import time

logger = logging.getLogger(__name__)


# ===================================================================
# SNOMED-CT Integration - Medical Terminology (Knows ALL diseases)
# ===================================================================

class SNOMEDIntegration:
    """
    SNOMED-CT (Systematized Nomenclature of Medicine Clinical Terms)
    • 400K+ medical concepts
    • Covers ALL diseases, symptoms, procedures
    • Relationships between concepts (is-a, part-of, etc.)

    Example: Query "Ehlers-Danlos" → Get ICD code, symptoms, complications
    """

    # Official SNOMED International Browser API (Ground Truth)
    SNOMED_APIS = [
        "https://browser.ihtsdotools.org/snowstorm/snomed-ct",
        "https://snowstorm.ihtsdotools.org/snowstorm/snomed-ct"
    ]
    
    # Latest verified branch as of April 2026
    # Note: Snowstorm often requires specific versioned branches (e.g. MAIN/2026-04-01)
    LATEST_BRANCHES = ["MAIN", "SNOMEDCT-US", "MAIN/2026-04-01"]

    # Disease aliases mapping - normalize user input to standard names
    DISEASE_ALIASES = {
        'heart attack': 'Myocardial Infarction',
        'mi': 'Myocardial Infarction',
        'stroke': 'Cerebrovascular Accident',
        'cva': 'Cerebrovascular Accident',
        'diabetes': 'Diabetes Mellitus',
        'high sugar': 'Diabetes Mellitus',
        'flu': 'Influenza',
        'chest infection': 'Pneumonia',
        'lung infection': 'Pneumonia',
        'hypertension': 'Hypertension',
        'high bp': 'Hypertension',
        'high blood pressure': 'Hypertension',
        'cancer': 'Malignant Neoplasm',
        'cholangiocarcinoma': 'Cholangiocarcinoma',
        'bile duct cancer': 'Cholangiocarcinoma',
    }

    @staticmethod
    def search_disease(disease_name: str, max_retries: int = 2) -> Dict:
        """Search SNOMED-CT for disease information with official browser-native descriptions"""
        normalized_name = SNOMEDIntegration._normalize_disease_name(disease_name)

        if not normalized_name or normalized_name.lower() in ['none', 'null', 'nan']:
            return {'found': False, 'reason': 'Empty query'}

        # Use official description matching for high fidelity
        params = {
            'term': normalized_name,
            'active': 'true',
            'conceptActive': 'true',
            'limit': 5,
            'lang': 'en',
            'searchMode': 'PARTIAL_MATCHING'
        }

        headers = {
            'User-Agent': 'SmartTriage-AI-Dashboard/2.0 (Clinical-Research)',
            'Accept': 'application/json'
        }

        # FAST-FAIL CASCADE: Attempt only the most reliable endpoints with ultra-short timeouts
        # SNOMED International Browser API is often slow; we fail fast to hit MeSH/Wiki instead
        for server_url in SNOMEDIntegration.SNOMED_APIS:
            for branch in SNOMEDIntegration.LATEST_BRANCHES:
                try:
                    search_url = f"{server_url.rstrip('/')}/browser/{branch}/descriptions"
                    # Ultra-fast timeout: 2.5s is enough for a medical terminology hit
                    response = requests.get(search_url, params=params, headers=headers, timeout=2.5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        items = data.get('items', [])
                        if items:
                            match = items[0]
                            concept = match.get('concept', {})
                            logger.info(f"✅ [SNOMED-HIT] Found '{normalized_name}' on {branch}")
                            return {
                                'found': True,
                                'snomed_id': concept.get('conceptId'),
                                'disease_name': normalized_name,
                                'preferred_term': concept.get('pt', {}).get('term') or match.get('term'),
                                'server': f'SNOMED-CT ({branch})'
                            }
                        elif response.status_code == 410:
                            logger.warning(f"⚠️ [SNOMED-DEPRECATED] Branch {branch} is no longer active.")
                except: 
                    continue # Move to next branch/server immediately

        return {'found': False}

    @staticmethod
    def _normalize_disease_name(disease_name: str) -> str:
        """Normalize disease name using aliases"""
        if not disease_name:
            return ""
        disease_lower = disease_name.lower().strip()

        # Check if direct alias exists
        if disease_lower in SNOMEDIntegration.DISEASE_ALIASES:
            return SNOMEDIntegration.DISEASE_ALIASES[disease_lower]
        
        return disease_name


# ===================================================================
# Mayo Clinic / Medical API Integration
# ===================================================================

class MedicalDiseaseAPI:
    """
    Query medical databases for disease characteristics
    """

    @staticmethod
    def get_disease_from_web(disease_name: str) -> Dict:
        """
        Attempt to get disease info from multiple medical sources
        Cascade through: SNOMED → Wikipedia (medical) → MeSH/Wikidata
        """
        if not disease_name:
            return None

        # Try 1: Wikipedia (medical content)
        logger.info(f"🌐 [WIKI] Attempting Wikipedia search for medical context: '{disease_name}'")
        wiki_result = MedicalDiseaseAPI._search_wikipedia_medical(disease_name)
        if wiki_result:
            return {
                'source': 'Wikipedia (Medical)',
                'disease_name': disease_name,
                'description': wiki_result.get('description'),
                'confidence': 0.70,
            }

        # Try 2: Comprehensive Medical Research (MeSH, Wikidata, etc.)
        from utils.medical_database_apis import MedicalDatabaseAPIs
        comprehensive_result = MedicalDatabaseAPIs.search_disease_comprehensive(disease_name)
        
        if comprehensive_result.get('found'):
            sources = comprehensive_result.get('sources', {})
            source_key = 'mesh' if 'mesh' in sources else 'wikidata' if 'wikidata' in sources else 'wikipedia'
            source_data = sources.get(source_key)
            
            return {
                'source': f'Medical Research ({source_key.upper()})',
                'disease_name': disease_name,
                'description': source_data.get('definition') or source_data.get('snippet') or source_data.get('description'),
                'confidence': 0.85 if source_key == 'mesh' else 0.65,
            }

        return None

    @staticmethod
    def _search_wikipedia_medical(query: str) -> Optional[Dict]:
        """Search Wikipedia for medical definitions"""
        try:
            import wikipedia
            # Add 'disease' or 'medical' to query to improve accuracy
            search_query = f"{query} disease"
            page = wikipedia.page(search_query, auto_suggest=True)
            return {
                'title': page.title,
                'description': page.summary[:1000],
                'url': page.url
            }
        except:
            return None


# ===================================================================
# Universal Disease Risk Assessment
# ===================================================================

class UniversalDiseaseRiskAssessment:
    """
    Main engine for disease recognition and risk scoring
    """

    def __init__(self):
        from utils.disease_database import LocalDiseaseDatabase
        self.local_db = LocalDiseaseDatabase()

    def assess_disease_risk_universal(
        self,
        disease_input: str,
        symptoms: str,
        age: int,
        gender: str,
        sys_bp: int,
        dia_bp: int,
        hr: int,
        temp_f: float,
        comorbidities: List[str] = None
    ) -> Dict:
        """
        Universal assessment: Local DB → SNOMED → Web → Semantic Fallback
        """
        result = {
            'input': disease_input,
            'sources_checked': [],
            'source_used': None,
            'final_risk': None
        }

        # 1. Identify ALL Potential Disease Terms from Symptoms and Input
        potential_terms = []
        if disease_input and disease_input.lower() not in ['none', 'null', 'nan', 'unknown']:
            potential_terms.append(disease_input.strip())
        
        if symptoms:
            import re
            # Split by BOTH commas and dots to handle "Fatigue, Aches. Morquio Syndrome"
            parts = [p.strip() for p in re.split(r'[,.]', symptoms)]
            for p in parts:
                if len(p) > 3:
                    clean_p = p.split('(')[0].strip() if '(' in p else p
                    if clean_p and clean_p not in potential_terms:
                        potential_terms.append(clean_p)

        if not potential_terms:
            potential_terms = ["General Symptoms"]

        logger.info(f"🔎 [INFERENCE] Investigative cascade for terms: {potential_terms}")

        # 2. SEARCH CASCADE - STAGE 1: Authoritative Global Terminology (SNOMED-CT)
        # We check ALL terms for SNOMED first, as it is the most reliable for specific diseases.
        for term in potential_terms:
            # Skip generic symptom-only searches on SNOMED to save time/bandwidth
            if term.lower() in ['fatigue', 'pain', 'fever', 'cough', 'nausea', 'aches', 'body aches']:
                continue
                
            snomed_info = SNOMEDIntegration.search_disease(term)
            if snomed_info.get('found'):
                logger.info(f"🏥 [SNOMED-HIT] Definitive clinical match for '{term}'")
                result['sources_checked'].append(f'SNOMED-CT ({term})')
                
                # Priority: Rare syndromes/diseases
                is_rare = any(x in term.lower() for x in ['syndrome', 'disease', 'infarction', 'type'])
                risk_profile = {
                    'disease_identified': snomed_info['preferred_term'],
                    'risk_score': 0.85 if is_rare else 0.65,
                    'risk_category': 'HIGH' if is_rare else 'MEDIUM',
                    'description': f"Authoritative Clinical Term: {snomed_info['preferred_term']} (Verified via SNOMED-CT {snomed_info['server']})"
                }
                result['source_used'] = 'SNOMED-CT'
                result['final_risk'] = risk_profile
                return result # Found the most specific medical hit, stop.

        # 3. SEARCH CASCADE - STAGE 2: Local AI Database (Fast Clinical Matching)
        best_local_hit = None
        for term in potential_terms:
            local_db_match = self.local_db.search_disease(term)
            if local_db_match:
                logger.info(f"⚡ [LOCAL-HIT] Found '{term}' in local knowledge base")
                result['sources_checked'].append(f'Local DB ({term})')
                
                current_risk = {
                    'disease_identified': local_db_match['disease_name'],
                    'risk_score': 0.95 if local_db_match['severity'] == 'CRITICAL' else 0.80 if local_db_match['severity'] == 'HIGH' else 0.55 if local_db_match['severity'] == 'MEDIUM' else 0.30,
                    'risk_category': local_db_match['severity'],
                    'description': f"Clinical Category: {local_db_match['severity']} (Source: Local AI Knowledge Base)"
                }
                
                # Keep the highest severity hit found across all symptoms
                if not best_local_hit or current_risk['risk_score'] > best_local_hit['risk_score']:
                    best_local_hit = current_risk
                    result['source_used'] = 'Local AI (Known Disease)'

        if best_local_hit:
            result['final_risk'] = best_local_hit
            return result

        # 4. SEARCH CASCADE - STAGE 3: Medical Web Enrichment (Wikipedia/Wikidata)
        for term in potential_terms:
            if term.lower() in ['fatigue', 'pain', 'fever', 'cough', 'nausea']: continue
            
            web_info = MedicalDiseaseAPI.get_disease_from_web(term)
            if web_info:
                logger.info(f"📚 [WEB-HIT] Retrieved enrichment data from {web_info.get('source')} for '{term}'")
                result['sources_checked'].append(f"{web_info.get('source')} ({term})")
                
                result['final_risk'] = {
                    'disease_identified': term,
                    'risk_score': 0.60,
                    'risk_category': 'MEDIUM',
                    'description': f"Extracted from {web_info.get('source')}: {web_info.get('description')[:300]}..."
                }
                result['source_used'] = web_info.get('source')
                return result

        # 5. ULTIMATE FALLBACK: Pure Symptomatic Triage
        logger.warning(f"⚠️ [FALLBACK] No specific disease identified for terms: {potential_terms}")
        result['source_used'] = 'Symptomatic AI Triage'
        result['final_risk'] = {
            'disease_identified': 'General Syndrome',
            'risk_score': 0.50,
            'risk_category': 'MEDIUM',
            'description': 'Assessment based on symptomatic presentation and vital signs only.'
        }
        return result
