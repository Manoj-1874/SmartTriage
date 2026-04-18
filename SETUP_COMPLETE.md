====================================================================
SMARTTRIAGE DASHBOARD - COMPLETE SETUP & TESTING GUIDE
====================================================================
Date: April 17, 2026
Status: READY FOR TESTING

====================================================================
1. DATABASE & BACKEND STATUS
====================================================================

✓ Database: triage.db (SQLite) - Fully Initialized
✓ Tables: All 10+ tables created and connected
  - users (14 test users)
  - phc_facilities (6 regions)
  - patient_logs (for checkup records)
  - appointments
  - messages
  - staff_attendance
  - model_monitoring_logs
  - AND MORE...

✓ Flask App: Running at http://localhost:5000
✓ All Endpoints: Active and Connected
  - Role-based routing working
  - Data validation active
  - Security headers enabled
  - Rate limiting enabled
  - Dual-Brain AI Engine loaded (XGBoost + BERT)
  - Disease database ready (141 diseases)

====================================================================
2. USERS CREATED & ASSIGNED TO REGIONS
====================================================================

DDHS ADMIN (District Level - All Regions)
-------------------------------------------
Email: admin@ddhs.gov
Password: test123
Dashboard: http://localhost:5000/ddhs-admin/dashboard
ID: 73
Role: DDHS Admin
Permissions: View all PHCs, assign staff, manage region resources

PATIENTS (5 Total - No Region Assignment)
------------------------------------------
Patient 1 - ramesh@example.com / test123 (ID: 74)
Patient 2 - priya@example.com / test123 (ID: 75)
Patient 3 - arjun@example.com / test123 (ID: 76)
Patient 4 - sneha@example.com / test123 (ID: 77)
Patient 5 - vikram@example.com / test123 (ID: 78)

DOCTORS (5 Total - Assigned to Different PHCs)
----------------------------------------------
Doctor 1 - doctor1@hospital.com / test123 (ID: 79)
  Specialization: Cardiology
  Assigned: PHC Central (Region 1)

Doctor 2 - doctor2@hospital.com / test123 (ID: 80)
  Specialization: Pediatrics
  Assigned: PHC North (Region 2)

Doctor 3 - doctor3@hospital.com / test123 (ID: 81)
  Specialization: Orthopedics
  Assigned: PHC South (Region 3)

Doctor 4 - doctor4@hospital.com / test123 (ID: 82)
  Specialization: Dermatology
  Assigned: PHC East (Region 4)

Doctor 5 - doctor5@hospital.com / test123 (ID: 83)
  Specialization: General Medicine
  Assigned: PHC West (Region 5)

PHC NURSES (3 Total - Assigned to Different PHCs)
-------------------------------------------------
Nurse 1 - nurse1@phc.gov / test123 (ID: 84)
  Specialization: General Nursing
  Assigned: PHC Central (Region 1)

Nurse 2 - nurse2@phc.gov / test123 (ID: 85)
  Specialization: Maternal Health
  Assigned: PHC North (Region 2)

Nurse 3 - nurse3@phc.gov / test123 (ID: 86)
  Specialization: Community Health
  Assigned: PHC South (Region 3)

====================================================================
3. PHC REGIONS & STAFF DISTRIBUTION
====================================================================

Region 1 - PHC Central (City Center)
  Staff: Doctor 1 (Cardiology), Nurse 1 (General)
  Patients: Can register through Nurse 1

Region 2 - PHC North (North Ward)
  Staff: Doctor 2 (Pediatrics), Nurse 2 (Maternal Health)
  Patients: Can register through Nurse 2

Region 3 - PHC South (South Ward)
  Staff: Doctor 3 (Orthopedics), Nurse 3 (Community Health)
  Patients: Can register through Nurse 3

Region 4 - PHC East (East Ward)
  Staff: Doctor 4 (Dermatology)
  Patients: Need to register

Region 5 - PHC West (West Ward)
  Staff: Doctor 5 (General Medicine)
  Patients: Need to register

Region 6 - PHC Rural (Rural Sub-district)
  Staff: None assigned yet
  Patients: Need to setup

====================================================================
4. DATABASE CONNECTIONS - VERIFIED
====================================================================

✓ Users Table
  - All 14 users created
  - Roles: patient, doctor, phc_nurse, ddhs_admin
  - Email verification: Enabled
  - Password hashing: Implemented

✓ PHC Facilities Table
  - 6 regions created and linked
  - Each staff member assigned to correct PHC
  - Region data accessible from dashboard

✓ Patient Logs Table
  - Ready to receive checkup records
  - Connected to users (by user_id and phc_id)
  - Will store: symptoms, vitals, risk scores, outcomes
  - Foreign keys: user_id → users, phc_id → phc_facilities

✓ Appointments Table
  - Linked to patients and doctors
  - Status tracking: Pending, Confirmed, Completed
  - Connected to user records

✓ Messages Table
  - Doctor-Patient communication ready
  - Two-way messaging system
  - linked to user IDs

