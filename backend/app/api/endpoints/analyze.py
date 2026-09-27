import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from backend.app.database.session import get_db, SessionLocal
from backend.app.models.findings import AnalysisRun, Finding, Recommendation, InterviewQuestion, ProjectExplanation
from backend.app.models.evidence import FindingEvidence
from backend.app.models.verification import VerificationResult
from backend.app.models.claims import Claim, claim_evidence_links, claim_finding_links
from backend.app.schemas.analysis import (
    AnalyzeRequest, AnalysisResponse, FindingSchema, CategoryScoreSchema,
    ComparisonResponse, CategoryDeltaSchema, RecommendationSchema, VerificationResultSchema,
    InterviewQuestionSchema, ProjectExplanationSchema
)
from backend.app.schemas.evidence import EvidenceItemSchema
from backend.app.services.repo_fetcher import fetch_repository, parse_github_url, RepositoryFetchError
from backend.app.analyzer.orchestrator import AnalysisOrchestrator
from backend.app.analyzer.finding_keys import compute_finding_key
from backend.app.analyzer.claims import ClaimAuditor
from backend.app.ai.service import AIReasoningService
from backend.app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

def persist_deterministic_artifacts(db: Session, analysis_id: str, workspace, analysis_results: dict) -> int:
    """Persist findings, evidence and audited claims for an analysis run.

    Deterministic only — called before any AI processing. Returns the number
    of claims extracted. Evidence and claims relate to findings via the
    stable finding_key (titles are not unique).
    """
    from backend.app.models.claims import Claim

    assigned_keys: List[str] = []
    title_to_keys: dict = {}
    finding_rows: List[Finding] = []
    for f in analysis_results['findings']:
        fkey = compute_finding_key(f, assigned_keys)
        assigned_keys.append(fkey)
        title_to_keys.setdefault(f.title, []).append(fkey)
        finding_db = Finding(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            category=f.category,
            severity=f.severity,
            title=f.title,
            file_path=f.file_path,
            line_number=f.line_number,
            evidence=f.evidence,
            description=f.description,
            why_it_matters=f.why_it_matters,
            recommended_fix=f.recommended_fix,
            verification_method=f.verification_method,
            finding_key=fkey,
        )
        db.add(finding_db)
        finding_rows.append(finding_db)

    # Persist structured evidence items — deterministic analyzers only,
    # before the AI block. Each EvidenceItem links to the first finding
    # with a matching title (FIFO), same correlation as Phase 1, but the
    # stable finding_key is stored for cross-run traceability. Orphaned
    # evidence (no matching finding) is skipped, as in Phase 1.
    evidence_rows: List[FindingEvidence] = []
    used_keys: dict = {}
    for ev in analysis_results.get('evidence_items', []):
        keys = title_to_keys.get(ev.finding_title, [])
        if not keys:
            continue  # orphaned evidence — skip safely
        idx = used_keys.get(ev.finding_title, 0)
        fkey = keys[min(idx, len(keys) - 1)]
        used_keys[ev.finding_title] = idx + 1
        ev_row = FindingEvidence(
            id=str(uuid.uuid4()),
            finding_id=next(fr.id for fr in finding_rows if fr.finding_key == fkey),
            finding_key=fkey,
            category=ev.category,
            source_file=ev.source_file,
            source_line=ev.source_line,
            evidence_type=ev.evidence_type,
            evidence_summary=ev.evidence_summary,
            confidence=ev.confidence,
            verification_status=ev.verification_status,
        )
        db.add(ev_row)
        evidence_rows.append(ev_row)

    db.commit()

    # ------------------------------------------------------------------
    # Phase 2 — Project Claim Auditor (deterministic, before any AI).
    # README/documentation are untrusted data: pattern-scanned only.
    # ------------------------------------------------------------------
    claim_results = ClaimAuditor(workspace).audit(
        analysis_results['findings'], analysis_results.get('evidence_items', [])
    )

    evidence_by_index = {i: row for i, row in enumerate(evidence_rows)}
    finding_by_index = {i: row for i, row in enumerate(finding_rows)}

    for cr in claim_results:
        claim_row = Claim(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            claim_text=cr.claim_text,
            normalized_claim=cr.normalized_claim,
            source_file=cr.source_file or '',
            source_line=cr.source_line,
            category=cr.category,
            status=cr.status,
            confidence=cr.confidence,
            explanation=cr.explanation,
            evidence_count=len(cr.evidence_indices),
        )
        for ev_i in cr.evidence_indices:
            ev_row = evidence_by_index.get(ev_i)
            if ev_row is not None:
                claim_row.evidence_items.append(ev_row)
        for f_i in cr.finding_indices:
            f_row = finding_by_index.get(f_i)
            if f_row is not None:
                claim_row.findings.append(f_row)
        db.add(claim_row)
    db.commit()
    return len(claim_results)


