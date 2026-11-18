# Changelog

All notable changes to this skill are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the skill follows
[Semantic Versioning](https://semver.org/) via `metadata.version` in `SKILL.md`.

## [Unreleased]

### Added
- Generated `.security-audit/README.md` (executive summary), `AGENTS.md` (how to work with findings),
  and `.gitignore` (credential-bearing paths) alongside each audit's reports.
- `--acceptances` records the mitigation and approval a release needs for a no-fix finding.
- Repository logistics: `CLAUDE.md`, `CONTRIBUTING.md`, `SECURITY.md`, `.editorconfig`, issue and
  pull request templates, Dependabot for GitHub Actions, and committed settings under
  `.github/settings/`.

### Changed
- **Breaking:** reports now default to `PROJECT/.security-audit/dependency-audit/` (was
  `.security/dependency-audit/`). The next release should be 2.0.0.
- The skill moved to `skills/security-audit-skill/`; tests and specs are no longer part of it.

### Fixed
- CVSS enrichment ignores GitHub's empty `cvss_v4` placeholder and NVD's non-CVSS containers, while
  still failing closed on malformed CVSS data.
- Untrusted report values are HTML- and Markdown-escaped in the generated README.

## [1.1.0]

Dependency vulnerability audit spun off from `spec-driven-development-skills` as
`security-audit-skill`: OSV, CISA KEV, and native-tool evidence in `change`, `main`, and `release`
modes with JSON and Markdown reports.