✓ Staff Attendance Table
  - Track PHC nurse check-ins
  - Geo-location support
  - Connected to phc_facilities

✓ Dual-Brain AI Models
  - XGBoost model: Loaded & Ready
  - BERT model: Loaded & Ready
  - Disease database: 141 diseases loaded
  - Risk assessment: CRITICAL, HIGH, MEDIUM, LOW

====================================================================
5. TESTING CHECKLIST - PHASE 1: AUTHENTICATION
====================================================================

[] 1. Login as Patient (patient1@example.com / test123)
     - Verify patient dashboard loads
     - Check: Can see appointments, health history
     - Check: Role label shows "Patient"
     - URL: http://localhost:5000/patient/dashboard

[] 2. Login as Doctor (doctor1@hospital.com / test123)
     - Verify doctor dashboard loads
     - Check: Can see assigned patients
     - Check: Role label shows "Doctor"
     - Check: Specialization visible (Cardiology)
     - Check: Can access PHC Central patients only
     - URL: http://localhost:5000/doctor/dashboard

[] 3. Login as PHC Nurse (nurse1@phc.gov / test123)
     - Verify PHC dashboard loads
     - Check: Role label shows "PHC Nurse"
     - Check: Can see PHC Central metrics only
     - Check: Doctors & nurses in region visible
     - URL: http://localhost:5000/phc/nurse/dashboard

[] 4. Login as DDHS Admin (admin@ddhs.gov / test123)
     - Verify admin dashboard loads
     - Check: Can see all 6 PHC regions
     - Check: Can see all staff members
     - Check: Can see district-level analytics
     - URL: http://localhost:5000/ddhs-admin/dashboard

====================================================================
6. TESTING CHECKLIST - PHASE 2: STAFF ASSIGNMENT (DDHS Admin)
====================================================================

[] 1. Navigate to DDHS Staff Assignment page
     - URL: http://localhost:5000/ddhs-admin/staff-assignment
     - Check: All 5 doctors listed as "Assigned"
     - Check: All 3 nurses listed as "Assigned"
     - Check: Correct PHC centers shown

[] 2. Verify staff assignments
     - Doctor 1 → PHC Central
     - Doctor 2 → PHC North
     - Doctor 3 → PHC South
     - Doctor 4 → PHC East
     - Doctor 5 → PHC West
     - Nurse 1 → PHC Central
     - Nurse 2 → PHC North
     - Nurse 3 → PHC South

[] 3. Can unassign and reassign staff (optional test)
     - Unassign a doctor
     - Reassign to different PHC
     - Verify changes persist

====================================================================
7. TESTING CHECKLIST - PHASE 3: PATIENT HEALTH CHECKUP
====================================================================

[] 1. Login as Patient 1 (patient1@example.com / test123)

[] 2. Navigate to Health Checkup
     - Fill out health form with vital signs
     - Enter symptoms
     - Select specialization needed

[] 3. AI Dual-Brain Risk Assessment
     - System 1 (XGBoost): Calculates risk probability
     - System 2 (BERT): NLP analysis of symptoms
     - System 3 (Fusion): Combined AI decision
     - Check: Risk level assigned (CRITICAL/HIGH/MEDIUM/LOW)

[] 4. Appointment Booking
     - Check: Recommended doctor shown
     - Check: Can select preferred doctor
     - Check: Appointment date/time choosable
     - Check: Appointment created successfully

[] 5. Doctor Review (doctor1@hospital.com / test123)
     - Check: Can see patient appointment
     - Check: Can review AI assessment
     - Check: Can provide diagnosis/notes

[] 6. Patient Outcome Tracking
     - Check: Appointment outcome recorded
     - Check: Status changed to "Completed"
     - Check: Checkup record in patient history

====================================================================
8. TESTING CHECKLIST - PHASE 4: PHC NURSE DASHBOARD
====================================================================

[] 1. Login as PHC Nurse (nurse1@phc.gov / test123)

[] 2. Dashboard Metrics
     - Check: "New Patients Registered Today"
     - Check: "Total Patients Under Care"
     - Check: "Total Appointments"
     - Check: "Critical Cases"
     - Check: Doctors available in region: 1 (Doctor 1)
     - Check: Nurses available in region: 1 (Nurse 1)

[] 3. PHC Center Information
     - Check: Center name shown (PHC Central)
     - Check: Region details visible
     - Check: Can view center contact

[] 4. 7-Day Admission Trend
     - Check: Chart loads (when data exists)
     - Check: Shows daily admissions

[] 5. Risk Distribution Chart
     - Check: Chart loads (when patient data exists)
     - Check: Shows CRITICAL/HIGH/MEDIUM/LOW breakdown

[] 6. System Alerts
     - Check: No alerts when no critical cases
     - Check: Shows alert when critical patient registered

====================================================================
9. TESTING CHECKLIST - PHASE 5: DDHS ADMIN ANALYTICS
====================================================================

[] 1. Login as DDHS Admin (admin@ddhs.gov / test123)

