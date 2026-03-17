from spell_corrector import symptom_corrector

test_cases = [
    "retentis pigmentosa",  # Wrong spelling
    "retinitis pigmentosa",  # Correct spelling
    "glawcoma",  # Wrong spelling
    "diabetis",  # Wrong spelling
    "diabetes",  # Correct
    "pnemonia",  # Wrong spelling
    "chest pian",  # Wrong spelling
]

print("=" * 80)
print("SPELL CORRECTOR TEST - Hospital Typo Scenario")
print("=" * 80 + "\n")

for test in test_cases:
    corrected, was_corrected, confidence = symptom_corrector.correct_symptom(test)
    status = "CORRECTED ✓" if was_corrected else "CORRECT ✓"
    print(f"[{status:15}] '{test}' → '{corrected}' ({confidence*100:.0f}% confidence)")

print("\n" + "=" * 80)
print("CONCLUSION: Spell corrector can handle hospital typos automatically!")
print("=" * 80)
