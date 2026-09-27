from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from backend.app.database.session import get_db
from backend.app.models.findings import AnalysisRun
from backend.app.models.phase6_9 import PortfolioArtifact, EngineeringSnapshot, InterviewSession, ProofPassport
from backend.app.services.phase6_9 import portfolio_payload, portfolio_markdown, snapshot_for, compare_snapshots, interview_questions, evaluate_answer, passport_payload, passport_markdown, _canonical

router = APIRouter()


def run_or_404(db, analysis_id):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
    if not run: raise HTTPException(status_code=404, detail='Analysis run not found')
    return run


@router.get('/portfolio/{analysis_id}')
def get_portfolio(analysis_id: str, db: Session = Depends(get_db)):
    run = run_or_404(db, analysis_id)
    row = db.query(PortfolioArtifact).filter(PortfolioArtifact.analysis_id == analysis_id).first()
    if not row:
        payload = portfolio_payload(db, run); row = PortfolioArtifact(analysis_id=analysis_id, payload=payload, markdown=portfolio_markdown(payload)); db.add(row); db.commit(); db.refresh(row)
    return {'id': row.id, 'analysis_id': analysis_id, 'payload': row.payload, 'markdown': row.markdown, 'created_at': row.created_at}


@router.post('/portfolio/{analysis_id}/generate')
def generate_portfolio(analysis_id: str, db: Session = Depends(get_db)):
    run_or_404(db, analysis_id)
    row = db.query(PortfolioArtifact).filter(PortfolioArtifact.analysis_id == analysis_id).first()
    run = run_or_404(db, analysis_id); payload = portfolio_payload(db, run); md = portfolio_markdown(payload)
    if row: row.payload, row.markdown = payload, md
    else: row = PortfolioArtifact(analysis_id=analysis_id, payload=payload, markdown=md); db.add(row)
    db.commit(); db.refresh(row)
    return {'id': row.id, 'analysis_id': analysis_id, 'payload': row.payload, 'markdown': row.markdown}


@router.get('/portfolio/{analysis_id}/export', response_class=PlainTextResponse)
def export_portfolio(analysis_id: str, format: str = 'markdown', db: Session = Depends(get_db)):
    data = get_portfolio(analysis_id, db)
    if format == 'json': return json.dumps(data['payload'], indent=2, ensure_ascii=False)
    return data['markdown']


@router.get('/monitor/{analysis_id}')
def get_monitor(analysis_id: str, db: Session = Depends(get_db)):
    run = run_or_404(db, analysis_id)
    row = db.query(EngineeringSnapshot).filter(EngineeringSnapshot.analysis_id == analysis_id).first()
    if not row:
        snap = snapshot_for(db, run); row = EngineeringSnapshot(analysis_id=analysis_id, repository=run.repo_url, commit_sha=run.commit_sha, branch=run.branch, snapshot=snap); db.add(row); db.commit(); db.refresh(row)
    previous = db.query(EngineeringSnapshot).filter(EngineeringSnapshot.repository == run.repo_url, EngineeringSnapshot.created_at < row.created_at).order_by(EngineeringSnapshot.created_at.desc()).first()
    comparison = compare_snapshots(previous.snapshot, row.snapshot) if previous else None
    timeline = db.query(EngineeringSnapshot).filter(EngineeringSnapshot.repository == run.repo_url).order_by(EngineeringSnapshot.created_at.asc()).all()
    return {'current': row.snapshot, 'previous': previous.snapshot if previous else None, 'comparison': comparison, 'timeline': [x.snapshot for x in timeline]}


@router.get('/monitor/{analysis_id}/timeline')
def monitor_timeline(analysis_id: str, db: Session = Depends(get_db)):
    return get_monitor(analysis_id, db)['timeline']


class InterviewStart(BaseModel):
    mode: str = Field(default='Project Defense', max_length=100)
    difficulty: str = Field(default='Mixed', max_length=50)
    limit: int = Field(default=8, ge=1, le=20)

class InterviewAnswer(BaseModel):
    question_index: int = Field(ge=0)
    answer: str = Field(max_length=8000)


@router.post('/interview/{analysis_id}/sessions')
def start_interview(analysis_id: str, req: InterviewStart, db: Session = Depends(get_db)):
    run = run_or_404(db, analysis_id); questions = interview_questions(db, run, req.mode, req.limit)
    session = InterviewSession(analysis_id=analysis_id, mode=req.mode, difficulty=req.difficulty, questions=questions, answers=[]); db.add(session); db.commit(); db.refresh(session)
    return {'id': session.id, 'analysis_id': analysis_id, 'mode': session.mode, 'difficulty': session.difficulty, 'questions': questions, 'answers': []}


