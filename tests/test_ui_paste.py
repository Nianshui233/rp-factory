"""界面粘贴形态 + MVU 本体地址。

真机验证过两件事（2026-11-22，极寒末日 / ST 1.19.0 + 酒馆助手 4.12.1）：
1. `replaceString` 里的 HTML 必须在 ```html 围栏里，裸 HTML 只出一段代码块、界面不出现；
2. `StageDog/tavern_module/dist/MVU/index.js` 已 404，MVU 本体换到 MagicalAstrogy 的 bundle。
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "rp-factory"
PENDING = "【尚未粘贴界面】"
FENCE_OPEN = "```html\n"
FENCE_CLOSE = "```"


def _regex_files():
    yield SKILL / "templates" / "regex-frontend.json"
    yield SKILL / "examples" / "dry-run-盐湖守夜人" / "导入包" / "正则.json"


class TestPendingPlaceholder(unittest.TestCase):
    def test_pending_在围栏里(self):
        for path in _regex_files():
            rules = json.loads(path.read_text(encoding="utf-8"))
            for rule in rules:
                repl = rule.get("replaceString", "")
                if PENDING not in repl:
                    continue
                with self.subTest(src=path.name, rule=rule.get("scriptName")):
                    self.assertTrue(repl.startswith(FENCE_OPEN), "待粘占位必须以 ```html 围栏开头")
                    self.assertTrue(repl.rstrip().endswith(FENCE_CLOSE), "围栏必须收尾")
                    self.assertEqual(repl.count(FENCE_CLOSE), 2, "围栏内不许再出现三反引号")

    def test_围栏内说明不含反引号(self):
        for path in _regex_files():
            rules = json.loads(path.read_text(encoding="utf-8"))
            for rule in rules:
                repl = rule.get("replaceString", "")
                if PENDING not in repl:
                    continue
                body = repl[len(FENCE_OPEN):].rstrip()
                body = body[: body.rfind(FENCE_CLOSE)]
                with self.subTest(rule=rule.get("scriptName")):
                    self.assertNotIn("``", body)


class TestMvuBundleUrl(unittest.TestCase):
    def test_stage_mvu_用可用的_bundle(self):
        text = (SKILL / "references" / "stage-mvu.md").read_text(encoding="utf-8")
        self.assertIn("MagicalAstrogy/MagVarUpdate/artifact/bundle.js", text)

    def test_不再引用失效的_mvu_地址(self):
        """失效的是那个 URL 路径；文档里提一句「哪条已 404」是可以的。"""
        dead = "tavern_module/dist/MVU"
        files = list((SKILL / "references").glob("*.md"))
        files += [p for p in (SKILL / "templates").iterdir() if p.is_file()]
        for path in files:
            if path.suffix not in {".md", ".json", ".js", ".yaml", ".txt"}:
                continue
            with self.subTest(src=path.name):
                self.assertNotIn(dead, path.read_text(encoding="utf-8"))

    def test_导入说明提醒围栏(self):
        text = (SKILL / "templates" / "import-guide.txt").read_text(encoding="utf-8")
        self.assertIn("围栏", text)


if __name__ == "__main__":
    unittest.main()
