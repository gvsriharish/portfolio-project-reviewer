from typing import List, Tuple
from backend.app.analyzer.base import BaseAnalyzer, FindingResult, EvidenceItem
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

CRITICAL_IGNORES = ['.env', 'node_modules', '__pycache__', '.venv', 'dist']

class GitHygieneAnalyzer(BaseAnalyzer):
    @property
    def category_name(self) -> str:
        return "Git Hygiene"

    def analyze(self, workspace: SafeRepositoryWorkspace) -> List[FindingResult]:
        findings, _ = self.analyze_with_evidence(workspace)
        return findings

    def analyze_with_evidence(
        self, workspace: SafeRepositoryWorkspace
    ) -> Tuple[List[FindingResult], List[EvidenceItem]]:
        findings: List[FindingResult] = []
        evidence: List[EvidenceItem] = []

        gitignore_content = workspace.read_text('.gitignore')
        if gitignore_content is None:
            title = "Missing .gitignore File"
            findings.append(FindingResult(
                category=self.category_name,
                severity="HIGH",
                title=title,
                file_path=".gitignore",
                line_number=None,
                evidence="File .gitignore does not exist in repository root",
                description="The repository lacks a .gitignore configuration file.",
                why_it_matters="Without a .gitignore, temporary build artifacts, compiled bytecode, virtual environments, and sensitive .env files can be accidentally committed.",
                recommended_fix="Add a comprehensive .gitignore tailored to your project tech stack (Python/Node/OS).",
                verification_method="Add .gitignore and verify untracked temporary files are ignored by git."
            ))
            evidence.append(EvidenceItem(
                finding_title=title,
                category=self.category_name,
                source_file='.gitignore',
                source_line=None,
                evidence_type='ABSENCE',
                evidence_summary=".gitignore file is absent from the repository root.",
                confidence='HIGH',
                verification_status='INFERRED',
            ))
        else:
            missing_ignores = [item for item in CRITICAL_IGNORES if item not in gitignore_content]
            if len(missing_ignores) >= 2:
                title = "Incomplete .gitignore Rules"
                findings.append(FindingResult(
                    category=self.category_name,
                    severity="LOW",
                    title=title,
                    file_path=".gitignore",
                    line_number=1,
                    evidence=f"Missing standard ignore rules for: {', '.join(missing_ignores)}",
                    description=".gitignore is missing rules for common build or secret patterns.",
                    why_it_matters="Prevents cluttering the repository with virtual environments, build artifacts, or secret files.",
                    recommended_fix="Add standard patterns (.env, node_modules/, __pycache__/, .venv/) to .gitignore.",
                    verification_method="Check .gitignore covers all local build output directories."
                ))
                evidence.append(EvidenceItem(
                    finding_title=title,
                    category=self.category_name,
                    source_file='.gitignore',
                    source_line=1,
                    evidence_type='CONFIG_CHECK',
                    evidence_summary=(
                        f".gitignore is missing {len(missing_ignores)} standard patterns: "
                        f"{', '.join(missing_ignores)}."
                    ),
                    confidence='MEDIUM',
                    verification_status='OBSERVED',
                ))

        has_license = any(workspace.exists(f) for f in ['LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENCE'])
        if not has_license:
            title = "Missing Open Source LICENSE"
            findings.append(FindingResult(
                category=self.category_name,
                severity="MEDIUM",
                title=title,
                file_path="LICENSE",
                line_number=None,
                evidence="No LICENSE file found in repository root",
                description="The repository has no explicit open source license attached.",
                why_it_matters="Without an explicit license, standard copyright applies by default, preventing others from legally using or contributing to the project.",
                recommended_fix="Add a standard open source license such as MIT, Apache-2.0, or BSD.",
                verification_method="Add a LICENSE file to the root of the repository."
            ))
            evidence.append(EvidenceItem(
                finding_title=title,
                category=self.category_name,
                source_file='LICENSE',
                source_line=None,
                evidence_type='ABSENCE',
                evidence_summary=(
                    "No LICENSE, LICENSE.md, LICENSE.txt, or LICENCE file found in the repository root."
                ),
                confidence='HIGH',
                verification_status='INFERRED',
            ))

        return findings, evidence
