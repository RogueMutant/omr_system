import csv

from pipeline.exporter import export_to_csv


def sample_result(name: str = "Ada") -> dict:
    details = {
        question: {"detected": "A", "correct": "A", "status": "correct"}
        for question in range(1, 61)
    }
    details[2] = {"detected": None, "correct": "B", "status": "skipped"}
    details[3] = {"detected": "C", "correct": "D", "status": "flagged"}
    return {
        "student_name": name,
        "student_id": "STU001",
        "class_group": "JSS 2A",
        "subject": "Mathematics",
        "score": 58,
        "total": 60,
        "percentage": 96.67,
        "flagged_count": 1,
        "skipped_count": 1,
        "per_question": details,
    }


def read_rows(path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_export_to_csv_creates_file_if_missing(tmp_path) -> None:
    output = tmp_path / "results.csv"

    export_to_csv([sample_result()], str(output))

    assert output.exists()


def test_export_to_csv_appends_rows_to_existing_file(tmp_path) -> None:
    output = tmp_path / "results.csv"

    export_to_csv([sample_result("Ada")], str(output))
    export_to_csv([sample_result("Bola")], str(output))

    assert [row["student_name"] for row in read_rows(output)] == ["Ada", "Bola"]


def test_output_csv_has_expected_columns(tmp_path) -> None:
    output = tmp_path / "results.csv"

    export_to_csv([sample_result()], str(output))

    row = read_rows(output)[0]
    assert list(row.keys()) == [
        "student_id",
        "student_name",
        "class_group",
        "subject",
        "score",
        "total",
        "percentage",
        "flagged_count",
        "skipped_count",
        *[f"q{question}" for question in range(1, 61)],
    ]


def test_flag_appears_for_flagged_questions(tmp_path) -> None:
    output = tmp_path / "results.csv"

    export_to_csv([sample_result()], str(output))

    assert read_rows(output)[0]["q3"] == "FLAG"


def test_empty_string_appears_for_skipped_questions(tmp_path) -> None:
    output = tmp_path / "results.csv"

    export_to_csv([sample_result()], str(output))

    assert read_rows(output)[0]["q2"] == ""
