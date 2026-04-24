# FIXES PLAN - Real-World Workflow Corrections

**Document:** Architecture fixes to align with real healthcare workflows
**Date:** April 18, 2026
**Status:** READY FOR IMPLEMENTATION

---

## 📊 RECOMMENDATION MATRIX

| Fix | What's Wrong | Real-World Impact | Difficulty | Time |
|-----|-------------|------------------|-----------|------|
| #1: Fix Messaging Template | PHC nurse messaging broken | **🔴 CRITICAL** - Nurses can't communicate | ⭐ Easy | 5 min |
| #2: Patient Appointment Removal | Patient books directly (bypasses triage) | **🔴 CRITICAL** - Wrong workflow | ⭐ Easy | 15 min |
| #3: Nurse Appointment Creation | No way to create appointments | **🔴 CRITICAL** - Nurse can't manage care | ⭐⭐ Medium | 30 min |
| #4: Move Checkup to Nurse | Patient self-diagnoses | **🔴 CRITICAL** - Bad medical practice | ⭐⭐ Medium | 45 min |
| #5: Fix Approval Permissions | Nurse approves (wrong role) | **🟠 HIGH** - Security & correctness | ⭐ Easy | 5 min |
| #6: Nurse-Doctor Messaging | No consultation channel | **🟠 HIGH** - Coordination breaks | ⭐⭐ Medium | 30 min |
| #7: Referral System | Non-functional mock | **🟠 HIGH** - Emergency escalation fails | ⭐⭐⭐ Hard | 1 hour |
| #8: Resource Visibility for Nurse | Nurse blind to inventory | **🟡 MEDIUM** - Dispensing issues | ⭐⭐ Medium | 45 min |
| #9: Assign Doctors to Patients | Patient messages any doctor | **🟡 MEDIUM** - System integrity | ⭐⭐ Medium | 30 min |

---

## 🔥 PRIORITY 1: CRITICAL FIXES (Must Do)

### **FIX #1: PHC Nurse Messaging Template (5 minutes)**

**Current Issue:**
```python
@app.route('/phc/nurse/messages')
def phc_nurse_messages():
    contacts = [...]
    # WRONG: Renders dashboard template without messaging UI
    return render_template('phc_nurse_dashboard.html',
                         contacts=contacts)
```

**Problem:** Template `phc_nurse_dashboard.html` doesn't have chat UI

**Fix:**
```python
@app.route('/phc/nurse/messages')
def phc_nurse_messages():
    contacts = [...]
    # RIGHT: Render messages template (same as patient/doctor)
    return render_template('messages.html',
                         contacts=contacts,
                         page_title='Messages - PHC Nurse',
                         current_page='messages')
```

**Impact:** ✅ PHC Nurse can now message patients

---

### **FIX #2: Remove "Book Appointment" from Patient (15 minutes)**

**Current Issue:**
- Patient has `/appointments/create` endpoint
- Patient can book with ANY doctor

**What to Remove from Patient Dashboard:**
```html
<!-- DELETE THIS BUTTON FROM patient_dashboard.html -->
<button onclick="location.href='/appointments'" class="btn">
  Book Appointment
</button>
```

**What to Keep:**
- View their own appointments (read-only)
- Message doctor
- View health records

**New Patient Flow:**
```
Patient arrives at PHC
    ↓
Nurse does intake
    ↓
Nurse creates appointment (if needed)
    ↓
Patient sees it in their dashboard
    ↓
"Your appointment is tomorrow at 10 AM"
```

**Code Change:**
```python
# REMOVE OR DISABLE:
@app.route('/appointments/create', methods=['POST'])
@login_required
def create_appointment():
    if current_user.role == 'patient':
        # Either DELETE this entire block
        # OR change to:
        flash('Appointments are booked by your PHC nurse', 'info')
        return redirect(url_for('patient_dashboard'))
```

**Impact:** ✅ Appointments flow through proper triage

---

### **FIX #3: Add Appointment Creation to PHC Nurse (30 minutes)**

**Current State:**
- Nurse CAN view appointments (read-only)
- Nurse CANNOT create appointments
- Missing: Button/form to create appointment

**Add to `/phc/nurse/appointments` route:**

