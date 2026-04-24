# SmartTriage Dashboard - Real-World Workflow & Role Clarification

## 🏥 Healthcare Hierarchy (Real-World Context)

```
┌─────────────────────────────────────────────────────┐
│         DDHS (Deputy Director of Health)            │ ← District Level
│         - Oversees all PHCs in district             │
│         - Makes policy decisions                     │
│         - Allocates resources & budget              │
│         - Monitors disease surveillance             │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┴──────────────┐
        │                           │
        ▼                           ▼
    ┌──────────┐              ┌──────────┐
    │  PHC #1  │              │  PHC #2  │  ← Facility Level
    │(50 beds) │              │(50 beds) │
    │ 3 Nurses │              │ 2 Nurses │
    │ 2 Doctors│              │ 2 Doctors│
    └────┬─────┘              └────┬─────┘
         │                         │
      1000 patients          1200 patients
```

---

## 🎯 Role Definitions & Real-World Workflows

### 1️⃣ PATIENT Role

**Real-World Scenario:**
> "Mr. Ram has fever for 3 days. He goes to PHC-1. After registration by the nurse, he wants to book an appointment with Dr. Sharma for follow-up."

**What Patients CAN Do:**
1. ✅ **Register** for healthcare at a specific PHC
2. ✅ **Self-Check-in** at PHC via portal
3. ✅ **Book Appointments** with doctors at their PHC
   - System shows available slots
   - Confirms based on doctor's schedule
4. ✅ **View Personal Health Records**
   - Only their own vitals, assessments, history
5. ✅ **Track Appointment Status**
   - Pending → Confirmed → Completed → Reviewed
6. ✅ **Receive Health Reports**
   - Diagnosis from doctor
   - Follow-up instructions
   - Medication details
7. ✅ **Message Doctor**
   - For follow-up questions
   - Not for emergency consultations

**What Patients CANNOT Do:**
- ❌ See other patients' data
- ❌ Modify their own records
- ❌ Cancel appointments (only request)
- ❌ Access facility-wide reports
- ❌ View staff schedules

**Data Access:**
```sql
SELECT * FROM patient_logs WHERE patient_id = CURRENT_USER
SELECT * FROM appointments WHERE patient_id = CURRENT_USER
```

**Journey Map:**
```
Patient Portal
    ↓
1. Register / Sign In
    ↓
2. See PHC Options
    ↓
3. Choose PHC Near Home
    ↓
4. Check-in at PHC (via portal/SMS)
    ↓
5. Nurse Records Vitals (AI Triage)
    ↓
6. Get Risk Score
    ↓
7. Book Doctor Appointment
    ↓
8. Doctor Sees Patient
    ↓
9. Doctor Records Outcome
    ↓
10. Patient Gets Report
```

---

### 2️⃣ PHC NURSE Role

**Real-World Scenario:**
> "Sister Priya works at PHC-1. She's responsible for all patient intakes, vital sign recording, and preliminary triage. She ensures the AI system flags high-risk cases before they see the doctor."

**What PHC Nurses CAN Do:**

#### A. **Patient Registration & Intake** (Primary Role)
1. ✅ **Record Patient Vitals**
   - Blood pressure, temp, pulse, SPO2, respiration
   - Manually enter or scan vitals device
   - Save to patient_logs table

2. ✅ **Conduct AI Triage Assessment**
   - Input symptoms (fever, cough, pain location, duration, severity)
   - System runs 3 AI models in sequence:
     - **XGBoost:** Disease risk prediction
     - **BERT NLP:** Symptom classification
     - **Integrated:** Final risk score (CRITICAL, HIGH, MEDIUM, LOW)
   - Nurse sees risk level immediately

3. ✅ **Triage Decision Making**
   - **CRITICAL (Red)** → Call doctor immediately, escalate
   - **HIGH (Orange)** → See doctor today
   - **MEDIUM (Yellow)** → Routine appointment
   - **LOW (Green)** → Home care advice, follow-up

#### B. **Facility Patient Management**
4. ✅ **Manage All Patients at Their PHC**
   - View patient list (only PHC-1 patients if assigned to PHC-1)
   - Search by name/ID
   - View complete history
   - Track outcomes

