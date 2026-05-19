import numpy as np

from config import FILL_THRESHOLD, OPTIONS, QUESTIONS_PER_SHEET
from pipeline.detector import (
    build_bubble_grid,
    detect_answers,
    flag_anomalies,
    is_bubble_filled,
)


def test_is_bubble_filled_returns_near_zero_on_blank_image() -> None:
    image = np.zeros((100, 100), dtype=np.uint8)

    ratio = is_bubble_filled(image, 50, 50, 10)

    assert ratio == 0.0


def test_is_bubble_filled_returns_near_one_on_filled_image() -> None:
    image = np.full((100, 100), 255, dtype=np.uint8)

    ratio = is_bubble_filled(image, 50, 50, 10)

    assert ratio > 0.95


def test_flag_anomalies_detects_multiple_filled() -> None:
    fills = {1: {"A": FILL_THRESHOLD + 0.1, "B": FILL_THRESHOLD + 0.2, "C": 0, "D": 0, "E": 0}}

    anomalies = flag_anomalies(fills)

    assert anomalies == [{"question": 1, "issue": "multiple_filled", "fills": fills[1]}]


def test_flag_anomalies_detects_no_answer() -> None:
    fills = {1: {option: 0.0 for option in OPTIONS}}

    anomalies = flag_anomalies(fills)

    assert anomalies == [{"question": 1, "issue": "no_answer", "fills": fills[1]}]


def test_detect_answers_returns_all_questions_on_blank_image() -> None:
    image = np.zeros((1000, 800), dtype=np.uint8)

    detected = detect_answers(image)

    assert len(detected) == QUESTIONS_PER_SHEET
    assert all(answer is None for answer in detected.values())


def test_detect_answers_accepts_clear_tick_below_shaded_threshold() -> None:
    image = np.zeros((1000, 800), dtype=np.uint8)
    cx, cy = build_bubble_grid(image.shape)[3]["A"]
    import cv2

    cv2.line(image, (cx - 7, cy), (cx - 2, cy + 6), 255, 5)
    cv2.line(image, (cx - 2, cy + 6), (cx + 9, cy - 8), 255, 5)

    detected = detect_answers(image)

    assert detected[3] == "A"


def test_build_bubble_grid_returns_all_questions_and_options() -> None:
    grid = build_bubble_grid((1000, 800))

    assert len(grid) == QUESTIONS_PER_SHEET
    assert all(set(options.keys()) == set(OPTIONS) for options in grid.values())
