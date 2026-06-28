# from flask import Flask, request, jsonify, Response, send_from_directory
# import pandas as pd
# from flask_cors import CORS
# import requests
# from bs4 import BeautifulSoup
# import os
# import re
# import threading
# from urllib.parse import quote
# import sqlite3



# import process_wikiproject_monthly
# import process_wikiproject_latest

# app = Flask(__name__, static_folder='dist')
# CORS(app)

# # ---------------------------------------------------------------------------
# # Configuration
# # ---------------------------------------------------------------------------

# # Per-project processed CSVs are cached here so we don't re-download and
# # re-process the same WikiProject on every request.
# DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
# os.makedirs(DATA_DIR, exist_ok=True)


# DB_PATH = os.path.join(DATA_DIR, 'wikievolution.db')


# DATASET_BASE = "https://analytics.wikimedia.org/published/datasets/outreachy-round-28"

# # Wikimedia infrastructure rejects requests without a descriptive User-Agent
# # (HTTP 403). See https://meta.wikimedia.org/wiki/User-Agent_policy
# USER_AGENT = "WikiEvolution/1.0 (https://wikievol.toolforge.org/; toolforge-wikievol)"

# # WikiProject names are used to build filenames and URLs, so they must be
# # restricted to a safe character set (prevents path traversal / SSRF).
# PROJECT_NAME_RE = re.compile(r'^[A-Za-z0-9_-]+$')

# # Numeric feature columns shared by several endpoints.
# FEATURE_COLUMNS = [
#     'num_refs', 'num_media', 'num_wikilinks', 'num_categories',
#     'num_headings', 'page_length', 'pred_qual',
# ]

# # Per-project locks so two concurrent requests don't download/process the same
# # project's data simultaneously.
# _locks = {}
# _locks_guard = threading.Lock()


# def _project_lock(project):
#     with _locks_guard:
#         if project not in _locks:
#             _locks[project] = threading.Lock()
#         return _locks[project]


# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------

# def normalize_project(project):
#     """Strip a trailing '.csv' and validate the project name. Returns the clean
#     name, or None if it is missing/invalid."""
#     if not project:
#         return None
#     if project.endswith('.csv'):
#         project = project[:-4]
#     if not PROJECT_NAME_RE.match(project):
#         return None
#     return project


# def get_project():
#     """Read the project name from the request (query string or JSON body)."""
#     project = request.args.get('project') or request.args.get('project_name')
#     if not project and request.is_json:
#         body = request.get_json(silent=True) or {}
#         project = body.get('project') or body.get('project_name')
#     return normalize_project(project)


# def merged_path(project):
#     return os.path.join(DATA_DIR, f"{project}_merged.csv")


# def monthly_path(project):
#     return os.path.join(DATA_DIR, f"{project}_latest_monthly.csv")


# def ensure_project_data(project):
#     """Make sure the merged + monthly CSVs for ``project`` exist, building them
#     once if necessary. Returns (ok: bool, error: str | None)."""
#     if os.path.exists(merged_path(project)) and os.path.exists(monthly_path(project)):
#         return True, None

#     lock = _project_lock(project)
#     with lock:
#         # Re-check inside the lock in case another thread just built it.
#         if os.path.exists(merged_path(project)) and os.path.exists(monthly_path(project)):
#             return True, None
#         try:
#             process_wikiproject_latest.main(project, out_dir=DATA_DIR)
#             process_wikiproject_monthly.main(project, out_dir=DATA_DIR)
#         except Exception as e:
#             return False, str(e)

#     if os.path.exists(merged_path(project)) and os.path.exists(monthly_path(project)):
#         return True, None
#     return False, "Failed to build data for this WikiProject."


# def load_project_df(kind):
#     """Resolve the project from the request, ensure its data exists, and load
#     the requested dataframe. Returns (df, error_response). On success
#     error_response is None; on failure df is None and error_response is a ready
#     Flask (response, status) tuple."""
#     project = get_project()
#     if not project:
#         return None, (jsonify({"error": "Missing or invalid WikiProject name"}), 400)

