"""W19–W22：关键词宽度、`@@` 装饰器、常驻条目的递归扇出。

这四条都来自同一个观察：世界书里最贵的失败不是"报错"，是"看起来正常但行为不对"。

- W19 单字关键词（`他`、`月`）在任何句子里都成立，`include_names` 关着时
  一条 3k 字的角色条目就靠一个"他"被拉进上下文；
- W20 短词是别条长词的子串（`灯油` ⊂ `灯油税`），提到长词时短词那条也一起亮；
- W21 正文以 `@@` 开头会被 `parseDecorators`（`world-info.js:4655`）当装饰器剥掉，
  第一段凭空消失，而且不报错；
- W22 常驻条目正文里点了别的条目的关键词，递归一开它每轮都在，等于永久点亮器。
"""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "rp-factory"
SCRIPT = ROOT / "scripts" / "validate-st-package.py"
EXAMPLE = ROOT / "examples/dry-run-盐湖守夜人/导入包/白潮 世界书.json"


def _load():
    spec = importlib.util.spec_from_file_location("validate_st_package_tuning", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def entry(content: str, *, keys=None, constant=False, comment="条目",
          exclude_recursion=True, prevent_recursion=False, **extra):
    """按 ST 的 newWorldInfoEntryDefinition 造一条，缺什么补什么。"""
    e = {
        "uid": 0, "key": keys or [], "keysecondary": [], "comment": comment, "content": content,
        "constant": constant, "vectorized": False, "selective": True, "selectiveLogic": 0,
        "addMemo": True, "order": 100, "position": 0, "disable": False, "ignoreBudget": False,
        "excludeRecursion": exclude_recursion, "preventRecursion": prevent_recursion,
        "matchPersonaDescription": False, "matchCharacterDescription": False,
        "matchCharacterPersonality": False, "matchCharacterDepthPrompt": False,
        "matchScenario": False, "matchCreatorNotes": False, "delayUntilRecursion": False,
        "probability": 100, "useProbability": True, "depth": 4, "outletName": "",
        "group": "", "groupOverride": False, "groupWeight": 100, "scanDepth": None,
        "caseSensitive": None, "matchWholeWords": False, "useGroupScoring": None,
        "automationId": "", "role": None, "sticky": 0, "cooldown": 0, "delay": 0,
        "triggers": [],
    }
    e.update(extra)
    return e


def book(*entries):
    out = {}
    for i, e in enumerate(entries):
        e = dict(e)
        e["uid"] = i
        out[str(i)] = e
    return {"entries": out}


def run(b):
    rep = mod.Report()
    mod.validate_worldbook(b, Path("白潮 世界书.json"), rep)
    return rep


def codes(rep, level=None):
    return [c for l, c, _ in rep.items if level is None or l == level]


def msgs(rep, code):
    return [m for l, c, m in rep.items if c == code]


class TestShortKeys(unittest.TestCase):
    def test_single_char_key_warns(self):
        rep = run(book(entry("祁昭是守塔人。", keys=["祁昭", "他"])))
        self.assertIn("W19", codes(rep, "WARN"))
        self.assertIn("他", msgs(rep, "W19")[0])

    def test_two_char_key_is_fine(self):
        rep = run(book(entry("祁昭是守塔人。", keys=["祁昭", "塔顶", "白盐镇"])))
        self.assertNotIn("W19", codes(rep))


class TestSubstringKeys(unittest.TestCase):
    def test_cross_entry_substring_warns(self):
        rep = run(book(
            entry("灯油税按灯芯算。", keys=["灯油税"]),
            entry("灯油是配给制的。", keys=["灯油"]),
        ))
        self.assertIn("W20", codes(rep, "WARN"))
        self.assertIn("灯油 ⊂ 灯油税", msgs(rep, "W20")[0])

    def test_same_entry_substring_is_silent(self):
        rep = run(book(entry("白盐镇与盐镇是同义。", keys=["白盐镇", "盐镇"])))
        self.assertNotIn("W20", codes(rep))

    def test_long_pair_without_containment_is_silent(self):
        rep = run(book(entry("盐潮按潮历记。", keys=["盐潮记录"]),
                       entry("落潮最贵。", keys=["落潮"])))
        self.assertNotIn("W20", codes(rep))


class TestDecorators(unittest.TestCase):
    def test_at_prefix_fails(self):
        rep = run(book(entry("@@activate\n守夜所不许点灯。", keys=["守夜所"])))
        self.assertIn("W21", codes(rep, "FAIL"))

    def test_escaped_at_prefix_only_warns(self):
        rep = run(book(entry("@@@未定义标记写在正文里。", keys=["守夜所"])))
        self.assertIn("W21", codes(rep, "WARN"))
        self.assertNotIn("W21", codes(rep, "FAIL"))

    def test_mid_text_at_is_fine(self):
        rep = run(book(entry("守夜所的规矩 @@ 只写在末尾。", keys=["守夜所"])))
        self.assertNotIn("W21", codes(rep))


class TestConstantFanout(unittest.TestCase):
    def test_constant_naming_another_key_warns(self):
        rep = run(book(
            entry("信息分层：守夜所的人不多话。", constant=True, prevent_recursion=False),
            entry("守夜所里点灯要报备。", keys=["守夜所"]),
        ))
        self.assertIn("W22", codes(rep, "WARN"))
        self.assertIn("守夜所", msgs(rep, "W22")[0])

    def test_constant_with_prevent_recursion_is_silent(self):
        rep = run(book(
            entry("信息分层：守夜所的人不多话。", constant=True, prevent_recursion=True),
            entry("守夜所里点灯要报备。", keys=["守夜所"]),
        ))
        self.assertNotIn("W22", codes(rep))

    def test_single_char_key_does_not_count_for_fanout(self):
        rep = run(book(
            entry("信息分层：全凭他一个人撑着。", constant=True, prevent_recursion=False),
            entry("祁昭是守塔人。", keys=["祁昭", "他"]),
        ))
        self.assertNotIn("W22", codes(rep))


class TestExamplePackage(unittest.TestCase):
    """示例包是世界书规则的公开样例，它自己必须干净。"""

    def test_example_book_has_no_tuning_warnings(self):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        rep = run(data)
        for code in ("W19", "W20", "W21", "W22"):
            self.assertNotIn(code, codes(rep), f"示例包触发了 {code}：{msgs(rep, code)}")

    def test_example_constants_prevent_recursion(self):
        data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        for uid, e in data["entries"].items():
            if e.get("constant"):
                self.assertIs(e.get("preventRecursion"), True, f"常驻条目 {uid} 缺 preventRecursion")


class TestDatabaseEntries(unittest.TestCase):
    """资料库式：disable 的 [data]/[阶段] 条目 + 控制器 getwi() 取用。两条断链点各一条规则。"""

    def test_controller_referencing_missing_entry_fails(self):
        rep = run(book(
            entry("<%- await getwi(null, '[data]人物·尾张') %>", constant=True, prevent_recursion=True),
        ))
        self.assertIn("W24", codes(rep, "FAIL"))
        self.assertIn("[data]人物·尾张", msgs(rep, "W24")[0])

    def test_controller_referencing_existing_entry_is_silent(self):
        rep = run(book(
            entry("<%- await getwi(null, '[data]人物·尾张') %>", constant=True, prevent_recursion=True),
            entry("织田信长在此。", comment="[data]人物·尾张", disable=True),
        ))
        self.assertNotIn("W24", codes(rep))
        self.assertNotIn("W23", codes(rep))

    def test_orphan_data_entry_warns(self):
        rep = run(book(
            entry("没人取我。", comment="[data]城池·尾张", disable=True),
        ))
        self.assertIn("W23", codes(rep, "WARN"))
        self.assertIn("[data]城池·尾张", msgs(rep, "W23")[0])

    def test_disabled_protocol_entry_is_exempt(self):
        """协议条目（[initvar] / [statusbar] / [mvu]…）由脚本读，不经 getwi，不该被 W23 抓。"""
        rep = run(book(
            entry("变量初始化。", comment="[initvar]变量初始化", disable=True),
            entry("状态栏协议。", comment="[statusbar]状态栏协议", disable=True),
        ))
        self.assertNotIn("W23", codes(rep))

    def test_cross_book_reference_is_not_checked(self):
        rep = run(book(
            entry("<%- await getwi('别人的书', '[data]人物·尾张') %>", constant=True, prevent_recursion=True),
        ))
        self.assertNotIn("W24", codes(rep))


if __name__ == "__main__":
    unittest.main()
