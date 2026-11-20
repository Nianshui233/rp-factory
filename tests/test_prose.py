"""check_prose.py（P01–P08）测试：每条规则都要「该响时响、不该响时安静」。"""
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

    def test_findings_have_location(self):
        mod = _load()
        hits = mod.check_text(BAD_TELL)
        self.assertTrue(hits)
        self.assertIn("line", hits[0])
        self.assertIn("message", hits[0])


if __name__ == "__main__":
    unittest.main()
