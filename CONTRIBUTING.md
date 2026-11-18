# Contributing

Thanks for helping improve `security-audit-skill`. The full contributor and maintainer rules live in
[AGENTS.md](AGENTS.md); they apply to people as well as AI agents. The essentials:

1. Open an issue first for anything beyond a small fix, and use the issue templates.
2. Branch from `main`. Write or update a test first, using fixtures under `tests/fixtures/`.
3. Run the offline suite before pushing:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
   ```

4. Keep to Python 3.10+ and the standard library only, and keep the skill failing closed: missing
   evidence is `unavailable`, never `pass`.
5. Keep `SKILL.md` and `references/` in sync with code changes, and add a `CHANGELOG.md` entry.
6. Open a pull request using the template. Squash merge is the preferred merge style.

Report security problems privately; see [SECURITY.md](SECURITY.md).
