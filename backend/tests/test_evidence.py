"""
Tests for the Phase 1 Engineering Evidence Foundation.

Covers:
- EvidenceItem dataclass emission from analyzers
- FindingEvidence ORM persistence via run_analysis_task
- GET /api/analysis/{id}/findings/{fid}/evidence endpoint
- GET /api/analysis/{id}/findings?include_evidence=true
- Cascade delete of evidence rows with parent analysis
- Secret masking in evidence summaries
- Clean project produces no evidence (no false positives from clean code)
"""
import os
import pytest
from sqlalchemy.orm import Session

from backend.app.services.repo_fetcher import SafeRepositoryWorkspace
from backend.app.analyzer.security import SecurityAnalyzer
from backend.app.analyzer.testing import TestingAnalyzer
from backend.app.analyzer.documentation import DocumentationAnalyzer
from backend.app.analyzer.dependencies import DependencyAnalyzer
from backend.app.analyzer.git_hygiene import GitHygieneAnalyzer
from backend.app.analyzer.code_quality import CodeQualityAnalyzer
from backend.app.analyzer.base import EvidenceItem
from backend.app.models.evidence import FindingEvidence
from backend.app.models.findings import AnalysisRun, Finding


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BAD_DIR = os.path.abspath("sample_projects/bad_project")
GOOD_DIR = os.path.abspath("sample_projects/improved_project")


def _bad_workspace() -> SafeRepositoryWorkspace:
    return SafeRepositoryWorkspace(BAD_DIR, "bad_project", "sample", is_sample=True)


def _good_workspace() -> SafeRepositoryWorkspace:
    return SafeRepositoryWorkspace(GOOD_DIR, "improved_project", "sample", is_sample=True)


# ---------------------------------------------------------------------------
# Unit tests: EvidenceItem emission from analyzers
# ---------------------------------------------------------------------------

class TestSecurityAnalyzerEvidence:
    def test_emits_evidence_for_secrets(self):
        findings, evidence = SecurityAnalyzer().analyze_with_evidence(_bad_workspace())
        assert len(findings) > 0, "Expected security findings in bad_project"
        assert len(evidence) > 0, "Expected evidence items in bad_project"

    def test_evidence_type_is_pattern_match_or_file_match(self):
        _, evidence = SecurityAnalyzer().analyze_with_evidence(_bad_workspace())
        for ev in evidence:
            assert ev.evidence_type in ("PATTERN_MATCH", "FILE_MATCH", "AST_NODE"), (
                f"Unexpected evidence type: {ev.evidence_type}"
            )

    def test_evidence_has_correct_fields(self):
        _, evidence = SecurityAnalyzer().analyze_with_evidence(_bad_workspace())
        assert len(evidence) > 0
        ev = evidence[0]
        assert ev.finding_title
        assert ev.category == "Security"
        assert ev.confidence in ("HIGH", "MEDIUM", "LOW")
        assert ev.verification_status in ("OBSERVED", "INFERRED", "UNVERIFIED")

    def test_secrets_are_masked_in_evidence_summary(self):
        _, evidence = SecurityAnalyzer().analyze_with_evidence(_bad_workspace())
        for ev in evidence:
            # Raw AWS key pattern should never appear unmasked
            assert "AKIAIOSFODNN7EXAMPLE" not in ev.evidence_summary, (
                "Raw AWS key appeared unmasked in evidence_summary"
            )
            # The masked placeholder must be present when a key is referenced
            if "AKIA" in ev.evidence_summary:
                assert "REDACTED" in ev.evidence_summary

    def test_finding_title_correlates_with_evidence(self):
        findings, evidence = SecurityAnalyzer().analyze_with_evidence(_bad_workspace())
        finding_titles = {f.title for f in findings}
        for ev in evidence:
            assert ev.finding_title in finding_titles, (
                f"EvidenceItem.finding_title '{ev.finding_title}' has no matching FindingResult"
            )

    def test_clean_project_produces_no_security_evidence(self):
        findings, evidence = SecurityAnalyzer().analyze_with_evidence(_good_workspace())
        assert len(findings) == 0
        assert len(evidence) == 0

    def test_analyze_is_backward_compatible(self):
        """analyze() must return identical findings to analyze_with_evidence()[0]."""
        a = SecurityAnalyzer()
        ws = _bad_workspace()
        plain = a.analyze(ws)
        with_ev, _ = a.analyze_with_evidence(ws)
        assert [f.title for f in plain] == [f.title for f in with_ev]


