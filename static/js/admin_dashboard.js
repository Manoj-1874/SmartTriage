/* ═════════════════════════════════════════════════════
   DDHS ADMIN DASHBOARD - JAVASCRIPT
   Theme-matched version for emergency management
   ═════════════════════════════════════════════════════ */

// Section titles for breadcrumb
const sectionTitles = {
    'dashboard': 'Dashboard',
    'emergencies': 'Emergency Alerts',
    'dispatch': 'Ambulance Dispatch',
    'tracking': 'Case Tracking',
    'workforce': 'Workforce Monitoring',
    'reports-action': 'Patient Reports & Actions',
    'reports': 'Reports & Analytics',
    'settings': 'Settings'
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    updateTime();
    initializeAlertsCount();
    loadEmergencyCases();
    setupEventListeners();
    setInterval(updateTime, 1000);
    setInterval(refreshEmergencies, 10000); // Auto-refresh every 10 seconds
});

// ═════════════════════════════════════════════════════
// EVENT LISTENERS
// ═════════════════════════════════════════════════════
function setupEventListeners() {
    // Click handlers will use onclick attributes in HTML
    // But we can add additional event delegation here if needed
}

// ═════════════════════════════════════════════════════
// SECTION NAVIGATION
// ═════════════════════════════════════════════════════
function showSection(sectionName) {
    // Hide all sections
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => {
        section.classList.remove('active');
    });

    // Remove active class from sidebar links
    const links = document.querySelectorAll('.s-link');
    links.forEach(link => {
        link.classList.remove('active');
    });

    // Show selected section
    const sectionId = sectionName + '-section';
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.add('active');
    }

    // Add active class to corresponding sidebar link
    const activeLink = document.querySelector(`.s-link[onclick*="'${sectionName}'"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }

    // Update breadcrumb
    const breadcrumbPage = document.getElementById('breadcrumbPage');
    if (breadcrumbPage) {
        breadcrumbPage.textContent = sectionTitles[sectionName] || sectionName;
    }

    // Load data for specific sections on first view
    if (sectionName === 'workforce') {
        loadWorkforceAttendance();
    } else if (sectionName === 'reports-action') {
        loadPatientReports();
    }

    console.log('Navigated to section:', sectionName);
}

// ═════════════════════════════════════════════════════
// SIDEBAR TOGGLE
// ═════════════════════════════════════════════════════
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('collapsed');
    }
}

// ═════════════════════════════════════════════════════
// TIME MANAGEMENT
// ═════════════════════════════════════════════════════
function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', {
        hour12: true,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    const timeDisplay = document.getElementById('timeDisplay');
    if (timeDisplay) {
        timeDisplay.textContent = timeString;
    }
}

// ═════════════════════════════════════════════════════
// ALERTS & NOTIFICATIONS
// ═════════════════════════════════════════════════════
function initializeAlertsCount() {
    fetch('/api/emergency/cases')
        .then(response => response.json())
        .then(data => {
            const count = (data.cases || []).length;
            updateAlertCount(count);
        })
        .catch(error => {
            console.error('Error loading alerts:', error);
            updateAlertCount(0);
        });
}

function updateAlertCount(count) {
    const alertChip = document.getElementById('alertChip');
    const urgentCount = document.getElementById('urgentCount');

    if (alertChip) {
        alertChip.textContent = count;
    }
    if (urgentCount) {
        urgentCount.textContent = count > 0 ? Math.min(count, 9) : 0;
    }
}

function refreshEmergencies() {
    loadEmergencyCases();
}

// ═════════════════════════════════════════════════════
// LOAD EMERGENCY CASES
// ═════════════════════════════════════════════════════
function loadEmergencyCases() {
    fetch('/api/emergency/cases')
        .then(response => {
            if (!response.ok) throw new Error('API error: ' + response.status);
            return response.json();
        })
        .then(data => {
            console.log('Cases loaded:', data);

            const cases = data.cases || [];

            // Update KPI counts
            updateKPICards(cases);

            // Update emergency queue
            updateEmergencyQueue(cases);

            // Populate cases table
            populateEmergenciesTable(cases);

            // Populate dispatch form selects
            populateDispatchForm(cases);
        })
        .catch(error => {
            console.error('Error loading cases:', error);
            updateKPICards([]);
        });
}

// ═════════════════════════════════════════════════════
// UPDATE KPI CARDS
// ═════════════════════════════════════════════════════
function updateKPICards(cases) {
    let urgent = 0;
    let highRisk = 0;
    let handled = 0;
    let active = 0;

    cases.forEach(c => {
        const riskScore = c.risk_score || 0;
        const status = c.status || 'pending';

        if (riskScore >= 80) urgent++;
        if (riskScore >= 60) highRisk++;
        if (status === 'completed') handled++;
        if (status === 'dispatched' || status === 'en_route') active++;
    });

    const urgentCountEl = document.getElementById('urgentCount');
    const highRiskCountEl = document.getElementById('highRiskCount');
    const handledCountEl = document.getElementById('handledCount');
    const activeAmbCountEl = document.getElementById('activeAmbCount');

    if (urgentCountEl) urgentCountEl.textContent = urgent;
    if (highRiskCountEl) highRiskCountEl.textContent = highRisk;
    if (handledCountEl) handledCountEl.textContent = handled;
    if (activeAmbCountEl) activeAmbCountEl.textContent = active;
}

// ═════════════════════════════════════════════════════
// UPDATE EMERGENCY QUEUE
// ═════════════════════════════════════════════════════
function updateEmergencyQueue(cases) {
    const queueContainer = document.getElementById('emergencyQueue');
    if (!queueContainer) return;

    // Get urgent cases (risk score >= 80)
    const urgentCases = cases.filter(c => (c.risk_score || 0) >= 80);

    if (urgentCases.length === 0) {
        queueContainer.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--t-muted);">No urgent cases currently</div>';
        return;
    }

    queueContainer.innerHTML = urgentCases.map(c => `
        <div class="queue-item">
            <div class="queue-priority urgent">URGENT</div>
            <div class="queue-info"><strong>Patient ID: #${c.id}</strong></div>
            <div class="queue-location">${c.symptoms || 'N/A'} | Risk Score: ${c.risk_score || 0}</div>
            <div class="queue-location">📍 Location: ${c.location || 'Downtown Medical Center'}</div>
            <button class="btn-dispatch-quick" onclick="showSection('dispatch')">DISPATCH NOW</button>
        </div>
    `).join('');
}

// ═════════════════════════════════════════════════════
// POPULATE EMERGENCIES TABLE
// ═════════════════════════════════════════════════════
function populateEmergenciesTable(cases) {
    const tableBody = document.getElementById('emergenciesTable');
    if (!tableBody) return;

    if (cases.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 20px; color: var(--t-muted);">No cases found</td></tr>';
        return;
    }

    tableBody.innerHTML = cases.map(c => {
        const riskScore = c.risk_score || 0;
        const priorityClass = riskScore >= 80 ? 'urgent' : riskScore >= 60 ? 'high' : 'moderate';
        const priorityLabel = riskScore >= 80 ? '🔴 URGENT' : riskScore >= 60 ? '🟠 HIGH' : '🟡 MODERATE';

        return `
            <tr>
                <td><span style="padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; background: ${priorityClass === 'urgent' ? 'var(--red-light)' : 'var(--amber-light)'}; color: ${priorityClass === 'urgent' ? 'var(--red-dark)' : 'var(--amber-dark)'};">${priorityLabel}</span></td>
                <td>#${c.id} - ${c.patient_name || 'Unknown'}</td>
                <td>${c.symptoms || 'N/A'}</td>
                <td><strong>${riskScore}</strong></td>
                <td>📍 ${c.location || 'N/A'}</td>
                <td><span style="padding: 2px 8px; border-radius: 4px; font-size: 11px; background: var(--surface-2);">${c.status || 'pending'}</span></td>
                <td>${new Date(c.created_at || Date.now()).toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'})}</td>
                <td>
                    <button class="btn-small" onclick="showSection('dispatch')">Dispatch</button>
                    <button class="btn-small" onclick="showSection('tracking')">Track</button>
                </td>
            </tr>
        `;
    }).join('');
}

// ═════════════════════════════════════════════════════
// POPULATE DISPATCH FORM
// ═════════════════════════════════════════════════════
function populateDispatchForm(cases) {
    const caseSelect = document.getElementById('caseSelect');
    if (!caseSelect) return;

    caseSelect.innerHTML = '<option value="">Choose a case...</option>' +
        cases.map(c => `<option value="${c.id}">Case #${c.id} - ${c.patient_name || 'Unknown'} (Risk: ${c.risk_score})</option>`).join('');

    // Load ambulances
    loadAmbulances();

    // Load staff
    loadStaff();

    // Load hospitals
    loadHospitals();
}

// ═════════════════════════════════════════════════════
// LOAD AMBULANCES
// ═════════════════════════════════════════════════════
function loadAmbulances() {
    fetch('/api/ambulances')
        .then(response => response.json())
        .then(data => {
            const selectors = document.getElementById('ambulanceSelect');
            if (selectors) {
                selectors.innerHTML = '<option value="">Choose ambulance...</option>' +
                    (data.ambulances || []).map(a =>
                        `<option value="${a.id}">${a.registration_number} - ${a.status || 'Available'}</option>`
                    ).join('');
            }
        })
        .catch(error => console.error('Error loading ambulances:', error));
}

// ═════════════════════════════════════════════════════
// LOAD STAFF
// ═════════════════════════════════════════════════════
function loadStaff() {
    fetch('/api/staff')
        .then(response => response.json())
        .then(data => {
            const selector = document.getElementById('paramedic');
            if (selector) {
                selector.innerHTML = '<option value="">Choose paramedic...</option>' +
                    (data.staff || []).map(s =>
                        `<option value="${s.id}">${s.name} - ${s.role || 'Staff'}</option>`
                    ).join('');
            }

            // Update staff grid
            updateStaffGrid(data.staff || []);
        })
        .catch(error => console.error('Error loading staff:', error));
}

// ═════════════════════════════════════════════════════
// UPDATE STAFF GRID
// ═════════════════════════════════════════════════════
function updateStaffGrid(staff) {
    const staffGrid = document.getElementById('staffGrid');
    if (!staffGrid || staff.length === 0) return;

    staffGrid.innerHTML = staff.map(s => `
        <div class="staff-card">
            <div class="staff-badge">${s.gender === 'Female' ? '👩‍⚕️' : '👨‍⚕️'}</div>
            <h4>${s.name}</h4>
            <div class="role">${s.role || 'Staff'}</div>
            <div class="status online">● Online</div>
            <div class="assignment">${s.assignment || 'Standby'}</div>
            <div class="staff-actions">
                <button class="btn-small">Call</button>
                <button class="btn-small">Assign</button>
            </div>
        </div>
    `).join('');
}

// ═════════════════════════════════════════════════════
// LOAD HOSPITALS
// ═════════════════════════════════════════════════════
function loadHospitals() {
    fetch('/api/hospitals')
        .then(response => response.json())
        .then(data => {
            const selector = document.getElementById('hospital');
            if (selector) {
                selector.innerHTML = '<option value="">Choose hospital...</option>' +
                    (data.hospitals || []).map(h =>
                        `<option value="${h.id}">${h.name} - ${h.department || 'General'}</option>`
                    ).join('');
            }
        })
        .catch(error => console.error('Error loading hospitals:', error));
}

// ═════════════════════════════════════════════════════
// HANDLE DISPATCH
// ═════════════════════════════════════════════════════
function handleDispatch(event) {
    event.preventDefault();

    const formData = {
        case_id: document.getElementById('caseSelect').value,
        ambulance_id: document.getElementById('ambulanceSelect').value,
        paramedic_id: document.getElementById('paramedic').value,
        hospital_id: document.getElementById('hospital').value,
        priority: document.querySelector('input[name="priority"]:checked')?.value || 'high',
        notes: document.getElementById('notes').value
    };

    console.log('Dispatching ambulance:', formData);

    fetch('/api/emergency/dispatch', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        if (!response.ok) throw new Error('Dispatch failed: ' + response.status);
        return response.json();
    })
    .then(data => {
        console.log('Dispatch successful:', data);
        alert('✅ Ambulance dispatched successfully!');

        // Reset form
        event.target.reset();

        // Refresh data
        loadEmergencyCases();

        // Switch to tracking section
        setTimeout(() => showSection('tracking'), 500);
    })
    .catch(error => {
        console.error('Error dispatching ambulance:', error);
        alert('❌ Error dispatching ambulance: ' + error.message);
    });
}

