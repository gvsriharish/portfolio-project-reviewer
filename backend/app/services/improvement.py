"""Phase 4 — Proof of Improvement.

Compares two analysis runs and produces an evidence-backed account of
WHAT changed and WHY. Every metric is computed from stored analysis data;
when a change cannot be measured reliably the delta is reported as
"Change could not be verified." — never fabricated. Improvement is never
inferred from the overall score alone.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.models.findings import AnalysisRun, Finding, Recommendation
from backend.app.models.evidence import FindingEvidence
from backend.app.models.claims import Claim
from backend.app.models.verification import VerificationResult
from datetime import datetime, timezone
from backend.app.services.finding_comparison import compare_findings, FindingDelta


def _finding_dict(f: Finding) -> Dict[str, Any]:
    return {
        'id': f.id, 'finding_key': f.finding_key, 'title': f.title,
        'category': f.category, 'severity': f.severity,
        'file_path': f.file_path, 'line_number': f.line_number,
    }


def _delta_dict(d: FindingDelta) -> Dict[str, Any]:
    return {
        'finding_key': d.finding_key, 'status': d.status, 'category': d.category,
        'title': d.title, 'before_severity': d.before_severity,
        'after_severity': d.after_severity, 'before_id': d.before_id,
        'after_id': d.after_id, 'match_method': d.match_method,
    }


def _test_file_count(db: Session, analysis_id: str) -> Optional[int]:
    """Read the deterministic test-file metric; never infer coverage from it."""
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if run and run.metrics and 'test_file_count' in run.metrics:
        return int(run.metrics['test_file_count'])
    rows = (
        db.query(FindingEvidence)
        .join(Finding, FindingEvidence.finding_id == Finding.id)
        .filter(Finding.analysis_id == analysis_id, Finding.category == 'Testing')
        .all()
    )
    test_rows = [
        r for r in rows
        if r.evidence_type in ('FILE_MATCH', 'FILE_COUNT') and 'test' in (r.source_file or '').lower() + r.evidence_summary.lower()
    ]
    if not rows and not test_rows:
        return None
    return len(test_rows) if test_rows else None


def _claim_stats(claims: List[Claim]) -> Dict[str, int]:
    return {
        'total': len(claims),
        'supported': sum(1 for c in claims if c.status == 'SUPPORTED'),
        'partially_supported': sum(1 for c in claims if c.status == 'PARTIALLY_SUPPORTED'),
        'unverified': sum(1 for c in claims if c.status == 'UNVERIFIED'),
        'contradicted': sum(1 for c in claims if c.status == 'CONTRADICTED'),
    }


def _claim_changes(before_claims: List[Claim], after_claims: List[Claim]) -> List[Dict[str, Any]]:
    before_map = {c.normalized_claim: c for c in before_claims}
    after_map = {c.normalized_claim: c for c in after_claims}
    changes = []
    for key, after in after_map.items():
        before = before_map.get(key)
        if before is None:
            changes.append({
                'claim_text': after.claim_text, 'category': after.category,
                'before_status': None, 'after_status': after.status,
                'change': 'NEW_CLAIM', 'verified': after.status is not None,
            })
        elif before.status != after.status:
            changes.append({
                'claim_text': after.claim_text, 'category': after.category,
                'before_status': before.status, 'after_status': after.status,
                'change': 'STATUS_CHANGED', 'verified': True,
            })
    for key, before in before_map.items():
        if key not in after_map:
            changes.append({
                'claim_text': before.claim_text, 'category': before.category,
                'before_status': before.status, 'after_status': None,
                'change': 'REMOVED_CLAIM', 'verified': True,
            })
    return changes


def _metric(before_value, after_value, unit: str = '') -> Dict[str, Any]:
    verified = before_value is not None and after_value is not None
    delta = (after_value - before_value) if verified else None
    return {
        'before': before_value,
        'after': after_value,
        'delta': delta,
        'verified': verified,
        'display': (
            f'{before_value} → {after_value}{unit} ({delta:+d}{unit})'
            if verified else 'Change could not be verified.'
        ),
    }



def verify_recommendations(db: Session, before_id: str, after_id: str) -> List[VerificationResult]:
    """Create deterministic VerificationResult rows for finding-backed recommendations.

    A PASS means the finding key disappeared from the after run. A FAIL means it
    remains (including severity changes). UNVERIFIED is used when a deterministic
    condition cannot be evaluated. Overall score is never used as verification.
    """
    before_recs = (
        db.query(Recommendation)
        .filter(Recommendation.analysis_id == before_id, Recommendation.finding_id.isnot(None))
        .all()
    )
    if not before_recs:
        return []

    before_findings = db.query(Finding).filter(Finding.analysis_id == before_id).all()
    after_findings = db.query(Finding).filter(Finding.analysis_id == after_id).all()
    after_by_key = {f.finding_key: f for f in after_findings if f.finding_key}

    # Avoid duplicate verification rows if comparison is requested repeatedly.
    existing = db.query(VerificationResult).filter(VerificationResult.analysis_id == after_id).all()
    existing_by_rec = {v.recommendation_id: v for v in existing if v.recommendation_id}

    results = []
    for rec in before_recs:
        if rec.id in existing_by_rec:
            results.append(existing_by_rec[rec.id])
            continue
        before_f = next((f for f in before_findings if f.id == rec.finding_id), None)
        if not before_f or not before_f.finding_key:
            result, details, method = (
                'UNVERIFIED',
                'The recommendation is linked to a legacy finding without a stable finding_key.',
                'Stable finding key unavailable',
            )
        elif before_f.finding_key not in after_by_key:
            result, details, method = (
                'PASS',
                f"Finding key '{before_f.finding_key}' is absent from the after-analysis findings.",
                'Finding key absent from after analysis',
            )
        else:
            after_f = after_by_key[before_f.finding_key]
            result, details, method = (
                'FAIL',
                f"Finding key remains in the after analysis (severity {before_f.severity} -> {after_f.severity}).",
                'Finding key remains in after analysis',
            )
        row = VerificationResult(
            id=str(__import__('uuid').uuid4()),
            analysis_id=after_id,
            recommendation_id=rec.id,
            finding_key=before_f.finding_key if before_f else 'unknown',
            method=method,
            result=result,
            details=details,
        )
        # Evidence-derived lifecycle; users cannot falsely mark resolution.
        rec.status = {'PASS': 'RESOLVED', 'FAIL': 'STILL_PRESENT'}.get(result, 'UNVERIFIED')
        db.add(row)
        results.append(row)
    db.commit()
    return results

def build_improvement_report(db: Session, before_id: str, after_id: str) -> Dict[str, Any]:
    before_run = db.query(AnalysisRun).filter(AnalysisRun.id == before_id).first()
    after_run = db.query(AnalysisRun).filter(AnalysisRun.id == after_id).first()
    if not before_run or not after_run:
        raise ValueError('One or both analysis runs not found')

    before_findings = db.query(Finding).filter(Finding.analysis_id == before_id).all()
    after_findings = db.query(Finding).filter(Finding.analysis_id == after_id).all()
    resolved, still_present, new, changed = compare_findings(before_findings, after_findings)

    before_claims = db.query(Claim).filter(Claim.analysis_id == before_id).all()
    after_claims = db.query(Claim).filter(Claim.analysis_id == after_id).all()

    # Category score deltas — only for categories present in both runs.
    category_changes = []
    before_cats = before_run.category_scores or {}
    after_cats = after_run.category_scores or {}
    for cat in sorted(set(before_cats) & set(after_cats)):
        b = before_cats[cat].get('score', 0)
        a = after_cats[cat].get('score', 0)
        category_changes.append({
            'category': cat, 'before_score': b, 'after_score': a, 'delta': a - b,
            'verified': True,
        })
    for cat in sorted(set(before_cats) ^ set(after_cats)):
        category_changes.append({
            'category': cat,
            'before_score': before_cats.get(cat, {}).get('score'),
            'after_score': after_cats.get(cat, {}).get('score'),
            'delta': None,
            'verified': False,
            'note': 'Change could not be verified: category missing from one run.',
        })

    # Measurable metric changes (None when not reliably measurable).
    metrics = {
        'testing': _metric(_test_file_count(db, before_id), _test_file_count(db, after_id)),
        'security_findings': _metric(
            sum(1 for f in before_findings if f.category == 'Security'),
            sum(1 for f in after_findings if f.category == 'Security'),
        ),
        'documentation_findings': _metric(
            sum(1 for f in before_findings if f.category == 'Documentation'),
            sum(1 for f in after_findings if f.category == 'Documentation'),
        ),
        'total_findings': _metric(len(before_findings), len(after_findings)),
        'overall_score': _metric(before_run.overall_score, after_run.overall_score),
    }

    return {
        'before_id': before_id,
        'after_id': after_id,
        'before_repo': f'{before_run.owner}/{before_run.repo_name}',
        'after_repo': f'{after_run.owner}/{after_run.repo_name}',
        'before_created_at': before_run.created_at,
        'after_created_at': after_run.created_at,
        'score': {
            'before': before_run.overall_score,
            'after': after_run.overall_score,
            'delta': after_run.overall_score - before_run.overall_score,
            'note': 'Score delta alone is NOT proof of improvement; see finding-level evidence below.',
        },
        'category_changes': category_changes,
        'findings': {
            'resolved': [_delta_dict(d) for d in resolved],
            'still_present': [_delta_dict(d) for d in still_present],
            'new': [_delta_dict(d) for d in new],
            'changed': [_delta_dict(d) for d in changed],
        },
        'claim_stats': {
            'before': _claim_stats(before_claims),
            'after': _claim_stats(after_claims),
        },
        'claim_changes': _claim_changes(before_claims, after_claims),
        'metrics': metrics,
        'timeline': [
            {'step': 1, 'event': 'Analysis 1 (before)', 'analysis_id': before_id, 'overall_score': before_run.overall_score, 'findings': len(before_findings), 'created_at': before_run.created_at},
            {'step': 2, 'event': 'Findings + Recommendations reviewed', 'count': len(before_findings)},
            {'step': 3, 'event': 'Fixes applied by developer', 'count': len(resolved) + len(changed)},
            {'step': 4, 'event': 'Analysis 2 (after)', 'analysis_id': after_id, 'overall_score': after_run.overall_score, 'findings': len(after_findings), 'created_at': after_run.created_at},
            {'step': 5, 'event': 'Verification', 'resolved': len(resolved), 'still_present': len(still_present), 'new': len(new), 'changed': len(changed)},
        ],
    }
