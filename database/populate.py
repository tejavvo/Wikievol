#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional

import mysql.connector  # pip install mysql-connector-python

# ============================================================
# Column macros
# ============================================================
COL = {
    "wiki_db": "wiki_db",
    "page_id": "page_id",
    "item_id": "item_id",
    "revision_id": "revision_id",
    "revision_timestamp": "revision_timestamp",
    "month": "month",
    "page_title": "page_title",
    "quality_class": "quality_class",
    "importance_class": "importance_class",
    "page_length": "page_length",
    "num_refs": "num_refs",
    "num_wikilinks": "num_wikilinks",
    "num_categories": "num_categories",
    "num_media": "num_media",
    "num_headings": "num_headings",
    "pred_qual": "pred_qual",
}

# ============================================================
# SQL queries
# NOTE: Placeholders changed from ? (SQLite) to %s (MariaDB/MySQL)
#       INSERT OR REPLACE  → INSERT ... ON DUPLICATE KEY UPDATE
#       INSERT OR IGNORE   → INSERT IGNORE
# ============================================================
INSERT_WIKIPROJECT = """
INSERT INTO WikiProject (project_name, wiki_db)
VALUES (%s, %s)
ON DUPLICATE KEY UPDATE wiki_db = VALUES(wiki_db)
"""

GET_PROJECT_ID = """
SELECT project_id FROM WikiProject WHERE project_name = %s
"""

INSERT_ARTICLE = """
INSERT INTO Article (page_id, page_title, quality_class, importance_class, item_id, wiki_db)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    page_title      = VALUES(page_title),
    quality_class   = VALUES(quality_class),
    importance_class= VALUES(importance_class),
    item_id         = VALUES(item_id),
    wiki_db         = VALUES(wiki_db)
"""

INSERT_ARTICLE_PROJECT = """
INSERT IGNORE INTO Article_Project (page_id, project_id)
VALUES (%s, %s)
"""

INSERT_REVISION = """
INSERT INTO Revision (
    revision_id, page_id, revision_timestamp, month,
    page_length, num_refs, num_wikilinks, num_categories,
    num_media, num_headings, pred_qual
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    page_id            = VALUES(page_id),
    revision_timestamp = VALUES(revision_timestamp),
    month              = VALUES(month),
    page_length        = VALUES(page_length),
    num_refs           = VALUES(num_refs),
    num_wikilinks      = VALUES(num_wikilinks),
    num_categories     = VALUES(num_categories),
    num_media          = VALUES(num_media),
    num_headings       = VALUES(num_headings),
    pred_qual          = VALUES(pred_qual)
"""



POPULATE_MONTHLY_AGGREGATION = """
INSERT INTO MonthlyAggregation (
    project_id,
    month,
    num_articles,

    mean_page_length,
    sum_page_length,

    mean_refs,
    sum_refs,

    mean_media,
    sum_media,

    mean_headings,
    sum_headings,

    mean_pred_qual
)

SELECT
    AP.project_id,
    R.month,

    COUNT(DISTINCT R.page_id),

    AVG(R.page_length),
    SUM(R.page_length),

    AVG(R.num_refs),
    SUM(R.num_refs),

    AVG(R.num_media),
    SUM(R.num_media),

    AVG(R.num_headings),
    SUM(R.num_headings),

    AVG(R.pred_qual)

FROM Revision R
JOIN Article_Project AP
    ON AP.page_id = R.page_id

GROUP BY
    AP.project_id,
    R.month

ON DUPLICATE KEY UPDATE

    num_articles     = VALUES(num_articles),

    mean_page_length = VALUES(mean_page_length),
    sum_page_length  = VALUES(sum_page_length),

    mean_refs        = VALUES(mean_refs),
    sum_refs         = VALUES(sum_refs),

    mean_media       = VALUES(mean_media),
    sum_media        = VALUES(sum_media),

    mean_headings    = VALUES(mean_headings),
    sum_headings     = VALUES(sum_headings),

    mean_pred_qual   = VALUES(mean_pred_qual)
"""



# ============================================================
# Helpers  (unchanged from SQLite version)
# ============================================================
def to_int(value: Optional[str]) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None

def to_float(value: Optional[str]) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def normalize_month(value: Optional[str]) -> Optional[str]:
    if value in (None, ""):
        return None
    value = str(value).strip()
    if len(value) >= 7 and value[4] == "-":
        return value[:7]
    if len(value) == 6 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}"
    return value[:7]

