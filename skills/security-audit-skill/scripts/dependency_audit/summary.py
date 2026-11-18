"""Build the area-neutral ``summary`` block that every audit report carries.

The block is the only thing the generated ``.security-audit/README.md`` reads, so an audit area
never needs the README to understand its own finding shape. Status and counts derive from the same
result the gate used and are never recomputed independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .models import AuditResult, Decision, Finding, GateStatus, SourceState

DEPENDENCY_AREA = "dependency-audit"
MAX_TOP_FINDINGS = 10
MAX_GAP_ITEMS = 10
MAX_TEXT = 200
MAX_COUNT = 1_000_000
MODES = ("change", "main", "release")

_SEVERITY_ORDER = ("critical", "high", "medium", "low", "unknown")
_GAP_STATES = (SourceState.PARTIAL, SourceState.UNAVAILABLE)
_STATUSES = tuple(item.value for item in GateStatus)
_SOURCE_STATES = tuple(item.value for item in SourceState)
_FLAGS = ("known_exploited",)
_COUNT_KEYS = ("blocking", "warnings", "excluded", "source_gaps")


@dataclass(frozen=True)
class SummaryFinding:
    """One validated top finding, ready for display."""

    severity: str
    id: str
    subject: str
    flags: tuple[str, ...]


@dataclass(frozen=True)
class ReportSummary:
    """A validated, size-capped view of a report's ``summary`` block."""

    area: str
    status: str
    mode: str
    blocking: int
    warnings: int
    excluded: int
    source_gaps: int
    top_findings: tuple[SummaryFinding, ...]
    more_findings: int
    gap_items: tuple[tuple[str, str], ...]


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
    # The gate treats inventory statuses and source statuses alike, so the summary must too.
    gaps = sorted(
        (item for item in (*result.inventory.statuses, *result.sources) if item.state in _GAP_STATES),
        key=lambda item: (item.source, item.state.value),
    )
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


def rag_for(status: object) -> str:
    """Map a report status to red, amber, or green without ever rounding toward green.

    Only ``pass`` is green and only ``warnings`` is amber. Everything else, including an unknown,
    missing, or non-string status, is red so missing evidence can never look healthy.
    """
    if status == GateStatus.PASS.value:
        return "green"
    if status == GateStatus.WARNINGS.value:
        return "amber"
    return "red"


def read_summary(data: Mapping[str, Any]) -> ReportSummary | None:
    """Validate and clamp a report's untrusted ``summary`` block.

    Returns ``None`` when the block is missing or structurally unusable, including counts that are
    not plain integers in ``0..MAX_COUNT``. Callers then fall back to status-only handling, so a
    malformed summary can never make a result look better than it is. Unknown enum values degrade
    to ``invalid``, ``-``, ``unknown``, or are dropped; text is flattened and length-capped here,
    and escaped later by whatever renders it.
    """
    raw = data.get("summary") if isinstance(data, Mapping) else None
    if not isinstance(raw, Mapping):
        return None
    counts = raw.get("counts")
    if not isinstance(counts, Mapping):
        return None
    values = [_count_value(counts.get(key)) for key in _COUNT_KEYS]
    more = _count_value(raw.get("more_findings"))
    if more is None or any(item is None for item in values):
        return None
    status = raw.get("status")
    mode = raw.get("mode")
    findings = raw.get("top_findings")
    gaps = raw.get("source_gaps")
    return ReportSummary(
        area=_flat(raw.get("area")),
        status=status if isinstance(status, str) and status in _STATUSES else "invalid",
        mode=mode if isinstance(mode, str) and mode in MODES else "-",
        blocking=values[0], warnings=values[1], excluded=values[2], source_gaps=values[3],
        top_findings=tuple(
            _read_finding(item) for item in (findings if isinstance(findings, list) else [])
            if isinstance(item, Mapping)
        )[:MAX_TOP_FINDINGS],
        more_findings=more,
        gap_items=tuple(
            (_flat(item.get("source")), _read_state(item.get("state")))
            for item in (gaps if isinstance(gaps, list) else []) if isinstance(item, Mapping)
        )[:MAX_GAP_ITEMS],
    )


def _count_value(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_COUNT:
        return None
    return value


def _flat(value: object) -> str:
    return " ".join(value.split())[:MAX_TEXT] if isinstance(value, str) else ""


def _read_state(value: object) -> str:
    return value if isinstance(value, str) and value in _SOURCE_STATES else "unknown"


def _read_finding(item: Mapping[str, Any]) -> SummaryFinding:
    severity = item.get("severity")
    flags = item.get("flags")
    return SummaryFinding(
        severity=severity if isinstance(severity, str) and severity in _SEVERITY_ORDER else "unknown",
        id=_flat(item.get("id")),
        subject=_flat(item.get("subject")),
        flags=tuple(flag for flag in (flags if isinstance(flags, list) else []) if flag in _FLAGS),
    )