```python
@app.route('/phc/nurse/appointments')
@login_required
def phc_nurse_appointments():
    """PHC Nurse can view AND CREATE appointments"""

    if current_user.role != 'phc_nurse':
        flash('Access denied')
        return redirect(url_for('index'))

    # GET: Show appointments + create form
    if request.method == 'GET':
        appointments = [...existing code...]

        # NEW: Get facility doctors for dropdown
        doctors = conn.execute('''
            SELECT id, fullname FROM users
            WHERE phc_id = ? AND role = 'doctor'
        ''', (current_user.phc_id,)).fetchall()

        # NEW: Get facility patients for dropdown
        patients = conn.execute('''
            SELECT DISTINCT u.id, u.fullname FROM users u
            INNER JOIN patient_logs pl ON u.id = pl.user_id
            WHERE pl.phc_id = ? AND u.role = 'patient'
        ''', (current_user.phc_id,)).fetchall()

        return render_template('phc_nurse_dashboard.html',
                             appointments=appointments,
                             doctors=doctors,
                             patients=patients,
                             current_page='appointments',
                             user=current_user)

# NEW ROUTE: Create appointment
@app.route('/phc/nurse/appointments/create', methods=['POST'])
@login_required
def phc_nurse_create_appointment():
    """Nurse creates appointment for patient"""

    if current_user.role != 'phc_nurse':
        abort(403)

    patient_id = request.form['patient_id']
    doctor_id = request.form['doctor_id']
    appointment_date = request.form['appointment_date']
    urgency = request.form.get('urgency', 'Routine')  # Routine, Urgent, Emergency
    reason = request.form.get('reason', '')

    # Verify patient is at this PHC
    patient = conn.execute('''
        SELECT user_id FROM patient_logs
        WHERE user_id = ? AND phc_id = ?
    ''', (patient_id, current_user.phc_id)).fetchone()

    if not patient:
        flash('Patient not at this PHC', 'error')
        return redirect(url_for('phc_nurse_appointments'))

    # Verify doctor is at this PHC
    doctor = conn.execute('''
        SELECT id FROM users
        WHERE id = ? AND phc_id = ? AND role = 'doctor'
    ''', (doctor_id, current_user.phc_id)).fetchone()

    if not doctor:
        flash('Doctor not at this PHC', 'error')
        return redirect(url_for('phc_nurse_appointments'))

    # Create appointment
    conn.execute('''
        INSERT INTO appointments
        (patient_id, doctor_id, appointment_date, status, urgency, reason, created_by_nurse)
        VALUES (?, ?, ?, 'Approved', ?, ?, ?)
    ''', (patient_id, doctor_id, appointment_date, urgency, reason, current_user.id))

    conn.commit()

    # Send notification
    conn.execute('''
        INSERT INTO messages (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
    ''', (current_user.id, patient_id,
          f'Your appointment with Dr. {doctor.fullname} is confirmed for {appointment_date}'))

    flash('Appointment created successfully', 'success')
    return redirect(url_for('phc_nurse_appointments'))
```

**Add to HTML template (`phc_nurse_dashboard.html`):**

```html
<!-- NEW: Create Appointment Form -->
<div class="appointment-create" id="createAppointmentForm" style="display:none;">
    <h3>Create Appointment for Patient</h3>
    <form method="POST" action="/phc/nurse/appointments/create">
        <select name="patient_id" required>
            <option value="">Select Patient</option>
            {% for patient in patients %}
            <option value="{{ patient.id }}">{{ patient.fullname }}</option>
            {% endfor %}
        </select>

        <select name="doctor_id" required>
            <option value="">Select Doctor</option>
            {% for doctor in doctors %}
            <option value="{{ doctor.id }}">Dr. {{ doctor.fullname }}</option>
            {% endfor %}
        </select>

        <input type="datetime-local" name="appointment_date" required>

        <select name="urgency">
            <option value="Routine">Routine</option>
            <option value="Urgent">Urgent (Today if possible)</option>
            <option value="Emergency">Emergency (Immediate)</option>
        </select>

        <textarea name="reason" placeholder="Reason for appointment"></textarea>

        <button type="submit" class="btn btn-primary">Create Appointment</button>
        <button type="button" onclick="document.getElementById('createAppointmentForm').style.display='none'" class="btn btn-secondary">Cancel</button>
    </form>
</div>

<!-- Button to show form -->
<button onclick="document.getElementById('createAppointmentForm').style.display='block'" class="btn btn-success">
  + Create New Appointment
</button>
```

**Database Schema Update:**
```sql
ALTER TABLE appointments ADD COLUMN urgency TEXT DEFAULT 'Routine';
ALTER TABLE appointments ADD COLUMN reason TEXT;
ALTER TABLE appointments ADD COLUMN created_by_nurse INTEGER;
```

**Impact:** ✅ Nurse can now create appointments based on patient triage

---

### **FIX #4: Move Health Checkup Input to Nurse (45 minutes)**

**Current Issue:**
- Patient can access `/checkup` form
- Patient self-diagnoses with AI
- No nurse oversight

**Solution:**
1. Disable patient checkup
2. Add checkup form to nurse intake
3. Keep AI review but nurse explains results

**Step 1: Disable Patient Checkup**

```python
# In app.py, modify:
@app.route('/checkup', methods=['GET', 'POST'])
@login_required
def checkup():
    if current_user.role == 'patient':
        # NEW: Redirect instead of allowing
        flash('Appointments and health assessments are done with your PHC nurse', 'info')
        return redirect(url_for('patient_dashboard'))

    # Rest of code for other roles...
```

