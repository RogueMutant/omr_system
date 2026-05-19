# PHF OMR Grading System

Local OMR grading system for the 2026 PHF PRE-BECE exam. Each scan image, or each PDF page, is treated as one subject answer sheet. Students are entered individually with each uploaded answer sheet, and each student's subject results are stored under one assessment.

## System Requirements

- Python 3.10+
- Poppler for PDF support through `pdf2image`
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`
  - macOS: `brew install poppler`
  - Windows: [Poppler for pdf support](https://github.com/oschwartz10612/poppler-windows)

## Install

```bash
pip install -r requirements.txt
```

## Run Dashboard

```bash
streamlit run app.py
```

The dashboard lets you create exams and subjects, save answer keys, upload individual answer sheets with student details, review assessments, and export CSV reports.

By default the app uses a local SQLite database at `omr.db`. To use Neon Postgres, set `DATABASE_URL` to your Neon connection string before starting Streamlit. In Streamlit Community Cloud, add `DATABASE_URL` in the app's Secrets settings.

The first admin account is created automatically when the `users` table is empty. Defaults are `admin` / `omr1234`; override them with `ADMIN_USERNAME` and `ADMIN_PASSWORD` in environment variables or Streamlit secrets before the first startup.

## Individual Upload Flow

For each answer sheet:

1. Select the exam and subject.
2. Enter the student name and student ID.
3. Optionally enter the class/group.
4. Upload one answer sheet image or a one-page PDF.
5. Grade and store the result.

Each student can have three stored subject results, one per subject. Re-uploading the same student ID for the same subject replaces that subject result.

## Run CLI

```bash
python main.py --help
```

Individual grading example:

```bash
python main.py \
  --input sample_data/ada_math.jpg \
  --key answer_key.csv \
  --student-name "Ada Okafor" \
  --student-id STU001 \
  --class-group "JSS 2A" \
  --subject Mathematics \
  --exam "2026 PRE-BECE" \
  --output output
```

The dashboard is the primary workflow for individual uploads. The CLI remains available for individual grading and calibration.

## Answer Key CSV

The file must contain exactly questions 1-60.

```csv
question,answer
1,A
2,B
3,C
```

Answers must be one of `A`, `B`, `C`, `D`, or `E`.

## Calibration Mode

Calibration mode processes one scan and writes an annotated image to `output/`.

```bash
python main.py --calibrate --input sample_data/example.jpg
```

Green circles are above the fill threshold. Red circles are below the fill threshold. Fill ratios are printed to stdout for every bubble.

## Tests

```bash
pytest tests/
```

## Output CSV Columns

Full exports include:

- `student_id`
- `student_name`
- `class_group`
- `subject`
- `score`
- `total`
- `percentage`
- `flagged_count`
- `skipped_count`
- `q1` through `q60`

Question values are the detected answer letter, an empty string for skipped questions, or `FLAG` for flagged questions.

The aggregate export arranges one row per student as:

```text
student_id,name,<subject score columns>,aggregate,percentage,positionInResult
```

Positions are ranked by aggregate score descending, with tied scores sharing the same position.

## Known Limitations

- Handwritten student information is not read.
- The border rectangle must be clearly visible in the scan.
- One subject answer sheet per image/PDF page is assumed always.

## Streamlit Community Cloud Hosting

This project is ready for Streamlit Community Cloud.

Deployment settings:

- Repository path: this project folder
- Main file path: `app.py`
- Python version: `runtime.txt`
- Python dependencies: `requirements.txt`
- System dependencies: `packages.txt`

Set this secret in Streamlit Community Cloud:

```toml
DATABASE_URL = "your-neon-postgres-connection-string"
```

The included `packages.txt` installs Poppler for PDF uploads, and the app initializes the required Postgres tables automatically on startup.
