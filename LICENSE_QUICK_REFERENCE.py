#!/usr/bin/env python3
"""
SmartTriage Dashboard - License Quick Reference
License Type: PROPRIETARY (NOT OPEN SOURCE)
Effective Date: March 21, 2026
"""

# ============================================================================
# QUICK REFERENCE - WHAT YOU CAN AND CANNOT DO
# ============================================================================

LICENSE_QUICK_REFERENCE = {
    "Project": "SmartTriage Dashboard",
    "Owner": "NilalThiruvila",
    "License_Type": "PROPRIETARY AND CONFIDENTIAL",
    "Open_Source": False,
    "Status": "ACTIVELY ENFORCED",

    # CAN DO
    "PERMITTED_ACTIONS": [
        "✅ Read and evaluate the software",
        "✅ Use for personal, non-commercial purposes",
        "✅ Use in authorized healthcare deployment",
        "✅ Report security vulnerabilities",
        "✅ Request features from owner",
        "✅ Use under licensed agreement (commercial)",
        "✅ Deploy with written permission",
    ],

    # CAN'T DO
    "PROHIBITED_ACTIONS": [
        "❌ Copy or clone the repository",
        "❌ Create a fork for distribution",
        "❌ Upload to GitHub/GitLab publicly",
        "❌ Share source code with others",
        "❌ Modify and redistribute",
        "❌ Create derivative works",
        "❌ Use commercially without license",
        "❌ Reverse engineer the algorithms",
        "❌ Remove copyright notices",
        "❌ Bundle with other products",
        "❌ Create competing systems",
        "❌ Extract ML models for standalone use",
        "❌ Disassemble or decompile",
        "❌ Expose to unauthorized parties",
    ],

    # PENALTIES
    "VIOLATIONS_RESULT_IN": [
        "💰 Civil damages: $10,000 - $150,000+",
        "⚖️  Legal prosecution",
        "🔒 Injunctions and court orders",
        "📋 Attorney fees and court costs",
        "👮 Criminal charges (DMCA)",
        "🚫 Permanent loss of access",
    ],

    # IMPORTANT FILES
    "LICENSE_FILES": {
        "LICENSE": "Full proprietary license agreement (~500 lines)",
        "COPYRIGHT.txt": "Copyright notice and legal warning",
        "REDISTRIBUTION.md": "Detailed copying restrictions",
        "SECURITY.md": "Anti-duplication and security measures",
        "README.md": "Project overview with license info",
    },

    # CONTACT
    "CONTACT_FOR": {
        "Commercial_License": "[Your Email]",
        "Violation_Report": "[Your Email]",
        "Permission_Request": "[Your Email]",
        "Technical_Support": "[Your Email]",
    }
}

# ============================================================================
# LICENSE KEY POINTS
# ============================================================================

def print_license_summary():
    """Print a quick summary of the license"""

    print("""
╔═════════════════════════════════════════════════════════════╗
║     SMARTTRIAGE DASHBOARD - LICENSE QUICK REFERENCE         ║
╚═════════════════════════════════════════════════════════════╝

PROJECT STATUS:
  • Name: SmartTriage Dashboard
  • Type: PROPRIETARY SOFTWARE (NOT OPEN SOURCE)
  • License: Proprietary & Confidential
  • Status: ACTIVELY ENFORCED
  • Owner: NilalThiruvila

═══════════════════════════════════════════════════════════════

✅ YOU CAN DO:
  ✓ Evaluate the software
  ✓ Use for personal purposes
  ✓ Deploy in authorized healthcare facility
  ✓ Report security issues
  ✓ Request features from owner

❌ YOU CANNOT DO:
  ✗ Copy the repository
  ✗ Create a public fork
  ✗ Share source code
  ✗ Modify and redistribute
  ✗ Use commercially without license
  ✗ Create competing products
  ✗ Reverse engineer
  ✗ Remove copyright notices

═══════════════════════════════════════════════════════════════

⚖️  PENALTIES FOR VIOLATION:
  • Civil damages: $10,000 - $150,000+
  • Criminal charges possible (DMCA)
  • Injunctions and court orders
  • Attorney fees and costs
  • Permanent loss of access

═══════════════════════════════════════════════════════════════

📄 KEY LICENSE FILES:
  1. LICENSE - Full legal agreement
  2. COPYRIGHT.txt - Copyright notice
  3. REDISTRIBUTION.md - Copying restrictions
  4. SECURITY.md - Anti-duplication measures
  5. README.md - Project overview

═══════════════════════════════════════════════════════════════

📞 CONTACT:
  Email: [Your Email - TO BE CONFIGURED]

  For:
    • Commercial licensing
    • Permission requests
    • Violation reports
    • Technical support

═══════════════════════════════════════════════════════════════

🔒 PROTECTION MECHANISMS:
  ✓ Copyright law protection
  ✓ Trade secret designation
  ✓ Git monitoring
  ✓ Code similarity detection
  ✓ Deployment tracking
  ✓ DMCA compliance
  ✓ Legal enforcement procedures

═══════════════════════════════════════════════════════════════

⚠️  IMPORTANT WARNINGS:
  • Do NOT copy this repository
  • Do NOT create public forks
  • Do NOT modify and share
  • Do NOT use commercially
  • Do NOT reverse engineer
  • Do NOT expose source code

  Unauthorized copying WILL BE DETECTED and PROSECUTED

═══════════════════════════════════════════════════════════════

For complete license terms, see:
  👉 Read the LICENSE file

For technical details, see:
  👉 Read the SECURITY.md file

For copying restrictions, see:
  👉 Read the REDISTRIBUTION.md file

═══════════════════════════════════════════════════════════════

Effective Date: March 21, 2026
Status: ACTIVE AND ENFORCED

By downloading or using this software, you agree to comply
with all terms of the proprietary license agreement.

═══════════════════════════════════════════════════════════════
    """)


def check_compliance():
    """Return True if usage appears to be compliant"""

    print("""
COMPLIANCE CHECK:

Before using SmartTriage Dashboard, verify:

1. [ ] I have read the LICENSE file
2. [ ] I understand the restrictions
3. [ ] I am not copying the repository
4. [ ] I am not creating a public fork
5. [ ] I am not planning commercial use without license
6. [ ] I will not share source code
7. [ ] I will not reverse engineer
8. [ ] I will not remove copyright notices
9. [ ] I understand the penalties
10. [ ] I agree to all license terms

If all items are checked, you may proceed.
If any are unchecked, DO NOT use this software.

    """)


if __name__ == "__main__":
    print_license_summary()

    print("\n" + "="*60)
    print("LICENSE STATUS: ACTIVE")
    print("="*60)

    print("""
NEXT STEPS:

1. READ the LICENSE file thoroughly
2. UNDERSTAND the restrictions
3. ENSURE compliance before use
4. CONTACT owner for questions
5. REQUEST permission for special use cases

Questions? Contact: [Your Email]

═══════════════════════════════════════════════════════════════
⛔ UNAUTHORIZED COPYING WILL BE PROSECUTED ⛔
═══════════════════════════════════════════════════════════════
    """)
