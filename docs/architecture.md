

## Phase 6–9 Extensions

The original relational evidence chain remains the source of truth. Phase 6–9 services read `AnalysisRun`, `Finding`, `FindingEvidence`, `Claim`, `Recommendation`, `VerificationResult`, and existing explanation rows, then persist derived artifacts in four small tables: `portfolio_artifacts`, `engineering_snapshots`, `interview_sessions`, and `proof_passports`. No duplicate evidence, claim, finding, recommendation, or verification store is introduced.

The monitor compares deterministic finding keys, claim statuses, and evidence file paths between stored snapshots. The interview question generator selects only detected technologies and findings. The passport hashes canonical JSON with sorted keys and excludes ORM metadata or secrets.
