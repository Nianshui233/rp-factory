"""版本号不变量：SKILL.md 的 metadata.version、CHANGELOG 首条、run_checks 的 banner 必须一致。

版本号只为了让人知道「手上这份是哪一版」，所以它必须只有一处真相是能被读错的。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "rp-factory"
REPO = Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR
SKILL = ROOT / "SKILL.md"
CHANGELOG = REPO / "CHANGELOG.md"
RUN_CHECKS = ROOT / "scripts" / "run_checks.sh"

VERSION_RE = re.compile(r"^\d+\.\d+\.\d{2}$")


def _frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


def skill_version() -> str:
    block = _frontmatter(SKILL.read_text(encoding="utf-8"))
    m = re.search(r"^  version:\s*['\"]?([0-9.]+)['\"]?\s*$", block, re.M)
    return m.group(1) if m else ""


def changelog_version() -> str:
    m = re.search(r"^##\s+([0-9]+\.[0-9]+\.[0-9]+)", CHANGELOG.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else ""


class TestVersion(unittest.TestCase):
    def test_skill_declares_version(self):
        self.assertTrue(skill_version(), "SKILL.md frontmatter 缺 metadata.version")

    def test_version_format_is_x_y_zz(self):
        self.assertRegex(skill_version(), VERSION_RE)

    def test_changelog_matches_skill(self):
        self.assertEqual(changelog_version(), skill_version(),
                         "CHANGELOG 首条版本与 SKILL.md 的 metadata.version 不一致")

    def test_changelog_entry_has_date(self):
        # assertRegex 不带 re.M，^ 只认全文开头，所以这里自己 search
        text = CHANGELOG.read_text(encoding="utf-8")
        self.assertTrue(
            re.search(r"^##\s+[0-9]+\.[0-9]+\.[0-9]+\s+—\s+\d{4}-\d{2}-\d{2}", text, re.M),
            "CHANGELOG 首条要写成 `## <版本> — YYYY-MM-DD`",
        )

    def test_run_checks_prints_version(self):
        self.assertIn("rp-factory v", RUN_CHECKS.read_text(encoding="utf-8"),
                      "run_checks.sh 头部应打印版本，方便确认手上这份是哪一版")


if __name__ == "__main__":
    unittest.main()
