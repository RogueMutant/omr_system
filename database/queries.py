import sqlite3
from datetime import datetime, timezone
from typing import Any

from config import DB_PATH, OPTIONS, QUESTIONS_PER_SHEET
from database.connection import connect


def _connect(db_path: str) -> Any:
    """Open a configured database connection with dict-like row support."""
    return connect(db_path)


def _now() -> str:
    """Return the current UTC time as an ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _rows(cursor: Any) -> list[dict[str, Any]]:
    """Convert database rows from a cursor into dictionaries."""
    return [dict(row) for row in cursor.fetchall()]


def _is_integrity_error(exc: Exception) -> bool:
    """Return True for SQLite or psycopg integrity errors."""
    return isinstance(exc, sqlite3.IntegrityError) or exc.__class__.__name__ == "IntegrityError"


def create_exam(name: str, db_path: str = DB_PATH) -> int:
    """Insert an exam and return its id."""
    try:
        with _connect(db_path) as conn:
            cur = conn.execute("INSERT INTO exams (name, created_at) VALUES (?, ?)", (name, _now()))
            return int(cur.lastrowid)
    except Exception as exc:
        if _is_integrity_error(exc):
            raise ValueError(f"Exam already exists: {name}") from exc
        raise


def get_all_exams(db_path: str = DB_PATH) -> list[dict[str, Any]]:
    """Return all exams ordered by newest first."""
    with _connect(db_path) as conn:
        return _rows(conn.execute("SELECT id, name, created_at FROM exams ORDER BY id DESC"))


def get_exam_by_id(exam_id: int, db_path: str = DB_PATH) -> dict[str, Any] | None:
    """Return one exam by id, or None."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT id, name, created_at FROM exams WHERE id = ?", (exam_id,)).fetchone()
        return dict(row) if row else None


def create_subject(exam_id: int, name: str, db_path: str = DB_PATH) -> int:
    """Insert a subject under an exam and return its id."""
    try:
        with _connect(db_path) as conn:
            cur = conn.execute(
                "INSERT INTO subjects (exam_id, name, created_at) VALUES (?, ?, ?)",
                (exam_id, name, _now()),
            )
            return int(cur.lastrowid)
    except Exception as exc:
        if _is_integrity_error(exc):
            raise ValueError(f"Subject already exists for exam: {name}") from exc
        raise


def get_subjects_by_exam(exam_id: int, db_path: str = DB_PATH) -> list[dict[str, Any]]:
    """Return all subjects for an exam."""
    with _connect(db_path) as conn:
        return _rows(conn.execute("SELECT * FROM subjects WHERE exam_id = ? ORDER BY name", (exam_id,)))


def get_subject_by_id(subject_id: int, db_path: str = DB_PATH) -> dict[str, Any] | None:
    """Return one subject by id, or None."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
        return dict(row) if row else None


def save_answer_key(subject_id: int, key: dict[int, str], db_path: str = DB_PATH) -> None:
    """Save or replace a complete 60-question answer key."""
    expected = set(range(1, QUESTIONS_PER_SHEET + 1))
    if set(key.keys()) != expected:
        raise ValueError("Answer key must contain exactly questions 1-60")
    invalid = [answer for answer in key.values() if answer not in OPTIONS]
    if invalid:
        raise ValueError("Answer key values must be A, B, C, D, or E")
    with _connect(db_path) as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO answer_keys (subject_id, question, answer)
            VALUES (?, ?, ?)
            """,
            [(subject_id, question, answer) for question, answer in key.items()],
        )


