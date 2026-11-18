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
        self.assertIn("**Overall: 🔴 Red (BLOCKED).**", readme)
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

    def test_untrusted_report_values_cannot_inject_markup_or_links(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = self._folder(Path(raw))
            path = folder / "dependency-audit" / "latest.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["mode"] = "<img src=x onerror=alert(1)>"
            data["gate_status"] = "[x](http://evil.example)"
            data["summary"]["mode"] = "<img src=x onerror=alert(1)>"
            data["summary"]["status"] = "[x](http://evil.example)"
            data["summary"]["top_findings"][0]["id"] = "<script>x</script>[a](http://evil.example)|"
            data["summary"]["top_findings"][0]["subject"] = "<b>pkg</b>"
            data["summary"]["top_findings"][0]["severity"] = "high](http://evil.example)"
            data["summary"]["source_gaps"] = [{"source": "<b>nvd</b>", "state": "partial"}]
            path.write_text(json.dumps(data), encoding="utf-8")
            bad = folder / "evil](x)"
            bad.mkdir()
            (bad / "latest.json").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            readme = dict(refresh_folder_docs(folder))[folder / "README.md"]
        for forbidden in ("<script>", "<img", "<b>", "](http://evil.example)", "evil](x)"):
            self.assertNotIn(forbidden, readme)

    def _write(self, folder: Path, name: str, data: dict) -> None:
        area = folder / name
        area.mkdir(parents=True, exist_ok=True)
        (area / "latest.json").write_text(json.dumps(data), encoding="utf-8")

    def _summary(self, status: str, **extra: object) -> dict:
        return {"area": "x", "status": status, "mode": "change",
                "counts": {"blocking": 0, "warnings": 0, "excluded": 0, "source_gaps": 0},
                "top_findings": [], "more_findings": 0, "source_gaps": [], **extra}

    def _three_areas(self, folder: Path) -> str:
        for name, status in (("a-pass", "pass"), ("b-warn", "warnings"), ("c-block", "blocked")):
            self._write(folder, name, {"gate_status": status, "mode": "change", "summary": self._summary(status)})
        return dict(refresh_folder_docs(folder))[folder / "README.md"]

    def test_readme_comes_only_from_the_summary(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = self._folder(Path(raw))
            path = folder / "dependency-audit" / "latest.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["findings"][0]["advisory"]["id"] = "CHANGED-ONLY-IN-FINDINGS"
            path.write_text(json.dumps(data), encoding="utf-8")
            readme = dict(refresh_folder_docs(folder))[folder / "README.md"]
        self.assertNotIn("CHANGED-ONLY-IN-FINDINGS", readme)
        self.assertIn("GHSA", readme)

    def test_readme_shows_rag_word_overall_banner_legend_and_pie(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw) / ".security-audit"
            readme = self._three_areas(folder)
        for label in ("🟢 Green", "🟠 Amber", "🔴 Red"):
            self.assertIn(label, readme)
        self.assertIn("**Overall: 🔴 Red", readme)
        self.assertIn("pie title Areas by RAG status", readme)
        for slice_line in ('"Green" : 1', '"Amber" : 1', '"Red" : 1'):
            self.assertIn(slice_line, readme)

    def test_pie_omits_zero_slices_and_holds_only_counts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = self._folder(Path(raw))
            readme = dict(refresh_folder_docs(folder))[folder / "README.md"]
        self.assertNotIn('"Green"', readme)
        self.assertNotIn('"Amber"', readme)
        self.assertIn('"Red" : 1', readme)

    def test_unavailable_or_unknown_status_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw) / ".security-audit"
            self._write(folder, "a", {"gate_status": "unavailable"})
            self._write(folder, "b", {"gate_status": "[x](y)", "summary": []})
            self._write(folder, "c", {})
            readme = dict(refresh_folder_docs(folder))[folder / "README.md"]
        self.assertEqual(readme.count("🔴 Red |"), 3)
        self.assertNotIn("| 🟢 Green |", readme)
        self.assertNotIn('"Green"', readme)

    def test_pre_summary_report_is_listed_with_status_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = self._folder(Path(raw))
            path = folder / "dependency-audit" / "latest.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            del data["summary"]
            data["schema_version"] = "1.0"
            path.write_text(json.dumps(data), encoding="utf-8")
            readme = dict(refresh_folder_docs(folder))[folder / "README.md"]
        self.assertIn("| [dependency-audit](dependency-audit/latest.md) | 🔴 Red | blocked | change |", readme)
        self.assertIn("re-run the audit", readme)

    def test_malformed_summary_falls_back_without_crashing(self) -> None:
        for bad in ([], "x", None, {"counts": {"blocking": -1}}):
            with self.subTest(bad=repr(bad)), tempfile.TemporaryDirectory() as raw:
                folder = Path(raw) / ".security-audit"
                self._write(folder, "area", {"gate_status": "pass", "mode": "main", "summary": bad})
                readme = dict(refresh_folder_docs(folder))[folder / "README.md"]
                self.assertIn("| [area](area/latest.md) | 🟢 Green | pass | main |", readme)
                self.assertIn("re-run the audit", readme)

    def test_oversized_summary_is_capped_in_the_readme(self) -> None:
        finding = {"severity": "high", "id": "ADV", "subject": "pkg:npm/a@1", "flags": []}
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw) / ".security-audit"
            summary = self._summary("blocked", top_findings=[finding] * 1000, more_findings=990)
            self._write(folder, "area", {"gate_status": "blocked", "summary": summary})
            readme = dict(refresh_folder_docs(folder))[folder / "README.md"]
        self.assertLessEqual(sum(line.startswith("- **high**") for line in readme.splitlines()), 10)
        self.assertIn("and 990 more", readme)

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
