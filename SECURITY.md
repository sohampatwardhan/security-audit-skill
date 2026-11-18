# Security policy

## Reporting a vulnerability

Please do not open a public issue. Report privately through GitHub's
[private vulnerability reporting](https://github.com/sohampatwardhan/security-audit-skill/security/advisories/new)
for this repository, with the affected version or commit, reproduction steps, and the impact you
see.

You can expect an acknowledgement within a few days. Fixes ship in a patch release and are noted in
[CHANGELOG.md](CHANGELOG.md).

## Scope

This skill audits other projects, so the most relevant issues are ones that make it report a
dependency set as safe when it is not, leak credentials into arguments or reports, execute data from
advisories or scanners, or write unsafe content into the published `.security-audit/` folder.

## Supported versions

Only the latest release receives fixes.