def run_analysis_task(analysis_id: str, repo_url: str, use_ai: bool):
    db: Session = SessionLocal()
    try:
        run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
        if not run:
            return

        run.status = "FETCHING"
        run.current_stage = "Fetching and validating repository..."
        run.progress_percent = 10
        db.commit()

        with fetch_repository(repo_url) as workspace:
            run.repo_name = workspace.repo_name
            run.owner = workspace.owner
            run.is_sample = workspace.is_sample
            run.status = "SCANNING"
            run.current_stage = "Scanning repository files..."
            run.progress_percent = 25
            db.commit()

            def progress_cb(stage: str, percent: int):
                try:
                    run.current_stage = stage
                    run.progress_percent = percent
                    db.commit()
                except Exception:
                    pass

            orchestrator = AnalysisOrchestrator()
            analysis_results = orchestrator.run_full_analysis(workspace, progress_callback=progress_cb)

            run.languages = analysis_results['languages']
            run.frameworks = analysis_results['frameworks']
            run.architecture_summary = analysis_results['architecture_summary']
            run.metrics = analysis_results.get('metrics', {})
            run.overall_score = analysis_results['overall_score']
            run.category_scores = analysis_results['category_scores']
            run.duration_seconds = analysis_results['duration_seconds']

            # Deterministic artifacts: findings + evidence + audited claims.
            # Evidence and claims relate to findings via the stable finding_key
            # (titles are not unique) with in-run collision suffixes.
            run.status = "AUDITING_CLAIMS"
            run.current_stage = "Auditing documentation claims against repository evidence..."
            run.progress_percent = 85
            db.commit()
            persist_deterministic_artifacts(db, analysis_id, workspace, analysis_results)
            finding_rows = db.query(Finding).filter(Finding.analysis_id == analysis_id).all()

            if use_ai:
                run.status = "AI_PROCESSING"
                run.current_stage = "Generating grounded AI recommendations & interview prep..."
                run.progress_percent = 90
                db.commit()

                ai_service = AIReasoningService()
                ai_data = ai_service.generate_ai_enhancements(
                    repo_name=run.repo_name,
                    languages=run.languages,
                    frameworks=run.frameworks,
                    findings=analysis_results['findings'],
                    architecture_summary=run.architecture_summary
                )

                # AI can explain/prioritize, but it cannot invent the
                # relationship. A recommendation is finding-backed only when
                # its returned finding_key exactly matches deterministic data
                # from this analysis.
                finding_by_key = {f.finding_key: f for f in finding_rows if f.finding_key}
                for rec in ai_data.get('recommendations', []):
                    rec_finding = finding_by_key.get(rec.get('finding_key'))
                    db.add(Recommendation(
                        id=str(uuid.uuid4()),
                        analysis_id=analysis_id,
                        priority_group=rec.get('priority_group', 'Improve Next'),
                        rank=rec.get('rank', 1),
                        title=rec.get('title', ''),
                        action=rec.get('action', ''),
                        reason=rec.get('reason', ''),
                        verification=rec.get('verification', ''),
                        finding_id=rec_finding.id if rec_finding else None,
                        expected_change=rec.get('expected_change', ''),
                        status='OPEN'
                    ))

                for q in ai_data.get('interview_questions', []):
                    db.add(InterviewQuestion(
                        id=str(uuid.uuid4()),
                        analysis_id=analysis_id,
                        level=q.get('level', 'Beginner'),
                        category=q.get('category', 'Architecture'),
                        question=q.get('question', ''),
                        context_reason=q.get('context_reason', ''),
                        sample_answer_guideline=q.get('sample_answer_guideline', '')
                    ))

                pe = ai_data.get('project_explanation', {})
                if pe:
                    db.add(ProjectExplanation(
                        id=str(uuid.uuid4()),
                        analysis_id=analysis_id,
                        summary=pe.get('summary', ''),
                        architecture_narrative=pe.get('architecture_narrative', ''),
                        main_components=pe.get('main_components', []),
                        data_flow=pe.get('data_flow', []),
                        key_files=pe.get('key_files', []),
                        technical_decisions=pe.get('technical_decisions', []),
                        limitations=pe.get('limitations', [])
                    ))

                db.commit()

            run.status = "COMPLETED"
            run.current_stage = "Analysis complete!"
            run.progress_percent = 100
            db.commit()

    except Exception:
        logger.exception("Analysis task failed for run %s", analysis_id)
        db.rollback()
        run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
        if run:
            run.status = "FAILED"
            run.error_message = "Analysis failed. Confirm the repository is public and try again."
            run.current_stage = "Analysis failed"
            db.commit()
    finally:
        db.close()