#     ok, err = ensure_project_data(project)
#     if not ok:
#         return None, (jsonify({"error": err}), 502)

#     path = merged_path(project) if kind == 'merged' else monthly_path(project)
#     if not os.path.exists(path):
#         return None, (jsonify({"error": f"No {kind} data for '{project}'"}), 404)
#     return pd.read_csv(path), None


# def json_records(df):
#     """Serialize a dataframe to a JSON array response. Uses pandas' ``to_json``
#     (not ``jsonify``) so that NaN values become valid JSON ``null`` instead of
#     the bare ``NaN`` token, which browsers cannot parse."""
#     return Response(df.to_json(orient='records'), mimetype='application/json')


# # ---------------------------------------------------------------------------
# # Static SPA
# # ---------------------------------------------------------------------------

# @app.route('/', defaults={'path': ''})
# @app.route('/<path:path>')
# def serve_react_app(path):
#     if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
#         return send_from_directory(app.static_folder, path)
#     return send_from_directory(app.static_folder, 'index.html')


# # ---------------------------------------------------------------------------
# # API
# # ---------------------------------------------------------------------------

# @app.route('/get_wikiprojects', methods=['GET'])
# def get_wikiprojects():
#     """List the WikiProjects available in the published dataset."""
#     url = f'{DATASET_BASE}/revisions/'
#     try:
#         response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=30)
#         response.raise_for_status()
#     except requests.exceptions.RequestException as e:
#         return jsonify({'error': f'Failed to fetch WikiProjects: {e}'}), 502

#     soup = BeautifulSoup(response.text, 'html.parser')
#     names = [
#         a.get('href')[:-4]
#         for a in soup.find_all('a')
#         if a.get('href') and a.get('href').endswith('.csv')
#     ]
#     return jsonify(names)


# @app.route('/set_selected_wikiproject', methods=['POST'])
# def set_selected_wikiproject():
#     """Prepare (download + process) a project's data. Idempotent and cached;
#     no longer stores any global server-side state."""
#     project = get_project()
#     if not project:
#         return jsonify({'error': 'No valid WikiProject name provided'}), 400

#     ok, err = ensure_project_data(project)
#     if not ok:
#         return jsonify({'error': f'Failed to process data: {err}'}), 502
#     return jsonify({'success': f'Data ready for {project}.'}), 200


# @app.route('/get_csv_data', methods=['GET'])
# def get_csv_data():
#     """Latest-revision rows for the selected project (used by the bar charts)."""
#     df, err = load_project_df('merged')
#     if err:
#         return err
#     return json_records(df)


# @app.route('/get_csv_data_monthly_aggregated', methods=['GET'])
# def get_csv_data_monthly_aggregated():
#     df, err = load_project_df('monthly')
#     if err:
#         return err
#     try:
#         df['month'] = pd.to_datetime(df['month'], format='%Y-%m')
#         df = df.sort_values(by='month')

#         numeric_columns = df.select_dtypes(include='number').columns
#         monthly_mean = df.groupby(df['month'].dt.to_period('M'))[numeric_columns].mean().reset_index()
#         monthly_sum = df.groupby(df['month'].dt.to_period('M'))[numeric_columns].sum().reset_index()

#         monthly_mean['month'] = monthly_mean['month'].astype(str)
#         monthly_sum['month'] = monthly_sum['month'].astype(str)

#         monthly_aggregated = monthly_mean.merge(monthly_sum, on='month', suffixes=('_mean', '_sum'))
#         return json_records(monthly_aggregated)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route('/minmax', methods=['GET'])
# def get_minmax():
#     df, err = load_project_df('merged')
#     if err:
#         return err
#     try:
#         minmax_values = {
#             'num_refs': [int(df['num_refs'].min()), int(df['num_refs'].max())],
#             'num_media': [int(df['num_media'].min()), int(df['num_media'].max())],
#             'num_wikilinks': [int(df['num_wikilinks'].min()), int(df['num_wikilinks'].max())],
#             'num_categories': [int(df['num_categories'].min()), int(df['num_categories'].max())],
#             'num_headings': [int(df['num_headings'].min()), int(df['num_headings'].max())],
#             'page_length': [int(df['page_length'].min()), int(df['page_length'].max())],
#             'pred_qual': [float(df['pred_qual'].min()), float(df['pred_qual'].max())],
#         }
#         return jsonify(minmax_values)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route('/filter', methods=['POST'])
# def filter_data():
#     df, err = load_project_df('merged')
#     if err:
#         return err
#     try:
#         filters = request.get_json(silent=True) or {}

