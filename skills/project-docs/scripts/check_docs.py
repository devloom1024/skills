"""Read-only documentation checks; Python 3.10+, standard library only."""
import argparse
from datetime import date
import fnmatch
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from urllib.parse import unquote


EXCLUDED = {".git", ".cache", "node_modules", "vendor", ".venv", "venv",
            "__pycache__", "dist", "build", "target", "coverage", ".generated"}
CLASSES = {"feature", "bug-fix", "simplification", "architecture", "process", "testing"}
SECTIONS = {
    "problem": ("Problem", "问题"), "proposal": ("Proposal", "提案"),
    "decision": ("Decision", "决定"),
    "alternatives": ("Alternatives considered", "考虑过的替代方案"),
    "acceptance": ("Acceptance criteria", "验收标准"), "risks": ("Risks", "风险"),
    "consequences": ("Consequences", "后果"),
}
DEFAULTS = {"required_files": ["AGENTS.md", "docs/AGENTS.md"], "exclude": [],
            "note_roots": [{"path": ".agents/notes", "format": "agent-note"}], "budgets": {}}


def safe_relative(value):
    """Accept only nonempty project-relative paths without parent traversal."""
    return (isinstance(value, str) and bool(value.strip()) and value != "."
            and str(PurePosixPath(value)) == value and "\\" not in value
            and not PurePosixPath(value).is_absolute() and ".." not in PurePosixPath(value).parts
            and not re.match(r"^[A-Za-z]:", value))


def load_config(root, filename):
    config = dict(DEFAULTS)
    if filename:
        path = Path(filename)
        if not path.is_absolute():
            path = root / path
        supplied = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(supplied, dict) or set(supplied) - set(DEFAULTS):
            raise ValueError("configuration must be an object with known keys only")
        config.update(supplied)
    for key in ("required_files", "exclude"):
        if not isinstance(config[key], list) or not all(safe_relative(v) for v in config[key]):
            raise ValueError(f"{key} must contain project-relative paths or patterns")
    if not isinstance(config["note_roots"], list):
        raise ValueError("note_roots must be a list")
    for item in config["note_roots"]:
        if (not isinstance(item, dict) or set(item) != {"path", "format"}
                or not safe_relative(item["path"]) or item["format"] not in ("agent-note", "external")):
            raise ValueError("each note root needs a relative path and agent-note/external format")
    if not isinstance(config["budgets"], dict):
        raise ValueError("budgets must be an object")
    for path, item in config["budgets"].items():
        if (not safe_relative(path) or PurePosixPath(path).suffix.lower() not in (".md", ".markdown")
                or not isinstance(item, dict) or set(item) != {"max", "metric"}
                or type(item["max"]) is not int or item["max"] < 1
                or item["metric"] not in ("words", "mixed")):
            raise ValueError("budget needs a canonical relative Markdown file, positive integer max, and words/mixed metric")
    for path in config["required_files"] + list(config["budgets"]):
        if ignored(path, config):
            raise ValueError(f"required or budgeted file is excluded: {path}")
    roots = [PurePosixPath(item["path"]).parts for item in config["note_roots"]]
    for i, first in enumerate(roots):
        if any(first[:len(other)] == other or other[:len(first)] == first for other in roots[i + 1:]):
            raise ValueError("note roots must not overlap")
    return config


def ignored(relative, config):
    parts = PurePosixPath(relative).parts
    ancestors = ["/".join(parts[:end]) for end in range(1, len(parts) + 1)]
    return any(part in EXCLUDED for part in parts) or any(
        fnmatch.fnmatchcase(candidate, pattern) or candidate == pattern.rstrip("/**")
        for pattern in config["exclude"] for candidate in ancestors)


def directory_link(path):
    """Do not walk directory symlinks or Windows reparse points (including junctions)."""
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0)
                                            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def prose(source):
    """Mask code and HTML comments while preserving source line numbers."""
    source = re.sub(r"<!--[\s\S]*?-->", lambda m: "\n" * m.group().count("\n"), source)
    result, fence = [], None
    for line in source.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            result.append("")
        elif marker:
            fence = marker[1]
            result.append("")
        elif line.startswith("    ") or line.startswith("\t"):
            result.append("")
        else:
            result.append(re.sub(r"(`+).*?\1", "", line))
    return "\n".join(result)


def destination(raw):
    raw = raw.strip()
    if raw.startswith("<"):
        end = raw.find(">")
        return raw[1:end] if end >= 0 else raw[1:]
    return re.split(r"\s", raw, maxsplit=1)[0] if raw else ""


