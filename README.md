# SmartTriage Dashboard

**Healthcare AI Triage System with Dual-Brain Intelligence**

---

## ⚠️ LICENSE & USAGE RESTRICTIONS

### **PROPRIETARY SOFTWARE - NOT OPEN SOURCE**

```
⛔ THIS SOFTWARE IS PROTECTED BY COPYRIGHT AND TRADE SECRET LAW
⛔ UNAUTHORIZED COPYING, DUPLICATION, OR DISTRIBUTION IS PROHIBITED
⛔ VIOLATORS WILL BE PROSECUTED TO THE FULL EXTENT OF THE LAW
```

**Please read the LICENSE file before using this software.**

**Key Restrictions:**
- ❌ NO unauthorized copying or duplication
- ❌ NO commercial use without written permission
- ❌ NO reverse engineering or modification
- ❌ NO distribution to third parties
- ❌ NO creation of derivative works

**Permitted Uses:**
- ✅ Authorized healthcare deployment
- ✅ Personal evaluation and testing
- ✅ Licensed clinical use only
- ✅ Educational use with permission

**See:**
- [`LICENSE`](LICENSE) - Full legal agreement
- [`COPYRIGHT.txt`](COPYRIGHT.txt) - Copyright notice
- [`REDISTRIBUTION.md`](REDISTRIBUTION.md) - Restriction details

---

## 📋 Project Overview

SmartTriage Dashboard is an advanced AI-powered healthcare triage system that combines:
- **XGBoost** for rapid risk classification
- **DistilBERT (BERT)** for semantic symptom analysis
- **Clinical Rule-Based Logic** for contextual risk adjustment
- **Dual-Brain Consensus** for high-safety critical decisions

**Status:** Production-ready healthcare application
**Version:** 1.0.0
**Build Stability:** 97.39% K-Fold CV Accuracy

---

## 🏥 Features

### Core Functionality
- **AI-Powered Risk Assessment** - Predicts patient risk level (LOW/MEDIUM/HIGH)
- **Symptom Auto-Correction** - Handles hospital typos automatically
- **Pain & Duration Tracking** - Captures severity and chronicity
- **Dual-Brain Consensus** - XGBoost + BERT agreement logic
- **Specialist Routing** - Recommends appropriate care pathway

### Clinical Integration
- **Healthcare Professional Dashboard** - PHC nurses, doctors access
- **Patient Portal** - Self-assessment and result tracking
- **Appointment Management** - Integrated scheduling system
- **Medical History** - Pre-condition tracking
- **Secure Communication** - Doctor-patient messaging

### Security & Compliance
- HIPAA-compliant data handling
- Encrypted sensitive information
- Role-based access control (RBAC)
- Comprehensive audit logging
- Database integrity enforcement

---

## 🚀 Quick Start

### Installation
```bash
git clone [AUTHORIZED REPOSITORY ONLY]
cd SmartTriage_Dashboard
pip install -r requirements.txt
```

### Configuration
```bash
cp .env.example .env
# Edit .env with your settings
python app.py
```

### Deployment
```
Access: http://localhost:5000
Login: Use patient/doctor/admin credentials
```

---

## 🏗️ Architecture

### Backend
- **Flask** - Web framework
- **SQLite** - Database
- **XGBoost** - Primary ML model (97.39% accuracy)
- **DistilBERT** - Secondary NLP model
- **NumPy/Pandas** - Data processing

### Frontend
- **HTML5/CSS3** - Responsive UI
- **JavaScript** - Interactive features
- **Chart.js** - Analytics visualization

### ML Models
- **XGBoost Model**: Trained on 1,340+ cases (expanded from 1,090)
- **BERT Model**: DistilBERT for symptom semantic analysis
- **Clinical Rules**: Age-aware, contextual adjustments

---

## 📊 Model Performance

| Metric | Score |
|--------|-------|
| K-Fold CV Accuracy | 97.39% |
| Overfitting Gap | 1.88% |
| Training Samples | 1,340 (expanded) |
| Features | 23 (vitals + demographics + symptoms) |
| Classes | 3 (LOW/MEDIUM/HIGH) |

**Test Results:**
- ✅ 25/25 unit tests passing
- ✅ 8/8 integration tests passing
- ✅ 33/33 production tests passing

---

## 🔍 Key Algorithms

### 1. Risk Classification (XGBoost)
```
Features: Age, Gender, Vitals, Symptoms, History, Duration, Pain
Output: LOW (score ≤ 0.35), MEDIUM (0.35-0.80), HIGH (≥ 0.80)
```

### 2. Symptom Analysis (BERT)
```
Input: Patient-provided symptom text
Process: Semantic analysis via DistilBERT
Output: Emergency vs. non-emergency classification
```

### 3. Dual-Brain Consensus
```
IF XGBoost says LOW but BERT detects emergency:
  → Override to HIGH (Safety First)
  → Route to Emergency Department
```

