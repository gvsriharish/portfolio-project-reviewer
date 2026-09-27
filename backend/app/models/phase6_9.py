import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from backend.app.database.base import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class PortfolioArtifact(Base):
    __tablename__ = 'portfolio_artifacts'
    id = Column(String(36), primary_key=True, default=_uuid)
    analysis_id = Column(String(36), ForeignKey('analysis_runs.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    markdown = Column(Text, nullable=False, default='')
    created_at = Column(DateTime, default=_now)


class EngineeringSnapshot(Base):
    __tablename__ = 'engineering_snapshots'
    id = Column(String(36), primary_key=True, default=_uuid)
    analysis_id = Column(String(36), ForeignKey('analysis_runs.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    repository = Column(String(500), nullable=False)
    commit_sha = Column(String(100), nullable=True)
    branch = Column(String(200), nullable=True)
    snapshot = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=_now)


class InterviewSession(Base):
    __tablename__ = 'interview_sessions'
    id = Column(String(36), primary_key=True, default=_uuid)
    analysis_id = Column(String(36), ForeignKey('analysis_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    mode = Column(String(50), nullable=False)
    difficulty = Column(String(50), nullable=False, default='Mixed')
    questions = Column(JSON, nullable=False, default=list)
    answers = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=_now)
    completed_at = Column(DateTime, nullable=True)


class ProofPassport(Base):
    __tablename__ = 'proof_passports'
    id = Column(String(36), primary_key=True, default=_uuid)
    analysis_id = Column(String(36), ForeignKey('analysis_runs.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    proof_id = Column(String(80), nullable=False, unique=True)
    payload = Column(JSON, nullable=False, default=dict)
    payload_hash = Column(String(64), nullable=False)
    markdown = Column(Text, nullable=False, default='')
    created_at = Column(DateTime, default=_now)
