import cv2
import numpy as np

from config import (
    ADAPTIVE_THRESHOLD_BLOCK_SIZE,
    ADAPTIVE_THRESHOLD_C,
    BORDER_APPROX_EPSILON,
    BORDER_MIN_AREA_RATIO,
    GAUSSIAN_BLUR_KERNEL,
    WARP_HEIGHT,
    WARP_WIDTH,
)


def preprocess(image: np.ndarray) -> dict:
    """Deskew, crop, threshold, and return intermediate processing images."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, GAUSSIAN_BLUR_KERNEL, 0)
    thresh = threshold_image(blurred)
    border_rect = find_border_rectangle(thresh)
    warped = perspective_transform(image, border_rect)
    warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    warped_thresh = threshold_image(warped_gray)
    return {
        "original": image,
        "gray": gray,
        "thresh": thresh,
        "warped": warped,
        "warped_thresh": warped_thresh,
        "grid_roi": warped,
        "grid_thresh": warped_thresh,
        "border_rect": border_rect.tolist(),
    }


def find_border_rectangle(thresh: np.ndarray) -> np.ndarray:
    """Find the largest four-corner border rectangle in a threshold image."""
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = thresh.shape[0] * thresh.shape[1]
    candidates: list[tuple[float, np.ndarray]] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < image_area * BORDER_MIN_AREA_RATIO:
            continue
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, BORDER_APPROX_EPSILON * perimeter, True)
        if len(approx) == 4:
            candidates.append((area, approx.reshape(4, 2).astype("float32")))
    if not candidates:
        raise RuntimeError("Border rectangle not detected")
    return order_points(max(candidates, key=lambda item: item[0])[1])


def order_points(pts: np.ndarray) -> np.ndarray:
    """Order corners as top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    sums = pts.sum(axis=1)
    diffs = np.diff(pts, axis=1).reshape(-1)
    rect[0] = pts[np.argmin(sums)]
    rect[2] = pts[np.argmax(sums)]
    rect[1] = pts[np.argmin(diffs)]
    rect[3] = pts[np.argmax(diffs)]
    return rect


def perspective_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Warp the sheet border into the configured fixed output size."""
    rect = order_points(pts.astype("float32"))
    dst = np.array(
        [[0, 0], [WARP_WIDTH - 1, 0], [WARP_WIDTH - 1, WARP_HEIGHT - 1], [0, WARP_HEIGHT - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (WARP_WIDTH, WARP_HEIGHT))


def threshold_image(gray: np.ndarray) -> np.ndarray:
    """Apply adaptive inverse binary thresholding for uneven scan lighting."""
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        ADAPTIVE_THRESHOLD_BLOCK_SIZE,
        ADAPTIVE_THRESHOLD_C,
    )