### 4. Pain & Duration Adjustment
```
IF pain_intensity >= 7: LOW → MEDIUM (severe pain override)
IF symptom_duration == "2+ weeks": LOW → MEDIUM (chronic condition)
```

---

## 📁 Project Structure

```
SmartTriage_Dashboard/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── triage.db                       # SQLite database
├── models/
│   ├── experimental_brain/         # BERT model
│   └── triage_assets_mingled.pkl   # XGBoost + encoders
├── static/
│   ├── css/                        # Stylesheets
│   └── js/                         # JavaScript
├── templates/                      # HTML templates
├── production_modules/             # Clinical logic
│   ├── input_validator.py
│   ├── confidence_threshold.py
│   ├── monitoring_system.py
│   └── production_pipeline.py
├── utils/
│   ├── triage_override.py          # Health score overrides
│   ├── model_calibration.py        # Risk calibration
│   └── spell_corrector.py          # Symptom auto-correction
├── tests/                          # Test suites
├── LICENSE                         # 🔒 PROPRIETARY LICENSE
├── COPYRIGHT.txt                   # Copyright notice
├── REDISTRIBUTION.md               # Copying restrictions
└── README.md                       # This file
```

---

## 🔐 License Information

### License Type
**PROPRIETARY AND CONFIDENTIAL**

### Key Terms
1. **No Duplication** - Source code is protected
2. **No Commercial Use** - Requires written license agreement
3. **No Modification** - Cannot alter or extend without permission
4. **No Distribution** - Cannot share or publish
5. **No Reverse Engineering** - Algorithms are trade secrets

### Penalties for Violation
- Civil damages up to $10,000+
- Legal action and injunctions
- Criminal prosecution possible
- Attorney fees paid by violator

### How to Obtain Permission
```
Contact: [Your Name/Email]
Subject: SmartTriage Dashboard - Licensing Inquiry
Include: Detailed description of intended use
```

**See LICENSE file for complete terms.**

---

## 👨‍💼 Contact & Support

**Project Owner:** NilalThiruvila

**For:**
- **Licensing Inquiries** → Contact owner
- **Commercial Use** → Request licensing agreement
- **Security Issues** → Email [Your Email] (do not publish)
- **Bug Reports** → Submit via proper channels
- **Feature Requests** → Contact owner

---

## 📜 Legal Notices

### Copyright
```
Copyright © 2024-2026 NilalThiruvila
All Rights Reserved
```

### Intellectual Property
- Machine learning models are proprietary
- Risk assessment algorithms are trade secrets
- Source code is fully protected by copyright
- Healthcare data processing methods are confidential

### Usage Acknowledgment
By using this software, you agree to:
- Comply with all license terms
- Not copy or modify the software
- Not distribute to unauthorized parties
- Respect intellectual property rights
- Follow all legal restrictions

---

## 🛡️ Important Warnings

⚠️ **DO NOT:**
- Copy this repository
- Create a fork for public distribution
- Republish the source code
- Reverse engineer the algorithms
- Create competing products
- Use commercially without license

⚠️ **REMEMBER:**
- All violations will be detected
- Legal action will be pursued
- Damages can be substantial
- Criminal penalties possible
- Ignorance of law doesn't excuse violation

---

## 📞 Licensing Inquiries

**Questions about what you can/cannot do?**

Contact the copyright holder:
- Name: NilalThiruvila
- Email: [Your Email]
- Subject: License clarification needed

**Before proceeding, get clear written permission.**

---

## 📝 Additional Resources

- [`LICENSE`](LICENSE) - Full proprietary license agreement
- [`COPYRIGHT.txt`](COPYRIGHT.txt) - Copyright and ownership notice
- [`REDISTRIBUTION.md`](REDISTRIBUTION.md) - Detailed restriction guide
- [`PAIN_DURATION_FIX.md`](PAIN_DURATION_FIX.md) - Technical documentation
- [`INTEGRATION_AUDIT_REPORT.md`](INTEGRATION_AUDIT_REPORT.md) - Security audit

---

## 🎯 Next Steps

1. **Read the LICENSE file** - Understand your rights and restrictions
2. **Request Permission** - If you need to do anything beyond personal use
3. **Deploy Responsibly** - Follow all license terms exactly
4. **Report Issues** - Notify owner of violations or questions

---

**Last Updated:** March 21, 2026
**Status:** PRODUCTION READY
**License:** PROPRIETARY - NOT OPEN SOURCE
**Protection Level:** MAXIMUM (Legal enforcement active)

---

**IMPORTANT:** This README is provided informational only. The LICENSE file is the legally binding document. In case of conflicting information between this README and the LICENSE file, the LICENSE file takes precedence.

⛔ **UNAUTHORIZED COPYING WILL BE DETECTED AND PROSECUTED** ⛔
