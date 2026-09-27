import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database.base import Base

def generate_uuid():
    return str(uuid.uuid4())

class AnalysisRun(Base):
    __tablename__ = 'analysis_runs'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    repo_url = Column(String(500), nullable=False)
    repo_name = Column(String(200), nullable=False, default='Unknown')
    owner = Column(String(200), nullable=False, default='Unknown')
    
    status = Column(String(50), nullable=False, default='QUEUED')
    current_stage = Column(String(200), nullable=False, default='Queued for analysis')
    progress_percent = Column(Integer, default=0)
    
    overall_score = Column(Integer, default=0)
    category_scores = Column(JSON, default=dict)
    languages = Column(JSON, default=list)
    frameworks = Column(JSON, default=list)
    architecture_summary = Column(JSON, default=dict)
    # Deterministic measurable repository metrics (never LLM-generated).
    metrics = Column(JSON, default=dict)
    
    duration_seconds = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    is_sample = Column(Boolean, default=False)
    # Populated only when safely available from repository metadata; never fabricated.
    commit_sha = Column(String(100), nullable=True)
    branch = Column(String(200), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    findings = relationship('Finding', back_populates='analysis', cascade='all, delete-orphan')
    recommendations = relationship('Recommendation', back_populates='analysis', cascade='all, delete-orphan')
    interview_questions = relationship('InterviewQuestion', back_populates='analysis', cascade='all, delete-orphan')
    project_explanation = relationship('ProjectExplanation', back_populates='analysis', uselist=False, cascade='all, delete-orphan')

class Finding(Base):
    __tablename__ = 'findings'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey('analysis_runs.id'), nullable=False)
    
    category = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    title = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)
    line_number = Column(Integer, nullable=True)
    
    evidence = Column(Text, nullable=False, default='')
    description = Column(Text, nullable=False, default='')
    why_it_matters = Column(Text, nullable=False, default='')
    recommended_fix = Column(Text, nullable=False, default='')
    verification_method = Column(Text, nullable=False, default='')

    # Deterministic stable identifier (category.rule.path). Titles are not
    # unique and must not be used to relate evidence/claims to findings.
    # Nullable for backwards compatibility with Phase 1 rows.
    finding_key = Column(String(300), nullable=True, index=True)

    analysis = relationship('AnalysisRun', back_populates='findings')
    evidence_items = relationship(
        'FindingEvidence',
        back_populates='finding',
        cascade='all, delete-orphan',
        lazy='dynamic',
    )

class Recommendation(Base):
    __tablename__ = 'recommendations'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey('analysis_runs.id'), nullable=False)

    priority_group = Column(String(50), nullable=False)
    rank = Column(Integer, nullable=False, default=1)
    title = Column(String(300), nullable=False)
    action = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    verification = Column(Text, nullable=False)

    # Finding → Fix → Verify chain (Phase 3). Nullable: AI-generated
    # roadmap items and legacy Phase 1 rows are not finding-backed.
    finding_id = Column(String(36), ForeignKey('findings.id'), nullable=True, index=True)
    # Lifecycle: OPEN | IN_PROGRESS | RESOLVED | STILL_PRESENT
    status = Column(String(30), nullable=False, default='OPEN')
    expected_change = Column(Text, nullable=False, default='')

    analysis = relationship('AnalysisRun', back_populates='recommendations')

class InterviewQuestion(Base):
    __tablename__ = 'interview_questions'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey('analysis_runs.id'), nullable=False)
    
    level = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False, default='Architecture')
    question = Column(Text, nullable=False)
    context_reason = Column(Text, nullable=False)
    sample_answer_guideline = Column(Text, nullable=False)

    analysis = relationship('AnalysisRun', back_populates='interview_questions')

class ProjectExplanation(Base):
    __tablename__ = 'project_explanations'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey('analysis_runs.id'), nullable=False)
    
    summary = Column(Text, nullable=False)
    architecture_narrative = Column(Text, nullable=False)
    main_components = Column(JSON, default=list)
    data_flow = Column(JSON, default=list)
    key_files = Column(JSON, default=list)
    technical_decisions = Column(JSON, default=list)
    limitations = Column(JSON, default=list)

    analysis = relationship('AnalysisRun', back_populates='project_explanation')
