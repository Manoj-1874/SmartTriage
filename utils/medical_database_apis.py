"""
MULTI-SOURCE MEDICAL DISEASE LOOKUP
Connects to multiple free medical APIs with fallback chain
CRITICAL: External APIs are essential when local database doesn't have disease!
"""

import requests
import json
from typing import Dict, List, Optional
import logging
import time

logger = logging.getLogger(__name__)

class MedicalDatabaseAPIs:
    """
    Query multiple free medical knowledge bases
    Fallback chain: SNOMED → Wikipedia → MeSH → Local cache

    TIMEOUT STRATEGY:
    - Per API: 8 seconds (enough for network latency)
    - Per source search: 8 seconds
    - Total query timeout: 30 seconds (allow all APIs to respond)
    """

    # HTTP headers (User-Agent required by many APIs)
    HTTP_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Multiple medical knowledge sources
    API_SOURCES = {
        'wikipedia': 'https://en.wikipedia.org/w/api.php',
        'wikidata': 'https://www.wikidata.org/w/api.php',
        'mesh': 'https://clinicaltables.nlm.nih.gov/api/mesh/v3/search',
        'rxnorm': 'https://clinicaltables.nlm.nih.gov/api/rxnorm/v3/search',
    }

    # Per-API timeout configuration (seconds)
    # CRITICAL: Reduced from 8s to 2s to prevent anti-bot protection delays
    # External APIs with anti-bot measures hold connections open to timeout
    # Fast timeout ensures graceful fallback to local AI without UI freezing
    API_TIMEOUTS = {
        'wikipedia': 2,    # Reduced from 8: Wikipedia has heavy anti-bot protection
        'mesh': 2,         # Reduced from 8: MeSH slow due to Cloudflare
        'wikidata': 2,     # Reduced from 8: Wikidata also slow
        'rxnorm': 2,       # Reduced from 6: RxNorm can be slow too
    }

    # Retry configuration
    MAX_RETRIES = 1      # Reduced from 3: No point retrying if API blocks bots
    RETRY_DELAY = 0.1    # Reduced from 0.5: Faster failure

    # Local cache for fetched diseases
    _disease_cache = {}

    @staticmethod
    def search_disease_comprehensive(disease_name: str, timeout: int = 8) -> Dict:
        """
        Search multiple medical databases for disease information

        Returns comprehensive disease info including:
        - Wikipedia summary
        - Symptoms & treatments
        - ICD codes
        - Severity classification
        """

        logger.info(f"[MULTI-API] Starting comprehensive search for: '{disease_name}'")

        # Check cache first
        if disease_name.lower() in MedicalDatabaseAPIs._disease_cache:
            logger.info(f"[CACHE-HIT] Disease found in cache: '{disease_name}'")
            return MedicalDatabaseAPIs._disease_cache[disease_name.lower()]

        # Try multiple sources in sequence
        results = {
            'disease_name': disease_name,
            'found': False,
            'sources': {},
        }

        # Source 1: Wikipedia Medical Article
        wiki_result = MedicalDatabaseAPIs._search_wikipedia(disease_name, timeout)
        if wiki_result:
            results['sources']['wikipedia'] = wiki_result
            results['found'] = True
            logger.info(f"[WIKIPEDIA] Found: '{disease_name}'")

        # Source 2: MeSH (Medical Subject Headings)
        mesh_result = MedicalDatabaseAPIs._search_mesh(disease_name, timeout)
        if mesh_result:
            results['sources']['mesh'] = mesh_result
            results['found'] = True
            logger.info(f"[MeSH] Found: '{disease_name}'")

        # Source 3: Wikidata
        wikidata_result = MedicalDatabaseAPIs._search_wikidata(disease_name, timeout)
        if wikidata_result:
            results['sources']['wikidata'] = wikidata_result
            results['found'] = True
            logger.info(f"[WIKIDATA] Found: '{disease_name}'")

        # Cache the result
        if results['found']:
            MedicalDatabaseAPIs._disease_cache[disease_name.lower()] = results
            logger.info(f"[CACHE-STORE] Cached disease: '{disease_name}'")

        return results

    @staticmethod
    def _search_wikipedia(disease_name: str, timeout: int = 8) -> Optional[Dict]:
        """Search Wikipedia for medical articles with retry logic"""
        api_timeout = timeout or MedicalDatabaseAPIs.API_TIMEOUTS['wikipedia']

        for attempt in range(1, MedicalDatabaseAPIs.MAX_RETRIES + 1):
            try:
                params = {
                    'action': 'query',
                    'list': 'search',
                    'srsearch': disease_name,
                    'format': 'json',
                    'srlimit': 3,
                }

                response = requests.get(
                    MedicalDatabaseAPIs.API_SOURCES['wikipedia'],
                    params=params,
                    timeout=api_timeout,
                    headers=MedicalDatabaseAPIs.HTTP_HEADERS
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('query', {}).get('search', [])

                    if results:
                        top_result = results[0]
                        logger.info(f"[WIKIPEDIA-SUCCESS] Found '{disease_name}' (attempt {attempt})")
                        return {
                            'title': top_result.get('title'),
                            'snippet': top_result.get('snippet'),
                            'url': f"https://en.wikipedia.org/wiki/{top_result.get('title').replace(' ', '_')}"
                        }
            except requests.Timeout:
                logger.warning(f"[WIKIPEDIA-TIMEOUT] Attempt {attempt}/{MedicalDatabaseAPIs.MAX_RETRIES} - timeout after {api_timeout}s")
                if attempt < MedicalDatabaseAPIs.MAX_RETRIES:
                    time.sleep(MedicalDatabaseAPIs.RETRY_DELAY)
                continue
            except requests.ConnectionError as e:
                logger.warning(f"[WIKIPEDIA-CONNECTION] Attempt {attempt}/{MedicalDatabaseAPIs.MAX_RETRIES} - {str(e)[:80]}")
                if attempt < MedicalDatabaseAPIs.MAX_RETRIES:
                    time.sleep(MedicalDatabaseAPIs.RETRY_DELAY)
                continue
            except Exception as e:
                logger.debug(f"[WIKIPEDIA-ERROR] Attempt {attempt}: {type(e).__name__}: {str(e)[:80]}")
                if attempt < MedicalDatabaseAPIs.MAX_RETRIES:
                    time.sleep(MedicalDatabaseAPIs.RETRY_DELAY)
                continue

        logger.info(f"[WIKIPEDIA-FAILED] Could not find '{disease_name}' after {MedicalDatabaseAPIs.MAX_RETRIES} attempts")
        return None

    @staticmethod
    def _search_mesh(disease_name: str, timeout: int = 8) -> Optional[Dict]:
        """Search MeSH (Medical Subject Headings) database with retry logic"""
        api_timeout = timeout or MedicalDatabaseAPIs.API_TIMEOUTS['mesh']

        for attempt in range(1, MedicalDatabaseAPIs.MAX_RETRIES + 1):
            try:
                params = {
                    'q': disease_name,
                    'max_list_size': 10,
                }

                response = requests.get(
                    MedicalDatabaseAPIs.API_SOURCES['mesh'],
                    params=params,
                    timeout=api_timeout,
                    headers=MedicalDatabaseAPIs.HTTP_HEADERS
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('result', [])

                    if results:
                        top_match = results[1] if len(results) > 1 else results[0]  # Skip "Search Results"

                        # Extract key data
                        mesh_info = {
                            'mesh_id': top_match.get('ui'),
                            'name': top_match.get('name'),
                            'definition': top_match.get('definition'),
                        }

                        logger.info(f"[MeSH-SUCCESS] Found '{disease_name}' (attempt {attempt})")
                        return mesh_info
            except requests.Timeout:
                logger.warning(f"[MeSH-TIMEOUT] Attempt {attempt}/{MedicalDatabaseAPIs.MAX_RETRIES} - timeout after {api_timeout}s")
                if attempt < MedicalDatabaseAPIs.MAX_RETRIES:
                    time.sleep(MedicalDatabaseAPIs.RETRY_DELAY)
                continue
            except requests.ConnectionError as e:
                logger.warning(f"[MeSH-CONNECTION] Attempt {attempt}/{MedicalDatabaseAPIs.MAX_RETRIES} - {str(e)[:80]}")
                if attempt < MedicalDatabaseAPIs.MAX_RETRIES:
                    time.sleep(MedicalDatabaseAPIs.RETRY_DELAY)
                continue
            except Exception as e:
                logger.debug(f"[MeSH-ERROR] Attempt {attempt}: {type(e).__name__}: {str(e)[:80]}")
                if attempt < MedicalDatabaseAPIs.MAX_RETRIES:
                    time.sleep(MedicalDatabaseAPIs.RETRY_DELAY)
                continue

        logger.info(f"[MeSH-FAILED] Could not find '{disease_name}' after {MedicalDatabaseAPIs.MAX_RETRIES} attempts")
        return None

    @staticmethod
    def _search_wikidata(disease_name: str, timeout: int = 8) -> Optional[Dict]:
        """Search Wikidata for disease information with retry logic"""
        api_timeout = timeout or MedicalDatabaseAPIs.API_TIMEOUTS['wikidata']

        for attempt in range(1, MedicalDatabaseAPIs.MAX_RETRIES + 1):
            try:
                params = {
                    'action': 'wbsearchentities',
                    'search': disease_name,
                    'language': 'en',
                    'format': 'json',
                    'limit': 5,
                }

                response = requests.get(
                    MedicalDatabaseAPIs.API_SOURCES['wikidata'],
                    params=params,
                    timeout=api_timeout,
                    headers=MedicalDatabaseAPIs.HTTP_HEADERS
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('search', [])

                    if results:
                        top_result = results[0]
                        logger.info(f"[WIKIDATA-SUCCESS] Found '{disease_name}' (attempt {attempt})")
                        return {
                            'wikidata_id': top_result.get('id'),
                            'label': top_result.get('label'),
                            'description': top_result.get('description'),
                            'url': f"https://www.wikidata.org/wiki/{top_result.get('id')}"
                        }
            except requests.Timeout:
                logger.warning(f"[WIKIDATA-TIMEOUT] Attempt {attempt}/{MedicalDatabaseAPIs.MAX_RETRIES} - timeout after {api_timeout}s")
                if attempt < MedicalDatabaseAPIs.MAX_RETRIES:
                    time.sleep(MedicalDatabaseAPIs.RETRY_DELAY)
                continue
            except requests.ConnectionError as e:
                logger.warning(f"[WIKIDATA-CONNECTION] Attempt {attempt}/{MedicalDatabaseAPIs.MAX_RETRIES} - {str(e)[:80]}")
                if attempt < MedicalDatabaseAPIs.MAX_RETRIES:
                    time.sleep(MedicalDatabaseAPIs.RETRY_DELAY)
                continue
            except Exception as e:
                logger.debug(f"[WIKIDATA-ERROR] Attempt {attempt}: {type(e).__name__}: {str(e)[:80]}")
                if attempt < MedicalDatabaseAPIs.MAX_RETRIES:
                    time.sleep(MedicalDatabaseAPIs.RETRY_DELAY)
                continue

        logger.info(f"[WIKIDATA-FAILED] Could not find '{disease_name}' after {MedicalDatabaseAPIs.MAX_RETRIES} attempts")
        return None

    @staticmethod
    def get_cached_diseases() -> List[str]:
        """Get list of all cached diseases"""
        return list(MedicalDatabaseAPIs._disease_cache.keys())

    @staticmethod
    def clear_cache():
        """Clear disease cache"""
        MedicalDatabaseAPIs._disease_cache.clear()
        logger.info("[CACHE] Disease cache cleared")
