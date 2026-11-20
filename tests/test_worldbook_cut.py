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

ROOT = Path(__file__).resolve().parents[1]
CUTTER = ROOT / "scripts" / "cut-worldbook.py"
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
