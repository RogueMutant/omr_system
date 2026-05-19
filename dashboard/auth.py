import os

import streamlit as st

from database.auth import authenticate_user, ensure_default_admin


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "omr1234"


def bootstrap_default_admin() -> None:
    """Create the first admin user from env/secrets or local defaults."""
    ensure_default_admin(_secret("ADMIN_USERNAME", DEFAULT_ADMIN_USERNAME), _secret("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD))


def require_login() -> bool:
    """Render login controls and return True when the user is authenticated."""
    if st.session_state.get("authenticated"):
        with st.sidebar:
            st.caption(f"Signed in as {st.session_state.get('username', 'admin')}")
            if st.button("Logout"):
                st.session_state.pop("authenticated", None)
                st.session_state.pop("username", None)
                st.rerun()
        return True

    st.title("PHF OMR Grading System")
    st.subheader("Admin login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        user = authenticate_user(username, password)
        if user:
            st.session_state["authenticated"] = True
            st.session_state["username"] = user["username"]
            st.rerun()
        st.error("Invalid username or password.")
    return False


def _secret(name: str, default: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        secret = st.secrets.get(name)
        return str(secret) if secret else default
    except Exception:
        return default
