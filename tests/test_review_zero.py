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