@router.get('/interview/sessions/{session_id}')
def get_interview(session_id: str, db: Session = Depends(get_db)):
    row = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not row: raise HTTPException(status_code=404, detail='Interview session not found')
    return {'id': row.id, 'analysis_id': row.analysis_id, 'mode': row.mode, 'difficulty': row.difficulty, 'questions': row.questions or [], 'answers': row.answers or [], 'created_at': row.created_at, 'completed_at': row.completed_at}


@router.post('/interview/sessions/{session_id}/answers')
def answer_interview(session_id: str, req: InterviewAnswer, db: Session = Depends(get_db)):
    row = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not row: raise HTTPException(status_code=404, detail='Interview session not found')
    if req.question_index >= len(row.questions or []): raise HTTPException(status_code=400, detail='Question index out of range')
    q = row.questions[req.question_index]
    evaluation = evaluate_answer(q, req.answer)
    entry = {'question_index': req.question_index, 'answer': req.answer, 'evaluation': evaluation, 'evidence_reference': q.get('evidence_reference')}
    answers = list(row.answers or [])
    # One persisted answer per question: resubmission updates the existing answer.
    answers = [a for a in answers if a.get('question_index') != req.question_index]
    answers.append(entry)
    answers.sort(key=lambda a: a.get('question_index', 0))
    row.answers = answers
    if len(answers) >= len(row.questions or []):
        row.completed_at = datetime.now(timezone.utc)
    db.commit()
    return entry


def _passport_improvements(db, run):
    previous = db.query(AnalysisRun).filter(
        AnalysisRun.repo_url == run.repo_url,
        AnalysisRun.created_at < run.created_at,
    ).order_by(AnalysisRun.created_at.desc()).first()
    if not previous:
        return 'Improvement history unavailable: no previous analysis was found.'
    before = snapshot_for(db, previous)
    after = snapshot_for(db, run)
    return compare_snapshots(before, after)


@router.post('/passport/{analysis_id}/generate')
def generate_passport(analysis_id: str, db: Session = Depends(get_db)):
    run = run_or_404(db, analysis_id)
    payload = passport_payload(db, run, _passport_improvements(db, run))
    proof_id = payload['proof_id']
    payload_hash = __import__('hashlib').sha256(_canonical(payload).encode()).hexdigest()
    md = passport_markdown(payload, payload_hash)
    row = db.query(ProofPassport).filter(ProofPassport.analysis_id == analysis_id).first()
    if row:
        row.proof_id, row.payload, row.payload_hash, row.markdown = proof_id, payload, payload_hash, md
    else:
        row = ProofPassport(analysis_id=analysis_id, proof_id=proof_id, payload=payload, payload_hash=payload_hash, markdown=md)
        db.add(row)
    db.commit(); db.refresh(row)
    return {'proof_id': row.proof_id, 'analysis_id': analysis_id, 'payload': row.payload, 'payload_hash': row.payload_hash, 'markdown': row.markdown, 'valid': True}


@router.get('/passport/{analysis_id}')
def get_passport(analysis_id: str, db: Session = Depends(get_db)):
    row = db.query(ProofPassport).filter(ProofPassport.analysis_id == analysis_id).first()
    if not row: return generate_passport(analysis_id, db)
    return {'proof_id': row.proof_id, 'analysis_id': analysis_id, 'payload': row.payload, 'payload_hash': row.payload_hash, 'markdown': row.markdown, 'valid': __import__('hashlib').sha256(_canonical(row.payload).encode()).hexdigest() == row.payload_hash}


@router.get('/passport/{analysis_id}/export', response_class=PlainTextResponse)
def export_passport(analysis_id: str, format: str = 'markdown', db: Session = Depends(get_db)):
    data = get_passport(analysis_id, db)
    return json.dumps(data['payload'], indent=2, ensure_ascii=False) if format == 'json' else data['markdown']


@router.post('/passport/{analysis_id}/verify')
def verify_passport(analysis_id: str, db: Session = Depends(get_db)):
    data = get_passport(analysis_id, db); actual = __import__('hashlib').sha256(_canonical(data['payload']).encode()).hexdigest(); return {'status': 'VALID' if actual == data['payload_hash'] else 'MODIFIED', 'expected_hash': data['payload_hash'], 'actual_hash': actual}
