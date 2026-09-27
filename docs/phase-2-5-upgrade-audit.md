# Phase 2–5 Upgrade Audit — Portfolio Project Reviewer

> Inspection stage artifact. No production code was modified during this audit.

## 1. Current Architecture

```
React 19 + Vite + Tailwind (frontend/)
    └── src/services/api.ts  →  http://127.0.0.1:8000/api
FastAPI backend (backend/app)
    ├── main.py                  – app factory, router registration, create_all
    ├── core/config.py          – pydantic-settings (limits, CORS, Gemini key)
    ├── database/session.py     – SQLAlchemy engine (sqlite), get_db
    ├── models/findings.py      – AnalysisRun, Finding, Recommendation,
    │                             InterviewQuestion, ProjectExplanation
    ├── models/evidence.py      – FindingEvidence (Phase 1 evidence store)
    ├── schemas/analysis.py     – pydantic v2 request/response schemas
    ├── schemas/evidence.py     – EvidenceItemSchema
    ├── api/endpoints/
    │     ├── analyze.py        – POST /analyze, GET /analysis/{id},
    │     │                       GET /analysis/{id}/findings,
    │     │                       GET /analysis/compare, POST /self-analysis
    │     ├── evidence.py       – GET /analysis/{id}/findings/{fid}/evidence
    │     ├── sample_projects.py– GET /sample-projects
    │     └── health.py
    ├── services/repo_fetcher.py– SafeRepositoryWorkspace (sandbox, limits,
    │                             path-traversal guard, binary filter)
    ├── analyzer/
    │     ├── base.py           – FindingResult, EvidenceItem, BaseAnalyzer,
    │     │                       EVIDENCE_TYPES, VERIFICATION_STATUSES
    │     ├── orchestrator.py   – runs 8 deterministic analyzers + scoring
    │     ├── language_detector / code_quality / security / documentation /
    │     │   testing / dependencies / git_hygiene / architecture
    │     └── scoring.py
    └── ai/service.py           – AIReasoningService (Gemini, with grounded
                                  deterministic fallback; explanation-only)
```

## 2. Phase 1 Implementation (observed)

- `EvidenceItem` dataclass (`backend/app/analyzer/base.py`): `finding_title`, `category`,
  `source_file`, `evidence_type`, `evidence_summary`, `confidence`, `verification_status`, `source_line`.
- `EVIDENCE_TYPES`: FILE_MATCH, PATTERN_MATCH, AST_NODE, ABSENCE, FILE_COUNT, RATIO, CONFIG_CHECK.
- `VERIFICATION_STATUSES`: OBSERVED, INFERRED, UNVERIFIED. `CONFIDENCE_LEVELS`: HIGH, MEDIUM, LOW.
- Persistence model `FindingEvidence` (`backend/app/models/evidence.py`) — FK to `findings.id`
  with CASCADE delete, category mirror, indexed `source_file`.
- All 8 analyzers emit evidence (`analyze_with_evidence`).
- Evidence is persisted **before** the AI block in `run_analysis_task`
  (`backend/app/api/endpoints/analyze.py:89-115`); AI is explanation-only with a
  deterministic grounded fallback (`backend/app/ai/service.py`).
- Tests: `backend/tests/test_evidence.py` (513 lines, evidence emission, masking,
  cascade delete, endpoint), `test_api.py`, `test_analyzers.py`, `test_scoring.py`.
  Baseline suite: **34 passed**.

## 3. Current Evidence Flow

```
repo_fetcher (sandboxed) → analyzers → (findings, evidence_items)
  → run_analysis_task: findings persisted; evidence linked to Finding DB id
    by matching finding title (FIFO for duplicate titles)
  → AI enhancement (optional, after evidence commit)
```

## 4. Database Relationships (actual)

- `analysis_runs` 1—N `findings` (cascade)
- `analysis_runs` 1—N `recommendations`, `interview_questions`, `project_explanations`
- `findings` 1—N `finding_evidence` (cascade, indexed source_file)
- No Alembic; schema via `Base.metadata.create_all` at startup (`backend/app/main.py:13`).
- Existing SQLite DBs: `data/portfolio_reviewer.db`, `data/test_db.db`.

