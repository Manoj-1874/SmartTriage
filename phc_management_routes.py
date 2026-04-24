"""
PHC Management API Endpoints
Enables DDHS Admins to manage PHC facility status and operations
"""

# Add these endpoints to app.py routes section

def create_phc_management_routes():
    """Generate PHC management route code to add to app.py"""

    code = '''
# ===================================
# PHC MANAGEMENT ROUTES (DDHS Admin Only)
# ===================================

@app.route('/api/phc/list', methods=['GET'])
@require_role(['ddhs_admin'])
@login_required
def api_phc_list():
    """Get list of all PHC facilities with status"""
    try:
        conn = get_db_connection()
        phcs = conn.execute('''
            SELECT id, name, location, contact, status, created_at, updated_at
            FROM phc_facilities
            ORDER BY id
        ''').fetchall()

        phc_list = []
        for phc in phcs:
            # Count staff at each PHC
            staff_count = conn.execute(
                'SELECT COUNT(DISTINCT user_id) as count FROM users WHERE phc_id=? AND role IN ("doctor", "phc_nurse")',
                (phc['id'],)
            ).fetchone()['count']

            # Count patients at each PHC
            patient_count = conn.execute(
                'SELECT COUNT(*) as count FROM users WHERE phc_id=? AND role="patient"',
                (phc['id'],)
            ).fetchone()['count']

            phc_list.append({
                'id': phc['id'],
                'name': phc['name'],
                'location': phc['location'],
                'contact': phc['contact'],
                'status': phc['status'],
                'staff_count': staff_count,
                'patient_count': patient_count,
                'created_at': phc['created_at'],
                'updated_at': phc['updated_at']
            })

        conn.close()

        audit_action(
            current_user.email,
            'PHC_LIST_VIEWED',
            f'Viewed {len(phc_list)} PHC facilities',
            'SUCCESS'
        )

        return jsonify({
            'status': 'success',
            'data': phc_list,
            'total': len(phc_list)
        }), 200

    except Exception as e:
        app.logger.error(f"Error fetching PHC list: {str(e)}")
        audit_action(
            current_user.email,
            'PHC_LIST_FAILED',
            f'Error: {str(e)}',
            'FAILED'
        )
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/phc/<int:phc_id>/status', methods=['PUT'])
@require_role(['ddhs_admin'])
@login_required
def api_phc_update_status(phc_id):
    """Update PHC facility status (ACTIVE/INACTIVE/MAINTENANCE)"""
    try:
        data = request.get_json()
        new_status = data.get('status', '').upper()
        reason = InputSanitizer.sanitize_string(data.get('reason', ''), max_length=500)

        # Validate status
        valid_statuses = ['ACTIVE', 'INACTIVE', 'MAINTENANCE']
        if new_status not in valid_statuses:
            return jsonify({
                'status': 'error',
                'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400

        conn = get_db_connection()

        # Check if PHC exists
        phc = conn.execute('SELECT id, name, status FROM phc_facilities WHERE id=?', (phc_id,)).fetchone()
        if not phc:
            return jsonify({'status': 'error', 'message': 'PHC not found'}), 404

        old_status = phc['status']

        # Update status
        conn.execute(
            'UPDATE phc_facilities SET status=?, updated_at=datetime("now") WHERE id=?',
            (new_status, phc_id)
        )
        conn.commit()

        # Log audit trail
        audit_action(
            current_user.email,
            'PHC_STATUS_CHANGED',
            f'PHC {phc_id} ({phc["name"]}): {old_status} → {new_status} | Reason: {reason}',
            'SUCCESS'
        )

        conn.close()

        return jsonify({
            'status': 'success',
            'message': f'PHC status updated from {old_status} to {new_status}',
            'phc_id': phc_id,
            'new_status': new_status
        }), 200

    except Exception as e:
        app.logger.error(f"Error updating PHC status: {str(e)}")
        audit_action(
            current_user.email,
            'PHC_STATUS_UPDATE_FAILED',
            f'PHC {phc_id}: {str(e)}',
            'FAILED'
        )
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/phc/<int:phc_id>/staff', methods=['GET'])
@require_role(['ddhs_admin', 'phc_nurse', 'doctor'])
@login_required
def api_phc_staff(phc_id):
    """Get staff assigned to a PHC facility"""
    try:
        conn = get_db_connection()

        # Verify user has access to this PHC (either admin or assigned to PHC)
        if current_user.role != 'ddhs_admin' and current_user.phc_id != phc_id:
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403

        staff = conn.execute('''
            SELECT id, fullname, role, email, phone, phc_id
            FROM users
            WHERE phc_id=? AND role IN ("doctor", "phc_nurse")
            ORDER BY role, fullname
        ''', (phc_id,)).fetchall()

        staff_list = [dict(s) for s in staff]
        conn.close()

        return jsonify({
            'status': 'success',
            'data': staff_list,
            'total': len(staff_list)
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/phc/<int:phc_id>/patients', methods=['GET'])
@require_role(['ddhs_admin', 'phc_nurse', 'doctor'])
@login_required
def api_phc_patients(phc_id):
    """Get patients assigned to a PHC facility"""
    try:
        conn = get_db_connection()

        # Verify user has access (admin sees all, others see only their PHC)
        if current_user.role != 'ddhs_admin' and current_user.phc_id != phc_id:
            return jsonify({'status': 'error', 'message': 'Access denied'}), 403

        patients = conn.execute('''
            SELECT id, fullname, email, phone, location, phc_id
            FROM users
            WHERE phc_id=? AND role="patient"
            ORDER BY fullname
        ''', (phc_id,)).fetchall()

        patient_list = [dict(p) for p in patients]
        conn.close()

        return jsonify({
            'status': 'success',
            'data': patient_list,
            'total': len(patient_list)
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/phc/management', methods=['GET'])
@require_role(['ddhs_admin'])
@login_required
def phc_management_dashboard():
    """DDHS Admin Dashboard for PHC Management"""
    try:
        conn = get_db_connection()

        # Get all PHCs with stats
        phcs = conn.execute('''
            SELECT id, name, location, status FROM phc_facilities ORDER BY id
        ''').fetchall()

        phc_stats = []
        for phc in phcs:
            doctors = conn.execute(
                'SELECT COUNT(*) as count FROM users WHERE phc_id=? AND role="doctor"',
                (phc['id'],)
            ).fetchone()['count']

            nurses = conn.execute(
                'SELECT COUNT(*) as count FROM users WHERE phc_id=? AND role="phc_nurse"',
                (phc['id'],)
            ).fetchone()['count']

            patients = conn.execute(
                'SELECT COUNT(*) as count FROM users WHERE phc_id=? AND role="patient"',
                (phc['id'],)
            ).fetchone()['count']

            phc_stats.append({
                'id': phc['id'],
                'name': phc['name'],
                'location': phc['location'],
                'status': phc['status'],
                'doctors': doctors,
                'nurses': nurses,
                'patients': patients,
                'total_staff': doctors + nurses
            })

        conn.close()

        return render_template('phc_management.html', phcs=phc_stats)

    except Exception as e:
        app.logger.error(f"Error loading PHC management: {str(e)}")
        flash('Error loading PHC management dashboard', 'error')
        return redirect(url_for('dashboard'))
'''

    return code

if __name__ == '__main__':
    print("PHC Management API Endpoints")
    print("=" * 80)
    print(create_phc_management_routes())
