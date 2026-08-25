#!/usr/bin/env python3
"""Review-Zero — deterministic pre-push checks for agent-authored changes.

Local semantic checks apply to added lines so pre-existing debt cannot block an
unrelated PR. Referential-integrity checks are different: if this PR deletes,
renames, or shrinks a target, existing inbound references to that impacted
surface are checked across the repository. This preserves blast-radius scoping
without allowing deletion-only changes to silently break trusted docs.
"""

from __future__ import annotations

import argparse
import ast
import posixpath
import re
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache

ALLOWED_STATUS = {"CANDIDATE", "VALIDATED", "REJECTED", "NOT_COMPUTED"}
MIGRATIONS_DIR_MARKER = "alembic/versions"
MAX_ADDED_LINES = 800
HOT_PATH_PREFIXES: set[str] = set()
CITABLE_EXT = (
    "py", "ts", "tsx", "js", "jsx", "go", "rs", "java", "rb",
    "sql", "sh", "yml", "yaml", "toml", "json", "md",
)

CITATION_RE = re.compile(
    r"(?<![\w/.])((?:[\w.-]+/)+[\w.-]+\.(?:" + "|".join(CITABLE_EXT) + r"))(?::(\d+))?"
)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
STATUS_RE = re.compile(r"STATUS:\s*([A-Za-z_|/ ]+)")
GET_DEFAULT_RE = re.compile(r"\.get\(\s*[\"'][\w.]+[\"']\s*,\s*(?!\)).+?\)")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
FULL_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
IGNORE_TOKEN = "rz-ignore"


@dataclass(frozen=True)
class Finding:
    level: str
    cls: str
    path: str
    line: int
    message: str


@dataclass(frozen=True)
class Impact:
    deleted: frozenset[str]
    shrunk: frozenset[str]
    deleted_dirs: frozenset[str]
    restructured: frozenset[str]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def git_ok(*args: str) -> bool:
    return subprocess.run(["git", *args], capture_output=True).returncode == 0


def resolve_base(explicit: str | None) -> str:
    if explicit:
        return explicit
    for ref in ("origin/HEAD", "origin/main", "origin/master", "main", "master"):
        if git_ok("rev-parse", "--verify", "--quiet", ref):
            return ref
    return "HEAD~1"


@lru_cache(maxsize=None)
def tree_paths(ref: str) -> frozenset[str]:
    return frozenset(git("ls-tree", "-r", "--name-only", ref).splitlines())


@lru_cache(maxsize=None)
def tree_dirs(ref: str) -> frozenset[str]:
    dirs: set[str] = set()
    for path in tree_paths(ref):
        parts = path.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            dirs.add("/".join(parts[:i]))
    return frozenset(dirs)


@lru_cache(maxsize=None)
def blob_line_count(ref: str, path: str) -> int | None:
    try:
        return len(git("show", f"{ref}:{path}").splitlines())
    except subprocess.CalledProcessError:
        return None


@lru_cache(maxsize=None)
def file_hunks(base: str, path: str) -> tuple[tuple[int, int, int, int], ...]:
    """(old_start, old_count, new_start, new_count) for each diff hunk on path."""
    try:
        diff = git("diff", "--unified=0", "--no-color", f"{base}...HEAD", "--", path)
    except subprocess.CalledProcessError:
        return ()
    hunks: list[tuple[int, int, int, int]] = []
    for raw in diff.splitlines():
        match = FULL_HUNK_RE.match(raw)
        if not match:
            continue
        old_start = int(match.group(1))
        old_count = int(match.group(2)) if match.group(2) is not None else 1
        new_start = int(match.group(3))
        new_count = int(match.group(4)) if match.group(4) is not None else 1
        hunks.append((old_start, old_count, new_start, new_count))
    return tuple(hunks)


def citation_line_shifted(base: str, path: str, num: int) -> bool:
    """True if a net line-count change at or before `num` could have moved
    what that line number now points at, even though `num` is still within
    the new EOF — e.g. deleting an earlier line shifts every later line up
    by one, so an unchanged citation number now names different content."""
    for _old_start, old_count, new_start, new_count in file_hunks(base, path):
        if old_count == new_count:
            continue
        # A pure deletion (new_count == 0) anchors new_start on the new-file
        # line *preceding* the removed content — e.g. deleting old line 4
        # from a file produces `@@ -4 +3,0 @@`, meaning the cut sits strictly
        # after line 3, not at-or-before it. Anything up to and including
        # new_start is untouched; only lines after it can have shifted.
        # A hunk that adds content (new_count > 0) instead spans real new
        # lines starting at new_start, so that boundary is inclusive there.
        boundary = new_start if new_count > 0 else new_start + 1
        if num >= boundary:
            return True
    return False


