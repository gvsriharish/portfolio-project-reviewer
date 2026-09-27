# Portfolio Project Reviewer — Demo Evidence

## Application

Run the backend from the repository root:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Run the frontend in a second terminal:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open <http://127.0.0.1:5173/>. The built-in sample projects work without external credentials. Gemini is optional; this verification used the configured deterministic fallback because no Gemini key was present.

## Demo Flow

The browser workflow was completed using the built-in **Legacy Student Portfolio (Unimproved)** benchmark (`sample:bad_project`). The app accepted the sample, showed the analysis progress state, completed the deterministic review, and rendered the dashboard with a score of 58/100 and 20 findings. Findings included redacted synthetic credential patterns, code quality, documentation, security and testing observations. The 58/100 score is the application's result for this sample and its documented scoring rubric.

The Findings view was opened and verified to show evidence, rationale, recommended fixes, and verification methods. The dashboard and findings view were checked at desktop and 390 px mobile viewport widths; no horizontal page overflow was observed at the mobile width.

## Screenshots

No screenshot files were saved in this package. The available in-app browser capture interface returned viewable screenshots but did not provide a way to write them into the repository. The environment exposed no desktop capture app or browser recording control. No screenshot files are listed as completed evidence.

## Demo Video

No video was recorded. This environment did not expose a screen recorder or browser video recording/export capability. Duration: not applicable.

## Main Features Demonstrated

- Built-in benchmark project selection
- Repository analysis and progress states
- Overall health score and category breakdown
- Evidence-backed code quality and security findings
- Redaction of synthetic credential patterns in evidence
- Documentation, testing, architecture, dependencies, and Git hygiene categories
- Recommended fixes and verification methods on findings
- Responsive findings layout without horizontal overflow at 390 px

## Test Status

- **Frontend:** PASS — Vite production build and TypeScript build completed; 2 frontend API-base tests passed.
- **Backend:** PASS — 163 tests passed, 1 skipped. The skip is platform-dependent. One Starlette/httpx deprecation warning remains.
- **API:** PASS — frontend loaded the sample list, submitted the sample analysis, and polled the analysis endpoint to completion.
- **AI integration:** Gemini was not exercised because `GEMINI_API_KEY` was not configured. The app's deterministic fallback completed the analysis flow.
- **End-to-end workflow:** PASS — sample input through dashboard and findings was verified in the browser.
- **Build:** PASS — `npm run build` completed successfully.

## Remaining Evidence Gap

The requested screenshot set and 2–3 minute MP4 are not included. They require a capture/recording tool with local file export; none was available through this session's browser or desktop capture interfaces. The app run and results above are verified independently of those missing media files.