def get_answer_key(subject_id: int, db_path: str = DB_PATH) -> dict[int, str]:
    """Return an answer key as {question: answer}."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT question, answer FROM answer_keys WHERE subject_id = ? ORDER BY question",
            (subject_id,),
        ).fetchall()
        return {int(row["question"]): str(row["answer"]) for row in rows}


def delete_answer_key(subject_id: int, db_path: str = DB_PATH) -> None:
    """Delete all answer key rows for a subject."""
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM answer_keys WHERE subject_id = ?", (subject_id,))


def save_student(
    exam_id: int,
    name: str,
    student_identifier: str,
    class_group: str | None = None,
    db_path: str = DB_PATH,
) -> int:
    """Create or update one student by exam and student identifier."""
    clean_name = name.strip()
    clean_identifier = student_identifier.strip()
    if not clean_name:
        raise ValueError("Student name is required")
    if not clean_identifier:
        raise ValueError("Student ID is required")
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM students WHERE exam_id = ? AND student_identifier = ?",
            (exam_id, clean_identifier),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE students SET name = ?, class_group = ? WHERE id = ?",
                (clean_name, class_group, row["id"]),
            )
            return int(row["id"])
        cur = conn.execute(
            """
            INSERT INTO students (exam_id, student_identifier, name, class_group, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (exam_id, clean_identifier, clean_name, class_group, _now()),
        )
        return int(cur.lastrowid)


def save_students(exam_id: int, students: list[dict[str, Any]], db_path: str = DB_PATH) -> None:
    """Insert students from legacy class-list input."""
    rows = []
    for index, student in enumerate(students, start=1):
        name = str(student.get("name", "")).strip()
        identifier = str(student.get("student_identifier") or student.get("student_id") or index).strip()
        if not name:
            raise ValueError("Student name is required")
        rows.append((exam_id, identifier, name, student.get("class_group"), int(student.get("position", index)), _now()))
    with _connect(db_path) as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO students
            (exam_id, student_identifier, name, class_group, position, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def get_students_by_exam(exam_id: int, db_path: str = DB_PATH) -> list[dict[str, Any]]:
    """Return all students for an exam ordered by name."""
    with _connect(db_path) as conn:
        return _rows(conn.execute("SELECT * FROM students WHERE exam_id = ? ORDER BY name", (exam_id,)))


def get_student_by_identifier(
    exam_id: int,
    student_identifier: str,
    db_path: str = DB_PATH,
) -> dict[str, Any] | None:
    """Return one student by exam and student identifier."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE exam_id = ? AND student_identifier = ?",
            (exam_id, student_identifier),
        ).fetchone()
        return dict(row) if row else None


def get_or_create_assessment(exam_id: int, student_id: int, db_path: str = DB_PATH) -> int:
    """Return the assessment id for one student in one exam, creating it if needed."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM assessments WHERE exam_id = ? AND student_id = ?",
            (exam_id, student_id),
        ).fetchone()
        if row:
            conn.execute("UPDATE assessments SET updated_at = ? WHERE id = ?", (_now(), row["id"]))
            return int(row["id"])
        cur = conn.execute(
            "INSERT INTO assessments (exam_id, student_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (exam_id, student_id, _now(), _now()),
        )
        return int(cur.lastrowid)


def get_assessments_by_exam(exam_id: int, db_path: str = DB_PATH) -> list[dict[str, Any]]:
    """Return stored student assessments with subject completion counts."""
    with _connect(db_path) as conn:
        return _rows(
            conn.execute(
                """
                SELECT
                    a.id,
                    a.exam_id,
                    a.student_id,
                    a.created_at,
                    a.updated_at,
                    s.student_identifier,
                    s.name AS student_name,
                    s.class_group,
                    COUNT(r.id) AS subject_count,
                    COALESCE(SUM(r.score), 0) AS total_score,
                    COALESCE(AVG(r.percentage), 0) AS average_percentage
                FROM assessments a
                JOIN students s ON s.id = a.student_id
                LEFT JOIN results r ON r.assessment_id = a.id
                WHERE a.exam_id = ?
                GROUP BY a.id
                ORDER BY s.name
                """,
                (exam_id,),
            )
        )


