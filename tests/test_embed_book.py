"""embed-book.py：内嵌书后必须能被 ST 的 convertCharacterBook 原样读回来。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "embed-book.py"

_spec = importlib.util.spec_from_file_location("embed_book", SCRIPT)
eb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eb)


def make_card(world: str = "白潮 世界书") -> dict:
    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "name": "白潮",
        "description": "骨架",
        "first_mes": "开场",
        "data": {
            "name": "白潮",
            "description": "骨架",
            "first_mes": "开场",
            "extensions": {"world": world, "talkativeness": "0.5"},
        },
    }


def make_book() -> dict:
    return json.loads((ROOT / "templates" / "st-worldbook.json").read_text(encoding="utf-8"))


class TestRoundTrip(unittest.TestCase):
    def test_template_book_survives_round_trip(self):
        book = make_book()["entries"]
        card = make_card()
        card["character_book"] = eb.native_to_v2(book, "白潮 世界书")
        card["data"]["character_book"] = card["character_book"]
        self.assertEqual(eb.verify(book, card), [])

    def test_position_zero_becomes_before_char(self):
        v2 = eb.native_to_v2(make_book()["entries"], "书")
        self.assertEqual(v2["entries"][0]["position"], "before_char")
        self.assertEqual(v2["entries"][0]["extensions"]["position"], 0)

    def test_depth_position_kept_in_extensions(self):
        entries = {"0": {"uid": 0, "key": ["a"], "content": "x", "position": 4, "depth": 2}}
        v2 = eb.native_to_v2(entries, "书")
        self.assertEqual(v2["entries"][0]["position"], "after_char")
        self.assertEqual(v2["entries"][0]["extensions"]["position"], 4)
        self.assertEqual(eb.convert_character_book(v2)[0]["position"], 4)

    def test_disabled_entry_maps_to_enabled_false(self):
        entries = {"0": {"uid": 0, "content": "x", "disable": True}}
        v2 = eb.native_to_v2(entries, "书")
        self.assertFalse(v2["entries"][0]["enabled"])
        self.assertTrue(eb.convert_character_book(v2)[0]["disable"])

    def test_keys_and_secondary_keys_renamed(self):
        entries = {"0": {"uid": 0, "key": ["甲", "乙"], "keysecondary": ["丙"]}}
        v2 = eb.native_to_v2(entries, "书")
        self.assertEqual(v2["entries"][0]["keys"], ["甲", "乙"])
        self.assertEqual(v2["entries"][0]["secondary_keys"], ["丙"])

    def test_verify_catches_a_field_st_ignores(self):
        entries = {"0": {"uid": 0, "content": "x", "position": 4, "depth": 2}}
        card = make_card()
        card["character_book"] = eb.native_to_v2(entries, "书")
        card["data"]["character_book"] = card["character_book"]
        # 人为破坏：ST 只读 extensions.position，改 v2 的 position 字符串无效
        card["data"]["character_book"]["entries"][0]["extensions"]["position"] = 1
        self.assertTrue(eb.verify(entries, card))


class TestCli(unittest.TestCase):
    def _write(self, tmp: Path, card: dict, book: dict) -> tuple[Path, Path]:
        c = tmp / "卡.json"
        b = tmp / "书.json"
        c.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
        b.write_text(json.dumps(book, ensure_ascii=False), encoding="utf-8")
        return c, b

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), *args],
                              capture_output=True, text=True, encoding="utf-8")

    def test_writes_both_top_level_and_data(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            c, b = self._write(tmp, make_card(), make_book())
            out = tmp / "out.json"
            r = self.run_cli("--card", str(c), "--book", str(b), "--out", str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            card = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(card["character_book"], card["data"]["character_book"])
            self.assertEqual(len(card["data"]["character_book"]["entries"]), len(make_book()["entries"]))

    def test_refuses_array_shaped_book(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            v2book = {"entries": [{"keys": ["a"], "content": "x"}]}
            c, b = self._write(tmp, make_card(), v2book)
            r = self.run_cli("--card", str(c), "--book", str(b), "--out", str(tmp / "o.json"))
            self.assertEqual(r.returncode, 2)
            self.assertIn("native", r.stderr)

    def test_refuses_v1_card(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            old = {"name": "老卡", "description": "x"}
            c, b = self._write(tmp, old, make_book())
            r = self.run_cli("--card", str(c), "--book", str(b), "--out", str(tmp / "o.json"))
            self.assertEqual(r.returncode, 2)

    def test_requires_out_or_in_place(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            c, b = self._write(tmp, make_card(), make_book())
            r = self.run_cli("--card", str(c), "--book", str(b))
            self.assertEqual(r.returncode, 2)

    def test_warns_when_world_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            card = make_card(world="")
            c, b = self._write(tmp, card, make_book())
            r = self.run_cli("--card", str(c), "--book", str(b), "--out", str(tmp / "o.json"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("extensions.world", r.stderr)


if __name__ == "__main__":
    unittest.main()
