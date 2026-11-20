"""锚点校验器测试：用临时目录假装一份 ST 源码树。"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_st_facts.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_st_facts", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_tree(root: Path, engine_lines: int, needle_line: int) -> None:
    regex_dir = root / "public" / "scripts" / "extensions" / "regex"
    regex_dir.mkdir(parents=True)
    body = ["// filler"] * engine_lines
    body[needle_line - 1] = "export const regex_placement = {"
    (regex_dir / "engine.js").write_text("\n".join(body), encoding="utf-8")
    (root / "public" / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "public" / "scripts" / "world-info.js").write_text(
        "\n".join(["// filler"] * 32 + ["export const world_info_logic = {"]), encoding="utf-8")
    (root / "public" / "script.js").write_text(
        "\n".join(["// filler"] * 493 + ["export const extension_prompt_roles = {"]), encoding="utf-8")
    (root / "public" / "scripts" / "macros.js").write_text(
        "\n".join(["// filler"] * 609 + ["export function evaluateMacros(content, env, postProcessFn)"]),
        encoding="utf-8")


MINE = [
    ("public/scripts/extensions/regex/engine.js", "export const regex_placement = {", 281),
    ("public/scripts/world-info.js", "export const world_info_logic = {", 33),
    ("public/script.js", "export const extension_prompt_roles = {", 494),
    ("public/scripts/macros.js", "export function evaluateMacros(content, env, postProcessFn)", 610),
]


class TestCheckStFacts(unittest.TestCase):
    def test_exact_anchors_pass(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_tree(root, engine_lines=300, needle_line=281)
            problems = mod.verify(MINE, root, tolerance=0)
            self.assertEqual(problems, [], problems)

    def test_drift_beyond_tolerance_is_reported(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_tree(root, engine_lines=300, needle_line=250)
            problems = mod.verify(MINE, root, tolerance=5)
            self.assertEqual(len(problems), 1, problems)
            self.assertIn("S", problems[0] + "S")
            self.assertIn("250", problems[0])

    def test_drift_within_tolerance_passes(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_tree(root, engine_lines=300, needle_line=285)
            self.assertEqual(mod.verify(MINE, root, tolerance=10), [])

    def test_missing_file_is_reported_not_raised(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            problems = mod.verify(MINE, Path(tmp), tolerance=5)
            self.assertTrue(problems)
            self.assertTrue(all("不存在" in p for p in problems))

    def test_missing_needle_is_reported(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_tree(root, engine_lines=300, needle_line=281)
            rows = MINE + [("public/scripts/extensions/regex/engine.js", "export const never_there = 1", 10)]
            problems = mod.verify(rows, root, tolerance=0)
            self.assertEqual(len(problems), 1)
            self.assertIn("找不到", problems[0])


if __name__ == "__main__":
    unittest.main()
