"""
REAL-TIME NOTIFICATIONS SYSTEM USING WEBSOCKETS
Enables live updates for appointments, messages, and notifications
Uses Flask-SocketIO for real-time bidirectional communication
"""

from flask import session, request
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

# Global SocketIO instance (will be initialized in app.py)
socketio = None


def init_socketio(app):
    """Initialize SocketIO with Flask app"""
    global socketio
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        logger=True,
        engineio_logger=True
    )

    # Register event handlers
    socketio.on_event('connect', handle_connect)
    socketio.on_event('disconnect', handle_disconnect)
    socketio.on_event('join_appointment', handle_join_appointment)
    socketio.on_event('leave_appointment', handle_leave_appointment)
    socketio.on_event('new_message', handle_new_message)
    socketio.on_event('mark_notification_read', handle_mark_notification_read)

    logger.info("[SOCKETIO] WebSocket server initialized")
    return socketio


# ===========================
# CONNECTION HANDLERS
# ===========================

def handle_connect():
    """Handle client connection"""
    try:
        if not current_user.is_authenticated:
            logger.warning(f"[WEBSOCKET] Unauthenticated connection attempt")
            return False

        user_room = f"user_{current_user.id}"
        join_room(user_room)

        logger.info(f"[WEBSOCKET] User {current_user.id} connected (room: {user_room})")

        emit('connection_response', {
            'status': 'connected',
            'user_id': current_user.id,
            'username': current_user.username,
            'room': user_room
        })
        return True
    except Exception as e:
        logger.error(f"[WEBSOCKET-CONNECT-ERROR] {str(e)}")
        return False


def handle_disconnect():
    """Handle client disconnection"""
    try:
        if current_user.is_authenticated:
            logger.info(f"[WEBSOCKET] User {current_user.id} disconnected")
    except Exception as e:
        logger.error(f"[WEBSOCKET-DISCONNECT-ERROR] {str(e)}")


def handle_join_appointment(data):
    """Handle user joining an appointment room for real-time updates"""
    try:
        appointment_id = data.get('appointment_id')
        if not appointment_id:
            emit('error', {'message': 'Missing appointment_id'})
            return

        room = f"appointment_{appointment_id}"
        join_room(room)

        logger.info(f"[WEBSOCKET] User {current_user.id} joined appointment room: {room}")

        # Notify others in the room
        emit('user_joined', {
            'user_id': current_user.id,
            'username': current_user.username,
            'appointment_id': appointment_id
        }, room=room)
    except Exception as e:
        logger.error(f"[WEBSOCKET-JOIN-ERROR] {str(e)}")
        emit('error', {'message': str(e)})


def handle_leave_appointment(data):
    """Handle user leaving an appointment room"""
    try:
        appointment_id = data.get('appointment_id')
        if not appointment_id:
            return

        room = f"appointment_{appointment_id}"
        leave_room(room)

        logger.info(f"[WEBSOCKET] User {current_user.id} left appointment room: {room}")

        # Notify others in the room
        emit('user_left', {
            'user_id': current_user.id,
            'username': current_user.username,
            'appointment_id': appointment_id
        }, room=room)
    except Exception as e:
        logger.error(f"[WEBSOCKET-LEAVE-ERROR] {str(e)}")


# ===========================
# MESSAGING HANDLERS
# ===========================

def handle_new_message(data):
    """Handle new message in appointment conversation"""
    try:
        appointment_id = data.get('appointment_id')
        message_text = data.get('message')

        if not appointment_id or not message_text:
            emit('error', {'message': 'Missing appointment_id or message'})
            return

        room = f"appointment_{appointment_id}"

        # Broadcast message to all users in this appointment
        emit('message_received', {
            'user_id': current_user.id,
            'username': current_user.username,
            'message': message_text,
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'appointment_id': appointment_id
        }, room=room, include_self=True)

        logger.info(f"[WEBSOCKET-MESSAGE] User {current_user.id} sent message in appointment {appointment_id}")
    except Exception as e:
        logger.error(f"[WEBSOCKET-MESSAGE-ERROR] {str(e)}")
        emit('error', {'message': str(e)})


def handle_mark_notification_read(data):
    """Handle marking notification as read"""
    try:
        notification_id = data.get('notification_id')
        if not notification_id:
            return

        # This would call the database here
        # For now, just emit acknowledgment
        emit('notification_read_ack', {
            'notification_id': notification_id,
            'status': 'marked_read'
        })

        logger.info(f"[WEBSOCKET-READ] Notification {notification_id} marked as read by user {current_user.id}")
    except Exception as e:
        logger.error(f"[WEBSOCKET-READ-ERROR] {str(e)}")


# ===========================
# BROADCAST FUNCTIONS (Called from Python backend)
# ===========================

def broadcast_appointment_update(appointment_id: int, update_data: dict):
    """Broadcast appointment status update to relevant users"""
    try:
        room = f"appointment_{appointment_id}"
        socketio.emit('appointment_updated', {
            'appointment_id': appointment_id,
            **update_data
        }, room=room)
        logger.info(f"[BROADCAST] Appointment {appointment_id} update sent")
    except Exception as e:
        logger.error(f"[BROADCAST-UPDATE-ERROR] {str(e)}")


def broadcast_notification(user_id: int, notification_data: dict):
    """Broadcast notification to a specific user"""
    try:
        room = f"user_{user_id}"
        socketio.emit('notification', notification_data, room=room)
        logger.info(f"[BROADCAST] Notification sent to user {user_id}")
    except Exception as e:
        logger.error(f"[BROADCAST-NOTIFICATION-ERROR] {str(e)}")


def broadcast_reminder(appointment_id: int, reminder_data: dict):
    """Broadcast appointment reminder"""
    try:
        room = f"appointment_{appointment_id}"
        socketio.emit('reminder', reminder_data, room=room)
        logger.info(f"[BROADCAST] Reminder sent for appointment {appointment_id}")
    except Exception as e:
        logger.error(f"[BROADCAST-REMINDER-ERROR] {str(e)}")


def notify_appointment_status_change(appointment_id: int, patient_id: int, doctor_id: int, status: str, message: str):
    """Notify both patient and doctor of appointment status change"""
    try:
        update_data = {
            'status': status,
            'message': message,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

        # Notify patient
        broadcast_notification(patient_id, {
            'type': 'appointment_status_change',
            'appointment_id': appointment_id,
            'status': status,
            'message': message
        })

        # Notify doctor
        broadcast_notification(doctor_id, {
            'type': 'appointment_status_change',
            'appointment_id': appointment_id,
            'status': status,
            'message': message
        })

        # Broadcast to appointment room
        broadcast_appointment_update(appointment_id, update_data)

        logger.info(f"[NOTIFY] Appointment {appointment_id} status changed to {status}")
    except Exception as e:
        logger.error(f"[NOTIFY-ERROR] {str(e)}")
