import pandas as pd
import streamlit as st

from config import DB_PATH
from database.queries import get_result_details, get_results_by_subject, get_subjects_by_exam
from pipeline.exporter import export_to_csv


def render() -> None:
    """Render CSV export controls for the selected exam."""
    exam_id = st.session_state.get("exam_id")
    if not exam_id:
        st.info("Please select or create an exam in the sidebar.")
        return
    st.title("Export")
    subjects = get_subjects_by_exam(exam_id)
    selected = st.multiselect("Subjects", [subject["name"] for subject in subjects], default=[s["name"] for s in subjects])
    chosen = [subject for subject in subjects if subject["name"] in selected]
    rows = _result_rows(chosen)
    if not rows:
        st.info("No results available for selected subjects.")
        return
    full_csv = _full_csv(rows)
    summary_df = pd.DataFrame(rows)[["student_id", "student_name", "class_group", "subject", "score", "total", "percentage"]]
    aggregate_df = aggregate_export_df(exam_id)
    st.download_button("Download Full Results CSV", full_csv, "full_results.csv", "text/csv")
    st.download_button("Download Summary CSV", summary_df.to_csv(index=False), "summary_results.csv", "text/csv")
    if not aggregate_df.empty:
        st.download_button(
            "Download Aggregate Results CSV",
            aggregate_df.to_csv(index=False),
            "aggregate_results.csv",
            "text/csv",
        )


def aggregate_export_df(exam_id: int, db_path: str = DB_PATH) -> pd.DataFrame:
    """Build a wide aggregate result table with one score column per subject."""
    subjects = sorted(get_subjects_by_exam(exam_id, db_path), key=lambda subject: int(subject["id"]))
    subject_names = [subject["name"] for subject in subjects]
    students: dict[str, dict] = {}
    subject_totals = {subject["name"]: 60 for subject in subjects}
    for subject in subjects:
        for result in get_results_by_subject(subject["id"], db_path):
            student_id = result["student_identifier"]
            row = students.setdefault(
                student_id,
                {
                    "student_id": student_id,
                    "name": result["student_name"],
                    **{name: 0 for name in subject_names},
                },
            )
            row[subject["name"]] = int(result["score"])
            subject_totals[subject["name"]] = int(result["total"])
    rows = []
    possible_total = sum(subject_totals.values()) or 1
    for row in students.values():
        aggregate = sum(int(row[name]) for name in subject_names)
        rows.append(
            {
                **row,
                "aggregate": aggregate,
                "percentage": round((aggregate / possible_total) * 100, 2),
            }
        )
    rows.sort(key=lambda item: (-int(item["aggregate"]), str(item["name"])))
    previous_score = None
    previous_position = 0
    for index, row in enumerate(rows, start=1):
        if row["aggregate"] == previous_score:
            row["positionInResult"] = previous_position
        else:
            row["positionInResult"] = index
            previous_position = index
            previous_score = row["aggregate"]
    return pd.DataFrame(rows, columns=["student_id", "name", *subject_names, "aggregate", "percentage", "positionInResult"])


def _result_rows(subjects: list[dict]) -> list[dict]:
    """Collect dashboard export rows across subjects."""
    rows = []
    for subject in subjects:
        for result in get_results_by_subject(subject["id"]):
            details = {
                item["question"]: item
                for item in get_result_details(result["id"])
            }
            rows.append(
                {
                    "student_name": result["student_name"],
                    "student_id": result["student_identifier"],
                    "class_group": result["class_group"],
                    "subject": subject["name"],
                    "score": result["score"],
                    "total": result["total"],
                    "percentage": result["percentage"],
                    "flagged_count": result["flagged_count"],
                    "skipped_count": result["skipped_count"],
                    "per_question": details,
                }
            )
    return rows


def _full_csv(rows: list[dict]) -> str:
    """Build the full CSV payload using the shared exporter."""
    import tempfile

    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    handle.close()
    export_to_csv(rows, handle.name)
    return open(handle.name, encoding="utf-8").read()