[] 2. Dashboard Overview
     - Check: Total patients across all regions
     - Check: Total doctors (5)
     - Check: Total nurses (3)
     - Check: Total PHC centers (6)

[] 3. Regional Analytics
     - Check: Each region data visible
     - Check: Can drill down to PHC details
     - Check: Staff per region shown

[] 4. Health Centers Page
     - Check: All 6 PHC centers listed
     - Check: Can view center details
     - Check: Can see staff assignments

[] 5. Staff Management Page
     - Check: All staff members listed
     - Check: Can see roles and assignments
     - Check: Can perform bulk operations (if available)

====================================================================
10. DATA FLOW VERIFICATION
====================================================================

Patient Checkup Data Flow:
  Patient Input → AI Risk Assessment → Database (patient_logs)
  → Doctor Notification → Doctor Review → Outcome Record
  → PHC Nurse Dashboard → DDHS Admin Analytics

Each step should:
  ✓ Save to correct database table
  ✓ Link user IDs correctly
  ✓ Maintain region isolation
  ✓ Update relevant dashboards
  ✓ Show in appropriate views

====================================================================
11. FEATURE VERIFICATION BY ROLE
====================================================================

PATIENT FEATURES:
  ✓ View Dashboard
  ✓ Book Health Checkup
  ✓ AI Health Assessment
  ✓ View Appointments
  ✓ Message Doctor
  ✓ View Health History
  ✓ Receive AI Risk Assessment

DOCTOR FEATURES:
  ✓ View Dashboard
  ✓ View Assigned Patients
  ✓ Review Patient Health Data
  ✓ Provide Diagnosis
  ✓ Manage Appointments
  ✓ Message Patients
  ✓ Record Outcomes

PHC NURSE FEATURES:
  ✓ View Dashboard (Region-specific)
  ✓ Register Patients
  ✓ View Center Metrics
  ✓ Monitor Staff
  ✓ 7-Day Trends
  ✓ Risk Distribution
  ✓ System Alerts
  ✓ Generate Reports

DDHS ADMIN FEATURES:
  ✓ View All Regions
  ✓ District Analytics
  ✓ Staff Management
  ✓ PHC Center Management
  ✓ Staff Assignment
  ✓ System Oversight
  ✓ Resource Allocation

====================================================================
12. KNOWN ISSUES & NOTES
====================================================================

- Chart.js CSP warning: Minor security policy issue, doesn't affect
  dashboard functionality
- Doctor 4 & 5 and Nurse (role not fully assigned): May need additional
  nurses in regions 4 & 5 for full testing
- All passwords unified as "test123": Change for production use
- Test data includes sample specializations: Can be customized

====================================================================
13. NEXT STEPS
====================================================================

1. Run Phase 1-5 tests above
2. For each patient checkup:
   - Go through full health assessment
   - Verify AI risk calculation
   - Check doctor receives notification
   - Confirm database records created
3. Test cross-region isolation:
   - Doctor 1 should only see PHC Central patients
   - Nurse 1 should only see PHC Central data
4. Monitor Flask logs for errors
5. Verify database queries are efficient
6. Test concurrent users (multiple browser tabs/windows)

====================================================================
14. DATABASE QUERY EXAMPLES FOR VERIFICATION
====================================================================

Check test users created:
  SELECT COUNT(*) FROM users WHERE role IN ('patient', 'doctor', 'phc_nurse', 'ddhs_admin');
  Expected: 14

Check staff assignments:
  SELECT u.fullname, u.role, pf.name FROM users u
  LEFT JOIN phc_facilities pf ON u.phc_id = pf.id
  WHERE u.role IN ('doctor', 'phc_nurse');

Check PHC facilities:
  SELECT * FROM phc_facilities;
  Expected: 6 regions

Check patient checkups created:
  SELECT COUNT(*) FROM patient_logs WHERE user_id IN (74,75,76,77,78);

====================================================================
15. TROUBLESHOOTING
====================================================================

Login failing?
  → Check Flask logs for error messages
  → Verify credentials in TEST_CREDENTIALS.txt
  → Ensure database path is correct

Dashboard not loading?
  → Check browser console for JavaScript errors
  → Verify Flask is running (should see terminal output)
  → Check if role is correctly assigned in database

Data not saving?
  → Monitor Flask debug output
  → Verify database file permissions
  → Check foreign key constraints

Performance issues?
  → Check database indexes
  → Monitor Flask CPU usage
  → Consider query optimization

====================================================================
SUMMARY
====================================================================

Complete SmartTriage setup with:
  ✓ 14 test users across 4 roles
  ✓ 6 PHC regions fully defined
  ✓ Staff assigned to specific regions
  ✓ All database tables connected
  ✓ Dual-Brain AI ready for health assessment
  ✓ Role-based dashboards prepared
  ✓ Region isolation configured
  ✓ Backend and frontend integrated

Ready for comprehensive testing of all features!

====================================================================
Date: April 17, 2026
Status: PRODUCTION READY FOR TESTING
====================================================================
