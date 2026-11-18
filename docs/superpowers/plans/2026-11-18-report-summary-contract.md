# Report Summary Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every audit report carries an area-neutral `summary` block, and the generated `.security-audit/README.md` reads only that block.

**Architecture:** A new `summary.py` in the existing `dependency_audit` package builds the block (writer side) and validates it (reader side). `reporting.render_json` adds it to the dependency report at schema `1.1`; `folder_docs.py` drops its dependency-shaped parsing and renders from `read_summary`, falling back to status-only for reports without a summary.

**Tech Stack:** Python 3.10+, standard library only, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-18-report-summary-contract-design.md`

## Global Constraints

- Python 3.10+, standard library only; offline, deterministic tests; fail closed.
- Schema change is additive: audit reports go from `"1.0"` to `"1.1"`; no existing field, exit code, report path, or decision changes. The advisory-search result schema stays `"1.0"`.
- `summary` status and counts derive from the same `result.gate_status`, `result.decisions`, and `result.sources` the gate uses; they are never recomputed independently.
- `top_findings` is capped at 10, ordered known-exploited first then by severity (critical, high, medium, low, unknown); `more_findings` counts the rest.
- The README treats every summary field as untrusted: enums restricted, text flattened, escaped, and length-capped, lists capped, area folder names must match `[A-Za-z0-9._-]+`.
- No credential values, local paths, or hostnames in reports or the README.
- Out of scope: new audit areas, an `Area` protocol, registry, `AreaResult` envelope, unified CLI.

## Review Focus

1. A summary that says `pass` while evidence is unavailable or sources have gaps: status must equal `result.gate_status` (Task 1).
2. Withdrawn or excluded advisories appearing in `top_findings` or counted as blocking (Task 1).
3. Hostile or oversized summary content (HTML, Markdown links, newlines, pipes, 1000-item lists, 10k-char strings) reaching the README (Task 3).
4. A `summary` that is a list, string, `null`, or has negative, boolean, string, or float counts: must fall back, never crash or look better than the truth (Task 3).
5. A pre-`1.1` report with no `summary` still listed in the README with status only and a re-run note (Task 3).

---

### Task 1: Build the summary block

**Files:**
- Create: `skills/security-audit-skill/scripts/dependency_audit/summary.py`
- Test: `tests/test_summary.py`

**Interfaces:**
- Consumes: `AuditResult`, `Finding`, `Decision`, `SourceState` from `dependency_audit.models`.
- Produces: `DEPENDENCY_AREA = "dependency-audit"`, `MAX_TOP_FINDINGS = 10`, and `build_summary(area: str, result: AuditResult, active_findings: Sequence[Finding]) -> dict[str, Any]` returning the spec's `summary` dict (keys `area`, `status`, `mode`, `counts` {`blocking`, `warnings`, `excluded`, `source_gaps`}, `top_findings` [{`severity`, `id`, `subject`, `flags`}], `more_findings`, `source_gaps` [{`source`, `state`}]).

- [ ] **Step 1: Write the failing tests** in `tests/test_summary.py`, building `Finding`s the way `tests/test_reporting.py` does:

```python
def test_counts_and_status_match_the_gate(self):  # decisions block+warn+excluded; sources ok, partial, unavailable
    summary = build_summary(DEPENDENCY_AREA, result, active)
    self.assertEqual(summary["counts"], {"blocking": 1, "warnings": 1, "excluded": 1, "source_gaps": 2})
    self.assertEqual(summary["status"], result.gate_status.value)

def test_unavailable_status_is_never_reported_as_pass(self):  # gate_status UNAVAILABLE, sources partial
    self.assertEqual(build_summary(DEPENDENCY_AREA, result, [])["status"], "unavailable")

def test_excluded_findings_are_not_listed(self):  # caller passes only active findings
    ids = [f["id"] for f in build_summary(DEPENDENCY_AREA, result, [active_one])["top_findings"]]
    self.assertEqual(ids, ["GHSA-active"])

def test_top_findings_ordered_and_capped(self):  # 12 active: one low+KEV, rest critical/high/medium
    summary = build_summary(DEPENDENCY_AREA, result, twelve)
    self.assertEqual(summary["top_findings"][0]["flags"], ["known_exploited"])
    self.assertEqual(len(summary["top_findings"]), 10)
    self.assertEqual(summary["more_findings"], 2)

