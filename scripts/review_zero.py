#!/usr/bin/env python3
"""Review-Zero — the mechanical half of the Round-0 pre-push self-review.

Runs deterministic checks for the finding classes reviewers most often burn
rounds on. Every check is decidable: if a check needs judgment, it does not
belong here — it belongs in the adversarial half of Round 0, which is a human
or agent reading the full diff against .github/agent-review-guidelines.md and
cannot be scripted.

DESIGN RULES (read before adding a check)

  1. ADDED LINES ONLY. Every check runs on lines this diff introduces, so a
     pre-existing defect can never block an unrelated PR. Without this rule,
     adding a check retroactively fails every open PR that happens to sit near
     old code — and the team disables the check.

  2. NO JUDGMENT CALLS. A check that is right 80% of the time trains people to
     ignore the output. FAIL classes must be provably wrong, not suspicious.

  3. MINE YOUR OWN HISTORY. The checks below are a starting set. The valuable
     ones are the classes YOUR reviewers keep raising. Go read your merged PRs,
     find the repeated findings, and script the decidable ones.

FAIL classes (exit 1):
  citation        `path/to/file.py:123` in a changed doc points at a file absent
                  from the COMMITTED tree, or at a line past EOF. Docs cite line
                  numbers and those rot silently.
  md-link         relative markdown link in a changed doc resolves to nothing in
                  the committed tree.
  status-grammar  a `STATUS:` stamp that is not one of the allowed verdicts —
                  a typo makes the verdict unactionable and ungreppable.
  migration       a new migration whose `downgrade()` is `pass`-only, or whose
                  numeric prefix collides with an existing revision.

WARN classes (advisory, never fail):
  evidence        a `STATUS:` stamp on a line carrying no `evidence:` path.
  size            more than MAX_ADDED_LINES added lines — finding count scales
                  with diff size; consider decomposing.
  param-default   `.get("key", <default>)` inside a configured hot-path prefix.
                  Inert until you set HOT_PATH_PREFIXES.

Untracked-but-present local files do NOT count as existing: the push would omit
them, so a citation to one is broken for everyone else.

Escape hatch: any line containing `rz-ignore` is skipped by every check.

Usage:
  python scripts/review_zero.py                 # human report
  python scripts/review_zero.py --base <ref>    # explicit base ref
  python scripts/review_zero.py --ci            # GitHub annotations + exit code
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

# ---------------------------------------------------------------------------
# CONFIGURATION — edit for your repo
# ---------------------------------------------------------------------------

#: Verdicts allowed in a `STATUS:` stamp. See docs/reference/evidence-grammar.md
ALLOWED_STATUS = {"CANDIDATE", "VALIDATED", "REJECTED", "NOT_COMPUTED"}

#: Directory fragment identifying migration files (substring match on the path).
MIGRATIONS_DIR_MARKER = "alembic/versions"

#: Added hand-written lines above which the diff earns a size warning.
MAX_ADDED_LINES = 800

#: Path prefixes treated as consequential hot paths for the param-default check.
#: Empty = check inert. Set e.g. {"services/engine/", "services/worker/"}.
HOT_PATH_PREFIXES: set[str] = set()

#: Extensions treated as citable source files in `path:line` citations.
CITABLE_EXT = (
    "py", "ts", "tsx", "js", "jsx", "go", "rs", "java", "rb",
    "sql", "sh", "yml", "yaml", "toml", "json", "md",
)

# ---------------------------------------------------------------------------

CITATION_RE = re.compile(
    r"(?<![\w/.])((?:[\w.-]+/)+[\w.-]+\.(?:" + "|".join(CITABLE_EXT) + r"))(?::(\d+))?"
)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
STATUS_RE = re.compile(r"STATUS:\s*([A-Za-z_|/ ]+)")
GET_DEFAULT_RE = re.compile(r"\.get\(\s*[\"'][\w.]+[\"']\s*,\s*(?!\)).+?\)")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

IGNORE_TOKEN = "rz-ignore"


@dataclass(frozen=True)
class Finding:
    level: str  # "FAIL" | "WARN"
    cls: str
    path: str
    line: int
    message: str


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def git_ok(*args: str) -> bool:
    return subprocess.run(["git", *args], capture_output=True).returncode == 0


def resolve_base(explicit: str | None) -> str:
    if explicit:
        return explicit
    for ref in ("origin/HEAD", "origin/main", "origin/master", "main", "master"):
        if git_ok("rev-parse", "--verify", "--quiet", ref):
            return ref
    return "HEAD~1"


@lru_cache(maxsize=1)
def tree_paths(ref: str) -> frozenset[str]:
    """Every file path present in the committed tree at `ref`."""
    return frozenset(git("ls-tree", "-r", "--name-only", ref).splitlines())


@lru_cache(maxsize=1)
def tree_dirs(ref: str) -> frozenset[str]:
    dirs: set[str] = set()
    for p in tree_paths(ref):
        parts = p.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            dirs.add("/".join(parts[:i]))
    return frozenset(dirs)


@lru_cache(maxsize=None)
def blob_line_count(ref: str, path: str) -> int | None:
    try:
        return len(git("show", f"{ref}:{path}").splitlines())
    except subprocess.CalledProcessError:
        return None


def added_lines(base: str) -> dict[str, list[tuple[int, str]]]:
    """{path: [(lineno_in_new_file, text), ...]} for added lines only."""
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
        m = HUNK_RE.match(raw)
        if m:
            lineno = int(m.group(1))
            continue
        if raw.startswith("+") and path:
            out[path].append((lineno, raw[1:]))
            lineno += 1
    return {p: ls for p, ls in out.items() if ls}


# --- checks -----------------------------------------------------------------


def check_citations(base: str, added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
    found: list[Finding] = []
    paths = tree_paths("HEAD")
    for doc, lines in added.items():
        if not doc.endswith(".md"):
            continue
        for lineno, text in lines:
            for cited, num in CITATION_RE.findall(text):
                if cited not in paths:
                    # Only flag when it plausibly means THIS repo: the path must
                    # share a top-level directory with something we track.
                    top = cited.split("/", 1)[0]
                    if top in tree_dirs("HEAD"):
                        found.append(Finding(
                            "FAIL", "citation", doc, lineno,
                            f"cites `{cited}` — not in the committed tree",
                        ))
                    continue
                if num:
                    total = blob_line_count("HEAD", cited)
                    if total is not None and int(num) > total:
                        found.append(Finding(
                            "FAIL", "citation", doc, lineno,
                            f"cites `{cited}:{num}` but that file has {total} lines",
                        ))
    return found


def check_md_links(base: str, added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
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
                if resolved in paths or resolved in dirs:
                    continue
                found.append(Finding(
                    "FAIL", "md-link", doc, lineno,
                    f"link `{target}` resolves to `{resolved}` — not in the committed tree",
                ))
    return found


def check_status_grammar(added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
    found: list[Finding] = []
    for doc, lines in added.items():
        if not doc.endswith(".md"):
            continue
        for lineno, text in lines:
            m = STATUS_RE.search(text)
            if not m:
                continue
            raw = m.group(1).strip()
            # `A|B|C` is the grammar being *defined*, not a stamp being made.
            if "|" in raw:
                continue
            verdict = raw.split()[0] if raw.split() else ""
            if verdict and verdict not in ALLOWED_STATUS:
                found.append(Finding(
                    "FAIL", "status-grammar", doc, lineno,
                    f"`STATUS: {verdict}` is not one of {sorted(ALLOWED_STATUS)}",
                ))
            elif "evidence:" not in text:
                found.append(Finding(
                    "WARN", "evidence", doc, lineno,
                    "STATUS stamp carries no `evidence:` path",
                ))
    return found


def _downgrade_is_empty(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "downgrade":
            body = [n for n in node.body
                    if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                            and isinstance(n.value.value, str))]
            return all(isinstance(n, ast.Pass) for n in body)
    return False


def check_migrations(base: str, added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
    found: list[Finding] = []
    new_migrations = [p for p in added
                      if MIGRATIONS_DIR_MARKER in p and p.endswith(".py")]
    if not new_migrations:
        return found

    base_prefixes: dict[str, str] = {}
    for p in tree_paths(base):
        if MIGRATIONS_DIR_MARKER in p and p.endswith(".py"):
            m = re.match(r"(\d+)", posixpath.basename(p))
            if m:
                base_prefixes[m.group(1)] = p

    for path in new_migrations:
        if path in tree_paths(base):
            continue  # modified, not new
        try:
            src = git("show", f"HEAD:{path}")
        except subprocess.CalledProcessError:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        if _downgrade_is_empty(tree):
            found.append(Finding(
                "FAIL", "migration", path, 1,
                "`downgrade()` is pass-only — every migration needs a working "
                "downgrade (a deliberate `raise` with a message is accepted)",
            ))
        m = re.match(r"(\d+)", posixpath.basename(path))
        if m and m.group(1) in base_prefixes:
            found.append(Finding(
                "FAIL", "migration", path, 1,
                f"revision prefix {m.group(1)} collides with "
                f"`{base_prefixes[m.group(1)]}` on {base}",
            ))
    return found


def check_param_defaults(added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
    if not HOT_PATH_PREFIXES:
        return []
    found: list[Finding] = []
    for path, lines in added.items():
        if not any(path.startswith(p) for p in HOT_PATH_PREFIXES):
            continue
        for lineno, text in lines:
            if GET_DEFAULT_RE.search(text):
                found.append(Finding(
                    "WARN", "param-default", path, lineno,
                    "`.get(key, default)` on a hot path — a missing "
                    "consequential parameter must HALT, never silently fall back",
                ))
    return found


def check_size(added: dict[str, list[tuple[int, str]]]) -> list[Finding]:
    total = sum(len(v) for v in added.values())
    if total > MAX_ADDED_LINES:
        return [Finding(
            "WARN", "size", "<diff>", 0,
            f"{total} added lines (> {MAX_ADDED_LINES}) — finding count scales "
            f"with diff size; consider decomposing",
        )]
    return []


# --- driver -----------------------------------------------------------------


def strip_ignored(added: dict[str, list[tuple[int, str]]]) -> dict[str, list[tuple[int, str]]]:
    return {
        p: [(n, t) for n, t in lines if IGNORE_TOKEN not in t]
        for p, lines in added.items()
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", help="base ref (default: auto-detected default branch)")
    ap.add_argument("--ci", action="store_true", help="emit GitHub annotations")
    args = ap.parse_args()

    if not git_ok("rev-parse", "--git-dir"):
        print("review_zero: not a git repository", file=sys.stderr)
        return 2

    base = resolve_base(args.base)
    if not git_ok("rev-parse", "--verify", "--quiet", base):
        print(f"review_zero: base ref `{base}` not found", file=sys.stderr)
        return 2

    added = strip_ignored(added_lines(base))
    if not added:
        print(f"review-zero: no added lines vs {base} — nothing to check.")
        print("note: a deletion-only diff still carries the adversarial Round-0 duty.")
        return 0

    findings: list[Finding] = []
    findings += check_citations(base, added)
    findings += check_md_links(base, added)
    findings += check_status_grammar(added)
    findings += check_migrations(base, added)
    findings += check_param_defaults(added)
    findings += check_size(added)

    fails = [f for f in findings if f.level == "FAIL"]
    warns = [f for f in findings if f.level == "WARN"]

    if args.ci:
        for f in findings:
            kind = "error" if f.level == "FAIL" else "warning"
            loc = f"file={f.path},line={max(f.line, 1)}" if f.path != "<diff>" else ""
            print(f"::{kind} {loc},title=review-zero[{f.cls}]::{f.message}")
    else:
        n_files = len(added)
        n_lines = sum(len(v) for v in added.values())
        print(f"review-zero: base={base} · {n_files} file(s) · {n_lines} added line(s)\n")
        for f in findings:
            where = f"{f.path}:{f.line}" if f.path != "<diff>" else f.path
            print(f"  [{f.level}] {f.cls:<14} {where}\n           {f.message}")
        if not findings:
            print("  clean — no mechanical findings.")
        print(f"\n{len(fails)} FAIL · {len(warns)} WARN")
        print(
            "\nReminder: this is the MECHANICAL half of Round 0. The other half —\n"
            "reading the full diff as an adversary against\n"
            ".github/agent-review-guidelines.md — is still mandatory."
        )

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
