import re
from typing import List, Tuple
from backend.app.analyzer.base import BaseAnalyzer, FindingResult, EvidenceItem
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

class DependencyAnalyzer(BaseAnalyzer):
    @property
    def category_name(self) -> str:
        return "Dependencies"

    def analyze(self, workspace: SafeRepositoryWorkspace) -> List[FindingResult]:
        findings, _ = self.analyze_with_evidence(workspace)
        return findings

    def analyze_with_evidence(
        self, workspace: SafeRepositoryWorkspace
    ) -> Tuple[List[FindingResult], List[EvidenceItem]]:
        findings: List[FindingResult] = []
        evidence: List[EvidenceItem] = []
        manifest_found = False

        req_content = workspace.read_text('requirements.txt')
        if req_content is not None:
            manifest_found = True
            lines = req_content.splitlines()
            unpinned = []
            for idx, line in enumerate(lines, start=1):
                clean = line.strip()
                if not clean or clean.startswith('#') or clean.startswith('-'):
                    continue
                if re.match(r'^[a-zA-Z0-9_\-\.]+$', clean):
                    unpinned.append((idx, clean))

            if unpinned:
                sample_unpinned = ', '.join([pkg for _, pkg in unpinned[:4]])
                title = "Unpinned Python Dependencies in requirements.txt"
                findings.append(FindingResult(
                    category=self.category_name,
                    severity="MEDIUM",
                    title=title,
                    file_path="requirements.txt",
                    line_number=unpinned[0][0],
                    evidence=f"Unpinned packages: {sample_unpinned}",
                    description=f"Found {len(unpinned)} package(s) without pinned version numbers in requirements.txt.",
                    why_it_matters="Unpinned packages allow breaking upstream releases to cause non-deterministic build failures.",
                    recommended_fix="Pin package versions using exact (==) or minimum compatible (~=) version constraints.",
                    verification_method="Run 'pip freeze > requirements.txt' or use poetry/pip-tools for deterministic locking."
                ))
                # Emit one EvidenceItem per unpinned package (all affected locations).
                for line_no, pkg in unpinned:
                    evidence.append(EvidenceItem(
                        finding_title=title,
                        category=self.category_name,
                        source_file='requirements.txt',
                        source_line=line_no,
                        evidence_type='FILE_MATCH',
                        evidence_summary=f"Package '{pkg}' at requirements.txt:{line_no} has no version constraint.",
                        confidence='HIGH',
                        verification_status='OBSERVED',
                    ))

        pkg_content = workspace.read_text('package.json') or workspace.read_text('frontend/package.json')
        pkg_file = 'package.json' if workspace.read_text('package.json') else 'frontend/package.json'
        if pkg_content is not None:
            manifest_found = True
            if '"*"' in pkg_content:
                title = "Wildcard (*) Dependency in package.json"
                findings.append(FindingResult(
                    category=self.category_name,
                    severity="HIGH",
                    title=title,
                    file_path="package.json",
                    line_number=1,
                    evidence='"*" version constraint detected',
                    description="Wildcard (*) dependencies pull in the latest arbitrary package version on every install.",
                    why_it_matters="Exposes builds to breaking API changes and upstream supply chain attacks.",
                    recommended_fix="Specify standard semver caret (^) or pinned versions.",
                    verification_method="Verify package.json contains explicit semver version strings."
                ))
                evidence.append(EvidenceItem(
                    finding_title=title,
                    category=self.category_name,
                    source_file=pkg_file,
                    source_line=None,
                    evidence_type='FILE_MATCH',
                    evidence_summary=f'Wildcard "*" version constraint found in {pkg_file}.',
                    confidence='HIGH',
                    verification_status='OBSERVED',
                ))

        if not manifest_found:
            title = "Missing Dependency Manifest File"
            findings.append(FindingResult(
                category=self.category_name,
                severity="HIGH",
                title=title,
                file_path="requirements.txt / package.json",
                line_number=None,
                evidence="No dependency manifest (requirements.txt, pyproject.toml, package.json) found",
                description="The project has no declarative dependency manifest file.",
                why_it_matters="Without a dependency manifest, other developers cannot install prerequisites or run the project.",
                recommended_fix="Add a 'requirements.txt' for Python or 'package.json' for JavaScript/Node.",
                verification_method="Verify that a fresh environment can install dependencies with a single command."
            ))
            evidence.append(EvidenceItem(
                finding_title=title,
                category=self.category_name,
                source_file='',
                source_line=None,
                evidence_type='ABSENCE',
                evidence_summary=(
                    "Neither requirements.txt, pyproject.toml, nor package.json found in the repository root."
                ),
                confidence='HIGH',
                verification_status='INFERRED',
            ))

        return findings, evidence
