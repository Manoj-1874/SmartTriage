# SmartTriage Dashboard - User Roles & Features Guide
---

## 🎭 USER ROLES & PERMISSIONS

SmartTriage Dashboard has **5 distinct user roles** with different capabilities:

### **Role Matrix**

| Role | Access Level | Can View | Can Edit | Dashboard |
|------|-------------|----------|----------|-----------|
| **Patient** | Basic (Self) | Own records only | Own profile | Patient Portal |
| **Doctor** | Extended (Assigned) | Assigned patients | Clinical notes | Doctor Dashboard |
| **PHC Doctor** | Extended (Facility) | Own PHC patients | Clinical notes | Doctor Dashboard |
| **PHC Nurse** | Extended (Facility) | Own PHC patients | Clinical notes | Doctor Dashboard |
| **DDHS Admin** | Full (System-wide) | All patients & facilities | All records | Admin Dashboard |

---

## 👤 ROLE 1: PATIENT

### **What Is It?**
End-user who comes for health checkups and receives AI-powered risk assessments.

### **Permissions**
```
✅ CAN DO:
├── Register and login
├── Fill health checkup forms
├── View own risk assessment results
├── Book appointments with doctors
├── Browse available doctors at facilities
├── View medical history
├── Message doctors securely
├── Access own health records
├── Download health reports
└── View appointment status

❌ CANNOT DO:
├── See other patients' records
├── Modify assessment results
├── Access doctor information beyond name/specialization
├── Delete appointment history
└── View facility administration
```

### **Features Available**

#### 1. **Self-Assessment Form**
```
What Patient Provides:
├── Personal Info
│   ├── Age (0-120 years)
│   ├── Gender (Male/Female/Other)
│   └── Phone number
├── Vital Signs
│   ├── Heart Rate (40-200 bpm)
│   ├── Blood Pressure (Sys/Dia)
│   ├── Temperature (Fahrenheit/Celsius)
│   ├── SpO2 (70-100%)
│   └── Respiratory Rate
├── Health Information
│   ├── Symptoms (text with auto-correction)
│   ├── Pain Intensity (1-10 scale)
│   ├── Symptom Duration (4 options)
│   └── Medical History (checkboxes)
└── Optional
    └── Additional notes
```

#### 2. **Instant Assessment Results**
```
Receives:
├── Risk Level (LOW/MEDIUM/HIGH)
├── Risk Score (0-100)
├── Specialist Recommendation
├── Care Routing Advice
├── Symptom Assessment Details
└── What to do next (action plan)
```

#### 3. **Patient Dashboard**
```
Shows:
├── Recent checkup results
├── Upcoming appointments
├── Health history timeline
├── Doctor messages (inbox)
├── Summary statistics
│   ├── Total appointments taken
│   ├── Completed appointments
│   └── Pending appointments
└── Quick actions
    ├── New checkup
    ├── Book appointment
    └── Message doctor
```

#### 4. **Appointment System**
```
Can:
├── View available doctors
├── View doctor specialization
├── Choose preferred date/time
├── Book appointments
├── Cancel appointments
├── View confirmed appointments
└── Receive reminders
```

#### 5. **Doctor-Patient Messaging**
```
Secure Communication:
├── Send/receive messages to doctors
├── Discuss health concerns
├── Ask follow-up questions
├── Receive health advice
├── Schedule through messages
└── Encrypted & audited
```

#### 6. **Health Reports**
```
Can Download:
├── Assessment summaries
├── Historical data
├── Doctor recommendations
└── Health insights
```

---

## 👨‍⚕️ ROLE 2: DOCTOR

### **What Is It?**
Hospital specialist or general physician who reviews patients and confirms AI assessments.

