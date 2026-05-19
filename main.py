import argparse
import csv
from pathlib import Path
from typing import Any

import cv2

from config import FILL_THRESHOLD, OPTIONS, OUTPUT_DIR, QUESTIONS_PER_SHEET, SAMPLE_RADIUS
from database.models import init_db
from database.queries import (
    create_exam,
    create_subject,
    get_all_exams,
    get_answer_key,
    get_students_by_exam,
    get_subjects_by_exam,
    save_answer_key,
    save_result,
    save_student,
    save_students,
)
from pipeline.detector import build_bubble_grid, detect_with_anomalies
from pipeline.exporter import export_to_csv
from pipeline.grader import grade
from pipeline.loader import load_file
from pipeline.preprocessor import preprocess


def main() -> None:
    """Run the OMR command-line interface."""
    parser = build_parser()
    args = parser.parse_args()
    init_db()
    if args.calibrate:
        run_calibration(args.input, args.output)
        return
    validate_grading_args(args)
    if args.students:
        run_batch(args)
    else:
        run_individual(args)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(description="PHF OMR Grading System")
    parser.add_argument("--input", required=True, help="Scan file or folder")
    parser.add_argument("--key", help="Answer key CSV with question,answer columns")
    parser.add_argument("--students", help="Class list CSV with name,class_group columns")
    parser.add_argument("--student-name", help="Student name for individual grading")
    parser.add_argument("--student-id", help="Student ID for individual grading")
    parser.add_argument("--class-group", help="Optional class or group for individual grading")
    parser.add_argument("--subject", help="Subject name")
    parser.add_argument("--exam", help="Exam name")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output folder")
    parser.add_argument("--calibrate", action="store_true", help="Create annotated calibration image")
    return parser


def validate_grading_args(args: argparse.Namespace) -> None:
    """Validate required grading arguments."""
    missing = [name for name in ("key", "subject", "exam") if not getattr(args, name)]
    if not args.students:
        missing.extend(name for name in ("student_name", "student_id") if not getattr(args, name))
    if missing:
        labels = ["--" + name.replace("_", "-") for name in missing]
        raise SystemExit(f"Missing required arguments: {', '.join(labels)}")


def run_batch(args: argparse.Namespace) -> None:
    """Run batch grading from CSV inputs and scan files."""
    exam_id = get_or_create_exam(args.exam)
    subject_id = get_or_create_subject(exam_id, args.subject)
    answer_key = read_answer_key_csv(args.key)
    students = read_students_csv(args.students)
    save_answer_key(subject_id, answer_key)
    save_students(exam_id, students)
    db_students = get_students_by_exam(exam_id)
    scan_paths = collect_scan_paths(args.input)
    sheet_count = count_sheets(scan_paths)
    if len(students) != sheet_count:
        raise SystemExit(f"Class list rows ({len(students)}) do not match detected sheets ({sheet_count})")
    rows = process_scan_paths(scan_paths, db_students, subject_id, args.subject, answer_key)
    output_path = str(Path(args.output) / f"{args.exam}_{args.subject}_results.csv")
    export_to_csv(rows, output_path)
    print(f"Processed {len(rows)} sheets. CSV written to {output_path}")


def run_individual(args: argparse.Namespace) -> None:
    """Run individual grading for one student answer sheet."""
    exam_id = get_or_create_exam(args.exam)
    subject_id = get_or_create_subject(exam_id, args.subject)
    answer_key = read_answer_key_csv(args.key)
    save_answer_key(subject_id, answer_key)
    student_id = save_student(exam_id, args.student_name, args.student_id, args.class_group)
    sheets = [sheet for path in collect_scan_paths(args.input) for sheet in load_file(str(path))]
    if len(sheets) != 1:
        raise SystemExit(f"Individual grading requires exactly one answer sheet; found {len(sheets)}")
    student = {
        "id": student_id,
        "name": args.student_name,
        "student_identifier": args.student_id,
        "class_group": args.class_group,
    }
    row = process_one_sheet(sheets[0], student, subject_id, args.subject, answer_key, Path(args.input).name)
    output_path = str(Path(args.output) / f"{args.student_id}_{args.subject}_result.csv")
    export_to_csv([row], output_path)
    print(f"Stored assessment for {args.student_name} ({args.student_id}). CSV written to {output_path}")


def get_or_create_exam(name: str) -> int:
    """Return an existing exam id or create it."""
    for exam in get_all_exams():
        if exam["name"] == name:
            return int(exam["id"])
    return create_exam(name)


