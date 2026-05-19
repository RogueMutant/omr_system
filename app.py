import streamlit as st

st.set_page_config(page_title="PHF OMR Grading System", layout="wide")

from dashboard.auth import bootstrap_default_admin, require_login
from dashboard.components.sidebar import render_sidebar
from dashboard.pages import answer_keys, export, home, results, upload
from database.models import init_db


init_db()
bootstrap_default_admin()

if not require_login():
    st.stop()

page = render_sidebar()

if page == "Home":
    home.render()
elif page == "Upload":
    upload.render()
elif page == "Answer Keys":
    answer_keys.render()
elif page == "Results":
    results.render()
elif page == "Export":
    export.render()
