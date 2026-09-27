# Portfolio Project Reviewer

**Portfolio Project Reviewer** is an AI-assisted engineering evidence platform for students and developers. It analyzes a GitHub repository, turns observable project artifacts into evidence-backed findings and claims, and helps the developer improve and defend their project — without inventing evidence.

---

## Why this is different

Most project graders produce opaque scores. Portfolio Project Reviewer produces **transparent, evidence-linked findings**: deductions link to the deterministic finding and its available evidence (including file and line details when applicable). The AI layer explains and prioritises findings but cannot override deterministic measurements.

---

## Features

| Feature | Description |
|---|---|
| **Repository Analysis** | Static analysis covering code quality, security, documentation, testing, architecture, dependencies and git hygiene |
| **Evidence Graph** | Every finding is linked to structured evidence (file, line, pattern) |
| **Claim Auditor** | Verifies README claims against repository reality |
| **Trust Report** | Engineering confidence scoring with transparent calculation |
| **Before / After Comparison** | Deterministic diff of two analysis runs showing resolved and new findings |
| **Proof of Improvement** | Evidence-backed verification that a fix actually resolved a finding |
| **Portfolio & Proof Workspace** | Engineering Portfolio, Monitor timeline, Interview Prep, and Proof Passport |
| **AI Enhancements** | Grounded recommendations and interview questions from Google Gemini (optional) |
| **Sample Projects** | Built-in benchmark projects for instant demonstration |

---

## Architecture

```
┌─────────────────────────────────────────────┐
│            React + TypeScript + Vite          │
│  (Findings Explorer, Health Dashboard,        │
│   Claim Auditor, Evidence Explorer,           │
│   Trust Report, Phase 6–9 Workspace)          │
└─────────────────────┬───────────────────────┘
                      │ HTTP REST (JSON)
                      ▼
┌─────────────────────────────────────────────┐
│                 FastAPI                       │
│  /api/analyze   /api/analysis/{id}            │
│  /api/evidence  /api/claims                   │
│  /api/portfolio /api/passport                 │
└──────────┬──────────────┬────────────────────┘
           │              │
           ▼              ▼
┌──────────────┐  ┌───────────────────────────┐
│ Repo Fetcher │  │    SQLite (SQLAlchemy)     │
│ (GitHub ZIP  │  │  AnalysisRun, Finding,    │
│  or sample)  │  │  FindingEvidence, Claim,  │
└──────┬───────┘  │  Recommendation, Phase6–9 │
       │          └───────────────────────────┘
       ▼
┌──────────────────────────────────────────────┐
│             Analysis Orchestrator             │
│  Language Detector | Architecture Analyzer    │
│  Code Quality      | Security Analyzer        │
│  Documentation     | Testing Analyzer         │
│  Dependency        | Git Hygiene Analyzer     │
│  Scoring Engine    | Claim Auditor            │
└──────────────────────┬───────────────────────┘
                       │ (optional)
                       ▼
               Google Gemini AI
               (grounded fallback
                if key absent)
```

---

## Installation

### Prerequisites

- Python 3.11+ (tested on 3.13)
- Node.js 18+

### 1. Clone and set up environment

```bash
git clone https://github.com/your-org/portfolio-project-reviewer
cd portfolio-project-reviewer

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env — add GEMINI_API_KEY if you want AI-enhanced analysis.
# AI is optional; a grounded deterministic fallback is used if key is absent.
```

### 3. Start the backend

```bash
uvicorn backend.app.main:app --reload
```

API documentation is available at:
- `http://127.0.0.1:8000/api/docs` (Swagger UI)
- `http://127.0.0.1:8000/api/redoc`

### 4. Start the frontend

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Environment variables

Copy `.env.example` to `.env` and fill in the values you need.

