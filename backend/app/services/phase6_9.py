import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from backend.app.models.findings import AnalysisRun, Finding, Recommendation, InterviewQuestion, ProjectExplanation
from backend.app.models.claims import Claim
from backend.app.models.evidence import FindingEvidence
from backend.app.models.verification import VerificationResult


def _iso(value):
    return value.isoformat() if value else None


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _technology_status(value: str, claims, evidence):
    """Return only evidence-backed technology details.

    Languages/frameworks are analyzer metadata. A direct repository observation is
    preferred; otherwise the technology is explicitly marked INFERRED/UNVERIFIED.
    """
    value_l = value.lower()
    claim_hits = [c for c in claims if value_l in (c.claim_text or '').lower()]
    evidence_hits = [
        e for e in evidence
        if value_l in f"{e.evidence_summary} {e.source_file}".lower()
    ]
    if evidence_hits:
        e = evidence_hits[0]
        return {
            'technology': value,
            'evidence': e.evidence_summary,
            'confidence': e.confidence,
            'status': e.verification_status,
            'source': e.source_file or 'project-level evidence',
        }
    if claim_hits:
        c = claim_hits[0]
        return {
            'technology': value,
            'evidence': c.claim_text,
            'confidence': c.confidence,
            'status': c.status,
            'source': c.source_file or 'claim',
        }
    return {
        'technology': value,
        'evidence': 'Detected by deterministic analyzer metadata; direct source evidence was not persisted.',
        'confidence': 'LOW',
        'status': 'UNVERIFIED',
        'source': 'analysis metadata',
    }


def portfolio_payload(db, run):
    claims = db.query(Claim).filter(Claim.analysis_id == run.id).all()
    findings = db.query(Finding).filter(Finding.analysis_id == run.id).all()
    evidence = db.query(FindingEvidence).join(Finding, FindingEvidence.finding_id == Finding.id).filter(Finding.analysis_id == run.id).all()
    recs = db.query(Recommendation).filter(Recommendation.analysis_id == run.id).order_by(Recommendation.rank).all()
    verifications = db.query(VerificationResult).filter(VerificationResult.analysis_id == run.id).all()
    explanation = db.query(ProjectExplanation).filter(ProjectExplanation.analysis_id == run.id).first()

    technologies = []
    for value in (run.languages or []) + (run.frameworks or []):
        if value and value not in technologies:
            technologies.append(value)
    tech_items = [_technology_status(t, claims, evidence) for t in technologies]

    claim_items = [{
        'content': c.claim_text, 'source_type': 'Claim', 'source_reference': c.source_file,
        'verification_status': c.status, 'confidence': c.confidence, 'claim_id': c.id,
        'evidence_count': c.evidence_count,
    } for c in claims]

    problem = next(
        (c['content'] for c in claim_items
         if any(x in c['content'].lower() for x in ('problem', 'challenge', 'issue', 'need'))),
        None,
    )
    if not problem:
        problem = 'Problem statement not reliably detected from repository evidence.'
    solution = explanation.summary if explanation and explanation.summary else None
    if not solution:
        solution = 'Solution description could not be fully verified.'

    architecture = run.architecture_summary or {}
    architecture_status = 'VERIFIED' if architecture else 'UNVERIFIED'

    return {
        'analysis_id': run.id,
        'project': {'name': run.repo_name, 'owner': run.owner, 'repository': run.repo_url, 'generated_at': _iso(run.created_at)},
        'hero': {
            'name': run.repo_name,
            'description': (explanation.summary if explanation else 'Repository-derived engineering evidence package.'),
            'engineering_confidence': run.overall_score,
            'verified_claims': sum(c.status == 'SUPPORTED' for c in claims),
            'limitations': ['Portfolio Reviewer Score is an internal product metric, not a certification.'],
        },
        'technologies': tech_items,
        'architecture': {'status': architecture_status, 'components': architecture},
        'sections': {
            'overview': explanation.summary if explanation else 'Repository overview not reliably detected from available evidence.',
            'problem': {'text': problem, 'status': 'VERIFIED' if problem != 'Problem statement not reliably detected from repository evidence.' else 'UNVERIFIED'},
            'solution': {'text': solution, 'status': 'VERIFIED' if explanation else 'UNVERIFIED'},
            'architecture': {'status': architecture_status, 'components': architecture},
            'engineering_decisions': [
                {'text': x, 'status': 'DOCUMENTED'} for x in (explanation.technical_decisions if explanation else [])
            ] or [{'text': 'Engineering decision not documented.', 'status': 'NOT DOCUMENTED'}],
            'testing': [e.evidence_summary for e in evidence if e.category.lower() in ('testing', 'tests')],
            'security': [e.evidence_summary for e in evidence if e.category.lower() == 'security'],
            'improvements': [r.action for r in recs],
            'limitations': (explanation.limitations if explanation else []) + ['Static analysis cannot prove runtime behavior.'],
        },
        'claims': claim_items,
        'findings': [{
            'id': f.id, 'finding_key': f.finding_key, 'title': f.title, 'category': f.category,
            'severity': f.severity, 'file_path': f.file_path, 'line_number': f.line_number,
            'evidence': f.evidence, 'description': f.description,
        } for f in findings],
        'recommendations': [{
            'id': r.id, 'title': r.title, 'action': r.action, 'status': r.status,
            'finding_id': r.finding_id, 'verification': r.verification,
        } for r in recs],
        'evidence': [{
            'id': e.id, 'finding_id': e.finding_id, 'source_file': e.source_file,
            'source_line': e.source_line, 'summary': e.evidence_summary,
            'verification_status': e.verification_status, 'confidence': e.confidence,
            'finding_key': e.finding_key,
        } for e in evidence],
        'verifications': [{
            'id': v.id, 'finding_key': v.finding_key, 'result': v.result,
            'method': v.method, 'details': v.details, 'recommendation_id': v.recommendation_id,
        } for v in verifications],
        'interview_talking_points': [q.question for q in db.query(InterviewQuestion).filter(InterviewQuestion.analysis_id == run.id).all()],
    }


