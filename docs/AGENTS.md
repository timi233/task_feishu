# Repository Guidelines

## Project Structure & Module Organization
FastAPI backend lives under `backend/`; core entrypoint is `main.py` with Feishu ingestion helpers (`read_feishu_data.py`, `process_feishu_data.py`) and storage utilities (`task_db.py`, `task_filter.py`). SQLite data persists in `data/tasks.db`, mounted when running Docker. The React SPA resides in `frontend/src/`, while `frontend/index.html` serves as the static fallback. Container and orchestration manifests (`Dockerfile`, `docker-compose.yml`) live at the repository root; shared configuration samples belong alongside them.

## Build, Test, and Development Commands
From `backend/`, install Python deps with `pip install -r requirements.txt`, then run `uvicorn main:app --reload --host 0.0.0.0 --port 8000` for local API development. Refresh Feishu-derived tasks via `python sync_feishu_to_db.py` before validating filters. In `frontend/`, execute `npm install` once, `npm start` for hot reload, and `npm run build` to produce optimized assets. Orchestrate the full stack with `docker-compose up --build` at the repo root after exporting Feishu credentials.

## Coding Style & Naming Conventions
Follow PEP 8, four-space indentation, and descriptive snake_case functions in Python modules. Consolidate Feishu constants near the top of `backend/main.py` and rely on shared helpers instead of duplicating request logic. React components should remain functional, camel-case file names (`taskList.js`), and respect the default ESLint/Prettier configuration from `react-scripts`. Store runtime config behind `REACT_APP_*` environment variables.

## Testing Guidelines
Backend smoke tests live in `backend/test_*.py`; run `pytest backend` for the suite or target scripts individually (e.g., `python test_filter.py`). Rebuild the SQLite cache before tests that exercise live queries. Frontend tests run through `npm test`; add assertions rather than console logging, and name specs `*.test.js` beside their components.

## Commit & Pull Request Guidelines
Use imperative Conventional Commit messages such as `feat: add weekly task filter`, scoped to a single logical change. Pull requests should summarize the change set, reference related Feishu docs or issues, list local commands executed, and include screenshots or cURL output for API-facing updates. Highlight configuration or schema changes explicitly and confirm secrets remain in environment variables.

## Security & Configuration Tips
Never hard-code Feishu secrets; rely on environment variables or untracked `.env.local` files. Treat `data/tasks.db` as sensitive operational data and keep it out of public artifacts. Review Docker and compose settings before sharing to ensure no credentials leak through bind mounts.
