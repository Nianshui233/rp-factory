"""导入包槽位：卡 / 世界书 / 正则 / 脚本 / html / 说明，五槽各一份、平铺、内容对得上（C15）。

为什么按内容认而不是按文件名认：文件名可以写错，内容不会。把世界书改名成 `角色卡.json`
导进酒馆，表现是「导入成功但什么也没有」——没人会立刻想到是文件类型错了。
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "rp-factory"
CONTRACT_SCRIPT = ROOT / "scripts" / "validate-contract.py"
PACKAGE_SCRIPT = ROOT / "scripts" / "validate-st-package.py"
EXAMPLE = ROOT / "examples/dry-run-盐湖守夜人"

CONTRACT = """project:
  name: 示例
  workspace: workspace
  stages_requested: [world, delivery]
stages:
  world: done
  mvu: done
  delivery: done
naming:
  world: 示例
delivery:
  route: st
  st_name: 示例
decisions: []
"""

CARD = {"spec": "chara_card_v2", "data": {"name": "示例", "first_mes": "<建卡向导>",
                                          "extensions": {"world": "示例 世界书"}}}
BOOK = {"entries": {"0": {"key": ["示例"], "content": "设定"}}}
REGEX = [{"scriptName": "RP · 建卡向导", "findRegex": "/<建卡向导>/g",
          "replaceString": "【尚未粘贴界面】打开「示例 开局前端.html」粘贴"}]
SCRIPT = {"type": "folder", "enabled": False, "name": "示例", "id": "x",
          "scripts": [{"type": "script", "enabled": True, "name": "MVU", "id": "y", "content": ""}]}


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSlots(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "制作文件").mkdir()
        (self.root / "导入包").mkdir()
        (self.root / "制作文件" / "contract.yaml").write_text(CONTRACT, encoding="utf-8")
        self.mod = _load(CONTRACT_SCRIPT, "vc_slots")
        self.mod.fails.clear()
        self.mod.warns.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, data):
        p = self.root / "导入包" / name
        if isinstance(data, str):
            p.write_text(data, encoding="utf-8")
        else:
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _full_package(self):
        self._write("示例（纯净）.json", CARD)
        self._write("示例 世界书.json", BOOK)
        self._write("正则.json", REGEX)
        self._write("示例 酒馆助手脚本.json", SCRIPT)
        self._write("示例 开局前端.html", "<html><body><div></div></body></html>")
        self._write("导入说明.txt", "按顺序导")

    def _codes(self):
        return [c for c, _ in self.mod.fails]

    def test_full_package_passes(self):
        self._full_package()
        self.mod.check_output_dirs(self.mod.yaml.safe_load(CONTRACT), self.root)
        self.assertEqual(self._codes(), [])

    def test_missing_guide_fails(self):
        self._full_package()
        (self.root / "导入包" / "导入说明.txt").unlink()
        self.mod.check_output_dirs(self.mod.yaml.safe_load(CONTRACT), self.root)
        self.assertIn("C15", self._codes())

    def test_missing_script_when_mvu_done_fails(self):
        self._full_package()
        (self.root / "导入包" / "示例 酒馆助手脚本.json").unlink()
        self.mod.check_output_dirs(self.mod.yaml.safe_load(CONTRACT), self.root)
        self.assertTrue(any("酒馆助手脚本" in m for _, m in self.mod.fails))

    def test_wrong_content_in_book_slot_fails(self):
        self._full_package()
        self._write("示例 世界书.json", CARD)  # 文件名叫世界书，内容是卡
        self.mod.check_output_dirs(self.mod.yaml.safe_load(CONTRACT), self.root)
        self.assertTrue(any("文件名与内容对不上" in m for _, m in self.mod.fails))

    def test_subdir_fails_because_flat(self):
        self._full_package()
        (self.root / "导入包" / "备份").mkdir()
        self.mod.check_output_dirs(self.mod.yaml.safe_load(CONTRACT), self.root)
        self.assertTrue(any("平铺" in m for _, m in self.mod.fails))

    def test_stray_file_fails(self):
        self._full_package()
        self._write("world-bible.yaml", "a: 1")
        self.mod.check_output_dirs(self.mod.yaml.safe_load(CONTRACT), self.root)
        self.assertTrue(any("不认识的文件" in m for _, m in self.mod.fails))

    def test_pending_ui_without_html_fails(self):
        self._full_package()
        (self.root / "导入包" / "示例 开局前端.html").unlink()
        self.mod.check_output_dirs(self.mod.yaml.safe_load(CONTRACT), self.root)
        self.assertTrue(any("用户永远粘不上" in m for _, m in self.mod.fails))


class TestPackageRules(unittest.TestCase):
    """validate-st-package 的两条新规则：卡里不许带脚本（C12）、界面待粘贴（R07）。"""

    def setUp(self):
        self.mod = _load(PACKAGE_SCRIPT, "vsp_rules")
        self.rep = self.mod.Report()

    def _codes(self):
        return [code for _, code, _ in self.rep.failures]

    def _warns(self):
        return [code for _, code, _ in self.rep.warnings]

    def test_embedded_script_fails(self):
        card = json.loads(json.dumps(CARD))
        card["data"]["extensions"]["tavern_helper"] = {"scripts": [{"type": "script", "name": "MVU"}]}
        self.mod.validate_card(card, None, None, self.rep)
        self.assertIn("C12", self._codes())

    def test_clean_card_passes(self):
        self.mod.validate_card(json.loads(json.dumps(CARD)), None, None, self.rep)
        self.assertNotIn("C12", self._codes())

    def test_pending_ui_is_accepted(self):
        self.mod.validate_regex_pack(REGEX, None, self.rep)
        self.assertNotIn("R07", self._codes())

    def test_empty_replacement_fails(self):
        self.mod.validate_regex_pack(
            [{"scriptName": "RP · 建卡向导", "findRegex": "/<建卡向导>/g",
              "replaceString": "", "placement": [2], "markdownOnly": True}], None, self.rep)
        self.assertIn("R07", self._codes())

    def test_hiding_rule_may_be_empty(self):
        self.mod.validate_regex_pack(
            [{"scriptName": "RP · 不显示：变量更新块",
              "findRegex": r"/<UpdateVariable>[\s\S]*?<\/UpdateVariable>/g",
              "replaceString": "", "placement": [2], "markdownOnly": True}], None, self.rep)
        self.assertNotIn("R07", self._codes())

    def test_bare_html_doc_is_not_warned(self):
        self.mod.validate_regex_pack(
            [{"scriptName": "RP · 建卡向导", "findRegex": "/<建卡向导>/g",
              "replaceString": "<!DOCTYPE html><html><body></body></html>",
              "placement": [2], "markdownOnly": True}], None, self.rep)
        self.assertNotIn("R06", self._warns())


class TestExamplePackage(unittest.TestCase):
    def test_example_has_five_slots(self):
        names = sorted(p.name for p in (EXAMPLE / "导入包").iterdir())
        for want in ("导入说明.txt", "正则.json", "白潮 开局前端.html",
                     "白潮 状态栏.html", "白潮 酒馆助手脚本.json", "白潮 世界书.json", "白潮（纯净）.json"):
            self.assertIn(want, names)

    def test_example_card_is_clean(self):
        card = json.loads((EXAMPLE / "导入包" / "白潮（纯净）.json").read_text(encoding="utf-8"))
        ext = card["data"]["extensions"]
        self.assertNotIn("character_book", card["data"])
        self.assertFalse(ext.get("regex_scripts"))
        self.assertFalse(ext.get("tavern_helper"), "脚本应单独一份")

    def test_example_regex_is_pending(self):
        rules = json.loads((EXAMPLE / "导入包" / "正则.json").read_text(encoding="utf-8"))
        pending = [r for r in rules if "【尚未粘贴界面】" in str(r.get("replaceString", ""))]
        self.assertEqual(len(pending), 2, "开局与状态栏两条都该是待粘贴态")


if __name__ == "__main__":
    unittest.main()