def links(text):
    """Yield (line, destination, unresolved-reference) for the documented subset."""
    definitions = {}
    for line in text.splitlines():
        match = re.match(r"^ {0,3}\[([^\]]+)\]:\s*(.*)$", line)
        if match:
            definitions[" ".join(match[1].split()).casefold()] = destination(match[2])
    for number, line in enumerate(text.splitlines(), 1):
        if re.match(r"^ {0,3}\[[^\]]+\]:", line):
            continue
        cursor = 0
        while True:
            match = re.search(r"!?\[([^\]\n]*)\](\(|\[([^\]]*)\])?", line[cursor:])
            if not match:
                break
            end = cursor + match.end()
            if match[2] == "(":
                start, depth, angle = end, 1, False
                while end < len(line) and depth:
                    char = line[end]
                    if char == "\\":
                        end += 2
                        continue
                    if char == "<":
                        angle = True
                    elif char == ">":
                        angle = False
                    elif not angle and char == "(":
                        depth += 1
                    elif not angle and char == ")":
                        depth -= 1
                    end += 1
                if depth == 0:
                    yield number, destination(line[start:end - 1]), None
            else:
                key = " ".join((match[3] or match[1]).split()).casefold()
                if key in definitions:
                    yield number, definitions[key], None
                elif match[2] is not None:
                    yield number, "", key
            cursor = end


def count_units(text, metric):
    cjk = r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]"
    if metric == "words":
        return len(text.split())
    return len(re.findall(cjk, text)) + len(re.findall(r"[^\W_]+(?:['’-][^\W_]+)*", re.sub(cjk, " ", text)))


