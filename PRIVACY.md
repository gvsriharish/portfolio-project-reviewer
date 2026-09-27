# Portfolio Project Reviewer — Privacy & Data Handling

This document describes how the Portfolio Project Reviewer application handles data. The application analyses source-code repositories — it does not process photographs, personal images, EXIF data, or any biometric information.

## 1. What Data Is Collected

When you submit a GitHub repository URL for analysis, the application:

- **Downloads the repository** into a temporary directory on the server (`data/scratch/`).
- **Reads source files** from the repository (text files only; binary and media files are skipped).
- **Stores analysis results** in a local SQLite database (`data/portfolio_reviewer.db`), including:
  - The repository URL, owner, and name
  - Detected languages and frameworks
  - Analysis findings (category, severity, file path, line number, evidence)
  - Scores per category and overall health score
  - AI-generated recommendations, interview questions, and project narrative (when AI is enabled)
  - Timestamps and analysis duration

The application does **not** collect personal information such as names, email addresses, passwords, or payment details.

## 2. Repository Content Handling

- **Ephemeral download**: The repository is extracted into `data/scratch/` only for the duration of the analysis. The temporary directory is permanently deleted immediately after the analysis completes or fails, regardless of outcome.
- **Secret redaction**: Before any content is stored in the database or forwarded to the AI layer, the `SecurityAnalyzer` automatically masks detected credentials (API keys, tokens, private keys) with `****REDACTED****`. The original secret value is never written to the database.
- **No persistence of raw files**: Raw repository source code is not saved to disk beyond the ephemeral workspace. Only derived analysis artefacts (findings, scores, narratives) are stored.

## 3. External AI Processing

- When the **"Use AI"** option is enabled, a subset of analysis findings (category, severity, title, file path, and redacted evidence) is sent to the **Google Gemini API** (`gemini-2.5-flash`) for reasoning enhancement.
- Raw repository source code is **not** sent to Gemini — only structured finding metadata is forwarded.
- The Gemini API key is stored server-side in a `.env` file and is never exposed to the frontend browser or included in API responses.
- If no Gemini API key is configured, all AI features operate entirely offline using a deterministic fallback generator. No external network calls are made in this mode.

## 4. Local Storage

- The SQLite database at `data/portfolio_reviewer.db` is stored locally on the server running the application. It is not replicated to any remote service.
- Analysis records are retained indefinitely until manually deleted. There is currently no automatic expiry or bulk-deletion endpoint.
- The `uploads/` directory is present for legacy reasons and is not used by this application.

## 5. No Personal Tracking

- The application does not use cookies, sessions, or fingerprinting to track individual users.
- There is currently no user account system. All analyses are identified by a random UUID and are accessible to anyone who knows that UUID.
- No analytics, telemetry, or third-party tracking scripts are included.

## 6. Data Deletion

To remove analysis data, delete the SQLite file at `data/portfolio_reviewer.db`. The application will recreate an empty database on next startup.

To remove temporary workspace residue (e.g., after an interrupted analysis), delete the contents of `data/scratch/`.
