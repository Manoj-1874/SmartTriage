"""
AUTOMATED APPOINTMENT REMINDER SCHEDULER
Sends reminders at scheduled times (24h before, 1h before, on-time)
Can be run as a background task or integrated with Celery/APScheduler
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from utils.appointment_manager import AppointmentManager
from utils.database import db_manager

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """
    Background scheduler for appointment reminders
    Runs as a separate thread and checks for pending reminders
    """

    def __init__(self, check_interval_seconds: int = 60):
        """
        Initialize reminder scheduler

        Args:
            check_interval_seconds: How often to check for pending reminders (default 60s)
        """
        self.check_interval = check_interval_seconds
        self.running = False
        self.thread = None

    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            logger.warning("[SCHEDULER] Already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"[SCHEDULER] Started with {self.check_interval}s check interval")

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("[SCHEDULER] Stopped")

    def _run(self):
        """Main scheduler loop (runs in background thread)"""
        while self.running:
            try:
                self._check_and_send_reminders()
            except Exception as e:
                logger.error(f"[SCHEDULER-ERROR] {str(e)}")

            # Sleep for check interval
            time.sleep(self.check_interval)

    def _check_and_send_reminders(self):
        """Check for pending reminders and send them"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                now = datetime.now().isoformat()

                # Get all pending reminders that are due
                cursor.execute("""
                    SELECT id, appointment_id, reminder_type FROM appointment_reminders
                    WHERE status = 'pending' AND scheduled_time <= ?
                    LIMIT 100
                """, (now,))

                pending_reminders = cursor.fetchall()

                if pending_reminders:
                    logger.info(f"[REMINDERS] Found {len(pending_reminders)} pending reminders to send")

                for reminder_id, appointment_id, reminder_type in pending_reminders:
                    try:
                        self._send_reminder(cursor, conn, reminder_id, appointment_id, reminder_type)
                    except Exception as e:
                        logger.error(f"[REMINDER-ERROR] ID {reminder_id}: {str(e)}")
        except Exception as e:
            logger.error(f"[SCHEDULER-CHECK-ERROR] {str(e)}")

    def _send_reminder(self, cursor, conn, reminder_id: int, appointment_id: int, reminder_type: str):
        """Send a specific reminder"""
        try:
            # Get appointment details
            cursor.execute("""
                SELECT patient_id, patient_name, doctor_id, doctor_name,
                       appointment_date, appointment_time
                FROM appointments WHERE id = ?
            """, (appointment_id,))

            result = cursor.fetchone()
            if not result:
                logger.warning(f"[REMINDER] Appointment {appointment_id} not found")
                return

            (patient_id, patient_name, doctor_id, doctor_name,
             appointment_date, appointment_time) = result

            # Create reminders for both patient and doctor
            reminder_messages = {
                '24h_before': {
                    'patient_title': f"Appointment Reminder - Tomorrow",
                    'patient_msg': f"Your appointment with Dr. {doctor_name} is tomorrow at {appointment_time}",
                    'doctor_title': f"Appointment Tomorrow",
                    'doctor_msg': f"You have appointment with {patient_name} tomorrow at {appointment_time}"
                },
                '1h_before': {
                    'patient_title': f"Appointment in 1 Hour",
                    'patient_msg': f"Your appointment with Dr. {doctor_name} is in 1 hour at {appointment_time}",
                    'doctor_title': f"Appointment in 1 Hour",
                    'doctor_msg': f"You have appointment with {patient_name} in 1 hour at {appointment_time}"
                },
                'on_time': {
                    'patient_title': f"Time for Your Appointment",
                    'patient_msg': f"Your appointment with Dr. {doctor_name} is now. Please go to the reception.",
                    'doctor_title': f"Patient Arriving",
                    'doctor_msg': f"{patient_name} is arriving for their appointment"
                }
            }

            if reminder_type not in reminder_messages:
                logger.warning(f"[REMINDER] Unknown reminder type: {reminder_type}")
                return

            messages = reminder_messages[reminder_type]

            # Send to patient
            cursor.execute("""
                INSERT INTO notifications
                (recipient_id, notification_type, title, message, related_id, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (patient_id, 'appointment_reminder', messages['patient_title'],
                  messages['patient_msg'], appointment_id, 0, datetime.now().isoformat()))

            # Send to doctor
            cursor.execute("""
                INSERT INTO notifications
                (recipient_id, notification_type, title, message, related_id, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (doctor_id, 'appointment_reminder', messages['doctor_title'],
                  messages['doctor_msg'], appointment_id, 0, datetime.now().isoformat()))

            # Mark reminder as sent
            cursor.execute("""
                UPDATE appointment_reminders
                SET status = 'sent', sent_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), reminder_id))

            conn.commit()

            logger.info(f"[REMINDER-SENT] ID {reminder_id}, Type: {reminder_type}, Appointment: {appointment_id}")
        except Exception as e:
            logger.error(f"[SEND-REMINDER-ERROR] {str(e)}")

    def reschedule_reminders(self, appointment_id: int, new_date: str, new_time: str) -> bool:
        """Reschedule reminders for an appointment (if date/time changed)"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                appt_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")

                # 24-hour reminder
                reminder_24h = appt_datetime - timedelta(hours=24)
                # 1-hour reminder
                reminder_1h = appt_datetime - timedelta(hours=1)

                # Update reminders
                cursor.execute("""
                    UPDATE appointment_reminders
                    SET scheduled_time = ?, status = 'pending'
                    WHERE appointment_id = ? AND reminder_type = '24h_before'
                """, (reminder_24h.isoformat(), appointment_id))

                cursor.execute("""
                    UPDATE appointment_reminders
                    SET scheduled_time = ?, status = 'pending'
                    WHERE appointment_id = ? AND reminder_type = '1h_before'
                """, (reminder_1h.isoformat(), appointment_id))

                logger.info(f"[REMINDERS-RESCHEDULED] Appointment {appointment_id} to {new_date} {new_time}")
                return True
        except Exception as e:
            logger.error(f"[RESCHEDULE-ERROR] {str(e)}")
            return False


# Global scheduler instance
_global_scheduler = None


def get_reminder_scheduler() -> ReminderScheduler:
    """Get or create global reminder scheduler"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = ReminderScheduler(check_interval_seconds=60)
    return _global_scheduler


def start_reminder_scheduler():
    """Start the global reminder scheduler"""
    scheduler = get_reminder_scheduler()
    scheduler.start()


def stop_reminder_scheduler():
    """Stop the global reminder scheduler"""
    if _global_scheduler:
        _global_scheduler.stop()
