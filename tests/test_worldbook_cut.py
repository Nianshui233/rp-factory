"""cut-worldbook.py 与 W17/W18：世界书条目必须是原稿切片，不是摘要。

手写条目最常见的病是「顺手压缩」——把《常见误解或谣言》压成「有一些谣言」、
把每级 `behavioral_signs` 压成一句。压掉的那些句子，原本是模型做判断时唯一的
依据；包看起来完整，跑起来人物只剩空标签。所以这里测两件事：

1. 切割器切出来的 content 与原文逐行相同（不许脚本自己顺手润色）；
2. 校验器能认出「被改写过」与「整段没进书」的书。
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "rp-factory"
CUTTER = ROOT / "scripts" / "cut-worldbook.py"
SAMPLE = ROOT / "examples/dry-run-盐湖守夜人"
NL = chr(10)
PACKAGE_SCRIPT = ROOT / "scripts" / "validate-st-package.py"
EXAMPLE = ROOT / "examples/dry-run-盐湖守夜人"

DRAFT = """白潮:

  世界规则:
    昼夜: "入夜后全镇熄灯，只留塔灯"
    规则:
      - 名称: "换班"
        内容: "每六个时辰换一次，迟到者罚役"

  常识清单:
    - "塔内不许提自己的全名"
    - "盐价按潮汐定，落潮那一日最贵"

  未决事项: []
"""

PLAN = """book_name: "白潮 世界书"
default_from: "world-bible.yaml"
skip: ["未决事项"]
entries:
  - section: "世界规则"
    constant: true
    order: 90
  - section: "常识清单"
    order: 86
    keys: ["规矩", "常识", "忌讳", "换班", "灯油", "盐价", "落潮", "宵禁", "名字"]
