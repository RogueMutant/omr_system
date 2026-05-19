import csv
from pathlib import Path

from pipeline.detector import detect_with_anomalies
from pipeline.grader import grade
from pipeline.loader import load_file
from pipeline.preprocessor import preprocess


def test_sample_answer_sheet_matches_expected_score() -> None:
    """Grade the real sample sheet against the test key."""
    image_path = Path("sample_data/sample_answer_sheet.png")
    key_path = Path("sample_data/test_answer_key.csv")
    with key_path.open(newline="") as handle:
        answer_key = {int(row["question"]): row["answer"] for row in csv.DictReader(handle)}

    processed = preprocess(load_file(str(image_path))[0])
    detected, anomalies, _ = detect_with_anomalies(processed["grid_thresh"])
    result = grade(detected, answer_key, anomalies)

    assert detected[3] == "A"
    assert detected[50] == "E"
    assert result["score"] == 11
