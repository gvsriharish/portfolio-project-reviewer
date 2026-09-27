"""Phase 3 — Engineering Evidence Graph.

Assembles the traceable relationship chain

    AnalysisRun → Claim → EvidenceItem → Finding → Recommendation → VerificationResult

from the existing relational models. No graph database: plain foreign
keys / association tables, joined here into a JSON-serializable graph.
Only real, persisted relationships are emitted.
"""
from typing import Dict, List, Any

from sqlalchemy.orm import Session

from backend.app.models.findings import AnalysisRun, Finding, Recommendation
from backend.app.models.evidence import FindingEvidence
from backend.app.models.claims import Claim
from backend.app.models.verification import VerificationResult


def build_evidence_graph(db: Session, analysis_id: str) -> Dict[str, Any]:
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()

    findings = db.query(Finding).filter(Finding.analysis_id == analysis_id).all()
    evidence_rows = (
        db.query(FindingEvidence)
        .join(Finding, FindingEvidence.finding_id == Finding.id)
        .filter(Finding.analysis_id == analysis_id)
        .all()
    )
    claims = db.query(Claim).filter(Claim.analysis_id == analysis_id).all()
    recommendations = (
        db.query(Recommendation).filter(Recommendation.analysis_id == analysis_id).all()
    )
    verifications = (
        db.query(VerificationResult)
        .filter(VerificationResult.analysis_id == analysis_id)
        .all()
    )

    finding_ids = {f.id for f in findings}
    evidence_ids = {e.id for e in evidence_rows}

    # Claim → evidence / finding edges (via association tables). Only rows
    # belonging to this analysis can appear (claims are analysis-scoped).
    claim_evidence_edges = []
    claim_finding_edges = []
    for c in claims:
        for ev in c.evidence_items:
            if ev.id in evidence_ids:
                claim_evidence_edges.append({'claim_id': c.id, 'evidence_id': ev.id})
        for f in c.findings:
            if f.id in finding_ids:
                claim_finding_edges.append({'claim_id': c.id, 'finding_id': f.id})

    # Evidence → finding edges.
    evidence_finding_edges = [
        {'evidence_id': e.id, 'finding_id': e.finding_id}
        for e in evidence_rows if e.finding_id in finding_ids
    ]

    # Finding → recommendation edges (finding-backed recommendations only).
    finding_recommendation_edges = [
        {'finding_id': r.finding_id, 'recommendation_id': r.id}
        for r in recommendations if r.finding_id and r.finding_id in finding_ids
    ]

    # Recommendation → verification edges.
    rec_ids = {r.id for r in recommendations}
    recommendation_verification_edges = [
        {'recommendation_id': v.recommendation_id, 'verification_id': v.id}
        for v in verifications
        if v.recommendation_id in rec_ids
    ]

    return {
        'analysis_id': analysis_id,
        'run': {
            'id': run.id,
            'repo_url': run.repo_url,
            'repo_name': run.repo_name,
            'status': run.status,
            'overall_score': run.overall_score,
            'created_at': run.created_at,
        } if run else None,
        'nodes': {
            'claims': [
                {
                    'id': c.id, 'claim_text': c.claim_text, 'category': c.category,
                    'status': c.status, 'confidence': c.confidence,
                    'source_file': c.source_file, 'source_line': c.source_line,
                }
                for c in claims
            ],
            'evidence': [
                {
                    'id': e.id, 'evidence_type': e.evidence_type,
                    'source_file': e.source_file, 'source_line': e.source_line,
                    'evidence_summary': e.evidence_summary,
                    'confidence': e.confidence, 'verification_status': e.verification_status,
                    'finding_key': e.finding_key,
                }
                for e in evidence_rows
            ],
            'findings': [
                {
                    'id': f.id, 'finding_key': f.finding_key, 'title': f.title,
                    'category': f.category, 'severity': f.severity,
                    'file_path': f.file_path, 'line_number': f.line_number,
                }
                for f in findings
            ],
            'recommendations': [
                {
                    'id': r.id, 'title': r.title, 'action': r.action,
                    'reason': r.reason, 'verification': r.verification,
                    'status': r.status, 'finding_id': r.finding_id,
                }
                for r in recommendations
            ],
            'verifications': [
                {
                    'id': v.id, 'finding_key': v.finding_key, 'method': v.method,
                    'result': v.result, 'details': v.details,
                    'recommendation_id': v.recommendation_id,
                }
                for v in verifications
            ],
        },
        'edges': {
            'claim_evidence': claim_evidence_edges,
            'claim_finding': claim_finding_edges,
            'evidence_finding': evidence_finding_edges,
            'finding_recommendation': finding_recommendation_edges,
            'recommendation_verification': recommendation_verification_edges,
        },
        'counts': {
            'claims': len(claims),
            'evidence': len(evidence_rows),
            'findings': len(findings),
            'recommendations': len(recommendations),
            'verifications': len(verifications),
        },
    }
