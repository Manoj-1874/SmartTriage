"""
APPOINTMENT MANAGEMENT ROUTES
Real-time appointment booking, status tracking, messaging, and feedback
"""

from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging
from utils.appointment_manager import AppointmentManager
from utils.database import db_manager

appointments_bp = Blueprint('appointments', __name__, url_prefix='/appointments')
logger = logging.getLogger(__name__)


def get_appointment_manager():
    """Get appointment manager with current database connection"""
    conn = db_manager.get_connection()
    return AppointmentManager(conn)


# ===========================
# APPOINTMENT BOOKING ROUTES
# ===========================

@appointments_bp.route('/available-slots', methods=['POST'])
@login_required
def get_available_slots():
    """Get available appointment slots for a doctor on a specific date"""
    try:
        data = request.json
        doctor_id = data.get('doctor_id')
        appointment_date = data.get('date')  # YYYY-MM-DD

        if not doctor_id or not appointment_date:
            return jsonify({'error': 'Missing doctor_id or date'}), 400

        manager = get_appointment_manager()

        # Define available time slots (9 AM to 5 PM, 30-minute slots)
        available_slots = []
        for hour in range(9, 17):
            for minute in [0, 30]:
                time_str = f"{hour:02d}:{minute:02d}"
                is_available, _ = manager.check_doctor_availability(
                    doctor_id, appointment_date, time_str, duration_minutes=30
                )

                if is_available:
                    available_slots.append({
                        'time': time_str,
                        'display': f"{hour:02d}:{minute:02d} {'AM' if hour < 12 else 'PM'}"
                    })

        logger.info(f"[AVAILABLE-SLOTS] Doctor {doctor_id} on {appointment_date}: {len(available_slots)} slots")
        return jsonify({
            'success': True,
            'doctor_id': doctor_id,
            'date': appointment_date,
            'available_slots': available_slots,
            'total_slots': len(available_slots)
        })
    except Exception as e:
        logger.error(f"[SLOTS-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@appointments_bp.route('/book', methods=['POST'])
@login_required
def book_appointment():
    """Book a new appointment"""
    try:
        data = request.json

        # Validate required fields
        required_fields = ['doctor_id', 'doctor_name', 'appointment_date', 'appointment_time',
                          'department', 'symptoms']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400

        manager = get_appointment_manager()

        success, appointment_id, message = manager.book_appointment(
            patient_id=data.get('patient_id', current_user.id),
            patient_name=data.get('patient_name', current_user.fullname),
            doctor_id=data['doctor_id'],
            doctor_name=data['doctor_name'],
            appointment_date=data['appointment_date'],
            appointment_time=data['appointment_time'],
            department=data['department'],
            symptoms=data['symptoms'],
            notes=data.get('notes', ''),
            triage_log_id=data.get('triage_log_id')
        )

        if success:
            return jsonify({
                'success': True,
                'appointment_id': appointment_id,
                'message': message
            }), 201
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        logger.error(f"[BOOKING-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@appointments_bp.route('/<int:appointment_id>/confirm', methods=['POST'])
@login_required
def confirm_appointment(appointment_id):
    """Doctor confirms appointment"""
    try:
        manager = get_appointment_manager()
        success, message = manager.update_appointment_status(
            appointment_id,
            AppointmentManager.STATUS_CONFIRMED
        )

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        logger.error(f"[CONFIRM-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@appointments_bp.route('/<int:appointment_id>/start', methods=['POST'])
@login_required
def start_appointment(appointment_id):
    """Mark appointment as in-progress"""
    try:
        manager = get_appointment_manager()
        success, message = manager.update_appointment_status(
            appointment_id,
            AppointmentManager.STATUS_IN_PROGRESS
        )

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        logger.error(f"[START-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@appointments_bp.route('/<int:appointment_id>/complete', methods=['POST'])
@login_required
def complete_appointment(appointment_id):
    """Mark appointment as completed"""
    try:
        manager = get_appointment_manager()
        success, message = manager.mark_appointment_completed(appointment_id)

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        logger.error(f"[COMPLETE-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@appointments_bp.route('/<int:appointment_id>/no-show', methods=['POST'])
@login_required
def mark_no_show(appointment_id):
    """Record patient no-show"""
    try:
        manager = get_appointment_manager()
        success, message = manager.record_no_show(appointment_id)

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        logger.error(f"[NO-SHOW-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@appointments_bp.route('/<int:appointment_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    """Cancel an appointment"""
    try:
        manager = get_appointment_manager()
        success, message = manager.update_appointment_status(
            appointment_id,
            AppointmentManager.STATUS_CANCELLED
        )

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        logger.error(f"[CANCEL-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===========================
# APPOINTMENT RETRIEVAL ROUTES
# ===========================

@appointments_bp.route('/my-appointments', methods=['GET'])
@login_required
def my_appointments():
    """Get current user's appointments"""
    try:
        manager = get_appointment_manager()

        # Get based on user role
        if current_user.role == 'patient':
            appointments = manager.get_patient_appointments(current_user.id)
        elif current_user.role == 'phc_nurse':
            # Get as doctor
            appointment_date = request.args.get('date')
            appointments = manager.get_doctor_appointments(current_user.id, appointment_date)
        else:
            appointments = []

        return jsonify({
            'success': True,
            'appointments': appointments,
            'total': len(appointments)
        })
    except Exception as e:
        logger.error(f"[GET-APPOINTMENTS-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@appointments_bp.route('/<int:appointment_id>', methods=['GET'])
@login_required
def get_appointment_details(appointment_id):
    """Get detailed appointment information"""
    try:
        manager = get_appointment_manager()

        # Get appointment
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()

        if not row:
            return jsonify({'error': 'Appointment not found'}), 404

        appointment = dict(zip(columns, row))

        # Get feedback if exists
        feedback = manager.get_feedback(appointment_id)
        appointment['feedback'] = feedback

        # Get notifications
        notifications = manager.get_notifications(current_user.id)
        appointment['notifications'] = notifications

        conn.close()

        return jsonify({
            'success': True,
            'appointment': appointment
        })
    except Exception as e:
        logger.error(f"[DETAIL-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===========================
# MESSAGING ROUTES
# ===========================

@appointments_bp.route('/messages/<int:appointment_id>', methods=['GET'])
@login_required
def get_messages(appointment_id):
    """Get all messages for an appointment conversation"""
    try:
        # Get appointment to find the other user
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT patient_id, doctor_id FROM appointments WHERE id = ?",
            (appointment_id,)
        )
        result = cursor.fetchone()

        if not result:
            conn.close()
            return jsonify({'error': 'Appointment not found'}), 404

        patient_id, doctor_id = result

        # Get messages between current user and the other party
        other_user_id = doctor_id if current_user.id == patient_id else patient_id

        cursor.execute("""
            SELECT * FROM messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY created_at ASC
        """, (current_user.id, other_user_id, other_user_id, current_user.id))

        columns = [description[0] for description in cursor.description]
        messages = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Mark messages as read
        cursor.execute("""
            UPDATE messages
            SET is_read = 1
            WHERE receiver_id = ? AND sender_id = ? AND is_read = 0
        """, (current_user.id, other_user_id))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'appointment_id': appointment_id,
            'messages': messages
        })
    except Exception as e:
        logger.error(f"[GET-MESSAGES-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@appointments_bp.route('/messages/<int:appointment_id>/send', methods=['POST'])
@login_required
def send_message(appointment_id):
    """Send a message in appointment conversation"""
    try:
        data = request.json
        message_text = data.get('message')

        if not message_text or not message_text.strip():
            return jsonify({'error': 'Message cannot be empty'}), 400

        conn = db_manager.get_connection()
        cursor = conn.cursor()

        # Get appointment
        cursor.execute(
            "SELECT patient_id, doctor_id FROM appointments WHERE id = ?",
            (appointment_id,)
        )
        result = cursor.fetchone()

        if not result:
            conn.close()
            return jsonify({'error': 'Appointment not found'}), 404

        patient_id, doctor_id = result

        # Determine receiver
        receiver_id = doctor_id if current_user.id == patient_id else patient_id

        # Store message
        cursor.execute("""
            INSERT INTO messages (sender_id, receiver_id, message, is_read, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (current_user.id, receiver_id, message_text, 0, datetime.now().isoformat()))

        message_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"[MESSAGE-SENT] From {current_user.id} to {receiver_id} for appointment {appointment_id}")

        return jsonify({
            'success': True,
            'message_id': message_id,
            'message': 'Message sent successfully'
        }), 201
    except Exception as e:
        logger.error(f"[SEND-MESSAGE-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===========================
# NOTIFICATION ROUTES
# ===========================

@appointments_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    """Get notifications for current user"""
    try:
        manager = get_appointment_manager()
        unread_only = request.args.get('unread', 'false').lower() == 'true'

        notifications = manager.get_notifications(current_user.id, unread_only=unread_only)

        return jsonify({
            'success': True,
            'notifications': notifications,
            'total': len(notifications)
        })
    except Exception as e:
        logger.error(f"[GET-NOTIFICATIONS-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@appointments_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        manager = get_appointment_manager()
        success = manager.mark_notification_read(notification_id)

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to mark notification as read'}), 400
    except Exception as e:
        logger.error(f"[MARK-READ-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===========================
# FEEDBACK ROUTES
# ===========================

@appointments_bp.route('/<int:appointment_id>/feedback', methods=['POST'])
@login_required
def submit_feedback(appointment_id):
    """Submit feedback for completed appointment"""
    try:
        data = request.json
        rating = data.get('rating')
        comments = data.get('comments', '')

        if not rating:
            return jsonify({'error': 'Rating is required'}), 400

        manager = get_appointment_manager()
        success, message = manager.submit_feedback(appointment_id, rating, comments)

        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 201
        else:
            return jsonify({'error': message}), 400
    except Exception as e:
        logger.error(f"[FEEDBACK-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


@appointments_bp.route('/<int:appointment_id>/feedback', methods=['GET'])
@login_required
def get_feedback(appointment_id):
    """Get feedback for an appointment"""
    try:
        manager = get_appointment_manager()
        feedback = manager.get_feedback(appointment_id)

        if feedback:
            return jsonify({
                'success': True,
                'feedback': feedback
            })
        else:
            return jsonify({
                'success': True,
                'feedback': None,
                'message': 'No feedback yet'}
            )
    except Exception as e:
        logger.error(f"[GET-FEEDBACK-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===========================
# ADMIN ROUTES
# ===========================

@appointments_bp.route('/expire-old', methods=['POST'])
@login_required
def expire_old_appointments():
    """Background task: Mark old appointments as expired (admin only)"""
    try:
        if current_user.role not in ['admin', 'phc_admin']:
            return jsonify({'error': 'Access denied'}), 403

        manager = get_appointment_manager()
        count = manager.check_and_expire_appointments()

        return jsonify({
            'success': True,
            'expired_count': count
        })
    except Exception as e:
        logger.error(f"[EXPIRE-ERROR] {str(e)}")
        return jsonify({'error': str(e)}), 500
