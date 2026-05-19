import numpy as np
import pytest

from config import ADAPTIVE_THRESHOLD_BLOCK_SIZE, SAMPLE_RADIUS, WARP_HEIGHT, WARP_WIDTH
from pipeline.preprocessor import (
    find_border_rectangle,
    order_points,
    perspective_transform,
    threshold_image,
)


def test_order_points_returns_tl_tr_br_bl() -> None:
    pts = np.array([[90, 90], [10, 10], [90, 10], [10, 90]], dtype="float32")

    ordered = order_points(pts)

    assert ordered.tolist() == [[10.0, 10.0], [90.0, 10.0], [90.0, 90.0], [10.0, 90.0]]


def test_perspective_transform_has_configured_output_shape() -> None:
    image = np.zeros((120, 120, 3), dtype=np.uint8)
    pts = np.array([[10, 10], [110, 10], [110, 110], [10, 110]], dtype="float32")

    warped = perspective_transform(image, pts)

    assert warped.shape == (WARP_HEIGHT, WARP_WIDTH, 3)


def test_find_border_rectangle_raises_on_blank_image() -> None:
    blank = np.zeros((500, 700), dtype=np.uint8)

    with pytest.raises(RuntimeError):
        find_border_rectangle(blank)


def test_threshold_image_outputs_binary_values() -> None:
    gray = np.tile(np.arange(100, dtype=np.uint8), (100, 1))

    thresh = threshold_image(gray)

    assert set(np.unique(thresh).tolist()).issubset({0, 255})


def test_adaptive_threshold_block_size_exceeds_bubble_diameter() -> None:
    """Keep adaptive thresholding from erasing filled bubble interiors."""
    assert ADAPTIVE_THRESHOLD_BLOCK_SIZE > SAMPLE_RADIUS * 2
