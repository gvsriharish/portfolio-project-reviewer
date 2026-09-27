import re
from typing import List, Tuple
from backend.app.analyzer.base import BaseAnalyzer, FindingResult, EvidenceItem
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

README_NAMES = ['README.md', 'README.rst', 'README.txt', 'README']

REQUIRED_SECTIONS = [
    ('Title / Project Statement', [r'^#\s+', r'project\s+name', r'title'], 'LOW', 'Clear project title and 1-line statement'),
    ('Problem / Overview', [r'##?\s*(?:problem|overview|about|introduction|what\s+is)'], 'MEDIUM', 'Description of problem statement and solution overview'),
    ('Tech Stack / Architecture', [r'##?\s*(?:tech(?:nology)?\s*stack|architecture|built\s+with|system\s+design)'], 'LOW', 'Summary of technologies and architectural layers'),
    ('Installation & Setup', [r'##?\s*(?:installation|getting\s+started|setup|prerequisites|requirements)'], 'HIGH', 'Step-by-step setup and installation instructions'),
    ('Environment Variables', [r'##?\s*(?:env(?:ironment)?(?:\s*variables)?|configuration|\.env)'], 'HIGH', 'Documentation of required environment variables'),
    ('Running / Usage', [r'##?\s*(?:usage|running|how\s+to\s+run|quickstart)'], 'MEDIUM', 'Commands to run and verify the application'),
    ('Screenshots / Visual Demo', [r'!\[.*?\]\(.*?\)', r'##?\s*(?:demo|screenshots?|preview|ui)'], 'INFO', 'Visual screenshots or demo links for recruiter appeal'),
    ('License', [r'##?\s*license', r'mit\s+license', r'apache\s+license'], 'LOW', 'Open source license declaration'),
]

class DocumentationAnalyzer(BaseAnalyzer):
    @property
    def category_name(self) -> str:
        return "Documentation"

    def analyze(self, workspace: SafeRepositoryWorkspace) -> List[FindingResult]:
        findings, _ = self.analyze_with_evidence(workspace)
        return findings

    def analyze_with_evidence(
        self, workspace: SafeRepositoryWorkspace
    ) -> Tuple[List[FindingResult], List[EvidenceItem]]:
        findings: List[FindingResult] = []
        evidence: List[EvidenceItem] = []

        readme_path = None
        readme_content = None
        for name in README_NAMES:
            if workspace.exists(name):
                readme_path = name
                readme_content = workspace.read_text(name)
                break

        if not readme_path or not readme_content or len(readme_content.strip()) < 50:
            title = "Missing or Empty README.md"
            findings.append(FindingResult(
                category=self.category_name,
                severity="CRITICAL",
                title=title,
                file_path=readme_path or "README.md",
                line_number=1,
                evidence="File not found or fewer than 50 characters",
                description="The repository lacks a functional README document.",
                why_it_matters="A README is the single most important onboarding and evaluation document for recruiters and open-source contributors.",
                recommended_fix="Create a comprehensive README.md including project overview, setup steps, tech stack, and usage.",
                verification_method="Add a structured README.md and re-run analysis."
            ))
            evidence.append(EvidenceItem(
                finding_title=title,
                category=self.category_name,
                source_file=readme_path or "README.md",
                source_line=None,
                evidence_type='ABSENCE',
                evidence_summary=(
                    "README.md is absent from the repository root."
                    if not readme_path
                    else f"README.md exists but contains fewer than 50 characters ({len((readme_content or '').strip())} chars)."
                ),
                confidence='HIGH',
                verification_status='INFERRED',
            ))
            return findings, evidence

        placeholder_matches = re.findall(r'(TODO|FIXME|REPLACE_ME|YOUR_API_KEY_HERE|Lorem ipsum)', readme_content, re.IGNORECASE)
        if placeholder_matches:
            title = "Template / Placeholder Text in README"
            findings.append(FindingResult(
                category=self.category_name,
                severity="MEDIUM",
                title=title,
                file_path=readme_path,
                line_number=1,
                evidence=f"Found placeholder tokens: {', '.join(set(placeholder_matches))}",
                description="The README contains unfilled placeholder or template tokens.",
                why_it_matters="Unfinished template text gives recruiters the impression of an incomplete or abandoned project.",
                recommended_fix="Replace all TODO and template markers with accurate project details.",
                verification_method="Search README.md for TODO / template keywords."
            ))
            evidence.append(EvidenceItem(
                finding_title=title,
                category=self.category_name,
                source_file=readme_path,
                source_line=None,
                evidence_type='PATTERN_MATCH',
                evidence_summary=f"Placeholder tokens found in {readme_path}: {', '.join(set(placeholder_matches))}",
                confidence='HIGH',
                verification_status='OBSERVED',
            ))

        for section_name, patterns, severity, rationale in REQUIRED_SECTIONS:
            found = False
            for pat in patterns:
                if re.search(pat, readme_content, re.IGNORECASE | re.MULTILINE):
                    found = True
                    break

            if not found:
                title = f"Missing Documentation: {section_name}"
                findings.append(FindingResult(
                    category=self.category_name,
                    severity=severity,
                    title=title,
                    file_path=readme_path,
                    line_number=1,
                    evidence=f"Section '{section_name}' not detected in {readme_path}",
                    description=f"The README does not clearly provide a section for {section_name}.",
                    why_it_matters=f"{rationale}. Missing this makes it hard for new engineers or recruiters to evaluate the project.",
                    recommended_fix=f"Add a dedicated '## {section_name}' section to {readme_path}.",
                    verification_method=f"Check {readme_path} for '{section_name}' header and clear guidance."
                ))
                evidence.append(EvidenceItem(
                    finding_title=title,
                    category=self.category_name,
                    source_file=readme_path,
                    source_line=None,
                    evidence_type='ABSENCE',
                    evidence_summary=(
                        f"Section '{section_name}' not found in {readme_path} "
                        f"after searching {len(patterns)} pattern(s)."
                    ),
                    confidence='LOW',
                    verification_status='INFERRED',
                ))

        return findings, evidence
