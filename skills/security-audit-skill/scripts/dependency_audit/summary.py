"""Build the area-neutral ``summary`` block that every audit report carries.

The block is the only thing the generated ``.security-audit/README.md`` reads, so an audit area
never needs the README to understand its own finding shape. Status and counts derive from the same
result the gate used and are never recomputed independently.
"""

from __future__ import annotations

from typing import Any, Sequence

from .models import AuditResult, Decision, Finding, SourceState

DEPENDENCY_AREA = "dependency-audit"
MAX_TOP_FINDINGS = 10

_SEVERITY_ORDER = ("critical", "high", "medium", "low", "unknown")
_GAP_STATES = (SourceState.PARTIAL, SourceState.UNAVAILABLE)


def build_summary(
    area: str, result: AuditResult, active_findings: Sequence[Finding],
) -> dict[str, Any]:
    """Describe one completed audit as plain, area-neutral data.

    Args:
        area: Stable area name; matches the report's directory name under ``.security-audit``.
        result: Completed audit whose ``gate_status``, ``decisions``, and ``sources`` are final.
        active_findings: Findings that count as active, meaning not excluded or withdrawn.

    Returns:
        A JSON-serializable dict with ``area``, ``status``, ``mode``, ``counts``,
        ``top_findings`` (at most ``MAX_TOP_FINDINGS``), ``more_findings`` and ``source_gaps``.
    """
    ordered = sorted(active_findings, key=_sort_key)
    gaps = [item for item in result.sources if item.state in _GAP_STATES]
    return {
        "area": area,
        "status": result.gate_status.value,
        "mode": result.mode.value,
        "counts": {
            "blocking": _count(result, Decision.BLOCK),
            "warnings": _count(result, Decision.WARN),
            "excluded": _count(result, Decision.EXCLUDED),
            "source_gaps": len(gaps),
        },
        "top_findings": [_entry(item) for item in ordered[:MAX_TOP_FINDINGS]],
        "more_findings": max(len(ordered) - MAX_TOP_FINDINGS, 0),
        "source_gaps": [{"source": item.source, "state": item.state.value} for item in gaps],
    }


def _count(result: AuditResult, decision: Decision) -> int:
    return sum(record.decision is decision for record in result.decisions)


def _severity(finding: Finding) -> str:
    value = finding.advisory.severity.strip().lower()
    return value if value in _SEVERITY_ORDER else "unknown"


def _sort_key(finding: Finding) -> tuple[int, int, str, str]:
    return (
        0 if finding.kev else 1,
        _SEVERITY_ORDER.index(_severity(finding)),
        finding.advisory.id,
        finding.package.purl,
    )


def _entry(finding: Finding) -> dict[str, Any]:
    return {
        "severity": _severity(finding),
        "id": finding.advisory.id,
        "subject": finding.package.purl,
        "flags": ["known_exploited"] if finding.kev else [],
    }
