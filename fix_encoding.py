#!/usr/bin/env python3
"""Fix encoding issues in HTML templates"""

import os
import glob

# List of HTML files to fix
html_files = [
    'templates/health_report.html',
    'templates/patient_dashboard.html',
    'templates/appointments.html',
    'templates/checkup.html',
    'templates/doctors.html',
    'templates/messages.html',
]

replacements = {
    'â€"': '-',        # Garbled em-dash
    'â€"': '–',        # Garbled dash variant
    'Â©': '©',         # Garbled copyright
    'Â·': '·',         # Garbled middle dot
    'â•': '',          # Garbled box drawing
}

for filepath in html_files:
    full_path = filepath
    if not os.path.exists(full_path):
        print(f"✗ File not found: {full_path}")
        continue

    try:
        # Read with error handling
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        original_length = len(content)

        # Apply replacements
        for bad, good in replacements.items():
            content = content.replace(bad, good)

        # Write back
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✓ Fixed: {full_path}")

    except Exception as e:
        print(f"✗ Error fixing {full_path}: {e}")

print("\n✓ All encoding issues fixed!")
