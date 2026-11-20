"""check_prose.py（P01–P09）测试：每条规则都要「该响时响、不该响时安静」。"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_prose.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_prose", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GOOD = """她把手收回袖子里，指尖还在抖。

「别站在风口。」他说，把门带上。

屋里比外面暗，炉子上坐着水，壶盖被顶得一跳一跳。
"""

BAD_DASH = """他看着她——他知道她在想什么——那是一种说不清的感觉——他决定不再问了。
"""

BAD_TELL = """他感到一阵恐惧，不禁后退了一步，心里涌起某种说不出的滋味。
"""

BAD_CLICHE = """她的眼睛像星星一样闪亮，时间仿佛静止，空气仿佛凝固了。
"""

BAD_TAG = """「你来了。」他淡淡地说道。

「嗯。」她冷冷地道。

「坐吧。」他轻轻地说。
"""

BAD_PARALLEL = """这不是勇气，而是固执；不是坚持，而是执念。
"""

BAD_ENDING = """这一刻，他终于明白了。

或许，一切都还来得及。
"""

ABS_ONLY = """守夜人一律不离开岗位。
闸门一定是闭着的，所有船都过不去。
任何人不许进闸区。
每个人都记得那条规矩。
"""

ABS_WITH_HEDGE = """守夜人通常不离开岗位。
闸门多数时候闭着，偶尔会开半边。
大多数人都进不去，可是巡夜人有钥匙。
那条路往往封锁。
"""

ABS_STACKED = """所有人都一定记得那一天，绝不会有例外。
"""


class TestProseRules(unittest.TestCase):
    def test_clean_text_has_no_findings(self):
        mod = _load()
        self.assertEqual(mod.check_text(GOOD), [])

    def test_dash_explanation_cluster(self):
        mod = _load()
        codes = {f["code"] for f in mod.check_text(BAD_DASH)}
        self.assertIn("P01", codes)

    def test_tell_not_show(self):
        mod = _load()
        codes = {f["code"] for f in mod.check_text(BAD_TELL)}
        self.assertTrue({"P02", "P03"} & codes, codes)

    def test_cliche_metaphor(self):
        mod = _load()
        codes = {f["code"] for f in mod.check_text(BAD_CLICHE)}
        self.assertIn("P05", codes)

    def test_monotonous_dialogue_tags(self):
        mod = _load()
        codes = {f["code"] for f in mod.check_text(BAD_TAG)}
        self.assertIn("P07", codes)

    def test_parallel_summary(self):
        mod = _load()
        codes = {f["code"] for f in mod.check_text(BAD_PARALLEL)}
        self.assertIn("P04", codes)

    def test_section_closing_lines(self):
        mod = _load()
        codes = {f["code"] for f in mod.check_text(BAD_ENDING)}
        self.assertIn("P06", codes)

    def test_code_fences_and_tables_are_skipped(self):
        mod = _load()
        text = "```\n他感到一阵恐惧——不禁后退\n```\n\n| 他感到 | 恐惧 |\n"
        self.assertEqual(mod.check_text(text), [])

    def test_single_dash_is_fine(self):
        mod = _load()
        self.assertEqual(mod.check_text("他停了一下——然后走了。"), [])

    def test_cli_json_and_exit_codes(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.md"
            good.write_text(GOOD, encoding="utf-8")
            bad = Path(tmp) / "bad.md"
            bad.write_text(BAD_DASH + BAD_TELL, encoding="utf-8")
            self.assertEqual(mod.main([str(good)]), 0)
            self.assertEqual(mod.main([str(bad)]), 0)          # 默认只警告
            self.assertEqual(mod.main([str(bad), "--strict"]), 1)
            json.dump({}, open(Path(tmp) / "x.json", "w"))
            self.assertEqual(mod.main([str(bad), "--json"]), 0)

    def test_absolute_without_hedge_is_flagged(self):
        mod = _load()
        codes = {f["code"] for f in mod.check_text(ABS_ONLY)}
        self.assertIn("P09", codes)

    def test_absolute_with_hedges_is_quiet(self):
        mod = _load()
        codes = {f["code"] for f in mod.check_text(ABS_WITH_HEDGE)}
        self.assertNotIn("P09", codes)

    def test_absolute_stacked_in_one_sentence_is_flagged(self):
        mod = _load()
        codes = {f["code"] for f in mod.check_text(ABS_STACKED)}
        self.assertIn("P09", codes)

    def test_findings_have_location(self):
        mod = _load()
        hits = mod.check_text(BAD_TELL)
        self.assertTrue(hits)
        self.assertIn("line", hits[0])
        self.assertIn("message", hits[0])

    # ———— 免疫区：真机包（14 张卡）测出来的误报 ————

    def test_rolecard_taboos_are_not_absolute_flags(self):
        """人物设定的 anti_ooc / taboos 里写「绝不」「一定」是设定，不是八股。"""
        mod = _load()
        text = """identity:
  name: 张伟
  anti_ooc:
    always:
      - "答应的事一定做到，做不到会提前赔不是"
    never:
      - "绝不说自己没有把握的话，说了就一定做到"
      - "绝不白拿别人的东西，一顿饭也要还"
      - "绝不在别人有难的时候谈条件"
"""
        self.assertEqual([f["code"] for f in mod.check_text(text) if f["code"] == "P09"], [])

    def test_habits_with_always_are_not_flags(self):
        """习惯写成「一定/每次」本来就是对的：频率即设定。"""
        mod = _load()
        text = """habits:
  - "凌晨十二点前十分钟一定在看表"
  - "说谎时那句话一定加个『真的』"
  - "紧张时把所有杯子摆成一条线"
"""
        self.assertEqual([f["code"] for f in mod.check_text(text) if f["code"] == "P09"], [])

    def test_world_text_still_flags_absolutes(self):
        """免疫只对设定块生效：世界正文里把倾向写成绝对，照样要报。"""
        mod = _load()
        text = """geography:
  content: "所有商队一律绕行北道，任何人不得走盐径，每个人都记得那次塌方。"
"""
        self.assertTrue([f for f in mod.check_text(text) if f["code"] == "P09"])

    def test_dialogue_first_person_feeling_is_not_tell(self):
        """「我觉得这样比较好」是台词，不是叙述替角色报情绪。"""
        mod = _load()
        text = """mes_example: |
  {{user}}: 要不要换个地方？
  {{char}}: "我觉得这样比较好。"
"""
        self.assertEqual([f["code"] for f in mod.check_text(text) if f["code"] == "P03"], [])


if __name__ == "__main__":
    unittest.main()