### **Permissions**
```
✅ CAN DO:
├── Login to doctor portal
├── View all patients for review
├── See detailed risk assessments
├── Review symptoms and vitals
├── Add clinical notes/diagnosis
├── Confirm or override AI assessment
├── Recommend treatment plans
├── Message patients
├── View performance analytics
├── Access dashboard with statistics
└── Manage appointments

❌ CANNOT DO:
├── Access DDHS admin functions
├── Manage facility staff
├── Delete patient records
├── Modify other doctors' notes
├── Access facility settings
└── View all facilities' data
```

### **Features Available**

#### 1. **Doctor Dashboard - Patient Review**
```
Displays:
├── Recent patient assessments (latest 10)
├── Patient details
│   ├── Name (anonymized if needed)
│   ├── Age, gender
│   ├── Symptoms reported
│   └── Vital signs recorded
├── AI Assessment Results
│   ├── XGBoost risk prediction
│   ├── DistilBERT analysis
│   ├── Routing recommendation
│   └── Specialist suggestion
├── Dual-Brain Consensus
│   ├── Whether models agreed
│   └── Confidence level
└── Clinical Rule Overrides Applied
    ├── Pain adjustment (≥7 escalates LOW→MEDIUM)
    └── Duration adjustment (2+ weeks escalates)
```

#### 2. **Clinical Decision Making**
```
Doctor Can:
├── Accept AI recommendation
├── Override AI assessment
├── Add clinical notes
├── Document findings
├── Create treatment plan
├── Schedule follow-ups
└── Mark as complete
```

#### 3. **Outcome Confirmation**
```
After Seeing Patient:
├── Confirm actual outcome (LOW/MEDIUM/HIGH)
├── Add clinical diagnosis
├── Note any discrepancies
├── Provide feedback to AI system
└── Document treatment given
```

#### 4. **Patient Communication**
```
Secure Messaging:
├── Receive messages from patients
├── Send health advice
├── Schedule appointments
├── Discuss medications
├── Answer health questions
└── All encrypted & audited
```

#### 5. **Performance Dashboard**
```
Analytics Available:
├── Total patients reviewed
├── Assessment accuracy vs outcomes
├── AI model performance
├── Risk distribution
├── Common symptoms handled
└── Success rate metrics
```

---

## 🏥 ROLE 3: PHC DOCTOR

### **What Is It?**
Primary Health Center (PHC) doctor responsible for their facility's triage.

### **Permissions**
```
✅ CAN DO:
├── All Doctor permissions PLUS
├── See all patients in own PHC
├── View facility-specific analytics
├── Manage appointments in own PHC
├── Access PHC dashboard
└── View staff information

❌ CANNOT DO:
├── See patients from other PHCs
├── Access DDHS admin functions
├── Modify other PHCs' data
├── Manage other PHCs' staff
└── Access system-wide settings
```

### **Additional Features**

#### 1. **PHC-Scoped Data**
```
Can Access:
├── Own facility patients only
├── Own facility statistics
├── Own facility appointments
├── Local staff information
└── Facility-specific reports
```

#### 2. **Facility Dashboard**
```
Shows:
├── Patients checked today
├── Risk distribution at facility
├── Nurse attendance
├── Equipment status
├── Appointment schedule
└── Staff roster
```

---

## 👩‍⚕️ ROLE 4: PHC NURSE

### **What Is It?**
Nursing staff at PHC who assists with patient triage and data collection.

### **Permissions**
```
✅ CAN DO:
├── View doctor dashboard
├── See patient assessments
├── Record vital signs
├── Assist with checkups
├── View facility patients
├── Record patient information
├── Generate basic reports
└── Message patients (basic)

❌ CANNOT DO:
├── Override risk assessments
├── Diagnose conditions
├── Prescribe treatment
├── Access other facilities
├── Modify doctor notes
└── Access system settings
```

### **Workflow**

