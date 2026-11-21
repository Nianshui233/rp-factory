"""包自身的结构不变量：防止「文档说一套、文件是另一套」。

这些断言只用文件系统与文本，不跑酒馆、不联网——CI 或改完随手跑一遍都行。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "skills" / "rp-factory"
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
PIPELINE = (ROOT / "references" / "pipeline.md").read_text(encoding="utf-8")

STAGES = ["world", "cast", "scenes", "axes", "mvu", "ejs", "opening", "statusbar", "delivery"]


class TestIndex(unittest.TestCase):
    def test_every_reference_is_indexed(self):
        refs = sorted(p.name for p in (ROOT / "references").glob("*.md"))
        missing = [n for n in refs if n not in SKILL]
        self.assertEqual(missing, [], f"这些 reference 没在 SKILL 索引里出现：{missing}")

    def test_every_template_is_indexed_or_folder_listed(self):
        templates = sorted(p.name for p in (ROOT / "templates").iterdir())
        self.assertTrue(templates)
        # 索引按「templates/*.yaml」这种模式列；只要提及 templates/ 就算覆盖
        self.assertIn("templates/", SKILL)

    def test_every_stage_has_a_file(self):
        # 阶段名与文件名不是一一对应（cast → stage-2-cast.md），以加载表的映射为准
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import measure_load as ml
        self.assertEqual(sorted(ml.LOAD_MAP), sorted(STAGES), "加载表的阶段集合与 pipeline 不一致")
        for stage, filenames in ml.LOAD_MAP.items():
            for filename in filenames:
                self.assertTrue((ROOT / filename).exists(), f"阶段 {stage} 的文件不存在：{filename}")


class TestGates(unittest.TestCase):
    def test_fourteen_gates_numbered_zero_to_thirteen(self):
        numbers = [int(m.group(1)) for m in re.finditer(r"^\*\*(\d+)\. ", PIPELINE, re.M)]
        self.assertEqual(numbers, list(range(14)), f"门编号不连续：{numbers}")

    def test_no_stale_gate_count(self):
        for stale in ("十一道门", "十七道门", "十二道门"):
            self.assertNotIn(stale, SKILL, f"SKILL.md 还在说 {stale}")
            self.assertNotIn(stale, PIPELINE, f"pipeline.md 还在说 {stale}")

    def test_skill_gate_table_matches_pipeline(self):
        # SKILL 的表里每一行都以 | n | 开头；条数必须与 pipeline 一致
        rows = re.findall(r"^\|\s*(\d+)\s*\|\s*`?([^|`]+)`?\s*\|", SKILL, re.M)
        table = [(int(n), name.strip()) for n, name in rows if int(n) < 14]
        self.assertEqual([n for n, _ in table], list(range(14)), table)
        pipeline_names = [m.group(2).strip() for m in
                          re.finditer(r"^\*\*(\d+)\. `([^`]+)`", PIPELINE, re.M)]
        self.assertEqual([name for _, name in table], pipeline_names,
                         "SKILL 索引表的门名与 pipeline 不一致")


class TestScripts(unittest.TestCase):
    def test_referenced_scripts_exist(self):
        referenced = set()
        for md in list((ROOT / "references").glob("*.md")) + [ROOT / "SKILL.md"]:
            text = md.read_text(encoding="utf-8")
            # 排除 public/scripts/xxx.js 这类 ST 源码锚点，只认包自己的 scripts/
            referenced.update(re.findall(r"(?<![\w/])scripts/([\w.\-]+\.(?:py|js|sh))", text))
        # 文档里说明「已删除」的脚本不算引用（迁移说明里会提到）
        blob = "".join(m.read_text(encoding="utf-8") for m in (ROOT / "references").glob("*.md"))
        removed = set(re.findall(r"`scripts/([\w.\-]+\.(?:py|js|sh))`[^\n]*删了", blob))
        missing = [n for n in sorted(referenced - removed) if not (ROOT / "scripts" / n).exists()]
        self.assertEqual(missing, [], f"文档提到但脚本不存在：{missing}")

    def test_every_script_compiles(self):
        import py_compile
        import tempfile
        for script in sorted((ROOT / "scripts").glob("*.py")):
            with tempfile.TemporaryDirectory() as tmp:
                py_compile.compile(str(script), cfile=str(Path(tmp) / "out.pyc"), doraise=True)

    def test_scripts_have_docstrings(self):
        for script in sorted((ROOT / "scripts").glob("*.py")):
            text = script.read_text(encoding="utf-8")
            self.assertIn('"""', text, f"{script.name} 没有模块文档串")


class TestContractTemplate(unittest.TestCase):
    def test_template_lists_decision_states(self):
        text = (ROOT / "templates" / "contract.yaml").read_text(encoding="utf-8")
        for state in ("confirmed", "proposed", "pending", "rejected"):
            self.assertIn(state, text, f"模板没提 decisions 的 {state} 态")

    def test_acceptance_template_lists_layers(self):
        text = (ROOT / "templates" / "acceptance.yaml").read_text(encoding="utf-8")
        self.assertIn("L5", text)
        self.assertIn("human", text)


if __name__ == "__main__":
    unittest.main()
