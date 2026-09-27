"""Phase 4 tests — Proof of Improvement (before/after comparison)."""
import os
import pytest

from backend.app.services.repo_fetcher import SafeRepositoryWorkspace
from backend.app.services.improvement import build_improvement_report
from backend.app.models.findings import AnalysisRun, Finding
from backend.app.models.evidence import FindingEvidence
from backend.app.models.claims import Claim

BAD_DIR = os.path.abspath("sample_projects/bad_project")
GOOD_DIR = os.path.abspath("sample_projects/improved_project")


def _analyze(client, sample):
    res = client.post("/api/analyze", json={"github_url": f"sample:{sample}", "use_ai": False})
    return res.json()["id"]


class TestImprovementReport:
    def test_sample_improvement_is_evidence_backed(self, client, db_session):
        bad_id = _analyze(client, "bad_project")
        good_id = _analyze(client, "improved_project")
        report = build_improvement_report(db_session, bad_id, good_id)

        # score must improve but never be cited as proof by itself
        assert report["score"]["after"] > report["score"]["before"]
        assert "NOT proof" in report["score"]["note"]

        findings = report["findings"]
        assert findings["resolved"], "bad→improved must resolve real findings"
        assert all(d["status"] == "RESOLVED" for d in findings["resolved"])
        for d in findings["resolved"]:
            assert d["finding_key"], "resolved findings must be identified by stable key"

        # security findings must measurably drop
        sec = report["metrics"]["security_findings"]
        assert sec["verified"] and sec["after"] == 0 and sec["before"] > 0

        # testing metric: measured or explicitly unverified — never faked
        testing = report["metrics"]["testing"]
        if not testing["verified"]:
            assert "could not be verified" in testing["display"]

        # timeline uses real analysis runs
        steps = report["timeline"]
        assert steps[0]["analysis_id"] == bad_id
        assert steps[3]["analysis_id"] == good_id

    def test_unverifiable_change_reported_honestly(self, client, db_session):
        """Comparing the same repo with itself: no fabricated deltas."""
        aid = _analyze(client, "bad_project")
        report = build_improvement_report(db_session, aid, aid)
        assert report["score"]["delta"] == 0
        assert not report["findings"]["resolved"]
        assert not report["findings"]["new"]

    def test_claim_status_changes_captured(self, client, db_session):
        bad_id = _analyze(client, "bad_project")
        good_id = _analyze(client, "improved_project")
        report = build_improvement_report(db_session, bad_id, good_id)
        # CI/CD claim: UNVERIFIED in bad_project (no workflows) →
        # SUPPORTED in improved_project (workflow present)
        ci_change = next(
            (c for c in report["claim_changes"]
             if c["claim_text"] and "CI/CD" in c["claim_text"]),
            None,
        )
        assert ci_change is not None
        assert ci_change["before_status"] == "UNVERIFIED"
        assert ci_change["after_status"] == "SUPPORTED"
        assert ci_change["verified"] is True

    def test_missing_run_raises(self, client, db_session):
        with pytest.raises(ValueError):
            build_improvement_report(db_session, "nope", "nope2")

    def test_improvement_endpoint(self, client):
        bad_id = _analyze(client, "bad_project")
        good_id = _analyze(client, "improved_project")
        res = client.get(f"/api/analysis/improvement?before_id={bad_id}&after_id={good_id}")
        assert res.status_code == 200
        data = res.json()
        assert "resolved" in data["findings"]
        assert all(d["finding_key"] for d in data["findings"]["resolved"])
