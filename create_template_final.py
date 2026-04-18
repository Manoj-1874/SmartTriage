f = open(r'e:\Nilal_thiruvila\SmartTriage_Dashboard\templates\ddhs_admin_dashboard.html', 'wb')
f.write(b'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - DDHS Admin</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Outfit', sans-serif; background: #f5f5f5; min-height: 100vh; display: flex; }
        .sidebar { width: 250px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px 0; position: fixed; left: 0; top: 0; z-index: 1000; overflow-y: auto; }
        .sidebar-header { padding: 20px; color: white; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.2); margin-bottom: 20px; }
        .sidebar-header h3 { font-size: 18px; margin-bottom: 5px; }
        .sidebar-header p { font-size: 12px; opacity: 0.9; }
        .sidebar-menu { list-style: none; padding: 0; }
        .sidebar-menu a { display: block; padding: 12px 20px; color: white; text-decoration: none; transition: all 0.3s; border-left: 3px solid transparent; }
        .sidebar-menu a:hover { background: rgba(255,255,255,0.1); border-left-color: white; }
        .sidebar-menu a.active { background: rgba(255,255,255,0.2); border-left-color: white; font-weight: 600; }
        .sidebar-menu i { width: 20px; margin-right: 10px; text-align: center; }
        .sidebar-footer { position: absolute; bottom: 20px; left: 0; right: 0; padding: 20px; border-top: 1px solid rgba(255,255,255,0.2); }
        .sidebar-footer a { color: white; text-decoration: none; font-size: 12px; display: block; padding: 8px 0; }
        .main-content { margin-left: 250px; flex: 1; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .page-title { font-size: 28px; font-weight: 700; color: #1a1a1a; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 28px; font-weight: 700; color: #667eea; }
        .stat-label { font-size: 12px; color: #999; text-transform: uppercase; margin-top: 8px; }
        .section { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .section-title { font-size: 18px; font-weight: 700; color: #1a1a1a; margin-bottom: 15px; display: flex; align-items: center; }
        .section-title i { margin-right: 10px; color: #667eea; }
        .resource-table { width: 100%; border-collapse: collapse; }
        .resource-table th { background: #f5f5f5; padding: 12px; text-align: left; font-weight: 600; font-size: 12px; color: #666; border-bottom: 2px solid #e0e0e0; text-transform: uppercase; }
        .resource-table td { padding: 12px; border-bottom: 1px solid #e0e0e0; }
        .resource-table tbody tr:hover { background: #f9f9f9; }
        .status-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .status-optimal { background: #d4edda; color: #155724; }
        .status-warning { background: #fff3cd; color: #856404; }
        .status-critical { background: #f8d7da; color: #721c24; }
        .no-data { text-align: center; padding: 40px 20px; color: #999; }
    </style>
</head>
<body>
<div class="sidebar">
    <div class="sidebar-header">
        <h3>PriorityMed</h3>
        <p>DDHS Admin</p>
    </div>
    <ul class="sidebar-menu">
        <li><a href="/ddhs-admin/dashboard" class="active"><i class="fas fa-chart-line"></i>Dashboard</a></li>
        <li><a href="/ddhs-admin/health-centers"><i class="fas fa-hospital"></i>Health Centers</a></li>
        <li><a href="/ddhs-admin/staff"><i class="fas fa-users"></i>Staff</a></li>
        <li><a href="/ddhs-admin/resources"><i class="fas fa-boxes"></i>Resources</a></li>
        <li><a href="/ddhs-admin/reports"><i class="fas fa-file-chart"></i>Reports</a></li>
        <li><a href="/ddhs-admin/disease-surveillance"><i class="fas fa-virus"></i>Disease</a></li>
        <li><a href="/ddhs-admin/budget"><i class="fas fa-wallet"></i>Budget</a></li>
        <li><a href="/ddhs-admin/campaigns"><i class="fas fa-bullhorn"></i>Campaigns</a></li>
        <li><a href="/ddhs-admin/audit-log"><i class="fas fa-history"></i>Audit</a></li>
    </ul>
    <div class="sidebar-footer">
        <a href="/patient_dashboard">Back to Main</a>
        <a href="/logout" style="color: #ff6b6b;">Logout</a>
    </div>
</div>
<div class="main-content">
<div class="container">
    <h1 class="page-title">Dashboard</h1>
    <div class="stats-grid">
        <div class="stat-card"><div class="stat-value">{{ total_patients }}</div><div class="stat-label">Patients</div></div>
        <div class="stat-card"><div class="stat-value">{{ health_centers }}</div><div class="stat-label">Centers</div></div>
        <div class="stat-card"><div class="stat-value">{{ total_staff }}</div><div class="stat-label">Staff</div></div>
        <div class="stat-card"><div class="stat-value">{{ critical_cases }}</div><div class="stat-label">Critical</div></div>
    </div>
    <div class="section">
        <div class="section-title"><i class="fas fa-chart-bar"></i>Performance</div>
        {% if center_performance %}
        <table class="resource-table">
            <thead><tr><th>Center</th><th>Appointments</th><th>Completed</th><th>Rate</th></tr></thead>
            <tbody>
            {% for center in center_performance %}
            <tr><td>PHC {{ center.center_id }}</td><td>{{ center.total_appointments }}</td><td>{{ center.completed }}</td><td><span class="status-badge status-optimal">{{ center.completion_rate }}%</span></td></tr>
            {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="no-data">No data available</div>
        {% endif %}
    </div>
</div>
</div>
</body>
</html>''')
f.close()
print('Template file created successfully')
