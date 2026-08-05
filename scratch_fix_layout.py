import re

with open(r'templates\ddhs_admin_ambulances_redesigned.html', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('{% block content %}')
end = content.find('{% block extra_js %}')

if start != -1 and end != -1:
    block_content = content[start:end]
    
    new_content = """{% block content %}

<!-- Search & Filter -->
<div class="section-card" style="margin-bottom: 24px;">
    <div class="section-header">
        <h3>🔍 Search & Filter</h3>
    </div>
    <div class="section-body">
        <div style="display: grid; grid-template-columns: 2fr 1fr auto; gap: 15px;">
            <div>
                <input type="text" id="ambulanceSearchInput" placeholder="Search by ambulance number or driver..."
                       style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; background: var(--base); color: var(--text-head);">
            </div>
            <div>
                <select id="ambulanceStatusFilter" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; background: var(--base); color: var(--text-head);">
                    <option value="">All Statuses</option>
                    <option value="available">Available</option>
                    <option value="in_transit">In Transit</option>
                    <option value="maintenance">Maintenance</option>
                </select>
            </div>
            <button onclick="performAmbulanceSearch()" class="btn btn-primary">
                Search
            </button>
        </div>
    </div>
</div>

<div style="display: grid; grid-template-columns: 2fr 1fr; gap: 24px; margin-bottom: 24px;">
    <!-- Map View -->
    <div class="section-card" style="margin: 0;">
        <div class="section-header">
            <h3><i class="fas fa-map"></i> Live Tracking Map</h3>
        </div>
        <div class="section-body">
            <div id="ambulance-map"></div>
            <p style="font-size: 12px; color: var(--text-muted); margin-top: 12px;">
                <i class="fas fa-info-circle"></i> Red pins: Available | Blue pins: In Transit | Gray pins: Maintenance
            </p>
        </div>
    </div>

    <!-- Ambulance Fleet -->
    <div class="section-card" style="margin: 0; max-height: 500px; overflow-y: auto;">
        <div class="section-header" style="position: sticky; top: 0; background: var(--base); z-index: 10;">
            <h3><i class="fas fa-ambulance"></i> Ambulance Fleet</h3>
            <div class="section-header-actions">
                <button class="btn btn-primary btn-sm" onclick="openAddAmbulanceModal()">
                    <i class="fas fa-plus"></i> Add Ambulance
                </button>
            </div>
        </div>
        <div class="section-body">
            {% if ambulances %}
                {% for ambulance in ambulances %}
                <div class="ambulance-card" data-status="{{ ambulance.status }}" data-number="{{ ambulance.ambulance_number }}">
                    <div class="ambulance-icon">
                        <i class="fas fa-ambulance"></i>
                    </div>
                    <div class="ambulance-info">
                        <div class="ambulance-number">{{ ambulance.ambulance_number }}</div>
                        <div class="ambulance-driver">
                            <i class="fas fa-user"></i> {{ ambulance.driver_name or 'No Driver' }} 
                            ({{ ambulance.district }})
                        </div>
                    </div>
                    <div class="ambulance-status">
                        {% if ambulance.status == 'available' %}
                            <span class="status-badge active"><i class="fas fa-check-circle"></i> Available</span>
                        {% elif ambulance.status == 'in_transit' %}
                            <span class="status-badge warning"><i class="fas fa-route"></i> In Transit</span>
                        {% elif ambulance.status == 'maintenance' %}
                            <span class="status-badge inactive"><i class="fas fa-wrench"></i> Maintenance</span>
                        {% else %}
                            <span class="status-badge">{{ ambulance.status|title }}</span>
                        {% endif %}
                        
                        <div style="margin-top: 8px;">
                            <button class="btn btn-secondary btn-sm" onclick="viewAmbulanceDetails({{ ambulance.id }})">
                                <i class="fas fa-eye"></i> View
                            </button>
                        </div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
                    <i class="fas fa-ambulance" style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></i>
                    <p>No ambulances found in your district.</p>
                </div>
            {% endif %}
        </div>
    </div>
</div>

<!-- Active Allocations -->
{% if active_allocations_list %}
<div class="section-card">
    <div class="section-header">
        <h3><i class="fas fa-hourglass-end"></i> Active Allocations ({{ active_allocations_list|length }})</h3>
    </div>
    <div class="section-body">
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>Ambulance</th>
                        <th>Driver</th>
                        <th>From Location</th>
                        <th>To Location</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for allocation in active_allocations_list %}
                    <tr>
                        <td><strong>{{ allocation.ambulance_number }}</strong></td>
                        <td>{{ allocation.driver_name or 'Not Assigned' }}</td>
                        <td>{{ allocation.source_location }}</td>
                        <td>{{ allocation.destination_location }}</td>
                        <td>
                            <span class="status-badge active">
                                <i class="fas fa-check-circle"></i> In Transit
                            </span>
                        </td>
                        <td>
                            <button class="btn btn-secondary btn-sm" onclick="completeAllocation({{ allocation.id }})">
                                <i class="fas fa-check"></i> Complete
                            </button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endif %}
"""
    
    full_new = content[:start] + new_content + content[end:]
    with open(r'templates\ddhs_admin_ambulances_redesigned.html', 'w', encoding='utf-8') as fw:
        fw.write(full_new)
    print('Successfully restructured layout!')
else:
    print('Tags not found')
