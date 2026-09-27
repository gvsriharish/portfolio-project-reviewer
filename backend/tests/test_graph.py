"""Phase 3 tests — Evidence Graph, recommendations, finding lifecycle."""
import os
import pytest

from backend.app.services.repo_fetcher import SafeRepositoryWorkspace
from backend.app.services.graph_builder import build_evidence_graph
from backend.app.services.finding_comparison import compare_findings
from backend.app.models.findings import AnalysisRun, Finding, Recommendation
from backend.app.models.evidence import FindingEvidence
from backend.app.models.claims import Claim
from backend.app.models.verification import VerificationResult

BAD_DIR = os.path.abspath("sample_projects/bad_project")
GOOD_DIR = os.path.abspath("sample_projects/improved_project")


def _analyze(client, sample):
    res = client.post("/api/analyze", json={"github_url": f"sample:{sample}", "use_ai": False})
    return res.json()["id"]


class TestEvidenceGraph:
    def test_graph_structure(self, client, db_session):
        aid = _analyze(client, "bad_project")
        graph = build_evidence_graph(db_session, aid)
        assert graph["analysis_id"] == aid
        counts = graph["counts"]
        assert counts["findings"] > 0
        assert counts["evidence"] > 0
        assert counts["claims"] > 0
        # edges exist and reference existing nodes only
        nodes = graph["nodes"]
        finding_ids = {n["id"] for n in nodes["findings"]}
        evidence_ids = {n["id"] for n in nodes["evidence"]}
        claim_ids = {n["id"] for n in nodes["claims"]}
        for e in graph["edges"]["evidence_finding"]:
            assert e["evidence_id"] in evidence_ids
            assert e["finding_id"] in finding_ids
        for e in graph["edges"]["claim_evidence"]:
            assert e["claim_id"] in claim_ids
            assert e["evidence_id"] in evidence_ids
        for e in graph["edges"]["claim_finding"]:
            assert e["claim_id"] in claim_ids
            assert e["finding_id"] in finding_ids

    def test_graph_endpoint(self, client):
        aid = _analyze(client, "bad_project")
        res = client.get(f"/api/analysis/{aid}/evidence-graph")
        assert res.status_code == 200
        data = res.json()
        assert data["counts"]["findings"] > 0

    def test_graph_404(self, client):
        assert client.get("/api/analysis/nope/evidence-graph").status_code == 404

    def test_full_chain_traversable(self, client, db_session):
        """Claim → Evidence → Finding must be traversable for real rows."""
        aid = _analyze(client, "bad_project")
        graph = build_evidence_graph(db_session, aid)
        evidence_ids = {n["id"] for n in graph["nodes"]["evidence"]}
        traversed = False
        for edge in graph["edges"]["claim_evidence"]:
            if any(e["evidence_id"] == edge["evidence_id"] for e in graph["edges"]["evidence_finding"]):
                traversed = True
                break
        assert traversed, "at least one full Claim→Evidence→Finding path must exist"


class TestFindingLifecycle:
    def _mk(self, analysis_id, title, sev, key=None):
        return Finding(id=f"f-{title}-{sev}", analysis_id=analysis_id, category="Security",
                       severity=sev, title=title, file_path="app/config.py", line_number=1,
                       evidence="", description="", why_it_matters="",
                       recommended_fix="", verification_method="", finding_key=key)

    def test_resolved(self):
        before = [self._mk("a", "Hardcoded Secret", "HIGH", "security.hardcoded-secret.app-config-py")]
        after = []
        resolved, sp, new, ch = compare_findings(before, after)
        assert len(resolved) == 1 and resolved[0].status == "RESOLVED"
        assert not sp and not new and not ch

    def test_new(self):
        before = []
        after = [self._mk("b", "Hardcoded Secret", "HIGH", "security.hardcoded-secret.app-config-py")]
        resolved, sp, new, ch = compare_findings(before, after)
        assert len(new) == 1 and new[0].status == "NEW"

    def test_still_present_and_changed(self):
        before = [
            self._mk("a", "Hardcoded Secret", "HIGH", "security.hardcoded-secret.app-config-py"),
            self._mk("a", "Bare Except", "MEDIUM", "code-quality.bare-except.app-main-py"),
        ]
        after = [
            self._mk("b", "Hardcoded Secret", "HIGH", "security.hardcoded-secret.app-config-py"),
            self._mk("b", "Bare Except", "LOW", "code-quality.bare-except.app-main-py"),
        ]
        resolved, sp, new, ch = compare_findings(before, after)
        assert len(sp) == 1 and sp[0].status == "STILL_PRESENT"
        assert len(ch) == 1 and ch[0].status == "CHANGED"
        assert ch[0].before_severity == "MEDIUM" and ch[0].after_severity == "LOW"

    def test_duplicate_titles_resolved_by_key(self):
        """Two findings with the same title but different paths must not
        be confused during comparison."""
        before = [
            self._mk("a", "Same Title", "HIGH", "security.same-title.app-a-py"),
            self._mk("a", "Same Title", "HIGH", "security.same-title.app-b-py"),
        ]
        after = [self._mk("b", "Same Title", "HIGH", "security.same-title.app-a-py")]
        resolved, sp, new, ch = compare_findings(before, after)
        assert len(resolved) == 1 and len(sp) == 1 and not new

    def test_title_fallback_for_legacy_rows(self):
        before = [self._mk("a", "Legacy Finding", "HIGH", None)]
        after = [self._mk("b", "Legacy Finding", "HIGH", None)]
        resolved, sp, new, ch = compare_findings(before, after)
        assert len(sp) == 1
        assert sp[0].match_method == "title_fallback"

    def test_resolution_not_inferred_from_score(self, client, db_session):
        """bad → improved improves the score, but only actually-fixed
        findings may be RESOLVED; findings still present stay STILL_PRESENT."""
        bad_id = _analyze(client, "bad_project")
        good_id = _analyze(client, "improved_project")
        bad_run = db_session.get(AnalysisRun, bad_id)
        good_run = db_session.get(AnalysisRun, good_id)
        assert good_run.overall_score > bad_run.overall_score  # score improves...
        from backend.app.models.findings import Finding
        bad_f = db_session.query(Finding).filter(Finding.analysis_id == bad_id).all()
        good_f = db_session.query(Finding).filter(Finding.analysis_id == good_id).all()
        resolved, sp, new, ch = compare_findings(bad_f, good_f)
        # ...yet any finding type still present in the improved repo must NOT be resolved
        resolved_categories = {(d.category, d.title) for d in resolved}
        still_categories = {(d.category, d.title) for d in sp}
        assert resolved_categories.isdisjoint(still_categories)


class TestRecommendations:
    def test_recommendation_model_supports_lifecycle(self, client, db_session):
        aid = _analyze(client, "bad_project")
        rec = Recommendation(
            id="rec-1", analysis_id=aid, priority_group="Fix First", rank=1,
            title="Add automated tests", action="Add tests", reason="No tests",
            verification="Test files detected", finding_id=None,
            status="OPEN", expected_change="Test files > 0",
        )
        db_session.add(rec)
        db_session.commit()
        stored = db_session.get(Recommendation, "rec-1")
        assert stored.status == "OPEN"
        assert stored.finding_id is None  # nullable for AI/legacy rows
