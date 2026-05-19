from config import QUESTIONS_PER_SHEET
from dashboard.pages.export import aggregate_export_df
from database.models import init_db
from database.queries import create_exam, create_subject, save_result, save_student


def test_aggregate_export_has_subject_scores_and_positions(tmp_path) -> None:
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    exam_id = create_exam("Exam", db_path)
    math_id = create_subject(exam_id, "Mathematics", db_path)
    english_id = create_subject(exam_id, "English", db_path)
    ada_id = save_student(exam_id, "Ada", "STU001", db_path=db_path)
    bola_id = save_student(exam_id, "Bola", "STU002", db_path=db_path)
    chi_id = save_student(exam_id, "Chi", "STU003", db_path=db_path)
    details = [{"question": q, "detected": "A", "correct": "A", "status": "correct"} for q in range(1, QUESTIONS_PER_SHEET + 1)]

    save_result(ada_id, math_id, 50, 60, 83.33, 0, 0, "ada-math.jpg", details, db_path)
    save_result(ada_id, english_id, 40, 60, 66.67, 0, 0, "ada-english.jpg", details, db_path)
    save_result(bola_id, math_id, 45, 60, 75.0, 0, 0, "bola-math.jpg", details, db_path)
    save_result(bola_id, english_id, 45, 60, 75.0, 0, 0, "bola-english.jpg", details, db_path)
    save_result(chi_id, math_id, 20, 60, 33.33, 0, 0, "chi-math.jpg", details, db_path)

    df = aggregate_export_df(exam_id, db_path)

    assert list(df.columns) == [
        "student_id",
        "name",
        "Mathematics",
        "English",
        "aggregate",
        "percentage",
        "positionInResult",
    ]
    assert df.iloc[0].to_dict() == {
        "student_id": "STU001",
        "name": "Ada",
        "Mathematics": 50,
        "English": 40,
        "aggregate": 90,
        "percentage": 75.0,
        "positionInResult": 1,
    }
    assert df.iloc[1]["student_id"] == "STU002"
    assert df.iloc[1]["positionInResult"] == 1
    assert df.iloc[2]["student_id"] == "STU003"
    assert df.iloc[2]["English"] == 0
    assert df.iloc[2]["positionInResult"] == 3
