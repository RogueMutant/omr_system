from pathlib import Path

import cv2
import numpy as np
from pdf2image import convert_from_path

from config import DPI


def load_file(filepath: str) -> list[np.ndarray]:
    """Load an image or PDF as one subject answer sheet image per item."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(filepath)
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png"}:
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Could not read image: {filepath}")
        return [normalize_sheet_image(image)]
    if suffix == ".pdf":
        pages = convert_from_path(str(path), dpi=DPI)
        return [cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR) for page in pages]
    raise ValueError(f"Unsupported file type: {suffix}")


def normalize_sheet_image(image: np.ndarray) -> np.ndarray:
    """Return the full subject answer sheet image."""
    return image.copy()
