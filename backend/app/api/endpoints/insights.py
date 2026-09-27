"""Phase 3/5 — Evidence Graph and Trust Report API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.services.graph_builder import build_evidence_graph
from backend.app.services.trust_report import build_trust_report, render_markdown

router = APIRouter()


@router.get("/analysis/{analysis_id}/evidence-graph")
def get_evidence_graph(analysis_id: str, db: Session = Depends(get_db)):
    from backend.app.models.findings import AnalysisRun
    if not db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first():
        raise HTTPException(status_code=404, detail="Analysis run not found")
    try:
        return build_evidence_graph(db, analysis_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/analysis/{analysis_id}/trust-report")
def get_trust_report(analysis_id: str, format: str = Query('json'), db: Session = Depends(get_db)):
    try:
        report = build_trust_report(db, analysis_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if format == 'markdown' or format == 'md':
        return PlainTextResponse(render_markdown(report), media_type='text/markdown')
    return report
