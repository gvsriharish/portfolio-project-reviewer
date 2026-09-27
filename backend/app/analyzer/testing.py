import os
from typing import List, Tuple
from backend.app.analyzer.base import BaseAnalyzer, FindingResult, EvidenceItem
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

TEST_DIR_PATTERNS = {'tests', 'test', '__tests__', 'spec', 'specs'}

class TestingAnalyzer(BaseAnalyzer):
    @property
    def category_name(self) -> str:
        return "Testing"

    def analyze(self, workspace: SafeRepositoryWorkspace) -> List[FindingResult]:
        findings, _ = self.analyze_with_evidence(workspace)
        return findings

    def analyze_with_evidence(
        self, workspace: SafeRepositoryWorkspace
    ) -> Tuple[List[FindingResult], List[EvidenceItem]]:
        findings: List[FindingResult] = []
        evidence: List[EvidenceItem] = []

        test_files = []
        source_files = []

        for f in workspace.files:
            parts = f.replace('\\', '/').split('/')
            filename = parts[-1].lower()

            is_test_dir = any(d in TEST_DIR_PATTERNS for d in parts[:-1])
            is_test_file = filename.startswith('test_') or filename.endswith(('_test.py', '.test.ts', '.test.tsx', '.test.js', '.spec.ts', '.spec.js'))

            if is_test_dir or is_test_file:
                test_files.append(f)
            else:
                ext = os.path.splitext(filename)[1].lower()
                if ext in ('.py', '.ts', '.tsx', '.js', '.jsx', '.go', '.rs', '.java'):
                    source_files.append(f)

        if not test_files:
            title_zero = "Zero Automated Tests in Repository"
            findings.append(FindingResult(
                category=self.category_name,
                severity="CRITICAL",
                title=title_zero,
                file_path="tests/",
                line_number=None,
                evidence="0 test files discovered",
                description="The project has no automated unit, integration, or regression test suite.",
                why_it_matters="Automated testing is the foremost technical indicator of software quality, safety, and maintainability for recruiters and senior engineers.",
                recommended_fix="Create a 'tests/' directory and implement automated tests using Pytest (Python) or Vitest/Jest (JS/TS).",
                verification_method="Add unit tests and run 'pytest' to verify all test suites execute and pass."
            ))
            evidence.append(EvidenceItem(
                finding_title=title_zero,
                category=self.category_name,
                source_file='',
                source_line=None,
                evidence_type='ABSENCE',
                evidence_summary=(
                    f"No test files detected. Scanned {len(source_files)} source file(s); "
                    f"none matched test file naming patterns (test_*, *_test.py, *.test.ts, *.spec.js)."
                ),
                confidence='HIGH',
                verification_status='INFERRED',
            ))

            title_cfg = "Missing Test Runner Configuration"
            findings.append(FindingResult(
                category=self.category_name,
                severity="HIGH",
                title=title_cfg,
                file_path="pytest.ini / jest.config.js",
                line_number=None,
                evidence="No test framework configuration detected",
                description="No configuration file or scripts found to orchestrate automated test execution.",
                why_it_matters="Developers and CI/CD pipelines cannot automatically discover and execute test targets.",
                recommended_fix="Add pytest.ini / pyproject.toml test settings or test npm scripts in package.json.",
                verification_method="Verify CI test execution command executes successfully."
            ))
            evidence.append(EvidenceItem(
                finding_title=title_cfg,
                category=self.category_name,
                source_file='',
                source_line=None,
                evidence_type='ABSENCE',
                evidence_summary=(
                    "No test runner config files found (pytest.ini, pyproject.toml [pytest], "
                    "jest.config.js, vitest.config.ts) in the repository root."
                ),
                confidence='MEDIUM',
                verification_status='INFERRED',
            ))
            return findings, evidence

        if source_files and (len(test_files) / len(source_files)) < 0.20:
            title_ratio = "Low Test-to-Source File Ratio"
            findings.append(FindingResult(
                category=self.category_name,
                severity="MEDIUM",
                title=title_ratio,
                file_path=test_files[0],
                line_number=None,
                evidence=f"{len(test_files)} test file(s) vs {len(source_files)} source file(s)",
                description="The proportion of test files relative to application source files is low (< 20%).",
                why_it_matters="Sparse test coverage increases the probability of undetected regressions and untested edge cases.",
                recommended_fix="Add unit test coverage for core business logic, services, and API endpoints.",
                verification_method="Ensure every major module has a corresponding unit test file in tests/."
            ))
            evidence.append(EvidenceItem(
                finding_title=title_ratio,
                category=self.category_name,
                source_file='',
                source_line=None,
                evidence_type='RATIO',
                evidence_summary=(
                    f"Test-to-source ratio: {len(test_files)}/{len(source_files)} = "
                    f"{len(test_files)/len(source_files):.1%} (threshold: 20%)."
                ),
                confidence='MEDIUM',
                verification_status='INFERRED',
            ))

        return findings, evidence
