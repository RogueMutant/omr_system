import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any

from config import DB_PATH
from database.connection import connect


def ensure_default_admin(username: str, password: str, db_path: str = DB_PATH) -> None:
    """Create the initial admin account when the users table is empty."""
    with connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        if row and int(row["count"]) > 0:
            return
        now = _now()
        conn.execute(
            """
            INSERT INTO users (username, password_hash, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username.strip(), hash_password(password), "admin", now, now),
        )


def authenticate_user(username: str, password: str, db_path: str = DB_PATH) -> dict[str, Any] | None:
    """Return the user when the submitted credentials are valid."""
    user = get_user_by_username(username, db_path)
    if not user or not verify_password(password, str(user["password_hash"])):
        return None
    return user


def get_user_by_username(username: str, db_path: str = DB_PATH) -> dict[str, Any] | None:
    """Return one user by username."""
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, role, created_at, updated_at FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
        return dict(row) if row else None


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2 and a random salt."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"pbkdf2_sha256$200000${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored PBKDF2 hash."""
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
