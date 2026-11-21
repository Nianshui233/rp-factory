"""导入包槽位：卡 / 世界书 / 正则 / 脚本 / html / 说明，五槽各一份、平铺、内容对得上（C15）。

为什么按内容认而不是按文件名认：文件名可以写错，内容不会。把世界书改名成 `角色卡.json`
导进酒馆，表现是「导入成功但什么也没有」——没人会立刻想到是文件类型错了。
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "rp-factory"
NL = chr(10)
CONTRACT_SCRIPT = ROOT / "scripts" / "validate-contract.py"
PACKAGE_SCRIPT = ROOT / "scripts" / "validate-st-package.py"
SKILL = ROOT
EXAMPLE = ROOT / "examples/dry-run-盐湖守夜人"
VALIDATOR = ROOT / "scripts" / "validate-contract.py"

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
        self._write("导入说明.txt", "按顺序导；脚本导进「角色脚本」那一栏，不要放全局。"
                            "正则导入时选「角色正则」，进聊天点「允许角色专属正则」。")

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

class TestScriptGoesToCharacterSlot(unittest.TestCase):
    """脚本要导进「角色脚本」，不是全局：全局的存在插件设置里，换张卡照跑。"""

    def test_示例包导入说明点名角色脚本(self):
        text = (EXAMPLE / "导入包" / "导入说明.txt").read_text(encoding="utf-8")
        self.assertIn("角色脚本", text)
        self.assertIn("全局", text, "还要说明为什么不能放全局")

    def test_模板骨架也点名(self):
        text = (SKILL / "templates" / "import-guide.txt").read_text(encoding="utf-8")
        self.assertIn("角色脚本", text)

    def test_C17_缺角色脚本会拦(self):
        with tempfile.TemporaryDirectory() as td:
            proj = pathlib.Path(td) / "p"
            (proj / "制作文件" / "项目记录").mkdir(parents=True)
            (proj / "导入包").mkdir(parents=True)
            src_contract = EXAMPLE / "制作文件" / "项目记录" / "contract.yaml"
            (proj / "制作文件" / "项目记录" / "contract.yaml").write_text(
                src_contract.read_text(encoding="utf-8"), encoding="utf-8")
            for name in ("白潮（纯净）.json", "白潮 世界书.json", "正则.json",
                         "白潮 酒馆助手脚本.json", "白潮 开局前端.html", "白潮 状态栏.html"):
                shutil.copy(EXAMPLE / "导入包" / name, proj / "导入包" / name)
            (proj / "导入包" / "导入说明.txt").write_text("照做就行", encoding="utf-8")
            run = subprocess.run([sys.executable, str(VALIDATOR), str(proj)],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertIn("C17", run.stdout or "")

class TestRegexGoesToCharacterSlot(unittest.TestCase):
    """正则要导进「角色正则」：全局正则会跑到别人的卡上。代价是首次要「允许」，说明里必须写。"""

    def test_示例包导入说明点名角色正则并写了允许(self):
        text = (EXAMPLE / "导入包" / "导入说明.txt").read_text(encoding="utf-8")
        self.assertIn("角色正则", text)
        self.assertIn("允许", text, "S-28：漏点一次，正则永久静默")

    def test_模板骨架也点名(self):
        text = (SKILL / "templates" / "import-guide.txt").read_text(encoding="utf-8")
        self.assertIn("角色正则", text)

    def _proj(self, td, guide_text):
        proj = pathlib.Path(td) / "p"
        (proj / "制作文件" / "项目记录").mkdir(parents=True)
        (proj / "导入包").mkdir(parents=True)
        shutil.copy(EXAMPLE / "制作文件" / "项目记录" / "contract.yaml",
                    proj / "制作文件" / "项目记录" / "contract.yaml")
        for name in ("白潮（纯净）.json", "白潮 世界书.json", "正则.json",
                     "白潮 酒馆助手脚本.json", "白潮 开局前端.html", "白潮 状态栏.html"):
            shutil.copy(EXAMPLE / "导入包" / name, proj / "导入包" / name)
        (proj / "导入包" / "导入说明.txt").write_text(guide_text, encoding="utf-8")
        return proj

    def _run(self, proj):
        return subprocess.run([sys.executable, str(VALIDATOR), str(proj)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_C18_写着全局就拦(self):
        with tempfile.TemporaryDirectory() as td:
            proj = self._proj(td, "脚本导进角色脚本。正则导入时选「全局」。")
            run = self._run(proj)
        self.assertIn("[ FAIL ] C18", run.stdout or "")
        self.assertIn("全局", run.stdout or "")

    def test_C18_写了角色正则但没写允许会警告(self):
        with tempfile.TemporaryDirectory() as td:
            proj = self._proj(td, "脚本导进角色脚本。正则导入时选「角色正则」。")
            run = self._run(proj)
        self.assertIn("[ warn ] C18", run.stdout or "")

    def test_C18_两项都写了就过(self):
        with tempfile.TemporaryDirectory() as td:
            proj = self._proj(td, "脚本导进角色脚本。正则导入时选「角色正则」，进聊天点「允许角色专属正则」。")
            run = self._run(proj)
        self.assertNotIn("[ FAIL ] C18", run.stdout or "")
        self.assertNotIn("[ warn ] C18", run.stdout or "")


class TestMvuEntriesRideTheBook(unittest.TestCase):
    """MVU 三件套留在 制作文件/ 里等于没交：脚本读不到初值、模型收不到更新规则（W25）。"""

    def test_示例包书里有两条MVU条目(self):
        book = json.loads((EXAMPLE / "导入包" / "白潮 世界书.json").read_text(encoding="utf-8"))
        comments = [str(e.get("comment", "")).lower() for e in book["entries"].values()]
        self.assertTrue(any("[initvar]" in c for c in comments), "缺 [initvar]")
        self.assertTrue(any("[mvu_update]" in c for c in comments), "缺 [mvu_update]")

    def test_W25_书里没有MVU条目就拦(self):
        with tempfile.TemporaryDirectory() as td:
            proj = pathlib.Path(td) / "p"
            (proj / "制作文件" / "项目记录").mkdir(parents=True)
            (proj / "导入包").mkdir(parents=True)
            shutil.copy(EXAMPLE / "制作文件" / "项目记录" / "contract.yaml",
                        proj / "制作文件" / "项目记录" / "contract.yaml")
            for name in ("白潮（纯净）.json", "正则.json", "白潮 酒馆助手脚本.json",
                         "白潮 开局前端.html", "白潮 状态栏.html", "导入说明.txt"):
                shutil.copy(EXAMPLE / "导入包" / name, proj / "导入包" / name)
            # 只有设定条目、没有 MVU 条目
            (proj / "导入包" / "白潮 世界书.json").write_text(
                json.dumps({"entries": {"0": {"uid": 0, "key": ["白潮"], "content": "设定",
                                              "comment": "世界规则"}}}, ensure_ascii=False),
                encoding="utf-8")
            run = subprocess.run([sys.executable, str(PACKAGE_SCRIPT), str(proj / "导入包"),
                                  "--contract", str(proj / "制作文件" / "项目记录" / "contract.yaml")],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertIn("W25", run.stdout or "")

class TestFirstMesUi(unittest.TestCase):
    """开局消息同时挂面板和状态栏 → 第一楼多一块 HUD（X08）。"""

    def _run(self, first_mes):
        with tempfile.TemporaryDirectory() as td:
            proj = pathlib.Path(td) / "p"
            (proj / "制作文件" / "项目记录").mkdir(parents=True)
            (proj / "导入包").mkdir(parents=True)
            shutil.copy(EXAMPLE / "制作文件" / "项目记录" / "contract.yaml",
                        proj / "制作文件" / "项目记录" / "contract.yaml")
            for name in ("白潮 世界书.json", "正则.json", "白潮 酒馆助手脚本.json",
                         "白潮 开局前端.html", "白潮 状态栏.html", "导入说明.txt"):
                shutil.copy(EXAMPLE / "导入包" / name, proj / "导入包" / name)
            card = json.loads((EXAMPLE / "导入包" / "白潮（纯净）.json").read_text(encoding="utf-8"))
            card["data"]["first_mes"] = first_mes
            (proj / "导入包" / "白潮（纯净）.json").write_text(
                json.dumps(card, ensure_ascii=False), encoding="utf-8")
            return subprocess.run([sys.executable, str(PACKAGE_SCRIPT), str(proj / "导入包")],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_两样都有会警告(self):
        run = self._run(NL.join(["<开局界面>", "<标题>x</标题>", "</开局界面>", "", "<StatusPlaceHolderImpl/>"]))
        self.assertIn("X08", run.stdout or "")

    def test_只在末行挂状态栏不警告(self):
        run = self._run(NL.join(["<开局界面>", "<标题>x</标题>", "</开局界面>"]))
        self.assertNotIn("X08", run.stdout or "")

    def test_示例包不触发(self):
        with tempfile.TemporaryDirectory() as td:
            run = subprocess.run([sys.executable, str(PACKAGE_SCRIPT), str(EXAMPLE / "导入包")],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertNotIn("X08", run.stdout or "")

class TestCardFieldSplit(unittest.TestCase):
    """X09–X11：description 是总设定、first_mes 是面板、alternate_greetings 是散文开场白。"""

    def _run(self, card_patch):
        with tempfile.TemporaryDirectory() as td:
            proj = pathlib.Path(td) / "p"
            (proj / "制作文件" / "项目记录").mkdir(parents=True)
            (proj / "导入包").mkdir(parents=True)
            shutil.copy(EXAMPLE / "制作文件" / "项目记录" / "contract.yaml",
                        proj / "制作文件" / "项目记录" / "contract.yaml")
            for name in ("白潮 世界书.json", "正则.json", "白潮 酒馆助手脚本.json",
                         "白潮 开局前端.html", "白潮 状态栏.html", "导入说明.txt"):
                shutil.copy(EXAMPLE / "导入包" / name, proj / "导入包" / name)
            card = json.loads((EXAMPLE / "导入包" / "白潮（纯净）.json").read_text(encoding="utf-8"))
            card["data"].update(card_patch)
            (proj / "导入包" / "白潮（纯净）.json").write_text(
                json.dumps(card, ensure_ascii=False), encoding="utf-8")
            return subprocess.run([sys.executable, str(PACKAGE_SCRIPT), str(proj / "导入包")],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_描述结尾是场景动作会警告(self):
        run = self._run({"description": NL.join(["世界设定若干。" * 20, "你把编号牌推进窗口，排在最后一批。"])})
        self.assertIn("X09", run.stdout or "")

    def test_有面板却没开场白会警告(self):
        run = self._run({"first_mes": NL.join(["<开局界面>", "<标题>x</标题>", "</开局界面>"]),
                         "alternate_greetings": []})
        self.assertIn("X10", run.stdout or "")

    def test_面板塞进开场白会失败(self):
        run = self._run({"alternate_greetings": ["散文开场。", NL.join(["<开局界面>", "<标题>x</标题>", "</开局界面>"])]})
        self.assertIn("] X11", run.stdout or "")

    def test_分好字段就不报(self):
        run = self._run({
            "description": NL.join(["世界设定若干。" * 20, "以上是设定，不是示例对话。"]),
            "first_mes": NL.join(["<开局界面>", "<标题>x</标题>", "</开局界面>"]),
            "alternate_greetings": ["配给窗口前的队伍排到门外。<StatusPlaceHolderImpl/>"],
        })
        for code in ("X09", "X10", "X11"):
            self.assertNotIn("[ FAIL ] " + code, run.stdout or "")
            self.assertNotIn("[ warn] " + code, run.stdout or "")

class TestDescriptionNotRepeat(unittest.TestCase):
    """X12：description 每轮都在烧 token，复述世界书就是重复付费。"""

    def _run(self, desc):
        with tempfile.TemporaryDirectory() as td:
            proj = pathlib.Path(td) / "p"
            (proj / "制作文件" / "项目记录").mkdir(parents=True)
            (proj / "导入包").mkdir(parents=True)
            shutil.copy(EXAMPLE / "制作文件" / "项目记录" / "contract.yaml",
                        proj / "制作文件" / "项目记录" / "contract.yaml")
            for name in ("白潮 世界书.json", "正则.json", "白潮 酒馆助手脚本.json",
                         "白潮 开局前端.html", "白潮 状态栏.html", "导入说明.txt"):
                shutil.copy(EXAMPLE / "导入包" / name, proj / "导入包" / name)
            card = json.loads((EXAMPLE / "导入包" / "白潮（纯净）.json").read_text(encoding="utf-8"))
            card["data"]["description"] = desc
            (proj / "导入包" / "白潮（纯净）.json").write_text(
                json.dumps(card, ensure_ascii=False), encoding="utf-8")
            return subprocess.run([sys.executable, str(PACKAGE_SCRIPT), str(proj / "导入包")],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_元话会警告(self):
        run = self._run("一句话世界。怎么玩若干。" + NL.join(["以上是设定，不是示例对话。"] * 1))
        self.assertIn("X12", run.stdout or "")

    def test_复述书里的段落会警告(self):
        book = json.loads((EXAMPLE / "导入包" / "白潮 世界书.json").read_text(encoding="utf-8"))
        chunk = max((str(e.get("content") or "") for e in book["entries"].values()), key=len)[:900]
        run = self._run(NL.join(["一句话世界。", "", chunk, "", "怎么玩若干。"]))
        self.assertIn("X12", run.stdout or "")

    def test_短描述放过(self):
        run = self._run("一句话世界。你刚到堤线，被派去补第七塔的缺。点灯要烧记忆。")
        self.assertNotIn("[ warn] X12", run.stdout or "")

    def test_示例包自身干净(self):
        run = subprocess.run([sys.executable, str(PACKAGE_SCRIPT), str(EXAMPLE / "导入包")],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertNotIn("[ warn] X12", run.stdout or "")