class Audit:
    def __init__(self, root, config):
        self.root, self.config = root, config
        self.findings, self.count, self.operational = [], 0, False
        self.checked = set()

    def add(self, code, message, path="", line=0, severity="error"):
        self.findings.append(dict(severity=severity, code=code, path=path, line=line, message=message))

    def inside(self, path):
        try:
            return path.resolve().is_relative_to(self.root)
        except (OSError, RuntimeError):
            return False

    def note_location(self, relative):
        for item in self.config["note_roots"]:
            try:
                parts = PurePosixPath(relative).relative_to(item["path"]).parts
                if parts and parts[-1] in ("README.md", "AGENTS.md", "CLAUDE.md"):
                    return None
                if parts:
                    return item, parts
            except ValueError:
                pass
        return None

    def note(self, relative, text, location):
        item, parts = location
        if item["format"] == "external":
            return False
        archived = parts[0] == "archived"
        valid_path = len(parts) == 3 and parts[0] in ("proposed", "implemented", "rejected", "archived") and parts[1] in CLASSES
        filename = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-[a-z0-9][a-z0-9-]*\.md", parts[-1])
        try:
            valid_path = valid_path and filename is not None
            if filename:
                date.fromisoformat(filename[1])
        except ValueError:
            valid_path = False
        if not valid_path:
            self.add("note-path", "Use lifecycle/class/YYYY-MM-DD-topic.md with a real date and supported class", relative)
        status = re.search(r"^Status:\s*(.+)$", text, re.M)
        expected = "implemented" if archived else parts[0]
        actual = status[1].strip() if status else ""
        if (expected == "rejected" and not re.fullmatch(r"rejected\s+[—-]\s+\S.*", actual)) or (expected != "rejected" and actual != expected):
            self.add("note-status", f"Status must agree with {expected}; rejection needs a reason", relative)
        if not re.match(r"\A# Agent Note: .+\n\nStatus: .+\n", text):
            self.add("note-header", "Start with # Agent Note: title, blank line, and Status: value", relative)
        if archived:
            stamp = re.search(r"^Archived: (\d{4}-\d{2}-\d{2})$", text, re.M)
            try:
                date.fromisoformat(stamp[1] if stamp else "")
            except ValueError:
                self.add("archive-date", "Archive needs a valid Archived: YYYY-MM-DD line", relative)
            return True
        headings = list(re.finditer(r"^## (.+)$", prose(text), re.M))
        bodies = {m[1].strip(): prose(text)[m.end():headings[i + 1].start() if i + 1 < len(headings) else None].strip()
                  for i, m in enumerate(headings)}
        required = ["problem", "alternatives"] + ({"proposed": ["proposal", "acceptance", "risks"],
                    "implemented": ["decision", "consequences"], "rejected": ["proposal"]}.get(expected, []))
        for key in required:
            name = next((name for name in SECTIONS[key] if name in bodies), None)
            if name is None:
                self.add("note-sections", f"Missing section: {SECTIONS[key][0]}", relative)
            elif not bodies[name]:
                self.add("note-content", f"Empty section: {name}", relative)
        if expected == "implemented" and any(name in bodies for name in
                ("Proposal", "提案", "Plan", "计划", "Migration plan", "迁移计划", "Acceptance criteria", "验收标准", "Risks", "风险")):
            self.add("note-sections", "Implemented notes describe current decisions; remove proposal-era headings", relative)
        return False

    def check_file(self, path):
        relative = path.relative_to(self.root).as_posix()
        if not self.inside(path):
            self.add("outside-root", "File or symlink resolves outside the project", relative)
            return
        try:
            source = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            self.operational = True
            self.add("read-error", str(error), relative)
            return
        self.count += 1
        self.checked.add(relative)
        budget = self.config["budgets"].get(relative)
        if budget:
            count = count_units(source, budget["metric"])
            if count > budget["max"]:
                self.add("budget", f"{count} {budget['metric']} units exceeds {budget['max']}; relocate, condense, or justify a new ceiling", relative)
        location = self.note_location(relative)
        if location and self.note(relative, source, location):
            return
        text = prose(source)
        for number, line in enumerate(text.splitlines(), 1):
            if re.search(r"\{\{[^{}\n]+\}\}|\b(?:TODO|TBD)\b|待填写", line):
                self.add("placeholder", "Resolve the draft marker or move an actual deferred task to its owner", relative, number)
        for line, target, unresolved in links(text):
            if unresolved:
                self.add("reference-link", f"Undefined reference: {unresolved}", relative, line)
                continue
            if not target or target.startswith(("#", "//")) or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            local = unquote(re.split(r"[?#]", target, maxsplit=1)[0])
            local = re.sub(r"\\([() ])", r"\1", local)
            resolved = self.root / local.lstrip("/") if local.startswith("/") else path.parent / local
            if not self.inside(resolved):
                self.add("outside-root", f"Link escapes project: {target}", relative, line)
            elif not resolved.exists():
                self.add("local-link", f"Missing local target: {target}", relative, line)
            else:
                note = self.note_location(resolved.resolve().relative_to(self.root).as_posix())
                if note and note[0]["format"] == "agent-note" and note[1][0] == "archived":
                    self.add("archive-reference", "Confirm this cites history, not current authority", relative, line, "warning")

    def run(self):
        for relative in self.config["required_files"]:
            path = self.root / relative
            if not path.is_file():
                self.add("required-file", "Required file is missing", relative)
        for relative in self.config["budgets"]:
            if not (self.root / relative).is_file():
                self.add("budget-file", "Budgeted file is missing", relative)
        for item in self.config["note_roots"]:
            if item["format"] == "external":
                self.add("external-notes", "Existing decision format is preserved; review its states and content manually", item["path"], severity="warning")
        def walk_error(error):
            self.operational = True
            self.add("read-error", str(error))
        for folder, directories, files in os.walk(self.root, followlinks=False, onerror=walk_error):
            base = Path(folder)
            kept = []
            for directory in sorted(directories):
                path = base / directory
                if ignored(path.relative_to(self.root).as_posix(), self.config):
                    continue
                try:
                    if not directory_link(path):
                        kept.append(directory)
                except OSError as error:
                    walk_error(error)
            directories[:] = kept
            for name in sorted(files):
                path = base / name
                if path.suffix.lower() in (".md", ".markdown") and not ignored(path.relative_to(self.root).as_posix(), self.config):
                    self.check_file(path)
        for relative in sorted(set(self.config["required_files"]) | set(self.config["budgets"])):
            if relative not in self.checked and (self.root / relative).is_file():
                self.add("unscanned-file", "Explicitly required/budgeted file was not checked; inspect file type and directory links", relative)
        if self.count == 0:
            self.add("empty-corpus", "No readable Markdown files were checked")
        return self.report(), 2 if self.operational else (1 if any(f["severity"] == "error" for f in self.findings) else 0)

    def report(self):
        return {"scope": {"root": str(self.root), "files_checked": self.count,
                          "required_files": self.config["required_files"], "exclude": self.config["exclude"],
                          "default_excluded_directories": sorted(EXCLUDED),
                          "note_roots": self.config["note_roots"], "budgeted_files": sorted(self.config["budgets"]),
                          "semantic_validation": False, "anchor_validation": False, "external_links": False},
                "findings": self.findings,
                "summary": {"errors": sum(f["severity"] == "error" for f in self.findings),
                            "warnings": sum(f["severity"] == "warning" for f in self.findings)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--config")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        if not root.is_dir():
            raise ValueError("project root must be an existing directory")
        config = load_config(root, args.config)
    except (OSError, UnicodeError, ValueError) as error:
        audit = Audit(root, DEFAULTS)
        audit.add("configuration", str(error))
        report, code = audit.report(), 2
    else:
        report, code = Audit(root, config).run()
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        for finding in report["findings"]:
            print(f"{finding['severity']}: {finding['path']}:{finding['line']} [{finding['code']}] {finding['message']}")
        print(f"Checked {report['scope']['files_checked']} Markdown files; "
              f"{report['summary']['errors']} errors, {report['summary']['warnings']} warnings. "
              "Semantics, anchors, external URLs, and executed commands require separate verification.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
