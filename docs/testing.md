# Testing and Acceptance Coverage

## Backend

Run:

```bash
python -m pytest backend/tests -q
```

The final merged implementation was executed against the complete backend test suite with **103 tests passing**.

Coverage includes:

- API and health behavior
- repository/project analyzers
- findings and stable finding keys
- evidence extraction and attribution
- claims and verification results
- scoring and comparisons
- trust report / evidence graph behavior
- phase 2–5 hardening regressions
- phase 6–9 portfolio generation
- engineering monitor snapshots
- evidence-backed interview sessions and duplicate-answer protection
- proof passport generation and SHA-256 verification

## Frontend

Install dependencies from the committed lockfile:

```bash
cd frontend
npm ci
npm run build
npm run lint
```

The final source was TypeScript-checked successfully during hardening. The verification environment used for packaging was Linux, while the cached frontend dependency tree available from the uploaded Windows archive contained Windows-native `rolldown`/Oxlint binaries. Therefore the production Vite build and Oxlint executable were not treated as source failures; they must be rerun after a clean `npm ci` on the target platform.

## Acceptance principle

Tests should pass because the application behavior is correct, not because Git metadata or evidence has been fabricated. The monitor and proof features preserve the distinction between verified evidence and unavailable information.
