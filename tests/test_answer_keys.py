import pandas as pd
import pytest

from dashboard.pages.answer_keys import _csv_key


def test_csv_key_accepts_trimmed_case_insensitive_columns() -> None:
    df = pd.DataFrame({" Question ": [1, 2], " Answer ": ["a", " b "]})

    assert _csv_key(df) == {1: "A", 2: "B"}


def test_csv_key_rejects_missing_required_columns() -> None:
    df = pd.DataFrame({"question": [1], "option": ["A"]})

    with pytest.raises(ValueError, match="question and answer"):
        _csv_key(df)


def test_csv_key_rejects_invalid_question_values() -> None:
    df = pd.DataFrame({"question": ["one"], "answer": ["A"]})

    with pytest.raises(ValueError, match="Question values must be numbers"):
        _csv_key(df)


def test_csv_key_rejects_blank_answers() -> None:
    df = pd.DataFrame({"question": [1], "answer": [" "]})

    with pytest.raises(ValueError, match="Answer values cannot be blank"):
        _csv_key(df)
