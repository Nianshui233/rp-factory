"""F10–F14：酒馆助手 iframe 环境里会静默失效的前端写法。

每条规则都对应 `references/tavern-helper.md` 里的一个源码锚点，锚点本身由
`scripts/check_st_facts.py` 的 TH_FACTS 守住。这里只测规则行为。
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "rp-factory" / "scripts" / "validate-frontend.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_frontend", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


VF = _load()

SKELETON = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>body{margin:0}</style></head>
<body>%s</body></html>
"""


def _check(body: str):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "ui.html"
        p.write_text(SKELETON % body, encoding="utf-8")
        return VF.check(p)


def _has(rows, code):
    return any(r.startswith(code) for r in rows)


class TestF10EventNames(unittest.TestCase):
    def test_手写事件字符串报警(self):
        _, warn, _ = _check("<script>eventOn('chat_changed', () => {});</script>")
        self.assertTrue(_has(warn, "F10"))

    def test_用事件常量不报警(self):
        _, warn, _ = _check("<script>eventOn(tavern_events.CHAT_CHANGED, () => {});</script>")
        self.assertFalse(_has(warn, "F10"))

    def test_eventSource手写也报(self):
        _, warn, _ = _check("<script>SillyTavern.eventSource.on('message_received', f);</script>")
        self.assertTrue(_has(warn, "F10"))


class TestF11RelativePaths(unittest.TestCase):
    def test_相对图片路径报警(self):
        _, warn, _ = _check('<img src="bg.png">')
        self.assertTrue(_has(warn, "F11"))

    def test_相对css_url报警(self):
        _, warn, _ = _check("<style>.a{background:url(img/bg.png)}</style><div class='a'></div>")
        self.assertTrue(_has(warn, "F11"))

    def test_data_uri不报警(self):
        _, warn, _ = _check('<img src="data:image/png;base64,AAA">')
        self.assertFalse(_has(warn, "F11"))

    def test_站内绝对路径不报警(self):
        # 酒馆同源，/scripts/... 是合法且稳定的写法
        _, warn, _ = _check('<img src="/img/ai4.png">')
        self.assertFalse(_has(warn, "F11"))


class TestF12CrossFrame(unittest.TestCase):
    def test_直接操作父文档报警(self):
        _, warn, _ = _check("<script>window.parent.document.getElementById('chat').innerHTML='';</script>")
        self.assertTrue(_has(warn, "F12"))

    def test_用父窗口全局不报警(self):
        _, warn, _ = _check("<script>console.log(parent.TavernHelper);</script>")
        self.assertFalse(_has(warn, "F12"))


class TestF13RefreshAll(unittest.TestCase):
    def test_refresh_all报警(self):
        _, warn, _ = _check("<script>await setChatMessages([{message_id: 3}], {refresh: 'all'});</script>")
        self.assertTrue(_has(warn, "F13"))

    def test_refresh_affected不报警(self):
        _, warn, _ = _check("<script>await setChatMessages([{message_id: 3}], {refresh: 'affected'});</script>")
        self.assertFalse(_has(warn, "F13"))


class TestF14TimerLeak(unittest.TestCase):
    def test_有setInterval没有clear报警(self):
        _, warn, _ = _check("<script>setInterval(tick, 1000);</script>")
        self.assertTrue(_has(warn, "F14"))

    def test_配对的清理不报警(self):
        _, warn, _ = _check(
            "<script>const t = setInterval(tick, 1000);"
            "window.addEventListener('pagehide', () => clearInterval(t));</script>"
        )
        self.assertFalse(_has(warn, "F14"))


class TestRealTemplates(unittest.TestCase):
    """仓库自带模板不许被新规则打脸（否则规则就是噪音）。"""

    def test_模板无新增警告(self):
        root = Path(__file__).resolve().parents[1] / "skills" / "rp-factory" / "templates"
        files = sorted(root.glob("*.html"))
        self.assertTrue(files, "templates/ 下应有前端模板")
        for f in files:
            _, warn, _ = VF.check(f)
            for code in ("F10", "F11", "F12", "F13", "F14"):
                self.assertFalse(
                    _has(warn, code), f"{f.name} 触发 {code}：{ [w for w in warn if w.startswith(code)] }"
                )


if __name__ == "__main__":
    unittest.main()
