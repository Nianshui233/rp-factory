"""F15–F17 与预览副本：设计层能机检的那一小部分。

不测"好不好看"——美学没有客观判据，量它只会诱发刷指标。
这里只测四件能判的：预览守卫是否真的把 MOCK 关在门外、色板有没有分层、
画布变量在不在、`make-preview.py` 会不会把没守卫的文件放过去。
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "rp-factory"
VF_SCRIPT = SKILL / "scripts" / "validate-frontend.py"
MP_SCRIPT = SKILL / "scripts" / "make-preview.py"
TEMPLATES = SKILL / "templates"
VALIDATOR = SKILL / "scripts" / "validate-frontend.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VF = _load("validate_frontend_design", VF_SCRIPT)
MP = _load("make_preview", MP_SCRIPT)

SKELETON = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>
:root { --c-ink: #111; --c-paper: #eee; --c-accent: #b8862b; }
.rp-x { color: var(--c-ink); background: var(--c-paper); }
.x { color: var(--c-accent); }
.y { background: var(--c-paper); }
</style></head>
<body><div class="rp-x" id="root"></div><script>%s</script></body></html>
"""

GUARD = """var RP_PREVIEW = (function(){ try { return window.self === window.top; } catch (e) { return false; } })();
var MOCK = '<x>1</x>';
var data = RP_PREVIEW ? MOCK : '';
"""

CANVAS = "\nbody.rp-preview { --canvas-w: 700px; }\n"


class TestPreviewGuard(unittest.TestCase):
    def _check(self, script: str, extra: str = "") -> tuple[list[str], list[str]]:
        html = SKELETON.replace("</style>", CANVAS + "</style>") % script
        html = extra + html if extra else html
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ui.html"
            p.write_text(html, encoding="utf-8")
            fail, warn, _ok = VF.check(p)
        return fail, warn

    def test_mock_without_guard_fails(self):
        fail, _ = self._check("var MOCK = '<x>1</x>';\nvar data = MOCK;\n")
        self.assertTrue(any(f.startswith("F15") for f in fail), fail)

    def test_mock_outside_preview_branch_fails(self):
        fail, _ = self._check("var MOCK = '<x>1</x>';\nfunction h(){ return window.self === window.top; }\nvar data = MOCK;\n")
        self.assertTrue(any(f.startswith("F15") for f in fail), fail)

    def test_guarded_mock_passes(self):
        fail, warn = self._check(GUARD)
        self.assertFalse([f for f in fail if f.startswith("F15")], fail)
        self.assertFalse([w for w in warn if w.startswith("F15")], warn)

    def test_no_mock_no_guard_is_fine(self):
        fail, _ = self._check("var data = '';\n")
        self.assertFalse([f for f in fail if f.startswith("F15")], fail)


class TestTokenLayers(unittest.TestCase):
    def _check(self, css: str) -> tuple[list[str], list[str]]:
        html = ("<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>" + css +
                CANVAS + "</style></head><body><div class=\"rp-x\"></div><script>" + GUARD +
                "</script></body></html>")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ui.html"
            p.write_text(html, encoding="utf-8")
            fail, warn, _ = VF.check(p)
        return fail, warn

    def test_literal_colour_in_component_layer_warns(self):
        _fail, warn = self._check(":root{} .rp-x{ --rp-x-bg: #fff; }")
        self.assertTrue(any(w.startswith("F16") for w in warn), warn)

    def test_missing_semantic_palette_warns(self):
        _fail, warn = self._check(":root{} .rp-x{ color: #222 }")
        self.assertTrue(any(w.startswith("F16") for w in warn), warn)

    def test_semantic_palette_passes(self):
        _fail, warn = self._check(":root{ --c-ink:#111; --c-paper:#eee; --c-accent:#b8862b; } .rp-x{ color: var(--c-ink); background: var(--c-paper); border-color: var(--c-accent); }")
        self.assertFalse([w for w in warn if w.startswith("F16")], warn)

    def test_missing_canvas_warns(self):
        html = (SKELETON % GUARD)  # 不带 CANVAS
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ui.html"
            p.write_text(html, encoding="utf-8")
            _fail, warn, _ = VF.check(p)
        self.assertTrue(any(w.startswith("F17") for w in warn), warn)