def get_or_create_subject(exam_id: int, name: str) -> int:
    """Return an existing subject id or create it."""
    for subject in get_subjects_by_exam(exam_id):
        if subject["name"] == name:
            return int(subject["id"])
    return create_subject(exam_id, name)


def read_answer_key_csv(path: str) -> dict[int, str]:
    """Read and validate an answer key CSV."""
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    key = {int(row["question"]): row["answer"].strip().upper() for row in rows}
    if any(answer not in OPTIONS for answer in key.values()):
        raise ValueError("Answer key CSV contains values outside A-E")
    if set(key.keys()) != set(range(1, QUESTIONS_PER_SHEET + 1)):
        raise ValueError("Answer key CSV must contain questions 1-60 exactly")
    return key


def read_students_csv(path: str) -> list[dict[str, Any]]:
    """Read and validate a class list CSV."""
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "name" not in reader.fieldnames:
            raise ValueError('Class list CSV is missing the "name" column')
        return [
            {"name": row["name"], "class_group": row.get("class_group"), "position": index}
            for index, row in enumerate(reader, start=1)
            if row.get("name", "").strip()
        ]


def collect_scan_paths(input_path: str) -> list[Path]:
    """Collect supported scan paths from one file or folder."""
    path = Path(input_path)
    if path.is_file():
        return [path]
    if path.is_dir():
        suffixes = {".jpg", ".jpeg", ".png", ".pdf"}
        return sorted(item for item in path.iterdir() if item.suffix.lower() in suffixes)
    raise FileNotFoundError(input_path)


def count_sheets(scan_paths: list[Path]) -> int:
    """Count subject sheets represented by image files and PDF pages."""
    return sum(len(load_file(str(path))) for path in scan_paths)


def process_scan_paths(
    scan_paths: list[Path],
    students: list[dict[str, Any]],
    subject_id: int,
    subject_name: str,
    answer_key: dict[int, str],
) -> list[dict[str, Any]]:
    """Process all scans, save results, and return export rows."""
    output_rows = []
    student_index = 0
    for path in scan_paths:
        for image in load_file(str(path)):
            student = students[student_index]
            student_index += 1
            row = process_one_sheet(image, student, subject_id, subject_name, answer_key, path.name)
            output_rows.append(row)
    return output_rows


def process_one_sheet(
    image: Any,
    student: dict[str, Any],
    subject_id: int,
    subject_name: str,
    answer_key: dict[int, str],
    scan_file: str,
) -> dict[str, Any]:
    """Process and persist one student's answer sheet."""
    processed = preprocess(image)
    detected, anomalies, _ = detect_with_anomalies(processed["grid_thresh"])
    graded = grade(detected, answer_key, anomalies)
    details = [
        {"question": question, **detail}
        for question, detail in graded["per_question"].items()
    ]
    save_result(
        student["id"],
        subject_id,
        graded["score"],
        graded["total"],
        graded["percentage"],
        len(graded["flagged"]),
        len(graded["skipped"]),
        scan_file,
        details,
    )
    return {
        "student_id": student.get("student_identifier", ""),
        "student_name": student["name"],
        "class_group": student.get("class_group"),
        "subject": subject_name,
        "score": graded["score"],
        "total": graded["total"],
        "percentage": graded["percentage"],
        "flagged_count": len(graded["flagged"]),
        "skipped_count": len(graded["skipped"]),
        "per_question": graded["per_question"],
    }


def run_calibration(input_path: str, output_dir: str) -> None:
    """Create an annotated calibration image and print fill ratios."""
    images = load_file(input_path)
    processed = preprocess(images[0])
    _, _, raw_fills = detect_with_anomalies(processed["grid_thresh"])
    annotated = processed["warped"].copy()
    grid = build_bubble_grid(processed["grid_thresh"].shape)
    for question, options in grid.items():
        for option, (cx, cy) in options.items():
            color = (0, 180, 0) if raw_fills[question][option] >= FILL_THRESHOLD else (0, 0, 255)
            cv2.circle(annotated, (cx, cy), SAMPLE_RADIUS, color, 2)
            print(f"Q{question:02d} {option}: {raw_fills[question][option]:.4f}")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = Path(output_dir) / f"calibration_{Path(input_path).stem}.jpg"
    cv2.imwrite(str(output_path), annotated)
    print(f"Calibration image written to {output_path}")


if __name__ == "__main__":
    main()