// ═════════════════════════════════════════════════════
// WORKFORCE MONITORING - ATTENDANCE TRACKING
// ═════════════════════════════════════════════════════
function loadWorkforceAttendance() {
    // Mock data for workforce attendance
    // In production, this would fetch from /api/staff/attendance
    const attendanceData = [
        {
            id: 1,
            name: 'Dr. Rajesh Kumar',
            role: 'PHC Doctor',
            phc: 'PHC North',
            checkIn: '08:32 AM',
            status: 'present',
            patients: 5
        },
        {
            id: 2,
            name: 'Nurse Priya Singh',
            role: 'PHC Nurse',
            phc: 'PHC North',
            checkIn: '08:45 AM',
            status: 'present',
            patients: 3
        },
        {
            id: 3,
            name: 'Dr. Anil Verma',
            role: 'PHC Doctor',
            phc: 'PHC South',
            checkIn: '09:15 AM',
            status: 'present',
            patients: 4
        }
    ];

    updateAttendanceTable(attendanceData);
    updateAttendanceSummary(attendanceData);
    updateStaffDirectoryGrid(attendanceData);
}

function updateAttendanceTable(data) {
    const tableBody = document.getElementById('attendanceTable');
    if (!tableBody) return;

    if (data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px;">No attendance data available</td></tr>';
        return;
    }

    tableBody.innerHTML = data.map(d => `
        <tr>
            <td><strong>${d.name}</strong></td>
            <td>${d.role}</td>
            <td>${d.phc}</td>
            <td>${d.checkIn}</td>
            <td><span class="staff-status ${d.status}">${d.status === 'present' ? '✓ Present' : '❌ Absent'}</span></td>
            <td>${d.patients}</td>
            <td>
                <button class="btn-small" onclick="alert('Actions for ${d.name}')">Manage</button>
            </td>
        </tr>
    `).join('');
}