class TestTemplates(unittest.TestCase):
    """仓库自带的三个骨架必须自洽：守卫、画布、语义层、降级动效都有。"""

    NAMES = ("statusbar.html", "opening-ui.html", "wizard-ui.html")

    def test_templates_are_clean(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                fail, warn, _ = VF.check(SKILL / "templates" / name)
                self.assertEqual(fail, [], fail)
                self.assertEqual(warn, [], warn)

    def test_templates_have_guard_and_canvas(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                text = (SKILL / "templates" / name).read_text(encoding="utf-8")
                self.assertIn("window.self === window.top", text)
                self.assertIn("if (RP_PREVIEW)", text.replace("RP_PREVIEW ?", "RP_PREVIEW ?"))
                self.assertIn("--canvas-w", text)
                self.assertGreaterEqual(text.count("var(--c-"), 3)
                self.assertIn("prefers-reduced-motion", text)

    def test_example_products_are_clean(self):
        prod = SKILL / "examples" / "dry-run-盐湖守夜人" / "制作文件" / "产物"
        for name in ("statusbar-ui.html", "wizard-ui.html"):
            with self.subTest(name=name):
                fail, warn, _ = VF.check(prod / name)
                self.assertEqual(fail, [], fail)
                self.assertEqual(warn, [], warn)


class TestMakePreview(unittest.TestCase):
    def test_guard_problems_detects_missing_guard(self):
        problems = MP.guard_problems("var MOCK = 1; var data = MOCK;")
        self.assertTrue(any("window.self" in p for p in problems), problems)

    def test_guard_problems_detects_missing_canvas(self):
        text = (SKILL / "templates" / "statusbar.html").read_text(encoding="utf-8")
        self.assertEqual(MP.guard_problems(text), [])

    def test_copy_writes_preview_folder(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "ui.html"
            src.write_text((SKILL / "templates" / "statusbar.html").read_text(encoding="utf-8"), encoding="utf-8")
            code = MP.main([str(src)])
            self.assertEqual(code, 0)
            self.assertTrue((Path(d) / "preview" / "ui.html").is_file())

    def test_check_mode_refuses_unguarded(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "bad.html"
            src.write_text(SKELETON % "var MOCK = 1; var data = MOCK;", encoding="utf-8")
            self.assertEqual(MP.main([str(src), "--check"]), 1)

    def test_check_mode_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "ui.html"
            src.write_text((SKILL / "templates" / "statusbar.html").read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(MP.main([str(src), "--check"]), 0)
            self.assertFalse((Path(d) / "preview").exists())


if __name__ == "__main__":
    unittest.main()

class TestSendTriggersGeneration(unittest.TestCase):
    """`/send` 只把消息塞进聊天；不跟 `/trigger` 就是「消息进了没人回」。"""

    def test_骨架里有_trigger(self):
        for name in ("opening-ui.html", "wizard-ui.html", "statusbar.html"):
            text = (TEMPLATES / name).read_text(encoding="utf-8")
            if "/send " not in text:
                continue
            with self.subTest(src=name):
                self.assertIn("/trigger", text, "发送后必须触发一次生成")

    def test_只发_send_会被拦(self):
        bad = "<!DOCTYPE html><html><body><script>triggerSlash('/send 你好');</script></body></html>"
        with tempfile.TemporaryDirectory() as td:
            f = pathlib.Path(td) / "bad.html"
            f.write_text(bad, encoding="utf-8")
            run = subprocess.run([sys.executable, str(VALIDATOR), str(f)], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("FAIL F22", (run.stdout or ""))

    def test_send_加_trigger_放行(self):
        good = "<!DOCTYPE html><html><body><script>await triggerSlash('/send 你好');await triggerSlash('/trigger');</script></body></html>"
        with tempfile.TemporaryDirectory() as td:
            f = pathlib.Path(td) / "good.html"
            f.write_text(good, encoding="utf-8")
            run = subprocess.run([sys.executable, str(VALIDATOR), str(f)], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace")
        self.assertIn("ok   F22", (run.stdout or ""))
