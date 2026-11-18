# AGENTS.md

Instructions for AI agents (and humans) contributing to or maintaining this skill. This repository
ships the skill from `skills/security-audit-skill/`, whose `SKILL.md` is the entry point. For what
the skill does and how to use it, read [README.md](README.md) and [SKILL.md](SKILL.md).

## Layout

| Path | Purpose |
|---|---|
| `skills/security-audit-skill/SKILL.md` | Skill entry point: frontmatter plus the operational workflow agents follow. |
| `skills/security-audit-skill/references/` | Detail loaded on demand (`policy.md`, `sources.md`); linked from `SKILL.md`. |
| `skills/security-audit-skill/scripts/` | The two CLIs and the `dependency_audit` package they share. |
| `skills/security-audit-skill/agents/openai.yaml` | Display metadata for agents that read it. |
| `tests/` | Offline unit tests and fixtures; `live_smoke.py` is opt-in and networked. Not shipped with the skill. |
| `.github/` | CI, issue and PR templates, Dependabot, and `settings/` (desired repo settings and labels as JSON; descriptive only, applying them to GitHub needs the owner's approval). |
| `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CLAUDE.md` | Keep a Changelog history, contributor entry point, private vulnerability reporting, and a one-line import of this file. |
| `.specs/` | Historical build spec. Do not edit or treat as current behavior. |

## Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v   # required; offline
PYTHONDONTWRITEBYTECODE=1 python3 tests/live_smoke.py                # optional; needs network
```

Run the offline suite from the repo root before every commit. CI runs the same command on Python
3.11. Do not add test dependencies: the suite uses `unittest` only.

## Constraints that must hold

- **Python 3.10+, standard library only.** No third-party runtime or test dependencies.
- **Fail closed.** A source failure, partial response, stale data, or incomplete inventory must
  never read as "no vulnerabilities". Missing evidence is `unavailable` or `unknown`, never `pass`.
- **Stable exit codes.** Audit CLI: `0` pass/warnings, `1` blocked, `2` unavailable, `3` invalid.
  Search CLI never returns `1`. Changing any of these is a breaking change.
- **No secrets in arguments or output.** Credential options take environment-variable names, never
  values, and credentials are scoped to their own host. Keep diagnostics and reports redacted.
- **Machine output is data.** Never execute advisory text or native-tool output; parse it only.
- **Tests stay offline and deterministic.** Use fixtures; never hit OSV, CISA, GitHub, or NVD from
  the unit suite. Assert on stable schemas, not live advisory counts or severities.
- **Reports may be published.** The audit writes to `PROJECT/.security-audit/`, and its contents may be
  committed to a public repository. Nothing written there may contain credential values, local absolute
  paths, hostnames, or personal data. Redaction and relative links are tested; keep them that way. Do
  not commit reports produced while developing this skill.

## Changing behavior

1. Write or update a test first, using fixtures under `tests/fixtures/`.
2. Keep `SKILL.md` and `references/` in sync with the code. If you add, rename, or remove a CLI
   flag, exit code, mode, report field, or source, update every place that documents it. Verify the
   documented commands against `--help` rather than from memory.
3. Policy and decision rules live in `references/policy.md`; source and endpoint details live in
   `references/sources.md`. Keep `SKILL.md` short and link out instead of duplicating.
4. Report schema changes are versioned. Do not change existing report fields silently.

## Keeping the skill spec-compliant

Follow the [Agent Skills specification](https://agentskills.io/specification):

- Frontmatter allows only `name`, `description`, `license`, `compatibility`, `metadata`, and
  `allowed-tools`. Put the semver in `metadata.version`, never as a top-level key.
- `name` must match the skill directory name (`skills/security-audit-skill/`), be lowercase with hyphens, and
  stay within 64 characters. `description` states what the skill does and when to use it, within
  1024 characters.
- Keep `SKILL.md` focused (aim under 500 lines); move depth into `references/` and reference it by
  relative path, one level deep.
- If the install directory name changes, change `name:` and the `agents/openai.yaml` prompt with
  it.

## Versioning and releases

Bump `metadata.version` in `SKILL.md` with semver when behavior changes: patch for fixes, minor for
backward-compatible features, major for breaking changes (exit codes, report schema, CLI flags).
Keep the README's documented behavior in step with the version you ship, and add a `CHANGELOG.md` entry
for every user-visible change.

## Scope

The current capability is dependency vulnerability auditing. The skill is named
`security-audit-skill` because it is intended to grow into broader security audits. When adding a
new audit area, add it as a clearly separated mode or reference in `SKILL.md`, update `description`
so agents can discover it, and keep the dependency workflow unchanged unless the task says
otherwise.

## Git

Use short imperative commit subjects with a body that explains why. Do not commit generated
reports, `__pycache__`, `.pytest_cache`, or `.DS_Store`. Do not push or open pull requests unless
asked.
