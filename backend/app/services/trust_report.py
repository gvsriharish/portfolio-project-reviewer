"""Phase 5 — Project Trust Report.

Computes an internal trust summary from actual analysis data: claim
statistics, finding statistics, evidence statistics, resolved/remaining
findings, proof of improvement and an explained internal Engineering
Confidence metric.

This is an INTERNAL PRODUCT METRIC — never an industry or professional
certification. Every number is calculated from persisted analysis rows;
nothing is fabricated. When data is missing the section reports that
fact instead of guessing.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.models.findings import AnalysisRun, Finding, Recommendation
from backend.app.models.evidence import FindingEvidence
from backend.app.models.claims import Claim
from backend.app.models.verification import VerificationResult

# Internal, explainable Engineering Confidence factors (0-100 each).
CONFIDENCE_FACTORS = [
    'claim_verification',        # share of claims verified (SUPPORTED or CONTRADICTED)
    'evidence_coverage',         # share of findings backed by structured evidence
    'security_evidence',         # security category present with evidence, no critical findings
    'testing_evidence',          # test evidence present
    'documentation_consistency', # share of doc claims not contradicted
    'architecture_evidence',     # architecture findings carry evidence
    'dependency_evidence',       # dependency findings carry evidence
    'git_evidence',              # git hygiene findings carry evidence
]


def _pct(part: int, total: int) -> Optional[float]:
    if total == 0:
        return None
    return round(100.0 * part / total, 1)


def build_trust_report(db: Session, analysis_id: str) -> Dict[str, Any]:
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run:
        raise ValueError('Analysis run not found')

    findings = db.query(Finding).filter(Finding.analysis_id == analysis_id).all()
    evidence_rows = (
        db.query(FindingEvidence)
        .join(Finding, FindingEvidence.finding_id == Finding.id)
        .filter(Finding.analysis_id == analysis_id)
        .all()
    )
    claims = db.query(Claim).filter(Claim.analysis_id == analysis_id).all()
    recommendations = db.query(Recommendation).filter(Recommendation.analysis_id == analysis_id).all()
    verifications = db.query(VerificationResult).filter(VerificationResult.analysis_id == analysis_id).all()

    # ------------------------------------------------------------ claims
    claim_stats = {
        'total': len(claims),
        'supported': sum(1 for c in claims if c.status == 'SUPPORTED'),
        'partially_supported': sum(1 for c in claims if c.status == 'PARTIALLY_SUPPORTED'),
        'unverified': sum(1 for c in claims if c.status == 'UNVERIFIED'),
        'contradicted': sum(1 for c in claims if c.status == 'CONTRADICTED'),
    }
    claim_details = [
        {
            'id': c.id, 'claim_text': c.claim_text, 'category': c.category,
            'status': c.status, 'confidence': c.confidence,
            'source_file': c.source_file, 'source_line': c.source_line,
            'evidence_count': c.evidence_count,
            'evidence_files': sorted({e.source_file for e in c.evidence_items if e.source_file}),
        }
        for c in claims
    ]

    # ---------------------------------------------------------- findings
    def _by_cat(cat: str) -> List[Finding]:
        return [f for f in findings if f.category == cat]

    finding_stats = {
        'total': len(findings),
        'critical': sum(1 for f in findings if f.severity == 'CRITICAL'),
        'high': sum(1 for f in findings if f.severity == 'HIGH'),
        'medium': sum(1 for f in findings if f.severity == 'MEDIUM'),
        'low': sum(1 for f in findings if f.severity == 'LOW'),
        'info': sum(1 for f in findings if f.severity == 'INFO'),
        'security': len(_by_cat('Security')),
        'testing': len(_by_cat('Testing')),
        'documentation': len(_by_cat('Documentation')),
        'architecture': len(_by_cat('Architecture')),
        'dependencies': len(_by_cat('Dependencies')),
        'git_hygiene': len(_by_cat('Git Hygiene')),
        'code_quality': len(_by_cat('Code Quality')),
    }

    finding_ids = {f.id for f in findings}
    evidenced_finding_ids = {e.finding_id for e in evidence_rows if e.finding_id in finding_ids}

    evidence_stats = {
        'total': len(evidence_rows),
        'observed': sum(1 for e in evidence_rows if e.verification_status == 'OBSERVED'),
        'inferred': sum(1 for e in evidence_rows if e.verification_status == 'INFERRED'),
        'unverified': sum(1 for e in evidence_rows if e.verification_status == 'UNVERIFIED'),
        'findings_with_evidence': len(evidenced_finding_ids),
        'findings_without_evidence': len(findings) - len(evidenced_finding_ids),
    }

    # ----------------------------------------------- resolved / remaining
    # Resolution requires a comparison run; without one, every finding is
    # reported as remaining (never assumed resolved from a score).
    prior_run = (
        db.query(AnalysisRun)
        .filter(
            AnalysisRun.repo_url == run.repo_url,
            AnalysisRun.created_at < run.created_at,
            AnalysisRun.status == 'COMPLETED',
        )
        .order_by(AnalysisRun.created_at.desc())
        .first()
    )
    resolved_findings: List[Dict[str, Any]] = []
    if prior_run:
        from backend.app.services.finding_comparison import compare_findings
        before = db.query(Finding).filter(Finding.analysis_id == prior_run.id).all()
        res, _sp, _n, _ch = compare_findings(before, findings)
        resolved_findings = [
            {'finding_key': d.finding_key, 'title': d.title, 'category': d.category,
             'severity': d.before_severity}
            for d in res
        ]
    remaining = [
        {'finding_key': f.finding_key, 'title': f.title, 'category': f.category,
         'severity': f.severity, 'file_path': f.file_path}
        for f in findings
        if f.severity in ('CRITICAL', 'HIGH', 'MEDIUM')
    ]

    # ------------------------------------------------ Engineering Confidence
    verified_claims = claim_stats['supported'] + claim_stats['contradicted']
    factors = {
        'claim_verification': _pct(verified_claims, claim_stats['total']),
        'evidence_coverage': _pct(evidence_stats['findings_with_evidence'], finding_stats['total']),
        'security_evidence': (
            100.0 if any(
                e.category == 'Security' and e.verification_status == 'OBSERVED'
                for e in evidence_rows
            )
            else (
                0.0 if any(f.category == 'Security' and f.severity == 'CRITICAL' for f in findings)
                else None
            )
        ),
        'testing_evidence': (
            100.0 if (run.metrics or {}).get('test_file_count', 0) > 0
            else (
                0.0 if any(
                    f.category == 'Testing' and 'zero automated tests' in f.title.lower()
                    for f in findings
                )
                else None
            )
        ),
        'documentation_consistency': _pct(
            claim_stats['total'] - claim_stats['contradicted'], claim_stats['total']
        ),
        'architecture_evidence': (
            100.0 if any(e.category == 'Architecture' for e in evidence_rows)
            else (0.0 if _by_cat('Architecture') else None)
        ),
        'dependency_evidence': (
            100.0 if any(e.category == 'Dependencies' for e in evidence_rows)
            else (0.0 if _by_cat('Dependencies') else None)
        ),
        'git_evidence': (
            100.0 if any(e.category == 'Git Hygiene' for e in evidence_rows)
            else (0.0 if _by_cat('Git Hygiene') else None)
        ),
    }
    measured = [v for v in factors.values() if v is not None]
    engineering_confidence = {
        'score': round(sum(measured) / len(measured), 1) if measured else None,
        'scale': '0-100 (internal metric, not a certification)',
        'calculation': 'Mean of measured factor scores below; factors without measurable data are excluded, not guessed.',
        'factors': factors,
        'factor_definitions': CONFIDENCE_FACTORS,
    }

    # ------------------------------------------------------- improvement
    improvement = None
    if prior_run:
        from backend.app.services.improvement import build_improvement_report
        improvement = build_improvement_report(db, prior_run.id, analysis_id)

    return {
        'analysis_id': analysis_id,
        'project_identity': {
            'repo_url': run.repo_url,
            'repo_name': run.repo_name,
            'owner': run.owner,
            'analyzed_at': run.created_at,
            'overall_score': run.overall_score,
            'languages': run.languages or [],
            'frameworks': run.frameworks or [],
        },
        'repository_summary': {
            'status': run.status,
            'duration_seconds': run.duration_seconds,
            'is_sample': run.is_sample,
            'architecture_summary': run.architecture_summary or {},
        },
        'claim_stats': claim_stats,
        'claims': claim_details,
        'finding_stats': finding_stats,
        'evidence_stats': evidence_stats,
        'recommendations': [
            {'id': r.id, 'title': r.title, 'status': r.status,
             'finding_id': r.finding_id, 'verification': r.verification}
            for r in recommendations
        ],
        'verifications': [
            {'id': v.id, 'finding_key': v.finding_key, 'method': v.method,
             'result': v.result, 'details': v.details}
            for v in verifications
        ],
        'resolved_findings': resolved_findings,
        'resolved_findings_compared_to': prior_run.id if prior_run else None,
        'remaining_findings': remaining,
        'proof_of_improvement': improvement,
        'engineering_confidence': engineering_confidence,
        'limitations': [
            'Static analysis cannot verify runtime behavior, performance claims, or completeness of test suites.',
            'Claim coverage percentages are never inferred from test counts; unmeasured coverage is reported as unverified.',
            'Claims extracted from README/documentation are treated as untrusted data and pattern-scanned only.',
            'Engineering Confidence is an internal, explainable product metric — not an industry certification.',
            'Resolved findings require a prior analysis run for the same repository URL; without one, all findings are reported as remaining.',
        ],
        'report_format': 'internal_product_metric',
    }


def render_markdown(report: Dict[str, Any]) -> str:
    """Lightweight Markdown export of the trust report (real data only)."""
    ident = report['project_identity']
    cs = report['claim_stats']
    fs = report['finding_stats']
    es = report['evidence_stats']
    ec = report['engineering_confidence']

    lines = [
        f"# Project Trust Report — {ident['repo_name']}",
        '',
        f"Repository: {ident['repo_url']}",
        f"Analyzed at: {ident['analyzed_at']}",
        f"Internal portfolio score: {ident['overall_score']}/100",
        '',
        '## Claim Verification',
        '',
        f"- Claims analyzed: {cs['total']}",
        f"- Supported: {cs['supported']}",
        f"- Partially supported: {cs['partially_supported']}",
        f"- Unverified: {cs['unverified']}",
        f"- Contradicted: {cs['contradicted']}",
        '',
        '## Engineering Evidence',
        '',
        f"- Findings: {fs['total']} (critical {fs['critical']}, high {fs['high']})",
        f"- Evidence items: {es['total']} (observed {es['observed']}, inferred {es['inferred']}, unverified {es['unverified']})",
        f"- Findings with structured evidence: {es['findings_with_evidence']}/{fs['total']}",
        '',
        '## Findings by Category',
        '',
        f"- Security: {fs['security']}",
        f"- Testing: {fs['testing']}",
        f"- Documentation: {fs['documentation']}",
        f"- Architecture: {fs['architecture']}",
        f"- Dependencies: {fs['dependencies']}",
        f"- Git Hygiene: {fs['git_hygiene']}",
        f"- Code Quality: {fs['code_quality']}",
        '',
        '## Resolved Findings',
        '',
    ]
    if report.get('resolved_findings_compared_to'):
        if report['resolved_findings']:
            lines += [f"- ✅ {r['title']} ({r['category']})" for r in report['resolved_findings']]
        else:
            lines.append('- No resolved findings detected compared to the previous run.')
    else:
        lines.append('- No prior analysis run available; resolution could not be verified.')

    lines += ['', '## Remaining Risks', '']
    if report['remaining_findings']:
        lines += [f"- {r['severity']}: {r['title']} ({r['file_path'] or 'project-level'})"
                  for r in report['remaining_findings']]
    else:
        lines.append('- No critical/high/medium findings remaining.')

    lines += [
        '',
        '## Engineering Confidence (internal metric)',
        '',
        f"- Score: {ec['score'] if ec['score'] is not None else 'Not measurable'} / 100",
        f"- Calculation: {ec['calculation']}",
    ]
    for name, val in ec['factors'].items():
        lines.append(f"- {name}: {val if val is not None else 'no measurable data'}")

    lines += ['', '## Limitations', '']
    lines += [f'- {l}' for l in report['limitations']]

    lines += [
        '',
        '---',
        'This is an internal product metric, not an industry or professional certification.',
        '',
    ]
    return '\n'.join(lines)
