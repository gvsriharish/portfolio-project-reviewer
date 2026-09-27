"""Phase 2 — Claim models (Project Claim Auditor).

Claims are extracted deterministically from README / documentation and
verified against FindingEvidence rows. Relationships use association
tables so that Claim → Evidence and Evidence → Claim are both many-to-many.

No new evidence system is introduced: claims link to the existing
`finding_evidence` rows produced by the Phase 1 analyzers.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Table, Index
from sqlalchemy.orm import relationship

from backend.app.database.base import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


# Claim ↔ EvidenceItem (many-to-many)
claim_evidence_links = Table(
    'claim_evidence_links',
    Base.metadata,
    Column('claim_id', String(36), ForeignKey('claims.id', ondelete='CASCADE'), primary_key=True),
    Column('evidence_id', String(36), ForeignKey('finding_evidence.id', ondelete='CASCADE'), primary_key=True),
)

# Claim ↔ Finding (many-to-many, e.g. a claim both supported by and
# conflicting with different findings)
claim_finding_links = Table(
    'claim_finding_links',
    Base.metadata,
    Column('claim_id', String(36), ForeignKey('claims.id', ondelete='CASCADE'), primary_key=True),
    Column('finding_id', String(36), ForeignKey('findings.id', ondelete='CASCADE'), primary_key=True),
)


class Claim(Base):
    __tablename__ = 'claims'

    id = Column(String(36), primary_key=True, default=_generate_uuid)
    analysis_id = Column(String(36), ForeignKey('analysis_runs.id', ondelete='CASCADE'), nullable=False, index=True)

    # Verbatim sentence from the documentation (data only — never executed).
    claim_text = Column(Text, nullable=False)
    # Lowercased, punctuation-stripped form used for de-duplication.
    normalized_claim = Column(Text, nullable=False, default='')
    source_file = Column(String(500), nullable=False, default='')
    source_line = Column(Integer, nullable=True)

    # TECHNOLOGY | ARCHITECTURE | SECURITY | TESTING | DEPLOYMENT | DATABASE |
    # AI_ML | API | PERFORMANCE | FEATURE | QUALITY | OTHER
    category = Column(String(50), nullable=False, default='OTHER')

    # SUPPORTED | PARTIALLY_SUPPORTED | UNVERIFIED | CONTRADICTED
    # Decided exclusively by the deterministic verifier, never by an LLM.
    status = Column(String(30), nullable=False, default='UNVERIFIED')

    # HIGH | MEDIUM | LOW
    confidence = Column(String(20), nullable=False, default='LOW')

    # Deterministic explanation of the verdict ("Evidence not detected." when none).
    explanation = Column(Text, nullable=False, default='')

    evidence_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    evidence_items = relationship(
        'FindingEvidence', secondary=claim_evidence_links, lazy='dynamic'
    )
    findings = relationship('Finding', secondary=claim_finding_links, lazy='dynamic')


Index('ix_claims_analysis_status', Claim.analysis_id, Claim.status)
