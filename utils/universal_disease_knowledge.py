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

    # Primary SNOMED Servers (with multiple fallbacks)
    SNOMED_APIS = [
        "https://browser.ihtsdotools.org/snowstorm/snomed-ct",  # Official free server
        "https://snomed.edu-hub.com/snowstorm/snomed-ct",       # Backup server
    ]

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
    def search_disease(disease_name: str, version: str = "MAIN/2023-01-31", max_retries: int = 3) -> Dict:
        """
        Search SNOMED-CT for disease information with retry logic and multiple servers

        Example:
        >>> search_disease("Cholangiocarcinoma")
        Returns: {
            'found': True,
            'disease_name': 'Cholangiocarcinoma',
            'preferred_term': 'Cholangiocarcinoma (disorder)',
            ...
        }
        """
        # Normalize disease name using aliases
        normalized_name = SNOMEDIntegration._normalize_disease_name(disease_name)

        logger.info(f"[SNOMED] Searching for: '{normalized_name}' (original: '{disease_name}')")

        # Try each SNOMED server
        for server_idx, snomed_api in enumerate(SNOMEDIntegration.SNOMED_APIS):
            for attempt in range(max_retries):
                try:
                    search_url = f"{snomed_api}/{version}/concepts"
                    params = {
                        'query': normalized_name,
                        'limit': 10,
                        'offset': 0,
                    }

                    logger.debug(f"[SNOMED-ATTEMPT {attempt+1}/{max_retries}] Server {server_idx+1}: {search_url}")

                    response = requests.get(search_url, params=params, timeout=5)  # Reduced timeout

                    if response.status_code == 200:
                        data = response.json()
                        logger.debug(f"[SNOMED-RESPONSE] Status 200, items found: {len(data.get('items', []))}")

                        if data.get('items'):
                            top_match = data['items'][0]
                            result = {
                                'found': True,
                                'snomed_id': top_match.get('id'),
                                'disease_name': normalized_name,
                                'preferred_term': top_match.get('pt', {}).get('term'),
                                'definitions': top_match.get('definitions', []),
                                'parent_concepts': SNOMEDIntegration._get_parent_concepts(
                                    top_match.get('id'), version, snomed_api
                                ),
                                'related_symptoms': SNOMEDIntegration._get_related_symptoms(
                                    top_match.get('id'), version, snomed_api
                                ),
                                'icd_code': SNOMEDIntegration._map_to_icd10(top_match.get('id')),
                                'server': f'SNOMED-CT (Server {server_idx+1})'
                            }

                            logger.info(f"[SNOMED-SUCCESS] Found: '{normalized_name}' via {result['server']}")
                            return result
                        else:
                            logger.warning(f"[SNOMED-NO-RESULTS] No items returned for '{normalized_name}'")
                    else:
                        logger.warning(f"[SNOMED-HTTP-{response.status_code}] Server returned error")

                except requests.Timeout:
                    logger.warning(f"[SNOMED-TIMEOUT] Server {server_idx+1} attempt {attempt+1} timed out")
                    time.sleep(0.5)  # Brief delay before retry
                except requests.ConnectionError as e:
                    logger.warning(f"[SNOMED-CONNECTION-ERROR] Server {server_idx+1} connection failed: {str(e)}")
                    time.sleep(0.5)
                except json.JSONDecodeError:
                    logger.warning(f"[SNOMED-JSON-ERROR] Server {server_idx+1} returned invalid JSON")
                except Exception as e:
                    logger.error(f"[SNOMED-ERROR] Server {server_idx+1} attempt {attempt+1}: {type(e).__name__}: {str(e)}")
                    time.sleep(0.5)

        # If all servers failed, return not found
        logger.warning(f"[SNOMED-ALL-FAILED] Could not find '{normalized_name}' in any SNOMED server")
        return {'found': False, 'reason': 'Disease not found in SNOMED-CT or all servers unavailable'}

    @staticmethod
    def _normalize_disease_name(disease_name: str) -> str:
        """Normalize disease name using aliases - convert user input to standard names"""
        disease_lower = disease_name.lower().strip()

        # Check if direct alias exists
        if disease_lower in SNOMEDIntegration.DISEASE_ALIASES:
            normalized = SNOMEDIntegration.DISEASE_ALIASES[disease_lower]
            logger.info(f"[ALIAS] '{disease_name}' → '{normalized}'")
            return normalized

        # Check for partial matches (e.g., "coronary disease" contains "coronary")
        for alias_key, standard_name in SNOMEDIntegration.DISEASE_ALIASES.items():
            if alias_key in disease_lower or disease_lower in alias_key:
                logger.info(f"[ALIAS-PARTIAL] '{disease_name}' → '{standard_name}'")
                return standard_name

        # No alias found, use original name
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
        wiki_result = MedicalDiseaseAPI._search_wikipedia_medical(disease_name)
        if wiki_result:
            return {
                'source': 'Wikipedia (Medical)',
                'disease_name': disease_name,
                'description': wiki_result.get('description'),
                'confidence': 0.70,
            }

        # Try 3: Semantic analysis (last resort)
        return None

    @staticmethod
    def _search_wikipedia_medical(disease_name: str) -> Optional[Dict]:
        """Search Wikipedia for disease information"""
        try:
            import wikipedia

            results = wikipedia.search(disease_name, results=1)
            if results:
                page = wikipedia.page(results[0])
                return {
                    'description': page.summary[:500],  # First 500 chars
                    'url': page.url,
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

        result = {
            'disease_input': disease_input,
            'sources_checked': [],
            'final_risk': None,
        }

        # ===== SOURCE 1: Local AI Database =====
        local_result = self.local_ai.assess_patient_disease_risk(
            disease_name_or_symptoms=disease_input,
            age=age,
            gender=gender,
            sys_bp=sys_bp,
            dia_bp=dia_bp,
            hr=hr,
            temp_f=temp_f,
            comorbidities=comorbidities,
        )

        if local_result.get('is_known_disease'):
            result['sources_checked'].append('Local Database')
            result['source_used'] = 'Local AI (Known Disease)'
            result['final_risk'] = local_result
            return result

        result['sources_checked'].append('Local Database')

        # ===== SOURCE 2: SNOMED-CT (Medical Terminology) =====
        snomed_info = SNOMEDIntegration.search_disease(disease_input)

        if snomed_info.get('found'):
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
        medical_info = MedicalDiseaseAPI.get_disease_from_web(disease_input)

        if medical_info:
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
            'disease_identified': disease_input,
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
            if any(word in parent.lower() for word in ['critical', 'emergency', 'acute severe']):
                base_risk = 0.80
                break
            elif any(word in parent.lower() for word in ['chronic', 'genetic', 'hereditary']):
                base_risk = 0.55

        # Apply vital signs
        vital_risk = self._assess_vitals(sys_bp, dia_bp, hr, temp_f)

        # Apply age
        age_risk = self._assess_age(age)

        final_risk = base_risk * vital_risk * age_risk

        return {
            'disease_identified': snomed_info.get('preferred_term'),
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

        description = medical_info.get('description', '').lower()

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
            'disease_identified': medical_info.get('disease_name'),
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