#         filtered_data = df[
#             (df['num_refs'] >= filters.get('num_refs_min', df['num_refs'].min())) &
#             (df['num_refs'] <= filters.get('num_refs_max', df['num_refs'].max())) &
#             (df['num_media'] >= filters.get('num_media_min', df['num_media'].min())) &
#             (df['num_media'] <= filters.get('num_media_max', df['num_media'].max())) &
#             (df['num_wikilinks'] >= filters.get('num_wikilinks_min', df['num_wikilinks'].min())) &
#             (df['num_wikilinks'] <= filters.get('num_wikilinks_max', df['num_wikilinks'].max())) &
#             (df['num_categories'] >= filters.get('num_categories_min', df['num_categories'].min())) &
#             (df['num_categories'] <= filters.get('num_categories_max', df['num_categories'].max())) &
#             (df['num_headings'] >= filters.get('num_headings_min', df['num_headings'].min())) &
#             (df['num_headings'] <= filters.get('num_headings_max', df['num_headings'].max())) &
#             (df['page_length'] >= filters.get('page_length_min', df['page_length'].min())) &
#             (df['page_length'] <= filters.get('page_length_max', df['page_length'].max())) &
#             (df['pred_qual'] >= filters.get('pred_qual_min', df['pred_qual'].min())) &
#             (df['pred_qual'] <= filters.get('pred_qual_max', df['pred_qual'].max()))
#         ]

#         # Treat a "All" selection (or empty) as "no filter on this column".
#         quality = [q for q in filters.get('quality_class', []) if q and q != 'All']
#         if quality:
#             filtered_data = filtered_data[filtered_data['quality_class'].isin(quality)]

#         importance = [i for i in filters.get('importance_class', []) if i and i != 'All']
#         if importance:
#             filtered_data = filtered_data[filtered_data['importance_class'].isin(importance)]

#         return Response(filtered_data.to_json(orient='records'), mimetype='application/json')
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route('/get_csv_data_monthly_Latest', methods=['GET'])
# def get_csv_data_monthly_Latest():
#     df, err = load_project_df('monthly')
#     if err:
#         return err
#     return json_records(df)


# @app.route('/get_article_data', methods=['GET'])
# def get_article_data():
#     df, err = load_project_df('monthly')
#     if err:
#         return err
#     try:
#         article_id = request.args.get('page_id')
#         if not article_id:
#             return jsonify({'error': 'No article ID provided'}), 400
#         if 'page_id' not in df.columns:
#             return jsonify({'error': 'page_id column not found'}), 400

#         article_data = df[df['page_id'] == int(article_id)]
#         if article_data.empty:
#             return jsonify({'error': 'Article not found'}), 404
#         return json_records(article_data)
#     except ValueError:
#         return jsonify({'error': 'page_id must be an integer'}), 400
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route('/get_correlation', methods=['GET'])
# def get_correlation():
#     """Correlation matrix of the numeric features for the selected project."""
#     df, err = load_project_df('merged')
#     if err:
#         return err
#     try:
#         present = [c for c in FEATURE_COLUMNS if c in df.columns]
#         corr = df[present].corr().fillna(0)
#         return jsonify(corr.to_dict())
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route('/download_csv', methods=['POST'])
# def download_csv_endpoint():
#     """Return a CSV of the selected articles (by page_title) for download."""
#     df, err = load_project_df('merged')
#     if err:
#         return err
#     try:
#         titles = request.get_json(silent=True) or []
#         if not isinstance(titles, list):
#             return jsonify({'error': 'Expected a JSON list of page titles'}), 400

