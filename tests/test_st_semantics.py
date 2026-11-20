"""S 系列（ST 静默失效）校验器测试。

只测「会静默失效」的语义，不重复 validate-st-package.py 的结构校验。
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_st_semantics.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_st_semantics", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _card(name="测试世界", world="测试世界 世界书"):
    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": name,
            "description": "描述",
            "personality": "性格",
            "scenario": "场景",
            "first_mes": "开场{{char}}",
            "mes_example": "",
            "creator_notes": "",
            "system_prompt": "",
            "post_history_instructions": "",
            "alternate_greetings": [],
            "tags": [],
            "creator": "",
            "character_version": "1.0",
            "extensions": {"world": world, "regex_scripts": []},
        },
    }


def _book(*entries):
    return {"entries": {str(i): e for i, e in enumerate(entries)}}


def _entry(**over):
    base = {
        "uid": 0, "key": ["钥匙"], "keysecondary": [], "comment": "注释",
        "content": "正文", "constant": False, "vectorized": False, "selective": True,
        "selectiveLogic": 0, "addMemo": True, "order": 100, "position": 0,
        "disable": False, "excludeRecursion": False, "preventRecursion": False,
        "delayUntilRecursion": 0, "probability": 100, "useProbability": True,
        "depth": 4, "outletName": "", "group": "", "groupOverride": False,
        "groupWeight": 100, "scanDepth": None, "caseSensitive": None,
        "matchWholeWords": None, "useGroupScoring": None, "automationId": "",
        "role": 0, "sticky": None, "cooldown": None, "delay": None, "triggers": [],
    }
    base.update(over)
    return base


def _script(**over):
    base = {
        "id": "s1", "scriptName": "状态栏", "findRegex": "/<状态栏>([\\s\\S]*?)<\\/状态栏>/g",
        "replaceString": "<div>$1</div>", "trimStrings": [], "placement": [2],
        "disabled": False, "markdownOnly": True, "promptOnly": False,
        "runOnEdit": True, "substituteRegex": 0, "minDepth": None, "maxDepth": None,
    }
    base.update(over)
    return base


class TestStSemantics(unittest.TestCase):
    def _run(self, card=None, regex=None, book=None, contract=None):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "最终产物").mkdir()
            (root / "最终产物" / "测试世界（纯净）.json").write_text(
                json.dumps(card or _card(), ensure_ascii=False), encoding="utf-8")
            (root / "最终产物" / "正则.json").write_text(
                json.dumps(regex if regex is not None else [_script()], ensure_ascii=False), encoding="utf-8")
            (root / "最终产物" / "测试世界 世界书.json").write_text(
                json.dumps(book or _book(_entry()), ensure_ascii=False), encoding="utf-8")
            if contract is not None:
                (root / "创作痕迹").mkdir()
                (root / "创作痕迹" / "contract.yaml").write_text(contract, encoding="utf-8")
            return mod.check_project(root), root

    def _codes(self, findings, severity="error"):
        return [f["code"] for f in findings if f["severity"] == severity]

    # ---- 干净包 -------------------------------------------------------
    def test_clean_project_has_no_findings(self):
        findings, _ = self._run()
        self.assertEqual(findings, [], findings)

    # ---- S-04 捕获组 --------------------------------------------------
    def test_missing_capture_group_is_error(self):
        findings, _ = self._run(regex=[_script(replaceString="<div>$1 $2</div>")])
        self.assertIn("S-04", self._codes(findings))

    def test_named_group_ok_and_unknown_name_is_error(self):
        ok, _ = self._run(regex=[_script(
            findRegex=r"/<面板>(?<body>[\s\S]*?)<\/面板>/g",
            replaceString="<div>$<body></div>")])
        self.assertEqual(ok, [])
        bad, _ = self._run(regex=[_script(
            findRegex=r"/<面板>(?<body>[\s\S]*?)<\/面板>/g",
            replaceString="<div>$<bod></div>")])
        self.assertIn("S-04", self._codes(bad))

    def test_match_alias_and_dollar_zero_are_allowed(self):
        findings, _ = self._run(regex=[_script(
            findRegex="/<面板>([\\s\\S]*?)<\\/面板>/g",
            replaceString="<div>{{match}}</div>$0")])
        self.assertEqual(findings, [])

    def test_non_capturing_groups_not_counted(self):
        findings, _ = self._run(regex=[_script(
            findRegex=r"/<面板>(?:[\s\S]*?)(a+)<\/面板>/g",
            replaceString="<div>$1</div>")])
        self.assertEqual(findings, [], findings)

    # ---- S-25 方言混用 --------------------------------------------------
    def test_helper_snake_case_keys_are_error(self):
        """助手端的 find_regex / replace_string 写进卡端正则：不报错，只是不生效。"""
        script = _script()
        script.pop("findRegex")
        script["find_regex"] = "/<状态栏>([\s\S]*?)<\/状态栏>/g"
        findings, _ = self._run(regex=[script])
        self.assertIn("S-25", self._codes(findings))

    def test_camel_case_keys_are_fine(self):
        findings, _ = self._run()
        self.assertNotIn("S-25", self._codes(findings))

    # ---- S-26 空替换与缺失替换 -----------------------------------------
    def test_missing_replace_string_is_error(self):
        script = _script()
        script.pop("replaceString")
        findings, _ = self._run(regex=[script])
        self.assertIn("S-26", self._codes(findings))

    def test_empty_replace_string_is_legal(self):
        """空串 = 把匹配到的全删掉，这是合法用法。"""
        findings, _ = self._run(regex=[_script(replaceString="")])
        self.assertNotIn("S-26", self._codes(findings))

    # ---- S-27 空 findRegex ---------------------------------------------
    def test_empty_find_regex_warns(self):
        findings, _ = self._run(regex=[_script(findRegex="")])
        self.assertIn("S-27", self._codes(findings, "warning"))

    # ---- S-28 卡内 scoped 正则 ----------------------------------------
    def test_card_embedded_regex_is_warning(self):
        """卡里带正则 = 要用户点「允许角色专属正则」，而那个弹窗只弹一次。"""
        card = _card()
        card["data"]["extensions"]["regex_scripts"] = [_script()]
        findings, _ = self._run(card=card)
        self.assertIn("S-28", self._codes(findings, "warning"))

    def test_clean_card_has_no_scoped_regex_warning(self):
        findings, _ = self._run()
        self.assertNotIn("S-28", self._codes(findings, "warning"))

    # ---- S-29 内嵌书名与绑定名 ---------------------------------------
    def test_book_name_mismatch_is_error(self):
        card = _card()
        card["data"]["character_book"] = {"name": "别的书", "entries": []}
        findings, _ = self._run(card=card)
        self.assertIn("S-29", self._codes(findings))

    def test_book_name_matches_world_is_fine(self):
        card = _card()
        card["data"]["character_book"] = {"name": "测试世界 世界书", "entries": []}
        findings, _ = self._run(card=card)
        self.assertNotIn("S-29", self._codes(findings) + self._codes(findings, "warning"))

    # ---- S-02 开关组合 ------------------------------------------------
    def test_markdown_only_and_prompt_only_both_true_is_error(self):
        findings, _ = self._run(regex=[_script(markdownOnly=True, promptOnly=True)])
        self.assertIn("S-02", self._codes(findings))

    # ---- S-03 substituteRegex ----------------------------------------
    def test_bad_substitute_regex_is_error(self):
        findings, _ = self._run(regex=[_script(substituteRegex=7)])
        self.assertIn("S-03", self._codes(findings))

    def test_substitute_regex_accepts_numeric_string(self):
        findings, _ = self._run(regex=[_script(substituteRegex="1")])
        self.assertEqual(findings, [], findings)

    # ---- S-07 深度哨兵 -------------------------------------------------
    def test_negative_max_depth_is_dead_rule(self):
        findings, _ = self._run(regex=[_script(maxDepth=-1)])
        self.assertIn("S-07", self._codes(findings))

    def test_min_depth_below_sentinel_is_error(self):
        findings, _ = self._run(regex=[_script(minDepth=-5)])
        self.assertIn("S-07", self._codes(findings))

    # ---- S-10 位置 ----------------------------------------------------
    def test_at_depth_without_depth_is_error(self):
        findings, _ = self._run(book=_book(_entry(position=4, depth=None)))
        self.assertIn("S-10", self._codes(findings))

    def test_outlet_without_name_is_error(self):
        findings, _ = self._run(book=_book(_entry(position=7, outletName="  ")))
        self.assertIn("S-10", self._codes(findings))

    def test_outlet_with_name_is_fine(self):
        findings, _ = self._run(book=_book(_entry(position=7, outletName="state")))
        self.assertEqual(findings, [], findings)

    # ---- S-11 order ---------------------------------------------------
    def test_missing_order_is_error(self):
        entry = _entry()
        del entry["order"]
        findings, _ = self._run(book=_book(entry))
        self.assertIn("S-11", self._codes(findings))

    # ---- S-13 关键词逻辑 ----------------------------------------------
    def test_secondary_keys_ignored_when_not_selective(self):
        findings, _ = self._run(book=_book(_entry(keysecondary=["副"], selective=False)))
        self.assertIn("S-13", self._codes(findings))

    def test_bad_selective_logic_is_error(self):
        findings, _ = self._run(book=_book(_entry(selectiveLogic=9)))
        self.assertIn("S-13", self._codes(findings))

    # ---- S-19 未知宏（警告，不算失败）----------------------------------
    def test_unknown_macro_is_warning_only(self):
        findings, _ = self._run(book=_book(_entry(content="{{fmt_data}}")))
        self.assertEqual(self._codes(findings), [])
        self.assertIn("S-19", self._codes(findings, severity="warning"))

    def test_known_macros_pass(self):
        findings, _ = self._run(book=_book(_entry(content="{{char}} 与 {{user}} {{// 注释}}")))
        self.assertEqual(findings, [])

    # ---- S-20 酒馆助手依赖（需契约）-----------------------------------
    def test_mvu_macro_without_tavern_helper_is_warning(self):
        contract = "project:\n  sillytavern:\n    tavern_helper: false\n"
        findings, _ = self._run(
            book=_book(_entry(content="{{format_message_variable::stat_data}}")),
            contract=contract)
        self.assertIn("S-20", self._codes(findings, severity="warning"))

    def test_mvu_macro_with_tavern_helper_is_fine(self):
        contract = "project:\n  sillytavern:\n    tavern_helper: true\n"
        findings, _ = self._run(
            book=_book(_entry(content="{{format_message_variable::stat_data}}")),
            contract=contract)
        self.assertEqual([f for f in findings if f["code"] == "S-20"], [])

    # ---- 逃生口 -------------------------------------------------------
    def test_report_has_stage_and_message(self):
        findings, _ = self._run(regex=[_script(promptOnly=True, markdownOnly=True)])
        hit = next(f for f in findings if f["code"] == "S-02")
        self.assertIn("message", hit)
        self.assertEqual(hit["file"], "正则.json")


if __name__ == "__main__":
    unittest.main()