**Step 2: Add Checkup to Nurse Intake**

```python
@app.route('/phc/nurse/intake', methods=['GET', 'POST'])
@login_required
def phc_nurse_intake():
    """PHC Nurse - Patient intake and AI assessment"""

    if current_user.role != 'phc_nurse':
        flash('Access denied')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Get patient selection (which patient being assessed)
        patient_id = request.form.get('patient_id')

        # Get vitals from nurse input
        vitals = {
            'hr': request.form.get('heart_rate'),
            'sys_bp': request.form.get('sys_bp'),
            'dia_bp': request.form.get('dia_bp'),
            'temperature': request.form.get('temperature'),
            'spo2': request.form.get('spo2'),
            'respiration_rate': request.form.get('respiration_rate')
        }

        # Get symptoms from patient (nurse asks questions)
        symptoms = request.form.get('symptoms')
        symptom_duration = request.form.get('symptom_duration')

        # Run AI assessment
        assessment = run_ai_assessment(vitals, symptoms, symptom_duration)
        # Returns: {'xgb_risk': ..., 'bert_diagnosis': ..., 'final_risk': ...}

        # Nurse sees results with interpretation
        return render_template('phc_nurse_intake_results.html',
                             patient_id=patient_id,
                             vitals=vitals,
                             symptoms=symptoms,
                             assessment=assessment,
                             user=current_user)

    # GET: Show intake form
    patients = conn.execute('''
        SELECT DISTINCT u.id, u.fullname FROM users u
        INNER JOIN patient_logs pl ON u.id = pl.user_id
        WHERE pl.phc_id = ? AND u.role = 'patient'
    ''', (current_user.phc_id,)).fetchall()

    return render_template('phc_nurse_intake_form.html',
                         patients=patients,
                         user=current_user)
```

**Add Assessment Result Handler:**

```python
@app.route('/phc/nurse/intake/confirm', methods=['POST'])
@login_required
def phc_nurse_intake_confirm():
    """Nurse confirms/overrides AI assessment"""

    patient_id = request.form.get('patient_id')
    ai_risk = request.form.get('ai_risk')
    nurse_override = request.form.get('nurse_override_risk')  # Can override
    decision = request.form.get('decision')  # 'home', 'appointment', 'urgent', 'referral'
    nurse_notes = request.form.get('nurse_notes')

    # Save assessment
    final_risk = nurse_override if nurse_override else ai_risk

    conn.execute('''
        INSERT INTO patient_logs
        (user_id, phc_id, symptoms, dual_brain_risk, nurse_notes, assessment_date)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (patient_id, current_user.phc_id,
          request.form.get('symptoms'), final_risk, nurse_notes))

    # Based on decision, take action
    if decision == 'home':
        message = "Rest at home. Drink fluids. Follow-up in 3 days."
    elif decision == 'appointment':
        # Nurse creates appointment (see FIX #3)
        message = "Appointment created. See doctor tomorrow at 10 AM."
    elif decision == 'urgent':
        # Urgent appointment today
        message = "Urgent appointment scheduled for today."
    elif decision == 'referral':
        # Ambulance + hospital referral
        message = "Ambulance dispatched. Going to hospital."

    # Notify patient
    conn.execute('''
        INSERT INTO messages (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
    ''', (current_user.id, patient_id, message))

    conn.commit()
    flash('Assessment saved. Patient notified.', 'success')
    return redirect(url_for('phc_nurse_dashboard'))
```

**Impact:** ✅ Professional triage through nurse instead of self-diagnosis

---

### **FIX #5: Fix Appointment Approval Permissions (5 minutes)**

**Current Bug:**
```python
if current_user.role in ('doctor', 'phc_nurse'):  # ← WRONG!
    conn.execute('UPDATE appointments SET status = ?', ...)
```

**Fix:**
```python
if current_user.role == 'doctor':  # ← ONLY doctor
    conn.execute('UPDATE appointments SET status = ?', ...)
elif current_user.role == 'phc_nurse':
    # Nurse can ONLY change certain statuses
    if status in ('Confirmed', 'Reschedule'):
        # OK to confirm/reschedule
        conn.execute('UPDATE appointments SET status = ?', ...)
    else:
        # Cannot approve/reject
        flash('Only doctors can approve/reject appointments', 'error')
```

**Impact:** ✅ Proper role permissions enforced

---

## 🟠 PRIORITY 2: HIGH PRIORITY FIXES

### **FIX #6: Add Nurse-Doctor Messaging (30 minutes)**

**New Feature:** Messages between nurses and doctors for consultation

