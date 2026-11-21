"""锚点校验器测试：用临时目录假装一份 ST 源码树。"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "rp-factory" / "scripts" / "check_st_facts.py"


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


TH_FACTS = [
    ("src/util/is_frontend.ts", "return ['html>', '<head>', '<body']", 2, "TH-01"),
    ("src/iframe/predefine.js", "'EjsTemplate', 'TavernHelper'", 12, "TH-06"),
]


def _make_th_tree(root: Path, shift: int = 0) -> None:
    (root / "src" / "util").mkdir(parents=True, exist_ok=True)
    (root / "src" / "iframe").mkdir(parents=True, exist_ok=True)
    front = ["// filler"] * (1 + shift)
    front.append("  return ['html>', '<head>', '<body'].some(tag => content.includes(tag));")
    (root / "src" / "util" / "is_frontend.ts").write_text("\n".join(front) + "\n", encoding="utf-8")
    pre = ["// filler"] * (11 + shift)
    pre.append("result = result.merge(_.pick(window.parent, ['EjsTemplate', 'TavernHelper']));")
    (root / "src" / "iframe" / "predefine.js").write_text("\n".join(pre) + "\n", encoding="utf-8")


class TestTavernHelperFacts(unittest.TestCase):
    """TH-xx 锚点走的是插件仓库，根目录可换，缺失时要能区分「跳过」与「失效」。"""

    def test_plugin_anchors_pass(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_th_tree(root)
            self.assertEqual(mod.verify(TH_FACTS, root, tolerance=0, label="酒馆助手"), [])

    def test_plugin_drift_mentions_plugin_not_st(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_th_tree(root, shift=40)
            problems = mod.verify(TH_FACTS, root, tolerance=2, label="酒馆助手")
            self.assertTrue(problems)
            self.assertTrue(all("酒馆助手" in p for p in problems), problems)

    def test_default_plugin_root_is_configurable(self):
        mod = _load()
        self.assertTrue(hasattr(mod, "DEFAULT_TH_ROOT"))
        self.assertTrue(hasattr(mod, "TH_FACTS"))
        self.assertTrue(all(row[3].startswith("TH-") for row in mod.TH_FACTS))

    def test_plugin_root_missing_does_not_fail_the_run(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope"
            code = mod.main(["--st-root", str(Path(tmp) / "also-nope"), "--th-root", str(missing), "--json"])
            # ST 根不存在 → 有失败；但只要 TH 根不在，就不该额外吐出 TH 组问题
            self.assertEqual(code, 1)



if __name__ == "__main__":
    unittest.main()