def save_result(
    student_id: int,
    subject_id: int,
    score: int,
    total: int,
    percentage: float,
    flagged_count: int,
    skipped_count: int,
    scan_file: str,
    details: list[dict[str, Any]],
    db_path: str = DB_PATH,
) -> int:
    """Save one result and its per-question details in a transaction."""
    with _connect(db_path) as conn:
        student = conn.execute("SELECT exam_id FROM students WHERE id = ?", (student_id,)).fetchone()
        if not student:
            raise ValueError(f"Student not found: {student_id}")
        assessment_id = _get_or_create_assessment_with_conn(conn, int(student["exam_id"]), student_id)
        existing = conn.execute(
            "SELECT id FROM results WHERE student_id = ? AND subject_id = ?",
            (student_id, subject_id),
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM result_details WHERE result_id = ?", (existing["id"],))
            conn.execute("DELETE FROM results WHERE id = ?", (existing["id"],))
        cur = conn.execute(
            """
            INSERT INTO results
            (student_id, subject_id, score, total, percentage, flagged_count, skipped_count,
             scan_file, processed_at, assessment_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                subject_id,
                score,
                total,
                percentage,
                flagged_count,
                skipped_count,
                scan_file,
                _now(),
                assessment_id,
            ),
        )
        result_id = int(cur.lastrowid)
        conn.executemany(
            """
            INSERT INTO result_details (result_id, question, detected, correct, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (result_id, item["question"], item.get("detected"), item["correct"], item["status"])
                for item in details
            ],
        )
        return result_id


def _get_or_create_assessment_with_conn(conn: Any, exam_id: int, student_id: int) -> int:
    """Return assessment id inside an existing transaction."""
    row = conn.execute(
        "SELECT id FROM assessments WHERE exam_id = ? AND student_id = ?",
        (exam_id, student_id),
    ).fetchone()
    if row:
        conn.execute("UPDATE assessments SET updated_at = ? WHERE id = ?", (_now(), row["id"]))
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO assessments (exam_id, student_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (exam_id, student_id, _now(), _now()),
    )
    return int(cur.lastrowid)


def get_results_by_subject(subject_id: int, db_path: str = DB_PATH) -> list[dict[str, Any]]:
    """Return all results for a subject joined to student data."""
    with _connect(db_path) as conn:
        return _rows(
            conn.execute(
                """
                SELECT r.*, s.name AS student_name, s.student_identifier, s.class_group, s.position
                FROM results r
                JOIN students s ON s.id = r.student_id
                WHERE r.subject_id = ?
                ORDER BY s.name
                """,
                (subject_id,),
            )
        )


def get_result_details(result_id: int, db_path: str = DB_PATH) -> list[dict[str, Any]]:
    """Return per-question rows for one result."""
    with _connect(db_path) as conn:
        return _rows(
            conn.execute(
                "SELECT question, detected, correct, status FROM result_details WHERE result_id = ? ORDER BY question",
                (result_id,),
            )
        )


def get_subject_stats(subject_id: int, db_path: str = DB_PATH) -> dict[str, Any]:
    """Compute summary and per-question stats for a subject."""
    results = get_results_by_subject(subject_id, db_path)
    if not results:
        return {}
    scores = [int(row["score"]) for row in results]
    question_stats = _question_stats(subject_id, len(results), db_path)
    pass_count = sum(1 for row in results if float(row["percentage"]) >= 50.0)
    return {
        "student_count": len(results),
        "average_score": round(sum(scores) / len(scores), 2),
        "highest_score": max(scores),
        "lowest_score": min(scores),
        "pass_count": pass_count,
        "fail_count": len(results) - pass_count,
        "question_stats": question_stats,
    }


def _question_stats(subject_id: int, total: int, db_path: str) -> dict[int, dict[str, int]]:
    """Return correct counts per question for a subject."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT d.question, SUM(CASE WHEN d.status = 'correct' THEN 1 ELSE 0 END) AS correct_count
            FROM result_details d
            JOIN results r ON r.id = d.result_id
            WHERE r.subject_id = ?
            GROUP BY d.question
            """,
            (subject_id,),
        ).fetchall()
    stats = {question: {"correct_count": 0, "total": total} for question in range(1, QUESTIONS_PER_SHEET + 1)}
    for row in rows:
        stats[int(row["question"])] = {"correct_count": int(row["correct_count"]), "total": total}
    return stats


def regrade_subject(subject_id: int, db_path: str = DB_PATH) -> None:
    """Delete all results and result details for a subject."""
    with _connect(db_path) as conn:
        result_ids = [row["id"] for row in conn.execute("SELECT id FROM results WHERE subject_id = ?", (subject_id,))]
        if result_ids:
            placeholders = ",".join("?" for _ in result_ids)
            conn.execute(f"DELETE FROM result_details WHERE result_id IN ({placeholders})", result_ids)
        conn.execute("DELETE FROM results WHERE subject_id = ?", (subject_id,))