#         subset = df[df['page_title'].isin(titles)] if titles else df.iloc[0:0]
#         csv_text = subset.to_csv(index=False)
#         return Response(
#             csv_text,
#             mimetype='text/csv',
#             headers={'Content-Disposition': 'attachment; filename=selected_articles.csv'},
#         )
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route('/get_pageviews', methods=['GET'])
# def get_pageviews():
#     title = request.args.get('title')
#     start = request.args.get('start')
#     end = request.args.get('end')

#     if not title or not start or not end:
#         return jsonify({'error': 'Missing required parameters'}), 400

#     # The title is a path segment, so it must be URL-encoded (titles can contain
#     # spaces, slashes, and other reserved characters).
#     encoded_title = quote(title, safe='')
#     url = (
#         'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/'
#         f'en.wikipedia/all-access/user/{encoded_title}/daily/{start}/{end}'
#     )
#     user_agent = 'WikiEvolution (https://wikievol.toolforge.org/)'

#     try:
#         response = requests.get(url, headers={'User-Agent': user_agent}, timeout=30)
#         if response.status_code == 200:
#             return jsonify(response.json())
#         return jsonify({
#             'error': 'Failed to fetch data from Wikimedia API',
#             'status_code': response.status_code,
#         }), response.status_code
#     except requests.exceptions.RequestException as e:
#         return jsonify({
#             'error': 'An error occurred while fetching data from the Wikimedia API',
#             'details': str(e),
#         }), 500


# if __name__ == '__main__':
#     # Debug mode is disabled by default. Enabling Werkzeug's debugger in
#     # production is a remote-code-execution risk, so it must be opted into
#     # explicitly via the FLASK_DEBUG environment variable for local dev.
#     debug = os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
#     app.run(debug=debug)



from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
import os
import re
from urllib.parse import quote

import pandas as pd
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv
load_dotenv()



app = Flask(__name__, static_folder='dist')
CORS(app)

PROJECT_NAME_RE = re.compile(r'^[A-Za-z0-9_-]+$')

DB_CONFIG = {
    "host": os.getenv("MARIADB_HOST", "127.0.0.1"),
    "port": int(os.getenv("MARIADB_PORT", "3306")),
    "user": os.getenv("MARIADB_USER"),
    "password": os.getenv("MARIADB_PASSWORD"),
    "database": os.getenv("MARIADB_DATABASE"),
    "cursorclass": DictCursor,
    "autocommit": True,
}

FEATURE_COLUMNS = [
    "num_refs", "num_media", "num_wikilinks",
    "num_categories", "num_headings", "page_length", "pred_qual",
]


def get_conn():
    return pymysql.connect(**DB_CONFIG)


def normalize_project(project):
    if not project:
        return None
    if project.endswith(".csv"):
        project = project[:-4]
    if not PROJECT_NAME_RE.match(project):
        return None
    return project


def get_project():
    project = request.args.get("project") or request.args.get("project_name")
    if not project and request.is_json:
        body = request.get_json(silent=True) or {}
        project = body.get("project") or body.get("project_name")
    return normalize_project(project)


def query_all(sql, params=()):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def query_one(sql, params=()):
    rows = query_all(sql, params)
    return rows[0] if rows else None


def json_records(rows):
    return Response(pd.DataFrame(rows).to_json(orient="records"), mimetype="application/json")


def get_latest_article_rows(project):
    sql = """
    WITH latest_revision AS (
        SELECT
            r.*,
            ROW_NUMBER() OVER (
                PARTITION BY r.page_id
                ORDER BY r.revision_timestamp DESC, r.revision_id DESC
            ) AS rn
        FROM Revision r
    )
    SELECT
        a.page_id,
        a.page_title,
        a.quality_class,
        a.importance_class,
        a.item_id,
        a.wiki_db,
        lr.revision_id,
        lr.revision_timestamp,
        lr.month,
        lr.page_length,
        lr.num_refs,
        lr.num_wikilinks,
        lr.num_categories,
        lr.num_media,
        lr.num_headings,
        lr.pred_qual
    FROM WikiProject wp
    JOIN Article_Project ap ON ap.project_id = wp.project_id
    JOIN Article a ON a.page_id = ap.page_id
    JOIN latest_revision lr ON lr.page_id = a.page_id AND lr.rn = 1
    WHERE wp.project_name = %s
    ORDER BY a.page_title
    """
    return query_all(sql, (project,))