5. ✅ **Appointment Coordination**
   - Check doctor availability
   - Block time for urgent cases
   - Reschedule if needed
   - Confirm appointments

6. ✅ **Facility Analytics**
   - See dashboard with:
     - Patients seen today
     - Cases by severity
     - Admission trend (7-day chart)
     - Resource utilization
   - Track KPIs: "200 patients this month, 5% critical"

7. ✅ **Reports Generation**
   - Daily summary: "50 patients, 2 critical, 8 referred"
   - Weekly trends: "Disease pattern shifting from GI to Respiratory"
   - Monthly report to DDHS

#### C. **Patient Communication**
8. ✅ **Message Patients**
   - Send follow-up reminders
   - Share health tips
   - Ask for feedback

9. ✅ **Health Outcomes Recording**
   - Record what happened post-visit
   - Did patient recover? Need referral?
   - Feeds into AI model improvement

**What PHC Nurses CANNOT Do:**
- ❌ Diagnose (that's doctor's role)
- ❌ Prescribe medication
- ❌ See patients from OTHER PHCs
- ❌ Access district-level budget/policies
- ❌ Manage ambulances
- ❌ Reassign staff
- ❌ See other PHCs' analytics

**Data Access:**
```sql
SELECT * FROM patient_logs WHERE phc_id = CURRENT_USER.phc_id
SELECT * FROM appointments WHERE phc_id = CURRENT_USER.phc_id
UPDATE patient_logs WHERE phc_id = CURRENT_USER.phc_id
```

**Database Role:**
- **INSERT:** patient_logs, staff_attendance, messages
- **READ:** appointments, patients, disease_database
- **UPDATE:** patient outcomes only

**Dashboard Should Show:**
```
┌─ SMARTTRIAGE PHC NURSE DASHBOARD ─────────────────┐
│                                                    │
│  PHC-1 "Primary Health Center, Bangalore"         │
│  ┌─ TODAY'S STATS ─────────────────────────────┐  │
│  │ 45 Patients Registered                      │  │
│  │ 8 Critical Cases ⚠️                         │  │
│  │ 12 Pending Appointments                     │  │
│  │ 3 Need Referral                             │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  ┌─ 7-DAY TREND ───────────────────────────────┐  │
│  │ Chart: Admission trend                      │  │
│  │ Mon: 42, Tue: 38, Wed: 51, ...              │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  ┌─ RISK DISTRIBUTION ──────────────────────────┐ │
│  │ Critical: 8   High: 22   Med: 30   Low: 25  │ │
│  │ 📊 Pie Chart showing distribution           │ │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  [Quick Actions]                                  │
│  [+ New Intake] [View Patients] [Reports]         │
└────────────────────────────────────────────────────┘
```

---

### 3️⃣ DOCTOR Role

**Real-World Scenario:**
> "Dr. Sharma works at PHC-1 full-time. He reviews AI-flagged cases, confirms diagnoses, decides treatment, and records outcomes. He also trains the AI by validating assessments."

**What Doctors CAN Do:**

1. ✅ **Review AI-Triaged Patients**
   - See flagged cases from nurse (HIGH/CRITICAL)
   - View:
     - Patient vitals
     - Symptoms entered
     - AI prediction (disease + confidence)
     - Historical health data

2. ✅ **Diagnostic Review**
   - Confirm/override AI prediction
   - Add additional diagnosis
   - Note clinical observations
   - Request lab tests if needed

3. ✅ **Treatment Decision**
   - Prescribe medications
   - Recommend specialists
   - Order referrals
   - Record clinical notes

4. ✅ **Validate AI Predictions** (Model Training)
   - Was AI correct? Yes/No
   - Add feedback to training data
   - Helps system improve over time

5. ✅ **Facility Reports**
   - See what nurse reported
   - Add doctor's notes
   - Confirm outcomes

6. ✅ **Patient Communication**
   - Message patients
   - Share prescriptions
   - Ask follow-up questions

**What Doctors CANNOT Do:**
- ❌ See patients from OTHER PHCs
- ❌ Access district budget/admin
- ❌ Manage staff assignments
- ❌ See DDHS surveillance data
- ❌ Override other doctors' notes

