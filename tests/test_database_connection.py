from database.connection import is_postgres_url, paramstyle


def test_database_url_selects_postgres_connection_style() -> None:
    assert is_postgres_url("postgresql://user:pass@example.com/db")
    assert paramstyle("SELECT * FROM exams WHERE id = ?", "postgresql://user:pass@example.com/db") == (
        "SELECT * FROM exams WHERE id = %s"
    )


def test_sqlite_path_keeps_sqlite_connection_style() -> None:
    assert not is_postgres_url("omr.db")
    assert paramstyle("SELECT * FROM exams WHERE id = ?", "omr.db") == "SELECT * FROM exams WHERE id = ?"
