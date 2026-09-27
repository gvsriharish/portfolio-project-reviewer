"""Phase 3 — VerificationResult model.

Stores the outcome of Finding → Fix → Verify checks performed when two
analysis runs are compared. A verification result is computed exclusively
from deterministic evidence (finding keys, evidence rows); the user's
word alone never resolves a recommendation.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from backend.app.database.base import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class VerificationResult(Base):
    __tablename__ = 'verification_results'

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    analysis_id = Column(String(36), ForeignKey('analysis_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    recommendation_id = Column(String(36), ForeignKey('recommendations.id', ondelete='SET NULL'), nullable=True)

    # Stable finding identity this verification refers to.
    finding_key = Column(String(300), nullable=False, index=True)

    # Verification rule applied (e.g. "finding key absent from new analysis").
    method = Column(Text, nullable=False, default='')

    # PASS | FAIL | UNVERIFIED
    result = Column(String(20), nullable=False, default='UNVERIFIED')
    details = Column(Text, nullable=False, default='')
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    analysis = relationship('AnalysisRun')
    recommendation = relationship('Recommendation')


Index('ix_verification_analysis_key', VerificationResult.analysis_id, VerificationResult.finding_key)
