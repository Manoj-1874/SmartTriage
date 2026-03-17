"""
Database Utilities for SmartTriage Dashboard
Thread-safe connection pooling with support for SQLite and PostgreSQL
"""
import sqlite3
import threading
import logging
from contextlib import contextmanager
from queue import Queue, Empty
from typing import Optional, Any, Dict, List
from config import Config

logger = logging.getLogger(__name__)


class ThreadSafeConnectionPool:
    """Thread-safe connection pool for SQLite"""

    def __init__(self, db_path: str, pool_size: int = 10, timeout: int = 30):
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self.pool = Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self._local = threading.local()

        # Initialize connection pool
        for _ in range(pool_size):
            conn = self._create_connection()
            self.pool.put(conn)

        logger.info(f"Initialized connection pool with {pool_size} connections")

    def _create_connection(self):
        """Create a new database connection with thread-safe settings"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,  # Allow cross-thread usage
            isolation_level=None,  # Autocommit mode for better concurrency
            timeout=self.timeout
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrent access
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA cache_size=-64000')  # 64MB cache
        conn.execute('PRAGMA temp_store=MEMORY')
        return conn

    @contextmanager
    def get_connection(self):
        """Get connection from pool with automatic return"""
        conn = None
        try:
            conn = self.pool.get(timeout=self.timeout)
            yield conn
        except Empty:
            logger.error("Connection pool exhausted, creating temporary connection")
            conn = self._create_connection()
            yield conn
        except Exception as e:
            logger.error(f"Database error: {str(e)}", exc_info=True)
            raise
        finally:
            if conn:
                try:
                    # Verify connection is still valid
                    conn.execute('SELECT 1')
                    self.pool.put(conn, block=False)
                except Exception as e:
                    logger.warning(f"Connection invalid, creating new: {str(e)}")
                    try:
                        conn.close()
                    except:
                        pass
                    new_conn = self._create_connection()
                    try:
                        self.pool.put(new_conn, block=False)
                    except:
                        new_conn.close()

    def close_all(self):
        """Close all connections in pool"""
        with self.lock:
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    conn.close()
                except Empty:
                    break
                except Exception as e:
                    logger.error(f"Error closing connection: {str(e)}")
            logger.info("All connections closed")


class DatabaseManager:
    """Thread-safe database connection manager supporting SQLite and PostgreSQL"""

    def __init__(self, config):
        self.config = config
        self.db_type = config.DATABASE_TYPE
        self._pool = None
        self._pg_pool = None

        if self.db_type == 'postgresql':
            try:
                import psycopg2
                from psycopg2 import pool
                from psycopg2.extras import RealDictCursor
                self.psycopg2 = psycopg2
                self.RealDictCursor = RealDictCursor
                self.available = True

                # Initialize PostgreSQL connection pool
                self._pg_pool = pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=20,
                    host=self.config.POSTGRES_HOST,
                    port=self.config.POSTGRES_PORT,
                    database=self.config.POSTGRES_DB,
                    user=self.config.POSTGRES_USER,
                    password=self.config.POSTGRES_PASSWORD
                )
                logger.info("PostgreSQL connection pool initialized")
            except ImportError:
                logger.warning("psycopg2 not installed. Falling back to SQLite.")
                self.db_type = 'sqlite'
                self.available = False

        if self.db_type == 'sqlite':
            # Extract database file path from DATABASE_URL
            db_path = self.config.DATABASE_URL.replace('sqlite:///', '')
            if db_path == ':memory:':
                db_path = ':memory:'

            # Initialize thread-safe connection pool for SQLite
            self._pool = ThreadSafeConnectionPool(db_path, pool_size=10, timeout=30)
            self.available = True

    @contextmanager
    def get_connection(self):
        """
        Get database connection as context manager
        Thread-safe with automatic connection pooling, commit/rollback, and cleanup
        """
        if self.db_type == 'postgresql' and self.available and self._pg_pool:
            conn = self._pg_pool.getconn()
            try:
                conn.autocommit = False
                cursor = conn.cursor(cursor_factory=self.RealDictCursor)
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"PostgreSQL transaction error: {str(e)}", exc_info=True)
                raise
            finally:
                self._pg_pool.putconn(conn)
        else:
            # Use thread-safe SQLite connection pool
            with self._pool.get_connection() as conn:
                try:
                    yield conn
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.error(f"SQLite transaction error: {str(e)}", exc_info=True)
                    raise

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """
        Execute a query and optionally return results (thread-safe)

        Args:
            query: SQL query string
            params: Query parameters (tuple or dict)
            fetch_one: Return single result
            fetch_all: Return all results

        Returns:
            Query results or None
        """
        try:
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
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}", exc_info=True)
            raise

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute query with multiple parameter sets (thread-safe batch operation)

        Args:
            query: SQL query string
            params_list: List of parameter tuples

        Returns:
            Number of affected rows
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Batch execution error: {str(e)}", exc_info=True)
            raise

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
                phc_id INTEGER,
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
                    phc_id INTEGER,
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
                phc_id INTEGER,
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
                recommended_specialist TEXT,
                risk_score INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (phc_id) REFERENCES phc_facilities (id)
            )
            """

            if self.db_type == 'postgresql':
                patient_logs_table = """
                CREATE TABLE IF NOT EXISTS patient_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    phc_id INTEGER,
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
                    recommended_specialist TEXT,
                    risk_score INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (phc_id) REFERENCES phc_facilities (id)
                )
                """

            # PHC facilities table
            phc_facilities_table = """
            CREATE TABLE IF NOT EXISTS phc_facilities (
                id INTEGER PRIMARY KEY """ + ("AUTOINCREMENT" if self.db_type == 'sqlite' else "") + """,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                contact TEXT
            )
            """

            if self.db_type == 'postgresql':
                phc_facilities_table = """
                CREATE TABLE IF NOT EXISTS phc_facilities (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    contact TEXT
                )
                """

            # Staff attendance table
            staff_attendance_table = """
            CREATE TABLE IF NOT EXISTS staff_attendance (
                id INTEGER PRIMARY KEY """ + ("AUTOINCREMENT" if self.db_type == 'sqlite' else "") + """,
                user_id INTEGER NOT NULL,
                phc_id INTEGER NOT NULL,
                check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'Present' CHECK(status IN ('Present', 'Absent')),
                geo_location TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (phc_id) REFERENCES phc_facilities (id)
            )
            """

            if self.db_type == 'postgresql':
                staff_attendance_table = """
                CREATE TABLE IF NOT EXISTS staff_attendance (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    phc_id INTEGER NOT NULL,
                    check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL DEFAULT 'Present' CHECK(status IN ('Present', 'Absent')),
                    geo_location TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (phc_id) REFERENCES phc_facilities (id)
                )
                """

            cursor.execute(patient_logs_table)
            cursor.execute(phc_facilities_table)
            cursor.execute(staff_attendance_table)

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

            # Backward-compatible migrations for existing SQLite databases
            if self.db_type == 'sqlite':
                cursor.execute("PRAGMA table_info(users)")
                users_columns = [col[1] for col in cursor.fetchall()]
                if 'phc_id' not in users_columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN phc_id INTEGER")

                cursor.execute("PRAGMA table_info(patient_logs)")
                logs_columns = [col[1] for col in cursor.fetchall()]
                if 'phc_id' not in logs_columns:
                    cursor.execute("ALTER TABLE patient_logs ADD COLUMN phc_id INTEGER")
                if 'recommended_specialist' not in logs_columns:
                    cursor.execute("ALTER TABLE patient_logs ADD COLUMN recommended_specialist TEXT")

            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id)",
                "CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON appointments(doctor_id)",
                "CREATE INDEX IF NOT EXISTS idx_patient_logs_user ON patient_logs(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_patient_logs_phc ON patient_logs(phc_id)",
                "CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)",
                "CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id)",
                "CREATE INDEX IF NOT EXISTS idx_staff_attendance_user ON staff_attendance(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_staff_attendance_phc ON staff_attendance(phc_id)",
                "CREATE INDEX IF NOT EXISTS idx_staff_attendance_time ON staff_attendance(check_in_time)"
            ]

            for index in indexes:
                try:
                    cursor.execute(index)
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")

            conn.commit()
            logger.info(f"Database initialized successfully using {self.db_type.upper()}")

    def cleanup(self):
        """Cleanup database connections on shutdown"""
        try:
            if self.db_type == 'sqlite' and self._pool:
                self._pool.close_all()
                logger.info("SQLite connection pool closed")
            elif self.db_type == 'postgresql' and self._pg_pool:
                self._pg_pool.closeall()
                logger.info("PostgreSQL connection pool closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)


# Legacy function for backward compatibility - now uses connection pool
def get_db_connection():
    """
    Legacy function to get SQLite connection
    Returns a context manager for backward compatibility
    WARNING: Prefer using DatabaseManager.get_connection() for new code
    """
    conn = sqlite3.connect('triage.db', check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent access
    conn.execute('PRAGMA journal_mode=WAL')
    return conn
