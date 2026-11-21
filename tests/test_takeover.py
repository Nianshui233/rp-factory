"""接手别人的包这一页的存在性与关键内容。

它最容易在重构时被当成「多余的一份」删掉——check_structure 只保证「被索引」，
不保证「该说的还在」。
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "rp-factory"


class TestTakeoverDoc(unittest.TestCase):
    def setUp(self):
        self.doc = SKILL / "references" / "takeover.md"
        self.text = self.doc.read_text(encoding="utf-8")

    def test_exists(self):
        self.assertTrue(self.doc.exists(), "references/takeover.md 不见了")

    def test_five_invariants(self):
        for needle in ("原文件字节不动", "快照与工作区分开", "不提原路径", "回读比对", "adapter"):
            self.assertIn(needle, self.text, f"五条不破坏里少了「{needle}」")

    def test_sha256_and_readonly(self):
        self.assertIn("sha256", self.text.lower())
        self.assertIn("只读", self.text)

    def test_indexed_from_skill(self):
        skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("takeover.md", skill_md, "SKILL.md 索引里没有 takeover.md")

    def test_pointed_from_cast_stage(self):
        stage = (SKILL / "references" / "stage-2-cast.md").read_text(encoding="utf-8")
        self.assertIn("takeover.md", stage, "阶段 2 没有指向接手流程")


if __name__ == "__main__":
    unittest.main()