def portfolio_markdown(p):
    h = p['hero']; s = p['sections']
    lines = [
        f"# {p['project']['name']} — Engineering Portfolio", '',
        h['description'], '',
        f"**Portfolio Reviewer Score:** {h['engineering_confidence']}/100 (internal product metric)", '',
        '## Project Overview', str(s['overview']), '',
        '## Problem', f"**{s['problem']['status']}** {s['problem']['text']}", '',
        '## Solution', f"**{s['solution']['status']}** {s['solution']['text']}", '',
        '## Technologies'
    ]
    lines += [f"- **{t['technology']}** — {t['status']} / {t['confidence']}; {t['evidence']} (`{t['source']}`)" for t in p['technologies']] or ['- Technology evidence not detected.']
    lines += ['', '## Architecture', f"**{s['architecture']['status']}**"]
    lines += [f"- {k}: {v}" for k, v in (s['architecture']['components'] or {}).items()] or ['- Architecture evidence not detected.']
    lines += ['', '## Engineering Decisions']
    lines += [f"- **{x['status']}** {x['text']}" for x in s['engineering_decisions']]
    for title, key in [('Testing','testing'), ('Security','security'), ('Improvements','improvements'), ('Limitations','limitations')]:
        lines += [f'## {title}']
        value = s.get(key, [])
        lines += [f'- {x}' for x in value] or ['- Evidence not detected.']
        lines.append('')
    lines += ['## Evidence-backed Claims']
    lines += [f"- **{c['verification_status']}** {c['content']} — `{c['source_reference'] or 'no source'}`" for c in p['claims']] or ['- Evidence not detected.']
    return '\n'.join(lines)


def snapshot_for(db, run):
    findings = db.query(Finding).filter(Finding.analysis_id == run.id).all()
    claims = db.query(Claim).filter(Claim.analysis_id == run.id).all()
    evidence = db.query(FindingEvidence).join(Finding, FindingEvidence.finding_id == Finding.id).filter(Finding.analysis_id == run.id).all()
    recs = db.query(Recommendation).filter(Recommendation.analysis_id == run.id).all()
    verifications = db.query(VerificationResult).filter(VerificationResult.analysis_id == run.id).all()
    return {
        'analysis_id': run.id, 'repository': run.repo_url, 'repo_name': run.repo_name,
        'commit_sha': getattr(run, 'commit_sha', None), 'branch': getattr(run, 'branch', None),
        'timestamp': _iso(run.created_at), 'score': run.overall_score,
        'category_scores': run.category_scores or {},
        'finding_count': len(findings), 'claim_count': len(claims), 'evidence_count': len(evidence),
        'verification_count': len(verifications),
        'finding_keys': sorted(f.finding_key for f in findings if f.finding_key),
        'finding_details': {
            (f.finding_key or f'id::{f.id}'): {
                'severity': f.severity, 'file_path': f.file_path, 'evidence': f.evidence,
                'description': f.description,
            } for f in findings
        },
        'claim_statuses': {c.normalized_claim: c.status for c in claims},
        'claim_keys': sorted(c.normalized_claim for c in claims),
        'evidence_files': sorted(set(e.source_file for e in evidence if e.source_file)),
        'recommendation_statuses': {r.id: r.status for r in recs},
        'verification_results': {v.finding_key: v.result for v in verifications},
    }


