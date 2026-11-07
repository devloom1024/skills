"""Read-only documentation checks; Python 3.10+, standard library only."""
import argparse
import fnmatch
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from urllib.parse import unquote


EXCLUDED = {".git", ".cache", "node_modules", "vendor", ".venv", "venv",
            "__pycache__", "dist", "build", "target", "coverage", ".generated"}
# Agent Notes are owned and checked by the external Notes Skill.
EXCLUDED_PATHS = {".agents/notes"}
DEFAULTS = {"required_files": ["AGENTS.md", "docs/AGENTS.md"], "exclude": [], "budgets": {}}


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
    return config


def ignored(relative, config):
    parts = PurePosixPath(relative).parts
    ancestors = ["/".join(parts[:end]) for end in range(1, len(parts) + 1)]
    return any(part in EXCLUDED for part in parts) or any(path in EXCLUDED_PATHS for path in ancestors) or any(
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

    def run(self):
        for relative in self.config["required_files"]:
            path = self.root / relative
            if not path.is_file():
                self.add("required-file", "Required file is missing", relative)
        for relative in self.config["budgets"]:
            if not (self.root / relative).is_file():
                self.add("budget-file", "Budgeted file is missing", relative)
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
                          "default_excluded_paths": sorted(EXCLUDED_PATHS),
                          "budgeted_files": sorted(self.config["budgets"]), "notes_validation": False,
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
