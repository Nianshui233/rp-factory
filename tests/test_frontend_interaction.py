# -*- coding: utf-8 -*-
"""交互联动的可机检部分：四栏声明、预览禁写、写后复读、pending 防护。

覆盖 validate-frontend.py 的 F18–F21 与 templates/control-center.html 的自洽性。
"""
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "rp-factory"


def _load():
    path = SKILL / "scripts" / "validate-frontend.py"
    spec = importlib.util.spec_from_file_location("validate_frontend", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VF = _load()


def _check(text: str, tmp: Path, name: str = "ui.html"):
    p = tmp / name
    p.write_text(text, encoding="utf-8")
    return VF.check(p)


BASE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>:root{--c-ink:#111;--c-paper:#eee;--canvas-w:700px}</style></head>
<body><div id="x"></div><script>
(function(){'use strict';
%s
})();
</script></body></html>
"""


class _Tmp(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()


class TestDeclarations(_Tmp):
    def test_write_without_declaration_fails(self):
        fail, _, _ = _check(BASE % "triggerSlash('/send hi');", self.tmp)
        self.assertTrue(any("F19" in f for f in fail), fail)

    def test_empty_declaration_with_write_fails(self):
        src = "var WRITES = [];\ntriggerSlash('/send hi');"
        fail, _, _ = _check(BASE % src, self.tmp)
        self.assertTrue(any("F19" in f for f in fail), fail)

    def test_declared_write_passes(self):
        src = ("var WRITES = [{ scope: 'chat', path: '玩家消息', when: '点确认' }];\n"
               "triggerSlash('/send hi');")
        fail, warn, _ = _check(BASE % src, self.tmp)
        self.assertFalse([f for f in fail if "F19" in f], fail)

    def test_readonly_ui_passes(self):
        src = "var WRITES = [];\nvar a = getChatMessages(getCurrentMessageId());"
        fail, _, _ = _check(BASE % src, self.tmp)
        self.assertFalse([f for f in fail if "F19" in f], fail)


class TestPreviewWrite(_Tmp):
    def test_write_inside_preview_block_fails(self):
        src = """var RP_PREVIEW = (function(){try{return window.self === window.top}catch(e){return false}})();
var MOCK = {}; MOCK['灯芯'] = 1;
if (RP_PREVIEW) {
  MOCK['灯芯'] = 2;
  Mvu.replaceMvuData({}, {type:'message', message_id: 0});
}"""
        fail, _, _ = _check(BASE % src, self.tmp)
        self.assertTrue(any("F18" in f for f in fail), fail)

    def test_write_outside_preview_block_passes(self):
        src = """var RP_PREVIEW = (function(){try{return window.self === window.top}catch(e){return false}})();
var MOCK = {}; MOCK['灯芯'] = 1;
var WRITES = [{scope:'message', path:'stat_data.灯芯', when:'点写入'}];
if (RP_PREVIEW) { MOCK['灯芯'] = 2; }
if (!RP_PREVIEW) { Mvu.replaceMvuData({}, {type:'message', message_id: 0}); }
var after = Mvu.getMvuData({type:'message', message_id: 0});
var btn = document.getElementById('x'); btn.disabled = true;"""
        fail, _, _ = _check(BASE % src, self.tmp)
        self.assertFalse([f for f in fail if "F18" in f], fail)


class TestReread(_Tmp):
    def test_write_without_reread_warns(self):
        src = ("var WRITES = [{scope:'message', path:'stat_data.a', when:'w'}];\n"
               "Mvu.replaceMvuData({}, {type:'message', message_id: 1});\n"
               "var b = document.getElementById('x'); b.disabled = false;")
        _, warn, _ = _check(BASE % src, self.tmp)
        self.assertTrue(any("F20" in w for w in warn), warn)

    def test_write_with_reread_passes(self):
        src = ("var WRITES = [{scope:'message', path:'stat_data.a', when:'w'}];\n"
               "Mvu.replaceMvuData({}, {type:'message', message_id: 1});\n"
               "var after = Mvu.getMvuData({type:'message', message_id: 1});\n"
               "var b = document.getElementById('x'); b.disabled = false;")
        _, warn, _ = _check(BASE % src, self.tmp)
        self.assertFalse([w for w in warn if "F20" in w], warn)


class TestPending(_Tmp):
    def test_missing_disabled_warns(self):
        src = ("var WRITES = [{scope:'message', path:'stat_data.a', when:'w'}];\n"
               "Mvu.replaceMvuData({}, {type:'message', message_id: 1});\n"
               "Mvu.getMvuData({type:'message', message_id: 1});")
        _, warn, _ = _check(BASE % src, self.tmp)
        self.assertTrue(any("F21" in w for w in warn), warn)


class TestControlCenterTemplate(unittest.TestCase):
    def setUp(self):
        self.path = SKILL / "templates" / "control-center.html"
        self.text = self.path.read_text(encoding="utf-8")

    def test_exists_and_clean(self):
        self.assertTrue(self.path.is_file())
        fail, warn, _ = VF.check(self.path)
        self.assertEqual((fail, warn), ([], []), (fail, warn))

    def test_declares_four_columns(self):
        for key in ("READS", "WRITES", "LISTENS", "NEEDS"):
            self.assertRegex(self.text, rf"\bvar {key}\s*=")

    def test_writes_are_declared(self):
        self.assertIn("replaceMvuData", self.text)
        m = re.search(r"var WRITES\s*=\s*\[([\s\S]*?)\];", self.text)
        self.assertIsNotNone(m)
        self.assertIn("stat_data.", m.group(1))

    def test_rereads_after_write(self):
        write_at = self.text.rfind("replaceMvuData(")
        read_at = self.text.rfind("getMvuData(")
        self.assertGreater(read_at, write_at)

    def test_pending_guard(self):
        self.assertIn("writing", self.text)
        self.assertIn("disabled", self.text)

    def test_preview_branch_has_no_writes(self):
        fail, _, _ = VF.check(self.path)
        self.assertFalse([f for f in fail if "F18" in f])

    def test_failure_keeps_input(self):
        self.assertIn("未写入", self.text)
        self.assertIn("保留用户输入", self.text)

    def test_stale_guard_documented(self):
        # 陈旧确认作废与幂等要写在模板注释或交互页里
        ref = (SKILL / "references" / "frontend-interaction.md").read_text(encoding="utf-8")
        self.assertIn("陈旧确认作废", ref)
        self.assertIn("幂等", ref)


class TestTemplatesDeclare(unittest.TestCase):
    def test_all_templates_declare_writes(self):
        for name in ("statusbar.html", "opening-ui.html", "wizard-ui.html", "control-center.html"):
            text = (SKILL / "templates" / name).read_text(encoding="utf-8")
            self.assertRegex(text, r"\bvar WRITES\s*=", name)

    def test_statusbar_is_readonly(self):
        text = (SKILL / "templates" / "statusbar.html").read_text(encoding="utf-8")
        m = re.search(r"var WRITES\s*=\s*\[([\s\S]*?)\];", text)
        self.assertEqual(m.group(1).strip(), "")
        self.assertNotIn("replaceMvuData", text)

    def test_example_products_are_clean(self):
        prods = SKILL / "examples" / "dry-run-盐湖守夜人" / "制作文件" / "产物"
        for p in sorted(prods.glob("*.html")):
            fail, warn, _ = VF.check(p)
            self.assertEqual(fail, [], (p.name, fail))

    def test_prompt_template_has_interaction_section(self):
        text = (SKILL / "templates" / "frontend-prompt.yaml").read_text(encoding="utf-8")
        for key in ("交互:", "读:", "写:", "听:", "依赖:"):
            self.assertIn(key, text)


if __name__ == "__main__":
    unittest.main()
