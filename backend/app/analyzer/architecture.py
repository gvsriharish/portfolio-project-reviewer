import os
from typing import List, Dict, Any, Tuple
from backend.app.analyzer.base import BaseAnalyzer, FindingResult, EvidenceItem
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

class ArchitectureAnalyzer(BaseAnalyzer):
    @property
    def category_name(self) -> str:
        return "Architecture"

    def analyze(self, workspace: SafeRepositoryWorkspace) -> List[FindingResult]:
        findings, _ = self.analyze_with_evidence(workspace)
        return findings

    def analyze_with_evidence(
        self, workspace: SafeRepositoryWorkspace
    ) -> Tuple[List[FindingResult], List[EvidenceItem]]:
        findings: List[FindingResult] = []
        evidence: List[EvidenceItem] = []

        root_source_files = [f for f in workspace.files if '/' not in f and f.endswith(('.py', '.js', '.ts'))]
        has_structured_dirs = any('/' in f for f in workspace.files)

        if len(root_source_files) >= 6 and not has_structured_dirs:
            title = "Flat Unstructured Project Hierarchy"
            findings.append(FindingResult(
                category=self.category_name,
                severity="MEDIUM",
                title=title,
                file_path="./",
                line_number=None,
                evidence=f"{len(root_source_files)} source files located in root directory",
                description="All application source files are placed flatly in the root directory without architectural modularization.",
                why_it_matters="A flat layout hinders maintainability, component separation, and scalability as the codebase grows.",
                recommended_fix="Organize source code into dedicated packages such as 'app/', 'core/', 'services/', 'api/', or 'src/'.",
                verification_method="Group modules into layered subdirectories and update import paths."
            ))
            evidence.append(EvidenceItem(
                finding_title=title,
                category=self.category_name,
                source_file='',
                source_line=None,
                evidence_type='FILE_COUNT',
                evidence_summary=(
                    f"{len(root_source_files)} source file(s) found directly in the repository root "
                    f"with no subdirectory structure detected. "
                    f"Files: {', '.join(root_source_files[:6])}"
                    + (" …" if len(root_source_files) > 6 else "")
                ),
                confidence='MEDIUM',
                verification_status='OBSERVED',
            ))

        return findings, evidence

    def inspect_architecture(self, workspace: SafeRepositoryWorkspace) -> Dict[str, Any]:
        components: List[Dict[str, Any]] = []

        has_frontend_dir = any(f.startswith(('frontend/', 'client/', 'ui/')) for f in workspace.files)
        has_react = any(f.endswith(('.tsx', '.jsx')) for f in workspace.files)
        if has_frontend_dir or has_react:
            components.append({
                'tier': 'Frontend',
                'name': 'Client UI Layer',
                'path': 'frontend/' if has_frontend_dir else 'src/',
                'status': 'OBSERVED',
                'details': 'React/SPA interface with modular views and components'
            })

        has_backend_dir = any(f.startswith(('backend/', 'server/', 'api/')) for f in workspace.files)
        has_fastapi = any('fastapi' in (workspace.read_text(f) or '').lower() for f in workspace.files if f.endswith('.py'))
        if has_backend_dir or has_fastapi:
            components.append({
                'tier': 'Backend',
                'name': 'REST API / Application Server',
                'path': 'backend/' if has_backend_dir else 'app/',
                'status': 'OBSERVED' if has_backend_dir else 'INFERRED',
                'details': 'FastAPI / Python application server orchestrating business logic and endpoints'
            })

        has_db_layer = any('database' in f or 'models' in f or 'schema' in f for f in workspace.files)
        if has_db_layer:
            components.append({
                'tier': 'Database',
                'name': 'Data Persistence Layer',
                'path': 'models/ or database/',
                'status': 'OBSERVED',
                'details': 'Relational ORM models and database session management'
            })

        has_tests = any(f.startswith(('tests/', 'test/', '__tests__/')) or 'test_' in f for f in workspace.files)
        if has_tests:
            components.append({
                'tier': 'Tests',
                'name': 'Automated Test Suite',
                'path': 'tests/',
                'status': 'OBSERVED',
                'details': 'Unit and integration testing harness'
            })

        return {
            'components': components,
            'is_monorepo': has_frontend_dir and has_backend_dir
        }
