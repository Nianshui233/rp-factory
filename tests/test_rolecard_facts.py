"""角色卡的事实分级：稳定事实进卡，会过期的进开场或状态层。

理由是实测里最常见的一类死稿：开场那一刻的「正在被追杀」被写成身份设定，
第一轮过去就自相矛盾，而卡已经通过所有结构校验。
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate-rolecard.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_rolecard", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _card(**over):
    c = {
        "character": {
            "name": "白潮",
            "identity": {"age": "24", "gender": "女", "appearance": ["银白短发"],
                         "impression": "看人的时候先看手"},
            "psychology": {
                "motivations": {"goal": "找到哥哥", "drive": "唯一亲人"},
                "fears": {"situation": "变成告密者", "loss": "哥哥的下落"},
                "values": {"ranking": "亲人 > 真相 > 自己", "rationale": "只剩一个人"},
                "taboos": ["绝不交出同伴的位置"],
                "internal_conflict": "真相会伤到哥哥",
            },
            "behavior": {
                "rules": [
                    {"trigger": "有人问哥哥", "action": "岔开话题", "reason": "亲人 > 真相"},
                    {"trigger": "同伴被扣", "action": "立刻换人", "cost": "欠下人情"},
                    {"trigger": "被逼到墙角", "action": "先动手", "condition": "没有退路"},
                    {"trigger": "有人出价买情报", "action": "拒", "reason": "真相 > 钱"},
                ],
                "stress_response": [{"when": "被戳痛处", "reaction": "笑"}, {"when": "危险", "reaction": "安静"},
                                    {"when": "崩溃", "reaction": "不出声"}],
                "quirks": ["转笔", "摸耳", "数台阶"],
            },
            "attitudes": {
                "close_ones": {"behavior": "毒舌让步", "subtext": "掩饰关心", "verbal_change": "叫绰号"},
                "strangers": {"behavior": "客气但保持距离", "subtext": "试探", "verbal_change": "用敬语"},
                "enemies": {"behavior": "先动手", "subtext": "怕被先动手", "verbal_change": "短句"},
                "authority": {"behavior": "表面服从", "subtext": "记仇", "verbal_change": "官方腔"},
            },
            "speech": {
                "style": {"tone": "干", "structure": "短句", "vocabulary": "市井"},
                "rules": [{"kind": "under_pressure", "text": "句子更短"}, {"kind": "when_close", "text": "叫绰号"},
                          {"kind": "conflict", "text": "不说敬语"}, {"kind": "formal", "text": "用官话"}],
                "quotes": [{"line": "走。", "context": "催人"}, {"line": "你猜。", "context": "被问"},
                           {"line": "别碰我。", "context": "被靠近"}],
                "catchphrases": ["走", "别碰", "算了"],
            },
            "background": "渡口长大，哥哥失踪三年。",
            "anti_ooc": {"never": ["绝不交出同伴的位置", "不哭"]},
        }
    }
    for key, value in over.items():
        c["character"][key] = value
    return c


def _run(card):
    mod = _load()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "card.yaml"
        path.write_text(yaml.safe_dump(card, allow_unicode=True), encoding="utf-8")
        return mod.check_file(str(path))


def _msgs(report, kind):
    return getattr(report, kind)


class TestFactStability(unittest.TestCase):
    def test_no_facts_block_is_fine(self):
        """facts 是可选的：不写不报错（精简档常见）。"""
        r = _run(_card())
        self.assertEqual(r.fails, [])

    def test_facts_with_stable_only_passes(self):
        r = _run(_card(facts={"stable": ["银白短发", "左手有旧伤"]}))
        self.assertEqual(r.fails, [])

    def test_facts_must_be_mapping(self):
        r = _run(_card(facts=["银白短发"]))
        self.assertTrue(any("facts" in f for f in r.fails), r.fails)

    def test_unknown_facts_key_fails(self):
        r = _run(_card(facts={"stable": [], "someday": []}))
        self.assertTrue(any("someday" in f for f in r.fails), r.fails)

    def test_temporary_needs_expires_when(self):
        r = _run(_card(facts={"temporary": [{"text": "正在被追杀"}]}))
        self.assertTrue(any("expires_when" in f for f in r.fails), r.fails)

    def test_temporary_with_expires_when_warns_to_move_out(self):
        r = _run(_card(facts={"temporary": [{"text": "正在被追杀", "expires_when": "开场三轮内"}]}))
        self.assertEqual(r.fails, [])
        self.assertTrue(any("开场" in w for w in r.warns), r.warns)

    def test_expiring_state_smuggled_into_identity_warns(self):
        identity = {"age": "24", "gender": "女",
                    "appearance": ["眼下有淤青（正被人追）"],
                    "impression": "此刻正靠在门边喘气"}
        r = _run(_card(identity=identity))
        self.assertTrue(any("临时事实" in w for w in r.warns), r.warns)

    def test_expiring_state_in_background_warns(self):
        r = _run(_card(background="三天前刚从渡口逃出来，现在正被追。"))
        self.assertTrue(any("临时事实" in w for w in r.warns), r.warns)


if __name__ == "__main__":
    unittest.main()
