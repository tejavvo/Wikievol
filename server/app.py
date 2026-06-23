from flask import Flask, request, jsonify, Response, send_from_directory
import pandas as pd
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
import re
import threading
from urllib.parse import quote

import process_wikiproject_monthly
import process_wikiproject_latest

app = Flask(__name__, static_folder='dist')
CORS(app)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Per-project processed CSVs are cached here so we don't re-download and
# re-process the same WikiProject on every request.
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

DATASET_BASE = "https://analytics.wikimedia.org/published/datasets/outreachy-round-28"

# Wikimedia infrastructure rejects requests without a descriptive User-Agent
# (HTTP 403). See https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = "WikiEvolution/1.0 (https://wikievol.toolforge.org/; toolforge-wikievol)"

# WikiProject names are used to build filenames and URLs, so they must be
# restricted to a safe character set (prevents path traversal / SSRF).
PROJECT_NAME_RE = re.compile(r'^[A-Za-z0-9_-]+$')

# Numeric feature columns shared by several endpoints.
FEATURE_COLUMNS = [
    'num_refs', 'num_media', 'num_wikilinks', 'num_categories',
    'num_headings', 'page_length', 'pred_qual',
]

# Per-project locks so two concurrent requests don't download/process the same
# project's data simultaneously.
_locks = {}
_locks_guard = threading.Lock()


def _project_lock(project):
    with _locks_guard:
        if project not in _locks:
            _locks[project] = threading.Lock()
        return _locks[project]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_project(project):
    """Strip a trailing '.csv' and validate the project name. Returns the clean
    name, or None if it is missing/invalid."""
    if not project:
        return None
    if project.endswith('.csv'):
        project = project[:-4]
    if not PROJECT_NAME_RE.match(project):
        return None
    return project


def get_project():
    """Read the project name from the request (query string or JSON body)."""
    project = request.args.get('project') or request.args.get('project_name')
    if not project and request.is_json:
        body = request.get_json(silent=True) or {}
        project = body.get('project') or body.get('project_name')
    return normalize_project(project)


def merged_path(project):
    return os.path.join(DATA_DIR, f"{project}_merged.csv")


def monthly_path(project):
    return os.path.join(DATA_DIR, f"{project}_latest_monthly.csv")


def ensure_project_data(project):
    """Make sure the merged + monthly CSVs for ``project`` exist, building them
    once if necessary. Returns (ok: bool, error: str | None)."""
    if os.path.exists(merged_path(project)) and os.path.exists(monthly_path(project)):
        return True, None

    lock = _project_lock(project)
    with lock:
        # Re-check inside the lock in case another thread just built it.
        if os.path.exists(merged_path(project)) and os.path.exists(monthly_path(project)):
            return True, None
        try:
            process_wikiproject_latest.main(project, out_dir=DATA_DIR)
            process_wikiproject_monthly.main(project, out_dir=DATA_DIR)
        except Exception as e:
            return False, str(e)

    if os.path.exists(merged_path(project)) and os.path.exists(monthly_path(project)):
        return True, None
    return False, "Failed to build data for this WikiProject."


def load_project_df(kind):
    """Resolve the project from the request, ensure its data exists, and load
    the requested dataframe. Returns (df, error_response). On success
    error_response is None; on failure df is None and error_response is a ready
    Flask (response, status) tuple."""
    project = get_project()
    if not project:
        return None, (jsonify({"error": "Missing or invalid WikiProject name"}), 400)

    ok, err = ensure_project_data(project)
    if not ok:
        return None, (jsonify({"error": err}), 502)

    path = merged_path(project) if kind == 'merged' else monthly_path(project)
    if not os.path.exists(path):
        return None, (jsonify({"error": f"No {kind} data for '{project}'"}), 404)
    return pd.read_csv(path), None


def json_records(df):
    """Serialize a dataframe to a JSON array response. Uses pandas' ``to_json``
    (not ``jsonify``) so that NaN values become valid JSON ``null`` instead of
    the bare ``NaN`` token, which browsers cannot parse."""
    return Response(df.to_json(orient='records'), mimetype='application/json')


