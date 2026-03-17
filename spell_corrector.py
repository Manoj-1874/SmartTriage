"""
SPELL CORRECTION MODULE
Handles typos in medical symptoms using fuzzy matching
Useful for hospital rush scenarios where spelling mistakes are common
"""

from difflib import SequenceMatcher
import logging

class SymptomSpellCorrector:
    """Auto-corrects misspelled medical symptoms"""

    # Common medical conditions (expandable)
    KNOWN_SYMPTOMS = {
        # Eye conditions
        'retinitis pigmentosa': ['retentis pigmentosa', 'retinitus pigmentosa', 'retinitis pigmntosa'],
        'glaucoma': ['glawcoma', 'glucoma', 'glaucomo'],
        'cataracts': ['cataract', 'cataracs', 'cateracts'],
        'macular degeneration': ['macular degradation', 'maclar degeneration'],

        # Respiratory
        'asthma': ['astma', 'asthma', 'athsma'],
        'pneumonia': ['pnemonia', 'pneumonia', 'pnuemonia'],
        'bronchitis': ['bronchitus', 'broncitis', 'bronchitus'],
        'cough': ['cough', 'cogh', 'cugh'],
        'dyspnea': ['dispnea', 'dyspnea', 'dyspnia'],

        # Cardiac
        'arrhythmia': ['arrhythmia', 'arrhythmya', 'arythmia'],
        'myocardial infarction': ['myocardal infarction', 'myo infarction'],
        'angina': ['angina', 'anginna'],
        'hypertension': ['hypertention', 'hypertention', 'hippertension'],
        'heart failure': ['heart failure', 'hart failure'],

        # Neurological
        'stroke': ['stroke', 'strok'],
        'seizure': ['seizure', 'siezure', 'seisure'],
        'migraine': ['migrane', 'migrene', 'migrain'],
        'dementia': ['dememtia', 'dementia', 'dmentsia'],

        # Endocrine
        'diabetes': ['diabetis', 'diabeties', 'diabetus'],
        'hypoglycemia': ['hypoglycemia', 'hypoglycaemia'],
        'hyperglycemia': ['hyperglycemia', 'hyperglycaemia'],

        # Gastrointestinal
        'gastroenteritis': ['gasteroenteritis', 'gastroenteritus'],
        'appendicitis': ['appendicitus', 'appendicitus'],
        'hepatitis': ['hepatitus', 'hepatitus'],
        'pancreatitis': ['pancreatitus', 'panceratitis'],

        # Other common conditions
        'fever': ['fevr', 'fever', 'feavr'],
        'nausea': ['nausea', 'nausea', 'nauasea'],
        'vomiting': ['vomiting', 'vomitting', 'vomiting'],
        'diarrhea': ['diarrhea', 'diarrhea', 'diahrehea'],
        'abdominal pain': ['abdominal pain', 'abdominal pian', 'abd pain'],
        'chest pain': ['chest pain', 'chest pian', 'cheast pain'],
        'dysphagia': ['disphagia', 'dysphagia', 'dysphgia'],
    }

    def __init__(self, threshold=0.75, logger=None):
        """
        Initialize corrector
        threshold: Similarity threshold (0-1) for accepting corrections
        """
        self.threshold = threshold
        self.logger = logger or logging.getLogger(__name__)

        # Build reverse lookup for faster searching
        self.symptom_map = {}
        for correct, misspellings in self.KNOWN_SYMPTOMS.items():
            self.symptom_map[correct.lower()] = correct
            for misspelling in misspellings:
                self.symptom_map[misspelling.lower()] = correct

    def find_similarity(self, input_text, correct_text):
        """Calculate similarity ratio between two strings"""
        return SequenceMatcher(None, input_text.lower(), correct_text.lower()).ratio()

    def correct_symptom(self, symptom_input):
        """
        Auto-correct misspelled symptom
        Returns: (corrected_symptom, was_corrected, confidence)
        """
        if not symptom_input or not isinstance(symptom_input, str):
            return symptom_input, False, 0.0

        symptom_lower = symptom_input.lower().strip()

        # Direct match (case-insensitive)
        if symptom_lower in self.symptom_map:
            correct = self.symptom_map[symptom_lower]
            was_corrected = (correct.lower() != symptom_lower)
            confidence = 1.0 if not was_corrected else 0.95
            return correct, was_corrected, confidence

        # Fuzzy match
        best_match = None
        best_similarity = 0.0

        for correct_symptom in self.KNOWN_SYMPTOMS.keys():
            similarity = self.find_similarity(symptom_input, correct_symptom)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = correct_symptom

        # Accept if above threshold
        if best_similarity >= self.threshold:
            if self.logger:
                self.logger.info(f"[SPELL-CORRECT] '{symptom_input}' → '{best_match}' (confidence: {best_similarity:.2%})")
            return best_match, True, best_similarity

        # No good match found
        if self.logger:
            self.logger.warning(f"[SPELL-CHECK] Could not correct '{symptom_input}' (best match similarity: {best_similarity:.2%})")
        return symptom_input, False, best_similarity

    def add_symptom(self, correct_symptom, misspellings=None):
        """Dynamically add new symptoms to the correction dictionary"""
        if correct_symptom not in self.KNOWN_SYMPTOMS:
            self.KNOWN_SYMPTOMS[correct_symptom] = misspellings or []
            self.symptom_map[correct_symptom.lower()] = correct_symptom
            if misspellings:
                for misspelling in misspellings:
                    self.symptom_map[misspelling.lower()] = correct_symptom
            self.logger.info(f"[SYMPTOM-ADD] Added '{correct_symptom}' to correction dictionary")


# Global corrector instance
symptom_corrector = SymptomSpellCorrector()
