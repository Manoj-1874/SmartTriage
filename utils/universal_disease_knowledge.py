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
    LATEST_BRANCH = "MAIN/2026-04-01"

    # Disease aliases mapping - normalize user input to standard names
    DISEASE_ALIASES = {
        'cad': 'Coronary Artery Disease',
        'heart disease': 'Coronary Artery Disease',
        'coronary disease': 'Coronary Artery Disease',
        'angina': 'Coronary Artery Disease',
        'heart attack': 'Acute Myocardial Infarction',
        'ami': 'Acute Myocardial Infarction',
        'mi': 'Acute Myocardial Infarction',
        'stroke': 'Acute Stroke',
        'cva': 'Acute Stroke',
        'brain stroke': 'Acute Stroke',
        'pe': 'Pulmonary Embolism',
        'blood clot': 'Pulmonary Embolism',
        'ki': 'Acute Kidney Injury',
        'aki': 'Acute Kidney Injury',
        'kidney failure': 'Acute Kidney Injury',
        'copd': 'Chronic Obstructive Pulmonary Disease',
        'emphysema': 'Chronic Obstructive Pulmonary Disease',
        'pneumonia': 'Pneumonia',
        'lung infection': 'Pneumonia',
        'hypertension': 'Hypertension',
        'high bp': 'Hypertension',
        'high blood pressure': 'Hypertension',
        'cancer': 'Malignant Neoplasm',
        'cholangiocarcinoma': 'Cholangiocarcinoma',
        'bile duct cancer': 'Cholangiocarcinoma',
    }
    @staticmethod
    def search_disease(disease_name: str, version: str = "MAIN", max_retries: int = 3) -> Dict:
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
            # We check MAIN first, then the specific US branch which is often more stable
            for branch in ["MAIN", "SNOMEDCT-US", "MAIN/2026-04-01"]:
                try:
                    # UPDATED: Correct Snowstorm path for public browser instances
                    # We try both 'browser' (Snowstorm UI) and native endpoints
                    search_url = f"{server_url.rstrip('/')}/browser/{branch}/descriptions"
                    
                    logger.info(f"🔍 [SNOMED-TRY] URL: {search_url} | Term: {params['term']}")
                    # Ultra-fast timeout: 3s is enough for a medical terminology hit
                    response = requests.get(search_url, params=params, headers=headers, timeout=3)
                    
                    if response.status_code == 200:
                        data = response.json()
                        items = data.get('items', [])
                        if items:
                            # Extract concept from description hit
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
                except: 
                    continue # Move to next branch/server immediately
        
        return {'found': False, 'reason': 'Not found in official SNOMED channels'}

    @staticmethod
    def _normalize_disease_name(disease_name: str) -> str:
        """Normalize disease name using aliases - convert user input to standard names"""
        if not disease_name:
            return ""
        disease_lower = disease_name.lower().strip()

        # [STRICT] If the input contains multiple symptoms or is very long, 
        # do NOT attempt alias normalization as it leads to hallucinations (e.g. "mi" in "abdominal").
        if len(disease_lower) > 25 or ',' in disease_name or '.' in disease_name:
            return disease_name

        # Check if direct alias exists (High Precision)
        if disease_lower in SNOMEDIntegration.DISEASE_ALIASES:
            normalized = SNOMEDIntegration.DISEASE_ALIASES[disease_lower]
            logger.info(f"[ALIAS-EXACT] '{disease_name}' → '{normalized}'")
            return normalized

        # Check for partial matches ONLY for extremely short, likely acronym inputs
        if len(disease_lower) <= 5:
            for alias_key, standard_name in SNOMEDIntegration.DISEASE_ALIASES.items():
                if alias_key == disease_lower:
                    logger.info(f"[ALIAS-MATCH] '{disease_name}' → '{standard_name}'")
                    return standard_name

        # No precise alias found, use original name to avoid incorrect mapping
        return disease_name

    @staticmethod
    def _get_parent_concepts(concept_id: str, version: str, snomed_api: str) -> List[str]:
        """Get what disease category this disease belongs to"""
        # Example: Ehlers-Danlos → Parents: "Hereditary disorder", "Connective tissue disease"
        try:
            url = f"{snomed_api}/{version}/concepts/{concept_id}/parents"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                return [item.get('pt', {}).get('term') for item in data.get('items', [])]
            return []
        except Exception as e:
            logger.debug(f"[SNOMED-PARENT] Failed to get parent concepts: {str(e)}")
            return []

    @staticmethod
    def _get_related_symptoms(concept_id: str, version: str, snomed_api: str) -> List[str]:
        """Get symptoms associated with this disease"""
        try:
            url = f"{snomed_api}/{version}/concepts/{concept_id}"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                # Extract relationships (is_a, has_symptom, presents_with, etc.)
                relationships = data.get('relationships', [])

                symptoms = []
                for rel in relationships:
                    if rel.get('type') in ['has-symptom', 'may-present-with']:
                        symptoms.append(rel.get('target', {}).get('term'))

                return symptoms
            return []
        except Exception as e:
            logger.debug(f"[SNOMED-SYMPTOMS] Failed to get related symptoms: {str(e)}")
            return []

    @staticmethod
    def _map_to_icd10(snomed_id: str) -> Optional[str]:
        """Map SNOMED ID to ICD-10 code for standardization"""
        # In production, use SNOMED-ICD10 mapping service
        # For now, return None (would need professional mapping service)
        return None


