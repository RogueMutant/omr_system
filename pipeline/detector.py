import cv2
import numpy as np

from config import (
    COLUMN_X_STARTS,
    FILL_THRESHOLD,
    MIN_SELECTED_MARGIN,
    NUM_ROWS,
    OPTION_X_SPACING,
    OPTIONS,
    QUESTIONS_PER_SHEET,
    ROW_Y_SPACING,
    ROW_Y_START,
    SAMPLE_RADIUS,
    TICK_FILL_THRESHOLD,
)


def detect_answers(grid_thresh: np.ndarray) -> dict[int, str | None]:
    """Detect filled answers for all 60 questions using grid sampling."""
    raw_fills = _measure_all_fills(grid_thresh)
    detected: dict[int, str | None] = {}
    for question, option_fills in raw_fills.items():
        filled = _selected_options(option_fills)
        detected[question] = filled[0] if len(filled) == 1 else None
    return detected


def build_bubble_grid(image_shape: tuple) -> dict[int, dict[str, tuple[int, int]]]:
    """Build expected bubble center coordinates for the warped sheet."""
    grid: dict[int, dict[str, tuple[int, int]]] = {}
    for column, x_start in enumerate(COLUMN_X_STARTS):
        for row in range(NUM_ROWS):
            question = column * NUM_ROWS + row + 1
            if question > QUESTIONS_PER_SHEET:
                continue
            y = ROW_Y_START + row * ROW_Y_SPACING
            grid[question] = {
                option: (x_start + option_index * OPTION_X_SPACING, y)
                for option_index, option in enumerate(OPTIONS)
            }
    return grid


def is_bubble_filled(thresh: np.ndarray, cx: int, cy: int, radius: int) -> float:
    """Return the ratio of marked pixels inside a circular bubble sample."""
    height, width = thresh.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.circle(mask, (int(cx), int(cy)), int(radius), 255, -1)
    sample = thresh[mask == 255]
    if sample.size == 0:
        return 0.0
    return round(float(np.count_nonzero(sample >= 128) / sample.size), 4)


def flag_anomalies(raw_fills: dict[int, dict[str, float]]) -> list[dict]:
    """Return multiple-fill and no-answer anomalies from raw fill ratios."""
    anomalies = []
    for question, fills in raw_fills.items():
        filled = _selected_options(fills)
        if len(filled) >= 2:
            anomalies.append({"question": question, "issue": "multiple_filled", "fills": fills})
        elif not filled:
            anomalies.append({"question": question, "issue": "no_answer", "fills": fills})
    return anomalies


def detect_with_anomalies(grid_thresh: np.ndarray) -> tuple[dict[int, str | None], list[dict], dict[int, dict[str, float]]]:
    """Detect answers and return anomalies plus raw fill ratios."""
    raw_fills = _measure_all_fills(grid_thresh)
    detected: dict[int, str | None] = {}
    for question, fills in raw_fills.items():
        filled = _selected_options(fills)
        detected[question] = filled[0] if len(filled) == 1 else None
    return detected, flag_anomalies(raw_fills), raw_fills


def _measure_all_fills(grid_thresh: np.ndarray) -> dict[int, dict[str, float]]:
    """Measure every expected bubble position on the warped sheet."""
    grid = build_bubble_grid(grid_thresh.shape)
    return {
        question: {
            option: is_bubble_filled(grid_thresh, center[0], center[1], SAMPLE_RADIUS)
            for option, center in options.items()
        }
        for question, options in grid.items()
    }


def _selected_options(option_fills: dict[str, float]) -> list[str]:
    """Return selected options, accepting clear tick marks below full-shade threshold."""
    filled = [option for option, ratio in option_fills.items() if ratio >= FILL_THRESHOLD]
    if filled:
        return filled
    ranked = sorted(option_fills.items(), key=lambda item: item[1], reverse=True)
    best_option, best_ratio = ranked[0]
    second_ratio = ranked[1][1] if len(ranked) > 1 else 0.0
    if best_ratio >= TICK_FILL_THRESHOLD and best_ratio - second_ratio >= MIN_SELECTED_MARGIN:
        return [best_option]
    return []