def compare_snapshots(before, after):
    before_details, after_details = before.get('finding_details', {}), after.get('finding_details', {})
    common = set(before_details) & set(after_details)
    changed = []
    for key in sorted(common):
        delta = {}
        for field in ('severity', 'file_path', 'evidence', 'description'):
            if before_details[key].get(field) != after_details[key].get(field):
                delta[field] = {'before': before_details[key].get(field), 'after': after_details[key].get(field)}
        if delta:
            changed.append({'finding_key': key, 'status': 'CHANGED', 'before': before_details[key], 'after': after_details[key], 'changes': delta})

    bkeys, akeys = set(before.get('finding_keys', [])), set(after.get('finding_keys', []))
    claim_keys = set(before.get('claim_statuses', {})) | set(after.get('claim_statuses', {}))
    claim_changes = [{
        'claim': k,
        'status': 'NEW CLAIM' if k not in before.get('claim_statuses', {}) else 'REMOVED CLAIM' if k not in after.get('claim_statuses', {}) else 'CLAIM STATUS CHANGED',
        'before': before.get('claim_statuses', {}).get(k),
        'after': after.get('claim_statuses', {}).get(k),
    } for k in sorted(claim_keys) if before.get('claim_statuses', {}).get(k) != after.get('claim_statuses', {}).get(k)]

    b_rec, a_rec = before.get('recommendation_statuses', {}), after.get('recommendation_statuses', {})
    rec_changes = [{'recommendation': k, 'before': b_rec.get(k), 'after': a_rec.get(k)} for k in sorted(set(b_rec)|set(a_rec)) if b_rec.get(k) != a_rec.get(k)]
    b_ver, a_ver = before.get('verification_results', {}), after.get('verification_results', {})
    ver_changes = [{'finding_key': k, 'before': b_ver.get(k), 'after': a_ver.get(k)} for k in sorted(set(b_ver)|set(a_ver)) if b_ver.get(k) != a_ver.get(k)]

    return {
        'new_findings': sorted(akeys - bkeys), 'resolved_findings': sorted(bkeys - akeys),
        'still_present': sorted(akeys & bkeys - {x['finding_key'] for x in changed}),
        'changed_findings': changed,
        'new_evidence': sorted(set(after.get('evidence_files', [])) - set(before.get('evidence_files', []))),
        'lost_evidence': sorted(set(before.get('evidence_files', [])) - set(after.get('evidence_files', []))),
        'score_delta': after.get('score', 0) - before.get('score', 0),
        'category_score_changes': {
            k: {'before': before.get('category_scores', {}).get(k), 'after': after.get('category_scores', {}).get(k)}
            for k in sorted(set(before.get('category_scores', {})) | set(after.get('category_scores', {})))
            if before.get('category_scores', {}).get(k) != after.get('category_scores', {}).get(k)
        },
        'claim_status_changes': claim_changes,
        'recommendation_changes': rec_changes,
        'verification_changes': ver_changes,
    }


TECH_CATALOG = {
    'postgresql','postgres','mysql','sqlite','redis','mongodb','kubernetes','docker',
    'fastapi','flask','django','react','next.js','nextjs','typescript','javascript',
    'python','java','c++','go','rust','node.js','nodejs','tailwind','supabase',
    'tensorflow','pytorch','opencv','github actions','aws','azure','gcp'
}


def interview_questions(db, run, mode='Project Defense', limit=8):
    p = portfolio_payload(db, run); qs = []
    for t in p['technologies'][:3]:
        qs.append({
            'question': f"How is {t['technology']} used in this repository?",
            'category': 'Technology', 'difficulty': 'Technical',
            'evidence_reference': t['source'], 'evidence_summary': t['evidence'],
            'expected_topics': [t['technology']], 'source': 'deterministic technology detection',
        })
    for f in p['findings'][:max(0, limit-len(qs))]:
        qs.append({
            'question': f"How would you address the {f['title']} finding?",
            'category': f['category'], 'difficulty': 'Project Defense',
            'evidence_reference': f['file_path'], 'evidence_summary': f['evidence'] or f['description'],
            'expected_topics': [f['finding_key'] or f['title']], 'source': 'deterministic finding',
        })
    return qs[:limit]


