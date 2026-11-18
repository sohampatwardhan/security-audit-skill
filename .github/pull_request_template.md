## Summary

<!-- What changed and why. Link the issue: Closes #N -->

## Checks

- [ ] `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` passes
- [ ] Tests cover the change, using offline fixtures
- [ ] `SKILL.md`, `references/`, and README match the behavior, and `CHANGELOG.md` has an entry
- [ ] No credential values, local paths, or hostnames in code, fixtures, or reports
- [ ] Failing or missing evidence still reads as `unavailable`, never `pass`