# ---------------------------------------------------------------------------
# Static SPA
# ---------------------------------------------------------------------------

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.route('/get_wikiprojects', methods=['GET'])
def get_wikiprojects():
    """List the WikiProjects available in the published dataset."""
    url = f'{DATASET_BASE}/revisions/'
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch WikiProjects: {e}'}), 502

    soup = BeautifulSoup(response.text, 'html.parser')
    names = [
        a.get('href')[:-4]
        for a in soup.find_all('a')
        if a.get('href') and a.get('href').endswith('.csv')
    ]
    return jsonify(names)


@app.route('/set_selected_wikiproject', methods=['POST'])
def set_selected_wikiproject():
    """Prepare (download + process) a project's data. Idempotent and cached;
    no longer stores any global server-side state."""
    project = get_project()
    if not project:
        return jsonify({'error': 'No valid WikiProject name provided'}), 400

    ok, err = ensure_project_data(project)
    if not ok:
        return jsonify({'error': f'Failed to process data: {err}'}), 502
    return jsonify({'success': f'Data ready for {project}.'}), 200


@app.route('/get_csv_data', methods=['GET'])
def get_csv_data():
    """Latest-revision rows for the selected project (used by the bar charts)."""
    df, err = load_project_df('merged')
    if err:
        return err
    return json_records(df)


@app.route('/get_csv_data_monthly_aggregated', methods=['GET'])
def get_csv_data_monthly_aggregated():
    df, err = load_project_df('monthly')
    if err:
        return err
    try:
        df['month'] = pd.to_datetime(df['month'], format='%Y-%m')
        df = df.sort_values(by='month')

        numeric_columns = df.select_dtypes(include='number').columns
        monthly_mean = df.groupby(df['month'].dt.to_period('M'))[numeric_columns].mean().reset_index()
        monthly_sum = df.groupby(df['month'].dt.to_period('M'))[numeric_columns].sum().reset_index()

        monthly_mean['month'] = monthly_mean['month'].astype(str)
        monthly_sum['month'] = monthly_sum['month'].astype(str)

        monthly_aggregated = monthly_mean.merge(monthly_sum, on='month', suffixes=('_mean', '_sum'))
        return json_records(monthly_aggregated)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/minmax', methods=['GET'])
def get_minmax():
    df, err = load_project_df('merged')
    if err:
        return err
    try:
        minmax_values = {
            'num_refs': [int(df['num_refs'].min()), int(df['num_refs'].max())],
            'num_media': [int(df['num_media'].min()), int(df['num_media'].max())],
            'num_wikilinks': [int(df['num_wikilinks'].min()), int(df['num_wikilinks'].max())],
            'num_categories': [int(df['num_categories'].min()), int(df['num_categories'].max())],
            'num_headings': [int(df['num_headings'].min()), int(df['num_headings'].max())],
            'page_length': [int(df['page_length'].min()), int(df['page_length'].max())],
            'pred_qual': [float(df['pred_qual'].min()), float(df['pred_qual'].max())],
        }
        return jsonify(minmax_values)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/filter', methods=['POST'])
