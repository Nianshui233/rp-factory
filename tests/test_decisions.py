"""契约里 decisions / pending 的新纪律：四态 + partial 必须挂 pending。"""
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
        "stages": {1: "done"},
        "naming": {"world": "测试"},
        "decisions": [],
        "pending": [],
    }
    c.update(over)
    return c


def _rules(mod):
    return [r for r, _ in mod.fails]


class TestDecisionStates(unittest.TestCase):
    def test_four_states_are_accepted(self):
        mod = _load()
        c = _base(decisions=[
            {"item": "数值上限", "choice": "100", "state": "confirmed"},
            {"item": "结局走向", "choice": "开放", "state": "proposed", "why": "用户没答"},
            {"item": "阵营名", "choice": "待定", "state": "pending"},
            {"item": "双主角", "choice": "否", "state": "rejected", "why": "用户否掉"},
        ])
        mod.check_lists(c)
        self.assertNotIn("C13", _rules(mod), mod.fails)

    def test_unknown_state_is_rejected(self):
        mod = _load()
        c = _base(decisions=[{"item": "数值上限", "choice": "100", "state": "maybe"}])
        mod.check_lists(c)
        self.assertIn("C13", _rules(mod))

    def test_state_is_optional_for_legacy_entries(self):
        mod = _load()
        c = _base(decisions=[{"item": "数值上限", "choice": "100"}])
        mod.check_lists(c)
        self.assertNotIn("C13", _rules(mod))

    def test_proposed_requires_why(self):
        mod = _load()
        c = _base(decisions=[{"item": "结局走向", "choice": "开放", "state": "proposed"}])
        mod.check_lists(c)
        self.assertIn("C13", _rules(mod))

    def test_unanswered_must_not_be_confirmed(self):
        mod = _load()
        c = _base(decisions=[{
            "item": "结局走向", "choice": "开放", "state": "confirmed",
            "answer": "用户没有回答",
        }])
        mod.check_lists(c)
        self.assertIn("C13", _rules(mod), "把『没回答』记成 confirmed 就是伪造签字")


class TestPartialNeedsPending(unittest.TestCase):
    def test_partial_without_pending_item_fails(self):
        mod = _load()
        c = _base(stages={1: "partial"})
        mod.check_stages(c)
        self.assertIn("C14", _rules(mod))

    def test_partial_with_matching_pending_item_passes(self):
        mod = _load()
        c = _base(stages={1: "partial"}, pending=[{"stage": 1, "item": "第三势力的目的"}])
        mod.check_stages(c)
        self.assertNotIn("C14", _rules(mod))

    def test_done_stage_needs_no_pending(self):
        mod = _load()
        c = _base(stages={1: "done"})
        mod.check_stages(c)
        self.assertNotIn("C14", _rules(mod))


if __name__ == "__main__":
    unittest.main()
