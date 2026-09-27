# Portfolio Project Reviewer — Security Overview

This document describes the security model of the Portfolio Project Reviewer application, which performs static analysis of GitHub repositories. No image processing, EXIF data, or file uploads are involved.

## 1. Repository Ingestion & Input Validation

- **URL Allowlist**: The `/api/analyze` endpoint accepts only GitHub HTTPS URLs (`https://github.com/owner/repo`) or well-known internal prefixes (`sample:`, `local:`). All other inputs are rejected before any network activity occurs.
- **Archive Size Limits**: Remote repositories are rejected if the compressed archive exceeds **25 MB** to prevent disk exhaustion.
- **File Count & Size Caps**: At most **500 files** per repository are analysed; individual files larger than **500 KB** are skipped.
- **Path Traversal Prevention**: During ZIP/tarball extraction every member path is validated. Any entry containing `..` or an absolute path is rejected, and extraction is aborted.
- **Binary File Filtering**: Non-text file types (`.exe`, `.pyc`, `.jar`, `.png`, `.mp4`, etc.) are skipped entirely and never loaded into memory.
- **Ignored Directories**: `.git`, `node_modules`, `__pycache__`, `.venv`, `.pytest_cache`, and other build/vendor directories are excluded from analysis.

## 2. Code Execution Prevention

- **No untrusted code is executed.** Repository source files are parsed as abstract syntax trees (Python AST) or scanned with regex patterns. Test scripts, build scripts, and any other executables present in the repository are never invoked.
- All analysis is entirely static; dynamic runtime behaviour cannot be observed.

## 3. Secret Redaction

- The `SecurityAnalyzer` module scans repository files for high-entropy credential patterns before any content is stored or transmitted to the AI layer.
- Detected secrets are **automatically masked** in the stored `evidence` field. For example: `sk-proj-****REDACTED****` (only the first and last 4 characters are preserved for identification).
- Patterns detected and redacted include:
  - AWS Access Key IDs (`AKIA[0-9A-Z]{16}`)
  - OpenAI / Anthropic secret keys (`sk-[a-zA-Z0-9_-]{20,}`)
  - GitHub Personal Access Tokens (`ghp_[a-zA-Z0-9]{36}`)
  - Google API Keys (`AIza[0-9A-Za-z-_]{35}`)
  - PEM private key blocks (`-----BEGIN ... PRIVATE KEY-----`)

## 4. Ephemeral Workspace Sandboxing

- Every remote repository is downloaded into a unique temporary directory under `data/scratch/` with a randomised prefix.
- The temporary directory is **always deleted** by a `finally` block in `backend/app/services/repo_fetcher.py` regardless of whether the analysis succeeded or failed.
- No repository content persists on disk after an analysis run completes.

## 5. API Security & CORS

- **CORS Configuration**: The FastAPI backend restricts allowed origins to explicit local development ports:
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
- The wildcard origin (`*`) is **not** permitted. Before deploying to a public host, update `CORS_ORIGINS` in `.env` or `backend/app/core/config.py` to the actual production domain.
- **Error Handling**: Unhandled exceptions in background analysis tasks are caught, logged server-side, and surfaced to the client only as a clean human-readable message in the `error_message` field. Raw tracebacks are never sent to the browser.

## 6. Secrets Management

- `GEMINI_API_KEY` and all other sensitive configuration values are read from a `.env` file via Pydantic `BaseSettings` — never hardcoded.
- The `.gitignore` file is pre-configured to exclude `.env`, `.env.*`, the SQLite database file, and the `data/scratch/` workspace directory.

## 7. Known Gaps (Planned)

- **No authentication**: All API endpoints are currently public. User authentication and analysis isolation are planned for a future phase.
- **No rate limiting**: The API does not currently limit the number of analyses a client can trigger. Rate limiting is planned for the same future phase.
- **SQLite single-node**: The database is a local SQLite file. It is not suitable for a concurrent multi-user production deployment without migration to a client–server database.