def evaluate_answer(question, answer):
    answer_l = answer.lower()
    topics = question.get('expected_topics', [])
    matched = [t for t in topics if str(t).lower() in answer_l]
    unsupported = []
    for tech in TECH_CATALOG:
        if re.search(rf'(?<!\w){re.escape(tech)}(?!\w)', answer_l) and not any(tech in str(t).lower() for t in topics):
            unsupported.append(tech)
    if not answer.strip():
        rating = 'WEAK'
    elif matched and unsupported:
        rating = 'PARTIAL'
    elif matched:
        rating = 'STRONG' if len(answer.split()) >= 8 else 'PARTIAL'
    elif unsupported:
        rating = 'UNSUPPORTED'
    else:
        rating = 'WEAK'
    return {
        'rating': rating,
        'evidence_alignment': bool(matched),
        'explanation': 'Answer aligns with repository evidence.' if matched and not unsupported else
            'Answer partially aligns with repository evidence and contains unsupported technology claims.' if matched else
            'Answer contains claims not supported by repository evidence.' if unsupported else
            'Answer did not provide enough evidence-aligned detail.',
        'matched_topics': matched,
        'unsupported_claims': unsupported,
    }


def passport_payload(db, run, improvements=None):
    p = portfolio_payload(db, run); snap = snapshot_for(db, run)
    return {
        'proof_id': f"PPR-{(run.created_at or datetime.now(timezone.utc)).strftime('%Y%m%d')}-{run.id[:8].upper()}",
        'project': p['project'], 'repository': snap, 'claims': p['claims'], 'evidence': p['evidence'],
        'findings': p['findings'], 'recommendations': p['recommendations'], 'verifications': p['verifications'],
        'improvements': improvements if improvements is not None else 'Improvement history unavailable: no previous analysis was found.',
        'engineering_confidence': {'label': 'Portfolio Reviewer Score', 'value': run.overall_score},
        'limitations': p['sections']['limitations'],
    }


def passport_markdown(p, payload_hash):
    lines = [
        '# Project Proof Passport', '',
        '> This Project Proof Passport is generated from repository analysis performed by Portfolio Project Reviewer. It is not a professional certification, security certification, academic credential, or guarantee of software quality.',
        '', f"**Proof ID:** {p['proof_id']}", f"**Repository:** {p['project']['repository']}",
        f"**Commit:** {p['repository'].get('commit_sha') or 'COMMIT NOT AVAILABLE'}",
        f"**Generated:** {p['project']['generated_at']}", f"**Integrity SHA-256:** `{payload_hash}`", '',
        '## Verified Claims'
    ]
    lines += [f"- **{c['verification_status']}** {c['content']} — `{c['source_reference'] or 'no source'}`" for c in p['claims']] or ['- None detected.']
    lines += ['', '## Evidence']
    lines += [f"- `{e['source_file']}`: {e['summary']} ({e['verification_status']})" for e in p['evidence']] or ['- None detected.']
    lines += ['', '## Findings']
    lines += [f"- [{f['severity']}] {f['title']} (`{f['file_path']}`)" for f in p['findings']] or ['- None detected.']
    lines += ['', '## Recommendations']
    lines += [f"- [{r['status']}] {r['title']}: {r['action']}" for r in p['recommendations']] or ['- None detected.']
    lines += ['', '## Verification']
    lines += [f"- [{v['result']}] {v['finding_key']}: {v['details']}" for v in p['verifications']] or ['- None detected.']
    lines += ['', '## Improvements']
    if isinstance(p['improvements'], str): lines.append(f"- {p['improvements']}")
    else: lines += [f"- {x}" for x in p['improvements']] or ['- None detected.']
    lines += ['', '## Security', '- Repository content is treated as untrusted input; static analysis does not execute repository code.']
    lines += ['', '## Testing', '- Testing evidence is included above when detected.']
    lines += ['', '## Architecture', f"- {json.dumps(p['project'], ensure_ascii=False)}"]
    lines += ['', '## Limitations'] + [f'- {x}' for x in p['limitations']]
    return '\n'.join(lines)