# ===================================================================
# Mayo Clinic / Medical API Integration
# ===================================================================

class MedicalDiseaseAPI:
    """
    Query medical databases for disease characteristics
    When you don't have a disease in your local DB, query external sources
    """

    @staticmethod
    def get_disease_from_web(disease_name: str) -> Dict:
        """
        Attempt to get disease info from multiple medical sources
        Cascade through: SNOMED → Wikipedia (medical) → General search
        """
        if not disease_name:
            return None

        # Try 1: SNOMED-CT
        snomed_result = SNOMEDIntegration.search_disease(disease_name)
        if snomed_result.get('found'):
            return {
                'source': 'SNOMED-CT',
                'disease_name': snomed_result.get('preferred_term'),
                'parent_categories': snomed_result.get('parent_concepts'),
                'symptoms': snomed_result.get('related_symptoms'),
                'icd_code': snomed_result.get('icd_code'),
                'confidence': 0.95,  # SNOMED is authoritative
            }

        # Try 2: Wikipedia (medical content)
        logger.info(f"🌐 [WIKI] Attempting Wikipedia search for medical context: '{disease_name}'")
        wiki_result = MedicalDiseaseAPI._search_wikipedia_medical(disease_name)
        if wiki_result:
            logger.info(f"✅ [WIKI-SUCCESS] Found Wikipedia article: {wiki_result.get('url')}")
            return {
                'source': 'Wikipedia (Medical)',
                'disease_name': disease_name,
                'description': wiki_result.get('description'),
                'confidence': 0.70,
            }

        # Try 3: Comprehensive Medical Research (MeSH, Wikidata, etc.)
        from utils.medical_database_apis import MedicalDatabaseAPIs
        comprehensive_result = MedicalDatabaseAPIs.search_disease_comprehensive(disease_name)
        
        if comprehensive_result.get('found'):
            # Pick best available source from comprehensive results
            sources = comprehensive_result.get('sources', {})
            source_key = 'mesh' if 'mesh' in sources else 'wikidata' if 'wikidata' in sources else 'wikipedia'
            source_data = sources.get(source_key)
            
            logger.info(f"✅ [COMPREHENSIVE-HIT] Found data via {source_key.upper()}")
            return {
                'source': f'Medical Research ({source_key.upper()})',
                'disease_name': disease_name,
                'description': source_data.get('definition') or source_data.get('snippet') or source_data.get('description'),
                'confidence': 0.85 if source_key == 'mesh' else 0.65,
            }

        logger.warning(f"⚠️ [WEB-SEARCH-FAILED] No medical info found for '{disease_name}'")
        return None

    @staticmethod
    def _search_wikipedia_medical(disease_name: str) -> Optional[Dict]:
        """Search Wikipedia for disease information"""
        try:
            import wikipedia

            # Strict medical filtering: Append "medical condition" and verify result contains the term
            results = wikipedia.search(disease_name + " disease", results=3)
            for title in results:
                # Basic validation: the result should be medically related
                if any(kw in title.lower() for kw in disease_name.lower().split()):
                    page = wikipedia.page(title)
                    summary = page.summary
                    # Only accept if the summary actually mentions a disease/condition
                    if any(kw in summary.lower() for kw in ['disease', 'syndrome', 'condition', 'infection', 'disorder']):
                        return {
                            'description': summary[:500],
                            'url': page.url,
                            'title': title
                        }
        except:
            pass
        return None


