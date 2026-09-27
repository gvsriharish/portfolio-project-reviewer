from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from backend.app.schemas.evidence import EvidenceItemSchema

class AnalyzeRequest(BaseModel):
    github_url: str = Field(..., description='Public GitHub repository URL or sample identifier')
    use_ai: bool = Field(True, description='Whether to generate AI-powered grounded explanations')

    @field_validator('github_url')
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Repository URL or identifier is required')
        if len(v) > 512:
            raise ValueError('URL is too long')
        from backend.app.services.repo_fetcher import parse_github_url, RepositoryFetchError
        try:
            parse_github_url(v)
        except RepositoryFetchError as exc:
            raise ValueError(str(exc)) from None
        return v

class FindingSchema(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    finding_key: Optional[str] = None
    status: Optional[str] = None
    before_severity: Optional[str] = None
    after_severity: Optional[str] = None
    before_id: Optional[str] = None
    after_id: Optional[str] = None
    match_method: Optional[str] = None
    file_path: str
    line_number: Optional[int] = None
    evidence: str
    description: str
    why_it_matters: str
    recommended_fix: str
    verification_method: str
    # Structured evidence items — populated when include_evidence=true is requested.
    # Empty list preserves backward compatibility with existing consumers.
    evidence_items: List[EvidenceItemSchema] = Field(default_factory=list)

class CategoryScoreSchema(BaseModel):
    category: str
    score: int
    max_score: int = 100
    findings_count: int
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    penalty_breakdown: List[str] = Field(default_factory=list)
    summary: str = ''

class RecommendationSchema(BaseModel):
    id: str
    priority_group: str
    rank: int
    title: str
    action: str
    reason: str
    verification: str
    finding_id: Optional[str] = None
    status: str = 'OPEN'
    expected_change: str = ''

class InterviewQuestionSchema(BaseModel):
    id: str
    level: str
    category: str
    question: str
    context_reason: str
    sample_answer_guideline: str

class ComponentItem(BaseModel):
    name: str
    tier: str
    path: str
    status: str
    details: str

class KeyFileItem(BaseModel):
    file_path: str
    purpose: str
    significance: str

class ProjectExplanationSchema(BaseModel):
    summary: str
    architecture_narrative: str
    main_components: List[ComponentItem] = Field(default_factory=list)
    data_flow: List[str] = Field(default_factory=list)
    key_files: List[KeyFileItem] = Field(default_factory=list)
    technical_decisions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)

class AnalysisResponse(BaseModel):
    id: str
    repo_url: str
    repo_name: str
    owner: str
    status: str
    current_stage: str
    progress_percent: int
    overall_score: int
    category_scores: Dict[str, CategoryScoreSchema] = Field(default_factory=dict)
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    architecture_summary: Dict[str, Any] = Field(default_factory=dict)
    findings: List[FindingSchema] = Field(default_factory=list)
    recommendations: List[RecommendationSchema] = Field(default_factory=list)
    interview_questions: List[InterviewQuestionSchema] = Field(default_factory=list)
    project_explanation: Optional[ProjectExplanationSchema] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    is_sample: bool = False
    created_at: Optional[datetime] = None

class CategoryDeltaSchema(BaseModel):
    category: str
    before_score: int
    after_score: int
    delta: int
    findings_before: int
    findings_after: int

class VerificationResultSchema(BaseModel):
    id: str
    finding_key: str
    method: str
    result: str
    details: str
    recommendation_id: Optional[str] = None


class ComparisonResponse(BaseModel):
    before_id: str
    after_id: str
    before_repo: str
    after_repo: str
    overall_score_before: int
    overall_score_after: int
    overall_score_delta: int
    category_deltas: Dict[str, CategoryDeltaSchema] = Field(default_factory=dict)
    resolved_findings: List[FindingSchema] = Field(default_factory=list)
    new_findings: List[FindingSchema] = Field(default_factory=list)
    persistent_findings: List[FindingSchema] = Field(default_factory=list)
    changed_findings: List[FindingSchema] = Field(default_factory=list)
    verification_results: List[VerificationResultSchema] = Field(default_factory=list)
    summary: str = ''

class SampleProjectInfo(BaseModel):
    id: str
    name: str
    description: str
    expected_score_range: str
    key_traits: List[str]