def added_lines(base: str) -> dict[str, list[tuple[int, str]]]:
    diff = git("diff", "--unified=0", "--no-color", f"{base}...HEAD")
    out: dict[str, list[tuple[int, str]]] = {}
    path: str | None = None
    lineno = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            path = raw[6:]
            out.setdefault(path, [])
            continue
        if raw.startswith("+++ ") or raw.startswith("--- "):
            continue
        match = HUNK_RE.match(raw)
        if match:
            lineno = int(match.group(1))
            continue
        if raw.startswith("+") and path:
            out[path].append((lineno, raw[1:]))
            lineno += 1
    return {p: rows for p, rows in out.items() if rows}


def impact(base: str) -> Impact:
    deleted: set[str] = set()
    candidates: set[str] = set()
    raw = git("diff", "--name-status", "-M", f"{base}...HEAD")
    for line in raw.splitlines():
        fields = line.split("\t")
        status = fields[0]
        if status.startswith("R") and len(fields) >= 3:
            deleted.add(fields[1])
            candidates.add(fields[2])
        elif status == "D" and len(fields) >= 2:
            deleted.add(fields[1])
        elif status in {"M", "A"} and len(fields) >= 2:
            candidates.add(fields[1])

    shrunk: set[str] = set()
    restructured: set[str] = set()
    for path in candidates:
        if path not in tree_paths(base) or path not in tree_paths("HEAD"):
            continue
        before = blob_line_count(base, path)
        after = blob_line_count("HEAD", path)
        if before is not None and after is not None and after < before:
            shrunk.add(path)
        # A file can be net the same size or even grow while still moving
        # existing content around — a deleted line and an unrelated added
        # line elsewhere both show up as hunks with unequal old/new counts.
        # `shrunk` alone misses that: gate the citation-shift check on
        # this broader set instead of net file size.
        if any(old_count != new_count for _os, old_count, _ns, new_count in file_hunks(base, path)):
            restructured.add(path)

    # A directory link (e.g. `[docs](docs/)`) is invalidated when the last
    # file that kept it in the tree is deleted, even though no path in
    # `deleted` names the directory itself — derive that from the tree diff.
    deleted_dirs = tree_dirs(base) - tree_dirs("HEAD")
    return Impact(frozenset(deleted), frozenset(shrunk), frozenset(deleted_dirs), frozenset(restructured))


def markdown_lines(ref: str, path: str) -> list[str]:
    try:
        return git("show", f"{ref}:{path}").splitlines()
    except subprocess.CalledProcessError:
        return []


