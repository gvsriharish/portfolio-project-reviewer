# Architecture Decision Records (ADR)

## ADR 1: Deterministic Analysis Precedes AI Reasoning
- **Decision**: Perform all code quality, security, documentation, testing, and dependency checks via deterministic Python AST parsers and regex heuristics before invoking AI.
- **Rationale**: Prevents LLM hallucinations, ensures 100% reproducible score calculations, reduces token costs, and enables full offline operation.

## ADR 2: Transparent Penalty-Based Scoring
- **Decision**: Base category score on 100 points with explicit, documented deductions (CRITICAL: -25 pts, HIGH: -15 pts, MEDIUM: -8 pts, LOW: -3 pts).
- **Rationale**: Eliminates "black-box" magic numbers. Developers can see the exact breakdown of why a score was calculated.

## ADR 3: Dual-Mode AI Reasoning (Gemini + Heuristic Fallback)
- **Decision**: Wrap Google GenAI SDK behind an isolated service with a robust deterministic heuristic generator.
- **Rationale**: Ensures the application remains fully functional during hackathon demos, offline environments, or rate-limited conditions without breaking user workflows.
