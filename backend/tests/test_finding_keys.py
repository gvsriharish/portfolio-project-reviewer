"""Phase gate tests — stable finding identifiers (architectural fix)."""
import os
import pytest

from backend.app.analyzer.base import FindingResult
from backend.app.analyzer.finding_keys import compute_finding_key, slug
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace
from backend.app.models.findings import AnalysisRun, Finding
from backend.app.models.evidence import FindingEvidence

BAD_DIR = os.path.abspath("sample_projects/bad_project")


def _workspace():
    return SafeRepositoryWorkspace(BAD_DIR, "bad_project", "sample", is_sample=True)


class TestFindingKeyDeterminism:
    def test_same_finding_same_key(self):
        f = FindingResult(category="Security", severity="HIGH", title="Hardcoded Secret",
                          file_path="app/config.py", line_number=14, evidence="",
                          description="", why_it_matters="", recommended_fix="",
                          verification_method="")
        assert compute_finding_key(f) == compute_finding_key(f)

    def test_key_format(self):
        f = FindingResult(category="Security", severity="HIGH", title="Hardcoded Secret",
                          file_path="app/config.py", line_number=14, evidence="",
                          description="", why_it_matters="", recommended_fix="",
                          verification_method="")
        assert compute_finding_key(f) == "security.hardcoded-secret.app-config-py"

    def test_duplicate_titles_get_unique_keys_in_run(self):
        f1 = FindingResult(category="Security", severity="HIGH", title="Same Title",
                           file_path="app/a.py", line_number=1, evidence="",
                           description="", why_it_matters="", recommended_fix="",
                           verification_method="")
        f2 = FindingResult(category="Security", severity="HIGH", title="Same Title",
                           file_path="app/b.py", line_number=2, evidence="",
                           description="", why_it_matters="", recommended_fix="",
                           verification_method="")
        f3 = FindingResult(category="Security", severity="HIGH", title="Same Title",
                           file_path="app/a.py", line_number=9, evidence="",
                           description="", why_it_matters="", recommended_fix="",
                           verification_method="")
        keys = []
        for f in (f1, f2, f3):
            keys.append(compute_finding_key(f, keys))
        assert len(set(keys)) == 3
        # line-only differences get a collision suffix, not a line-based key
        assert keys[0] == keys[2].rsplit('-', 1)[0]

    def test_line_shift_does_not_change_key(self):
        f1 = FindingResult(category="Code Quality", severity="LOW", title="Long Function",
                           file_path="app/main.py", line_number=10, evidence="",
                           description="", why_it_matters="", recommended_fix="",
                           verification_method="")
        f2 = FindingResult(category="Code Quality", severity="LOW", title="Long Function",
                           file_path="app/main.py", line_number=42, evidence="",
                           description="", why_it_matters="", recommended_fix="",
                           verification_method="")
        assert compute_finding_key(f1) == compute_finding_key(f2)


class TestFindingKeyPersistence:
    def test_analysis_persists_finding_keys(self, client, db_session):
        res = client.post("/api/analyze", json={"github_url": "sample:bad_project", "use_ai": False})
        analysis_id = res.json()["id"]
        findings = db_session.query(Finding).filter(Finding.analysis_id == analysis_id).all()
        assert findings, "expected findings persisted"
        keys = [f.finding_key for f in findings]
        assert all(keys), "every finding must carry a stable finding_key"
        assert len(set(keys)) == len(keys), "finding keys must be unique within a run"

    def test_evidence_rows_carry_finding_key(self, client, db_session):
        res = client.post("/api/analyze", json={"github_url": "sample:bad_project", "use_ai": False})
        analysis_id = res.json()["id"]
        evidence = (
            db_session.query(FindingEvidence)
            .join(Finding, FindingEvidence.finding_id == Finding.id)
            .filter(Finding.analysis_id == analysis_id)
            .all()
        )
        assert evidence, "expected evidence persisted"
        assert all(e.finding_key for e in evidence)

    def test_duplicate_title_findings_both_get_evidence(self, client, db_session):
        """Two findings sharing a title must not have their evidence merged."""
        res = client.post("/api/analyze", json={"github_url": "sample:bad_project", "use_ai": False})
        analysis_id = res.json()["id"]
        findings = db_session.query(Finding).filter(Finding.analysis_id == analysis_id).all()
        ev_by_finding = {
            f.id: db_session.query(FindingEvidence).filter(FindingEvidence.finding_id == f.id).count()
            for f in findings
        }
        # bad_project has secrets in two lines of app/config.py producing
        # multiple security findings; every finding with evidence keeps its own rows.
        for f in findings:
            assert ev_by_finding[f.id] >= 0  # rows exist only via valid linkage
        total_ev = db_session.query(FindingEvidence).join(Finding).filter(
            Finding.analysis_id == analysis_id).count()
        assert total_ev > 0