def test_unrecognized_severity_becomes_unknown(self):  # "SEV-9" -> "unknown", "HIGH" -> "high"
```

- [ ] **Step 2: Run** `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_summary -v`. Expected: FAIL with `ModuleNotFoundError: dependency_audit.summary`.

- [ ] **Step 3: Implement `build_summary` in `summary.py`** with the signature above. `status` is `result.gate_status.value`, `mode` is `result.mode.value`. Counts come from `result.decisions` (BLOCK, WARN, EXCLUDED) and `result.sources` (state `PARTIAL` or `UNAVAILABLE`). Sort `active_findings` by (not `kev`, severity rank, `advisory.id`, `package.purl`); `subject` is `package.purl`; `flags` is `["known_exploited"]` when `kev`.

- [ ] **Step 4: Run** the same command. Expected: PASS.

- [ ] **Step 5: Commit** `git add tests/test_summary.py skills/security-audit-skill/scripts/dependency_audit/summary.py && git commit -m "Add build_summary for the area-neutral report summary"`

---

### Task 2: Write the summary into audit reports (schema 1.1)

**Files:**
- Modify: `skills/security-audit-skill/scripts/dependency_audit/models.py` (add `AUDIT_SCHEMA_VERSION = "1.1"`; `AuditResult.schema_version` defaults to it; `AdvisorySearchResult` keeps `SCHEMA_VERSION = "1.0"`)
- Modify: `skills/security-audit-skill/scripts/dependency_audit/reporting.py` (`render_json`)
- Modify: `tests/fixtures/expected-report.json`
- Test: `tests/test_models.py:58`, `tests/test_reporting.py:106`, `tests/test_reporting.py`

**Interfaces:**
- Consumes: `build_summary`, `DEPENDENCY_AREA` (Task 1); `_ordered_evidence` in `reporting.py`.
- Produces: every `render_json` payload has `summary` (redacted with the rest of the payload) and `schema_version == "1.1"`.

- [ ] **Step 1: Update and add tests.** Change the two asserted `"1.0"` values for audit results to `"1.1"`. In `tests/test_reporting.py` add:

```python
def test_render_json_includes_summary_consistent_with_report(self):
    payload = json.loads(render_json(result))
    self.assertEqual(payload["summary"]["status"], payload["gate_status"])
    self.assertEqual(payload["summary"]["area"], "dependency-audit")
    self.assertEqual(payload["summary"]["counts"]["blocking"],
                     sum(d["decision"] == "block" for d in payload["decisions"]))

def test_summary_is_redacted_like_the_rest_of_the_report(self):  # credential value inside an advisory id
    self.assertNotIn("seeded-secret", render_json(result, credential_values=("seeded-secret",)))

def test_advisory_search_schema_version_is_unchanged(self):
    self.assertEqual(AdvisorySearchResult(...).to_dict()["schema_version"], "1.0")
```

- [ ] **Step 2: Run** `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_models tests.test_reporting -v`. Expected: FAIL (schema `1.0`, no `summary`).

- [ ] **Step 3: Implement.** In `render_json`, after building `ordered_pairs`, compute `active = [f for f, d in ordered_pairs if d.decision is not Decision.EXCLUDED] + unmatched_findings` and set `payload["summary"] = build_summary(DEPENDENCY_AREA, result, active)` before `_redact_value`. Add the models change above.

- [ ] **Step 4: Regenerate the golden fixture** `tests/fixtures/expected-report.json`: change `schema_version` to `"1.1"` and add the `summary` block that `render_json` now emits for that fixture (copy it from the failing golden diff). `expected-report.md` must not change.

- [ ] **Step 5: Verify additivity.** Run `git diff -U0 tests/fixtures/expected-report.json | grep '^-[^-]'`. Expected: exactly one removed line, the old `"schema_version": "1.0"`. Run the full suite `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests`. Expected: OK (CLI and acceptance tests pass unchanged, proving exit codes and paths are untouched).

- [ ] **Step 6: Commit** `git add -A && git commit -m "Write an area-neutral summary into audit reports at schema 1.1"`

---

### Task 3: Read the summary safely and render the README from it

**Files:**
- Modify: `skills/security-audit-skill/scripts/dependency_audit/summary.py`
- Modify: `skills/security-audit-skill/scripts/dependency_audit/folder_docs.py`
- Test: `tests/test_summary.py`, `tests/test_folder_docs.py`

**Interfaces:**
- Consumes: `build_summary` output shape (Task 1); `_text`, `_status`, `_mode`, `_AREA_NAME` already in `folder_docs.py`.
- Produces:

```python
@dataclass(frozen=True)
class SummaryFinding: severity: str; id: str; subject: str; flags: tuple[str, ...]
@dataclass(frozen=True)
class ReportSummary:
    area: str; status: str; mode: str
    blocking: int; warnings: int; excluded: int; source_gaps: int
    top_findings: tuple[SummaryFinding, ...]; more_findings: int
    gap_items: tuple[tuple[str, str], ...]