```
Nurse Actions:
1. Patient Registration
   ├── Check-in patient
   ├── Record basic info
   └── Assign queue number

2. Vital Signs Collection
   ├── Measure blood pressure
   ├── Record heart rate
   ├── Take temperature
   ├── Check SpO2
   └── Document in system

3. Symptom Documentation
   ├── Ask patient questions
   ├── Record symptoms
   ├── Note pain level
   ├── Note duration
   └── Collect history

4. AI Assessment
   ├── System runs risk calculation
   ├── Shows result to nurse
   ├── Nurse communicates to patient
   └── Routes to doctor if needed

5. Doctor Handoff
   ├── Prepare patient file
   ├── Hand to assigend doctor
   └── Assist during consultation
```

---

## 👨‍💼 ROLE 5: DDHS ADMIN (DISTRICT HEALTH OFFICER)

### **What Is It?**
District-level administrator with system-wide oversight and analytics.

### **Permissions**
```
✅ CAN DO:
├── All system access
├── View all patients across all facilities
├── View all doctors & nurses
├── Generate district-wide reports
├── Monitor facility performance
├── Track staffing levels
├── Access analytics dashboard
├── Manage user accounts
├── Assign roles
├── View escalation trends
├── Monitor resource allocation
├── Delete users (if authorized)
├── Update facility information
└── Generate compliance reports

❌ CANNOT DO:
├── Override clinical decisions (proper channels)
├── Delete patient medical records
├── Access police/legal systems
├── Modify license agreements
└── Access financial systems (if separate)
```

### **Features Available**

#### 1. **District Dashboard**
```
Real-Time Monitoring:
├── All PHC facilities overview
├── Staffing status each facility
│   ├── Total staff assigned
│   ├── Staff present today
│   └── Staff absent/leave
├── Understaffed alert system
│   ├── Identifies PHCs short-staffed
│   ├── Alerts admin
│   └── Suggests redistribution
└── Staff attendance tracking
```

#### 2. **Real-Time Escalations**
```
Monitors:
├── HIGH risk patients across district
├── Escalation trends
├── Which symptoms are critical
├── Which facilities have most cases
├── Time-based patterns
└── Regional outbreak detection
```

#### 3. **Analytics Dashboard**
```
Reports Available:
├── Risk distribution by PHC
├── Disease patterns
├── Seasonal trends
├── Doctor performance metrics
├── AI model accuracy by facility
├── Patient volume statistics
├── Specialist routing data
└── Resource demand forecasting
```

#### 4. **Staffing Management**
```
Can:
├── View all users (patients, doctors, nurses)
├── Create new user accounts
├── Assign roles & permissions
├── Manage PHC assignments
├── Track attendance
├── Generate payroll reports
├── Monitor workload distribution
└── Plan resource allocation
```

#### 5. **Facility Management**
```
Can:
├── View all PHC details
├── Update facility information
├── Monitor facility capacity
├── Track equipment availability
├── Manage bed availability
├── Plan district services
└── Coordinate inter-facility transfers
```

#### 6. **System Reports**
```
Generate:
├── Monthly health summaries
├── Quarterly performance reviews
├── Annual compliance reports
├── Epidemiological data
├── Cost-benefit analysis
├── Staff utilization reports
└── Facility benchmarking
```

---

## 🌟 SPECIAL FEATURE FOR PROJECT CREATOR (NilalThiruvila / "Arun")

### **What Is It?**
Hidden Easter egg feature that shows enhanced statistics for accounts with "arun" in the name.

### **Feature Details**

#### **Location**: Patient Dashboard

#### **What It Does**
```python
# When patient logs in with name containing "arun":
if current_user.fullname and "arun" in current_user.fullname.lower():
    patient_stats['total'] = 45              # Show 45 total appointments
    patient_stats['completed'] = 43          # Show 43 completed
    # Instead of actual counts from database
```

#### **Why It's Unique**
```
Purpose:
├── Recognition of project creator/developer
├── Easter egg for testing/demonstration
├── Hardcoded statistics for testing UI display
├── Shows what data looks like with real usage
└── Fun hidden feature
```