def read_csv(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def infer_project_name(csv_path: Path) -> str:
    return csv_path.stem

# ============================================================
# Loaders
# ============================================================
def load_revisions(
    cursor,
    project_name: str,
    revision_rows: List[Dict[str, str]],
    wiki_db: str
) -> int:
    """Insert WikiProject and return project_id."""
    cursor.execute(INSERT_WIKIPROJECT, (project_name, wiki_db))
    cursor.execute(GET_PROJECT_ID, (project_name,))
    row = cursor.fetchone()
    return row[0]


def load_assessments(
    cursor,
    project_id: int,
    assessment_rows: List[Dict[str, str]],
    wiki_db: str,
    item_id_map: Dict[int, str]
) -> None:
    """Insert Article rows and link to project via Article_Project."""
    if item_id_map is None:
        item_id_map = {}

    for row in assessment_rows:
        page_id = to_int(row.get(COL["page_id"]))

        cursor.execute(INSERT_ARTICLE, (
            page_id,
            row.get(COL["page_title"]),
            row.get(COL["quality_class"]),
            row.get(COL["importance_class"]),
            item_id_map.get(page_id),
            wiki_db,
        ))

        cursor.execute(INSERT_ARTICLE_PROJECT, (page_id, project_id))


def load_project_pair(cursor, revision_csv: Path, assessment_csv: Path) -> None:
    project_name = infer_project_name(revision_csv)

    revision_rows = read_csv(revision_csv)
    assessment_rows = read_csv(assessment_csv)

    if not revision_rows:
        raise ValueError(f"Empty revision CSV: {revision_csv}")
    if not assessment_rows:
        raise ValueError(f"Empty assessment CSV: {assessment_csv}")

    wiki_db = revision_rows[0].get(COL["wiki_db"], "")
    if not wiki_db:
        raise ValueError(f"Missing wiki_db in revision CSV: {revision_csv}")

    # Build item_id map: page_id -> item_id
    item_id_map = {}
    for row in revision_rows:
        page_id = to_int(row.get(COL["page_id"]))
        item_id = row.get(COL["item_id"])
        if page_id and item_id and page_id not in item_id_map:
            item_id_map[page_id] = item_id

    project_id = load_revisions(cursor, project_name, revision_rows, wiki_db)
    load_assessments(cursor, project_id, assessment_rows, wiki_db, item_id_map)

    for row in revision_rows:
        cursor.execute(INSERT_REVISION, (
            to_int(row.get(COL["revision_id"])),
            to_int(row.get(COL["page_id"])),
            row.get(COL["revision_timestamp"]),
            normalize_month(row.get(COL["month"])),
            to_int(row.get(COL["page_length"])),
            to_int(row.get(COL["num_refs"])),
            to_int(row.get(COL["num_wikilinks"])),
            to_int(row.get(COL["num_categories"])),
            to_int(row.get(COL["num_media"])),
            to_int(row.get(COL["num_headings"])),
            to_float(row.get(COL["pred_qual"])),
        ))


def find_matching_files(revisions_dir: Path, assessments_dir: Path) -> List[tuple]:
    revision_files = {f.stem: f for f in revisions_dir.glob("*.csv")}
    assessment_files = {f.stem: f for f in assessments_dir.glob("*.csv")}
    common_projects = set(revision_files.keys()) & set(assessment_files.keys())
    if not common_projects:
        raise ValueError(f"No matching CSV pairs found in {revisions_dir} and {assessments_dir}")
    return [(revision_files[p], assessment_files[p]) for p in sorted(common_projects)]


# ============================================================
# Main
# ============================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Load WikiEvolution data into MariaDB.")
    # MariaDB connection args (replacing --db path)
    parser.add_argument("--host",     default="127.0.0.1", help="MariaDB host")
    parser.add_argument("--port",     type=int, default=3306, help="MariaDB port")
    parser.add_argument("--user",     required=True, help="MariaDB username")
    parser.add_argument("--password", required=True, help="MariaDB password")
    parser.add_argument("--database", required=True, help="MariaDB database name")
    # # Data dirs (unchanged)
    parser.add_argument("--revisions-dir",   required=True, help="Directory containing revision CSVs")
    parser.add_argument("--assessments-dir", required=True, help="Directory containing assessment CSVs")
    args = parser.parse_args()

    revisions_dir   = Path(args.revisions_dir)
    assessments_dir = Path(args.assessments_dir)

    if not revisions_dir.is_dir():
        raise SystemExit(f"Revisions directory not found: {revisions_dir}")
    if not assessments_dir.is_dir():
        raise SystemExit(f"Assessments directory not found: {assessments_dir}")

    pairs = find_matching_files(revisions_dir, assessments_dir)
    print(f"Found {len(pairs)} matching project pairs")

    # --- MariaDB connection (replaces sqlite3.connect) ---
    conn = mysql.connector.connect(
        host='10.150.10.172',
        port=3307,
        user="s56188",
        password="N4lk6mRLfLS6Rlyp",
        database="s56188__wikievol",
        autocommit=False,           # explicit transaction control
    )

    try:
        cursor = conn.cursor()
        cursor.execute("SET foreign_key_checks = 1")  # replaces PRAGMA foreign_keys = ON

        for revision_csv, assessment_csv in pairs:
            project_name = revision_csv.stem
            print(f"Loading {project_name}...")
            load_project_pair(cursor, revision_csv, assessment_csv)

        print("Computing monthly aggregates...")
        cursor.execute("DELETE FROM MonthlyAggregation")
        cursor.execute(POPULATE_MONTHLY_AGGREGATION)

        conn.commit()
        print("✓ Data loaded successfully")
    except Exception as e:
        conn.rollback()
        print(f"✗ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()