**Data Access:**
```sql
SELECT * FROM patient_logs WHERE phc_id = CURRENT_USER.phc_id
UPDATE appointments WHERE doctor_id = CURRENT_USER.id
INSERT INTO model_monitoring_logs (for training data)
```

**Dashboard Should Show:**
```
┌─ DOCTOR DASHBOARD ─────────────────────────────┐
│                                                │
│ Dr. Sharma - PHC-1                             │
│ ┌─ TODAY'S SCHEDULE ─────────────────────────┐│
│ │ 10:00 AM - Raj (Fever) - AI: HIGH ⚠️      ││
│ │ 10:30 AM - Priya (Cough) - AI: MEDIUM    ││
│ │ 11:00 AM - Arun (Stomach) - AI: LOW      ││
│ │ ...                                        ││
│ └────────────────────────────────────────────┘│
│                                                │
│ ┌─ PENDING VALIDATIONS ──────────────────────┐│
│ │ 5 cases need AI outcome confirmation       ││
│ │ [Review Cases]                             ││
│ └────────────────────────────────────────────┘│
│                                                │
│ [My Patients] [Referrals] [Reports] [Profile] │
└────────────────────────────────────────────────┘
```

---

### 4️⃣ DDHS ADMIN Role (District-Level)

**Real-World Scenario:**
> "Dr. Gupta is Deputy Director of Health Services. He oversees 15 PHCs across the district. He monitors disease trends, allocates ambulances, assigns staff, approves budgets, and reports to state health ministry."

**What DDHS Admin CAN Do:**

#### A. **District Monitoring**
1. ✅ **District Dashboard**
   - Overview of all 15 PHCs
   - Total patients this month: 45,000
   - Disease trends: "GI issues ↑ 23%"
   - Staffing status: "2 PHCs understaffed"
   - Ambulance availability: "12/15 available"

2. ✅ **Disease Surveillance**
   - Real-time disease tracking across district
   - Alert if disease X cases > threshold
   - Example: "COVID suspected cases: 15 this week"
   - Track outbreaks

3. ✅ **Analytics & Reports**
   - Generate monthly district health report
   - Compare PHCs: "PHC-1 efficiency: 94%, PHC-5: 71%"
   - Identify best practices
   - Benchmark performance

#### B. **Resource Management**
4. ✅ **Ambulance Management**
   - Track all ambulances (12 in fleet)
   - Check status: available/allocated/maintenance
   - Assign to emergency cases
   - Track fuel, maintenance schedules

5. ✅ **Staff Assignment & Management**
   - View all staff across district (50+ staff)
   - Assign nurse/doctor to specific PHC
   - Track staff efficiency
   - Handle transfers/promotions
   - Monitor attendance

6. ✅ **Resource Allocation**
   - Allocate PPE, medicines to PHCs
   - Track inventory
   - Request supplies from state
   - Emergency resource redistribution

#### C. **Budget & Planning**
7. ✅ **Budget Management**
   - Allocate annual budget to PHCs
   - Track expenses
   - Approve emergency spending
   - Plan for new equipment

8. ✅ **Health Campaigns**
   - Launch vaccination drives
   - Disease awareness campaigns
   - Track participation

#### D. **Audit & Compliance**
9. ✅ **Complete Audit Log**
   - Who did what, when, why?
   - Track all changes
   - Detect anomalies
   - Compliance reporting

10. ✅ **System Administration**
    - Create new PHC centers
    - Create staff accounts
    - Reset passwords
    - System configuration

**What DDHS Admin CANNOT Do:**
- ❌ Diagnose patients (doctor role)
- ❌ Record vitals (nurse role)
- ❌ See individual patient details directly (privacy)
  - Only aggregated/anonymized district-level data

**Data Access:**
```sql
SELECT * FROM * (ALL TABLES, NO FILTERING)
UPDATE everything
DELETE (if needed for audit)
```

