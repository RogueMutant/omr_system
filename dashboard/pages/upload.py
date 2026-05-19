import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from database.queries import (
    get_answer_key,
    get_results_by_subject,
    get_subjects_by_exam,
    save_result,
    save_student,
)
from pipeline.detector import detect_with_anomalies
from pipeline.exporter import export_to_csv
from pipeline.grader import grade
from pipeline.loader import load_file
from pipeline.preprocessor import preprocess


def render() -> None:
    """Render individual answer sheet upload and grading workflow."""
    exam_id = st.session_state.get("exam_id")
    if not exam_id:
        st.info("Please select or create an exam in the sidebar.")
        return
    st.title("Upload Answer Sheet")
    subjects = [subject for subject in get_subjects_by_exam(exam_id) if get_answer_key(subject["id"])]
    if not subjects:
        st.error("No subjects have answer keys yet. Add one on the Answer Keys page.")
        return
    subject = _select_subject(subjects)
    student = _student_form()
    scan_file = st.file_uploader("Answer sheet", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=False)
    _existing_result_notice(subject, student)
    disabled = not scan_file or not student["name"] or not student["student_identifier"]
    if st.button("Grade Answer Sheet", disabled=disabled):
        _process_upload(exam_id, subject, student, scan_file)


def _select_subject(subjects: list[dict[str, Any]]) -> dict[str, Any]:
    """Render subject selector."""
    labels = [subject["name"] for subject in subjects]
    selected = st.selectbox("Subject", labels)
    return subjects[labels.index(selected)]


def _student_form() -> dict[str, str | None]:
    """Render student detail inputs for one uploaded sheet."""
    col1, col2 = st.columns(2)
    name = col1.text_input("Student name")
    student_identifier = col2.text_input("Student ID")
    class_group = st.text_input("Class / group (optional)")
    return {
        "name": name.strip(),
        "student_identifier": student_identifier.strip(),
        "class_group": class_group.strip() or None,
    }


def _existing_result_notice(subject: dict[str, Any], student: dict[str, str | None]) -> None:
    """Warn when a student already has a result for the selected subject."""
    if not student["student_identifier"]:
        return
    existing = [
        row for row in get_results_by_subject(subject["id"])
        if row["student_identifier"] == student["student_identifier"]
    ]
    if existing:
        st.warning("This student already has a result for this subject. Grading will replace that subject result.")


def _process_upload(exam_id: int, subject: dict[str, Any], student: dict[str, str | None], scan_file: Any) -> None:
    """Persist one upload, validate it has one sheet, then grade and store it."""
    path = _save_temp_upload(scan_file)
    sheets = load_file(str(path))
    if len(sheets) != 1:
        st.error(f"Upload exactly one answer sheet. This file produced {len(sheets)} sheets.")
        return
    student_id = save_student(
        exam_id,
        str(student["name"]),
        str(student["student_identifier"]),
        student["class_group"],
    )
    answer_key = get_answer_key(subject["id"])
    row = _grade_one(sheets[0], student_id, student, subject, answer_key, scan_file.name)
    output_path = Path("output") / f"{student['student_identifier']}_{subject['name']}_result.csv"
    export_to_csv([row], str(output_path))
    st.success("Assessment stored.")
    st.dataframe(pd.DataFrame([row])[["student_id", "student_name", "subject", "score", "percentage"]], hide_index=True)


def _save_temp_upload(scan_file: Any) -> Path:
    """Persist one Streamlit upload to a temporary file."""
    suffix = Path(scan_file.name).suffix
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    handle.write(scan_file.getbuffer())
    handle.close()
    return Path(handle.name)


def _grade_one(
    image: Any,
    student_id: int,
    student: dict[str, str | None],
    subject: dict[str, Any],
    answer_key: dict[int, str],
    filename: str,
) -> dict[str, Any]:
    """Grade one uploaded sheet and save the subject result."""
    processed = preprocess(image)
    detected, anomalies, _ = detect_with_anomalies(processed["grid_thresh"])
    graded = grade(detected, answer_key, anomalies)
    details = [{"question": question, **detail} for question, detail in graded["per_question"].items()]
    save_result(
        student_id,
        subject["id"],
        graded["score"],
        graded["total"],
        graded["percentage"],
        len(graded["flagged"]),
        len(graded["skipped"]),
        filename,
        details,
    )
    return {
        "student_id": student["student_identifier"],
        "student_name": student["name"],
        "class_group": student["class_group"],
        "subject": subject["name"],
        "score": graded["score"],
        "total": graded["total"],
        "percentage": graded["percentage"],
        "flagged_count": len(graded["flagged"]),
        "skipped_count": len(graded["skipped"]),
        "per_question": graded["per_question"],
    }