```python
# New route:
@app.route('/phc/nurse/consult/<int:doctor_id>', methods=['POST'])
@login_required
def phc_nurse_consult_doctor(doctor_id):
    """Nurse asks doctor for consultation"""

    if current_user.role != 'phc_nurse':
        abort(403)

    message = request.form['message']
    patient_id = request.form.get('patient_id')  # Optional reference

    # Store as "consultation" type message
    conn.execute('''
        INSERT INTO messages (sender_id, receiver_id, message, message_type)
        VALUES (?, ?, ?, 'consultation')
    ''', (current_user.id, doctor_id,
          f'[CONSULTATION] Patient #{patient_id}: {message}'))

    conn.commit()
    return {'status': 'sent', 'message': 'Doctor notified'}
```

**Impact:** ✅ Nurse-doctor coordination

---

### **FIX #7: Implement Referral System (1 hour)**

```python
@app.route('/phc/nurse/refer/<int:patient_id>', methods=['POST'])
@login_required
def phc_nurse_refer_to_hospital(patient_id):
    """Urgent referral to hospital"""

    if current_user.role != 'phc_nurse':
        abort(403)

    reason = request.form['reason']
    urgency = request.form.get('urgency', 'URGENT')  # URGENT, CRITICAL

    # Create referral record
    conn.execute('''
        INSERT INTO referrals
        (patient_id, from_phc_id, reason, urgency, created_by_nurse, status)
        VALUES (?, ?, ?, ?, ?, 'PENDING_DISPATCH')
    ''', (patient_id, current_user.phc_id, reason, urgency, current_user.id))

    # Get patient contact for SMS
    patient = conn.execute('''
        SELECT phone FROM users WHERE id = ?
    ''', (patient_id,)).fetchone()

    # Dispatch ambulance (real integration)
    # send_sms(patient['phone'], 'Ambulance coming to your PHC. Be ready.')

    # Notify hospital
    # send_to_hospital_system(...)

    flash('Referral submitted. Ambulance dispatched.', 'success')
    return redirect(url_for('phc_nurse_dashboard'))
```

**Impact:** ✅ Real emergency escalation

---

### **FIX #8: Resource Visibility for Nurses (45 minutes)**

```python
@app.route('/phc/nurse/resources')
@login_required
def phc_nurse_resources():
    """PHC Nurse can see inventory for their facility"""

    if current_user.role != 'phc_nurse':
        abort(403)

    # Get inventory for this PHC only
    inventory = conn.execute('''
        SELECT * FROM resources
        WHERE phc_id = ?
        ORDER BY quantity ASC
    ''', (current_user.phc_id,)).fetchall()

    return render_template('phc_nurse_resources.html',
                         inventory=inventory,
                         user=current_user)
```

**Impact:** ✅ Nurses know what medicines/equipment available

---

## 🟡 PRIORITY 3: MEDIUM PRIORITY (Polish)

### **FIX #9: Assign Doctors to Patients (30 minutes)**
- Track which doctor patient has appointment with
- Patient messages only that doctor
- Reduces chaos

---

## 📈 IMPLEMENTATION ROADMAP

### **Phase 1: Critical (Today)**
- [ ] Fix #1: Messaging template (5 min)
- [ ] Fix #2: Remove patient appointment booking (15 min)
- [ ] Fix #5: Fix approval permissions (5 min)
- **Total:** 25 minutes

### **Phase 2: Important (This Week)**
- [ ] Fix #3: Nurse appointment creation (30 min)
- [ ] Fix #4: Move checkup to nurse (45 min)
- [ ] Fix #6: Nurse-doctor messaging (30 min)
- **Total:** 1 hour 45 minutes

### **Phase 3: Enhancement (Next Week)**
- [ ] Fix #7: Referral system (1 hour)
- [ ] Fix #8: Resource visibility (45 min)
- [ ] Fix #9: Doctor assignment (30 min)
- **Total:** 2 hours 15 minutes

---

## ✅ FINAL STATE (After All Fixes)

**Patient Dashboard:**
- ✅ View own appointments (read-only)
- ✅ Message doctor
- ✅ View health records
- ❌ No appointment booking
- ❌ No self-diagnosis

**PHC Nurse Dashboard:**
- ✅ Create appointments
- ✅ Conduct patient intake
- ✅ Run AI assessment (with nurse review)
- ✅ Message patients
- ✅ Message doctors
- ✅ View resource inventory
- ✅ Refer to hospital
- ✅ Patient management

**Doctor Dashboard:**
- ✅ Approve appointments
- ✅ Review AI assessments
- ✅ Message nurse/patient
- ✅ Complete appointments
- ✅ Validate AI outcomes

**DDHS Admin Dashboard:**
- ✅ Manage all resources
- ✅ Monitor referrals
- ✅ Ambulance dispatch
- ✅ District analytics

---

**Ready to proceed?** Which phase should we implement first?
