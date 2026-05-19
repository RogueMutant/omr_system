from config import QUESTIONS_PER_SHEET


def grade(detected: dict[int, str | None], answer_key: dict[int, str], anomalies: list[dict]) -> dict:
    """Grade detected answers against a complete answer key."""
    _validate_answer_key(answer_key)
    multiple_filled = {item["question"] for item in anomalies if item["issue"] == "multiple_filled"}
    correct: list[int] = []
    wrong: list[int] = []
    skipped: list[int] = []
    flagged: list[int] = []
    per_question = {}
    for question in range(1, QUESTIONS_PER_SHEET + 1):
        actual = detected.get(question)
        expected = answer_key[question]
        status = _status_for_question(question, actual, expected, multiple_filled)
        per_question[question] = {"detected": actual, "correct": expected, "status": status}
        if status == "correct":
            correct.append(question)
        elif status == "skipped":
            skipped.append(question)
        elif status == "flagged":
            flagged.append(question)
        else:
            wrong.append(question)
    score = len(correct)
    return {
        "score": score,
        "total": QUESTIONS_PER_SHEET,
        "percentage": round((score / QUESTIONS_PER_SHEET) * 100, 2),
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "flagged": flagged,
        "per_question": per_question,
    }


def _validate_answer_key(answer_key: dict[int, str]) -> None:
    """Validate that an answer key covers every question."""
    expected = set(range(1, QUESTIONS_PER_SHEET + 1))
    if set(answer_key.keys()) != expected:
        raise ValueError("Answer key must contain exactly questions 1-60")


def _status_for_question(question: int, actual: str | None, expected: str, multiple_filled: set[int]) -> str:
    """Classify one graded question."""
    if question in multiple_filled:
        return "flagged"
    if actual is None:
        return "skipped"
    if actual == expected:
        return "correct"
    return "wrong"
