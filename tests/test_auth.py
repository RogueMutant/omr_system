from database.auth import authenticate_user, ensure_default_admin, get_user_by_username
from database.models import init_db


def test_default_admin_is_created_with_hashed_password(tmp_path) -> None:
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    ensure_default_admin("admin", "omr1234", db_path)

    user = get_user_by_username("admin", db_path)
    assert user is not None
    assert user["password_hash"] != "omr1234"
    assert authenticate_user("admin", "omr1234", db_path) is not None


def test_authenticate_user_rejects_wrong_password(tmp_path) -> None:
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    ensure_default_admin("admin", "omr1234", db_path)

    assert authenticate_user("admin", "wrong", db_path) is None
