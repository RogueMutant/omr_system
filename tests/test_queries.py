import pytest

from config import QUESTIONS_PER_SHEET
from database.models import init_db
from database.queries import (
    create_exam,
    create_subject,
    get_answer_key,
    get_assessments_by_exam,
    get_results_by_subject,
    get_students_by_exam,
    get_subject_stats,
    regrade_subject,
    save_answer_key,
    save_result,
    save_student,
    save_students,
)


@pytest.fixture()
def db_path(tmp_path) -> str:
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def full_key(answer: str = "A") -> dict[int, str]:
    return {question: answer for question in range(1, QUESTIONS_PER_SHEET + 1)}


def test_create_exam_returns_int_id(db_path: str) -> None:
    assert isinstance(create_exam("2026 PRE-BECE", db_path), int)


def test_create_exam_raises_on_duplicate_name(db_path: str) -> None:
    create_exam("2026 PRE-BECE", db_path)

    with pytest.raises(ValueError):
        create_exam("2026 PRE-BECE", db_path)


def test_save_answer_key_raises_if_fewer_than_sixty_questions(db_path: str) -> None:
    exam_id = create_exam("Exam", db_path)
    subject_id = create_subject(exam_id, "Math", db_path)

    with pytest.raises(ValueError):
        save_answer_key(subject_id, {1: "A"}, db_path)


def test_save_answer_key_raises_if_answer_invalid(db_path: str) -> None:
    exam_id = create_exam("Exam", db_path)
    subject_id = create_subject(exam_id, "Math", db_path)
    key = full_key()
    key[1] = "Z"

    with pytest.raises(ValueError):
        save_answer_key(subject_id, key, db_path)


def test_get_answer_key_returns_empty_dict_when_missing(db_path: str) -> None:
    exam_id = create_exam("Exam", db_path)
    subject_id = create_subject(exam_id, "Math", db_path)

    assert get_answer_key(subject_id, db_path) == {}


def test_save_result_and_get_results_round_trip(db_path: str) -> None:
    exam_id = create_exam("Exam", db_path)
    subject_id = create_subject(exam_id, "Math", db_path)
    student_id = save_student(exam_id, "Ada", "STU001", "A", db_path)
    details = [
        {"question": question, "detected": "A", "correct": "A", "status": "correct"}
        for question in range(1, 61)
    ]

    save_result(student_id, subject_id, 60, 60, 100.0, 0, 0, "scan.jpg", details, db_path)

    rows = get_results_by_subject(subject_id, db_path)
    assert rows[0]["student_name"] == "Ada"
    assert rows[0]["student_identifier"] == "STU001"
    assert rows[0]["score"] == 60


def test_regrade_subject_deletes_results_but_not_students_or_subject(db_path: str) -> None:
    exam_id = create_exam("Exam", db_path)
    subject_id = create_subject(exam_id, "Math", db_path)
    student_id = save_student(exam_id, "Ada", "STU001", db_path=db_path)
    details = [{"question": q, "detected": None, "correct": "A", "status": "skipped"} for q in range(1, 61)]
    save_result(student_id, subject_id, 0, 60, 0.0, 0, 60, "scan.jpg", details, db_path)

    regrade_subject(subject_id, db_path)

    assert get_results_by_subject(subject_id, db_path) == []
    assert get_students_by_exam(exam_id, db_path)[0]["name"] == "Ada"


def test_save_students_skips_duplicate_student_ids(db_path: str) -> None:
    exam_id = create_exam("Exam", db_path)
    save_students(
        exam_id,
        [{"name": "Ada", "student_identifier": "STU001"}, {"name": "Bola", "student_identifier": "STU001"}],
        db_path,
    )

    students = get_students_by_exam(exam_id, db_path)

    assert len(students) == 1
    assert students[0]["name"] == "Ada"


def test_get_subject_stats_returns_average_and_pass_count(db_path: str) -> None:
    exam_id = create_exam("Exam", db_path)
    subject_id = create_subject(exam_id, "Math", db_path)
    save_student(exam_id, "Ada", "STU001", db_path=db_path)
    save_student(exam_id, "Bola", "STU002", db_path=db_path)
    students = get_students_by_exam(exam_id, db_path)
    details = [{"question": q, "detected": "A", "correct": "A", "status": "correct"} for q in range(1, 61)]
    save_result(students[0]["id"], subject_id, 60, 60, 100.0, 0, 0, "a.jpg", details, db_path)
    save_result(students[1]["id"], subject_id, 30, 60, 50.0, 0, 0, "b.jpg", details, db_path)

    stats = get_subject_stats(subject_id, db_path)

    assert stats["average_score"] == 45.0
    assert stats["pass_count"] == 2


def test_save_result_creates_student_assessment(db_path: str) -> None:
    exam_id = create_exam("Exam", db_path)
    subject_id = create_subject(exam_id, "Math", db_path)
    student_id = save_student(exam_id, "Ada", "STU001", db_path=db_path)
    details = [{"question": q, "detected": "A", "correct": "A", "status": "correct"} for q in range(1, 61)]

    save_result(student_id, subject_id, 60, 60, 100.0, 0, 0, "scan.jpg", details, db_path)

    assessments = get_assessments_by_exam(exam_id, db_path)
    assert assessments[0]["student_identifier"] == "STU001"
    assert assessments[0]["subject_count"] == 1
