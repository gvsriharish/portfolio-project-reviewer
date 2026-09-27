"""Phase 2 — Claim Auditor API endpoints.

All verdicts come from the deterministic ClaimAuditor. The reanalyze
endpoint re-runs that deterministic audit (fetching the repository again);
it never asks an LLM to decide claim truth.
"""
import uuid as _uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.findings import AnalysisRun, Finding
from backend.app.models.evidence import FindingEvidence
from backend.app.models.claims import Claim
from backend.app.schemas.analysis import FindingSchema
from backend.app.schemas.evidence import EvidenceItemSchema
from backend.app.schemas.claims import (
    ClaimSchema, ClaimStatsSchema, ClaimSummaryResponse, ReanalyzeResponse,
)
from backend.app.services.repo_fetcher import fetch_repository, RepositoryFetchError
from backend.app.analyzer.claims import ClaimAuditor
from backend.app.analyzer.base import FindingResult, EvidenceItem

router = APIRouter()

CONFIDENCE_ORDER = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}


def _stats(claims: List[Claim]) -> ClaimStatsSchema:
    return ClaimStatsSchema(
        total=len(claims),
        supported=sum(1 for c in claims if c.status == 'SUPPORTED'),
        partially_supported=sum(1 for c in claims if c.status == 'PARTIALLY_SUPPORTED'),
        unverified=sum(1 for c in claims if c.status == 'UNVERIFIED'),
        contradicted=sum(1 for c in claims if c.status == 'CONTRADICTED'),
    )


def _claim_schema(claim: Claim, db: Session, include_related: bool = True) -> ClaimSchema:
    related: List[FindingSchema] = []
    evidence: List[EvidenceItemSchema] = []
    if include_related:
        for f in claim.findings:
            related.append(FindingSchema(
                id=f.id, category=f.category, severity=f.severity, title=f.title,
                file_path=f.file_path, line_number=f.line_number, evidence=f.evidence,
                description=f.description, why_it_matters=f.why_it_matters,
                recommended_fix=f.recommended_fix, verification_method=f.verification_method,
            ))
        for ev in claim.evidence_items:
            evidence.append(EvidenceItemSchema(
                id=ev.id, finding_id=ev.finding_id, category=ev.category,
                source_file=ev.source_file, source_line=ev.source_line,
                evidence_type=ev.evidence_type, evidence_summary=ev.evidence_summary,
                confidence=ev.confidence, verification_status=ev.verification_status,
            ))
    return ClaimSchema(
        id=claim.id,
        claim_text=claim.claim_text,
        normalized_claim=claim.normalized_claim,
        source_file=claim.source_file,
        source_line=claim.source_line,
        category=claim.category,
        status=claim.status,
        confidence=claim.confidence,
        explanation=claim.explanation,
        evidence_count=claim.evidence_count,
        related_findings=related,
        evidence_items=evidence,
        created_at=claim.created_at,
    )


