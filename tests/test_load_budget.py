import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ml = load("measure_load", "scripts/measure_load.py")


class TestLoadBudget(unittest.TestCase):
    def test_every_stage_under_absolute_cap(self):
        rows = ml.report()
        self.assertIn("cast", dict(rows))
        for stage, tok in rows:
            self.assertLessEqual(tok, ml.MAX_STAGE_TOKENS, f"{stage} 超绝对上限：{tok}")

    def test_no_stage_grows_beyond_baseline(self):
        for stage, tok in ml.report():
            self.assertLessEqual(
                tok, ml.BASELINE[stage], f"{stage} 变重了：{tok} > 基线 {ml.BASELINE[stage]}"
            )

    def test_skill_md_under_cap(self):
        self.assertLessEqual(ml.estimate(["SKILL.md"]), 6600)

    def test_pipeline_under_cap(self):
        self.assertLessEqual(ml.estimate(["references/pipeline.md"]), 4700)

    def test_all_paths_exist(self):
        for paths in [ml.ALWAYS, *ml.LOAD_MAP.values()]:
            for p in paths:
                self.assertTrue((ROOT / p).exists(), p)

    def test_baseline_covers_every_stage(self):
        self.assertEqual(sorted(ml.BASELINE), sorted(ml.LOAD_MAP))


if __name__ == "__main__":
    unittest.main()
