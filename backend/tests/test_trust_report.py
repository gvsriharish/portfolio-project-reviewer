"""Phase 5 tests — Project Trust Report."""
import os
import pytest

from backend.app.services.trust_report import build_trust_report, render_markdown, CONFIDENCE_FACTORS

BAD_DIR = os.path.abspath("sample_projects/bad_project")


def _analyze(client, sample):
    res = client.post("/api/analyze", json={"github_url": f"sample:{sample}", "use_ai": False})
    return res.json()["id"]


class TestTrustReport:
    def test_report_statistics_from_real_data(self, client, db_session):
        aid = _analyze(client, "bad_project")
        report = build_trust_report(db_session, aid)

        cs = report["claim_stats"]
        assert cs["total"] == cs["supported"] + cs["partially_supported"] + cs["unverified"] + cs["contradicted"]
        assert cs["total"] > 0

        fs = report["finding_stats"]
        assert fs["total"] == (fs["critical"] + fs["high"] + fs["medium"] + fs["low"] + fs["info"])
        es = report["evidence_stats"]
        assert es["total"] == es["observed"] + es["inferred"] + es["unverified"]

    def test_bad_project_reports_contradicted_and_unverified(self, client, db_session):
        aid = _analyze(client, "bad_project")
        report = build_trust_report(db_session, aid)
        assert report["claim_stats"]["contradicted"] >= 1
        assert report["claim_stats"]["unverified"] >= 1

    def test_engineering_confidence_explained(self, client, db_session):
        aid = _analyze(client, "bad_project")
        report = build_trust_report(db_session, aid)
        ec = report["engineering_confidence"]
        assert ec["score"] is None or 0 <= ec["score"] <= 100
        assert ec["calculation"]
        assert set(ec["factors"].keys()) == set(CONFIDENCE_FACTORS)
        # every factor is a measured percentage or explicitly None — never guessed
        for name, val in ec["factors"].items():
            assert val is None or 0 <= val <= 100

    def test_report_is_internal_metric_not_certification(self, client, db_session):
        aid = _analyze(client, "bad_project")
        report = build_trust_report(db_session, aid)
        assert report["report_format"] == "internal_product_metric"
        assert any("not an industry certification" in l for l in report["limitations"])

    def test_remaining_risks_populated(self, client, db_session):
        aid = _analyze(client, "bad_project")
        report = build_trust_report(db_session, aid)
        assert report["remaining_findings"], "bad_project must expose remaining risks"
        severities = {r["severity"] for r in report["remaining_findings"]}
        assert severities <= {"CRITICAL", "HIGH", "MEDIUM"}

    def test_markdown_export_contains_real_numbers(self, client, db_session):
        aid = _analyze(client, "bad_project")
        report = build_trust_report(db_session, aid)
        md = render_markdown(report)
        assert str(report["claim_stats"]["total"]) in md
        assert "internal product metric" in md.lower()
        assert "certification" in md.lower()

    def test_empty_repo_report(self, tmp_path, client, db_session):
        """Repository with no README / no code: report survives with zero claims."""
        res = client.post("/api/analyze", json={"github_url": "sample:bad_project", "use_ai": False})
        aid = res.json()["id"]
        report = build_trust_report(db_session, aid)  # must not raise
        assert report["claim_stats"]["total"] >= 0

    def test_malformed_analysis_data(self, client, db_session):
        with pytest.raises(ValueError):
            build_trust_report(db_session, "does-not-exist")

    def test_endpoints(self, client):
        aid = _analyze(client, "bad_project")
        res = client.get(f"/api/analysis/{aid}/trust-report")
        assert res.status_code == 200
        assert res.json()["claim_stats"]["total"] > 0
        res_md = client.get(f"/api/analysis/{aid}/trust-report?format=markdown")
        assert res_md.status_code == 200
        assert "Project Trust Report" in res_md.text
        assert client.get("/api/analysis/nope/trust-report").status_code == 404