@router.get("/analysis/{analysis_id}/claims", response_model=ClaimSummaryResponse)
def list_claims(
    analysis_id: str,
    status: Optional[str] = None,
    category: Optional[str] = None,
    min_confidence: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first():
        raise HTTPException(status_code=404, detail="Analysis run not found")

    all_claims = db.query(Claim).filter(Claim.analysis_id == analysis_id).all()

    filtered = all_claims
    if status:
        filtered = [c for c in filtered if c.status == status.upper()]
    if category:
        filtered = [c for c in filtered if c.category == category.upper()]
    if min_confidence:
        floor = CONFIDENCE_ORDER.get(min_confidence.upper())
        filtered = [c for c in filtered if CONFIDENCE_ORDER.get(c.confidence, 0) >= floor]
    if search:
        needle = search.lower()
        filtered = [c for c in filtered if needle in c.claim_text.lower()]

    return ClaimSummaryResponse(
        stats=_stats(all_claims),
        claims=[_claim_schema(c, db, include_related=False) for c in filtered],
    )


@router.get("/analysis/{analysis_id}/claims/{claim_id}", response_model=ClaimSchema)
def get_claim(analysis_id: str, claim_id: str, db: Session = Depends(get_db)):
    claim = (
        db.query(Claim)
        .filter(Claim.id == claim_id, Claim.analysis_id == analysis_id)
        .first()
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found in this analysis")
    return _claim_schema(claim, db)


@router.get("/analysis/{analysis_id}/claims/{claim_id}/evidence", response_model=List[EvidenceItemSchema])
def get_claim_evidence(analysis_id: str, claim_id: str, db: Session = Depends(get_db)):
    claim = (
        db.query(Claim)
        .filter(Claim.id == claim_id, Claim.analysis_id == analysis_id)
        .first()
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found in this analysis")
    return [
        EvidenceItemSchema(
            id=ev.id, finding_id=ev.finding_id, category=ev.category,
            source_file=ev.source_file, source_line=ev.source_line,
            evidence_type=ev.evidence_type, evidence_summary=ev.evidence_summary,
            confidence=ev.confidence, verification_status=ev.verification_status,
        )
        for ev in claim.evidence_items
    ]


@router.post("/analysis/{analysis_id}/claims/reanalyze", response_model=ReanalyzeResponse)
def reanalyze_claims(analysis_id: str, db: Session = Depends(get_db)):
    """Re-run the deterministic claim audit for an existing analysis run."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")

    findings_rows = db.query(Finding).filter(Finding.analysis_id == analysis_id).all()
    evidence_rows = (
        db.query(FindingEvidence)
        .join(Finding, FindingEvidence.finding_id == Finding.id)
        .filter(Finding.analysis_id == analysis_id)
        .all()
    )

    # Rebuild the deterministic inputs from persisted rows.
    finding_results = [
        FindingResult(
            category=f.category, severity=f.severity, title=f.title,
            file_path=f.file_path, line_number=f.line_number, evidence=f.evidence,
            description=f.description, why_it_matters=f.why_it_matters,
            recommended_fix=f.recommended_fix, verification_method=f.verification_method,
        )
        for f in findings_rows
    ]
    finding_title_by_id = {f.id: f.title for f in findings_rows}
    evidence_items = [
        EvidenceItem(
            finding_title=finding_title_by_id.get(ev.finding_id, ''),
            category=ev.category, source_file=ev.source_file,
            evidence_type=ev.evidence_type, evidence_summary=ev.evidence_summary,
            confidence=ev.confidence, verification_status=ev.verification_status,
            source_line=ev.source_line,
        )
        for ev in evidence_rows
    ]

    try:
        with fetch_repository(run.repo_url) as workspace:
            claim_results = ClaimAuditor(workspace).audit(finding_results, evidence_items)
    except RepositoryFetchError as e:
        raise HTTPException(status_code=503, detail=f"Repository unavailable for re-analysis: {e}")

    # Replace previous claims for this run (association rows cascade).
    db.query(Claim).filter(Claim.analysis_id == analysis_id).delete()
    db.commit()

    evidence_model_by_index = {i: row for i, row in enumerate(evidence_rows)}
    finding_model_by_index = {i: row for i, row in enumerate(findings_rows)}

    for cr in claim_results:
        claim_row = Claim(
            id=str(_uuid.uuid4()),
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
            row = evidence_model_by_index.get(ev_i)
            if row is not None:
                claim_row.evidence_items.append(row)
        for f_i in cr.finding_indices:
            row = finding_model_by_index.get(f_i)
            if row is not None:
                claim_row.findings.append(row)
        db.add(claim_row)
    db.commit()

    stored = db.query(Claim).filter(Claim.analysis_id == analysis_id).all()
    return ReanalyzeResponse(analysis_id=analysis_id, claims_extracted=len(stored), stats=_stats(stored))
