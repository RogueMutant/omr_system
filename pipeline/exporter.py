import csv
import os
from pathlib import Path
from typing import Any

from config import QUESTIONS_PER_SHEET


def export_to_csv(results: list[dict[str, Any]], output_path: str) -> None:
    """Append grading results to a CSV file, creating it when needed."""
    path = Path(output_path)
    if path.parent:
        os.makedirs(path.parent, exist_ok=True)
    fieldnames = [
        "student_id",
        "student_name",
        "class_group",
        "subject",
        "score",
        "total",
        "percentage",
        "flagged_count",
        "skipped_count",
        *[f"q{question}" for question in range(1, QUESTIONS_PER_SHEET + 1)],
    ]
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for result in results:
            writer.writerow(_result_to_row(result))


def _result_to_row(result: dict[str, Any]) -> dict[str, Any]:
    """Convert one rich result dictionary to an export row."""
    row = {
        "student_id": result.get("student_id") or result.get("student_identifier", ""),
        "student_name": result.get("student_name", ""),
        "class_group": result.get("class_group", ""),
        "subject": result.get("subject", ""),
        "score": result.get("score", 0),
        "total": result.get("total", QUESTIONS_PER_SHEET),
        "percentage": result.get("percentage", 0.0),
        "flagged_count": result.get("flagged_count", 0),
        "skipped_count": result.get("skipped_count", 0),
    }
    details = result.get("per_question", {})
    for question in range(1, QUESTIONS_PER_SHEET + 1):
        row[f"q{question}"] = _question_value(details.get(question) or details.get(str(question), {}))
    return row


def _question_value(detail: dict[str, Any]) -> str:
    """Return the CSV cell value for one question detail."""
    if detail.get("status") == "flagged":
        return "FLAG"
    if detail.get("status") == "skipped":
        return ""
    return detail.get("detected") or ""