# Static SPA
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react_app(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


# API
@app.route("/get_wikiprojects", methods=["GET"])
def get_wikiprojects():
    rows = query_all(
        "SELECT project_name FROM WikiProject ORDER BY project_name"
    )
    return jsonify([row["project_name"] for row in rows])


@app.route("/set_selected_wikiproject", methods=["POST"])
def set_selected_wikiproject():
    project = get_project()
    if not project:
        return jsonify({"error": "No valid WikiProject name provided"}), 400

    row = query_one(
        "SELECT 1 FROM WikiProject WHERE project_name = %s",
        (project,),
    )
    if not row:
        return jsonify({"error": f"Unknown WikiProject '{project}'"}), 404

    return jsonify({"success": f"Data ready for {project}."}), 200


@app.route("/get_csv_data", methods=["GET"])
def get_csv_data():
    project = get_project()
    if not project:
        return jsonify({"error": "Missing or invalid WikiProject name"}), 400

    rows = get_latest_article_rows(project)
    return json_records(rows)


@app.route("/get_csv_data_monthly_aggregated", methods=["GET"])
def get_csv_data_monthly_aggregated():
    project = get_project()
    if not project:
        return jsonify({"error": "Missing or invalid WikiProject name"}), 400

    sql = """
    SELECT
        ma.month,
        ma.num_articles,
        ma.mean_page_length,
        ma.sum_page_length,
        ma.mean_refs,
        ma.sum_refs,
        ma.mean_categories,
        ma.sum_categories,
        ma.mean_media,
        ma.sum_media,
        ma.mean_wikilinks,
        ma.sum_wikilinks,
        ma.mean_headings,
        ma.sum_headings,
        ma.mean_pred_qual
    FROM (
        SELECT
            ap.project_id,
            r.month,
            COUNT(DISTINCT r.page_id) AS num_articles,
            AVG(r.page_length) AS mean_page_length,
            SUM(r.page_length) AS sum_page_length,
            AVG(r.num_refs) AS mean_refs,
            SUM(r.num_refs) AS sum_refs,
            AVG(r.num_categories) AS mean_categories,
            SUM(r.num_categories) AS sum_categories,
            AVG(r.num_media) AS mean_media,
            SUM(r.num_media) AS sum_media,
            AVG(r.num_wikilinks) AS mean_wikilinks,
            SUM(r.num_wikilinks) AS sum_wikilinks,
            AVG(r.num_headings) AS mean_headings,
            SUM(r.num_headings) AS sum_headings,
            AVG(r.pred_qual) AS mean_pred_qual
        FROM Revision r
        JOIN Article_Project ap ON ap.page_id = r.page_id
        GROUP BY ap.project_id, r.month
    ) ma
    JOIN WikiProject wp ON wp.project_id = ma.project_id
    WHERE wp.project_name = %s
    ORDER BY ma.month
    c
    
    """
    rows = query_all(sql, (project,))
    return json_records(rows)


@app.route("/minmax", methods=["GET"])
def get_minmax():
    project = get_project()
    if not project:
        return jsonify({"error": "Missing or invalid WikiProject name"}), 400

    sql = """
    WITH latest_revision AS (
        SELECT
            r.*,
            ROW_NUMBER() OVER (
                PARTITION BY r.page_id
                ORDER BY r.revision_timestamp DESC, r.revision_id DESC
            ) AS rn
        FROM Revision r
    )
    SELECT
        MIN(lr.num_refs) AS num_refs_min, MAX(lr.num_refs) AS num_refs_max,
        MIN(lr.num_media) AS num_media_min, MAX(lr.num_media) AS num_media_max,
        MIN(lr.num_wikilinks) AS num_wikilinks_min, MAX(lr.num_wikilinks) AS num_wikilinks_max,
        MIN(lr.num_categories) AS num_categories_min, MAX(lr.num_categories) AS num_categories_max,
        MIN(lr.num_headings) AS num_headings_min, MAX(lr.num_headings) AS num_headings_max,
        MIN(lr.page_length) AS page_length_min, MAX(lr.page_length) AS page_length_max,
        MIN(lr.pred_qual) AS pred_qual_min, MAX(lr.pred_qual) AS pred_qual_max
    FROM WikiProject wp
    JOIN Article_Project ap ON ap.project_id = wp.project_id
    JOIN latest_revision lr ON lr.page_id = ap.page_id AND lr.rn = 1
    WHERE wp.project_name = %s
    """
    row = query_one(sql, (project,))
    if not row:
        return jsonify({"error": f"No data found for '{project}'"}), 404

    return jsonify({
        "num_refs": [row["num_refs_min"], row["num_refs_max"]],
        "num_media": [row["num_media_min"], row["num_media_max"]],
        "num_wikilinks": [row["num_wikilinks_min"], row["num_wikilinks_max"]],
        "num_categories": [row["num_categories_min"], row["num_categories_max"]],
        "num_headings": [row["num_headings_min"], row["num_headings_max"]],
        "page_length": [row["page_length_min"], row["page_length_max"]],
        "pred_qual": [float(row["pred_qual_min"]), float(row["pred_qual_max"])],
    })


@app.route("/filter", methods=["POST"])
def filter_data():
    project = get_project()
    if not project:
        return jsonify({"error": "Missing or invalid WikiProject name"}), 400

    filters = request.get_json(silent=True) or {}

    sql = """
    WITH latest_revision AS (
        SELECT
            r.*,
            ROW_NUMBER() OVER (
                PARTITION BY r.page_id
                ORDER BY r.revision_timestamp DESC, r.revision_id DESC
            ) AS rn
        FROM Revision r
    )
    SELECT
        a.page_id,
        a.page_title,
        a.quality_class,
        a.importance_class,
        lr.revision_id,
        lr.num_refs,
        lr.num_media,
        lr.num_wikilinks,
        lr.num_categories,
        lr.num_headings,
        lr.page_length,
        lr.pred_qual
    FROM WikiProject wp
    JOIN Article_Project ap ON ap.project_id = wp.project_id
    JOIN Article a ON a.page_id = ap.page_id
    JOIN latest_revision lr ON lr.page_id = a.page_id AND lr.rn = 1
    WHERE wp.project_name = %s
      AND lr.num_refs BETWEEN %s AND %s
      AND lr.num_media BETWEEN %s AND %s
      AND lr.num_wikilinks BETWEEN %s AND %s
      AND lr.num_categories BETWEEN %s AND %s
      AND lr.num_headings BETWEEN %s AND %s
      AND lr.page_length BETWEEN %s AND %s
      AND lr.pred_qual BETWEEN %s AND %s
    """

    params = [
        project,
        filters.get("num_refs_min"), filters.get("num_refs_max"),
        filters.get("num_media_min"), filters.get("num_media_max"),
        filters.get("num_wikilinks_min"), filters.get("num_wikilinks_max"),
        filters.get("num_categories_min"), filters.get("num_categories_max"),
        filters.get("num_headings_min"), filters.get("num_headings_max"),
        filters.get("page_length_min"), filters.get("page_length_max"),
        filters.get("pred_qual_min"), filters.get("pred_qual_max"),
    ]

    quality = [q for q in filters.get("quality_class", []) if q and q != "All"]
    importance = [i for i in filters.get("importance_class", []) if i and i != "All"]

    if quality:
        sql += f" AND a.quality_class IN ({','.join(['%s'] * len(quality))})"
        params.extend(quality)

    if importance:
        sql += f" AND a.importance_class IN ({','.join(['%s'] * len(importance))})"
        params.extend(importance)

    sql += " ORDER BY a.page_title"

    rows = query_all(sql, tuple(params))
    return json_records(rows)


@app.route("/get_article_data", methods=["GET"])
def get_article_data():
    project = get_project()
    if not project:
        return jsonify({"error": "Missing or invalid WikiProject name"}), 400

    page_id = request.args.get("page_id")
    if not page_id:
        return jsonify({"error": "No article ID provided"}), 400

    sql = """
    SELECT
        r.page_id,
        r.revision_id,
        r.revision_timestamp,
        r.month,
        r.page_length,
        r.num_refs,
        r.num_wikilinks,
        r.num_categories,
        r.num_media,
        r.num_headings,
        r.pred_qual
    FROM WikiProject wp
    JOIN Article_Project ap ON ap.project_id = wp.project_id
    JOIN Revision r ON r.page_id = ap.page_id
    WHERE wp.project_name = %s
      AND r.page_id = %s
    ORDER BY r.month
    """
    rows = query_all(sql, (project, page_id))
    if not rows:
        return jsonify({"error": "Article not found"}), 404

    return json_records(rows)


@app.route("/get_correlation", methods=["GET"])
def get_correlation():
    project = get_project()
    if not project:
        return jsonify({"error": "Missing or invalid WikiProject name"}), 400

    rows = get_latest_article_rows(project)
    if not rows:
        return jsonify({"error": f"No data found for '{project}'"}), 404

    df = pd.DataFrame(rows)
    present = [c for c in FEATURE_COLUMNS if c in df.columns]
    corr = df[present].corr().fillna(0)
    return jsonify(corr.to_dict())


@app.route("/download_csv", methods=["POST"])
def download_csv_endpoint():
    project = get_project()
    if not project:
        return jsonify({"error": "Missing or invalid WikiProject name"}), 400

    titles = request.get_json(silent=True) or []
    if not isinstance(titles, list):
        return jsonify({"error": "Expected a JSON list of page titles"}), 400

    if not titles:
        return Response(
            "",
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=selected_articles.csv"},
        )

    placeholders = ",".join(["%s"] * len(titles))
    sql = f"""
    WITH latest_revision AS (
        SELECT
            r.*,
            ROW_NUMBER() OVER (
                PARTITION BY r.page_id
                ORDER BY r.revision_timestamp DESC, r.revision_id DESC
            ) AS rn
        FROM Revision r
    )
    SELECT
        a.page_id,
        a.page_title,
        a.quality_class,
        a.importance_class,
        a.item_id,
        a.wiki_db,
        lr.revision_id,
        lr.revision_timestamp,
        lr.month,
        lr.page_length,
        lr.num_refs,
        lr.num_wikilinks,
        lr.num_categories,
        lr.num_media,
        lr.num_headings,
        lr.pred_qual
    FROM WikiProject wp
    JOIN Article_Project ap ON ap.project_id = wp.project_id
    JOIN Article a ON a.page_id = ap.page_id
    JOIN latest_revision lr ON lr.page_id = a.page_id AND lr.rn = 1
    WHERE wp.project_name = %s
      AND a.page_title IN ({placeholders})
    ORDER BY a.page_title
    """
    rows = query_all(sql, tuple([project] + titles))
    csv_text = pd.DataFrame(rows).to_csv(index=False)
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=selected_articles.csv"},
    )


@app.route("/get_pageviews", methods=["GET"])
def get_pageviews():
    title = request.args.get("title")
    start = request.args.get("start")
    end = request.args.get("end")

    if not title or not start or not end:
        return jsonify({"error": "Missing required parameters"}), 400

    encoded_title = quote(title, safe="")
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"en.wikipedia/all-access/user/{encoded_title}/daily/{start}/{end}"
    )
    user_agent = "WikiEvolution (https://wikievol.toolforge.org/)"

    try:
        response = requests.get(url, headers={"User-Agent": user_agent}, timeout=30)
        if response.status_code == 200:
            return jsonify(response.json())
        return jsonify({
            "error": "Failed to fetch data from Wikimedia API",
            "status_code": response.status_code,
        }), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(debug=debug)