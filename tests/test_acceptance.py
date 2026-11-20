"""验收账本校验器测试：脚本不许自签「真机通过」。"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_acceptance.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_acceptance", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _entry(**over):
    base = {
        "layer": "L2",
        "item": "契约校验",
        "evidence": "python scripts/validate-contract.py … → exit 0",
        "verdict": "pass",
        "by": "script",
    }
    base.update(over)
    return base


def _write(root: Path, entries, raw=None):
    d = root / "创作痕迹"
    d.mkdir(parents=True, exist_ok=True)
    if raw is not None:
        (d / "验收.yaml").write_text(raw, encoding="utf-8")
        return
    import json
    # 用 YAML 兼容的 JSON 超集写入，避免依赖 pyyaml 的 dump
    lines = ["entries:"]
    for e in entries:
        lines.append("  - " + json.dumps(e, ensure_ascii=False))
    (d / "验收.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestAcceptance(unittest.TestCase):
    def _run(self, entries, raw=None):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, entries, raw)
            return mod.check_project(root), root

    def test_clean_ledger_passes(self):
        findings, _ = self._run([
            _entry(),
            _entry(layer="L5", item="酒馆真机导入", verdict="pass", by="human",
                   evidence="手动导入后回读，三件都在；截图 12:31"),
        ])
        self.assertEqual([f for f in findings if f["severity"] == "error"], [], findings)

    def test_unknown_layer_is_error(self):
        findings, _ = self._run([_entry(layer="L9")])
        self.assertIn("A01", [f["code"] for f in findings])

    def test_bad_verdict_is_error(self):
        findings, _ = self._run([_entry(verdict="大概可以")])
        self.assertIn("A02", [f["code"] for f in findings])

    def test_skipped_needs_reason(self):
        findings, _ = self._run([_entry(verdict="skipped")])
        self.assertIn("A02", [f["code"] for f in findings])
        ok, _ = self._run([_entry(verdict="skipped", why="本机没装酒馆助手")])
        self.assertNotIn("A02", [f["code"] for f in ok])

    def test_script_layer_needs_exit_code_evidence(self):
        findings, _ = self._run([_entry(evidence="看起来没问题")])
        self.assertIn("A03", [f["code"] for f in findings])

    def test_real_st_claim_by_script_is_error(self):
        findings, _ = self._run([_entry(layer="L5", by="assistant", evidence="exit 0")])
        self.assertIn("A04", [f["code"] for f in findings])

    def test_human_layer_by_script_is_error(self):
        findings, _ = self._run([_entry(layer="L6", by="script", evidence="exit 0")])
        self.assertIn("A04", [f["code"] for f in findings])

    def test_no_human_check_is_warning(self):
        findings, _ = self._run([_entry()])
        self.assertIn("A05", [f["code"] for f in findings if f["severity"] == "warning"])

    def test_l4_needs_dimension(self):
        findings, _ = self._run([_entry(layer="L4", by="assistant",
                                        evidence="headless 打开后有 1 个 iframe，高 412px")])
        self.assertIn("A06", [f["code"] for f in findings])

    def test_l4_unknown_dimension_is_error(self):
        findings, _ = self._run([_entry(layer="L4", by="assistant", dimension="looks_fine",
                                        evidence="headless 打开后有 1 个 iframe，高 412px")])
        self.assertIn("A06", [f["code"] for f in findings])

    def test_l4_with_dimension_passes(self):
        findings, _ = self._run([
            _entry(layer="L4", by="assistant", dimension="dom",
                   evidence="headless 打开后 1 个 iframe，高 412px，无重复挂载"),
            _entry(layer="L5", item="酒馆真机导入", verdict="pass", by="human",
                   evidence="手动导入后回读，三件都在；截图 12:31"),
        ])
        self.assertNotIn("A06", [f["code"] for f in findings])
        self.assertEqual([f for f in findings if f["severity"] == "error"], [], findings)

    def test_other_layers_do_not_need_dimension(self):
        findings, _ = self._run([_entry()])
        self.assertNotIn("A06", [f["code"] for f in findings])

    def test_missing_ledger_is_error(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            findings = mod.check_project(Path(tmp))
            self.assertIn("A00", [f["code"] for f in findings])

    def test_broken_yaml_is_error(self):
        findings, _ = self._run([], raw="entries: [\n")
        self.assertIn("A00", [f["code"] for f in findings])


if __name__ == "__main__":
    unittest.main()
