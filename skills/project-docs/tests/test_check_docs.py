"""Exercise the public CLI against real temporary projects."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_docs.py"


class CheckDocsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write("AGENTS.md", "# Rules\n\nRead [docs](docs/AGENTS.md).\n")
        self.write("docs/AGENTS.md", "# Documentation\n\nOne owner per fact.\n")

    def write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def check(self, config=None, *extra):
        args = [sys.executable, str(SCRIPT), str(self.root), "--json"]
        if config is not None:
            self.write("rules.json", json.dumps(config))
            args.extend(["--config", "rules.json"])
        result = subprocess.run(args + list(extra), text=True, capture_output=True)
        self.assertTrue(result.stdout.strip(), result.stderr)
        try:
            report = json.loads(result.stdout)
        except ValueError:
            self.fail(result.stdout + result.stderr)
        return result.returncode, report

    def codes(self, report):
        return {item["code"] for item in report["findings"]}

    def test_valid_project_is_read_only_and_repeatable(self):
        def digest():
            return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.root.rglob("*") if p.is_file()}
        before = digest()
        first = self.check()
        self.assertEqual(first[0], 0, first)
        self.assertEqual(first, self.check())
        self.assertEqual(before, digest())
        self.assertFalse(first[1]["scope"]["semantic_validation"])

    def test_missing_required_file_fails(self):
        (self.root / "AGENTS.md").unlink()
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("required-file", self.codes(report))

    def test_broken_inline_and_image_links_fail(self):
        self.write("README.md", "[manual](missing.md)\n![image](missing.png)\n")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(sum(f["code"] == "local-link" for f in report["findings"]), 2)

    def test_reference_links_and_shortcuts_are_checked(self):
        self.write("README.md", "[read][guide]\n[short]\n[guide]: missing.md\n[short]: absent.md\n")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(sum(f["code"] == "local-link" for f in report["findings"]), 2)

    def test_unresolved_explicit_reference_is_error(self):
        self.write("README.md", "[read][absent]\n")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("reference-link", self.codes(report))

    def test_external_links_code_and_comments_are_not_local_targets(self):
        self.write("README.md", "[web](https://example.test/a) [mail](mailto:a@b.test)\n"
                   "[hash](#section) `TODO [bad](none.md)`\n"
                   "```md\n[bad](none.md)\nTODO\n```\n"
                   "~~~md\n![bad](none.png)\n~~~\n<!-- [bad](none.md) -->\n")
        code, report = self.check()
        self.assertEqual(code, 0, report)

    def test_encoded_spaces_title_and_parentheses_resolve(self):
        self.write("docs/a (b).md", "# Fine\n")
        self.write("README.md", '[one](docs/a%20(b).md) [two](<docs/a (b).md> "title")\n')
        code, report = self.check()
        self.assertEqual(code, 0, report)

    def test_ignored_cache_vendor_and_build_content_is_not_scanned(self):
        for folder in (".cache", "vendor", "node_modules", "build", ".venv", "target"):
            self.write(folder + "/bad.md", "[bad](missing.md)\nTODO\n")
        code, report = self.check()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["scope"]["files_checked"], 2)

    def test_config_exclusion_is_relative_glob(self):
        self.write("drafts/x.md", "TODO\n")
        code, report = self.check({"exclude": ["drafts/**"]})
        self.assertEqual(code, 0, report)

    def test_placeholder_is_detected_in_prose(self):
        self.write("README.md", "# {{project_name}}\n\n待填写。\n")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("placeholder", self.codes(report))

    def test_mixed_budget_counts_cjk_and_words(self):
        self.write("brief.md", "你好 world worker\n")
        code, report = self.check({"budgets": {"brief.md": {"metric": "mixed", "max": 3}}})
        self.assertEqual(code, 1)
        finding = next(f for f in report["findings"] if f["code"] == "budget")
        self.assertIn("4", finding["message"])

    def test_word_budget_exact_limit_passes(self):
        self.write("brief.md", "hello worker\n")
        code, report = self.check({"budgets": {"brief.md": {"metric": "words", "max": 2}}})
        self.assertEqual(code, 0, report)

    def test_budgeted_missing_file_fails(self):
        code, report = self.check({"budgets": {"absent.md": {"metric": "mixed", "max": 5}}})
        self.assertEqual(code, 1)
        self.assertIn("budget-file", self.codes(report))

    def note(self, lifecycle, status, body, topic="2026-10-29-task.md"):
        return self.write(f".agents/notes/{lifecycle}/architecture/{topic}",
                          f"# Agent Note: Task\n\nStatus: {status}\n\n{body}")

    def test_implemented_note_checks_state_and_sections(self):
        self.note("implemented", "proposed", "## Problem\n\n## Proposal\n")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("note-status", self.codes(report))
        self.assertIn("note-sections", self.codes(report))

    def test_implemented_note_cannot_keep_proposal_sections(self):
        self.note("implemented", "implemented", "## Problem\nP\n## Decision\nD\n"
                  "## Alternatives considered\nA\n## Consequences\nC\n## Plan\nLater\n")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("note-sections", self.codes(report))

    def test_chinese_note_headings_are_supported(self):
        self.note("implemented", "implemented", "## 问题\nP\n## 决定\nD\n"
                  "## 考虑过的替代方案\nA\n## 后果\nC\n")
        code, report = self.check()
        self.assertEqual(code, 0, report)

    def test_note_tree_instruction_and_navigation_files_are_not_notes(self):
        self.write('.agents/notes/implemented/AGENTS.md', '# Note rules\n\nWrite current facts.\n')
        self.write('.agents/notes/implemented/architecture/README.md', '# Architecture decisions\n')
        code, report = self.check()
        self.assertEqual(code, 0, report)

    def test_proposed_and_rejected_notes(self):
        body = "## Problem\nP\n## Proposal\nD\n## Alternatives considered\nA\n"
        self.note("proposed", "proposed", body + "## Acceptance criteria\nX\n## Risks\nR\n")
        self.note("rejected", "rejected — no current need", body)
        code, report = self.check()
        self.assertEqual(code, 0, report)

    def test_rejected_note_needs_reason(self):
        self.note("rejected", "rejected", "## Problem\nP\n## Proposal\nD\n## Alternatives considered\nA\n")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("note-status", self.codes(report))

    def test_note_date_and_class_are_validated(self):
        self.write(".agents/notes/implemented/random/2026-02-30-task.md", "# Agent Note: X\n")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("note-path", self.codes(report))

    def test_empty_note_sections_fail(self):
        self.note("implemented", "implemented", "## Problem\n## Decision\n"
                  "## Alternatives considered\n## Consequences\n")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("note-content", self.codes(report))

    def test_archive_content_is_frozen_history_and_reference_warns(self):
        self.note("archived", "implemented", "Archived: 2026-10-29\n\n[old](gone.md)\nTODO\n")
        self.write("history.md", "历史依据：[record](.agents/notes/archived/architecture/2026-10-29-task.md)\n")
        code, report = self.check()
        self.assertEqual(code, 0, report)
        self.assertIn("archive-reference", self.codes(report))
        self.assertEqual(report["summary"]["errors"], 0)

    def test_archive_requires_date(self):
        self.note("archived", "implemented", "Old history\n")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("archive-date", self.codes(report))

    def test_existing_adr_mapping_skips_canonical_format_and_reports_limit(self):
        self.write("docs/adr/0001-local.md", "# Choice\n\nStatus: accepted\n")
        code, report = self.check({"note_roots": [{"path": "docs/adr", "format": "external"}]})
        self.assertEqual(code, 0, report)
        self.assertIn("external-notes", self.codes(report))

    def test_invalid_config_returns_two(self):
        for config in ({"typo": []}, {"required_files": "AGENTS.md"},
                       {"budgets": {"AGENTS.md": {"max": -1, "metric": "mixed"}}},
                       {"required_files": ["../outside.md"]}):
            with self.subTest(config=config):
                code, report = self.check(config)
                self.assertEqual(code, 2)
                self.assertIn("configuration", self.codes(report))

    def test_invalid_json_returns_two(self):
        self.write("invalid.json", "{")
        code, report = self.check(None, "--config", "invalid.json")
        self.assertEqual(code, 2)
        self.assertIn("configuration", self.codes(report))

    def test_invalid_utf8_is_not_success(self):
        (self.root / "broken.md").write_bytes(b"\xff")
        code, report = self.check()
        self.assertEqual(code, 2)
        self.assertIn("read-error", self.codes(report))

    def test_empty_corpus_never_passes(self):
        (self.root / "AGENTS.md").unlink()
        (self.root / "docs/AGENTS.md").unlink()
        code, report = self.check({"required_files": []})
        self.assertEqual(code, 1)
        self.assertIn("empty-corpus", self.codes(report))

    def test_config_cannot_silently_exclude_required_document(self):
        code, report = self.check({"exclude": ["AGENTS.md"]})
        self.assertEqual(code, 2)
        self.assertIn("configuration", self.codes(report))

    def test_excluding_parent_of_required_or_budgeted_file_is_invalid(self):
        self.write('docs/AGENTS.md', 'TODO one two three\n')
        code, report = self.check({'exclude': ['docs'], 'budgets': {
            'docs/AGENTS.md': {'metric': 'words', 'max': 1}}})
        self.assertEqual(code, 2, report)
        self.assertIn('configuration', self.codes(report))

    def test_noncanonical_budget_path_is_rejected(self):
        code, report = self.check({'budgets': {'./AGENTS.md': {'metric': 'words', 'max': 1}}})
        self.assertEqual(code, 2, report)
        self.assertIn('configuration', self.codes(report))

    def test_nonmarkdown_budget_target_is_rejected(self):
        self.write('AGENTS.txt', 'one two three\n')
        code, report = self.check({'budgets': {'AGENTS.txt': {'metric': 'words', 'max': 1}}})
        self.assertEqual(code, 2, report)
        self.assertIn('configuration', self.codes(report))

    def test_archive_still_honors_explicit_budget(self):
        path = self.note('archived', 'implemented', 'Archived: 2026-10-29\n\nHistory\n')
        code, report = self.check({'budgets': {
            path.relative_to(self.root).as_posix(): {'metric': 'words', 'max': 1}}})
        self.assertEqual(code, 1, report)
        self.assertIn('budget', self.codes(report))

    def test_required_file_in_symlinked_directory_is_not_silently_skipped(self):
        self.write('rules/rules.md', '# rules\n')
        try:
            (self.root / 'alias').symlink_to(self.root / 'rules', target_is_directory=True)
        except OSError:
            self.skipTest('Host cannot create directory symlinks')
        code, report = self.check({'required_files': ['alias/rules.md']})
        self.assertEqual(code, 1, report)
        self.assertIn('unscanned-file', self.codes(report))

    def test_escape_target_fails(self):
        self.write("README.md", "[outside](../other.md)\n")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertIn("outside-root", self.codes(report))

    def test_symlink_escape_is_not_read(self):
        with tempfile.TemporaryDirectory() as outside:
            dest = Path(outside) / "secret.md"
            dest.write_text("# outside", encoding="utf-8")
            try:
                (self.root / "alias.md").symlink_to(dest)
            except OSError:
                self.skipTest("Host cannot create symlinks")
            code, report = self.check()
            self.assertEqual(code, 1)
            self.assertIn("outside-root", self.codes(report))

    def test_directory_links_are_not_traversed(self):
        with tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "broken.md").write_bytes(b"\xff")
            try:
                (self.root / "external").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("Host cannot create directory symlinks")
            code, report = self.check()
            self.assertEqual(code, 0, report)
            self.assertEqual(report["scope"]["files_checked"], 2)


if __name__ == "__main__":
    unittest.main()
