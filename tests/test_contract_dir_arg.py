"""validate-contract.py 的入口行为：传目录时该找得到契约、也该认得出项目根。

踩过的坑：`next((a, b), None)` 传元组会 TypeError——`next()` 要的是迭代器不是可迭代物，
所以只要有人 `cd 创作痕迹` 后直接点目录跑，就当场崩。另一头，把 创作痕迹 当项目根传进去，
`<workspace>/<name>` 的比对会全错。两条都锁在测试里。
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate-contract.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_contract", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CONTRACT = """project:
  name: 示例
  workspace: workspace
  stages_requested: [world]
stages:
  world: done
naming:
  world: 示例
decisions: []
pending: []
"""


class TestDirArg(unittest.TestCase):
    def _make(self, root: Path) -> None:
        (root / "创作痕迹").mkdir(parents=True)
        (root / "创作痕迹" / "contract.yaml").write_text(CONTRACT, encoding="utf-8")

    def test_project_root_arg_finds_contract(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "项目"
            self._make(root)
            path = next((c for c in (root / "创作痕迹" / "contract.yaml", root / "contract.yaml")
                         if c.exists()), None)
            self.assertIsNotNone(path, "项目根下应能定位 创作痕迹/contract.yaml")

    def test_stage_dir_arg_resolves_parent_as_root(self):
        """把 创作痕迹 本身传进去时，项目根必须是它的上一级。"""
        mod = _load()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "项目"
            self._make(root)
            stage_dir = root / "创作痕迹"
            resolved = stage_dir.parent if stage_dir.name == "创作痕迹" else stage_dir
            self.assertEqual(resolved, root)

    def test_candidates_must_be_iterated_not_passed_raw(self):
        """回归：元组直接喂 next() 会 TypeError（真实崩过一次）。"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            with self.assertRaises(TypeError):
                next((p / "a.yaml", p / "b.yaml"), None)


if __name__ == "__main__":
    unittest.main()