def check_added_citations(added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
    found: list[Finding] = []
    paths = tree_paths("HEAD")
    dirs = tree_dirs("HEAD")
    for doc, lines in added.items():
        if not doc.endswith(".md"):
            continue
        for lineno, text in lines:
            for cited, num in CITATION_RE.findall(text):
                if cited not in paths:
                    if cited.split("/", 1)[0] in dirs:
                        found.append(Finding("FAIL", "citation", doc, lineno,
                                             f"cites `{cited}` — not in committed HEAD"))
                    continue
                if num:
                    total = blob_line_count("HEAD", cited)
                    if total is not None and int(num) > total:
                        found.append(Finding("FAIL", "citation", doc, lineno,
                                             f"cites `{cited}:{num}` but file has {total} lines"))
    return found


def check_added_md_links(added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
    found: list[Finding] = []
    paths, dirs = tree_paths("HEAD"), tree_dirs("HEAD")
    for doc, lines in added.items():
        if not doc.endswith(".md"):
            continue
        doc_dir = posixpath.dirname(doc)
        for lineno, text in lines:
            for target in MD_LINK_RE.findall(text):
                if re.match(r"^(https?:|mailto:|#|<)", target):
                    continue
                clean = target.split("#", 1)[0].strip()
                if not clean:
                    continue
                resolved = posixpath.normpath(posixpath.join(doc_dir, clean))
                if resolved not in paths and resolved not in dirs:
                    found.append(Finding("FAIL", "md-link", doc, lineno,
                                         f"link `{target}` resolves to missing `{resolved}`"))
    return found


def check_impacted_references(base: str, change: Impact) -> list[Finding]:
    """Check only inbound references whose target this PR can invalidate."""
    if not change.deleted and not change.shrunk and not change.deleted_dirs and not change.restructured:
        return []
    found: list[Finding] = []
    current_paths = tree_paths("HEAD")
    for doc in sorted(p for p in current_paths if p.endswith(".md")):
        doc_dir = posixpath.dirname(doc)
        base_text = "\n".join(markdown_lines(base, doc))
        # Scope the "is this reference actually inherited from base?" check
        # to the reference itself, not the line it sits on — a line can be
        # edited for an unrelated reason while carrying over an untouched
        # citation/link verbatim, and a line-level skip would hide that
        # citation from impact scanning entirely (check_added_* only catches
        # it if the target's *containing directory* also still exists).
        base_targets = {
            posixpath.normpath(posixpath.join(doc_dir, clean))
            for target in MD_LINK_RE.findall(base_text)
            if not re.match(r"^(https?:|mailto:|#|<)", target)
            for clean in [target.split("#", 1)[0].strip()]
            if clean
        }
        base_citations = set(CITATION_RE.findall(base_text))
        for lineno, text in enumerate(markdown_lines("HEAD", doc), 1):
            if IGNORE_TOKEN in text:
                continue
            for target in MD_LINK_RE.findall(text):
                if re.match(r"^(https?:|mailto:|#|<)", target):
                    continue
                clean = target.split("#", 1)[0].strip()
                if not clean:
                    continue
                resolved = posixpath.normpath(posixpath.join(doc_dir, clean))
                if resolved not in base_targets:
                    # This exact link target isn't inherited from base — it's
                    # new or edited content already validated against current
                    # HEAD by check_added_md_links.
                    continue
                if resolved in change.deleted or resolved in change.deleted_dirs:
                    found.append(Finding(
                        "FAIL", "md-link-impact", doc, lineno,
                        f"existing link `{target}` targets `{resolved}`, deleted/renamed by this PR",
                    ))
            for cited, num in CITATION_RE.findall(text):
                if (cited, num) not in base_citations:
                    # Same reasoning as links: an untouched citation carries
                    # the exact same (path, line-number) pair over from base.
                    # A changed one — including a repair the PR made to a
                    # citation shifted by its own earlier edit — won't match
                    # and is already covered by check_added_citations.
                    continue
                if cited in change.deleted:
                    found.append(Finding(
                        "FAIL", "citation-impact", doc, lineno,
                        f"existing citation targets `{cited}`, deleted/renamed by this PR",
                    ))
                elif (cited in change.shrunk or cited in change.restructured) and num:
                    total = blob_line_count("HEAD", cited)
                    n = int(num)
                    if cited in change.shrunk and total is not None and n > total:
                        found.append(Finding(
                            "FAIL", "citation-impact", doc, lineno,
                            f"existing citation `{cited}:{num}` exceeds new EOF ({total}) after shrink",
                        ))
                    elif citation_line_shifted(base, cited, n):
                        found.append(Finding(
                            "FAIL", "citation-impact", doc, lineno,
                            f"existing citation `{cited}:{num}` may point at shifted content — an "
                            "earlier change in this PR moved what that line number now names",
                        ))
    return found


def check_status_grammar(added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
    found: list[Finding] = []
    for doc, lines in added.items():
        if not doc.endswith(".md"):
            continue
        for lineno, text in lines:
            match = STATUS_RE.search(text)
            if not match:
                continue
            raw = match.group(1).strip()
            if "|" in raw:
                continue
            verdict = raw.split()[0] if raw.split() else ""
            if verdict and verdict not in ALLOWED_STATUS:
                found.append(Finding("FAIL", "status-grammar", doc, lineno,
                                     f"`STATUS: {verdict}` not in {sorted(ALLOWED_STATUS)}"))
            elif "evidence:" not in text:
                found.append(Finding("WARN", "evidence", doc, lineno,
                                     "STATUS stamp carries no `evidence:` path"))
    return found


def downgrade_state(tree: ast.Module) -> str:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "downgrade":
            body = [n for n in node.body if not (
                isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)
            )]
            return "empty" if not body or all(isinstance(n, ast.Pass) for n in body) else "ok"
    return "missing"


def check_migrations(base: str, added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
    found: list[Finding] = []
    new_migrations = [p for p in added if MIGRATIONS_DIR_MARKER in p and p.endswith(".py")]
    prefixes: dict[str, str] = {}
    for path in tree_paths(base):
        if MIGRATIONS_DIR_MARKER in path and path.endswith(".py"):
            match = re.match(r"(\d+)", posixpath.basename(path))
            if match:
                prefixes[match.group(1)] = path

    for path in new_migrations:
        if path in tree_paths(base):
            continue
        try:
            src = git("show", f"HEAD:{path}")
            tree = ast.parse(src)
        except (subprocess.CalledProcessError, SyntaxError):
            continue
        state = downgrade_state(tree)
        if state != "ok":
            found.append(Finding(
                "FAIL", "migration", path, 1,
                f"`downgrade()` is {state}; every new migration needs an explicit working downgrade",
            ))
        match = re.match(r"(\d+)", posixpath.basename(path))
        if match and match.group(1) in prefixes:
            found.append(Finding(
                "FAIL", "migration", path, 1,
                f"revision prefix {match.group(1)} collides with `{prefixes[match.group(1)]}` on {base}",
            ))
    return found


def check_param_defaults(added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
    if not HOT_PATH_PREFIXES:
        return []
    found: list[Finding] = []
    for path, lines in added.items():
        if not any(path.startswith(prefix) for prefix in HOT_PATH_PREFIXES):
            continue
        for lineno, text in lines:
            if GET_DEFAULT_RE.search(text):
                found.append(Finding(
                    "WARN", "param-default", path, lineno,
                    "`.get(key, default)` on a configured hot path can silently disarm required config",
                ))
    return found


def check_size(added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
    total = sum(len(rows) for rows in added.values())
    if total <= MAX_ADDED_LINES:
        return []
    return [Finding("WARN", "size", "<diff>", 0,
                    f"{total} added lines (> {MAX_ADDED_LINES}); consider decomposing")]


def strip_ignored(added: dict[str, list[tuple[int, str]]]) -> dict[str, list[tuple[int, str]]]:
    return {p: [(n, t) for n, t in rows if IGNORE_TOKEN not in t] for p, rows in added.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="base ref (default: auto-detected default branch)")
    parser.add_argument("--ci", action="store_true", help="emit GitHub annotations")
    args = parser.parse_args()

    if not git_ok("rev-parse", "--git-dir"):
        print("review_zero: not a git repository", file=sys.stderr)
        return 2
    base = resolve_base(args.base)
    if not git_ok("rev-parse", "--verify", "--quiet", base):
        print(f"review_zero: base ref `{base}` not found", file=sys.stderr)
        return 2

    added = strip_ignored(added_lines(base))
    change = impact(base)
    findings: list[Finding] = []
    findings += check_added_citations(added)
    findings += check_added_md_links(added)
    findings += check_impacted_references(base, change)
    findings += check_status_grammar(added)
    findings += check_migrations(base, added)
    findings += check_param_defaults(added)
    findings += check_size(added)

    fails = [f for f in findings if f.level == "FAIL"]
    warns = [f for f in findings if f.level == "WARN"]
    if args.ci:
        for finding in findings:
            kind = "error" if finding.level == "FAIL" else "warning"
            loc = f"file={finding.path},line={max(finding.line, 1)}" if finding.path != "<diff>" else ""
            print(f"::{kind} {loc},title=review-zero[{finding.cls}]::{finding.message}")
    else:
        n_lines = sum(len(rows) for rows in added.values())
        print(
            f"review-zero: base={base} · {len(added)} file(s) with added lines · {n_lines} added line(s)"
        )
        if change.deleted or change.shrunk or change.deleted_dirs or change.restructured:
            print(
                f"impact scan: {len(change.deleted)} deleted/renamed · {len(change.shrunk)} shrunk target(s) · "
                f"{len(change.deleted_dirs)} deleted dir(s) · {len(change.restructured)} restructured target(s)"
            )
        for finding in findings:
            where = f"{finding.path}:{finding.line}" if finding.path != "<diff>" else finding.path
            print(f"  [{finding.level}] {finding.cls:<18} {where}\n           {finding.message}")
        if not findings:
            print("  clean — no mechanical findings")
        print(f"\n{len(fails)} FAIL · {len(warns)} WARN")
        print("\nReminder: the adversarial full-diff review is still mandatory.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