function updateAttendanceSummary(data) {
    const presentCount = data.filter(d => d.status === 'present').length;
    const absentCount = data.filter(d => d.status === 'absent').length;
    const lateCount = Math.max(0, presentCount - data.filter(d => new Date(d.checkIn).getHours() < 9).length);

    const presentEl = document.getElementById('presentCount');
    const absentEl = document.getElementById('absentCount');
    const lateEl = document.getElementById('lateCount');

    if (presentEl) presentEl.textContent = presentCount;
    if (absentEl) absentEl.textContent = absentCount;
    if (lateEl) lateEl.textContent = lateCount;
}

function updateStaffDirectoryGrid(data) {
    const staffGrid = document.getElementById('staffGrid');
    if (!staffGrid) return;

    staffGrid.innerHTML = data.map(d => `
        <div class="staff-card">
            <div class="staff-header">
                <div class="staff-badge">${d.role === 'PHC Nurse' ? '👩‍⚕️' : '👨‍⚕️'}</div>
                <div class="staff-status ${d.status}">${d.status === 'present' ? 'Present' : 'Absent'}</div>
            </div>
            <h4>${d.name}</h4>
            <div class="staff-role">${d.role}</div>
            <div class="staff-facility">${d.phc}</div>
            <div class="staff-check-in">✓ ${d.checkIn}</div>
            <div class="staff-contact">📞 Patients: ${d.patients}</div>
            <div class="staff-actions">
                <button class="btn-small" onclick="alert('Call ${d.name}')">Call</button>
                <button class="btn-small" onclick="alert('Assign to ${d.name}')">Assign</button>
            </div>
        </div>
    `).join('');
}

