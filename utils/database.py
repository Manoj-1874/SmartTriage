"""
Database Utilities for SmartTriage Dashboard
Supports both SQLite and PostgreSQL with abstraction layer
"""
import sqlite3
from contextlib import contextmanager
from config import Config


class DatabaseManager:
    """Database connection manager supporting SQLite and PostgreSQL"""

    def __init__(self, config):
        self.config = config
        self.db_type = config.DATABASE_TYPE

        if self.db_type == 'postgresql':
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                self.psycopg2 = psycopg2
                self.RealDictCursor = RealDictCursor
                self.available = True
            except ImportError:
                print("Warning: psycopg2 not installed. Falling back to SQLite.")
                self.db_type = 'sqlite'
                self.available = False
        else:
            self.available = True

    @contextmanager
    def get_connection(self):
        """
        Get database connection as context manager
        Automatically handles commit/rollback and connection closing
        """
        if self.db_type == 'postgresql' and self.available:
            conn = self.psycopg2.connect(
                host=self.config.POSTGRES_HOST,
                port=self.config.POSTGRES_PORT,
                database=self.config.POSTGRES_DB,
                user=self.config.POSTGRES_USER,
                password=self.config.POSTGRES_PASSWORD,
                cursor_factory=self.RealDictCursor
            )
        else:
            # Extract database file path from DATABASE_URL
            db_path = self.config.DATABASE_URL.replace('sqlite:///', '')
            if db_path == ':memory:':
                db_path = ':memory:'

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row

        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """
        Execute a query and optionally return results

        Args:
            query: SQL query string
            params: Query parameters (tuple or dict)
            fetch_one: Return single result
            fetch_all: Return all results

        Returns:
            Query results or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch_one:
                result = cursor.fetchone()
                return dict(result) if result else None
            elif fetch_all:
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                return cursor.lastrowid

    def get_placeholder(self):
        """Get the appropriate parameter placeholder for the database"""
        if self.db_type == 'postgresql':
            return '%s'
        else:
            return '?'

    def adapt_query(self, query):
        """
        Adapt SQL query from SQLite style to PostgreSQL style if needed
        Converts '?' placeholders to '%s' for PostgreSQL
        """
        if self.db_type == 'postgresql':
            # Replace ? with %s for PostgreSQL
            return query.replace('?', '%s')
        return query

    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Users table
            users_table = """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY """ + ("AUTOINCREMENT" if self.db_type == 'sqlite' else "") + """,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                fullname TEXT NOT NULL,
                role TEXT NOT NULL,
                phone TEXT,
                specialization TEXT,
                license TEXT,
                experience TEXT,
                email_verified INTEGER DEFAULT 0,
                verification_token TEXT,
                verification_expires TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """

            # For PostgreSQL, use SERIAL instead of INTEGER PRIMARY KEY AUTOINCREMENT
            if self.db_type == 'postgresql':
                users_table = """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    fullname TEXT NOT NULL,
                    role TEXT NOT NULL,
                    phone TEXT,
                    specialization TEXT,
                    license TEXT,
                    experience TEXT,
                    email_verified INTEGER DEFAULT 0,
                    verification_token TEXT,
                    verification_expires TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

            cursor.execute(users_table)

            # Patient logs table
            patient_logs_table = """
            CREATE TABLE IF NOT EXISTS patient_logs (
                id INTEGER PRIMARY KEY """ + ("AUTOINCREMENT" if self.db_type == 'sqlite' else "") + """,
                user_id INTEGER,
                age INTEGER,
                gender TEXT,
                symptoms TEXT,
                sys_bp INTEGER,
                dia_bp INTEGER,
                hr INTEGER,
                temp REAL,
                history TEXT,
                xgb_risk TEXT,
                dual_brain_risk TEXT,
                routing TEXT,
                risk_score INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """

            if self.db_type == 'postgresql':
                patient_logs_table = """
                CREATE TABLE IF NOT EXISTS patient_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    age INTEGER,
                    gender TEXT,
                    symptoms TEXT,
                    sys_bp INTEGER,
                    dia_bp INTEGER,
                    hr INTEGER,
                    temp REAL,
                    history TEXT,
                    xgb_risk TEXT,
                    dual_brain_risk TEXT,
                    routing TEXT,
                    risk_score INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
                """

            cursor.execute(patient_logs_table)

            # Appointments table
            appointments_table = """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY """ + ("AUTOINCREMENT" if self.db_type == 'sqlite' else "") + """,
                patient_id INTEGER,
                patient_name TEXT,
                doctor_id INTEGER,
                doctor_name TEXT,
                department TEXT,
                appointment_date TEXT,
                appointment_time TEXT,
                status TEXT DEFAULT 'Pending',
                symptoms TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES users (id),
                FOREIGN KEY (doctor_id) REFERENCES users (id)
            )
            """

            if self.db_type == 'postgresql':
                appointments_table = """
                CREATE TABLE IF NOT EXISTS appointments (
                    id SERIAL PRIMARY KEY,
                    patient_id INTEGER,
                    patient_name TEXT,
                    doctor_id INTEGER,
                    doctor_name TEXT,
                    department TEXT,
                    appointment_date TEXT,
                    appointment_time TEXT,
                    status TEXT DEFAULT 'Pending',
                    symptoms TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES users (id),
                    FOREIGN KEY (doctor_id) REFERENCES users (id)
                )
                """

            cursor.execute(appointments_table)

            # Messages table
            messages_table = """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY """ + ("AUTOINCREMENT" if self.db_type == 'sqlite' else "") + """,
                sender_id INTEGER,
                receiver_id INTEGER,
                message TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id)
            )
            """

            if self.db_type == 'postgresql':
                messages_table = """
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    sender_id INTEGER,
                    receiver_id INTEGER,
                    message TEXT,
                    is_read INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sender_id) REFERENCES users (id),
                    FOREIGN KEY (receiver_id) REFERENCES users (id)
                )
                """

            cursor.execute(messages_table)

            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id)",
                "CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON appointments(doctor_id)",
                "CREATE INDEX IF NOT EXISTS idx_patient_logs_user ON patient_logs(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)",
                "CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id)"
            ]

            for index in indexes:
                try:
                    cursor.execute(index)
                except Exception as e:
                    print(f"Index creation warning: {e}")

            conn.commit()
            print(f"✅ Database initialized successfully using {self.db_type.upper()}")


# Legacy function for backward compatibility
def get_db_connection():
    """
    Legacy function to get SQLite connection
    Maintained for backward compatibility with existing code
    """
    conn = sqlite3.connect('triage.db')
    conn.row_factory = sqlite3.Row
    return conn
