"""Tests for the area-neutral report summary block."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "security-audit-skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dependency_audit.models import (  # noqa: E402
    Advisory, AuditMode, AuditResult, Decision, DecisionRecord, DependencyScope, Finding,
    GateStatus, PackageRef, SourceState, SourceStatus,
)
from dependency_audit.summary import (  # noqa: E402
    DEPENDENCY_AREA, MAX_TOP_FINDINGS, build_summary,
)


def finding(advisory_id: str, severity: str = "high", kev: bool = False, name: str = "pkg") -> Finding:
    package = PackageRef(
        ecosystem="npm", name=name, version="1.0.0", purl=f"pkg:npm/{name}@1.0.0",
        scope=DependencyScope.RUNTIME,
    )
    return Finding(package=package, advisory=Advisory(id=advisory_id, severity=severity), kev=kev)


def result_with(decisions: list[Decision], sources: list[SourceState],
                status: GateStatus = GateStatus.BLOCKED) -> AuditResult:
    result = AuditResult.empty(AuditMode.CHANGE)
    result.decisions = [DecisionRecord(item, ()) for item in decisions]
    result.sources = [SourceStatus(f"source-{index}", state) for index, state in enumerate(sources)]
    result.gate_status = status
    return result


class BuildSummaryTest(unittest.TestCase):
    def test_counts_and_status_match_the_gate(self) -> None:
        result = result_with(
            [Decision.BLOCK, Decision.WARN, Decision.EXCLUDED],
            [SourceState.OK, SourceState.PARTIAL, SourceState.UNAVAILABLE, SourceState.NOT_APPLICABLE],
        )
        summary = build_summary(DEPENDENCY_AREA, result, [finding("GHSA-1")])
        self.assertEqual(
            summary["counts"], {"blocking": 1, "warnings": 1, "excluded": 1, "source_gaps": 2},
        )
        self.assertEqual(summary["status"], result.gate_status.value)
        self.assertEqual(summary["mode"], "change")
        self.assertEqual(summary["area"], "dependency-audit")
        self.assertEqual(
            summary["source_gaps"],
            [{"source": "source-1", "state": "partial"}, {"source": "source-2", "state": "unavailable"}],
        )

    def test_unavailable_status_is_never_reported_as_pass(self) -> None:
        result = result_with([], [SourceState.PARTIAL], GateStatus.UNAVAILABLE)
        summary = build_summary(DEPENDENCY_AREA, result, [])
        self.assertEqual(summary["status"], "unavailable")
        self.assertEqual(summary["counts"]["source_gaps"], 1)

    def test_only_the_findings_passed_in_are_listed(self) -> None:
        result = result_with([Decision.EXCLUDED, Decision.WARN], [])
        summary = build_summary(DEPENDENCY_AREA, result, [finding("GHSA-active")])
        self.assertEqual([item["id"] for item in summary["top_findings"]], ["GHSA-active"])
        self.assertEqual(summary["more_findings"], 0)

    def test_top_findings_are_ordered_and_capped(self) -> None:
        active = [finding("LOW-KEV", "low", kev=True, name="kev")]
        for index in range(11):
            active.append(finding(f"ADV-{index:02d}", ("critical", "high", "medium")[index % 3], name=f"p{index}"))
        summary = build_summary(DEPENDENCY_AREA, result_with([Decision.BLOCK], []), active)
        top = summary["top_findings"]
        self.assertEqual(top[0]["id"], "LOW-KEV")
        self.assertEqual(top[0]["flags"], ["known_exploited"])
        self.assertEqual(len(top), MAX_TOP_FINDINGS)
        self.assertEqual(summary["more_findings"], 2)
        severities = [item["severity"] for item in top[1:]]
        self.assertEqual(severities, sorted(severities, key=("critical", "high", "medium").index))

    def test_unrecognized_severity_becomes_unknown_and_case_is_normalized(self) -> None:
        active = [finding("A", "SEV-9"), finding("B", "HIGH", name="other")]
        summary = build_summary(DEPENDENCY_AREA, result_with([Decision.WARN], []), active)
        by_id = {item["id"]: item["severity"] for item in summary["top_findings"]}
        self.assertEqual(by_id, {"A": "unknown", "B": "high"})
        self.assertEqual(summary["top_findings"][0]["id"], "B")


if __name__ == "__main__":
    unittest.main()
