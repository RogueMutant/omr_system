import pandas as pd
import streamlit as st

from dashboard.components.tables import render_question_stats, render_results_table
from database.queries import (
    get_assessments_by_exam,
    get_result_details,
    get_results_by_subject,
    get_subject_stats,
    get_subjects_by_exam,
)


def render() -> None:
    """Render result tables, statistics, and per-student details."""
    exam_id = st.session_state.get("exam_id")
    if not exam_id:
        st.info("Please select or create an exam in the sidebar.")
        return
    st.title("Results")
    assessments = get_assessments_by_exam(exam_id)
    if assessments:
        st.subheader("Stored Assessments")
        st.dataframe(
            pd.DataFrame(assessments)[
                ["student_identifier", "student_name", "class_group", "subject_count", "total_score", "average_percentage"]
            ],
            width="stretch",
            hide_index=True,
        )
    subjects = [subject for subject in get_subjects_by_exam(exam_id) if get_results_by_subject(subject["id"])]
    if not subjects:
        st.info("No graded results yet.")
        return
    labels = [subject["name"] for subject in subjects]
    subject = subjects[labels.index(st.selectbox("Subject", labels))]
    rows = get_results_by_subject(subject["id"])
    stats = get_subject_stats(subject["id"])
    _metrics(stats)
    df = pd.DataFrame(rows)
    render_results_table(
        df[
            [
                "student_identifier",
                "student_name",
                "class_group",
                "score",
                "total",
                "percentage",
                "flagged_count",
                "skipped_count",
            ]
        ]
    )
    with st.expander("Per-question analysis"):
        render_question_stats(stats["question_stats"])
    _student_details(rows)


def _metrics(stats: dict) -> None:
    """Render top-level subject metrics."""
    cols = st.columns(4)
    cols[0].metric("Students", stats["student_count"])
    cols[1].metric("Average", f"{stats['average_score']:.2f}")
    cols[2].metric("Highest", stats["highest_score"])
    cols[3].metric("Lowest", stats["lowest_score"])


def _student_details(rows: list[dict]) -> None:
    """Render expandable per-question details for each student."""
    st.subheader("Student Details")
    for row in rows:
        with st.expander(f"{row['student_identifier']} - {row['student_name']}"):
            details = pd.DataFrame(get_result_details(row["id"]))
            st.dataframe(details, width="stretch", hide_index=True)