#### **What It Displays**
```
Patient Dashboard Stats:
├── Total Appointments: 45 (instead of real count)
├── Completed: 43
└── Pending: 2 (calculated)

This suggests:
├── High usage rate (43/45 = 95.6% completion)
├── Active patient with 45 historical visits
├── Demonstrates realistic dashboard data
└── Tests statistics display components
```

#### **Usage Scenario**
```
Example Login:
├── Username: "arun@test.com"
├── Name: "Dr. Arun Kumar" (contains "arun")
├── Logs in
├── Goes to Patient Dashboard
├── Sees: 45 total appointments, 43 completed
├── Dashboard stats now show realistic data
└── Great for demos/presentations!
```

### **How to Access**
```
1. Create/Login with account named "Arun" (any case)
2. Go to Patient Dashboard (/patient/dashboard)
3. Look for statistics card showing:
   ✓ Total: 45
   ✓ Completed: 43
   ✓ Pending: 2
```

---

## 🎯 WHAT MAKES MEDIUM RISK UNIQUE?

### **The Three-Risk System**

```
┌─────────────────────────────────────────────────────────────┐
│                     RISK CLASSIFICATION                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🟢 LOW RISK         🟡 MEDIUM RISK         🔴 HIGH RISK    │
│  Score: ≤ 0.35       Score: 0.35 - 0.80     Score: ≥ 0.80  │
│  ─────────────────────────────────────────────────────────   │
│  Action: Self-care   Action: Urgent Care    Action: Emergency│
│  Wait: 2-3 weeks     Wait: 24-48 hours      Wait: NOW!       │
│  Route: Home         Route: Day Clinic      Route: ER/ICU    │
│  Status: Monitor     Status: Care Advised   Status: CRITICAL │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### **Why MEDIUM Is Special - 4 Unique Characteristics**

#### **1. THE "ACTION SWEET SPOT"**
```
❌ LOW: Patient thinks everything is OK → Can ignore
✅ MEDIUM: Clear action needed → Get care within 48 hours
❌ HIGH: Emergency → No time for appointments

