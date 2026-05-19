import os

from database.connection import configured_database_url, is_postgres_url


DB_PATH = configured_database_url() or os.getenv("DB_PATH", "omr.db")

OUTPUT_DIR = "output"
SAMPLE_DIR = "sample_data"

DPI = 300
GAUSSIAN_BLUR_KERNEL = (5, 5)

QUESTIONS_PER_SHEET = 60
OPTIONS = ["A", "B", "C", "D", "E"]
NUM_OPTIONS = 5
NUM_COLUMNS = 4
NUM_ROWS = 15

HOUGH_DP = 1
HOUGH_MIN_DIST = 20
HOUGH_PARAM1 = 50
HOUGH_PARAM2 = 30
HOUGH_MIN_RADIUS = 8
HOUGH_MAX_RADIUS = 20

FILL_THRESHOLD = 0.45
TICK_FILL_THRESHOLD = 0.38
MIN_SELECTED_MARGIN = 0.07
SAMPLE_RADIUS = 12
ADAPTIVE_THRESHOLD_BLOCK_SIZE = 51
ADAPTIVE_THRESHOLD_C = 2

BORDER_APPROX_EPSILON = 0.02
BORDER_MIN_AREA_RATIO = 0.15

WARP_WIDTH = 800
WARP_HEIGHT = 1000

COLUMN_X_STARTS = [55, 255, 455, 655]
OPTION_X_SPACING = 29
ROW_Y_START = 61
ROW_Y_SPACING = 62

db_dir = os.path.dirname(DB_PATH)
if db_dir and not is_postgres_url(DB_PATH):
    os.makedirs(db_dir, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)
