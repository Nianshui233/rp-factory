"""契约里的 player_agency：演出许可三档，不许从画像细节或沉默推断。

判据来自真机踩坑：人物设定写得再细，也推不出「可以替玩家点头」。所以许可是一个
显式声明（来源、允许内容、排除项、范围、时长），脚本只查它自不自洽。
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "rp-factory" / "scripts" / "validate-contract.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_contract", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.fails.clear()
    mod.warns.clear()
    return mod


def _base(**over):
    c = {
        "project": {"name": "测试", "stages_requested": ["world"]},
        "stages": {"world": "done"},
        "naming": {"world": "测试"},
        "decisions": [],
        "pending": [],
    }
    c.update(over)
    return c


def _codes(mod):
    return [r for r, _ in mod.fails]


class TestPlayerAgency(unittest.TestCase):
    def test_absent_block_is_fine(self):
        """老契约没有这一段：默认 player-controlled，不判失败。"""
        mod = _load()
        mod.check_player_agency(_base())
        self.assertNotIn("C16", _codes(mod))

    def test_default_mode_passes(self):
        mod = _load()
        mod.check_player_agency(_base(player_agency={"mode": "player-controlled"}))
        self.assertNotIn("C16", _codes(mod))

    def test_unknown_mode_fails(self):
        mod = _load()
        mod.check_player_agency(_base(player_agency={"mode": "有时可以"}))
        self.assertIn("C16", _codes(mod))

    def test_limited_needs_allowed(self):
        mod = _load()
        mod.check_player_agency(_base(player_agency={"mode": "limited", "source": "用户确认"}))
        self.assertIn("C16", _codes(mod))

    def test_limited_with_allowed_passes(self):
        mod = _load()
        mod.check_player_agency(_base(player_agency={
            "mode": "limited",
            "allowed": ["收尾句替玩家点头"],
            "source": "用户确认",
        }))
        self.assertNotIn("C16", _codes(mod))

    def test_delegated_needs_duration(self):
        mod = _load()
        mod.check_player_agency(_base(player_agency={
            "mode": "delegated",
            "allowed": ["整段代跑玩家"],
            "source": "用户确认",
        }))
        self.assertIn("C16", _codes(mod))

    def test_relaxed_mode_needs_user_confirmation(self):
        """放宽到 limited / delegated 必须写明是用户定的，不许自己调。"""
        mod = _load()
        mod.check_player_agency(_base(player_agency={
            "mode": "limited",
            "allowed": ["收尾句"],
            "source": "推导",
            "duration": "本次开局",
        }))
        self.assertIn("C16", _codes(mod))

    def test_excluded_is_allowed_on_default(self):
        mod = _load()
        mod.check_player_agency(_base(player_agency={
            "mode": "player-controlled",
            "excluded": ["玩家内心独白", "玩家决定"],
        }))
        self.assertNotIn("C16", _codes(mod))

    def test_not_a_dict_fails(self):
        mod = _load()
        mod.check_player_agency(_base(player_agency="玩家说了算"))
        self.assertIn("C16", _codes(mod))


if __name__ == "__main__":
    unittest.main()
