import pandas as pd
import streamlit as st

from config import OPTIONS, QUESTIONS_PER_SHEET
from database.queries import (
    create_subject,
    delete_answer_key,
    get_answer_key,
    get_subjects_by_exam,
    regrade_subject,
    save_answer_key,
)


def render() -> None:
    """Render answer key management for one subject."""
    exam_id = st.session_state.get("exam_id")
    if not exam_id:
        st.info("Please select or create an exam in the sidebar.")
        return
    st.title("Answer Keys")
    _subject_creator(exam_id)
    subjects = get_subjects_by_exam(exam_id)
    if not subjects:
        st.info("Add a subject to create its answer key.")
        return
    labels = [subject["name"] for subject in subjects]
    selected = st.selectbox("Subject", labels)
    subject_id = int(subjects[labels.index(selected)]["id"])
    existing = get_answer_key(subject_id)
    if existing:
        _existing_key_section(subject_id, existing)
    _entry_section(subject_id, existing)


def _subject_creator(exam_id: int) -> None:
    """Render a compact subject creation form."""
    with st.expander("Add New Subject"):
        name = st.text_input("Subject name")
        if st.button("Create Subject") and name.strip():
            try:
                create_subject(exam_id, name.strip())
                st.success("Subject created.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def _existing_key_section(subject_id: int, key: dict[int, str]) -> None:
    """Show current key and re-grade controls."""
    st.subheader("Current Key")
    st.dataframe(pd.DataFrame({"question": list(key.keys()), "answer": list(key.values())}), hide_index=True)
    confirm = st.checkbox("This will delete all existing results for this subject. Are you sure?")
    if st.button("Delete Key + Re-grade", disabled=not confirm):
        delete_answer_key(subject_id)
        regrade_subject(subject_id)
        st.warning("Answer key and results deleted. Upload scans again after saving a new key.")
        st.rerun()


def _entry_section(subject_id: int, existing: dict[int, str]) -> None:
    """Render manual and CSV answer key entry tabs."""
    st.subheader("Save Answer Key")
    manual_tab, csv_tab = st.tabs(["Manual", "CSV Upload"])
    with manual_tab:
        key = _manual_key(existing)
        if st.button("Save Manual Answer Key"):
            _save_key(subject_id, key)
    with csv_tab:
        st.code("question,answer\n1,A\n2,B\n...\n60,E", language="csv")
        upload = st.file_uploader("Answer key CSV", type=["csv"])
        if upload and st.button("Save CSV Answer Key"):
            df = pd.read_csv(upload)
            _save_key(subject_id, _csv_key(df))


def _manual_key(existing: dict[int, str]) -> dict[int, str]:
    """Collect a 60-question key from compact dropdowns."""
    key = {}
    for group_start in range(1, QUESTIONS_PER_SHEET + 1, 15):
        cols = st.columns(15)
        for offset, col in enumerate(cols):
            question = group_start + offset
            current = existing.get(question, OPTIONS[0])
            key[question] = col.selectbox(str(question), OPTIONS, index=OPTIONS.index(current), key=f"q{question}")
    return key


def _csv_key(df: pd.DataFrame) -> dict[int, str]:
    """Convert uploaded CSV rows to an answer key dict."""
    if set(df.columns) < {"question", "answer"}:
        raise ValueError("CSV must include question and answer columns")
    return {int(row.question): str(row.answer).strip().upper() for row in df.itertuples()}


def _save_key(subject_id: int, key: dict[int, str]) -> None:
    """Validate and save an answer key, displaying UI feedback."""
    try:
        save_answer_key(subject_id, key)
        st.success("Answer key saved.")
    except ValueError as exc:
        st.error(str(exc))
