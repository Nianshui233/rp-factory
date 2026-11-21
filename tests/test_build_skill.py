"""构建脚本的契约：skill 里只该有运行时要用的东西，而文档里提到的文件必须真的在里面。

两件事分开测：
① 白名单——`docs/`、`tests/`、`node_modules/`、`.git/` 不进 skill；
② 引用完整性——`SKILL.md` 与 `references/*.md` 里写成 `templates/x.yaml` 这种路径的，
   构建后必须存在，否则模型照着文档去找会空手。
"""
from __future__ import annotations

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "rp-factory"
ROOT = SKILL
SCRIPT = REPO / "scripts" / "build-skill.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_skill", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BUILD = _load()

# 文档里会写出的路径形态。只认带已知后缀的，避免把散文里的斜杠算进来。
PATH_RE = re.compile(r"`((?:references|templates|scripts|examples)/[^`\s*]+?\.(?:md|yaml|json|js|py|sh|html|ejs|txt))`")


def _doc_texts():
    yield ROOT / "SKILL.md"
    for p in sorted((ROOT / "references").glob("*.md")):
        yield p


class TestWhitelist(unittest.TestCase):
    def test_excludes_dev_material(self):
        files = BUILD.collect(SKILL)
        bad = [rel for rel in files
               if rel.split("/")[0] in {"docs", "tests", "node_modules", ".git", ".superpowers"}]
        self.assertEqual(bad, [])
        # 开发物在仓库根，不在 skill 根本身——skill 根只有这五样
        self.assertEqual(sorted(p.name for p in SKILL.iterdir()),
                         ["SKILL.md", "examples", "references", "scripts", "templates"])

    def test_includes_runtime_material(self):
        files = BUILD.collect(SKILL)
        self.assertIn("SKILL.md", files)
        self.assertIn("references/pipeline.md", files)
        self.assertIn("templates/contract.yaml", files)
        self.assertIn("scripts/validate-contract.py", files)
        self.assertIn("examples/rolecard-minimal.yaml", files)

    def test_no_pycache(self):
        files = BUILD.collect(SKILL)
        self.assertEqual([r for r in files if "__pycache__" in r or r.endswith(".pyc")], [])

    def test_dry_run_examples_not_shipped(self):
        """示例包是给人看的验收示范，1.6 MB，不进 skill。"""
        files = BUILD.collect(SKILL)
        self.assertEqual([r for r in files if r.startswith("examples/") and r.endswith(".md")], [])


class TestReferencedFilesExist(unittest.TestCase):
    def test_every_path_mentioned_in_docs_is_shipped(self):
        files = BUILD.collect(SKILL)
        missing = []
        for doc in _doc_texts():
            for ref in PATH_RE.findall(doc.read_text(encoding="utf-8")):
                if "<" in ref or ">" in ref:  # templates/<type>.yaml 这类占位不是真路径
                    continue
                if ref not in files:
                    missing.append(f"{doc.relative_to(ROOT).as_posix()}: {ref}")
        self.assertEqual(missing, [], "文档提到的文件没进 skill：\n" + "\n".join(missing))


class TestBuildAndCheck(unittest.TestCase):
    def test_build_then_check_is_clean(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "rp-factory"
            self.assertEqual(BUILD.main(["--dest", str(dest)]), 0)
            self.assertTrue((dest / "SKILL.md").is_file())
            self.assertFalse((dest / "docs").exists())
            self.assertFalse((dest / "tests").exists())
            self.assertEqual(BUILD.main(["--dest", str(dest), "--check"]), 0)

    def test_check_detects_drift(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "rp-factory"
            BUILD.main(["--dest", str(dest)])
            # 旧内容
            (dest / "SKILL.md").write_text("旧版本", encoding="utf-8")
            # 多余文件
            (dest / "docs").mkdir()
            (dest / "docs" / "plan.md").write_text("x", encoding="utf-8")
            # 缺文件
            (dest / "references" / "pipeline.md").unlink()
            self.assertEqual(BUILD.main(["--dest", str(dest), "--check"]), 1)

    def test_refuses_to_clear_a_git_repo(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "looks-like-repo"
            (dest / ".git").mkdir(parents=True)
            with self.assertRaises(SystemExit):
                BUILD.main(["--dest", str(dest)])


if __name__ == "__main__":
    unittest.main()