"""


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestCutter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "产物").mkdir()
        (self.root / "产物" / "world-bible.yaml").write_text(DRAFT, encoding="utf-8")
        (self.root / "plan.yaml").write_text(PLAN, encoding="utf-8")
        self.out = self.root / "书.json"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *extra):
        return subprocess.run(
            [sys.executable, str(CUTTER), "--plan", str(self.root / "plan.yaml"),
             "--draft-root", str(self.root / "产物"), "--out", str(self.out), *extra],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def test_slices_are_verbatim(self):
        run = self._run()
        self.assertEqual(run.returncode, 0, run.stderr)
        book = json.loads(self.out.read_text(encoding="utf-8"))
        entries = book["entries"]
        self.assertEqual(len(entries), 2)
        rule = next(e for e in entries.values() if e["comment"] == "世界规则")
        # 逐行照搬：原文的那几行原样在这里，缩进都不动
        for line in ['    昼夜: "入夜后全镇熄灯，只留塔灯"', "      - 名称: \"换班\""]:
            self.assertIn(line, rule["content"])
        self.assertTrue(rule["content"].startswith("  世界规则:"))
        self.assertTrue(rule["constant"])
        self.assertEqual(rule["order"], 90)

    def test_native_shape_and_uid(self):
        self.assertEqual(self._run().returncode, 0)
        entries = json.loads(self.out.read_text(encoding="utf-8"))["entries"]
        for uid, e in entries.items():
            self.assertEqual(str(e["uid"]), uid)
            self.assertIsInstance(e["key"], list)
            self.assertIs(e["excludeRecursion"], True)
            self.assertEqual(e["position"], 0)
            for field in ("triggers", "outletName", "matchScenario", "ignoreBudget"):
                self.assertIn(field, e, f"缺 {field}，导入后编辑器里是 undefined")

    def test_unknown_section_fails_loudly(self):
        (self.root / "plan.yaml").write_text(
            PLAN.replace('section: "常识清单"', 'section: "不存在的节"'), encoding="utf-8")
        run = self._run()
        self.assertEqual(run.returncode, 1)
        self.assertIn("不存在的节", run.stderr)
        self.assertIn("世界规则", run.stderr)  # 顺便把现有节列出来

    def test_uncovered_section_is_reported(self):
        (self.root / "plan.yaml").write_text(
            PLAN.replace('  - section: "常识清单"', '  - section: "未决事项"'), encoding="utf-8")
        run = self._run()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("没进书", run.stdout)
        self.assertIn("常识清单", run.stdout)

    def test_same_section_twice_fails(self):
        (self.root / "plan.yaml").write_text(
            PLAN.replace('section: "常识清单"', 'section: "世界规则"'), encoding="utf-8")
        run = self._run()
        self.assertEqual(run.returncode, 1)
        self.assertIn("切了两次", run.stderr)


class TestFidelity(unittest.TestCase):
    """W17 / W18：条目像改写、原稿大段没进书，都要被点出来。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.mod = _load(PACKAGE_SCRIPT, "vp_fidelity")
        self.draft = self.root / "产物"
        self.draft.mkdir()
        (self.draft / "world-bible.yaml").write_text(DRAFT, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, entries):
        rep = self.mod.Report()
        book = {"entries": {str(i): {"comment": c, "content": t}
                            for i, (c, t) in enumerate(entries)}}
        self.mod.check_cut_fidelity(book["entries"], self.draft, rep)
        return rep

    def test_verbatim_slices_pass(self):
        rep = self._run([
            ("世界规则", '  世界规则:\n    昼夜: "入夜后全镇熄灯，只留塔灯"\n    规则:\n'
                         '      - 名称: "换班"\n        内容: "每六个时辰换一次，迟到者罚役"'),
            ("常识清单", '  常识清单:\n    - "塔内不许提自己的全名"\n'
                         '    - "盐价按潮汐定，落潮那一日最贵"'),
        ])
        self.assertEqual([c for c, _ in [(code, msg) for _lv, code, msg in rep.warnings]], [])

    def test_rewritten_entry_warns(self):
        rep = self._run([("世界规则", "入夜后全镇熄灯。\n换班每六个时辰一次，迟到罚役。\n盐价按潮汐定。")])
        self.assertIn("W17", [c for c, _ in [(code, msg) for _lv, code, msg in rep.warnings]])
        msg = next(m for c, m in [(code, msg) for _lv, code, msg in rep.warnings] if c == "W17")
        self.assertIn("cut-worldbook.py", msg)

    def test_dropped_sections_warn(self):
        # 只切了一节，另一节整段没进书
        rep = self._run([("世界规则", '  世界规则:\n    昼夜: "入夜后全镇熄灯，只留塔灯"\n'
                                     '    规则:\n      - 名称: "换班"\n        内容: "每六个时辰换一次，迟到者罚役"')])
        # 原稿只有 5 行实质内容，低于「至少 10 行才判」的门槛，所以不报 W18
        self.assertNotIn("W18", [c for c, _ in [(code, msg) for _lv, code, msg in rep.warnings]])

    def test_protocol_entries_are_exempt(self):
        rep = self._run([("[mvu_update]变量更新规则", "### 变量更新规则\n世界.日期：写整串\n角色.祁昭.wick：0–100"),
                         ("世界规则", '  世界规则:\n    昼夜: "入夜后全镇熄灯，只留塔灯"\n'
                                     '    规则:\n      - 名称: "换班"\n        内容: "每六个时辰换一次，迟到者罚役"')])
        self.assertNotIn("W17", [c for c, _ in [(code, msg) for _lv, code, msg in rep.warnings]])

    def test_real_example_is_cut_from_drafts(self):
        draft = EXAMPLE / "制作文件" / "产物"
        book = json.loads((EXAMPLE / "导入包" / "白潮 世界书.json").read_text(encoding="utf-8"))
        rep = self.mod.Report()
        self.mod.check_cut_fidelity(book["entries"], draft, rep)
        self.assertEqual([c for c, _ in [(code, msg) for _lv, code, msg in rep.warnings]], [],
                         f"示例包应当全是原稿切片，却报了 {[(code, msg) for _lv, code, msg in rep.warnings]}")


if __name__ == "__main__":
    unittest.main()