# ===================================================================
# INTEGRATED DISEASE RISK SYSTEM - With External Knowledge
# ===================================================================

class UniversalDiseaseRiskAssessment:
    """
    Risk assessment that:
    1. Checks local disease database
    2. If not found, queries SNOMED-CT
    3. If not found, attempts semantic analysis
    4. Handles ANY disease in the world
    """

    def __init__(self):
        from utils.medical_ai_knowledge_system import MedicalAIRiskAssessment
        self.local_ai = MedicalAIRiskAssessment()

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
        comorbidities: List[str] = None,
    ) -> Dict:
        """
        Universal disease risk assessment using multiple knowledge sources
        """
        # Normalize disease_input - handle "None" string or null
        if not disease_input or str(disease_input).lower() in ['none', 'null', 'nan']:
            disease_input = None

        logger.info(f"🚀 [START] Assessing universal risk for input: '{disease_input}' | Symptoms: '{symptoms[:50]}...'")

        result = {
            'disease_input': disease_input,
            'sources_checked': [],
            'final_risk': None,
        }

        # ===== SOURCE 1: Local AI Database =====
        # Use symptoms for identification if disease_input is missing
        local_search_term = disease_input if disease_input else symptoms

        local_result = self.local_ai.assess_patient_disease_risk(
            disease_name_or_symptoms=local_search_term,
            age=age,
            gender=gender,
            sys_bp=sys_bp,
            dia_bp=dia_bp,
            hr=hr,
            temp_f=temp_f,
            comorbidities=comorbidities,
        )
        result['final_risk'] = local_result
        result['sources_checked'].append('Local AI Database')

        # [SMART INFERENCE] If no disease name provided, analyze all symptoms
        global_search_term = disease_input
        if not global_search_term:
            # 1. Priority: Extract known disease names from the local database
            all_known_diseases = self.local_ai.get_all_disease_names()
            for disease_name in all_known_diseases:
                if len(disease_name) > 4 and disease_name.lower() in symptoms.lower():
                    global_search_term = disease_name
                    logger.info(f"🔎 [INFERENCE-MATCH] Extracted known disease from symptoms: '{global_search_term}'")
                    break

            # 2. Secondary: Extract text BEFORE parentheses (Usually the primary disease name)
            # Example: "Hurthle Cell Carcinoma (Oncocytic Carcinoma)" -> "Hurthle Cell Carcinoma"
            if not global_search_term and '(' in symptoms and ')' in symptoms:
                import re
                # Find text before parentheses, potentially after a period or at start
                match_complex = re.search(r'(?:^|\.\s*)([A-Z][a-zA-Z\s\-]{5,})\s*\(', symptoms)
                if match_complex:
                    global_search_term = match_complex.group(1).strip()
                    logger.info(f"🔎 [INFERENCE-PREFIX] Extracted primary disease before parentheses: '{global_search_term}'")
                else:
                    # Fallback to parentheses content if prefix extraction fails
                    matches = re.findall(r'\((.*?)\)', symptoms)
                    if matches:
                        potential_disease = matches[-1].strip()
                        if len(potential_disease) > 3:
                            global_search_term = potential_disease
                            logger.info(f"🔎 [INFERENCE-PAREN] Extracted disease from parentheses: '{global_search_term}'")

            # 3. Tertiary: Text after last period (Common way nurses append diagnosis)
            if not global_search_term and '.' in symptoms:
                last_phrase = symptoms.split('.')[-1].strip()
                if len(last_phrase) > 5 and len(last_phrase.split()) <= 4:
                    global_search_term = last_phrase
                    logger.info(f"🔎 [INFERENCE-SUFFIX] Extracted potential disease from suffix: '{global_search_term}'")

            # 4. Quaternary: Use BERT's best semantic match
            if not global_search_term and local_result.get('best_match'):
                global_search_term = local_result['best_match']['name']
                logger.info(f"🔎 [INFERENCE-BERT] Best semantic match for symptom set: '{global_search_term}'")
            
            # 5. ULTIMATE FALLBACK: Use ALL symptoms (last resort)
            if not global_search_term:
                if symptoms and len(symptoms) > 3:
                    global_search_term = str(symptoms)[:100].split('.')[0].replace(',', ' ').strip()
                    logger.info(f"🔎 [FALLBACK-SEARCH] Using cleaned symptoms for global search: '{global_search_term}'")
                else:
                    logger.info("ℹ️ [FALLBACK] No disease or symptom identified for global search.")
                    return result
                    
        # [CRITICAL] Sanitize search term: Strip quotes and accidental symbols that break API lookups
        if global_search_term:
            global_search_term = global_search_term.strip("'\"` .")

        # ===== SOURCE 2: SNOMED-CT (Terminology Brain) =====
        snomed_info = SNOMEDIntegration.search_disease(global_search_term)

        if local_result.get('is_known_disease'):
            logger.info(f"⚡ [LOCAL-HIT] '{global_search_term}' found in Local AI Database")
            result['sources_checked'].append('Local Database')
            result['source_used'] = 'Local AI (Known Disease)'
            result['final_risk'] = local_result
            return result

        logger.info(f"🔍 [LOCAL-MISS] '{global_search_term}' not in local DB. Escalating to global sources...")

        if snomed_info.get('found'):
            logger.info(f"🏥 [SNOMED-HIT] Found authoritative medical data for '{global_search_term}'")
            result['sources_checked'].append('SNOMED-CT')
            result['snomed_mapping'] = snomed_info

            # Create risk profile from SNOMED info
            risk_from_snomed = self._calculate_risk_from_snomed(
                snomed_info, age, sys_bp, dia_bp, hr, temp_f, comorbidities
            )

            result['source_used'] = 'SNOMED-CT (Mapped to Local Risk Model)'
            result['final_risk'] = risk_from_snomed
            return result

        # ===== SOURCE 3: Medical API / Wikipedia =====
        # Use inferred name for external web search
        medical_info = MedicalDiseaseAPI.get_disease_from_web(global_search_term)

        if medical_info:
            logger.info(f"📚 [WEB-HIT] Retrieved enrichment data from '{medical_info.get('source')}'")
            result['sources_checked'].append('Medical APIs')
            result['external_info'] = medical_info

            # Create risk profile from external info
            risk_from_external = self._calculate_risk_from_external(
                medical_info, age, sys_bp, dia_bp, hr, temp_f, comorbidities
            )

            result['source_used'] = 'External Medical Sources'
            result['final_risk'] = risk_from_external
            return result

        # ===== FALLBACK: Pure Semantic Analysis =====
        result['sources_checked'].append('Semantic Analysis (Fallback)')
        result['source_used'] = 'Pure Semantic Analysis (Unknown Disease)'

        fallback_risk = {
            'disease_identified': disease_input or 'General Symptom Assessment',
            'is_known_disease': False,
            'risk_category': 'MEDIUM',  # Conservative estimate for unknown
            'recommendation': 'Consult with specialist for accurate diagnosis',
            'reasoning': f"""
Unknown disease not found in medical databases.
Recommend specialist evaluation for proper diagnosis.
            """
        }

        result['final_risk'] = fallback_risk
        return result

    def _calculate_risk_from_snomed(self, snomed_info: Dict, age: int, sys_bp: int,
                                    dia_bp: int, hr: int, temp_f: float,
                                    comorbidities: List[str]) -> Dict:
        """Convert SNOMED info to risk calculation"""

        # Map parent concepts to severity levels
        parent_concepts = snomed_info.get('parent_concepts', [])

        base_risk = 0.50  # Default for unknown

        # Check parent concepts for severity
        for parent in parent_concepts:
            # Ensure parent is a string and handle None
            parent_str = str(parent or "").lower()
            if any(word in parent_str for word in ['critical', 'emergency', 'acute severe']):
                base_risk = 0.80
                break
            elif any(word in parent_str for word in ['chronic', 'genetic', 'hereditary']):
                base_risk = 0.55

        # Apply vital signs
        vital_risk = self._assess_vitals(sys_bp, dia_bp, hr, temp_f)

        # Apply age
        age_risk = self._assess_age(age)

        final_risk = base_risk * vital_risk * age_risk

        return {
            'disease_identified': snomed_info.get('preferred_term') or snomed_info.get('disease_name') or 'SNOMED Match',
            'source': 'SNOMED-CT',
            'risk_score': min(1.0, final_risk),
            'risk_category': self._risk_to_category(final_risk),
            'symptoms_from_snomed': snomed_info.get('related_symptoms', []),
            'icd_code': snomed_info.get('icd_code'),
        }

    def _calculate_risk_from_external(self, medical_info: Dict, age: int, sys_bp: int,
                                      dia_bp: int, hr: int, temp_f: float,
                                      comorbidities: List[str]) -> Dict:
        """Convert external medical API info to risk calculation"""

        # Similar to SNOMED but less detailed
        base_risk = 0.50

        description = str(medical_info.get('description', '') or "").lower()

        # Extract severity keywords from description
        if any(word in description for word in ['critical', 'fatal', 'lethal', 'severe']):
            base_risk = 0.75
        elif any(word in description for word in ['serious', 'significant', 'urgent']):
            base_risk = 0.60
        elif any(word in description for word in ['chronic', 'long-term', 'progressive']):
            base_risk = 0.55

        vital_risk = self._assess_vitals(sys_bp, dia_bp, hr, temp_f)
        age_risk = self._assess_age(age)

        final_risk = base_risk * vital_risk * age_risk

        return {
            'disease_identified': medical_info.get('disease_name') or medical_info.get('title') or 'External Match',
            'source': medical_info.get('source'),
            'risk_score': min(1.0, final_risk),
            'risk_category': self._risk_to_category(final_risk),
            'description': medical_info.get('description'),
            'confidence': medical_info.get('confidence', 0.50),
        }

    @staticmethod
    def _assess_vitals(sys_bp: int, dia_bp: int, hr: int, temp_f: float) -> float:
        """Quick vital signs assessment"""
        multiplier = 1.0

        if temp_f > 103 or temp_f < 94:
            multiplier *= 1.3
        if sys_bp > 180 or sys_bp < 80:
            multiplier *= 1.3
        if hr > 130 or hr < 40:
            multiplier *= 1.2

        return min(2.0, multiplier)

    @staticmethod
    def _assess_age(age: int) -> float:
        """Age risk adjustment"""
        if age > 75:
            return 1.3
        elif age > 65:
            return 1.2
        elif age < 5:
            return 1.2
        return 1.0

    @staticmethod
    def _risk_to_category(risk_score: float) -> str:
        """Convert risk score to category"""
        if risk_score >= 0.80:
            return 'HIGH'
        elif risk_score >= 0.60:
            return 'MEDIUM'
        else:
            return 'LOW'


