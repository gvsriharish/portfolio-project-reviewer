import re
from typing import List, Tuple
from backend.app.analyzer.base import BaseAnalyzer, FindingResult, EvidenceItem
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

SECRET_PATTERNS: List[Tuple[str, str, str]] = [
    (r'AKIA[0-9A-Z]{16}', 'CRITICAL', 'Potential AWS Access Key ID exposed'),
    (r'sk-[a-zA-Z0-9_-]{20,}', 'CRITICAL', 'Potential OpenAI / API Secret Key exposed'),
    (r'ghp_[a-zA-Z0-9]{36}', 'CRITICAL', 'Potential GitHub Personal Access Token exposed'),
    (r'AIza[0-9A-Za-z-_]{35}', 'CRITICAL', 'Potential Google API Key exposed'),
    (r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', 'CRITICAL', 'Private Cryptographic Key exposed in repository'),
]

DANGEROUS_PATTERNS: List[Tuple[str, str, str, str, str]] = [
    (
        r'subprocess\.(?:Popen|call|run|check_output)\([^)]*shell\s*=\s*True',
        'HIGH',
        'Insecure Subprocess Execution with shell=True',
        'Using shell=True with dynamic input exposes the application to command injection attacks.',
        'Pass arguments as a list of strings and set shell=False.'
    ),
    (
        r'eval\s*\(',
        'HIGH',
        'Dangerous eval() Function Call',
        'eval() dynamically executes arbitrary strings as code, leading to Remote Code Execution (RCE).',
        'Refactor to use safe alternatives like json.loads() or ast.literal_eval().'
    ),
    (
        r'exec\s*\(',
        'HIGH',
        'Dangerous exec() Function Call',
        'exec() executes arbitrary string content with full process privileges.',
        'Avoid dynamic code execution; use structured mappings or dispatch tables.'
    ),
]

def mask_secret(secret_text: str) -> str:
    if len(secret_text) <= 8:
        return '***REDACTED***'
    return secret_text[:4] + '***REDACTED***' + secret_text[-4:]

class SecurityAnalyzer(BaseAnalyzer):
    @property
    def category_name(self) -> str:
        return "Security"

    def analyze(self, workspace: SafeRepositoryWorkspace) -> List[FindingResult]:
        findings, _ = self.analyze_with_evidence(workspace)
        return findings

    def analyze_with_evidence(
        self, workspace: SafeRepositoryWorkspace
    ) -> Tuple[List[FindingResult], List[EvidenceItem]]:
        findings: List[FindingResult] = []
        evidence: List[EvidenceItem] = []

        for rel_path in workspace.files:
            base_name = rel_path.split('/')[-1].lower()
            if base_name in ('.env', '.env.local', '.env.production', '.env.development') and not base_name.endswith(('.example', '.sample', '.template')):
                title = f"Committed Environment File Detected ({rel_path})"
                findings.append(FindingResult(
                    category=self.category_name,
                    severity="HIGH",
                    title=title,
                    file_path=rel_path,
                    line_number=1,
                    evidence=f"File committed: {rel_path}",
                    description="Actual '.env' configuration files must never be committed to version control.",
                    why_it_matters="Committed environment files frequently leak sensitive production secrets, database credentials, and API keys.",
                    recommended_fix="Add '.env*' to .gitignore and provide only a sanitized '.env.example' template.",
                    verification_method="Verify git status shows .env is ignored and not tracked."
                ))
                evidence.append(EvidenceItem(
                    finding_title=title,
                    category=self.category_name,
                    source_file=rel_path,
                    source_line=1,
                    evidence_type='FILE_MATCH',
                    evidence_summary=f"Environment file '{rel_path}' is committed to the repository.",
                    confidence='HIGH',
                    verification_status='OBSERVED',
                ))

        for rel_path in workspace.files:
            if rel_path.endswith(('.example', '.sample', '.template', '.md', '.txt', '.png', '.jpg')):
                continue

            content = workspace.read_text(rel_path)
            if not content:
                continue

            lines = content.splitlines()
            for idx, line in enumerate(lines, start=1):
                for pattern, severity, title in SECRET_PATTERNS:
                    match = re.search(pattern, line)
                    if match:
                        raw_match = match.group(0)
                        masked = mask_secret(raw_match)
                        findings.append(FindingResult(
                            category=self.category_name,
                            severity=severity,
                            title=title,
                            file_path=rel_path,
                            line_number=idx,
                            evidence=masked,
                            description="A secret or authentication token pattern was detected directly in the source file.",
                            why_it_matters="Hardcoded secrets committed to public repositories can be harvested in seconds by automated bot scanners.",
                            recommended_fix="Revoke the exposed key immediately and migrate secret retrieval to environment variables.",
                            verification_method="Re-run security analysis to confirm no secret pattern remains."
                        ))
                        evidence.append(EvidenceItem(
                            finding_title=title,
                            category=self.category_name,
                            source_file=rel_path,
                            source_line=idx,
                            evidence_type='PATTERN_MATCH',
                            evidence_summary=f"Pattern matched at {rel_path}:{idx} — value: {masked}",
                            confidence='HIGH',
                            verification_status='OBSERVED',
                        ))

                for pattern, severity, title, why, fix in DANGEROUS_PATTERNS:
                    if re.search(pattern, line):
                        snippet = line.strip()[:100]
                        findings.append(FindingResult(
                            category=self.category_name,
                            severity=severity,
                            title=title,
                            file_path=rel_path,
                            line_number=idx,
                            evidence=snippet,
                            description=f"Dangerous execution pattern detected: {title}",
                            why_it_matters=why,
                            recommended_fix=fix,
                            verification_method="Verify the dangerous call is replaced with safe parameterized alternatives."
                        ))
                        evidence.append(EvidenceItem(
                            finding_title=title,
                            category=self.category_name,
                            source_file=rel_path,
                            source_line=idx,
                            evidence_type='PATTERN_MATCH',
                            evidence_summary=f"Dangerous call pattern at {rel_path}:{idx} — {snippet}",
                            confidence='HIGH',
                            verification_status='OBSERVED',
                        ))

                cred_match = re.search(r'\b(api_key|secret_key|password|jwt_secret)\s*=\s*["\']([^"\']{10,})["\']', line, re.IGNORECASE)
                if cred_match and not any(kw in line.lower() for kw in ('os.getenv', 'os.environ', 'your-', 'example', 'dummy', 'change-me', 'test')):
                    raw_val = cred_match.group(2)
                    masked_val = mask_secret(raw_val)
                    cred_name = cred_match.group(1)
                    title = f"Hardcoded Credential Assignment '{cred_name}'"
                    findings.append(FindingResult(
                        category=self.category_name,
                        severity="HIGH",
                        title=title,
                        file_path=rel_path,
                        line_number=idx,
                        evidence=f"{cred_name} = '{masked_val}'",
                        description="Direct assignment of a credential-like string found in code.",
                        why_it_matters="Credentials in code are easily leaked when code is shared or pushed to public repositories.",
                        recommended_fix="Load credentials via environment variables or secret managers.",
                        verification_method="Confirm value is read from os.environ / pydantic BaseSettings."
                    ))
                    evidence.append(EvidenceItem(
                        finding_title=title,
                        category=self.category_name,
                        source_file=rel_path,
                        source_line=idx,
                        evidence_type='PATTERN_MATCH',
                        evidence_summary=f"Hardcoded credential '{cred_name}' at {rel_path}:{idx} — {cred_name} = '{masked_val}'",
                        confidence='HIGH',
                        verification_status='OBSERVED',
                    ))

        return findings, evidence