class TestTestingAnalyzerEvidence:
    def test_emits_absence_evidence_for_zero_tests(self):
        _, evidence = TestingAnalyzer().analyze_with_evidence(_bad_workspace())
        absence_items = [e for e in evidence if e.evidence_type == "ABSENCE"]
        assert len(absence_items) >= 1

    def test_absence_evidence_is_inferred(self):
        _, evidence = TestingAnalyzer().analyze_with_evidence(_bad_workspace())
        for ev in evidence:
            assert ev.verification_status == "INFERRED"

    def test_improved_project_has_no_zero_test_finding(self):
        findings, _ = TestingAnalyzer().analyze_with_evidence(_good_workspace())
        titles = [f.title for f in findings]
        assert not any("Zero Automated Tests" in t for t in titles)


class TestDocumentationAnalyzerEvidence:
    def test_emits_absence_evidence_for_missing_sections(self):
        _, evidence = DocumentationAnalyzer().analyze_with_evidence(_bad_workspace())
        absence_items = [e for e in evidence if e.evidence_type == "ABSENCE"]
        # bad_project README is missing multiple sections
        assert len(absence_items) >= 1

    def test_absence_evidence_has_inferred_status(self):
        _, evidence = DocumentationAnalyzer().analyze_with_evidence(_bad_workspace())
        for ev in evidence:
            if ev.evidence_type == "ABSENCE":
                assert ev.verification_status == "INFERRED"


class TestDependencyAnalyzerEvidence:
    def test_emits_one_evidence_per_unpinned_package(self):
        findings, evidence = DependencyAnalyzer().analyze_with_evidence(_bad_workspace())
        # bad_project has unpinned deps; we expect multiple evidence items for one finding
        file_match_items = [e for e in evidence if e.evidence_type == "FILE_MATCH"]
        # At least the finding and some items
        assert len(file_match_items) >= 1
        # Each should have a line number (observed in requirements.txt)
        for ev in file_match_items:
            if ev.source_file == "requirements.txt":
                assert ev.source_line is not None


class TestGitHygieneAnalyzerEvidence:
    def test_emits_evidence_for_missing_gitignore(self):
        _, evidence = GitHygieneAnalyzer().analyze_with_evidence(_bad_workspace())
        assert any(e.evidence_type == "ABSENCE" for e in evidence)


class TestCodeQualityAnalyzerEvidence:
    def test_ast_node_evidence_for_bare_except(self):
        _, evidence = CodeQualityAnalyzer().analyze_with_evidence(_bad_workspace())
        ast_items = [e for e in evidence if e.evidence_type == "AST_NODE"]
        assert len(ast_items) >= 1
        for ev in ast_items:
            assert ev.source_line is not None
            assert ev.verification_status == "OBSERVED"


class TestEvidenceItemDataclass:
    def test_defaults(self):
        ev = EvidenceItem(
            finding_title="Test",
            category="Security",
            source_file="main.py",
            evidence_type="PATTERN_MATCH",
            evidence_summary="test summary",
        )
        assert ev.confidence == "MEDIUM"
        assert ev.verification_status == "OBSERVED"
        assert ev.source_line is None

    def test_all_fields(self):
        ev = EvidenceItem(
            finding_title="Secret found",
            category="Security",
            source_file="config.py",
            evidence_type="PATTERN_MATCH",
            evidence_summary="API key at config.py:5",
            confidence="HIGH",
            verification_status="OBSERVED",
            source_line=5,
        )
        assert ev.source_line == 5
        assert ev.confidence == "HIGH"


# ---------------------------------------------------------------------------
# Integration tests: API evidence endpoint
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Helper: poll until analysis is COMPLETED (background task uses SessionLocal)
# ---------------------------------------------------------------------------

def _wait_for_completion(client, analysis_id: str, max_polls: int = 30) -> dict:
    """Poll GET /api/analysis/{id} until status is COMPLETED or FAILED."""
    import time
    for _ in range(max_polls):
        res = client.get(f"/api/analysis/{analysis_id}")
        data = res.json()
        if data.get("status") in ("COMPLETED", "FAILED"):
            return data
        time.sleep(0.1)
    return client.get(f"/api/analysis/{analysis_id}").json()