# ===================================================================
# USAGE EXAMPLE
# ===================================================================

if __name__ == '__main__':
    universal_assessment = UniversalDiseaseRiskAssessment()

    # Test 1: Disease in local DB
    print("="*70)
    print("TEST 1: Known disease (in local database)")
    print("="*70)
    result1 = universal_assessment.assess_disease_risk_universal(
        disease_input='Sepsis',
        age=72,
        gender='Male',
        sys_bp=88,
        dia_bp=55,
        hr=128,
        temp_f=103.5,
    )
    print(f"Sources checked: {result1['sources_checked']}")
    print(f"Source used: {result1['source_used']}")
    print(f"Risk category: {result1['final_risk'].get('risk_category')}\n")

    # Test 2: Rare disease (queries SNOMED-CT)
    print("="*70)
    print("TEST 2: Rare disease (queries SNOMED-CT)")
    print("="*70)
    result2 = universal_assessment.assess_disease_risk_universal(
        disease_input='Ehlers-Danlos Syndrome',
        age=35,
        gender='Female',
        sys_bp=120,
        dia_bp=80,
        hr=75,
        temp_f=98.6,
    )
    print(f"Sources checked: {result2['sources_checked']}")
    print(f"Source used: {result2['source_used']}")
    print(f"Risk result: {result2['final_risk']}\n")

    # Test 3: Unknown disease (multi-source fallback)
    print("="*70)
    print("TEST 3: Unknown disease (tries all sources)")
    print("="*70)
    result3 = universal_assessment.assess_disease_risk_universal(
        disease_input='Ribose-5-Phosphate Deficiency',
        age=28,
        gender='Male',
        sys_bp=125,
        dia_bp=82,
        hr=78,
        temp_f=98.8,
    )
    print(f"Sources checked: {result3['sources_checked']}")
    print(f"Source used: {result3['source_used']}")
    print(f"Risk result: {result3['final_risk']}\n")