def read_summary(data: Mapping[str, Any]) -> ReportSummary | None
```

Reader rules: return `None` when `data["summary"]` is missing, not a dict, or any count is not a plain `int` (reject `bool`, negatives, floats, strings) in `0..1_000_000`. Unknown `status` becomes `"invalid"`, unknown `mode` becomes `"-"`, unknown severity becomes `"unknown"`, unknown flags are dropped. Text fields are whitespace-flattened and truncated to 200 characters; `top_findings` and `gap_items` truncated to 10. Escaping stays in the README renderer.

- [ ] **Step 1: Write failing reader tests** in `tests/test_summary.py`:

```python
def test_roundtrip_of_a_built_summary(self):
    self.assertEqual(read_summary({"summary": built}).blocking, built["counts"]["blocking"])

def test_malformed_summaries_return_none(self):  # missing; list; "x"; None; 3; counts -1, True, 1.5, "2"
    for bad in cases: self.assertIsNone(read_summary({"summary": bad}))

def test_enums_text_and_lists_are_clamped(self):  # status "x", mode "x", severity "x", 1000 findings, 10_000-char id with newlines
    parsed = read_summary({"summary": hostile})
    self.assertEqual((parsed.status, parsed.mode), ("invalid", "-"))
    self.assertEqual(len(parsed.top_findings), 10)
    self.assertLessEqual(len(parsed.top_findings[0].id), 200)
    self.assertNotIn("\n", parsed.top_findings[0].id)
```

- [ ] **Step 2: Write failing README tests** in `tests/test_folder_docs.py`, and update the existing injection test to mutate `summary` fields (`area`-folder name, finding `id`, `subject`, gap `source`) instead of `findings[...]`:

```python
def test_readme_comes_only_from_the_summary(self):  # change a finding id in `findings` but not in `summary`
    self.assertNotIn("CHANGED-ONLY-IN-FINDINGS", readme)

def test_pre_summary_report_is_listed_with_status_only(self):  # fixture minus `summary`, schema 1.0
    self.assertIn("| [dependency-audit](dependency-audit/latest.md) | blocked | change |", readme)
    self.assertIn("re-run the audit", readme)

def test_malformed_summary_falls_back_without_crashing(self):  # summary = []
def test_summary_content_cannot_inject_markup_or_links(self):  # `<img onerror>`, `[x](http://evil.example)`, `|` in id/subject/source
def test_oversized_summary_is_capped_in_the_readme(self):  # 1000 findings -> at most 10 bullets + one "more" line
```

- [ ] **Step 3: Run** `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_summary tests.test_folder_docs -v`. Expected: FAIL (`read_summary` missing; README still reads findings).

- [ ] **Step 4: Implement `read_summary`, `SummaryFinding`, `ReportSummary` in `summary.py`**, then refactor `folder_docs._render_readme`: the table row and per-area section use `read_summary(data)`; when it returns `None`, use `_status`, `_mode`, and `-` for counts, plus the line `Older report format: re-run the audit for counts and findings.` Delete `_top_findings`, `_decision_counts`, `_source_gaps` and their now-unused constants. Keep escaping through `_text` and keep the area-folder name check in `_load_reports`.

- [ ] **Step 5: Run** the same command, then the full suite. Expected: OK.

- [ ] **Step 6: Commit** `git add -A && git commit -m "Render the .security-audit README from the validated report summary"`

---

### Task 4: Document the contract and verify end to end

**Files:**
- Modify: `skills/security-audit-skill/references/policy.md` (new "Report summary block" section: schema `1.1`, field table, ordering and caps, and the fallback for older reports)
- Modify: `skills/security-audit-skill/SKILL.md` (one sentence in the report-folder paragraph: reports carry a `summary` the README reads)
- Modify: `AGENTS.md` ("Changing behavior": every area must write the summary block and never read area-specific fields in the README)
- Modify: `CHANGELOG.md` (Unreleased: Added summary block; Changed: audit report schema `1.1`)

**Interfaces:**
- Consumes: the behavior from Tasks 1 to 3.
- Produces: docs that match `--help`-verifiable behavior and the field table in the spec.

- [ ] **Step 1: Write the four documentation changes above**, copying field names and caps from the spec.

- [ ] **Step 2: Run the full suite.** `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`. Expected: OK, with the test count higher than the 174 baseline.

- [ ] **Step 3: Manual end-to-end check.** In the scratchpad, run `python3 skills/security-audit-skill/scripts/dependency_security_audit.py --root tests/fixtures/project --mode change --output <scratchpad>/.security-audit/dependency-audit --format human`, then read `<scratchpad>/.security-audit/README.md`. Expected: a table row for `dependency-audit` whose status matches the CLI's reported status (`unavailable` offline, otherwise `pass`, `warnings`, or `blocked`), no absolute paths in the file, and `latest.json` containing a `summary` whose `status` equals its `gate_status`.

- [ ] **Step 4: Commit** `git add -A && git commit -m "Document the report summary contract"`
