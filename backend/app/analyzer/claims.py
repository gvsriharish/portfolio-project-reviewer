"""Phase 2 — Project Claim Auditor (fully deterministic).

Extracts technical claims from README / documentation files and verifies
each claim against repository evidence produced by the deterministic
analyzers.

SECURITY MODEL
--------------
README files and documentation are UNTRUSTED DATA. Their text is only
scanned with regular expressions. Instructions contained in a README are
never followed, repository code is never executed, and no LLM participates
in deciding claim truth. AI (if enabled elsewhere) may only *explain* the
deterministic verdict after it has been established.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from backend.app.analyzer.base import FindingResult, EvidenceItem
from backend.app.services.repo_fetcher import SafeRepositoryWorkspace

CLAIM_STATUSES = ('SUPPORTED', 'PARTIALLY_SUPPORTED', 'UNVERIFIED', 'CONTRADICTED')
CLAIM_CATEGORIES = (
    'TECHNOLOGY', 'ARCHITECTURE', 'SECURITY', 'TESTING', 'DEPLOYMENT',
    'DATABASE', 'AI_ML', 'API', 'PERFORMANCE', 'FEATURE', 'QUALITY', 'OTHER',
)

README_CANDIDATES = ['README.md', 'README.rst', 'README.txt', 'README']
DOC_CANDIDATES = ['docs/README.md']

# Dependency manifests that constitute primary evidence for a technology.
DEP_FILES = ['requirements.txt', 'pyproject.toml', 'package.json', 'frontend/package.json']
# Directories/files treated as documentation (claims live here; they are not evidence).
DOC_PREFIXES = ('readme', 'docs/', 'doc/', 'contributing', 'changelog', 'license', 'code_of_conduct')

MAX_CLAIMS = 40
MAX_SENTENCE_LEN = 400

CI_FILES = [
    '.github/workflows', '.gitlab-ci.yml', '.circleci', 'azure-pipelines.yml',
    'Jenkinsfile', '.travis.yml', 'bitbucket-pipelines.yml',
]
DEPLOY_FILES = ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml', '.dockerignore']
COVERAGE_CONFIG_FILES = ['.coveragerc', 'pytest.ini', 'setup.cfg', 'tox.ini', 'pyproject.toml']
COVERAGE_DEP_TOKENS = ('pytest-cov', 'coverage', 'codecov', 'coveralls')
CRYPTO_TOKENS = ('cryptography', 'bcrypt', 'fernet', 'passlib', 'pynacl', 'jose', 'pyjwt', 'jwt')

TECH_TOKENS: Dict[str, Tuple[str, ...]] = {
    'fastapi': ('fastapi',),
    'flask': ('flask',),
    'django': ('django',),
    'sqlalchemy': ('sqlalchemy',),
    'postgresql': ('postgresql', 'psycopg2', 'psycopg', 'postgres'),
    'mysql': ('mysql', 'pymysql'),
    'mongodb': ('mongodb', 'pymongo', 'motor'),
    'sqlite': ('sqlite',),
    'redis': ('redis',),
    'react': ('react',),
    'vue': ('vue',),
    'svelte': ('svelte',),
    'angular': ('angular',),
    'express': ('express',),
    'next.js': ('next.js', 'next/'),
    'docker': ('docker',),
    'kubernetes': ('kubernetes', 'kubectl', 'k8s'),
    'celery': ('celery',),
    'pytest': ('pytest',),
    'jwt': ('jwt', 'pyjwt', 'jsonwebtoken'),
    'graphql': ('graphql', 'ariadne', 'strawberry-graphql'),
    'pydantic': ('pydantic',),
    'pytorch': ('pytorch', 'torch'),
    'tensorflow': ('tensorflow',),
    'scikit-learn': ('scikit-learn', 'sklearn'),
    'pandas': ('pandas',),
    'numpy': ('numpy',),
    'websockets': ('websockets', 'websocket'),
    'oauth': ('oauth', 'authlib'),
}

COVERAGE_RE = re.compile(r'\b\d+(?:\.\d+)?\s*%\s*(?:test\s*)?coverage|\bcoverage\b[^.\n]{0,40}\b\d+(?:\.\d+)?\s*%', re.I)
TESTING_RE = re.compile(r'\b(?:automated tests?|test suite|unit tests?|integration tests?|end.to.end tests?|tested|testing)\b', re.I)
STRONG_TEST_RE = re.compile(r'\b(?:fully|all|every|complete(?:ly)?|100\s*%|comprehensive)\b.*\b(?:tested|testing|coverage|tests?)\b|\b(?:tested|testing|coverage|tests?)\b.*\b(?:fully|all|every|complete(?:ly)?)\b', re.I)
CICD_RE = re.compile(r'\bCI/?CD\b|continuous\s+(?:integration|deployment)|github\s+actions|gitlab\s+ci', re.I)
SECURITY_NEG_RE = re.compile(r'no\s+(?:exposed\s+)?(?:secrets?|credentials|api\s+keys?)|secure[d]?|security\s+best\s+practices?|hardened', re.I)
ENCRYPT_RE = re.compile(r'\bencrypt\w*|\bhash(?:ed|ing)?\s+passwords?\b', re.I)
AUTH_RE = re.compile(r'\bJWT\b|\bOAuth\w*|\bauthentication\b|\bauthorization\b', re.I)
ML_RE = re.compile(r'\bmachine learning\b|\bdeep learning\b|\bneural networks?\b|\btrained (?:a |an |our )?model\b', re.I)
API_RE = re.compile(r'\bREST(?:ful)?\s+API\b|\bGraphQL\b|\bREST\b', re.I)
DB_RE = re.compile(r'\bPostgreSQL\b|\bMySQL\b|\bMongoDB\b|\bSQLite\b|\bRedis\b', re.I)
DOCKER_RE = re.compile(r'\bdocker\b|\bkubernetes\b|\bcontaineri[sz]ed\b', re.I)
ARCH_RE = re.compile(r'\bmicroservices?\b|\bmonolith\b|\bserverless\b|\bevent.driven\b|\bmessage queue\b', re.I)
PERF_RE = re.compile(r'\b(?:fast|faster|fastest|performant|high.performance|low.latency|scalable)\b', re.I)
QUALITY_RE = re.compile(r'\bproduction.ready\b|\benterprise.grade\b|\bbattle.tested\b|\bblazingly fast\b', re.I)
TECH_USE_RE = re.compile(r'\b(?:uses?|using|built with|powered by|implemented (?:with|in)|leverages?|relies on)\s+((?:[A-Za-z][\w\.+#\-/]*\s*){1,4})', re.I)


@dataclass
class ClaimResult:
    """Deterministic result of auditing a single documentation claim."""
    claim_text: str
    normalized_claim: str
    category: str
    status: str
    confidence: str
    source_file: str
    source_line: Optional[int]
    explanation: str
    evidence_indices: List[int] = field(default_factory=list)
    finding_indices: List[int] = field(default_factory=list)


def normalize_claim(text: str) -> str:
    text = text.lower().strip().strip('".!?:;')
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _sentence_fragments(readme: str) -> List[Tuple[int, str]]:
    """Yield (line_number, sentence) candidates, markdown bullets stripped."""
    out: List[Tuple[int, str]] = []
    for lineno, raw_line in enumerate(readme.splitlines(), start=1):
        line = re.sub(r'^\s*(?:[-*+]\s+|\d+\.\s+|>\s*)', '', raw_line)
        line = line.replace('**', '').replace('`', '')
        if line.lstrip().startswith(('#', '!', '|', '---', '===')):
            line = line.lstrip('#').strip()
        for sentence in re.split(r'(?<=[.!?])\s+|\n', line):
            sentence = sentence.strip()
            if 15 <= len(sentence) <= MAX_SENTENCE_LEN:
                out.append((lineno, sentence))
    return out


class ClaimAuditor:
    """Deterministic claim extraction + evidence verification pipeline.

    README → CLAIM EXTRACTION → NORMALIZATION → EVIDENCE SEARCH →
    CLAIM VERIFICATION → STATUS → CONFIDENCE
    """

    def __init__(self, workspace: SafeRepositoryWorkspace):
        self.workspace = workspace
        self._deps_text = self._load_deps_text()
        self._source_texts: List[Tuple[str, str]] = self._load_source_texts()
        self._test_files = self._count_test_files()
        self._ci_detected = self._detect_ci()
        self._deploy_detected = self._detect_deploy()
        self._coverage_configured = self._detect_coverage_config()

    # ------------------------------------------------------------------ data
    def _load_deps_text(self) -> str:
        parts = []
        for dep in DEP_FILES:
            content = self.workspace.read_text(dep)
            if content:
                parts.append(content.lower())
        return '\n'.join(parts)

    def _load_source_texts(self) -> List[Tuple[str, str]]:
        """Non-documentation text files — the only valid claim evidence."""
        out = []
        for rel in self.workspace.files:
            lower = rel.lower()
            if any(lower.startswith(p) for p in DOC_PREFIXES):
                continue
            if not lower.endswith(('.py', '.js', '.ts', '.tsx', '.jsx', '.toml', '.cfg', '.yml', '.yaml', '.json', '.txt', '.env.example')):
                continue
            if rel in DEP_FILES:
                continue
            content = self.workspace.read_text(rel)
            if content:
                out.append((rel, content.lower()))
        return out

    def _count_test_files(self) -> int:
        n = 0
        for rel in self.workspace.files:
            parts = rel.replace('\\', '/').split('/')
            fname = parts[-1].lower()
            if any(d in ('tests', 'test', '__tests__', 'spec', 'specs') for d in parts[:-1]):
                n += 1
            elif fname.startswith('test_') or fname.endswith(('_test.py', '.test.ts', '.test.js', '.spec.ts', '.spec.js')):
                n += 1
        return n

    def _detect_ci(self) -> bool:
        for marker in CI_FILES:
            if marker.endswith('/') or '.' not in os.path.basename(marker):
                # directory marker (e.g. .github/workflows)
                if any(rel.startswith(marker) for rel in self.workspace.files):
                    return True
            elif self.workspace.exists(marker):
                return True
        return False

    def _detect_deploy(self) -> bool:
        return any(self.workspace.exists(f) for f in DEPLOY_FILES)

    def _detect_coverage_config(self) -> bool:
        for rel in self.workspace.files:
            base = os.path.basename(rel).lower()
            if base in ('.coveragerc',) or base in ('pytest.ini', 'setup.cfg'):
                content = (self.workspace.read_text(rel) or '').lower()
                if '--cov' in content or '[coverage:' in content or 'cov' in content:
                    return True
        return any(t in self._deps_text for t in COVERAGE_DEP_TOKENS)

    # ------------------------------------------------------------- helpers
    def _in_deps(self, patterns: Tuple[str, ...]) -> bool:
        return any(p in self._deps_text for p in patterns)

    def _in_code(self, patterns: Tuple[str, ...]) -> bool:
        return any(p in content for _, content in self._source_texts for p in patterns)

    def _link_evidence(self, patterns: Tuple[str, ...], category: str,
                       evidence: List[EvidenceItem], findings: List[FindingResult]) -> Tuple[List[int], List[int]]:
        ev_idx = [
            i for i, ev in enumerate(evidence)
            if any(p in ev.evidence_summary.lower() or p in ev.source_file.lower() for p in patterns)
        ]
        f_idx = [
            i for i, f in enumerate(findings)
            if any(p in f.title.lower() or p in f.evidence.lower() for p in patterns)
            or (not patterns and f.category == category)
        ]
        return ev_idx, f_idx

    @staticmethod
    def _match_tech(sentence: str) -> Optional[Tuple[str, Tuple[str, ...]]]:
        low = sentence.lower()
        for name, patterns in TECH_TOKENS.items():
            if any(re.search(rf'\b{re.escape(p)}\b', low) for p in patterns):
                return name, patterns
        m = TECH_USE_RE.search(sentence)
        if m:
            phrase = m.group(1).strip().lower()
            for name, patterns in TECH_TOKENS.items():
                if name in phrase:
                    return name, patterns
        return None

    # ------------------------------------------------------------ extract
    def extract_claims(self) -> List[Tuple[str, int, str]]:
        """Return (sentence, line_number, source_file) technical-claim candidates."""
        readme_path, readme = None, None
        for name in README_CANDIDATES:
            if self.workspace.exists(name):
                readme = self.workspace.read_text(name)
                readme_path = name
                break
        if not readme:
            return []

        candidates: List[Tuple[str, int, str]] = []
        seen: set = set()
        for lineno, sentence in _sentence_fragments(readme):
            category = self._classify(sentence)
            if category is None:
                continue
            norm = normalize_claim(sentence)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            candidates.append((sentence, lineno, readme_path))
            if len(candidates) >= MAX_CLAIMS:
                break
        return candidates

    def _classify(self, sentence: str) -> Optional[str]:
        if COVERAGE_RE.search(sentence):
            return 'TESTING'
        if CICD_RE.search(sentence):
            return 'DEPLOYMENT'
        if DOCKER_RE.search(sentence):
            return 'DEPLOYMENT'
        if SECURITY_NEG_RE.search(sentence) or ENCRYPT_RE.search(sentence) or AUTH_RE.search(sentence):
            return 'SECURITY'
        if ML_RE.search(sentence):
            return 'AI_ML'
        if API_RE.search(sentence):
            return 'API'
        if DB_RE.search(sentence):
            return 'DATABASE'
        if ARCH_RE.search(sentence):
            return 'ARCHITECTURE'
        if TESTING_RE.search(sentence):
            return 'TESTING'
        if QUALITY_RE.search(sentence):
            return 'QUALITY'
        if PERF_RE.search(sentence):
            return 'PERFORMANCE'
        if TECH_USE_RE.search(sentence) or self._match_tech(sentence):
            return 'TECHNOLOGY'
        return None

    # -------------------------------------------------------------- verify
    def audit(self, findings: List[FindingResult], evidence: List[EvidenceItem]) -> List[ClaimResult]:
        results: List[ClaimResult] = []
        critical_security = [
            f for f in findings if f.category == 'Security' and f.severity in ('CRITICAL', 'HIGH')
        ]
        for sentence, lineno, source_file in self.extract_claims():
            category = self._classify(sentence)
            verifier = getattr(self, f"_verify_{category.lower()}", None)
            if verifier is None:
                verifier = self._verify_generic
            result = verifier(sentence, lineno, source_file, findings, evidence, critical_security)
            results.append(result)
        return results

    def _make(self, sentence, lineno, source_file, category, status, confidence, explanation,
              evidence, findings, patterns=(), ev_idx=None, f_idx=None) -> ClaimResult:
        if ev_idx is None and f_idx is None:
            ev_idx, f_idx = self._link_evidence(patterns, category, evidence, findings)
        return ClaimResult(
            claim_text=sentence.strip(),
            normalized_claim=normalize_claim(sentence),
            category=category,
            status=status,
            confidence=confidence,
            source_file=source_file,
            source_line=lineno,
            explanation=explanation,
            evidence_indices=ev_idx or [],
            finding_indices=f_idx or [],
        )

    def _verify_technology(self, sentence, lineno, source_file, findings, evidence, crit_sec):
        match = self._match_tech(sentence) or ('', ())
        name, patterns = match
        if not patterns:
            return self._make(sentence, lineno, source_file, 'TECHNOLOGY', 'UNVERIFIED', 'LOW',
                              'Evidence not detected: no recognizable technology token in the claim.',
                              evidence, findings)
        deps_hit, code_hit = self._in_deps(patterns), self._in_code(patterns)
        if deps_hit and code_hit:
            return self._make(sentence, lineno, source_file, 'TECHNOLOGY', 'SUPPORTED', 'HIGH',
                              f"'{name}' found in dependency manifests and source code.", evidence, findings, patterns)
        if deps_hit or code_hit:
            where = 'dependency manifests' if deps_hit else 'source code'
            return self._make(sentence, lineno, source_file, 'TECHNOLOGY', 'SUPPORTED', 'MEDIUM',
                              f"'{name}' found in {where}.", evidence, findings, patterns)
        return self._make(sentence, lineno, source_file, 'TECHNOLOGY', 'UNVERIFIED', 'LOW',
                          f"Evidence not detected: '{name}' not found in dependency manifests or source code.",
                          evidence, findings)

    def _verify_testing(self, sentence, lineno, source_file, findings, evidence, crit_sec):
        if COVERAGE_RE.search(sentence):
            if self._coverage_configured:
                return self._make(sentence, lineno, source_file, 'TESTING', 'UNVERIFIED', 'MEDIUM',
                                  'Coverage tooling detected, but no measured coverage result exists in the '
                                  'repository; the claimed percentage could not be verified. Percentages are '
                                  'never inferred from test counts.',
                                  evidence, findings)
            return self._make(sentence, lineno, source_file, 'TESTING', 'UNVERIFIED', 'LOW',
                              'Evidence not detected: no coverage configuration or measured coverage results '
                              'found. Coverage is never inferred from test counts.',
                              evidence, findings)
        strong = bool(STRONG_TEST_RE.search(sentence))
        patterns = ('test', 'pytest', 'unittest')
        ev_idx, f_idx = self._link_evidence(patterns, 'Testing', evidence, findings)
        if self._test_files == 0:
            if strong:
                return self._make(sentence, lineno, source_file, 'TESTING', 'CONTRADICTED', 'HIGH',
                                  'The repository contains zero test files, directly conflicting with the claim.',
                                  evidence, findings, ev_idx=ev_idx, f_idx=f_idx)
            return self._make(sentence, lineno, source_file, 'TESTING', 'UNVERIFIED', 'LOW',
                              'Evidence not detected: no test files found in the repository.',
                              evidence, findings, ev_idx=ev_idx, f_idx=f_idx)
        if strong:
            return self._make(sentence, lineno, source_file, 'TESTING', 'PARTIALLY_SUPPORTED', 'MEDIUM',
                              f'{self._test_files} test files detected, but the completeness implied by the '
                              'claim ("fully"/"all") cannot be verified from static evidence.',
                              evidence, findings, ev_idx=ev_idx, f_idx=f_idx)
        return self._make(sentence, lineno, source_file, 'TESTING', 'SUPPORTED', 'HIGH',
                          f'{self._test_files} test files detected.',
                          evidence, findings, ev_idx=ev_idx, f_idx=f_idx)

    def _verify_deployment(self, sentence, lineno, source_file, findings, evidence, crit_sec):
        if CICD_RE.search(sentence):
            if self._ci_detected:
                return self._make(sentence, lineno, source_file, 'DEPLOYMENT', 'SUPPORTED', 'HIGH',
                                  'CI configuration detected (e.g. .github/workflows).', evidence, findings)
            return self._make(sentence, lineno, source_file, 'DEPLOYMENT', 'UNVERIFIED', 'LOW',
                              'Evidence not detected: no CI configuration (.github/workflows, GitLab CI, etc.) found.',
                              evidence, findings)
        if DOCKER_RE.search(sentence):
            if self._deploy_detected:
                return self._make(sentence, lineno, source_file, 'DEPLOYMENT', 'SUPPORTED', 'HIGH',
                                  'Docker/container configuration file detected.', evidence, findings)
            return self._make(sentence, lineno, source_file, 'DEPLOYMENT', 'UNVERIFIED', 'LOW',
                              'Evidence not detected: no Dockerfile or docker-compose configuration found.',
                              evidence, findings)
        return self._make(sentence, lineno, source_file, 'DEPLOYMENT', 'UNVERIFIED', 'LOW',
                          'Evidence not detected.', evidence, findings)

    def _verify_security(self, sentence, lineno, source_file, findings, evidence, crit_sec):
        crit_indices = [i for i, f in enumerate(findings)
                        if f.category == 'Security' and f.severity in ('CRITICAL', 'HIGH')]
        if AUTH_RE.search(sentence) and not SECURITY_NEG_RE.search(sentence) and not ENCRYPT_RE.search(sentence):
            if self._in_deps(('jwt', 'pyjwt', 'jsonwebtoken', 'oauth', 'authlib')) or self._in_code(('jwt', 'oauth')):
                return self._make(sentence, lineno, source_file, 'SECURITY', 'SUPPORTED', 'MEDIUM',
                                  'Authentication/JWT libraries found in dependencies or source code.',
                                  evidence, findings)
            return self._make(sentence, lineno, source_file, 'SECURITY', 'UNVERIFIED', 'LOW',
                              'Evidence not detected: no authentication libraries found in dependencies or source code.',
                              evidence, findings)
        if ENCRYPT_RE.search(sentence):
            if self._in_deps(CRYPTO_TOKENS) or self._in_code(CRYPTO_TOKENS):
                return self._make(sentence, lineno, source_file, 'SECURITY', 'SUPPORTED', 'MEDIUM',
                                  'Encryption/hashing libraries found in dependencies or source code.',
                                  evidence, findings)
            if crit_sec:
                return self._make(sentence, lineno, source_file, 'SECURITY', 'CONTRADICTED', 'HIGH',
                                  'Security analyzer reported critical/high findings conflicting with the claim: '
                                  + '; '.join(sorted({f.title for f in crit_sec})), evidence, findings,
                                  f_idx=crit_indices)
            return self._make(sentence, lineno, source_file, 'SECURITY', 'UNVERIFIED', 'LOW',
                              'Evidence not detected: no encryption libraries found in dependencies or source code.',
                              evidence, findings)
        # Negative security claim ("no exposed secrets", "secure", ...)
        if crit_sec:
            return self._make(sentence, lineno, source_file, 'SECURITY', 'CONTRADICTED', 'HIGH',
                              'Security analyzer reported critical/high findings conflicting with the claim: '
                              + '; '.join(sorted({f.title for f in crit_sec})), evidence, findings,
                              f_idx=crit_indices)
        if self._in_deps(CRYPTO_TOKENS) or self._in_code(CRYPTO_TOKENS):
            return self._make(sentence, lineno, source_file, 'SECURITY', 'SUPPORTED', 'MEDIUM',
                              'No critical security findings and security-relevant libraries detected.',
                              evidence, findings)
        return self._make(sentence, lineno, source_file, 'SECURITY', 'UNVERIFIED', 'LOW',
                          'Evidence not detected: no critical security findings, but no positive security '
                          'evidence (libraries, configuration) was found either.',
                          evidence, findings)

    def _verify_ai_ml(self, sentence, lineno, source_file, findings, evidence, crit_sec):
        ml_tokens = ('torch', 'tensorflow', 'sklearn', 'scikit-learn', 'transformers', 'keras')
        if self._in_deps(ml_tokens) or self._in_code(ml_tokens):
            return self._make(sentence, lineno, source_file, 'AI_ML', 'SUPPORTED', 'MEDIUM',
                              'ML libraries found in dependencies or source code.', evidence, findings)
        return self._make(sentence, lineno, source_file, 'AI_ML', 'UNVERIFIED', 'LOW',
                          'Evidence not detected: no ML libraries found in dependencies or source code.',
                          evidence, findings)

    def _verify_api(self, sentence, lineno, source_file, findings, evidence, crit_sec):
        api_tokens = ('fastapi', 'flask', 'django', 'express', 'graphql', 'ariadne', 'strawberry-graphql')
        if self._in_deps(api_tokens) or self._in_code(api_tokens):
            return self._make(sentence, lineno, source_file, 'API', 'SUPPORTED', 'HIGH',
                              'API framework found in dependency manifests and/or source code.',
                              evidence, findings)
        return self._make(sentence, lineno, source_file, 'API', 'UNVERIFIED', 'LOW',
                          'Evidence not detected: no API framework found in dependencies or source code.',
                          evidence, findings)

    def _verify_database(self, sentence, lineno, source_file, findings, evidence, crit_sec):
        match = self._match_tech(sentence)
        patterns = match[1] if match else ('sqlite', 'postgres', 'mysql', 'mongo', 'database', 'sqlalchemy')
        deps_hit, code_hit = self._in_deps(patterns), self._in_code(patterns)
        if deps_hit or code_hit:
            return self._make(sentence, lineno, source_file, 'DATABASE', 'SUPPORTED', 'MEDIUM',
                              'Database technology found in dependency manifests and/or source code.',
                              evidence, findings, patterns)
        return self._make(sentence, lineno, source_file, 'DATABASE', 'UNVERIFIED', 'LOW',
                          'Evidence not detected: claimed database not found in dependency manifests or source code.',
                          evidence, findings)

    def _verify_architecture(self, sentence, lineno, source_file, findings, evidence, crit_sec):
        return self._make(sentence, lineno, source_file, 'ARCHITECTURE', 'UNVERIFIED', 'LOW',
                          'Evidence not detected: architectural style claims cannot be confirmed by static '
                          'file analysis.', evidence, findings)

    def _verify_performance(self, sentence, lineno, source_file, findings, evidence, crit_sec):
        return self._make(sentence, lineno, source_file, 'PERFORMANCE', 'UNVERIFIED', 'LOW',
                          'Evidence not detected: performance claims require benchmarks, which static '
                          'analysis does not provide.', evidence, findings)

    def _verify_quality(self, sentence, lineno, source_file, findings, evidence, crit_sec):
        return self._make(sentence, lineno, source_file, 'QUALITY', 'UNVERIFIED', 'LOW',
                          'Evidence not detected: subjective readiness claims cannot be verified '
                          'deterministically.', evidence, findings)

    def _verify_generic(self, sentence, lineno, source_file, findings, evidence, crit_sec):
        match = self._match_tech(sentence)
        if match:
            patterns = match[1]
            if self._in_deps(patterns) or self._in_code(patterns):
                return self._make(sentence, lineno, source_file, 'OTHER', 'SUPPORTED', 'MEDIUM',
                                  f"'{match[0]}' found in dependency manifests or source code.",
                                  evidence, findings, patterns)
        return self._make(sentence, lineno, source_file, 'OTHER', 'UNVERIFIED', 'LOW',
                          'Evidence not detected.', evidence, findings)


def audit_claims(workspace: SafeRepositoryWorkspace, findings: List[FindingResult],
                 evidence: List[EvidenceItem]) -> List[ClaimResult]:
    """Convenience entry point used by the orchestrator."""
    return ClaimAuditor(workspace).audit(findings, evidence)