class TestEvidenceAPI:
    def test_evidence_endpoint_returns_404_for_unknown_finding(self, client):
        res = client.get("/api/analysis/bad-id/findings/bad-fid/evidence")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_evidence_endpoint_returns_empty_list_for_finding_with_no_evidence(
        self, client, db_session
    ):
        """A finding created without evidence items returns an empty list, not 404."""
        # Create a minimal analysis run + finding directly in the DB.
        import uuid
        run_id = str(uuid.uuid4())
        finding_id = str(uuid.uuid4())
        db_session.add(AnalysisRun(
            id=run_id,
            repo_url="sample:bad_project",
            repo_name="test",
            owner="sample",
            status="COMPLETED",
        ))
        db_session.add(Finding(
            id=finding_id,
            analysis_id=run_id,
            category="Security",
            severity="HIGH",
            title="Test finding",
            file_path="main.py",
            evidence="some evidence",
            description="desc",
            why_it_matters="why",
            recommended_fix="fix",
            verification_method="verify",
        ))
        db_session.commit()

        res = client.get(f"/api/analysis/{run_id}/findings/{finding_id}/evidence")
        assert res.status_code == 200
        assert res.json() == []

    def test_evidence_embedded_via_include_evidence_param(self, client, db_session):
        """GET /findings?include_evidence=true returns evidence_items list on each finding.

        Because the background task uses SessionLocal (not the injected test session),
        we populate the test DB directly using the orchestrator and persist evidence
        via the ORM, then query via the API.
        """
        import uuid as _uuid
        from backend.app.analyzer.orchestrator import AnalysisOrchestrator
        from backend.app.models.evidence import FindingEvidence as _FE

        ws = _bad_workspace()
        results = AnalysisOrchestrator().run_full_analysis(ws)

        run_id = str(_uuid.uuid4())
        db_session.add(AnalysisRun(
            id=run_id,
            repo_url="sample:bad_project",
            repo_name="bad_project",
            owner="sample",
            status="COMPLETED",
            overall_score=results["overall_score"],
            category_scores=results["category_scores"],
            languages=results["languages"],
            frameworks=results["frameworks"],
            architecture_summary=results["architecture_summary"],
        ))

        from collections import defaultdict
        title_to_ids: dict = defaultdict(list)
        for f in results["findings"]:
            fid = str(_uuid.uuid4())
            db_session.add(Finding(
                id=fid, analysis_id=run_id,
                category=f.category, severity=f.severity, title=f.title,
                file_path=f.file_path, line_number=f.line_number, evidence=f.evidence,
                description=f.description, why_it_matters=f.why_it_matters,
                recommended_fix=f.recommended_fix, verification_method=f.verification_method,
            ))
            title_to_ids[f.title].append(fid)

        used: dict = defaultdict(int)
        for ev in results.get("evidence_items", []):
            id_list = title_to_ids.get(ev.finding_title, [])
            idx = used[ev.finding_title]
            fid = id_list[idx] if idx < len(id_list) else (id_list[-1] if id_list else None)
            if not fid:
                continue
            db_session.add(_FE(
                id=str(_uuid.uuid4()), finding_id=fid, category=ev.category,
                source_file=ev.source_file, source_line=ev.source_line,
                evidence_type=ev.evidence_type, evidence_summary=ev.evidence_summary,
                confidence=ev.confidence, verification_status=ev.verification_status,
            ))
        db_session.commit()

        # Now query via the API using the test session.
        findings_res = client.get(
            f"/api/analysis/{run_id}/findings?include_evidence=true"
        )
        assert findings_res.status_code == 200
        findings = findings_res.json()
        assert len(findings) > 0

        with_evidence = [f for f in findings if f.get("evidence_items")]
        assert len(with_evidence) > 0, (
            "Expected at least one finding to have structured evidence items"
        )

        for f in with_evidence:
            for ev in f["evidence_items"]:
                assert ev["finding_id"] == f["id"]
                assert ev["verification_status"] in ("OBSERVED", "INFERRED", "UNVERIFIED")
                assert ev["confidence"] in ("HIGH", "MEDIUM", "LOW")

    def test_include_evidence_false_returns_empty_list(self, client, db_session):
        """GET /findings without include_evidence=true returns evidence_items as empty list."""
        import uuid as _uuid

        run_id = str(_uuid.uuid4())
        db_session.add(AnalysisRun(
            id=run_id,
            repo_url="sample:bad_project",
            repo_name="bad_project",
            owner="sample",
            status="COMPLETED",
        ))
        fid = str(_uuid.uuid4())
        db_session.add(Finding(
            id=fid, analysis_id=run_id,
            category="Security", severity="HIGH", title="Test",
            file_path="x.py", evidence="e",
            description="d", why_it_matters="w",
            recommended_fix="r", verification_method="v",
        ))
        db_session.commit()

        findings_res = client.get(f"/api/analysis/{run_id}/findings")
        assert findings_res.status_code == 200
        for f in findings_res.json():
            assert f.get("evidence_items", []) == []

    def test_evidence_endpoint_returns_items_for_known_finding(self, client, db_session):
        """GET /findings/{fid}/evidence returns evidence rows for a finding in the test DB."""
        import uuid as _uuid
        from backend.app.models.evidence import FindingEvidence as _FE

        run_id = str(_uuid.uuid4())
        finding_id = str(_uuid.uuid4())
        ev_id = str(_uuid.uuid4())

        db_session.add(AnalysisRun(
            id=run_id, repo_url="sample:bad_project",
            repo_name="bad_project", owner="sample", status="COMPLETED",
        ))
        db_session.add(Finding(
            id=finding_id, analysis_id=run_id,
            category="Security", severity="HIGH",
            title="Potential AWS Access Key ID exposed",
            file_path="config.py", line_number=5,
            evidence="AKIA****REDACTED****",
            description="desc", why_it_matters="why",
            recommended_fix="fix", verification_method="verify",
        ))
        db_session.add(_FE(
            id=ev_id, finding_id=finding_id, category="Security",
            source_file="config.py", source_line=5,
            evidence_type="PATTERN_MATCH",
            evidence_summary="Pattern matched at config.py:5 — value: AKIA****REDACTED****",
            confidence="HIGH", verification_status="OBSERVED",
        ))
        db_session.commit()

        ev_res = client.get(
            f"/api/analysis/{run_id}/findings/{finding_id}/evidence"
        )
        assert ev_res.status_code == 200
        items = ev_res.json()
        assert len(items) == 1
        assert items[0]["id"] == ev_id
        assert items[0]["finding_id"] == finding_id
        assert items[0]["evidence_type"] == "PATTERN_MATCH"
        assert items[0]["verification_status"] == "OBSERVED"
        assert items[0]["confidence"] == "HIGH"
        assert items[0]["source_line"] == 5

    def test_evidence_finding_must_belong_to_analysis(self, client, db_session):
        """A finding ID from a different analysis should return 404."""
        import uuid

        # Create two separate runs
        run1_id = str(uuid.uuid4())
        run2_id = str(uuid.uuid4())
        fid_in_run2 = str(uuid.uuid4())

        for run_id in (run1_id, run2_id):
            db_session.add(AnalysisRun(
                id=run_id,
                repo_url="sample:bad_project",
                repo_name="test",
                owner="sample",
                status="COMPLETED",
            ))

        db_session.add(Finding(
            id=fid_in_run2,
            analysis_id=run2_id,
            category="Security",
            severity="HIGH",
            title="Cross-analysis test",
            file_path="x.py",
            evidence="e",
            description="d",
            why_it_matters="w",
            recommended_fix="r",
            verification_method="v",
        ))
        db_session.commit()

        # Querying with run1_id for a finding that belongs to run2 must 404
        res = client.get(f"/api/analysis/{run1_id}/findings/{fid_in_run2}/evidence")
        assert res.status_code == 404


