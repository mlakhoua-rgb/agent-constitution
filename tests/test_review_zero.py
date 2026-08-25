from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "review_zero.py"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


class ReviewZeroImpactTests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="review-zero-test-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        run("git", "init", "-q", cwd=root)
        run("git", "config", "user.email", "test@example.com", cwd=root)
        run("git", "config", "user.name", "Test", cwd=root)
        return root

    def commit(self, root: Path, message: str) -> str:
        run("git", "add", "-A", cwd=root)
        result = run("git", "commit", "-q", "-m", message, cwd=root)
        self.assertEqual(result.returncode, 0, result.stderr)
        sha = run("git", "rev-parse", "HEAD", cwd=root)
        self.assertEqual(sha.returncode, 0, sha.stderr)
        return sha.stdout.strip()

    def review(self, root: Path, base: str) -> subprocess.CompletedProcess[str]:
        return run(sys.executable, str(SCRIPT), "--base", base, cwd=root)

    def test_deletion_breaks_existing_markdown_link(self) -> None:
        root = self.make_repo()
        (root / "docs").mkdir()
        (root / "docs" / "a.md").write_text("[target](b.md)\n", encoding="utf-8")
        (root / "docs" / "b.md").write_text("# target\n", encoding="utf-8")
        base = self.commit(root, "base")
        (root / "docs" / "b.md").unlink()
        self.commit(root, "delete target")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("md-link-impact", result.stdout)

    def test_shrunk_source_invalidates_existing_line_citation(self) -> None:
        root = self.make_repo()
        (root / "docs").mkdir()
        (root / "src").mkdir()
        (root / "docs" / "a.md").write_text("See src/foo.py:4.\n", encoding="utf-8")
        (root / "src" / "foo.py").write_text("1\n2\n3\n4\n5\n", encoding="utf-8")
        base = self.commit(root, "base")
        (root / "src" / "foo.py").write_text("1\n2\n", encoding="utf-8")
        self.commit(root, "shrink target")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("citation-impact", result.stdout)

    def test_shrunk_source_with_earlier_deletion_shifts_existing_citation(self) -> None:
        root = self.make_repo()
        (root / "docs").mkdir()
        (root / "src").mkdir()
        (root / "docs" / "a.md").write_text("See src/foo.py:3.\n", encoding="utf-8")
        (root / "src" / "foo.py").write_text("one\ntwo\nthree\nfour\nfive\n", encoding="utf-8")
        base = self.commit(root, "base")
        # Deleting the first line shifts every later line up by one: line 3
        # ("three") is now line 2, and line 3 is what used to be line 4
        # ("four"). The citation number is still within the new EOF, so the
        # bounds-only check alone would call this clean.
        (root / "src" / "foo.py").write_text("two\nthree\nfour\nfive\n", encoding="utf-8")
        self.commit(root, "delete first line")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("citation-impact", result.stdout)

    def test_unrelated_edit_on_same_line_does_not_hide_a_broken_citation(self) -> None:
        root = self.make_repo()
        (root / "docs").mkdir()
        (root / "src").mkdir()
        (root / "docs" / "a.md").write_text("Some prose. See src/foo.py:1.\n", encoding="utf-8")
        (root / "src" / "foo.py").write_text("one\n", encoding="utf-8")
        base = self.commit(root, "base")
        # Delete the only file under src/ (removing the directory from the
        # HEAD tree entirely) and, in the same commit, edit the doc line for
        # an unrelated reason while leaving the citation itself untouched.
        # A line-level skip would hide this: check_added_citations also
        # misses it because `src` no longer exists as a directory either.
        (root / "src" / "foo.py").unlink()
        (root / "docs" / "a.md").write_text("Some fixed prose. See src/foo.py:1.\n", encoding="utf-8")
        self.commit(root, "delete src/foo.py and unrelated prose edit")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("citation-impact", result.stdout)

    def test_renaming_a_doc_to_a_different_directory_breaks_its_own_relative_link(self) -> None:
        root = self.make_repo()
        (root / "docs").mkdir()
        (root / "docs" / "a.md").write_text("[target](b.md)\n", encoding="utf-8")
        (root / "docs" / "b.md").write_text("# target\n", encoding="utf-8")
        base = self.commit(root, "base")
        # Move a.md to a different directory with its content — and the
        # relative link text — completely untouched. b.md itself never
        # moves, so the link now resolves to a path that never existed.
        (root / "guides").mkdir()
        (root / "docs" / "a.md").rename(root / "guides" / "a.md")
        self.commit(root, "move docs/a.md to guides/a.md")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("md-link-impact", result.stdout)

    def test_repaired_citation_matching_a_different_deleted_citations_value_is_not_reflagged(self) -> None:
        root = self.make_repo()
        (root / "docs").mkdir()
        (root / "src").mkdir()
        (root / "docs" / "a.md").write_text(
            "See src/foo.py:2.\n"
            "\n"
            "Unrelated paragraph.\n"
            "\n"
            "See src/foo.py:3.\n",
            encoding="utf-8",
        )
        (root / "src" / "foo.py").write_text("one\ntwo\nthree\nfour\nfive\n", encoding="utf-8")
        base = self.commit(root, "base")
        # Delete the first citation's line entirely, delete the source
        # file's first line (shifting "three" from line 3 to line 2), and
        # repair the second citation to point at the shifted "three" —
        # which happens to equal the *first* (now-deleted) citation's old
        # value. A document-wide set of base citations would misclassify
        # this repair as "inherited" from the unrelated first citation and
        # fail it as shifted; the fix must scope the comparison to the
        # specific hunk each citation's edit belongs to.
        (root / "src" / "foo.py").write_text("two\nthree\nfour\nfive\n", encoding="utf-8")
        (root / "docs" / "a.md").write_text(
            "\n"
            "Unrelated paragraph.\n"
            "\n"
            "See src/foo.py:2.\n",
            encoding="utf-8",
        )
        self.commit(root, "delete first citation, shift source, repair second citation")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_citation_fixed_in_same_pr_is_not_reflagged_as_shifted(self) -> None:
        root = self.make_repo()
        (root / "docs").mkdir()
        (root / "src").mkdir()
        (root / "docs" / "a.md").write_text("See src/foo.py:3.\n", encoding="utf-8")
        (root / "src" / "foo.py").write_text("one\ntwo\nthree\nfour\nfive\n", encoding="utf-8")
        base = self.commit(root, "base")
        # Delete the first line (shifting "three" from line 3 to line 2)
        # and, in the same commit, update the citation to point at the new
        # correct line. The impact scan must not re-flag a citation the PR
        # itself just repaired — it's already validated against current
        # HEAD by the added-citation check.
        (root / "src" / "foo.py").write_text("two\nthree\nfour\nfive\n", encoding="utf-8")
        (root / "docs" / "a.md").write_text("See src/foo.py:2.\n", encoding="utf-8")
        self.commit(root, "delete first line and fix the citation")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_deletion_strictly_after_cited_line_does_not_false_positive(self) -> None:
        root = self.make_repo()
        (root / "docs").mkdir()
        (root / "src").mkdir()
        (root / "docs" / "a.md").write_text("See src/foo.py:3.\n", encoding="utf-8")
        (root / "src" / "foo.py").write_text("one\ntwo\nthree\nfour\nfive\n", encoding="utf-8")
        base = self.commit(root, "base")
        # Deleting the line *after* the cited line ("four") does not move
        # what line 3 ("three") names. Git's zero-context hunk for a pure
        # deletion anchors `new_start` on the line *preceding* the cut
        # (`@@ -4,1 +3,0 @@`), which an inclusive `new_start <= num` check
        # would misread as "at or before line 3" and false-positive on.
        (root / "src" / "foo.py").write_text("one\ntwo\nthree\nfive\n", encoding="utf-8")
        self.commit(root, "delete the line after the citation")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_restructured_non_shrinking_file_shifts_existing_citation(self) -> None:
        root = self.make_repo()
        (root / "docs").mkdir()
        (root / "src").mkdir()
        (root / "docs" / "a.md").write_text("See src/foo.py:3.\n", encoding="utf-8")
        (root / "src" / "foo.py").write_text("one\ntwo\nthree\nfour\nfive\n", encoding="utf-8")
        base = self.commit(root, "base")
        # Delete the first line and add a new line at the end: net line
        # count is unchanged (the file never enters `shrunk`), but line 3
        # now names what used to be line 4 ("four") instead of "three".
        (root / "src" / "foo.py").write_text("two\nthree\nfour\nfive\nsix\n", encoding="utf-8")
        self.commit(root, "delete first line, add a line at the end")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("citation-impact", result.stdout)

    def test_deleting_last_file_in_directory_breaks_existing_directory_link(self) -> None:
        root = self.make_repo()
        (root / "docs").mkdir()
        (root / "docs" / "guide").mkdir()
        (root / "docs" / "a.md").write_text("[guide](guide/)\n", encoding="utf-8")
        (root / "docs" / "guide" / "only.md").write_text("# only\n", encoding="utf-8")
        base = self.commit(root, "base")
        (root / "docs" / "guide" / "only.md").unlink()
        self.commit(root, "delete last file in guide/")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("md-link-impact", result.stdout)

    def test_unrelated_deletion_does_not_surface_old_unrelated_debt(self) -> None:
        root = self.make_repo()
        (root / "docs").mkdir()
        (root / "docs" / "a.md").write_text("[already broken](missing.md)\n", encoding="utf-8")
        (root / "unrelated.txt").write_text("x\n", encoding="utf-8")
        base = self.commit(root, "base")
        (root / "unrelated.txt").unlink()
        self.commit(root, "delete unrelated")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_new_migration_without_downgrade_fails(self) -> None:
        root = self.make_repo()
        (root / "README.md").write_text("base\n", encoding="utf-8")
        base = self.commit(root, "base")
        migrations = root / "alembic" / "versions"
        migrations.mkdir(parents=True)
        (migrations / "001_new.py").write_text("def upgrade():\n    pass\n", encoding="utf-8")
        self.commit(root, "add migration")

        result = self.review(root, base)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("downgrade()", result.stdout)


if __name__ == "__main__":
    unittest.main()
