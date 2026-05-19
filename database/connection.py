import os
import sqlite3
from typing import Any


def is_postgres_url(db_path: str | None) -> bool:
    """Return True when the configured database target is Postgres."""
    return bool(db_path and db_path.startswith(("postgresql://", "postgres://")))


def paramstyle(sql: str, db_path: str | None) -> str:
    """Convert SQLite-style placeholders to psycopg placeholders for Postgres."""
    if is_postgres_url(db_path):
        return sql.replace("?", "%s")
    return sql


def connect(db_path: str) -> Any:
    """Open either a SQLite or Postgres connection."""
    if is_postgres_url(db_path):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("Postgres support requires psycopg. Install requirements.txt first.") from exc
        return PostgresConnection(psycopg.connect(db_path, row_factory=dict_row))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def configured_database_url() -> str | None:
    """Read DATABASE_URL from the environment or Streamlit secrets."""
    value = os.getenv("DATABASE_URL")
    if value:
        return value
    try:
        import streamlit as st

        secret = st.secrets.get("DATABASE_URL")
        return str(secret) if secret else None
    except Exception:
        return None


class PostgresConnection:
    """Small sqlite-compatible wrapper around a psycopg connection."""

    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def __enter__(self) -> "PostgresConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] = ()) -> "PostgresCursor":
        converted = _postgres_sql(sql)
        cur = self.conn.execute(converted, params)
        returns_id = converted.upper().startswith("INSERT INTO ") and " RETURNING ID" in converted.upper()
        return PostgresCursor(cur, returns_id)

    def executemany(self, sql: str, params_seq: list[tuple[Any, ...]]) -> None:
        with self.conn.cursor() as cur:
            cur.executemany(_postgres_sql(sql), params_seq)


class PostgresCursor:
    """Expose the subset of sqlite cursor behavior used by this project."""

    def __init__(self, cursor: Any, returns_id: bool = False) -> None:
        self.cursor = cursor
        self.lastrowid = _last_inserted_id(cursor) if returns_id else None

    def fetchone(self) -> dict[str, Any] | None:
        return self.cursor.fetchone()

    def fetchall(self) -> list[dict[str, Any]]:
        return self.cursor.fetchall()


def _last_inserted_id(cursor: Any) -> int | None:
    if cursor.description:
        row = cursor.fetchone()
        if row and "id" in row:
            return int(row["id"])
    return None


def _postgres_sql(sql: str) -> str:
    converted = sql.strip()
    converted = converted.replace("?", "%s")
    converted = converted.replace(
        "INSERT OR REPLACE INTO answer_keys (subject_id, question, answer)\n            VALUES (%s, %s, %s)",
        """
            INSERT INTO answer_keys (subject_id, question, answer)
            VALUES (%s, %s, %s)
            ON CONFLICT (subject_id, question) DO UPDATE SET answer = EXCLUDED.answer
            """.strip(),
    )
    converted = converted.replace(
        "INSERT OR IGNORE INTO students\n            (exam_id, student_identifier, name, class_group, position, created_at)\n            VALUES (%s, %s, %s, %s, %s, %s)",
        """
            INSERT INTO students
            (exam_id, student_identifier, name, class_group, position, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (exam_id, student_identifier) DO NOTHING
            """.strip(),
    )
    if converted.upper().startswith("INSERT INTO ") and " RETURNING " not in converted.upper():
        table = converted.split()[2]
        if table in {"exams", "subjects", "students", "assessments", "results", "users"}:
            converted = f"{converted} RETURNING id"
    return converted
