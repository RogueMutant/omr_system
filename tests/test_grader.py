from config import QUESTIONS_PER_SHEET
from pipeline.grader import grade


def make_key() -> dict[int, str]:
    return {question: "A" for question in range(1, QUESTIONS_PER_SHEET + 1)}


def test_correct_answer_increments_score() -> None:
    detected = {question: None for question in range(1, QUESTIONS_PER_SHEET + 1)}
    detected[1] = "A"

    result = grade(detected, make_key(), [])

    assert result["score"] == 1
    assert result["per_question"][1]["status"] == "correct"


def test_flagged_question_counts_as_wrong_even_if_answer_matches() -> None:
    detected = {question: "A" for question in range(1, QUESTIONS_PER_SHEET + 1)}

    result = grade(detected, make_key(), [{"question": 1, "issue": "multiple_filled", "fills": {}}])

    assert result["score"] == QUESTIONS_PER_SHEET - 1
    assert result["per_question"][1]["status"] == "flagged"


def test_skipped_question_counts_as_wrong() -> None:
    detected = {question: "A" for question in range(1, QUESTIONS_PER_SHEET + 1)}
    detected[1] = None

    result = grade(detected, make_key(), [])

    assert result["score"] == QUESTIONS_PER_SHEET - 1
    assert result["per_question"][1]["status"] == "skipped"


def test_percentage_rounds_to_two_decimal_places() -> None:
    detected = {question: None for question in range(1, QUESTIONS_PER_SHEET + 1)}
    detected[1] = "A"

    result = grade(detected, make_key(), [])

    assert result["percentage"] == 1.67


def test_per_question_covers_all_questions() -> None:
    detected = {question: None for question in range(1, QUESTIONS_PER_SHEET + 1)}

    result = grade(detected, make_key(), [])

    assert set(result["per_question"].keys()) == set(range(1, QUESTIONS_PER_SHEET + 1))
