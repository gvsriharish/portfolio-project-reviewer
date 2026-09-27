
import uuid
from backend.app.models.findings import AnalysisRun, Finding, Recommendation
from backend.app.services.finding_comparison import compare_findings
from backend.app.services.improvement import verify_recommendations


def make_run(db, repo, score=50):
    rid = str(uuid.uuid4())
    db.add(AnalysisRun(
        id=rid, repo_url=f"sample:{repo}", repo_name=repo, owner="sample",
        status="COMPLETED", overall_score=score,
        category_scores={"Security": {"score": score, "findings_count": 1}},
    ))
    db.commit()
    return rid


def make_finding(db, aid, key, title, severity="HIGH"):
    f = Finding(
        id=str(uuid.uuid4()), analysis_id=aid, category="Security",
        severity=severity, title=title, file_path="app/config.py",
        evidence="deterministic", description="d", why_it_matters="w",
        recommended_fix="fix", verification_method="re-analyze", finding_key=key,
    )
    db.add(f)
    db.commit()
    return f


def test_duplicate_titles_do_not_merge_when_keys_differ():
    class F:
        def __init__(self, key):
            self.finding_key = key
            self.title = "Configuration Issue"
            self.category = "Security"
            self.severity = "HIGH"
            self.id = key
    before = [F("security.rule.a"), F("security.rule.b")]
    after = [F("security.rule.a"), F("security.rule.c")]
    resolved, still, new, changed = compare_findings(before, after)
    assert {x.finding_key for x in resolved} == {"security.rule.b"}
    assert {x.finding_key for x in still} == {"security.rule.a"}
    assert {x.finding_key for x in new} == {"security.rule.c"}


def test_verification_pass_fail_and_recommendation_status(db_session):
    before_id = make_run(db_session, "before")
    after_id = make_run(db_session, "after")
    make_finding(db_session, after_id, "security.secret.config", "Hardcoded Secret")
    before = make_finding(db_session, before_id, "security.secret.config", "Hardcoded Secret")
    rec = Recommendation(
        id=str(uuid.uuid4()), analysis_id=before_id, priority_group="Fix First",
        rank=1, title="Remove secret", action="Move to env",
        reason="secret risk", verification="re-analyze",
        finding_id=before.id, status="OPEN", expected_change="finding disappears",
    )
    db_session.add(rec)
    db_session.commit()

    # Finding remains -> FAIL and STILL_PRESENT.
    rows = verify_recommendations(db_session, before_id, after_id)
    assert rows[0].result == "FAIL"
    assert rec.status == "STILL_PRESENT"

    # New after run without the finding -> PASS and RESOLVED.
    after2_id = make_run(db_session, "after2")
    rows = verify_recommendations(db_session, before_id, after2_id)
    assert rows[0].result == "PASS"
    assert rec.status == "RESOLVED"


def test_end_to_end_sample_story(db_session):
    """Exercise the central evidence chain on the real bundled sample projects."""
    from backend.app.analyzer.orchestrator import AnalysisOrchestrator
    from backend.app.services.repo_fetcher import fetch_repository
    from backend.app.api.endpoints.analyze import persist_deterministic_artifacts
    from backend.app.services.graph_builder import build_evidence_graph
    from backend.app.services.improvement import build_improvement_report
    from backend.app.services.trust_report import build_trust_report
    from backend.app.models.claims import Claim

    ids = []
    for sample in ("bad_project", "improved_project"):
        with fetch_repository("sample:" + sample) as ws:
            results = AnalysisOrchestrator().run_full_analysis(ws)
            aid = str(uuid.uuid4())
            ids.append(aid)
            db_session.add(AnalysisRun(
                id=aid, repo_url="sample:" + sample, repo_name=sample, owner="sample",
                status="COMPLETED", overall_score=results["overall_score"],
                category_scores=results["category_scores"], languages=results["languages"],
                frameworks=results["frameworks"], architecture_summary=results["architecture_summary"],
                metrics=results.get("metrics", {}),
            ))
            db_session.commit()
            persist_deterministic_artifacts(db_session, aid, ws, results)

    before_id, after_id = ids
    before_finding = db_session.query(Finding).filter(
        Finding.analysis_id == before_id,
        Finding.finding_key == "testing.zero-automated-tests-in-repository.tests",
    ).first()
    assert before_finding is not None

    db_session.add(Recommendation(
        id=str(uuid.uuid4()), analysis_id=before_id, priority_group="Fix First",
        rank=1, title="Add automated tests", action="Create tests",
        reason="Improve regression protection", verification="Re-run deterministic testing analysis",
        finding_id=before_finding.id, expected_change="Zero Automated Tests finding disappears",
    ))
    db_session.commit()

    rows = verify_recommendations(db_session, before_id, after_id)
    assert any(v.result == "PASS" for v in rows)

    report = build_improvement_report(db_session, before_id, after_id)
    assert report["findings"]["resolved"]
    assert report["score"]["note"].startswith("Score delta alone is NOT proof")

    graph = build_evidence_graph(db_session, after_id)
    assert graph["counts"]["claims"] >= 1
    assert graph["counts"]["evidence"] >= 1
    assert set(graph["edges"]) == {
        "claim_evidence", "claim_finding", "evidence_finding",
        "finding_recommendation", "recommendation_verification",
    }

    trust = build_trust_report(db_session, after_id)
    assert "engineering_confidence" in trust
    assert "proof_of_improvement" in trust
    assert trust["limitations"]
