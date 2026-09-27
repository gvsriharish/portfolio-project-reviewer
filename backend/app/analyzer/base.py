from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

@dataclass
class FindingResult:
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    title: str
    file_path: str
    line_number: Optional[int]
    evidence: str
    description: str
    why_it_matters: str
    recommended_fix: str
    verification_method: str

# Evidence types produced by deterministic analyzers.
EVIDENCE_TYPES = (
    'FILE_MATCH',    # A specific file was found / not found.
    'PATTERN_MATCH', # A regex pattern matched a line in a file.
    'AST_NODE',      # A Python AST node was identified.
    'ABSENCE',       # Something expected was not present.
    'FILE_COUNT',    # A count of files triggered the finding.
    'RATIO',         # A computed ratio triggered the finding.
    'CONFIG_CHECK',  # A configuration file was inspected.
)

# Verification status semantics:
#   OBSERVED   - directly detected from repository evidence.
#   INFERRED   - reasonably derived from one or more observed items,
#                but not a single directly observed fact.
#   UNVERIFIED - a claim or pattern was identified but repository
#                evidence is insufficient to confirm it.
VERIFICATION_STATUSES = ('OBSERVED', 'INFERRED', 'UNVERIFIED')

# Confidence levels.
CONFIDENCE_LEVELS = ('HIGH', 'MEDIUM', 'LOW')


@dataclass
class EvidenceItem:
    """Structured evidence record attached to a FindingResult.

    A single finding can have multiple EvidenceItem records — one per
    affected location or observation.  Secrets must be masked before
    populating evidence_summary.
    """
    finding_title: str          # Matches the parent FindingResult.title for correlation.
    category: str               # Mirror of parent finding category.
    source_file: str            # Repo-relative path; empty string for project-level items.
    evidence_type: str          # One of EVIDENCE_TYPES.
    evidence_summary: str       # Human-readable payload (secrets must be pre-masked).
    confidence: str = 'MEDIUM'  # One of CONFIDENCE_LEVELS.
    verification_status: str = 'OBSERVED'  # One of VERIFICATION_STATUSES.
    source_line: Optional[int] = None      # Line number when directly observed.


class BaseAnalyzer(ABC):
    @property
    @abstractmethod
    def category_name(self) -> str:
        pass

    @abstractmethod
    def analyze(self, workspace: SafeRepositoryWorkspace) -> List[FindingResult]:
        pass

    def analyze_with_evidence(
        self, workspace: SafeRepositoryWorkspace
    ) -> Tuple[List[FindingResult], List[EvidenceItem]]:
        """Return findings and structured evidence items.

        Default implementation calls analyze() and returns an empty evidence
        list.  Override in subclasses to emit EvidenceItem objects.
        """
        return self.analyze(workspace), []
