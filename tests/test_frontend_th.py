"""F10–F14：酒馆助手 iframe 环境里会静默失效的前端写法。

每条规则都对应 `references/tavern-helper.md` 里的一个源码锚点，锚点本身由
`scripts/check_st_facts.py` 的 TH_FACTS 守住。这里只测规则行为。
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "rp-factory"
SCRIPT = ROOT / "scripts" / "validate-frontend.py"
SKILL = ROOT
VALIDATOR = SCRIPT


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

class TestMvuWait(unittest.TestCase):
    """F23：消息 iframe 里的 Mvu 是异步注入的，起手就判 typeof 会把「还没到」显示成「未启用」。"""

    def _run(self, html: str):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "ui.html"
            f.write_text(html, encoding="utf-8")
            return subprocess.run([sys.executable, str(VALIDATOR), str(f)],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_直接判typeof会拦(self):
        run = self._run("<html><body><script>if (typeof Mvu === 'undefined') return;"
                        "var d = Mvu.getMvuData({type:'message'});</script></body></html>")
        self.assertIn("F23", run.stdout or "")

    def test_waitGlobalInitialized放过(self):
        run = self._run("<html><body><script>await waitGlobalInitialized('Mvu');"
                        "var d = Mvu.getMvuData({type:'message'});</script></body></html>")
        self.assertNotIn("[ FAIL ] F23", run.stdout or "")

    def test_parent兜底也放过(self):
        run = self._run("<html><body><script>var api = window.Mvu || window.parent.Mvu;"
                        "api.getMvuData({type:'message'});</script></body></html>")
        self.assertNotIn("[ FAIL ] F23", run.stdout or "")

    def test_不用Mvu的文件不报(self):
        run = self._run("<html><body><p>hi</p></body></html>")
        self.assertNotIn("F23", run.stdout or "")

    def test_模板与控制中心都过(self):
        for name in ("control-center.html", "statusbar.html"):
            run = self._run((SKILL / "templates" / name).read_text(encoding="utf-8"))
            self.assertNotIn("[ FAIL ] F23", run.stdout or "", name)

class TestLatestFloor(unittest.TestCase):
    """F24：写回必须写最新楼层——历史楼层的快照不会跟着后续回合更新。"""

    def _run(self, html: str):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "ui.html"
            f.write_text(html, encoding="utf-8")
            return subprocess.run([sys.executable, str(VALIDATOR), str(f)],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_写回自己那一楼会警告(self):
        run = self._run("<html><body><script>await waitGlobalInitialized('Mvu');"
                        "var mid = getCurrentMessageId();"
                        "Mvu.replaceMvuData(d, {type:'message', message_id: mid});</script></body></html>")
        self.assertIn("F24", run.stdout or "")

    def test_写最新楼层放过(self):
        run = self._run("<html><body><script>await waitGlobalInitialized('Mvu');"
                        "Mvu.replaceMvuData(d, {type:'message', message_id: 'latest'});</script></body></html>")
        self.assertNotIn("F24", run.stdout or "")

    def test_只读HUD读自己那一楼不警告(self):
        run = self._run("<html><body><script>await waitGlobalInitialized('Mvu');"
                        "var mid = getCurrentMessageId();"
                        "var d = Mvu.getMvuData({type:'message', message_id: mid});</script></body></html>")
        self.assertNotIn("F24", run.stdout or "")

    def test_示例状态栏与模板都不触发(self):
        for path in (SKILL / "templates" / "control-center.html",
                     SKILL / "examples/dry-run-盐湖守夜人/制作文件/产物/statusbar-ui.html"):
            run = self._run(path.read_text(encoding="utf-8"))
            self.assertNotIn("F24", run.stdout or "", path.name)
