"""Deterministic, stable finding identifiers.

Finding titles are NOT guaranteed to be unique (two different files can
produce the same finding title), so titles must never be used as the
primary relationship identifier between findings and evidence/claims.

`compute_finding_key` derives a stable key from:

    category + rule (slugified title) + repo-relative path

Line numbers are deliberately excluded: a fix that shifts code by a few
lines must not make the same finding look "new" during comparison runs.
Collisions inside a single analysis run are disambiguated with a numeric
suffix (-2, -3, ...) assigned in emission order.
"""
import re
from typing import List, Optional

from backend.app.analyzer.base import FindingResult


def slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80] or "unknown"


def compute_finding_key(finding: FindingResult, existing_keys: Optional[List[str]] = None) -> str:
    """Return a deterministic key: category.rule.path (line-independent).

    existing_keys: keys already assigned in this run, used for collision
    disambiguation. Mutated only via the returned value by the caller.
    """
    rule = slug(finding.title)
    path = slug(finding.file_path or "project")
    key = f"{slug(finding.category)}.{rule}.{path}"
    if existing_keys is None:
        return key
    base, n = key, 2
    while key in existing_keys:
        key = f"{base}-{n}"
        n += 1
    return key