| Variable | Default | Description |
|---|---|---|
| `PROJECT_NAME` | `Portfolio Project Reviewer` | Display name |
| `API_PREFIX` | `/api` | API route prefix |
| `HOST` | `127.0.0.1` | Bind host |
| `PORT` | `8000` | Bind port |
| `DATABASE_URL` | `sqlite:///./data/portfolio_reviewer.db` | SQLAlchemy DB URL |
| `GEMINI_API_KEY` | _(empty)_ | Google Gemini API key — optional |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `MAX_REPO_SIZE_MB` | `25` | Maximum repository download size |
| `MAX_REPO_FILES` | `500` | Maximum files scanned |
| `MAX_FILE_SIZE_KB` | `500` | Maximum individual file size |
| `CORS_ORIGINS` | Local development origins | JSON array of allowed browser origins; configure the deployed frontend origin in production |
| `VITE_API_BASE` | `/api` | Frontend build setting in `frontend/.env`; complete API prefix including `/api` |

**Never commit your `.env` file.** Provide only `.env.example`.

The frontend also uses `frontend/.env.example`. `VITE_API_BASE` is the complete API prefix (including `/api`); its default `/api` works with the Vite development proxy and with a same-origin production reverse proxy.

---

## Running tests

### Backend (Python)

```bash
# From repository root
python -m pytest backend/tests -q
```

Expected: all tests pass. The suite covers:
- All 8 analyzers
- Scoring engine
- Claim auditor
- Finding comparison and improvement verification
- Trust report
- Evidence graph builder
- Phase 6–9 portfolio, monitor, interview, passport
- **Security regression tests** (SSRF, path traversal, injection, secrets masking)
- API endpoint validation

### Python compilation check

```bash
python -m compileall backend/ -q
```

### Frontend (TypeScript)

```bash
cd frontend
npm ci
npx tsc -b           # TypeScript typecheck — must produce no errors
npm run lint         # oxlint — must produce 0 errors (warnings are informational)
npm test             # API base configuration regression tests
npm run build        # Production build
```

---

## Production build

```bash
cd frontend
npm ci
npm run build
```

Output in `frontend/dist/`. Serve with any static file server (nginx, Caddy, `vite preview`).

For the backend:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## Deployment notes

- The backend uses **SQLite** by default — single node only. For multi-worker deployment, configure `DATABASE_URL` to use PostgreSQL.
- The frontend `VITE_API_BASE` build variable controls the complete backend API prefix (defaults to same-origin `/api`). Configure a reverse proxy for `/api` in production or set this variable to the deployed API prefix.
- CORS origins are explicitly configured in `backend/app/core/config.py` and can be overridden with a JSON `CORS_ORIGINS` environment variable. Set the exact deployed frontend origin.
- See `PRIVACY.md` and `SECURITY.md` for privacy and security policies.

---

## Limitations

- Only **public** GitHub repositories are supported. Private repositories require a GitHub token (not currently implemented).
- Gemini-generated explanations and recommendations require a `GEMINI_API_KEY`. Without one, a deterministic fallback uses detected findings and labels; it does not infer runtime behavior or deployment settings.
- SQLite is used by default. High concurrency or multiple workers may hit write contention.
- `MAX_REPO_SIZE_MB` (default 25 MB) may exclude large repositories.
- There is no end-to-end analysis deadline or frontend timeout notification. Repository network operations and the Gemini request have individual timeouts; unusually long analysis tasks can remain in progress.
- The Proof Passport is an **application-generated evidence package** — it is not a professional, academic, security, or software-quality certification.
- Analysis scores are deterministic and transparent but should be interpreted as indicators, not absolute rankings.

---

## Project documentation

| File | Contents |
|---|---|
| `docs/architecture.md` | Full system architecture |
| `docs/demo.md` | Demonstration walkthrough |
| `docs/testing.md` | Test architecture and coverage map |
| `docs/verification-report.md` | Previous verification record |
| `docs/final-verification-report.md` | Latest full verification report |
| `docs/security.md` | Security design and threat model |
| `SECURITY.md` | Security disclosure policy |
| `PRIVACY.md` | Privacy policy |

---

## License

See `LICENSE`.


## Recent Improvements

The Portfolio Project Reviewer continues to be improved with better project analysis,
clearer recommendations, and a more user-friendly review experience.

### Project Focus

The application helps developers evaluate their GitHub projects by analyzing
project structure, documentation, code quality, and portfolio readiness.