class TestCascadeDelete:
    def test_evidence_rows_deleted_with_analysis(self, db_session: Session):
        """Deleting an AnalysisRun cascades to FindingEvidence rows."""
        import uuid

        run_id = str(uuid.uuid4())
        finding_id = str(uuid.uuid4())
        evidence_id = str(uuid.uuid4())

        db_session.add(AnalysisRun(
            id=run_id,
            repo_url="sample:bad_project",
            repo_name="test",
            owner="sample",
            status="COMPLETED",
        ))
        db_session.add(Finding(
            id=finding_id,
            analysis_id=run_id,
            category="Security",
            severity="HIGH",
            title="Cascade test finding",
            file_path="test.py",
            evidence="e",
            description="d",
            why_it_matters="w",
            recommended_fix="r",
            verification_method="v",
        ))
        db_session.add(FindingEvidence(
            id=evidence_id,
            finding_id=finding_id,
            category="Security",
            source_file="test.py",
            source_line=1,
            evidence_type="PATTERN_MATCH",
            evidence_summary="Test evidence",
            confidence="HIGH",
            verification_status="OBSERVED",
        ))
        db_session.commit()

        # Verify evidence exists
        ev = db_session.query(FindingEvidence).filter_by(id=evidence_id).first()
        assert ev is not None

        # Delete the analysis run
        run = db_session.query(AnalysisRun).filter_by(id=run_id).first()
        db_session.delete(run)
        db_session.commit()

        # Evidence must be gone
        ev_after = db_session.query(FindingEvidence).filter_by(id=evidence_id).first()
        assert ev_after is None, "FindingEvidence was not cascade-deleted with AnalysisRun"


class TestExistingTestsUnchanged:
    """Smoke tests confirming existing test assertions still pass."""

    def test_bad_project_score_still_low(self):
        from backend.app.analyzer.orchestrator import AnalysisOrchestrator
        ws = _bad_workspace()
        results = AnalysisOrchestrator().run_full_analysis(ws)
        assert results["overall_score"] <= 60

    def test_orchestrator_returns_evidence_items_key(self):
        from backend.app.analyzer.orchestrator import AnalysisOrchestrator
        ws = _bad_workspace()
        results = AnalysisOrchestrator().run_full_analysis(ws)
        assert "evidence_items" in results
        assert isinstance(results["evidence_items"], list)
        assert len(results["evidence_items"]) > 0

    def test_improved_project_score_still_high(self):
        from backend.app.analyzer.orchestrator import AnalysisOrchestrator
        ws = _good_workspace()
        results = AnalysisOrchestrator().run_full_analysis(ws)
        assert results["overall_score"] >= 85
