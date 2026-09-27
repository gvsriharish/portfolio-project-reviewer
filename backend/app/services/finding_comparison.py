"""Phase 3/4 — Finding lifecycle comparison across analysis runs.

Findings are compared using the deterministic finding_key
(category.rule.path). Legacy Phase 1 rows without a key fall back to a
title-based key (prefixed 'title::' so the two namespaces never collide).
Resolution is NEVER inferred from score improvement — only from the
actual presence/absence of matching findings.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

from backend.app.models.findings import Finding


FINDING_STATUSES = ('RESOLVED', 'STILL_PRESENT', 'NEW', 'CHANGED', 'UNVERIFIED')


@dataclass
class FindingDelta:
    finding_key: str
    status: str            # RESOLVED | STILL_PRESENT | NEW | CHANGED
    category: str
    title: str
    before_severity: Optional[str]
    after_severity: Optional[str]
    before_id: Optional[str]
    after_id: Optional[str]
    match_method: str      # 'finding_key' | 'title_fallback'


def finding_identity(f: Finding) -> Tuple[str, str]:
    """Stable identity tuple (key, method) for cross-run matching."""
    if f.finding_key:
        return f.finding_key, 'finding_key'
    return f'title::{f.title}', 'title_fallback'


def _delta(status: str, f: Finding, other: Optional[Finding], method: str) -> FindingDelta:
    """Build a delta. `f` is the row owned by the status's run:
    RESOLVED → before-row; NEW → after-row; otherwise the after-row
    with `other` as the before-row."""
    if status == 'RESOLVED':
        return FindingDelta(
            finding_key=finding_identity(f)[0], status=status, category=f.category,
            title=f.title, before_severity=f.severity, after_severity=None,
            before_id=f.id, after_id=None, match_method=method,
        )
    if status == 'NEW':
        return FindingDelta(
            finding_key=finding_identity(f)[0], status=status, category=f.category,
            title=f.title, before_severity=None, after_severity=f.severity,
            before_id=None, after_id=f.id, match_method=method,
        )
    # STILL_PRESENT / CHANGED — f is the after-row, other the before-row.
    before = other or f
    return FindingDelta(
        finding_key=finding_identity(f)[0], status=status, category=f.category,
        title=f.title, before_severity=before.severity, after_severity=f.severity,
        before_id=before.id, after_id=f.id, match_method=method,
    )


def compare_findings(before: List[Finding], after: List[Finding]) -> Tuple[
        List[FindingDelta], List[FindingDelta], List[FindingDelta], List[FindingDelta]]:
    """Return (resolved, still_present, new, changed).

    - RESOLVED:      identity present before, absent after.
    - STILL_PRESENT: identity present in both, identical severity.
    - CHANGED:       identity present in both, different severity.
    - NEW:           identity present only after.
    """
    # Stable finding_key is canonical. The title fallback exists only for
    # legacy Phase-1 rows that have no finding_key; it is deliberately
    # namespaced and deterministic so duplicate titles do not become a
    # cross-run identity.
    def build_map(rows: List[Finding]):
        result = {}
        for f in rows:
            key, _ = finding_identity(f)
            if key in result:
                # Legacy rows with duplicate titles cannot be safely matched.
                # Keep them distinct rather than silently collapsing evidence.
                suffix = 2
                candidate = f"{key}::{suffix}"
                while candidate in result:
                    suffix += 1
                    candidate = f"{key}::{suffix}"
                key = candidate
            result[key] = f
        return result

    before_map = build_map(before)
    after_map = build_map(after)
    method_of = {}
    for f in before + after:
        key, method = finding_identity(f)
        method_of.setdefault(key, method)

    resolved, still_present, new, changed = [], [], [], []

    for key, b in before_map.items():
        a = after_map.get(key)
        if a is None:
            resolved.append(_delta('RESOLVED', b, None, method_of[key]))
        elif a.severity != b.severity:
            changed.append(_delta('CHANGED', a, b, method_of[key]))
        else:
            still_present.append(_delta('STILL_PRESENT', a, b, method_of[key]))

    for key, a in after_map.items():
        if key not in before_map:
            new.append(_delta('NEW', a, None, method_of[key]))

    return resolved, still_present, new, changed
