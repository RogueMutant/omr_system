import pandas as pd
import streamlit as st

from database.queries import get_answer_key, get_exam_by_id, get_students_by_exam, get_subject_stats, get_subjects_by_exam


def render() -> None:
    """Render the selected exam overview."""
    exam_id = st.session_state.get("exam_id")
    if not exam_id:
        st.info("Please select or create an exam in the sidebar.")
        return
    exam = get_exam_by_id(exam_id)
    subjects = get_subjects_by_exam(exam_id)
    students = get_students_by_exam(exam_id)
    st.title(exam["name"] if exam else "Exam")
    col1, col2 = st.columns(2)
    col1.metric("Subjects", len(subjects))
    col2.metric("Students", len(students))
    rows = []
    for subject in subjects:
        stats = get_subject_stats(subject["id"])
        rows.append(
            {
                "subject": subject["name"],
                "has_answer_key": bool(get_answer_key(subject["id"])),
                "students_graded": stats.get("student_count", 0),
                "avg_score": stats.get("average_score", 0),
                "highest": stats.get("highest_score", 0),
                "lowest": stats.get("lowest_score", 0),
            }
        )
    st.subheader("Subject Status")
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
