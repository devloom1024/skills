"""Behavioral CLI tests using real temporary files and optional local Git."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / 'skills' / 'decision-records' / 'scripts' / 'archive_records.py'


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / '.agents/notes/archived'
        self.manifest = self.archive / 'manifest.json'
        self.record = '.agents/notes/implemented/architecture/2026-10-20-cache.md'
        self.body = ('# Agent Note: Cache\n\nStatus: implemented\n\n## 问题\nP\n'
                     '## 决定\nD\n## 考虑过的替代方案\nA\n## 后果\nC\n')
        self.write(self.record, self.body)

    def write(self, path, content):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode('utf-8') if isinstance(content, str) else content)
        return path

    def cli(self, mode='verify', *args):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), mode, str(self.root), '--json', *args],
                                text=True, capture_output=True)
        self.assertTrue(result.stdout.strip(), result.stderr)
        try:
            report = json.loads(result.stdout)
        except ValueError:
            self.fail(result.stdout + result.stderr)
        return result.returncode, report

    def seal(self, record=None, *args):
        return self.cli('seal', '--record', record or self.record, '--date', '2026-10-29', *args)

    def codes(self, report):
        return {item['code'] for item in report['findings']}

    def first(self):
        code, report = self.seal()
        self.assertEqual(code, 0, report)
        target = self.manifest.parent / 'architecture/2026-10-20-cache.md'
        self.assertTrue(target.exists(), report)
        self.assertTrue(self.manifest.exists(), report)
        return target

    def snapshot(self):
        return self.write('trusted.json', self.manifest.read_bytes())

    def test_empty_archive_verify_is_read_only(self):
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        code, report = self.cli()
        self.assertEqual(code, 0, report)
        self.assertEqual(report['scope']['records_checked'], 0)
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')))

    def test_first_seal_preserves_body_and_hashes_exact_bytes(self):
        target = self.first()
        expected = self.body.replace('Status: implemented\n', 'Status: implemented\nArchived: 2026-10-29\n', 1).encode('utf-8')
        self.assertEqual(target.read_bytes(), expected)
        self.assertFalse((self.root / self.record).exists())
        item = json.loads(self.manifest.read_text())['entries'][0]
        self.assertEqual(item, {'path': 'architecture/2026-10-20-cache.md', 'archived_on': '2026-10-29',
                                'sha256': hashlib.sha256(expected).hexdigest()})

    def test_crlf_and_bom_are_preserved(self):
        original = b'\xef\xbb\xbf' + self.body.replace('\n', '\r\n').encode('utf-8')
        self.write(self.record, original)
        target = self.first()
        expected = original.replace(b'Status: implemented\r\n', b'Status: implemented\r\nArchived: 2026-10-29\r\n', 1)
        self.assertEqual(target.read_bytes(), expected)

    def test_changed_file_is_detected_and_not_resealed(self):
        target = self.first()
        target.write_bytes(target.read_bytes() + b'changed\n')
        code, report = self.cli()
        self.assertEqual(code, 1)
        self.assertIn('hash-mismatch', self.codes(report))
        old_manifest = self.manifest.read_bytes()
        self.write('.agents/notes/implemented/architecture/2026-10-21-other.md', self.body)
        code, _ = self.seal('.agents/notes/implemented/architecture/2026-10-21-other.md')
        self.assertNotEqual(code, 0)
        self.assertEqual(old_manifest, self.manifest.read_bytes())

    def test_deleted_or_moved_archive_is_detected(self):
        target = self.first()
        target.rename(target.with_name('2026-10-20-moved.md'))
        code, report = self.cli()
        self.assertEqual(code, 1)
        self.assertIn('missing-record', self.codes(report))
        self.assertIn('unsealed-record', self.codes(report))

    def test_existing_unsealed_history_is_not_bootstrapped(self):
        self.write('.agents/notes/archived/architecture/2026-10-01-old.md',
                   self.body.replace('Status: implemented\n', 'Status: implemented\nArchived: 2026-10-10\n'))
        code, report = self.seal()
        self.assertEqual(code, 1)
        self.assertIn('unsealed-record', self.codes(report))
        self.assertTrue((self.root / self.record).exists())
        self.assertFalse(self.manifest.exists())

    def test_second_seal_requires_baseline(self):
        self.first()
        second = '.agents/notes/implemented/architecture/2026-10-21-other.md'
        self.write(second, self.body)
        code, report = self.seal(second)
        self.assertEqual(code, 1)
        self.assertIn('baseline-required', self.codes(report))

    def test_append_with_explicit_snapshot_and_verify_prefix(self):
        self.first()
        baseline = self.snapshot()
        second = '.agents/notes/implemented/architecture/2026-10-21-other.md'
        self.write(second, self.body)
        code, report = self.seal(second, '--baseline-manifest', str(baseline))
        self.assertEqual(code, 0, report)
        self.assertEqual(len(json.loads(self.manifest.read_text())['entries']), 2)
        code, report = self.cli('verify', '--baseline-manifest', str(baseline))
        self.assertEqual(code, 0, report)
        self.assertEqual(report['scope']['protected_entries'], 1)

    def test_rewritten_manifest_and_content_fail_trusted_comparison(self):
        target = self.first()
        baseline = self.snapshot()
        target.write_bytes(target.read_bytes() + b'rewritten\n')
        data = json.loads(self.manifest.read_text())
        data['entries'][0]['sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
        self.manifest.write_text(json.dumps(data), encoding='utf-8')
        code, report = self.cli('verify', '--baseline-manifest', str(baseline))
        self.assertEqual(code, 1)
        self.assertIn('baseline-rewrite', self.codes(report))

    def test_removed_manifest_and_records_fail_trusted_comparison(self):
        target = self.first()
        baseline = self.snapshot()
        target.unlink()
        self.manifest.unlink()
        code, report = self.cli('verify', '--baseline-manifest', str(baseline))
        self.assertEqual(code, 1)
        self.assertIn('baseline-rewrite', self.codes(report))

    def test_current_manifest_cannot_be_its_own_baseline(self):
        self.first()
        code, report = self.cli('verify', '--baseline-manifest', str(self.manifest))
        self.assertEqual(code, 2)
        self.assertIn('configuration', self.codes(report))

    def test_no_history_reports_current_consistency_only(self):
        self.first()
        code, report = self.cli()
        self.assertEqual(code, 0, report)
        self.assertIn('untrusted-history', self.codes(report))
        self.assertFalse(report['scope']['history_verified'])

    def test_reordered_manifest_entries_fail_baseline(self):
        self.first()
        baseline = self.snapshot()
        second = '.agents/notes/implemented/architecture/2026-10-21-other.md'
        self.write(second, self.body)
        code, report = self.seal(second, '--baseline-manifest', str(baseline))
        self.assertEqual(code, 0, report)
        baseline.write_bytes(self.manifest.read_bytes())
        data = json.loads(self.manifest.read_text())
        data['entries'].reverse()
        self.manifest.write_text(json.dumps(data))
        code, report = self.cli('verify', '--baseline-manifest', str(baseline))
        self.assertEqual(code, 1)
        self.assertIn('baseline-rewrite', self.codes(report))

    def test_verify_does_not_modify_archive(self):
        self.first()
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(self.cli()[0], 0)
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_snapshot_covers_all_entries_before_another_seal(self):
        self.first()
        baseline = self.snapshot()
        second = '.agents/notes/implemented/architecture/2026-10-21-other.md'
        self.write(second, self.body)
        self.assertEqual(self.seal(second, '--baseline-manifest', str(baseline))[0], 0)
        third = '.agents/notes/implemented/architecture/2026-10-22-third.md'
        self.write(third, self.body)
        code, report = self.seal(third, '--baseline-manifest', str(baseline))
        self.assertEqual(code, 1)
        self.assertIn('baseline-required', self.codes(report))

    def test_caught_manifest_write_failure_rolls_back(self):
        import importlib.util
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location('archive_records', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        audit = module.Archive(self.root, '.agents/notes')
        with patch.object(module.os, 'replace', side_effect=OSError('simulated full disk')):
            with self.assertRaises(OSError):
                audit.seal(self.record, '2026-10-29')
        self.assertEqual((self.root / self.record).read_bytes(), self.body.encode('utf-8'))
        self.assertFalse(self.manifest.exists())
        self.assertFalse((self.archive / 'architecture/2026-10-20-cache.md').exists())
        self.assertFalse((self.root / '.agents/notes/.archive-records.lock').exists())

    def test_target_write_failure_removes_partial_archive(self):
        import importlib.util
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location('archive_records', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        audit = module.Archive(self.root, '.agents/notes')
        normal_open = Path.open
        class BrokenWriter:
            def __init__(self, path):
                self.file = normal_open(path, 'xb')
            def __enter__(self):
                return self
            def write(self, content):
                self.file.write(content[:12])
                raise OSError('simulated target write failure')
            def __exit__(self, *args):
                self.file.close()
        def selective_open(path, mode='r', *args, **kwargs):
            if mode == 'xb':
                return BrokenWriter(path)
            return normal_open(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', selective_open):
            with self.assertRaises(OSError):
                audit.seal(self.record, '2026-10-29')
        self.assertEqual((self.root / self.record).read_bytes(), self.body.encode())
        self.assertFalse((self.archive / 'architecture/2026-10-20-cache.md').exists())
        self.assertFalse(self.manifest.exists())

    def test_unsupported_state_and_date_do_not_mutate(self):
        for state in ('proposed', 'rejected', 'accepted'):
            self.write(self.record, self.body.replace('Status: implemented', 'Status: ' + state))
            code, report = self.seal()
            self.assertEqual(code, 1, report)
            self.assertTrue((self.root / self.record).exists())
            self.assertFalse(self.manifest.exists())
        self.write(self.record, self.body)
        code, report = self.cli('seal', '--record', self.record, '--date', '2026-02-30')
        self.assertEqual(code, 2, report)
        self.assertTrue((self.root / self.record).exists())

    def test_proposed_path_and_existing_archived_stamp_rejected(self):
        path = '.agents/notes/proposed/architecture/2026-10-20-cache.md'
        self.write(path, self.body)
        code, report = self.seal(path)
        self.assertEqual(code, 1, report)
        self.write(self.record, self.body.replace('Status: implemented\n', 'Status: implemented\nArchived: 2026-10-29\n'))
        code, report = self.seal()
        self.assertEqual(code, 1, report)
        self.assertIn('source-record', self.codes(report))

    def test_escape_or_noncanonical_source_rejected(self):
        for path in ('../outside.md', './' + self.record, '/absolute.md'):
            code, report = self.seal(path)
            self.assertEqual(code, 2, report)
            self.assertIn('configuration', self.codes(report))

    def test_invalid_or_unsupported_manifest_rejected(self):
        self.write('.agents/notes/archived/manifest.json', '{')
        code, report = self.cli()
        self.assertEqual(code, 2)
        self.assertIn('manifest', self.codes(report))
        self.manifest.write_text(json.dumps({'version': 99, 'archive_root': '.agents/notes/archived', 'entries': []}))
        code, report = self.cli()
        self.assertEqual(code, 2, report)

    def test_duplicate_or_escaping_entries_rejected(self):
        self.first()
        original = json.loads(self.manifest.read_text())
        for path in ('../escape.md', './architecture/a.md', 'architecture/2026-10-20-cache.md'):
            data = json.loads(json.dumps(original))
            item = dict(data['entries'][0], path=path)
            data['entries'].append(item)
            self.manifest.write_text(json.dumps(data))
            code, report = self.cli()
            self.assertEqual(code, 2, report)

    def test_source_and_archive_links_are_not_followed(self):
        with tempfile.TemporaryDirectory() as outside:
            dest = Path(outside) / 'note.md'
            dest.write_text(self.body, encoding='utf-8')
            source = self.root / self.record
            source.unlink()
            try:
                source.symlink_to(dest)
            except OSError:
                self.skipTest('Host cannot create symlinks')
            code, report = self.seal()
            self.assertNotEqual(code, 0, report)
            self.assertIn('linked-path', self.codes(report))

    def test_existing_lock_prevents_mutation_and_verify(self):
        self.write('.agents/notes/.archive-records.lock', 'another operation\n')
        code, report = self.seal()
        self.assertEqual(code, 1, report)
        self.assertIn('operation-lock', self.codes(report))
        self.assertTrue((self.root / self.record).exists())
        code, report = self.cli()
        self.assertEqual(code, 1, report)

    def test_destination_collision_is_not_overwritten(self):
        dest = self.write('.agents/notes/archived/architecture/2026-10-20-cache.md', 'old\n')
        code, report = self.seal()
        self.assertNotEqual(code, 0, report)
        self.assertEqual(dest.read_text(), 'old\n')

    def test_custom_notes_root_and_unregistered_asset(self):
        custom = 'docs/decisions/implemented/architecture/2026-10-20-cache.md'
        self.write(custom, self.body)
        code, report = self.seal(custom, '--notes-root', 'docs/decisions')
        self.assertEqual(code, 0, report)
        self.assertTrue((self.root / 'docs/decisions/archived/manifest.json').exists())
        self.write('docs/decisions/archived/image.png', b'png')
        code, report = self.cli('verify', '--notes-root', 'docs/decisions')
        self.assertEqual(code, 1, report)
        self.assertIn('unsupported-file', self.codes(report))

    @unittest.skipUnless(shutil.which('git'), 'Git is not available')
    def test_git_head_protects_committed_manifest(self):
        def git(*args):
            result = subprocess.run(['git', '-C', str(self.root), *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        git('init')
        git('config', 'user.name', 'Test')
        git('config', 'user.email', 'test@example.invalid')
        git('config', 'core.autocrlf', 'false')
        self.first()
        git('add', '.')
        git('commit', '-m', 'Seal first record')
        code, report = self.cli()
        self.assertEqual(code, 0, report)
        self.assertTrue(report['scope']['history_verified'])
        target = self.archive / 'architecture/2026-10-20-cache.md'
        target.write_bytes(target.read_bytes() + b'tampered\n')
        data = json.loads(self.manifest.read_text())
        data['entries'][0]['sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
        self.manifest.write_text(json.dumps(data))
        code, report = self.cli()
        self.assertEqual(code, 1)
        self.assertIn('baseline-rewrite', self.codes(report))

    @unittest.skipUnless(shutil.which('git'), 'Git is not available')
    def test_project_gitattributes_preserves_sealed_bytes_with_autocrlf(self):
        def git(*args):
            result = subprocess.run(['git', '-C', str(self.root), *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        git('init')
        git('config', 'user.name', 'Test')
        git('config', 'user.email', 'test@example.invalid')
        git('config', 'core.autocrlf', 'true')
        self.write('.gitattributes', '.agents/notes/archived/** -text\n')
        target = self.first()
        sealed = target.read_bytes()
        git('add', '.')
        git('commit', '-m', 'Seal with project byte-preserving attributes')
        target.unlink()
        git('checkout-index', '--force', '--', target.relative_to(self.root).as_posix())
        self.assertEqual(target.read_bytes(), sealed)
        code, report = self.cli()
        self.assertEqual(code, 0, report)
        self.assertTrue(report['scope']['history_verified'])


if __name__ == '__main__':
    unittest.main()