def format_analysis_response(run: AnalysisRun, db: Session) -> AnalysisResponse:
    findings = db.query(Finding).filter(Finding.analysis_id == run.id).all()
    recommendations = db.query(Recommendation).filter(Recommendation.analysis_id == run.id).order_by(Recommendation.rank).all()
    questions = db.query(InterviewQuestion).filter(InterviewQuestion.analysis_id == run.id).all()
    explanation = db.query(ProjectExplanation).filter(ProjectExplanation.analysis_id == run.id).first()

    cat_scores_formatted = {}
    if run.category_scores:
        for cat, data in run.category_scores.items():
            cat_scores_formatted[cat] = CategoryScoreSchema(
                category=cat,
                score=data.get('score', 0),
                max_score=data.get('max_score', 100),
                findings_count=data.get('findings_count', 0),
                severity_counts=data.get('severity_counts', {}),
                penalty_breakdown=data.get('penalty_breakdown', []),
                summary=data.get('summary', '')
            )

    explanation_schema = None
    if explanation:
        explanation_schema = ProjectExplanationSchema(
            summary=explanation.summary,
            architecture_narrative=explanation.architecture_narrative,
            main_components=explanation.main_components or [],
            data_flow=explanation.data_flow or [],
            key_files=explanation.key_files or [],
            technical_decisions=explanation.technical_decisions or [],
            limitations=explanation.limitations or []
        )

    return AnalysisResponse(
        id=run.id,
        repo_url=run.repo_url,
        repo_name=run.repo_name,
        owner=run.owner,
        status=run.status,
        current_stage=run.current_stage,
        progress_percent=run.progress_percent,
        overall_score=run.overall_score,
        category_scores=cat_scores_formatted,
        languages=run.languages or [],
        frameworks=run.frameworks or [],
        architecture_summary=run.architecture_summary or {},
        findings=[
            FindingSchema(
                id=f.id, category=f.category, severity=f.severity, title=f.title,
                file_path=f.file_path, line_number=f.line_number, evidence=f.evidence,
                description=f.description, why_it_matters=f.why_it_matters,
                recommended_fix=f.recommended_fix, verification_method=f.verification_method
            )
            for f in findings
        ],
        recommendations=[
            RecommendationSchema(
                id=r.id, priority_group=r.priority_group, rank=r.rank,
                title=r.title, action=r.action, reason=r.reason, verification=r.verification,
                finding_id=r.finding_id, status=r.status, expected_change=r.expected_change
            )
            for r in recommendations
        ],
        interview_questions=[
            InterviewQuestionSchema(
                id=q.id, level=q.level, category=q.category, question=q.question,
                context_reason=q.context_reason, sample_answer_guideline=q.sample_answer_guideline
            )
            for q in questions
        ],
        project_explanation=explanation_schema,
        duration_seconds=run.duration_seconds,
        error_message=run.error_message,
        is_sample=run.is_sample,
        created_at=run.created_at
    )

