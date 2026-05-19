import sqlite3

from config import DB_PATH
from database.connection import connect, is_postgres_url


CREATE_EXAMS = """
CREATE TABLE IF NOT EXISTS exams (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);
"""

CREATE_SUBJECTS = """
CREATE TABLE IF NOT EXISTS subjects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id     INTEGER NOT NULL REFERENCES exams(id),
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    UNIQUE(exam_id, name)
);
"""

CREATE_ANSWER_KEYS = """
CREATE TABLE IF NOT EXISTS answer_keys (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id  INTEGER NOT NULL REFERENCES subjects(id),
    question    INTEGER NOT NULL CHECK(question >= 1 AND question <= 60),
    answer      TEXT NOT NULL CHECK(answer IN ('A','B','C','D','E')),
    UNIQUE(subject_id, question)
);
"""

CREATE_STUDENTS = """
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id     INTEGER NOT NULL REFERENCES exams(id),
    student_identifier TEXT NOT NULL,
    name        TEXT NOT NULL,
    class_group TEXT,
    position    INTEGER,
    created_at  TEXT NOT NULL,
    UNIQUE(exam_id, student_identifier)
);
"""

CREATE_ASSESSMENTS = """
CREATE TABLE IF NOT EXISTS assessments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id     INTEGER NOT NULL REFERENCES exams(id),
    student_id  INTEGER NOT NULL REFERENCES students(id),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    UNIQUE(exam_id, student_id)
);
"""

CREATE_RESULTS = """
CREATE TABLE IF NOT EXISTS results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL REFERENCES students(id),
    subject_id      INTEGER NOT NULL REFERENCES subjects(id),
    score           INTEGER NOT NULL,
    total           INTEGER NOT NULL DEFAULT 60,
    percentage      REAL NOT NULL,
    flagged_count   INTEGER NOT NULL DEFAULT 0,
    skipped_count   INTEGER NOT NULL DEFAULT 0,
    scan_file       TEXT NOT NULL,
    processed_at    TEXT NOT NULL,
    assessment_id   INTEGER REFERENCES assessments(id),
    UNIQUE(student_id, subject_id)
);
"""

CREATE_RESULT_DETAILS = """
CREATE TABLE IF NOT EXISTS result_details (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id   INTEGER NOT NULL REFERENCES results(id),
    question    INTEGER NOT NULL CHECK(question >= 1 AND question <= 60),
    detected    TEXT CHECK(detected IN ('A','B','C','D','E') OR detected IS NULL),
    correct     TEXT NOT NULL CHECK(correct IN ('A','B','C','D','E')),
    status      TEXT NOT NULL CHECK(status IN ('correct','wrong','skipped','flagged'))
);
"""

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'admin',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
"""


POSTGRES_STATEMENTS = [
    statement
    .replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    .replace("processed_at  TEXT NOT NULL", "processed_at   TEXT NOT NULL")
    for statement in (
        CREATE_EXAMS,
        CREATE_SUBJECTS,
        CREATE_ANSWER_KEYS,
        CREATE_STUDENTS,
        CREATE_ASSESSMENTS,
        CREATE_RESULTS,
        CREATE_RESULT_DETAILS,
        CREATE_USERS,
    )
]


def init_db(db_path: str = DB_PATH) -> None:
    """Create all database tables if they do not already exist."""
    with connect(db_path) as conn:
        statements = POSTGRES_STATEMENTS if is_postgres_url(db_path) else (
            CREATE_EXAMS,
            CREATE_SUBJECTS,
            CREATE_ANSWER_KEYS,
            CREATE_STUDENTS,
            CREATE_ASSESSMENTS,
            CREATE_RESULTS,
            CREATE_RESULT_DETAILS,
            CREATE_USERS,
        )
        for statement in statements:
            conn.execute(statement)
        if not is_postgres_url(db_path):
            _migrate_existing_db(conn)


def _migrate_existing_db(conn: sqlite3.Connection) -> None:
    """Add newer columns when an older local database already exists."""
    student_columns = _columns(conn, "students")
    if "student_identifier" not in student_columns:
        conn.execute("ALTER TABLE students ADD COLUMN student_identifier TEXT")
        conn.execute("UPDATE students SET student_identifier = COALESCE(CAST(position AS TEXT), name)")
    if "created_at" not in student_columns:
        conn.execute("ALTER TABLE students ADD COLUMN created_at TEXT")
        conn.execute("UPDATE students SET created_at = datetime('now') WHERE created_at IS NULL")
    result_columns = _columns(conn, "results")
    if "assessment_id" not in result_columns:
        conn.execute("ALTER TABLE results ADD COLUMN assessment_id INTEGER REFERENCES assessments(id)")
    user_columns = _columns(conn, "users")
    if user_columns and "updated_at" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")
        conn.execute("UPDATE users SET updated_at = created_at WHERE updated_at IS NULL")


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return column names for an existing SQLite table."""
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
