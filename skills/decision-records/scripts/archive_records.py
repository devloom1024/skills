"""Verify and seal Agent Note archives; Python 3.10+, standard library only."""
import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile


CLASSES = {'architecture', 'feature', 'bug-fix', 'simplification', 'process', 'testing'}
METADATA = {'README.md', 'AGENTS.md', 'CLAUDE.md'}


class ArchiveError(Exception):
    def __init__(self, code, message, operational=False):
        super().__init__(message)
        self.code, self.operational = code, operational


def relative(value):
    if (not isinstance(value, str) or not value or value == '.' or '\\' in value
            or str(PurePosixPath(value)) != value or PurePosixPath(value).is_absolute()
            or '..' in PurePosixPath(value).parts or re.match(r'^[A-Za-z]:', value)):
        raise ArchiveError('configuration', 'Use a canonical project-relative path: ' + str(value), True)
    return value


def valid_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Use YYYY-MM-DD')
    return date.fromisoformat(value)


def no_links(root, path):
    """Reject symlinks and Windows reparse points on every existing component."""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        raise ArchiveError('configuration', 'Path is outside project', True)
    current = root
    for part in parts:
        current = current / part
        if current.exists() or current.is_symlink():
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                raise ArchiveError('linked-path', 'Archive operations do not follow links: ' + str(current))
    if not path.resolve().is_relative_to(root):
        raise ArchiveError('linked-path', 'Resolved path escapes project')


def parse_manifest(raw, archive_root):
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or set(data) != {'version', 'archive_root', 'entries'}:
            raise ValueError('Expected version, archive_root and entries')
        if type(data['version']) is not int or data['version'] != 1 or data['archive_root'] != archive_root:
            raise ValueError('Manifest version or archive_root does not match')
        if not isinstance(data['entries'], list):
            raise ValueError('entries must be a list')
        seen = set()
        for item in data['entries']:
            if not isinstance(item, dict) or set(item) != {'path', 'archived_on', 'sha256'}:
                raise ValueError('Invalid entry fields')
            path = relative(item['path'])
            if PurePosixPath(path).suffix != '.md' or path in seen or len(PurePosixPath(path).parts) < 2:
                raise ValueError('Invalid or duplicate record path')
            valid_date(item['archived_on'])
            if not isinstance(item['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', item['sha256']):
                raise ValueError('sha256 must be lowercase hexadecimal')
            seen.add(path)
        return data
    except (ValueError, TypeError, UnicodeError, ArchiveError) as error:
        raise ArchiveError('manifest', 'Invalid manifest: ' + str(error), True)


def empty_manifest(archive_root):
    return {'version': 1, 'archive_root': archive_root, 'entries': []}


def baseline_from_git(root, archive_relative):
    """Read committed metadata without changing index, branch, or checkout."""
    if not shutil.which('git'):
        return None
    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=20)
    top = git('rev-parse', '--show-toplevel')
    if top.returncode:
        return None
    git_root = Path(os.fsdecode(top.stdout).strip()).resolve()
    path = (root / archive_relative / 'manifest.json').relative_to(git_root).as_posix()
    head = git('rev-parse', '--verify', 'HEAD')
    if head.returncode:
        return None
    listing = git('ls-tree', 'HEAD', '--', path)
    if listing.returncode:
        raise ArchiveError('baseline-read', 'Cannot inspect Git HEAD manifest', True)
    if not listing.stdout:
        # Missing committed metadata is not a trusted snapshot of uncommitted history.
        return None
    value = git('show', 'HEAD:' + path)
    if value.returncode:
        raise ArchiveError('baseline-read', 'Cannot read committed manifest', True)
    return parse_manifest(value.stdout, archive_relative)


