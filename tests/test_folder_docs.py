"""Tests for the generated ``.security-audit`` README.md and AGENTS.md."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "security-audit-skill" / "scripts"))

from dependency_audit.folder_docs import AGENTS_MD, is_security_dir, refresh_folder_docs  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "expected-report.json"


class FolderDocsTest(unittest.TestCase):
    def _folder(self, root: Path) -> Path:
        area = root / ".security-audit" / "dependency-audit"
        area.mkdir(parents=True)
        (area / "latest.json").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        return area.parent

    def test_only_security_audit_folder_gets_documents(self) -> None:
        self.assertTrue(is_security_dir(Path("/p/.security-audit")))
        self.assertFalse(is_security_dir(Path("/p/.security")))
        self.assertFalse(is_security_dir(Path("/p/reports")))

    def test_readme_summarizes_status_and_links_area_report(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = self._folder(Path(raw))
            readme = dict(refresh_folder_docs(folder))[folder / "README.md"]
        self.assertIn("**Overall: BLOCKED.**", readme)
        self.assertIn("[dependency-audit](dependency-audit/latest.md)", readme)
        self.assertIn("AGENTS.md", readme)

    def test_documents_contain_no_absolute_local_paths_or_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = self._folder(Path(raw))
            texts = [text for _path, text in refresh_folder_docs(folder)]
        for text in texts:
            self.assertNotIn(raw, text)
            self.assertNotIn("/Users/", text)
            self.assertNotIn("api_key:", text)
            self.assertNotIn("password:", text)

    def test_empty_folder_and_unreadable_report_do_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw) / ".security-audit"
            (folder / "bad").mkdir(parents=True)
            (folder / "bad" / "latest.json").write_text("{not json", encoding="utf-8")
            readme = dict(refresh_folder_docs(folder))[folder / "README.md"]
            self.assertIn("INVALID", readme)
            empty = Path(raw) / "other" / ".security-audit"
            empty.mkdir(parents=True)
            self.assertIn("No audit reports found", dict(refresh_folder_docs(empty))[empty / "README.md"])

    def test_gitignore_excludes_credential_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = self._folder(Path(raw))
            ignore = dict(refresh_folder_docs(folder))[folder / ".gitignore"]
        for pattern in ("private/", "raw/", ".env", "*.pem", "*.key", "credentials*"):
            self.assertIn(pattern, ignore.splitlines())
        for published in ("README.md", "AGENTS.md", "latest.json", "latest.md"):
            self.assertNotIn(published, ignore)

    def test_written_documents_redact_supplied_credentials(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "security-audit-skill" / "scripts"))
        from dependency_audit.models import AuditMode, AuditResult
        from dependency_audit.reporting import write_reports

        with tempfile.TemporaryDirectory() as raw:
            area = Path(raw) / ".security-audit" / "dependency-audit"
            result = AuditResult.empty(AuditMode.CHANGE)
            result.project_revision = "tok-ABC123SECRET"
            write_reports(result, area, credential_values=("tok-ABC123SECRET",))
            for name in ("README.md", "AGENTS.md", ".gitignore"):
                self.assertNotIn("tok-ABC123SECRET", (area.parent / name).read_text(encoding="utf-8"))
            self.assertTrue((area.parent / ".gitignore").is_file())

    def test_agents_document_covers_publication_safety(self) -> None:
        self.assertIn("may be committed to a public repository", AGENTS_MD)
        self.assertIn("Publication safety", AGENTS_MD)
        self.assertIn("ask the user before committing", " ".join(AGENTS_MD.split()))


if __name__ == "__main__":
    unittest.main()