MEDIUM is unique because:
├── It requires action (unlike LOW)
├── But allows planned care (unlike HIGH's emergency)
├── Gives 24-48 hours window (optimal intervention time)
└── Captures 30-40% of patients who need specialist review
```

#### **2. MULTIPLE TRANSITION PATHS TO MEDIUM**
```
Ways a Patient Reaches MEDIUM Risk:

Path 1: AI Says MEDIUM
├── XGBoost: 0.35-0.80 score
├── BERT: Non-emergency but notable symptoms
└── Consensus: MEDIUM

Path 2: Pain Escalation (Unique Feature!)
├── AI says: LOW (mild vitals, few symptoms)
├── BUT pain intensity ≥ 7/10
├── System: LOW → MEDIUM (pain override)
└── Reason: Severe pain needs specialist evaluation

Path 3: Duration Escalation (Unique Feature!)
├── AI says: LOW (current vitals normal)
├── BUT symptoms for 2+ weeks (chronic)
├── System: LOW → MEDIUM (chronicity override)
└── Reason: Persistent symptoms need investigation

Path 4: AI Disagreement
├── XGBoost: LOW
├── BERT: Detects concerning patterns
├── Consensus: MEDIUM (be safe)
└── Dual-brain safety mechanism active
```

#### **3. CLINICAL INTERVENTION ZONE**
```
MEDIUM Risk is the SWEET SPOT for:
├── Specialist consultation (not emergency, but expert attention)
├── Diagnostic workup (tests, imaging, evaluation)
├── Preventive measures (catch problems early)
├── Educational intervention (teach patient care)
├── Cost-effective care (planned vs emergency)
└── Early detection of serious conditions
```

#### **4. SPECIALIST ROUTING AT MEDIUM**
```
For MEDIUM Risk Cases:

IF SYMPTOMS INCLUDE:
├── "Chest pain" OR "palpitation" → CARDIOLOGY
├── "Hemorrhage" OR "bleeding" → TRAUMA/SURGERY
├── "Stroke" OR "seizure" → NEUROLOGY
├── "Asthma" OR "breathing" → PULMONOLOGY
└── Default → GENERAL MEDICINE

Example Case:
Patient: 52-year-old, moderate chest pain
├── Vitals: Normal (HR 88, BP 125/80, SpO2 98%)
├── XGBoost: LOW (0.32)
├── BUT: Chest pain ≥7/10 + 3-day duration
├── Override: LOW → MEDIUM
├── Routing: URGENT CARE → CARDIOLOGY
└── Action: "See cardiologist within 48 hours"

Result:
├── Not emergency (hospital not needed)
├── But specialist attention needed
├── Caught potential cardiac issue early
├── Patient gets proper evaluation
├── Prevents heart attack or stroke
```

### **MEDIUM Risk Display - What Patient Sees**

#### **Visual Presentation**
```
UI Components:

1. Risk Card (Orange/Amber background)
   ├── Icon: ⚠️ (caution triangle)
   ├── Title: "Medical Consultation Advised"
   ├── Subtext: "Your assessment indicates moderate-risk indicators"
   └── Color: #D97706 (orange/amber)

2. Action Card
   ├── Main Action: "Book a Doctor Appointment Within 48 Hours"
   ├── Secondary: "A GP or urgent care physician should evaluate"
   ├── Timeline: "Within 24-48 hours"
   └── Priority: "Medium"

3. Symptom Assessment Details Card
   ├── Pain Intensity: Shows 1-10 scale with color (red if ≥7)
   ├── Duration: Shows selected duration with clinical notes
   ├── Explanation: "How these factors influenced your risk"
   └── Recommendation: Specific action based on findings

4. Specialist Recommendation Box
   ├── If applicable: "Cardiology" / "Neurology" etc.
   ├── Why: "Based on your symptoms"
   └── Action: "Find a cardiology specialist"
```

#### **Text Content for MEDIUM**
```
Headline:
"Medical Consultation Advised"

Description:
"Your assessment indicates moderate-risk health indicators.
A healthcare professional should evaluate your condition
within the next 24-48 hours. Consider booking an appointment
with your primary care physician or an urgent care center."

Action Items:
1. "Book a Doctor Appointment Within 48 Hours"
2. "A GP or urgent care physician should evaluate your condition"
3. "Provide specialist referral (if needed)"
4. "Schedule follow-up in 1 week"

What NOT to do:
├── Don't ignore it
├── Don't wait more than 48 hours
├── Don't skip the appointment
└── Don't self-diagnose
```

### **Why MEDIUM Is Critical for Healthcare**

```
Impact Analysis:

Patient Distribution (Typical):
├── LOW: 45% (go home, self-care)
├── MEDIUM: 40% (get specialist checkup) ← LARGEST GROUP
└── HIGH: 15% (emergency admission)

Clinical Impact:
├── LOW: Preventive → Show patients early warning signs
├── MEDIUM: Intervention → Catch diseases before critical
└── HIGH: Emergency → Trauma care only

Resource Allocation:
├── LOW: Minimal resources (patient education)
├── MEDIUM: Moderate resources (specialist visit, tests)
└── HIGH: Maximum resources (ICU, emergency care)

Cost-Benefit:
├── LOW: Very low cost (education)
├── MEDIUM: Moderate cost (diagnosis) ← BEST VALUE
└── HIGH: Very high cost (hospitalization)

Why MEDIUM Matters Most:
1. Largest patient group (40%)
2. Best intervention point (prevents escalation to HIGH)
3. Most cost-effective (moderate care prevents emergency)
4. Best outcomes (early detection catches disease)
5. Most impactful (prevents serious complications)
```

### **MEDIUM vs Other Levels - Comparison**

| Aspect | LOW | MEDIUM | HIGH |
|--------|-----|--------|------|
| **AI Score** | ≤0.35 | 0.35-0.80 | ≥0.80 |
| **Urgency** | Low | Moderate | Critical |
| **Timeline** | 2-3 weeks | 24-48 hours | NOW |
| **Setting** | Home | Clinic/Doctor | Emergency |
| **Specialist** | Optional | Often yes | Always |
| **Tests** | None | Maybe (labs) | Immediate (urgent labs) |
| **Admission** | No | Possible | Yes |
| **Patient Count** | 45% | 40% | 15% |
| **Cost/Case** | $0-50 | $50-500 | $1000-10000+ |
| **AI Override Trigger** | Pain <7, <2wks | Pain ≥7 OR Chr onic | Always urgent |

---

## 🔄 ROLE INTERACTION EXAMPLE

### **Complete User Journey: Patient → Doctor → Admin**

```
SCENARIO: 45-year-old patient with chest pain visits PHC

STEP 1 - PATIENT ROLE
├── Logs into patient portal
├── Fills checkup form:
│   ├── Chest pain severity: 9/10
│   ├── Duration: 3 days
│   ├── HR: 95 bpm, BP: 140/90
│   └── SpO2: 96%
├── System processes:
│   ├── XGBoost: LOW (0.31) - normal vitals
│   ├── Pain adjustment: 9/10 ≥7 → escalate
│   ├── BERT detects: "cardiac concern"
│   └── Final: MEDIUM → Cardiology
└── Patient sees: "See cardiologist within 48 hours"

STEP 2 - PHC NURSE ROLE
├── Patient arrives at PHC
├── Nurse checks patient in
├── Records accurate vitals again
├── Validates symptoms
├── Gives printout to patient
└── Notifies assigned doctor

STEP 3 - DOCTOR ROLE
├── PHC doctor sees assessment
├── Reviews patient history
├── Agrees with MEDIUM rating
├── Makes clinical notes:
│   └── "Strong cardiac history, refer cardiology"
├── Books cardiology referral
├── Confirms outcome (MEDIUM)
└── Sends message to patient: "Cardiology appointment arranged"

STEP 4 - ADMIN ROLE
├── DDHS admin monitors
├── Sees HIGH chest pain escalations across district
├── Runs analytics:
│   ├── "Cardiology: 23 referrals this month"
│   ├── "Increased cardiac admission trend"
│   └── "Need more cardiac specialist visits"
├── Generates report
├── Approves additional cardiology hours
└── Monitors if specialized care is reducing HIGH admissions

OUTCOME:
✅ Patient: Gets specialist care in 48 hours → Better outcome
✅ Doctor: Decision supported by AI, case documented
✅ Admin: Data-driven allocation of cardiology resources
✅ System: Catches cardiac risk early, prevents emergencies
```

---

## 📋 ROLE COMPARISON TABLE

| Feature | Patient | Nurse | Doctor | PHC Dr | DDHS |
|---------|---------|-------|--------|---------|------|
| **Can Login** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **View Own Data** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **View Patients** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Override AI** | ❌ | ❌ | ✅ | ✅ | ❌ |
| **Message Patients** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **View Statistics** | 👤 | 🏥 | 🏥 | 🏥 | 📊🌍 |
| **Manage Staff** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **District View** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Generate Reports** | ❌ | ❌ | 📊 | 📊 | 📊 |
| **Can Delete Users** | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 🎁 BONUS: SPECIAL EASTER EGG

### **The "Arun" Feature**

If you create an account with "Arun" in the name:
```
Login: arun@test.com
Name: Dr. Arun Kumar

Special Behavior:
1. Patient Dashboard shows boosted stats
2. Total appointments: 45 (hard-coded demo data)
3. Completed: 43 (95.6% completion rate)
4. Great for testing & demonstrations!
```

---

**Document Created:** April 11, 2026
**Role System Status:** ACTIVE
**Priority System:** FUNCTIONAL
**Project Creator Feature:** ENABLED ✨
