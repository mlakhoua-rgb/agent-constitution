from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bootstrap.py"
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


class BootstrapTests(unittest.TestCase):
    def dest(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="bootstrap-test-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return root

    def bootstrap(self, dest: Path, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--dest", str(dest), *args],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def broken_links(self, doc: Path) -> list[str]:
        return [
            target
            for target in MD_LINK_RE.findall(doc.read_text(encoding="utf-8"))
            if not re.match(r"^(https?:|mailto:|#|<)", target)
            and not (doc.parent / target.split("#", 1)[0].strip()).exists()
        ]

    def test_stage1_handoff_index_has_no_broken_links(self) -> None:
        # The index is generated, so a copied one lists handoffs the adopter's tree
        # does not contain — a hard librarian --check failure on a clean install.
        dest = self.dest()
        self.bootstrap(dest)
        index = dest / "docs/handoffs/INDEX.md"
        self.assertTrue(index.exists(), "Stage 1 must leave a handoff index behind")
        self.assertEqual(self.broken_links(index), [])

    def test_stage1_does_not_copy_this_repo_handoff_history(self) -> None:
        dest = self.dest()
        self.bootstrap(dest)
        index = (dest / "docs/handoffs/INDEX.md").read_text(encoding="utf-8")
        self.assertIn("*none yet*", index)
        self.assertEqual(sorted(p.name for p in (dest / "docs/handoffs").iterdir()),
                         ["INDEX.md", "TEMPLATE.md"])

    def test_stage4_state_md_index_link_resolves(self) -> None:
        # docs/STATE.md links the index and librarian treats STATE.md links as hard
        # failures, so Stage 4 must not depend on the adopter running --write first.
        dest = self.dest()
        self.bootstrap(dest, "--stage", "4")
        self.assertEqual(self.broken_links(dest / "docs/STATE.md"), [])

    def test_existing_index_is_kept_without_force_and_replaced_with_force(self) -> None:
        dest = self.dest()
        self.bootstrap(dest)
        index = dest / "docs/handoffs/INDEX.md"
        index.write_text("# mine\n", encoding="utf-8")

        self.bootstrap(dest)
        self.assertEqual(index.read_text(encoding="utf-8"), "# mine\n")

        self.bootstrap(dest, "--force")
        self.assertIn("Handoff index", index.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