## 5. Risks Identified

| # | Risk | Impact | Mitigation in Phases 2–5 |
|---|------|--------|--------------------------|
| R1 | Evidence ↔ finding linking matches **by title** (`analyze.py:62-104`). Titles are not unique and analyzers may emit two findings with the same title; FIFO matching can mis-assign evidence. | High | Introduce deterministic `finding_key` (category.rule.path.line); evidence and claims reference the key. |
| R2 | `GET /analysis/compare` diffs findings **by title only** (`analyze.py:307-312`); false resolutions when titles collide, and no evidence/claim comparison. | High | Phase 3/4: key-based comparison with title fallback for legacy rows. |
| R3 | `Recommendation` rows are AI-generated and not linked to findings — no traceable Finding→Fix→Verify chain. | Medium | Add nullable `finding_id` + lifecycle `status`; generate deterministic recommendations from findings alongside AI ones. |
| R4 | No schema migrations; adding columns to existing SQLite DBs breaks on `create_all`. | Medium | Lightweight idempotent `ALTER TABLE` migration on startup. |
| R5 | README is rendered/used as data only, but claim extraction (new) must never treat README text as instructions. | High (new) | Claim auditor treats README as untrusted text: regex/pattern extraction only, no execution, no LLM truth-decisions. |
| R6 | Scores: new claim/evidence system could contaminate scoring. | Medium | Phases 2–5 keep the internal score untouched; trust metrics run independently. |

## 6. Required Modifications (per phase)

### Phase 2 — Claim Auditor
- New models: `Claim`, `ClaimEvidenceLink` (+ `ClaimFindingLink`) — `backend/app/models/claims.py`.
- New deterministic service: `backend/app/analyzer/claims.py` (extraction, normalization,
  evidence search, verification, status, confidence) wired into `run_analysis_task`
  **after** deterministic evidence, **before** AI explanation.
- New endpoints: `GET /api/analysis/{id}/claims`, `GET .../claims/{cid}`,
  `GET .../claims/{cid}/evidence`, `POST .../claims/reanalyze`.
- Frontend: new Claim Auditor tab reusing existing tab system.

### Phase 3 — Evidence Graph
- `Finding.finding_key` column + `FindingEvidence.finding_key` mirror (backfill migration).
- `Recommendation.finding_id` (nullable FK) + `status`; deterministic recommendations
  generated from findings.
- New model `VerificationResult`; graph assembly service; `GET /api/analysis/{id}/evidence-graph`;
  Evidence Explorer UI + lightweight relationship panel.

### Phase 4 — Proof of Improvement
- Key-based finding comparison (resolved / still_present / new / changed / unverified),
  claim status changes, evidence-backed metrics; `GET /api/analysis/improvement`;
  upgraded Before/After view + improvement timeline.

### Phase 5 — Project Trust Report
- `backend/app/services/trust_report.py` computing claim/finding/evidence statistics and
  an explained internal Engineering Confidence; `GET /api/analysis/{id}/trust-report`
  (JSON + Markdown export); Trust Report dashboard.

## 7. Testing Strategy

- Phase 1 suite must keep passing (regression gate) after every phase.
- New suites: `test_finding_key.py` (stable ids, duplicate titles), `test_claims.py`
  (extraction, normalization, tech/testing/security/CI verification, unsupported /
  contradicted / partial claims, evidence linking, malicious + empty README, duplicates),
  `test_graph.py` (graph relationships, recommendation→verification, finding lifecycle),
  `test_comparison.py` (key-based before/after), `test_trust_report.py` (statistics,
  confidence, export, missing/empty data).
- Sample projects extended so the demo repository genuinely produces
  SUPPORTED / PARTIALLY_SUPPORTED / UNVERIFIED / CONTRADICTED claims, plus an
  improved counterpart demonstrating verified before/after changes.
