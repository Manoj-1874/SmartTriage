"""
REAL-TIME APPOINTMENT MANAGEMENT SYSTEM
- Doctor availability checking (prevent double-booking)
- Appointment lifecycle management (Scheduled → Completed/NoShow → Feedback)
- Automated reminders (24h, 1h, on-time)
- Notification system
- Performance feedback collection
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class AppointmentManager:
    """
    Manages appointment lifecycle with real-time features
    """

    # Appointment Status Constants
    STATUS_PENDING = 'Pending'
    STATUS_SCHEDULED = 'Scheduled'
    STATUS_CONFIRMED = 'Confirmed'
    STATUS_IN_PROGRESS = 'In Progress'
    STATUS_COMPLETED = 'Completed'
    STATUS_NO_SHOW = 'No-Show'
    STATUS_CANCELLED = 'Cancelled'
    STATUS_FEEDBACK_PENDING = 'Feedback Pending'

    # Reminder Types
    REMINDER_24H = '24h_before'
    REMINDER_1H = '1h_before'
    REMINDER_NOW = 'on_time'

    def __init__(self, db_connection):
        """Initialize with database connection"""
        self.conn = db_connection
        self.cursor = self.conn.cursor()

    def check_doctor_availability(self, doctor_id: int, appointment_date: str, appointment_time: str, duration_minutes: int = 30) -> Tuple[bool, Optional[str]]:
        """
        Check if doctor has availability at specified time (prevents double-booking)

        Args:
            doctor_id: Doctor's user ID
            appointment_date: Date in YYYY-MM-DD format
            appointment_time: Time in HH:MM format
            duration_minutes: Duration of appointment in minutes (default 30)

        Returns:
            (is_available, conflict_message)
        """
        try:
            # Parse appointment time
            appt_hour, appt_minute = map(int, appointment_time.split(':'))
            appt_start = appt_hour * 60 + appt_minute
            appt_end = appt_start + duration_minutes

            query = """
                SELECT id, appointment_time, status
                FROM appointments
                WHERE doctor_id = ?
                AND appointment_date = ?
                AND status IN (?, ?, ?)
            """

            self.cursor.execute(query, (
                doctor_id,
                appointment_date,
                self.STATUS_SCHEDULED,
                self.STATUS_CONFIRMED,
                self.STATUS_IN_PROGRESS
            ))

            conflicts = self.cursor.fetchall()

            for conflict_id, conflict_time, conflict_status in conflicts:
                c_hour, c_minute = map(int, conflict_time.split(':'))
                c_start = c_hour * 60 + c_minute
                c_end = c_start + duration_minutes

                # Check for time overlap
                if not (appt_end <= c_start or appt_start >= c_end):
                    conflicting_appt = self.cursor.execute(
                        "SELECT patient_name FROM appointments WHERE id = ?",
                        (conflict_id,)
                    ).fetchone()

                    patient_name = conflicting_appt[0] if conflicting_appt else "Unknown"
                    conflict_msg = f"Doctor already has appointment with {patient_name} at {conflict_time} on {appointment_date}"
                    logger.warning(f"[AVAILABILITY-CONFLICT] {conflict_msg}")
                    return False, conflict_msg

            logger.info(f"[AVAILABILITY-OK] Doctor {doctor_id} available on {appointment_date} at {appointment_time}")
            return True, None

        except Exception as e:
            logger.error(f"[AVAILABILITY-ERROR] {str(e)}")
            return False, str(e)

    def book_appointment(self, patient_id: int, patient_name: str, doctor_id: int,
                        doctor_name: str, appointment_date: str, appointment_time: str,
                        department: str, symptoms: str, notes: str = "", 
                        triage_log_id: Optional[int] = None) -> Tuple[bool, Optional[int], str]:
        """
        Book appointment with availability check and dual notifications
        """
        try:
            # Check availability first
            is_available, conflict_msg = self.check_doctor_availability(
                doctor_id, appointment_date, appointment_time
            )

            if not is_available:
                return False, None, conflict_msg

            # Book appointment
            self.cursor.execute("""
                INSERT INTO appointments
                (patient_id, patient_name, doctor_id, doctor_name, department,
                 appointment_date, appointment_time, status, symptoms, notes, 
                 triage_log_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id, patient_name, doctor_id, doctor_name, department,
                appointment_date, appointment_time, self.STATUS_SCHEDULED,
                symptoms, notes, triage_log_id,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))

            self.conn.commit()
            appointment_id = self.cursor.lastrowid

            # 1. NOTIFICATION FOR DOCTOR (To prepare for patient)
            self._create_notification(
                recipient_id=doctor_id,
                notification_type='appointment_booked',
                title=f"New Patient Booking: {patient_name}",
                message=f"Scheduled for {appointment_date} at {appointment_time}. AI Medical History attached.",
                related_id=appointment_id
            )

            # 2. NOTIFICATION FOR PATIENT (Confirmation)
            self._create_notification(
                recipient_id=patient_id,
                notification_type='appointment_confirmed',
                title="Appointment Confirmed",
                message=f"Your appointment with Dr. {doctor_name} is confirmed for {appointment_date} at {appointment_time}.",
                related_id=appointment_id
            )

            # Schedule reminders
            self._schedule_reminders(appointment_id, appointment_date, appointment_time)

            logger.info(f"[REAL-WORLD-BOOKING] ID: {appointment_id} | Nurse-Patient Sync Complete")
            return True, appointment_id, f"Appointment successfully booked for {patient_name}"

        except Exception as e:
            logger.error(f"[APPOINTMENT-ERROR] {str(e)}")
            return False, None, f"Booking failed: {str(e)}"

    def _schedule_reminders(self, appointment_id: int, appointment_date: str, appointment_time: str):
        """Schedule automated reminders"""
        try:
            appt_datetime = datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M")

            # 24-hour reminder
            reminder_24h = appt_datetime - timedelta(hours=24)
            # 1-hour reminder
            reminder_1h = appt_datetime - timedelta(hours=1)

            # Store reminders (in production, these would be handled by a task queue like Celery)
            self.cursor.execute("""
                INSERT OR IGNORE INTO appointment_reminders
                (appointment_id, reminder_type, scheduled_time, status)
                VALUES (?, ?, ?, ?)
            """, (appointment_id, self.REMINDER_24H, reminder_24h.isoformat(), 'pending'))

            self.cursor.execute("""
                INSERT OR IGNORE INTO appointment_reminders
                (appointment_id, reminder_type, scheduled_time, status)
                VALUES (?, ?, ?, ?)
            """, (appointment_id, self.REMINDER_1H, reminder_1h.isoformat(), 'pending'))

            self.conn.commit()
            logger.info(f"[REMINDERS-SCHEDULED] Appointment {appointment_id}")
        except Exception as e:
            logger.warning(f"[REMINDERS-ERROR] {str(e)}")

    def update_appointment_status(self, appointment_id: int, new_status: str) -> Tuple[bool, str]:
        """Update appointment status and trigger workflows"""
        try:
            old_status = self.cursor.execute(
                "SELECT status FROM appointments WHERE id = ?",
                (appointment_id,)
            ).fetchone()

            if not old_status:
                return False, "Appointment not found"

            old_status = old_status[0]

            # Validate status transition
            valid_transitions = {
                self.STATUS_SCHEDULED: [self.STATUS_CONFIRMED, self.STATUS_CANCELLED],
                self.STATUS_CONFIRMED: [self.STATUS_IN_PROGRESS, self.STATUS_NO_SHOW, self.STATUS_CANCELLED],
                self.STATUS_IN_PROGRESS: [self.STATUS_COMPLETED, self.STATUS_NO_SHOW],
                self.STATUS_COMPLETED: [self.STATUS_FEEDBACK_PENDING],
            }

            if old_status in valid_transitions and new_status not in valid_transitions[old_status]:
                return False, f"Invalid status transition from {old_status} to {new_status}"

            # Update status
            self.cursor.execute("""
                UPDATE appointments
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (new_status, datetime.now().isoformat(), appointment_id))

            self.conn.commit()

            # Trigger notifications based on status change
            appt = self.cursor.execute(
                "SELECT patient_id, doctor_id, patient_name, appointment_date FROM appointments WHERE id = ?",
                (appointment_id,)
            ).fetchone()

            if appt:
                patient_id, doctor_id, patient_name, appt_date = appt

                if new_status == self.STATUS_CONFIRMED:
                    self._create_notification(
                        recipient_id=patient_id,
                        notification_type='appointment_confirmed',
                        title="Appointment Confirmed",
                        message=f"Your appointment on {appt_date} has been confirmed by Dr. {doctor_name}.",
                        related_id=appointment_id
                    )
                elif new_status == self.STATUS_COMPLETED:
                    self._create_notification(
                        recipient_id=patient_id,
                        notification_type='appointment_completed',
                        title="Appointment Completed",
                        message=f"Your appointment on {appt_date} is complete. Please provide feedback.",
                        related_id=appointment_id
                    )
                elif new_status == self.STATUS_NO_SHOW:
                    self._create_notification(
                        recipient_id=patient_id,
                        notification_type='appointment_no_show',
                        title="No-Show Recorded",
                        message="You did not attend your scheduled appointment.",
                        related_id=appointment_id
                    )
                elif new_status == self.STATUS_CANCELLED:
                    self._create_notification(
                        recipient_id=patient_id,
                        notification_type='appointment_cancelled',
                        title="Appointment Cancelled",
                        message="Your appointment has been cancelled.",
                        related_id=appointment_id
                    )

            logger.info(f"[STATUS-UPDATE] Appointment {appointment_id}: {old_status} → {new_status}")
            return True, f"Status updated to {new_status}"

        except Exception as e:
            logger.error(f"[STATUS-UPDATE-ERROR] {str(e)}")
            return False, str(e)

    def mark_appointment_completed(self, appointment_id: int) -> Tuple[bool, str]:
        """Mark appointment as completed and request feedback"""
        return self.update_appointment_status(appointment_id, self.STATUS_FEEDBACK_PENDING)

    def record_no_show(self, appointment_id: int) -> Tuple[bool, str]:
        """Record patient no-show and expire appointment"""
        return self.update_appointment_status(appointment_id, self.STATUS_NO_SHOW)

    def get_patient_appointments(self, patient_id: int, status: Optional[str] = None) -> List[Dict]:
        """Get all appointments for a patient"""
        try:
            if status:
                query = "SELECT * FROM appointments WHERE patient_id = ? AND status = ? ORDER BY appointment_date DESC"
                self.cursor.execute(query, (patient_id, status))
            else:
                query = "SELECT * FROM appointments WHERE patient_id = ? ORDER BY appointment_date DESC"
                self.cursor.execute(query, (patient_id,))

            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"[GET-APPOINTMENTS-ERROR] {str(e)}")
            return []

    def get_doctor_appointments(self, doctor_id: int, appointment_date: Optional[str] = None) -> List[Dict]:
        """Get all appointments for a doctor on a specific date (or all upcoming)"""
        try:
            if appointment_date:
                query = """
                    SELECT * FROM appointments
                    WHERE doctor_id = ? AND appointment_date = ?
                    ORDER BY appointment_time
                """
                self.cursor.execute(query, (doctor_id, appointment_date))
            else:
                query = """
                    SELECT * FROM appointments
                    WHERE doctor_id = ? AND appointment_date >= DATE('now')
                    ORDER BY appointment_date, appointment_time
                """
                self.cursor.execute(query, (doctor_id,))

            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"[GET-DOCTOR-APPOINTMENTS-ERROR] {str(e)}")
            return []

    def _create_notification(self, recipient_id: int, notification_type: str,
                            title: str, message: str, related_id: Optional[int] = None) -> bool:
        """Create and store notification"""
        try:
            self.cursor.execute("""
                INSERT INTO notifications
                (recipient_id, notification_type, title, message, related_id, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (recipient_id, notification_type, title, message, related_id, 0, datetime.now().isoformat()))

            self.conn.commit()
            logger.info(f"[NOTIFICATION-CREATED] For user {recipient_id}: {title}")
            return True
        except Exception as e:
            logger.warning(f"[NOTIFICATION-ERROR] {str(e)}")
            return False

    def get_notifications(self, user_id: int, unread_only: bool = False) -> List[Dict]:
        """Get notifications for a user"""
        try:
            if unread_only:
                query = "SELECT * FROM notifications WHERE recipient_id = ? AND is_read = 0 ORDER BY created_at DESC"
                self.cursor.execute(query, (user_id,))
            else:
                query = "SELECT * FROM notifications WHERE recipient_id = ? ORDER BY created_at DESC LIMIT 50"
                self.cursor.execute(query, (user_id,))

            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"[GET-NOTIFICATIONS-ERROR] {str(e)}")
            return []

    def mark_notification_read(self, notification_id: int) -> bool:
        """Mark notification as read"""
        try:
            self.cursor.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = ?",
                (notification_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"[MARK-READ-ERROR] {str(e)}")
            return False

    def submit_feedback(self, appointment_id: int, rating: int, comments: str) -> Tuple[bool, str]:
        """Submit post-appointment feedback"""
        try:
            if not (1 <= rating <= 5):
                return False, "Rating must be between 1 and 5"

            self.cursor.execute("""
                INSERT INTO appointment_feedback
                (appointment_id, rating, comments, created_at)
                VALUES (?, ?, ?, ?)
            """, (appointment_id, rating, comments, datetime.now().isoformat()))

            # Update appointment status
            self.cursor.execute(
                "UPDATE appointments SET status = ? WHERE id = ?",
                (self.STATUS_COMPLETED, appointment_id)
            )

            self.conn.commit()
            logger.info(f"[FEEDBACK-SUBMITTED] Appointment {appointment_id}, Rating: {rating}")
            return True, "Feedback submitted successfully"
        except Exception as e:
            logger.error(f"[FEEDBACK-ERROR] {str(e)}")
            return False, str(e)

    def get_feedback(self, appointment_id: int) -> Optional[Dict]:
        """Retrieve feedback for an appointment"""
        try:
            self.cursor.execute("SELECT * FROM appointment_feedback WHERE appointment_id = ?", (appointment_id,))
            row = self.cursor.fetchone()
            if row:
                columns = [description[0] for description in self.cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"[GET-FEEDBACK-ERROR] {str(e)}")
            return None

    def check_and_expire_appointments(self) -> int:
        """Check for missed appointments and mark as expired (background task)"""
        try:
            # Get appointments that were scheduled for the past without status update
            self.cursor.execute("""
                SELECT id, appointment_date, appointment_time FROM appointments
                WHERE status IN (?, ?)
                AND appointment_date < DATE('now')
            """, (self.STATUS_SCHEDULED, self.STATUS_CONFIRMED))

            expired_appointments = self.cursor.fetchall()
            count = 0

            for appt_id, appt_date, appt_time in expired_appointments:
                success, _ = self.record_no_show(appt_id)
                if success:
                    count += 1

            logger.info(f"[EXPIRY-CHECK] Marked {count} appointments as expired")
            return count
        except Exception as e:
            logger.error(f"[EXPIRY-CHECK-ERROR] {str(e)}")
            return 0
