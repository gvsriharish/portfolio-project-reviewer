"""Phase 2 — Claim Auditor response schemas."""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from backend.app.schemas.evidence import EvidenceItemSchema
from backend.app.schemas.analysis import FindingSchema


class ClaimSchema(BaseModel):
    id: str
    claim_text: str
    normalized_claim: str = ''
    source_file: str = ''
    source_line: Optional[int] = None
    category: str
    status: str
    confidence: str
    explanation: str = ''
    evidence_count: int = 0
    related_findings: List[FindingSchema] = []
    evidence_items: List[EvidenceItemSchema] = []
    created_at: Optional[datetime] = None


class ClaimStatsSchema(BaseModel):
    total: int = 0
    supported: int = 0
    partially_supported: int = 0
    unverified: int = 0
    contradicted: int = 0


class ClaimSummaryResponse(BaseModel):
    stats: ClaimStatsSchema
    claims: List[ClaimSchema]


class ReanalyzeResponse(BaseModel):
    analysis_id: str
    claims_extracted: int
    stats: ClaimStatsSchema