@router.post("/analyze", response_model=AnalysisResponse)
def analyze_repository(
    req: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    analysis_id = str(uuid.uuid4())
    owner, repo = parse_github_url(req.github_url)

    new_run = AnalysisRun(
        id=analysis_id,
        repo_url=req.github_url,
        repo_name=repo,
        owner=owner,
        status="QUEUED",
        current_stage="Queued for analysis...",
        progress_percent=0,
        is_sample=(owner == 'sample')
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    # In tests or requests, execute analysis
    background_tasks.add_task(run_analysis_task, analysis_id, req.github_url, req.use_ai)

    return format_analysis_response(new_run, db)

# STATIC ROUTES MUST PRECEDE PARAMETERIZED ROUTES
@router.get("/analysis/compare", response_model=ComparisonResponse)
def compare_analyses(
    before_id: str = Query(..., description="ID of the earlier analysis run"),
    after_id: str = Query(..., description="ID of the subsequent analysis run"),
    db: Session = Depends(get_db)
):
    before_run = db.query(AnalysisRun).filter(AnalysisRun.id == before_id).first()
    after_run = db.query(AnalysisRun).filter(AnalysisRun.id == after_id).first()

    if not before_run or not after_run:
        raise HTTPException(status_code=404, detail="One or both analysis runs not found")

    before_findings = db.query(Finding).filter(Finding.analysis_id == before_id).all()
    after_findings = db.query(Finding).filter(Finding.analysis_id == after_id).all()

    from backend.app.services.finding_comparison import compare_findings
    from backend.app.services.improvement import verify_recommendations
    resolved_d, persistent_d, new_d, changed_d = compare_findings(before_findings, after_findings)

    def delta_schema(d):
        source = next((f for f in (before_findings + after_findings)
                       if f.id in (d.before_id, d.after_id)), None)
        if source is None:
            raise HTTPException(status_code=500, detail="Comparison source finding missing")
        return _finding_schema_plain(
            source,
            status=d.status,
            finding_key=d.finding_key,
            before_severity=d.before_severity,
            after_severity=d.after_severity,
            before_id=d.before_id,
            after_id=d.after_id,
            match_method=d.match_method,
        )

    verification_rows = verify_recommendations(db, before_id, after_id)
    category_deltas = {}
    before_cats = before_run.category_scores or {}
    after_cats = after_run.category_scores or {}

    for cat in sorted(set(before_cats) | set(after_cats)):
        b_score = before_cats.get(cat, {}).get('score', 0)
        a_score = after_cats.get(cat, {}).get('score', 0)
        b_count = before_cats.get(cat, {}).get('findings_count', 0)
        a_count = after_cats.get(cat, {}).get('findings_count', 0)
        category_deltas[cat] = CategoryDeltaSchema(
            category=cat, before_score=b_score, after_score=a_score,
            delta=a_score - b_score, findings_before=b_count, findings_after=a_count
        )

    score_delta = after_run.overall_score - before_run.overall_score
    summary_text = (
        f"Score changed from {before_run.overall_score} to {after_run.overall_score}. "
        f"{len(resolved_d)} finding(s) resolved, {len(persistent_d)} still present, "
        f"{len(new_d)} new, {len(changed_d)} changed. "
        "Score change alone is not proof of improvement."
    )

    return ComparisonResponse(
        before_id=before_id,
        after_id=after_id,
        before_repo=f"{before_run.owner}/{before_run.repo_name}",
        after_repo=f"{after_run.owner}/{after_run.repo_name}",
        overall_score_before=before_run.overall_score,
        overall_score_after=after_run.overall_score,
        overall_score_delta=score_delta,
        category_deltas=category_deltas,
        resolved_findings=[delta_schema(d) for d in resolved_d],
        new_findings=[delta_schema(d) for d in new_d],
        persistent_findings=[delta_schema(d) for d in persistent_d],
        changed_findings=[delta_schema(d) for d in changed_d],
        verification_results=[
            VerificationResultSchema(
                id=v.id, finding_key=v.finding_key, method=v.method,
                result=v.result, details=v.details, recommendation_id=v.recommendation_id
            ) for v in verification_rows
        ],
        summary=summary_text
    )

@router.get("/analysis/improvement")
def get_improvement_report(
    before_id: str = Query(..., description="ID of the earlier analysis run"),
    after_id: str = Query(..., description="ID of the subsequent analysis run"),
    db: Session = Depends(get_db)
):
    """Phase 4 — Proof of Improvement: evidence-backed before/after report."""
    from backend.app.services.improvement import build_improvement_report
    try:
        return build_improvement_report(db, before_id, after_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/self-analysis", response_model=AnalysisResponse)
def trigger_self_analysis(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    req = AnalyzeRequest(github_url="local:.", use_ai=True)
    return analyze_repository(req, background_tasks, db)

@router.get("/analysis/{analysis_id}/verifications", response_model=List[VerificationResultSchema])
def get_analysis_verifications(analysis_id: str, db: Session = Depends(get_db)):
    """Return deterministic verification results scoped to one analysis."""
    if not db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first():
        raise HTTPException(status_code=404, detail="Analysis run not found")
    rows = db.query(VerificationResult).filter(
        VerificationResult.analysis_id == analysis_id
    ).order_by(VerificationResult.created_at.asc()).all()
    return [
        VerificationResultSchema(
            id=v.id, finding_key=v.finding_key, method=v.method,
            result=v.result, details=v.details, recommendation_id=v.recommendation_id
        ) for v in rows
    ]


# PARAMETERIZED ROUTES
@router.get("/analysis/{analysis_id}", response_model=AnalysisResponse)
def get_analysis_status(analysis_id: str, db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return format_analysis_response(run, db)

def _finding_to_schema(f: Finding, db: Session, include_evidence: bool = False) -> FindingSchema:
    """Convert a Finding ORM row to a FindingSchema, optionally embedding evidence."""
    ev_schemas = []
    if include_evidence:
        ev_rows = db.query(FindingEvidence).filter(FindingEvidence.finding_id == f.id).all()
        ev_schemas = [
            EvidenceItemSchema(
                id=ev.id,
                finding_id=ev.finding_id,
                category=ev.category,
                source_file=ev.source_file,
                source_line=ev.source_line,
                evidence_type=ev.evidence_type,
                evidence_summary=ev.evidence_summary,
                confidence=ev.confidence,
                verification_status=ev.verification_status,
            )
            for ev in ev_rows
        ]
    return FindingSchema(
        id=f.id,
        category=f.category,
        severity=f.severity,
        title=f.title,
        finding_key=f.finding_key,
        file_path=f.file_path,
        line_number=f.line_number,
        evidence=f.evidence,
        description=f.description,
        why_it_matters=f.why_it_matters,
        recommended_fix=f.recommended_fix,
        verification_method=f.verification_method,
        evidence_items=ev_schemas,
    )


@router.get("/analysis/{analysis_id}/findings", response_model=List[FindingSchema])
def get_analysis_findings(
    analysis_id: str,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    include_evidence: bool = Query(False, description="Embed structured evidence items in each finding"),
    db: Session = Depends(get_db)
):
    query = db.query(Finding).filter(Finding.analysis_id == analysis_id)
    if category:
        query = query.filter(Finding.category == category)
    if severity:
        query = query.filter(Finding.severity == severity.upper())

    findings = query.all()
    return [
        _finding_to_schema(f, db, include_evidence=include_evidence)
        for f in findings
    ]


# Keep the original inline schema builder for comparison endpoint (no evidence needed there).
def _finding_schema_plain(
    f: Finding,
    status: Optional[str] = None,
    finding_key: Optional[str] = None,
    before_severity: Optional[str] = None,
    after_severity: Optional[str] = None,
    before_id: Optional[str] = None,
    after_id: Optional[str] = None,
    match_method: Optional[str] = None,
) -> FindingSchema:
    return FindingSchema(
        id=f.id,
        category=f.category,
        severity=f.severity,
        title=f.title,
        finding_key=finding_key if finding_key is not None else f.finding_key,
        status=status,
        before_severity=before_severity,
        after_severity=after_severity,
        before_id=before_id,
        after_id=after_id,
        match_method=match_method,
        file_path=f.file_path,
        line_number=f.line_number,
        evidence=f.evidence,
        description=f.description,
        why_it_matters=f.why_it_matters,
        recommended_fix=f.recommended_fix,
        verification_method=f.verification_method,
    )
