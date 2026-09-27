from typing import Optional
from pydantic import BaseModel


class EvidenceItemSchema(BaseModel):
    """Pydantic v2 response schema for a single structured evidence record.

    Returned by GET /api/analysis/{analysis_id}/findings/{finding_id}/evidence
    and optionally embedded in FindingSchema when include_evidence=true.
    """
    id: str
    finding_id: str
    category: str
    source_file: str
    source_line: Optional[int] = None
    evidence_type: str
    evidence_summary: str
    confidence: str
    verification_status: str

    model_config = {"from_attributes": True}