**Dashboard Should Show:**
```
┌─ DDHS ADMIN - DISTRICT DASHBOARD ──────────────────┐
│                                                    │
│ District Health Overview - Bangalore              │
│ ┌─ DISTRICT KPIs ────────────────────────────────┐│
│ │ Total PHCs: 15         Staff: 48                ││
│ │ Total Patients: 45,234 Critical Cases: 234     ││
│ │ Disease Cases (This Week):                     ││
│ │   - Fever: 234    - Cough: 156    - GI: 89    ││
│ └────────────────────────────────────────────────┘│
│                                                    │
│ ┌─ PHC PERFORMANCE RANKING ──────────────────────┐│
│ │ 🥇 PHC-1: 94% efficiency                       ││
│ │ 🥈 PHC-3: 89% efficiency                       ││
│ │ 🥉 PHC-7: 87% efficiency                       ││
│ │ ⚠️  PHC-5: 71% efficiency (NEEDS REVIEW)       ││
│ └────────────────────────────────────────────────┘│
│                                                    │
│ ┌─ AMBULANCE FLEET ──────────────────────────────┐│
│ │ Available: 12  |  Allocated: 1  |  Maintenance: 2││
│ │ [Manage Fleet]                                 ││
│ └────────────────────────────────────────────────┘│
│                                                    │
│ ┌─ STAFF ASSIGNMENTS ────────────────────────────┐│
│ │ 48 Total Staff Assigned                        ││
│ │ Vacant Positions: 2                            ││
│ │ [Manage Staff]                                 ││
│ └────────────────────────────────────────────────┘│
│                                                    │
│ [Centers] [Staff] [Reports] [Budget] [Campaigns]  │
│ [Surveillance] [Ambulances] [Audit] [Settings]    │
└────────────────────────────────────────────────────┘
```

---

## 📊 Comparative Table: Role Differences

| Capability | Patient | PHC Nurse | Doctor | DDHS Admin |
|------------|---------|-----------|--------|-----------|
| **Data Scope** | Own only | PHC facility | PHC facility | All districts |
| **Patient Registration** | Self | ✅ | ✗ | ✗ |
| **Record Vitals** | ✗ | ✅ | View only | ✗ |
| **Run AI Triage** | ✗ | ✅ | ✗ | ✗ |
| **Diagnose** | ✗ | ✗ | ✅ | ✗ |
| **Prescribe** | ✗ | ✗ | ✅ | ✗ |
| **Book Appointments** | ✅ | Manage | Schedule | ✗ |
| **View Reports** | Own | PHC | PHC | District |
| **Access Ambulances** | ✗ | ✗ | Request | ✅ Manage |
| **Manage Staff** | ✗ | ✗ | ✗ | ✅ |
| **Budget Control** | ✗ | ✗ | ✗ | ✅ |
| **Audit Log Access** | ✗ | ✗ | ✗ | ✅ |
| **Disease Surveillance** | ✗ | Facility | ✗ | ✅ District |

---

## 🔄 Data Flow Between Roles

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  1. PATIENT ARRIVES AT PHC-1                               │
│     ↓                                                       │
│  2. NURSE (Sister Priya) RECORDS VITALS & SYMPTOMS        │
│     - Blood pressure, temp, symptoms, duration            │
│     - Enters into SmartTriage system                       │
│     ↓                                                       │
│  3. AI TRIAGE SYSTEM (Backend)                             │
│     - XGBoost model: Predicts disease                      │
│     - BERT NLP: Classifies symptoms                        │
│     - Integrated: Generates risk score                     │
│     ↓                                                       │
│  4. NURSE SEES RISK SCORE ON DASHBOARD                    │
│     - "CRITICAL" or "HIGH" → Call doctor immediately     │
│     - "MEDIUM" → Routine appointment                      │
│     ↓                                                       │
│  5. PATIENT BOOKS APPOINTMENT WITH DOCTOR                 │
│     (or nurse fast-tracks critical case)                  │
│     ↓                                                       │
│  6. DOCTOR (Dr. Sharma) REVIEWS PATIENT                   │
│     - Sees nurse's intake notes                           │
│     - Sees AI prediction with confidence                  │
│     - Performs clinical examination                       │
│     ↓                                                       │
│  7. DOCTOR MAKES FINAL DIAGNOSIS & TREATMENT              │
│     - Confirms or overrides AI prediction                 │
│     - Prescribes treatment                                │
│     - Records outcome                                     │
│     ↓                                                       │
│  8. PATIENT RECEIVES HEALTH REPORT                        │
│     - Prescription & follow-up instructions               │
│     - Can view report in portal                           │
│     ↓                                                       │
│  9. DATA FLOWS TO DDHS ADMIN DASHBOARD                   │
│     - Aggregated statistics only (privacy)                │
│     - Disease surveillance update                         │
│     - Performance metrics to district report              │
│     ↓                                                       │
│  10. DDHS ADMIN USES DATA FOR DISTRICT PLANNING            │
│     - Allocates resources                                 │
│     - Makes health policy decisions                       │
│     - Reports to state health ministry                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Data Each Role Needs From Each Other

