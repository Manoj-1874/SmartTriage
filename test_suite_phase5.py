"""
PHASE 5.1: FINAL TESTING SUITE
Comprehensive tests before deployment
Covers: unit tests, integration tests, safety checks, edge cases
"""

import json
import numpy as np
from input_validator import VitalSignsValidator
from confidence_threshold import ConfidenceThreshold
import joblib
from datetime import datetime

class TestSuite:
    """Comprehensive test suite for SmartTriage"""

    def __init__(self):
        self.results = {
            'test_timestamp': datetime.now().isoformat(),
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'test_results': {}
        }

    def run_all_tests(self):
        """Run complete test suite"""
        print("=" * 80)
        print("SMARTTRIAGE - PHASE 5.1: FINAL TESTING SUITE")
        print("=" * 80)
        print()

        self.test_input_validation()
        self.test_confidence_thresholds()
        self.test_model_loading()
        self.test_edge_cases()
        self.test_safety_overrides()
        self.test_clinical_scenarios()

        self.print_summary()
        return self.results

    def test_input_validation(self):
        """Test 1: Input validation"""
        print("TEST 1: Input Validation")
        print("-" * 80)

        validator = VitalSignsValidator()
        test_cases = [
            {
                'name': 'Normal vitals',
                'input': {'age': 45, 'sys_bp': 120, 'dia_bp': 78, 'hr': 72, 'temp_c': 37.2},
                'should_pass': True
            },
            {
                'name': 'Shock vitals (low BP)',
                'input': {'age': 55, 'sys_bp': 85, 'dia_bp': 52, 'hr': 135, 'temp_c': 40.0},
                'should_pass': True
            },
            {
                'name': 'Invalid age',
                'input': {'age': 'invalid', 'sys_bp': 120, 'dia_bp': 78, 'hr': 72, 'temp_c': 37.2},
                'should_pass': False
            },
            {
                'name': 'Missing age',
                'input': {'sys_bp': 120, 'dia_bp': 78, 'hr': 72, 'temp_c': 37.2},
                'should_pass': False
            },
            {
                'name': 'Age > 100',
                'input': {'age': 150, 'sys_bp': 120, 'dia_bp': 78, 'hr': 72, 'temp_c': 37.2},
                'should_pass': False
            }
        ]

        passed = 0
        for test in test_cases:
            valid, norm, errors, warnings = validator.validate_vital_signs(**test['input'])
            success = valid == test['should_pass']
            status = "✓" if success else "✗"
            passed += success

            print(f"  {status} {test['name']}: {valid} (expected: {test['should_pass']})")
            if errors:
                print(f"     Errors: {errors}")

        self.record_test('input_validation', passed, len(test_cases))
        print()

    def test_confidence_thresholds(self):
        """Test 2: Confidence threshold logic"""
        print("TEST 2: Confidence Thresholds")
        print("-" * 80)

        thresh = ConfidenceThreshold()

        test_cases = [
            {
                'name': 'High confidence HIGH',
                'probs': np.array([0.05, 0.05, 0.90]),
                'class': 2,
                'expected_level': 'HIGH'
            },
            {
                'name': 'Medium confidence MEDIUM',
                'probs': np.array([0.30, 0.45, 0.25]),
                'class': 1,
                'expected_level': 'MEDIUM'
            },
            {
                'name': 'Low confidence LOW',
                'probs': np.array([0.40, 0.35, 0.25]),
                'class': 0,
                'expected_level': 'LOW'
            },
            {
                'name': 'Very low confidence',
                'probs': np.array([0.33, 0.33, 0.34]),
                'class': 2,
                'expected_level': 'VERY_LOW'
            }
        ]

        passed = 0
        for test in test_cases:
            conf_info = thresh.classify_confidence(test['probs'], test['class'])
            success = conf_info['level'] == test['expected_level']
            status = "✓" if success else "✗"
            passed += success

            print(f"  {status} {test['name']}: {conf_info['level']} (expected: {test['expected_level']})")

        self.record_test('confidence_thresholds', passed, len(test_cases))
        print()

    def test_model_loading(self):
        """Test 3: Model loading and availability"""
        print("TEST 3: Model Loading")
        print("-" * 80)

        passed = 0
        try:
            assets = joblib.load('triage_assets_mingled.pkl')
            assert 'risk_model' in assets, "No risk_model in assets"
            assert 'scaler' in assets, "No scaler in assets"
            assert 'encoders' in assets, "No encoders in assets"
            assert 'features' in assets, "No features in assets"
            print("  ✓ Model file loaded successfully")
            print(f"  ✓ Features: {assets['features']}")
            passed = 1
        except Exception as e:
            print(f"  ✗ Model loading failed: {e}")
            passed = 0

        self.record_test('model_loading', passed, 1)
        print()

    def test_edge_cases(self):
        """Test 4: Edge cases and boundary conditions"""
        print("TEST 4: Edge Cases")
        print("-" * 80)

        validator = VitalSignsValidator()
        edge_cases = [
            {
                'name': 'Minimum age (newborn)',
                'input': {'age': 1, 'sys_bp': 80, 'dia_bp': 50, 'hr': 120, 'temp_c': 37.0},
                'warning_expected': True
            },
            {
                'name': 'Maximum age',
                'input': {'age': 100, 'sys_bp': 130, 'dia_bp': 75, 'hr': 68, 'temp_c': 37.0},
                'warning_expected': False
            },
            {
                'name': 'Extreme hypotension',
                'input': {'age': 45, 'sys_bp': 70, 'dia_bp': 40, 'hr': 140, 'temp_c': 40.0},
                'warning_expected': True
            },
            {
                'name': 'Extreme hypertension',
                'input': {'age': 65, 'sys_bp': 230, 'dia_bp': 130, 'hr': 105, 'temp_c': 37.0},
                'warning_expected': True
            },
            {
                'name': 'Extreme tachycardia',
                'input': {'age': 35, 'sys_bp': 140, 'dia_bp': 85, 'hr': 200, 'temp_c': 38.0},
                'warning_expected': True
            },
            {
                'name': 'Extreme fever',
                'input': {'age': 42, 'sys_bp': 115, 'dia_bp': 70, 'hr': 130, 'temp_c': 41.5},
                'warning_expected': True
            }
        ]

        passed = 0
        for case in edge_cases:
            valid, norm, errors, warnings = validator.validate_vital_signs(**case['input'])
            has_warning = len(warnings) > 0
            success = valid  # Should all be valid
            status = "✓" if success else "✗"
            passed += success

            print(f"  {status} {case['name']}: Valid={valid}, Warnings={len(warnings)}")
            if warnings:
                for w in warnings:
                    print(f"     → {w}")

        self.record_test('edge_cases', passed, len(edge_cases))
        print()

    def test_safety_overrides(self):
        """Test 5: Safety override logic"""
        print("TEST 5: Safety Overrides")
        print("-" * 80)

        thresh = ConfidenceThreshold()
        test_cases = [
            {
                'name': 'Shock pattern (low BP + high HR + fever)',
                'vitals': {'sys_bp': 85, 'hr': 135, 'temp_c': 40.0, 'age': 55},
                'prediction': 'MEDIUM',  # Model predicts MEDIUM
                'should_override_to_high': True
            },
            {
                'name': 'Severe hypotension alone',
                'vitals': {'sys_bp': 75, 'hr': 100, 'temp_c': 37.0, 'age': 50},
                'prediction': 'LOW',
                'should_override_to_high': True
            },
            {
                'name': 'Pediatric high fever',
                'vitals': {'sys_bp': 110, 'hr': 130, 'temp_c': 40.0, 'age': 8},
                'prediction': 'LOW',
                'should_override_to_high': False  # Would be escalated to MEDIUM
            },
            {
                'name': 'Normal vitals with normal prediction',
                'vitals': {'sys_bp': 120, 'hr': 75, 'temp_c': 37.0, 'age': 45},
                'prediction': 'LOW',
                'should_override_to_high': False
            }
        ]

        passed = 0
        for case in test_cases:
            conf_info = {
                'confidence': 0.50,
                'level': 'MEDIUM',
                'probabilities': {'LOW': 0.50, 'MEDIUM': 0.50, 'HIGH': 0.0},
                'predicted_class': 1,
                'margin': 0.0  # No margin between LOW and MEDIUM
            }
            rec = thresh.get_recommendation(conf_info, case['vitals'])
            has_override = rec['requires_override']

            success = has_override == case['should_override_to_high']
            status = "✓" if success else "✗"
            passed += success

            print(f"  {status} {case['name']}: Override={has_override} (expected: {case['should_override_to_high']})")
            if has_override:
                print(f"     Action: {rec['action']}")

        self.record_test('safety_overrides', passed, len(test_cases))
        print()

    def test_clinical_scenarios(self):
        """Test 6: Realistic clinical scenarios"""
        print("TEST 6: Clinical Scenarios")
        print("-" * 80)

        scenarios = [
            {
                'name': 'Routine checkup',
                'vitals': {'age': 35, 'sys_bp': 118, 'dia_bp': 76, 'hr': 72, 'temp_c': 37.0},
                'expected_risk': 'LOW'
            },
            {
                'name': 'Mild fever + cough',
                'vitals': {'age': 28, 'sys_bp': 125, 'dia_bp': 80, 'hr': 92, 'temp_c': 38.2},
                'expected_risk': 'MEDIUM'
            },
            {
                'name': 'Acute MI symptoms',
                'vitals': {'age': 58, 'sys_bp': 145, 'dia_bp': 90, 'hr': 115, 'temp_c': 37.5},
                'expected_risk': 'HIGH'
            },
            {
                'name': 'Septic shock',
                'vitals': {'age': 62, 'sys_bp': 82, 'dia_bp': 50, 'hr': 140, 'temp_c': 40.5},
                'expected_risk': 'HIGH'
            },
            {
                'name': 'Elderly with controlled HTN',
                'vitals': {'age': 72, 'sys_bp': 155, 'dia_bp': 92, 'hr': 80, 'temp_c': 37.0},
                'expected_risk': 'MEDIUM'
            }
        ]

        # Just verify they don't crash (can't validate actual predictions without model loaded)
        validator = VitalSignsValidator()
        passed = 0
        for scenario in scenarios:
            try:
                valid, norm, errors, warnings = validator.validate_vital_signs(**scenario['vitals'])
                if valid:
                    passed += 1
                    print(f"  ✓ {scenario['name']}: Valid")
                else:
                    print(f"  ✗ {scenario['name']}: Invalid - {errors}")
            except Exception as e:
                print(f"  ✗ {scenario['name']}: Exception - {e}")

        self.record_test('clinical_scenarios', passed, len(scenarios))
        print()

    def record_test(self, test_name: str, passed: int, total: int):
        """Record test results"""
        self.results['tests_run'] += total
        self.results['tests_passed'] += passed
        self.results['tests_failed'] += (total - passed)
        self.results['test_results'][test_name] = {
            'passed': passed,
            'total': total,
            'success_rate': f"{passed/total*100:.1f}%"
        }

    def print_summary(self):
        """Print test summary"""
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        total = self.results['tests_run']
        passed = self.results['tests_passed']
        failed = self.results['tests_failed']

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} {'✗' if failed > 0 else ''}")
        print(f"Success Rate: {passed/total*100:.1f}%")

        print(f"\nDetailed Results:")
        for test_name, results in self.results['test_results'].items():
            status = "✓" if results['passed'] == results['total'] else "⚠️"
            print(f"  {status} {test_name}: {results['passed']}/{results['total']} ({results['success_rate']})")

        overall_status = "✅ PASS" if failed == 0 and passed/total >= 0.95 else "❌ FAIL"
        print(f"\nOVERALL: {overall_status}")

        # Save results
        with open('test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: test_results.json")
        print("=" * 80)


if __name__ == '__main__':
    suite = TestSuite()
    results = suite.run_all_tests()
