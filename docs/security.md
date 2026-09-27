# Security Model & Policy — Portfolio Project Reviewer

## 1. Threat Model & Safety Guarantees

When analyzing untrusted public repositories:
- **No Arbitrary Code Execution**: Repository source code is parsed exclusively as abstract syntax trees (Python AST) or regex text scans. No scripts, binaries, or tests from the submitted repository are executed on the host system.
- **Path Traversal Shield**: Tarball and zip archive extractions reject members containing `..` or absolute path prefixes.
- **Secret Redaction**: Any detected API keys, credentials, or private tokens are automatically masked in memory (e.g. `sk-proj-****REDACTED****`) before being persisted or transmitted to client UIs.
- **Ephemeral Workspaces**: Repositories are fetched into isolated temporary directories and deleted upon analysis completion.

## 2. Security Disclaimer

> **Notice**: Static analysis detects common vulnerabilities, exposed credentials, and hazardous code patterns. However, automated static analysis does not constitute a full penetration test or formal security certification. No application should be considered 100% secure solely based on automated static scan results.
