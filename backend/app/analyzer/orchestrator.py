import time
from typing import List, Dict, Any, Callable, Optional, Tuple
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace
from backend.app.analyzer.base import FindingResult, EvidenceItem
from backend.app.analyzer.language_detector import LanguageDetector
from backend.app.analyzer.code_quality import CodeQualityAnalyzer
from backend.app.analyzer.security import SecurityAnalyzer
from backend.app.analyzer.documentation import DocumentationAnalyzer
from backend.app.analyzer.testing import TestingAnalyzer
from backend.app.analyzer.dependencies import DependencyAnalyzer
from backend.app.analyzer.git_hygiene import GitHygieneAnalyzer
from backend.app.analyzer.architecture import ArchitectureAnalyzer
from backend.app.analyzer.scoring import ScoringEngine

class AnalysisOrchestrator:
    def __init__(self):
        self.lang_detector = LanguageDetector()
        self.code_analyzer = CodeQualityAnalyzer()
        self.security_analyzer = SecurityAnalyzer()
        self.doc_analyzer = DocumentationAnalyzer()
        self.testing_analyzer = TestingAnalyzer()
        self.dep_analyzer = DependencyAnalyzer()
        self.git_analyzer = GitHygieneAnalyzer()
        self.arch_analyzer = ArchitectureAnalyzer()
        self.scoring_engine = ScoringEngine()

    def _run_with_evidence(
        self, analyzer, workspace: SafeRepositoryWorkspace
    ) -> Tuple[List[FindingResult], List[EvidenceItem]]:
        """Call analyze_with_evidence if the analyzer has overridden it; otherwise call analyze()."""
        return analyzer.analyze_with_evidence(workspace)

    def run_full_analysis(
        self,
        workspace: SafeRepositoryWorkspace,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()

        def update(stage: str, percent: int):
            if progress_callback:
                progress_callback(stage, percent)

        update("Detecting project languages & frameworks", 15)
        languages = self.lang_detector.detect_languages(workspace)
        frameworks = self.lang_detector.detect_frameworks(workspace)

        update("Analyzing repository structure & architecture", 30)
        arch_summary = self.arch_analyzer.inspect_architecture(workspace)
        arch_findings, arch_evidence = self._run_with_evidence(self.arch_analyzer, workspace)

        update("Analyzing code quality & AST metrics", 45)
        code_findings, code_evidence = self._run_with_evidence(self.code_analyzer, workspace)

        update("Scanning for exposed secrets & dangerous calls", 60)
        security_findings, security_evidence = self._run_with_evidence(self.security_analyzer, workspace)

        update("Evaluating README clarity & onboarding documentation", 70)
        doc_findings, doc_evidence = self._run_with_evidence(self.doc_analyzer, workspace)

        update("Inspecting test suites & coverage markers", 80)
        test_findings, test_evidence = self._run_with_evidence(self.testing_analyzer, workspace)

        update("Analyzing dependencies & git engineering hygiene", 90)
        dep_findings, dep_evidence = self._run_with_evidence(self.dep_analyzer, workspace)
        git_findings, git_evidence = self._run_with_evidence(self.git_analyzer, workspace)

        all_findings: List[FindingResult] = (
            security_findings +
            code_findings +
            doc_findings +
            test_findings +
            dep_findings +
            git_findings +
            arch_findings
        )

        all_evidence: List[EvidenceItem] = (
            security_evidence +
            code_evidence +
            doc_evidence +
            test_evidence +
            dep_evidence +
            git_evidence +
            arch_evidence
        )

        update("Calculating transparent project health score", 95)
        overall_score, category_scores = self.scoring_engine.calculate_scores(all_findings)

        duration = round(time.time() - start_time, 2)

        # Persist only deterministic, directly countable repository metrics.
        normalized = [f.replace('\\', '/') for f in workspace.files]
        test_files = [
            f for f in normalized
            if any(part.lower() in {'tests', 'test', '__tests__', 'spec', 'specs'} for part in f.split('/')[:-1])
            or f.split('/')[-1].lower().startswith('test_')
            or f.split('/')[-1].lower().endswith(('_test.py', '.test.ts', '.test.tsx', '.test.js', '.spec.ts', '.spec.js'))
        ]
        test_config_files = [
            f for f in normalized
            if f.lower().endswith(('pytest.ini', 'vitest.config.ts', 'jest.config.js'))
            or f.lower() in ('pyproject.toml', 'package.json')
        ]
        update("Deterministic analysis completed", 100)

        return {
            'languages': languages,
            'frameworks': frameworks,
            'architecture_summary': arch_summary,
            'findings': all_findings,
            'evidence_items': all_evidence,
            'overall_score': overall_score,
            'category_scores': category_scores,
            'duration_seconds': duration,
            'metrics': {
                'test_file_count': len(test_files),
                'test_config_file_count': len(test_config_files),
                'repository_file_count': len(normalized),
            }
        }
