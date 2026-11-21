"""作品目录布局：根下只许 `制作文件/` 与 `导入包/`，旧布局要拦住（C17）。

背景：交付目录改名前叫 `最终产物/`、制作目录叫 `创作痕迹/`。旧项目原地放着不动时，
脚本照样能跑、界面照样能开，只有人打开文件夹才发现两套名字并存——所以把它变成一道门。
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "rp-factory"
SCRIPT = ROOT / "scripts" / "validate-contract.py"
EXAMPLE = ROOT / "examples/dry-run-盐湖守夜人"


def _load():
    spec = importlib.util.spec_from_file_location("validate_contract_layout", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestLayoutGate(unittest.TestCase):
    def setUp(self):
        self.mod = _load()
        self.mod.fails.clear()
        self.mod.warns.clear()

    def _codes(self):
        return [c for c, _ in self.mod.fails]

    def _warn_codes(self):
        return [c for c, _ in self.mod.warns]

    def test_legacy_work_dir_is_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "创作痕迹").mkdir()
            (root / "导入包").mkdir()
            self.mod.check_layout(root)
        self.assertIn("C17", self._codes())

    def test_legacy_delivery_dir_is_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "制作文件").mkdir()
            (root / "最终产物").mkdir()
            self.mod.check_layout(root)
        self.assertIn("C17", self._codes())

    def test_clean_two_folder_layout_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "制作文件").mkdir()
            (root / "导入包").mkdir()
            self.mod.check_layout(root)
        self.assertEqual(self._codes(), [])
        self.assertEqual(self._warn_codes(), [])

    def test_stray_top_level_file_warns(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "制作文件").mkdir()
            (root / "导入包").mkdir()
            (root / "README.md").write_text("说明", encoding="utf-8")
            self.mod.check_layout(root)
        self.assertIn("C17", self._warn_codes())
        self.assertEqual(self._codes(), [], "散落文件只是警告，不要升级成失败")


class TestExampleLayout(unittest.TestCase):
    def test_example_has_only_two_folders(self):
        entries = sorted(p.name for p in EXAMPLE.iterdir() if not p.name.startswith("."))
        self.assertEqual(entries, ["制作文件", "导入包"])

    def test_ledgers_live_in_record_dir(self):
        record = EXAMPLE / "制作文件" / "项目记录"
        names = sorted(p.name for p in record.iterdir())
        for want in ("contract.yaml", "项目档案.yaml", "创作记录.md", "验收.yaml"):
            self.assertIn(want, names)
        self.assertFalse((EXAMPLE / "制作文件" / "contract.yaml").exists(),
                         "账本不该散在 制作文件/ 根上")

    def test_import_dir_is_flat(self):
        subdirs = [p.name for p in (EXAMPLE / "导入包").iterdir() if p.is_dir()]
        self.assertEqual(subdirs, [], "导入包要平铺，不建分类子目录")


if __name__ == "__main__":
    unittest.main()
