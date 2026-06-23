# WikiEvolution

WikiEvolution is an interactive web application that analyses and visualises the
evolution of Wikipedia articles within a WikiProject over time (quality,
importance, references, media, page length, and other structural metrics).

The frontend is built with **React + Vite**; the backend is a **Flask** API.
The tool is deployed on [Wikimedia Toolforge](https://wikievol.toolforge.org/).

## Project structure

```
client/   React + Vite single-page app (the dashboard UI)
server/   Flask API + data-processing scripts
  app.py                          API routes, also serves the built SPA
  process_wikiproject_latest.py   builds the "latest revision" dataset
  process_wikiproject_monthly.py  builds the monthly time-series dataset
  ssh/                            (WIP) MySQL ingestion over an SSH tunnel
```

## Prerequisites

- Node.js and npm (frontend)
- Python 3 and pip (backend)

## Getting started

### 1. Clone

```bash
git clone https://gitlab.wikimedia.org/repos/research/WikiEvolution.git
cd WikiEvolution
```

### 2. Backend

```bash
cd server
python -m venv WikiEnv && source WikiEnv/bin/activate
pip install -r requirements.txt
python app.py            # runs on http://localhost:5000
```

Debug mode is **off by default**. For local development you can enable it with:

```bash
FLASK_DEBUG=true python app.py
```

### 3. Frontend

```bash
cd client
npm install
cp .env.example .env     # point the app at your local backend
npm run dev              # runs on http://localhost:5173
```

The backend URL is configured via `VITE_API_BASE_URL` (see `client/.env.example`).
In production it is left empty, because Flask serves the built SPA from the same
origin as the API.

## Data source

The dashboard reads published datasets from
`https://analytics.wikimedia.org/published/datasets/outreachy-round-28/`.
Replacing this static snapshot with a refreshable database-backed pipeline is
tracked as ongoing work (see the project's Phabricator tasks).