// ═════════════════════════════════════════════════════
// PATIENT REPORTS & ACTIONS MANAGEMENT
// ═════════════════════════════════════════════════════
function loadPatientReports() {
    // Mock data for patient reports
    // In production, this would fetch from /api/patient-reports
    const reportsData = [
        {
            id: 1,
            patient: 'John Doe',
            type: 'Health Complaint',
            phc: 'PHC North',
            priority: 'high',
            status: 'pending',
            date: new Date().toLocaleDateString(),
            assignedTo: 'Unassigned'
        },
        {
            id: 2,
            patient: 'Jane Smith',
            type: 'Follow-up Required',
            phc: 'PHC South',
            priority: 'medium',
            status: 'under-review',
            date: new Date().toLocaleDateString(),
            assignedTo: 'Dr. Rajesh Kumar'
        }
    ];

    updateReportsTable(reportsData);
    updateReportsSummary(reportsData);
}

function updateReportsTable(data) {
    const tableBody = document.getElementById('reportsTable');
    if (!tableBody) return;

    if (data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 20px;">No reports available</td></tr>';
        return;
    }

    tableBody.innerHTML = data.map(d => {
        const priorityColor = d.priority === 'critical' ? 'var(--red)' : d.priority === 'high' ? 'var(--amber)' : 'var(--blue)';
        const statusBg = d.status === 'pending' ? 'var(--red-light)' : d.status === 'under-review' ? 'var(--amber-light)' : 'var(--green-light)';
        const statusText = d.status === 'pending' ? 'Pending' : d.status === 'under-review' ? 'Reviewing' : 'Resolved';

        return `
            <tr>
                <td><strong>${d.patient}</strong></td>
                <td>${d.type}</td>
                <td>${d.phc}</td>
                <td><span style="padding: 2px 6px; border-radius: 3px; font-size: 11px; background: ${priorityColor}20; color: ${priorityColor}; font-weight: 600;">${d.priority.toUpperCase()}</span></td>
                <td><span style="padding: 2px 6px; border-radius: 3px; background: ${statusBg}; font-size: 11px;">${statusText}</span></td>
                <td>${d.date}</td>
                <td>${d.assignedTo}</td>
                <td>
                    <button class="btn-small" onclick="alert('View details for ${d.patient}')">View</button>
                </td>
            </tr>
        `;
    }).join('');
}