class Archive:
    def __init__(self, root, notes_root, baseline_path=None):
        self.root = root
        self.notes_relative = relative(notes_root)
        self.notes = root / notes_root
        self.archive_relative = notes_root + '/archived'
        self.folder = root / self.archive_relative
        self.manifest = self.folder / 'manifest.json'
        self.lock = self.notes / '.archive-records.lock'
        self.findings, self.checked = [], 0
        self.data = empty_manifest(self.archive_relative)
        self.baseline, self.baseline_path = None, baseline_path
        self.operational = False

    def add(self, code, message, path='', warning=False, info=False):
        self.findings.append({'severity': 'info' if info else ('warning' if warning else 'error'), 'code': code, 'path': path, 'message': message})

    def errors(self):
        return any(item['severity'] == 'error' for item in self.findings)

    def load_baseline(self):
        if self.baseline_path:
            path = Path(self.baseline_path)
            path = path if path.is_absolute() else self.root / path
            if path.resolve() == self.manifest.resolve() or (path.exists() and self.manifest.exists() and os.path.samefile(path, self.manifest)):
                raise ArchiveError('configuration', 'Current manifest cannot be its own trusted baseline', True)
            self.baseline = parse_manifest(path.read_bytes(), self.archive_relative)
        else:
            self.baseline = baseline_from_git(self.root, self.archive_relative)

    def verify(self, own_lock=False):
        no_links(self.root, self.notes)
        no_links(self.root, self.folder)
        no_links(self.root, self.manifest)
        no_links(self.root, self.lock)
        if self.lock.exists() and not own_lock:
            self.add('operation-lock', 'Operation lock exists; inspect process and files before recovery')
            return
        if self.manifest.exists():
            self.data = parse_manifest(self.manifest.read_bytes(), self.archive_relative)
        self.load_baseline()
        if self.baseline is not None:
            old = self.baseline['entries']
            if self.data['entries'][:len(old)] != old:
                self.add('baseline-rewrite', 'Previously sealed entries must remain an identical prefix')
        elif self.data['entries']:
            self.add('untrusted-history', 'Only current file/manifest consistency is checked; supply a trusted snapshot or commit the manifest', warning=True)
        recorded = {entry['path']: entry for entry in self.data['entries']}
        actual = set()
        if self.folder.exists():
            if not self.folder.is_dir():
                raise ArchiveError('archive-directory', 'Archive path must be a directory', True)
            def walk_error(error):
                raise error
            for folder, directories, files in os.walk(self.folder, followlinks=False, onerror=walk_error):
                base = Path(folder)
                for name in sorted(directories):
                    no_links(self.root, base / name)
                for name in sorted(files):
                    path = base / name
                    no_links(self.root, path)
                    rel = path.relative_to(self.folder).as_posix()
                    if path == self.manifest or name in METADATA:
                        continue
                    if path.suffix != '.md':
                        self.add('unsupported-file', 'Only Markdown records and declared metadata are supported', rel)
                        continue
                    actual.add(rel)
        for rel in sorted(actual - set(recorded)):
            self.add('unsealed-record', 'Existing archive file has no seal; do not silently establish a new baseline', rel)
        for rel, entry in recorded.items():
            path = self.folder / rel
            no_links(self.root, path)
            if rel not in actual:
                self.add('missing-record', 'Sealed record is absent or moved', rel)
                continue
            raw = path.read_bytes()
            self.checked += 1
            if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                self.add('hash-mismatch', 'Archived bytes differ from the seal', rel)
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeError:
                self.add('archive-header', 'Archive record must use UTF-8', rel)
                continue
            if not re.match(r'\A# Agent Note: [^\r\n]+\r?\n\r?\nStatus: implemented\r?\nArchived: ' + re.escape(entry['archived_on']) + r'(?:\r?\n|$)', text):
                self.add('archive-header', 'Status/date header does not match the seal', rel)

    def seal(self, record, stamp):
        source = self.root / relative(record)
        no_links(self.root, source)
        try:
            parts = source.relative_to(self.notes).parts
        except ValueError:
            raise ArchiveError('configuration', 'Record must be under notes-root', True)
        if (len(parts) != 3 or parts[0] != 'implemented' or parts[1] not in CLASSES
                or not re.fullmatch(r'\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*\.md', parts[-1])):
            raise ArchiveError('source-record', 'Seal only implemented/class/YYYY-MM-DD-topic.md Agent Notes')
        try:
            valid_date(parts[-1][:10])
        except ValueError:
            raise ArchiveError('source-record', 'Source filename date is invalid')
        no_links(self.root, self.notes)
        self.notes.mkdir(parents=True, exist_ok=True)
        no_links(self.root, self.lock)
        try:
            descriptor = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise ArchiveError('operation-lock', 'Operation lock exists; another operation or recovery may be pending')
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(str(os.getpid()))
        try:
            self.verify(own_lock=True)
            if self.errors():
                return
            if self.data['entries'] and (self.baseline is None or self.baseline['entries'] != self.data['entries']):
                self.add('baseline-required', 'Before another seal, commit the complete current manifest or supply its trusted snapshot')
                return
            raw = source.read_bytes()
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeError:
                raise ArchiveError('source-record', 'Source must be UTF-8')
            if not re.match(r'\A# Agent Note: [^\r\n]+\r?\n\r?\nStatus: implemented\r?\n', text) or re.search(r'^Archived:', text, re.M):
                raise ArchiveError('source-record', 'Source needs implemented Agent Note header and no existing Archived stamp')
            marker = re.search(rb'(?m)^Status: implemented(\r?\n)', raw)
            newline = marker[1]
            sealed = raw[:marker.end()] + b'Archived: ' + stamp.encode('ascii') + newline + raw[marker.end():]
            target = self.folder / parts[1] / parts[2]
            no_links(self.root, target)
            if target.exists():
                raise ArchiveError('destination-exists', 'Archive destination already exists')
            target.parent.mkdir(parents=True, exist_ok=True)
            updated = dict(self.data, entries=self.data['entries'] + [{
                'path': target.relative_to(self.folder).as_posix(), 'archived_on': stamp,
                'sha256': hashlib.sha256(sealed).hexdigest()}])
            manifest_bytes = (json.dumps(updated, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            self.commit_seal(source, raw, target, sealed, manifest_bytes)
            self.data = updated
            self.checked += 1
            self.add('sealed', 'Archived record and appended its content seal', target.relative_to(self.root).as_posix(), info=True)
        finally:
            self.lock.unlink()

    def commit_seal(self, source, original, target, sealed, manifest_bytes):
        """Roll back caught failures; a process crash is detected by verify/lock."""
        old_manifest = self.manifest.read_bytes() if self.manifest.exists() else None
        temporary = None
        target_written = source_removed = manifest_written = False
        try:
            # Recheck raw input after all validation, before the first data write.
            if source.read_bytes() != original:
                raise ArchiveError('source-changed', 'Source changed during validation')
            with target.open('xb') as stream:
                target_written = True
                stream.write(sealed)
            descriptor, name = tempfile.mkstemp(prefix='.manifest-', suffix='.tmp', dir=self.folder)
            temporary = Path(name)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(manifest_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.manifest)
            temporary = None
            manifest_written = True
            source.unlink()
            source_removed = True
        except Exception:
            if source_removed:
                source.write_bytes(original)
            if manifest_written:
                if old_manifest is None:
                    self.manifest.unlink()
                else:
                    self.manifest.write_bytes(old_manifest)
            if target_written:
                target.unlink()
            raise
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def report(self):
        baseline_count = len(self.baseline['entries']) if self.baseline is not None else 0
        return {'scope': {'root': str(self.root), 'notes_root': self.notes_relative,
                          'manifest': self.manifest.relative_to(self.root).as_posix(),
                          'records_checked': self.checked, 'protected_entries': baseline_count,
                          'history_verified': self.baseline is not None and not self.errors(),
                          'baseline': str(self.baseline_path) if self.baseline_path else ('git:HEAD' if self.baseline is not None else None),
                          'metadata_files_excluded': sorted(METADATA), 'semantic_validation': False},
                'findings': self.findings,
                'summary': {'errors': sum(x['severity'] == 'error' for x in self.findings),
                            'warnings': sum(x['severity'] == 'warning' for x in self.findings)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('verify', 'seal'))
    parser.add_argument('root')
    parser.add_argument('--record')
    parser.add_argument('--date')
    parser.add_argument('--notes-root', default='.agents/notes')
    parser.add_argument('--baseline-manifest')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    audit = None
    try:
        if not root.is_dir():
            raise ArchiveError('configuration', 'Project root must exist', True)
        audit = Archive(root, args.notes_root, args.baseline_manifest)
        if args.mode == 'seal':
            try:
                valid_date(args.date)
            except (ValueError, TypeError):
                raise ArchiveError('configuration', 'Seal requires a valid --date YYYY-MM-DD', True)
            if not args.record:
                raise ArchiveError('configuration', 'Seal requires --record', True)
            audit.seal(args.record, args.date)
        else:
            audit.verify()
    except ArchiveError as error:
        if audit is None:
            audit = Archive(root, '.agents/notes')
        audit.operational = error.operational
        audit.add(error.code, str(error))
    except (OSError, UnicodeError, subprocess.SubprocessError) as error:
        if audit is None:
            audit = Archive(root, '.agents/notes')
        audit.operational = True
        audit.add('operation-error', str(error))
    report = audit.report()
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        for item in report['findings']:
            print(f"{item['severity']}: [{item['code']}] {item['path']} {item['message']}")
        print(f"Checked {audit.checked} records, {report['summary']['errors']} errors; "
              f"trusted historical entries: {report['scope']['protected_entries']}. Semantics and links require separate review.")
    return 2 if audit.operational else (1 if audit.errors() else 0)


if __name__ == '__main__':
    raise SystemExit(main())