def filter_data():
    df, err = load_project_df('merged')
    if err:
        return err
    try:
        filters = request.get_json(silent=True) or {}

        filtered_data = df[
            (df['num_refs'] >= filters.get('num_refs_min', df['num_refs'].min())) &
            (df['num_refs'] <= filters.get('num_refs_max', df['num_refs'].max())) &
            (df['num_media'] >= filters.get('num_media_min', df['num_media'].min())) &
            (df['num_media'] <= filters.get('num_media_max', df['num_media'].max())) &
            (df['num_wikilinks'] >= filters.get('num_wikilinks_min', df['num_wikilinks'].min())) &
            (df['num_wikilinks'] <= filters.get('num_wikilinks_max', df['num_wikilinks'].max())) &
            (df['num_categories'] >= filters.get('num_categories_min', df['num_categories'].min())) &
            (df['num_categories'] <= filters.get('num_categories_max', df['num_categories'].max())) &
            (df['num_headings'] >= filters.get('num_headings_min', df['num_headings'].min())) &
            (df['num_headings'] <= filters.get('num_headings_max', df['num_headings'].max())) &
            (df['page_length'] >= filters.get('page_length_min', df['page_length'].min())) &
            (df['page_length'] <= filters.get('page_length_max', df['page_length'].max())) &
            (df['pred_qual'] >= filters.get('pred_qual_min', df['pred_qual'].min())) &
            (df['pred_qual'] <= filters.get('pred_qual_max', df['pred_qual'].max()))
        ]

        # Treat a "All" selection (or empty) as "no filter on this column".
        quality = [q for q in filters.get('quality_class', []) if q and q != 'All']
        if quality:
            filtered_data = filtered_data[filtered_data['quality_class'].isin(quality)]

        importance = [i for i in filters.get('importance_class', []) if i and i != 'All']
        if importance:
            filtered_data = filtered_data[filtered_data['importance_class'].isin(importance)]

        return Response(filtered_data.to_json(orient='records'), mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_csv_data_monthly_Latest', methods=['GET'])
def get_csv_data_monthly_Latest():
    df, err = load_project_df('monthly')
    if err:
        return err
    return json_records(df)


@app.route('/get_article_data', methods=['GET'])
def get_article_data():
    df, err = load_project_df('monthly')
    if err:
        return err
    try:
        article_id = request.args.get('page_id')
        if not article_id:
            return jsonify({'error': 'No article ID provided'}), 400
        if 'page_id' not in df.columns:
            return jsonify({'error': 'page_id column not found'}), 400

        article_data = df[df['page_id'] == int(article_id)]
        if article_data.empty:
            return jsonify({'error': 'Article not found'}), 404
        return json_records(article_data)
    except ValueError:
        return jsonify({'error': 'page_id must be an integer'}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_correlation', methods=['GET'])
def get_correlation():
    """Correlation matrix of the numeric features for the selected project."""
    df, err = load_project_df('merged')
    if err:
        return err
    try:
        present = [c for c in FEATURE_COLUMNS if c in df.columns]
        corr = df[present].corr().fillna(0)
        return jsonify(corr.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/download_csv', methods=['POST'])
def download_csv_endpoint():
    """Return a CSV of the selected articles (by page_title) for download."""
    df, err = load_project_df('merged')
    if err:
        return err
    try:
        titles = request.get_json(silent=True) or []
        if not isinstance(titles, list):
            return jsonify({'error': 'Expected a JSON list of page titles'}), 400

        subset = df[df['page_title'].isin(titles)] if titles else df.iloc[0:0]
        csv_text = subset.to_csv(index=False)
        return Response(
            csv_text,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=selected_articles.csv'},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_pageviews', methods=['GET'])
def get_pageviews():
    title = request.args.get('title')
    start = request.args.get('start')
    end = request.args.get('end')

    if not title or not start or not end:
        return jsonify({'error': 'Missing required parameters'}), 400

    # The title is a path segment, so it must be URL-encoded (titles can contain
    # spaces, slashes, and other reserved characters).
    encoded_title = quote(title, safe='')
    url = (
        'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/'
        f'en.wikipedia/all-access/user/{encoded_title}/daily/{start}/{end}'
    )
    user_agent = 'WikiEvolution (https://wikievol.toolforge.org/)'

    try:
        response = requests.get(url, headers={'User-Agent': user_agent}, timeout=30)
        if response.status_code == 200:
            return jsonify(response.json())
        return jsonify({
            'error': 'Failed to fetch data from Wikimedia API',
            'status_code': response.status_code,
        }), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': 'An error occurred while fetching data from the Wikimedia API',
            'details': str(e),
        }), 500


if __name__ == '__main__':
    # Debug mode is disabled by default. Enabling Werkzeug's debugger in
    # production is a remote-code-execution risk, so it must be opted into
    # explicitly via the FLASK_DEBUG environment variable for local dev.
    debug = os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(debug=debug)