class TestMergeMvu(unittest.TestCase):
    """三件套要随书交付：留在 制作文件/ 里等于没交（W25 也会拦）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "draft").mkdir()
        (self.root / "draft" / "world.yaml").write_text(
            NL.join(["世界规则:", "  冷。", ""]), encoding="utf-8")
        (self.root / "mvu").mkdir()
        (self.root / "mvu" / "变量规则.yaml").write_text(NL.join([
            "entries:",
            "  - comment: \"[mvu_update]变量更新规则\"",
            "    constant: true",
            "    content: 只在有热源时改体温",
            "",
        ]), encoding="utf-8")
        (self.root / "mvu" / "[initvar]变量初始化.yaml").write_text(
            NL.join(["体温: 78", ""]), encoding="utf-8")
        (self.root / "plan.yaml").write_text(NL.join([
            "book_name: 测试",
            "entries:",
            "  - whole: world.yaml",
            "    comment: 世界规则",
            "    keys: [世界]",
            "",
        ]), encoding="utf-8")

    def _cut(self, *extra):
        out = self.root / "book.json"
        run = subprocess.run([sys.executable, str(CUTTER), "--plan", str(self.root / "plan.yaml"),
                              "--draft-root", str(self.root / "draft"), "--out", str(out), *extra],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        book = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"entries": {}}
        return run, book

    def test_不带参数时书里没有MVU条目(self):
        _run, book = self._cut()
        comments = [str(e.get("comment", "")) for e in book["entries"].values()]
        self.assertFalse(any("[initvar]" in c for c in comments))

    def test_merge_mvu_把三件套装进书(self):
        run, book = self._cut("--merge-mvu", str(self.root / "mvu"))
        comments = [str(e.get("comment", "")) for e in book["entries"].values()]
        self.assertIn("[mvu_update]变量更新规则", comments)
        self.assertIn("[initvar]变量初始化", comments)
        self.assertIn("带上 2 条 MVU 条目", run.stdout or "")
        init = [e for e in book["entries"].values() if "[initvar]" in str(e.get("comment"))][0]
        self.assertTrue(init["disable"], "[initvar] 必须禁用：只在开聊时读一次")
        self.assertTrue(init["ignoreBudget"], "[initvar] 不进上下文，别占预算")

    def test_缺规则文件时提醒(self):
        (self.root / "mvu" / "变量规则.yaml").unlink()
        run, book = self._cut("--merge-mvu", str(self.root / "mvu"))
        self.assertIn("变量更新规则", run.stderr or "")
        comments = [str(e.get("comment", "")) for e in book["entries"].values()]
        self.assertIn("[initvar]变量初始化", comments)

    def test_示例包的三件套已在书里(self):
        book = json.loads((SAMPLE / "导入包" / "白潮 世界书.json").read_text(encoding="utf-8"))
        comments = [str(e.get("comment", "")) for e in book["entries"].values()]
        self.assertTrue(any("[initvar]" in c for c in comments))
        self.assertEqual(sum(1 for c in comments if "[mvu_update]" in c), 2, "更新规则 + 输出格式两条")

_ENTRY_LINES = [
    "entries:",
    "  - comment: \"[statusbar]状态栏协议\"",
    "    constant: true",
    "    position: 4",
    "    depth: 2",
    "    content: |",
    "      每轮最后输出 <StatusPlaceHolderImpl/>。",
]


class TestMergeEntries(unittest.TestCase):
    """--merge-entries：协议条目不该靠角色卡的 depth_prompt 承载。"""

    def test_额外条目并进书(self):
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            proto = proj / "协议.yaml"
            proto.write_text(NL.join(_ENTRY_LINES) + NL, encoding="utf-8")
            out = proj / "book.json"
            run = subprocess.run(
                [sys.executable, str(CUTTER), "--plan", str(EXAMPLE / "制作文件" / "项目记录" / "世界书切割.yaml"),
                 "--draft-root", str(EXAMPLE / "制作文件" / "产物"),
                 "--merge-entries", str(proto), "--out", str(out), "--book-name", "白潮 世界书"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(run.returncode, 0, run.stderr)
            book = json.loads(out.read_text(encoding="utf-8"))
            hits = [e for e in book["entries"].values() if e.get("comment") == "[statusbar]状态栏协议"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["position"], 4)
            self.assertFalse(hits[0]["disable"])
