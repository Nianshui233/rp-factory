"""三件套校验里最容易静默失效的那一条：卡里的 extensions.world 必须等于世界书文件名。

ST 按**书名**把书挂到卡上（`public/scripts/world-info.js:1128` push 的是书名），
名字对不上时导入不报错、小地球不亮，只在聊天里表现为「设定全忘了」。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-st-package.py"

CARD = {
    "spec": "chara_card_v2",
    "spec_version": "2.0",
    "name": "测试世界",
    "description": "骨架。以上是设定，不是示例对话",
    "first_mes": "{{user}} 推开门。",
    "data": {
        "name": "测试世界",
        "description": "骨架。以上是设定，不是示例对话",
        "first_mes": "{{user}} 推开门。",
        "extensions": {"world": "@@WORLD@@", "regex_scripts": []},
    },
}


def build(tmp: Path, world: str, book_name: str) -> Path:
    pkg = tmp / "导入包"
    pkg.mkdir()
    card = json.loads(json.dumps(CARD).replace("@@WORLD@@", world))
    (pkg / "测试世界（纯净）.json").write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    (pkg / "正则.json").write_text("[]", encoding="utf-8")
    book = {"entries": {"0": {"uid": 0, "key": [], "comment": "规则", "content": "一句规则",
                              "constant": True, "order": 100, "position": 0,
                              "disable": False, "excludeRecursion": True}}}
    (pkg / f"{book_name}.json").write_text(json.dumps(book, ensure_ascii=False), encoding="utf-8")
    return pkg


def run(pkg: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), str(pkg)],
                          capture_output=True, text=True, encoding="utf-8")


class TestWorldBinding(unittest.TestCase):
    def test_matching_name_passes(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = build(Path(d), "测试世界 世界书", "测试世界 世界书")
            r = run(pkg)
            self.assertNotIn("≠ 世界书文件名", r.stdout)

    def test_mismatch_fails_with_the_two_names(self):
        with tempfile.TemporaryDirectory() as d:
            pkg = build(Path(d), "测试世界 世界书", "改过名的书 世界书")
            r = run(pkg)
            self.assertIn("≠ 世界书文件名", r.stdout)
            self.assertIn("改过名的书 世界书", r.stdout)
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
