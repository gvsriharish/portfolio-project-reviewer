import ast
import re
from typing import List, Tuple
from backend.app.analyzer.base import BaseAnalyzer, FindingResult, EvidenceItem
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

class CodeQualityAnalyzer(BaseAnalyzer):
    @property
    def category_name(self) -> str:
        return "Code Quality"

    def analyze(self, workspace: SafeRepositoryWorkspace) -> List[FindingResult]:
        findings, _ = self.analyze_with_evidence(workspace)
        return findings

    def analyze_with_evidence(
        self, workspace: SafeRepositoryWorkspace
    ) -> Tuple[List[FindingResult], List[EvidenceItem]]:
        findings: List[FindingResult] = []
        evidence: List[EvidenceItem] = []

        for rel_path in workspace.files:
            content = workspace.read_text(rel_path)
            if not content:
                continue

            if rel_path.endswith('.py'):
                f, e = self._analyze_python_with_evidence(rel_path, content)
                findings.extend(f)
                evidence.extend(e)
            elif rel_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                f, e = self._analyze_javascript_with_evidence(rel_path, content)
                findings.extend(f)
                evidence.extend(e)

        return findings, evidence

    def _analyze_python_with_evidence(
        self, file_path: str, content: str
    ) -> Tuple[List[FindingResult], List[EvidenceItem]]:
        findings: List[FindingResult] = []
        evidence: List[EvidenceItem] = []
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            title = "Python Syntax Error"
            findings.append(FindingResult(
                category=self.category_name,
                severity="CRITICAL",
                title=title,
                file_path=file_path,
                line_number=e.lineno,
                evidence=f"SyntaxError: {e.msg}",
                description="The Python file contains invalid syntax and will fail during execution or compilation.",
                why_it_matters="Files with syntax errors prevent the entire module or application from running.",
                recommended_fix=f"Review line {e.lineno} and resolve the invalid syntax.",
                verification_method=f"Run 'python -m py_compile {file_path}' to verify clean compilation."
            ))
            evidence.append(EvidenceItem(
                finding_title=title,
                category=self.category_name,
                source_file=file_path,
                source_line=e.lineno,
                evidence_type='AST_NODE',
                evidence_summary=f"SyntaxError: {e.msg} at line {e.lineno} in {file_path}",
                confidence='HIGH',
                verification_status='OBSERVED',
            ))
            return findings, evidence

        for node in ast.walk(tree):
            # 1. Bare except
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    title = "Bare 'except:' Clause"
                    findings.append(FindingResult(
                        category=self.category_name,
                        severity="HIGH",
                        title=title,
                        file_path=file_path,
                        line_number=node.lineno,
                        evidence="except:",
                        description="A bare 'except:' clause catches all exceptions indiscriminately, including SystemExit and KeyboardInterrupt.",
                        why_it_matters="Suppresses bugs, prevents graceful process termination, and complicates debugging.",
                        recommended_fix="Specify exact exception types (e.g. 'except ValueError:' or 'except Exception as e:').",
                        verification_method="Verify that all exception handlers specify concrete exception classes."
                    ))
                    evidence.append(EvidenceItem(
                        finding_title=title,
                        category=self.category_name,
                        source_file=file_path,
                        source_line=node.lineno,
                        evidence_type='AST_NODE',
                        evidence_summary=f"Bare 'except:' handler at {file_path}:{node.lineno}",
                        confidence='HIGH',
                        verification_status='OBSERVED',
                    ))

            # 2. Wildcard imports
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == '*':
                        title = "Wildcard Import Used"
                        findings.append(FindingResult(
                            category=self.category_name,
                            severity="LOW",
                            title=title,
                            file_path=file_path,
                            line_number=node.lineno,
                            evidence=f"from {node.module} import *",
                            description="Wildcard imports pollute the module namespace and make it difficult to trace symbol definitions.",
                            why_it_matters="Causes unexpected name collisions and breaks static analysis and linter tooling.",
                            recommended_fix="Import only the specific functions or classes required.",
                            verification_method="Run a linter like Ruff or Flake8 to ensure no wildcard imports remain."
                        ))
                        evidence.append(EvidenceItem(
                            finding_title=title,
                            category=self.category_name,
                            source_file=file_path,
                            source_line=node.lineno,
                            evidence_type='AST_NODE',
                            evidence_summary=f"Wildcard import 'from {node.module} import *' at {file_path}:{node.lineno}",
                            confidence='HIGH',
                            verification_status='OBSERVED',
                        ))

            # 3. Oversized functions (> 30 lines)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                if length >= 30:
                    title = f"Oversized Function '{node.name}' ({length} lines)"
                    findings.append(FindingResult(
                        category=self.category_name,
                        severity="MEDIUM",
                        title=title,
                        file_path=file_path,
                        line_number=node.lineno,
                        evidence=f"def {node.name}(...): spans lines {node.lineno} to {node.end_lineno}",
                        description=f"Function '{node.name}' exceeds 30 lines of code ({length} lines), indicating multiple mixed responsibilities.",
                        why_it_matters="Long functions increase cognitive complexity, reduce testability, and hide subtle bugs.",
                        recommended_fix="Refactor the function into smaller, single-purpose helper functions.",
                        verification_method="Ensure individual functions stay under 30 lines."
                    ))
                    evidence.append(EvidenceItem(
                        finding_title=title,
                        category=self.category_name,
                        source_file=file_path,
                        source_line=node.lineno,
                        evidence_type='AST_NODE',
                        evidence_summary=(
                            f"Function '{node.name}' spans {length} lines "
                            f"({file_path}:{node.lineno}–{node.end_lineno})"
                        ),
                        confidence='HIGH',
                        verification_status='OBSERVED',
                    ))

        # Check for lingering debug print statements in non-script files
        if not file_path.startswith(('scripts/', 'tests/')) and 'test' not in file_path.lower():
            lines = content.splitlines()
            for idx, line in enumerate(lines, start=1):
                if re.search(r'^\s*print\s*\(', line) and not line.strip().startswith('#'):
                    title = "Leftover Print Statement in Production Code"
                    findings.append(FindingResult(
                        category=self.category_name,
                        severity="INFO",
                        title=title,
                        file_path=file_path,
                        line_number=idx,
                        evidence=line.strip()[:100],
                        description="Direct 'print()' statement detected in application source code.",
                        why_it_matters="Standard logging frameworks should be used for production observability instead of stdout prints.",
                        recommended_fix="Replace print statements with Python standard library 'logging.getLogger()'.",
                        verification_method="Ensure no raw print() calls exist outside CLI scripts."
                    ))
                    evidence.append(EvidenceItem(
                        finding_title=title,
                        category=self.category_name,
                        source_file=file_path,
                        source_line=idx,
                        evidence_type='PATTERN_MATCH',
                        evidence_summary=f"print() call at {file_path}:{idx} — {line.strip()[:80]}",
                        confidence='HIGH',
                        verification_status='OBSERVED',
                    ))
                    break

        return findings, evidence

    def _analyze_javascript_with_evidence(
        self, file_path: str, content: str
    ) -> Tuple[List[FindingResult], List[EvidenceItem]]:
        findings: List[FindingResult] = []
        evidence: List[EvidenceItem] = []
        lines = content.splitlines()

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith('//') or trimmed.startswith('/*'):
                continue

            if re.search(r'console\.log\s*\(', line) and not file_path.startswith(('scripts/', 'tests/')):
                title = "Console.log Leftover in Production Code"
                findings.append(FindingResult(
                    category=self.category_name,
                    severity="INFO",
                    title=title,
                    file_path=file_path,
                    line_number=idx,
                    evidence=trimmed[:100],
                    description="A console.log statement was found in frontend/JavaScript source code.",
                    why_it_matters="Unnecessary console logs can leak sensitive internal state to browser dev tools.",
                    recommended_fix="Remove debugging console.log statements before building for production.",
                    verification_method="Run ESLint with no-console rule enabled."
                ))
                evidence.append(EvidenceItem(
                    finding_title=title,
                    category=self.category_name,
                    source_file=file_path,
                    source_line=idx,
                    evidence_type='PATTERN_MATCH',
                    evidence_summary=f"console.log() at {file_path}:{idx} — {trimmed[:80]}",
                    confidence='HIGH',
                    verification_status='OBSERVED',
                ))
                break

            if re.search(r'var\s+[a-zA-Z_$][a-zA-Z0-9_$]*\s*=', line):
                title = "Legacy 'var' Declaration Used"
                findings.append(FindingResult(
                    category=self.category_name,
                    severity="LOW",
                    title=title,
                    file_path=file_path,
                    line_number=idx,
                    evidence=trimmed[:100],
                    description="Legacy 'var' keyword used instead of block-scoped 'const' or 'let'.",
                    why_it_matters="'var' has function scope and is subject to hoisting quirks, leading to subtle scope bugs.",
                    recommended_fix="Replace 'var' with 'const' (for immutable bindings) or 'let' (for reassignable variables).",
                    verification_method="Verify code passes TypeScript/ESLint modern ES6+ linting."
                ))
                evidence.append(EvidenceItem(
                    finding_title=title,
                    category=self.category_name,
                    source_file=file_path,
                    source_line=idx,
                    evidence_type='PATTERN_MATCH',
                    evidence_summary=f"'var' declaration at {file_path}:{idx} — {trimmed[:80]}",
                    confidence='HIGH',
                    verification_status='OBSERVED',
                ))
                break

        return findings, evidence