function updateReportsSummary(data) {
    const pending = data.filter(d => d.status === 'pending').length;
    const review = data.filter(d => d.status === 'under-review').length;
    const resolved = data.filter(d => d.status === 'resolved').length;

    const pendingEl = document.getElementById('pendingReports');
    const reviewEl = document.getElementById('reviewReports');
    const resolvedEl = document.getElementById('resolvedReports');

    if (pendingEl) pendingEl.textContent = pending;
    if (reviewEl) reviewEl.textContent = review;
    if (resolvedEl) resolvedEl.textContent = resolved;
}

function handleDelegation() {
    const patient = document.getElementById('delegatePatient').value;
    const role = document.getElementById('delegateRole').value;
    const person = document.getElementById('delegatePerson').value;
    const action = document.getElementById('delegateAction').value;
    const notes = document.getElementById('delegateNotes').value;

    if (!patient || !role || !person || !action) {
        alert('❌ Please fill in all required fields');
        return;
    }

    const delegationData = {
        patient,
        role,
        person,
        action,
        notes,
        delegatedAt: new Date().toISOString()
    };

    console.log('Delegation created:', delegationData);

    // In production, this would POST to /api/delegation
    alert(`✅ Action delegated to ${person}\nTask: ${action}\nNotes: ${notes || 'None'}`);

    // Clear form
    document.getElementById('delegatePatient').value = '';
    document.getElementById('delegateRole').value = '';
    document.getElementById('delegatePerson').value = '';
    document.getElementById('delegateAction').value = '';
    document.getElementById('delegateNotes').value = '';

    // Refresh reports
    loadPatientReports();
}

// ═════════════════════════════════════════════════════
// EXPORT FUNCTIONS FOR EXTERNAL USE
// ═════════════════════════════════════════════════════
window.showSection = showSection;
window.toggleSidebar = toggleSidebar;
window.handleDispatch = handleDispatch;
window.handleDelegation = handleDelegation;
window.refreshEmergencies = refreshEmergencies;
window.loadWorkforceAttendance = loadWorkforceAttendance;
window.loadPatientReports = loadPatientReports;
window.loadEmergencyCases = loadEmergencyCases;