### Patient ← Nurse
- ✅ Appointment confirmation
- ✅ Health report
- ✅ Follow-up instructions

### Nurse ← Patient
- ✅ Health history
- ✅ Current symptoms
- ✅ Appointment preferences

### Doctor ← Nurse
- ✅ Patient vitals
- ✅ Symptoms entered
- ✅ AI triage result
- ✅ Patient priority (CRITICAL/HIGH/etc)

### Nurse ← Doctor
- ✅ Final diagnosis
- ✅ Treatment prescribed
- ✅ Follow-up schedule
- ✅ Referral (if needed)

### DDHS Admin ← PHC Nurse & Doctor
- ✅ Daily/weekly aggregate statistics
- ✅ Disease surveillance alerts
- ✅ Resource utilization data
- ✅ Performance metrics
- ✅ Incident reports

### PHC Nurse & Doctor ← DDHS Admin
- ✅ Staff assignments
- ✅ Resource allocations
- ✅ Policy updates
- ✅ Emergency protocols
- ✅ Ambulance availability

---

## 🎯 Key Principles

1. **Role Isolation**: Each role sees only data needed for their job
2. **Hierarchy**: DDHS > PHC > Patient (in terms of data access)
3. **Privacy**: Patient data aggregated before reaching district level
4. **Efficiency**: AI pre-screens before doctor consultation
5. **Accountability**: All actions audited and logged
6. **Feedback**: Doctor validates AI for continuous improvement

---

## ✅ Testing Scenarios

### Scenario 1: Patient with Fever
```
Patient: "I have fever for 3 days"
Nurse: Records 101.5°F, duration 3 days, headache
AI: XGBoost=Malaria(65%), BERT=Viral(78%), Risk=HIGH
Nurse: "Doctor will see you now (HIGH priority)"
Doctor: "Confirm Viral Fever, Prescribe: Paracetamol"
Patient: Receives prescription via portal
DDHS: Sees "Viral cases +1" in district surveillance
```

### Scenario 2: Ambulance Emergency
```
Doctor: "Patient needs referral to hospital"
Nurse: Requests ambulance via DDHS system
DDHS Admin: Sees request, allocates nearest ambulance
System: Updates ambulance GPS, sends to PHC
Patient: Transported safely to hospital
DDHS: Logs ambulance usage for audit
```

### Scenario 3: District Health Planning
```
DDHS: "Disease distribution shows GI cases ↑ 30%"
Action: Allocate more ORS packets to PHCs
Decision: Launch water sanitation campaign
Measure: Track campaign effectiveness next month
Result: Reduction in GI cases week-on-week
```

---

## 🔗 System Interconnection Map

```
                    ┌─ Database ─┐
                    │ (SQLite)   │
                    └─────┬──────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
    ┌────────────┐   ┌────────────┐   ┌────────────┐
    │  Patient   │   │ PHC Nurse  │   │  Doctor    │
    │ Portal     │ ←→│ Dashboard  │ ←→│ Dashboard  │
    └────────────┘   └────────────┘   └────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                    ┌─────▼──────┐
                    │ DDHS Admin │
                    │ Dashboard  │
                    │ (Reports & │
                    │ Analytics) │
                    └────────────┘
```

---

This clarifies the entire system! Each role has a **distinct purpose** and **data isolation** ensures privacy and efficiency.
