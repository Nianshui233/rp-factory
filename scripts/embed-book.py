#!/usr/bin/env python3
"""把 native 世界书内嵌进角色卡（`character_book`），做「双入口」交付的第二个口。

为什么要这个开关：`references/stage-7-delivery.md` 默认只出「世界书单独一份 + 卡里写
`extensions.world` 靠同名自动挂」。但 ST 另有一条路——卡里带 `data.character_book`，
打开角色卡时会提示「Import Card Lore」，导入后按书里 `name` 或 `<角色名>'s Lorebook`
建书并自动挂到这张卡上（`public/scripts/world-info.js:5690 checkEmbeddedWorld`、
`:5730 importEmbeddedWorldInfo`、`:5617 convertCharacterBook`）。单文件交付就靠它。

两个口子都有代价，别混着说：
- 外挂书：改设定要重导两份，卡与书可能版本不一致。
- 内嵌书：**卡选中世界书为空时保存，ST 会把 `data.character_book` 删掉**
  （`public/scripts/world-info.js:6105-6114` 的 "Dirty hack"），所以内嵌之后必须让
  `extensions.world` 指向导入后的书名，否则下次保存就丢；
  另外内嵌后书名叫 `<角色名>'s Lorebook`（除非 `character_book.name` 自己写了），
  与 `<世界名> 世界书` 不是同一个名字。

用法：
    python scripts/embed-book.py --card 卡.json --book 世界书.json --out 卡（内嵌书）.json
    python scripts/embed-book.py --card 卡.json --book 世界书.json --in-place
    python scripts/embed-book.py --card 卡.json --book 世界书.json --out x.json --dry-run

退出码：0 成功且回读一致；1 回读有字段不一致（已写文件）；2 参数/输入错误。
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

# convertCharacterBook 会读的这些字段：native → v2/extensions（反向映射时逐条对应）
TO_EXT = {
    "excludeRecursion": "exclude_recursion",
    "preventRecursion": "prevent_recursion",
    "delayUntilRecursion": "delay_until_recursion",
    "displayIndex": "display_index",
    "probability": "probability",
    "useProbability": "useProbability",
    "depth": "depth",
    "selectiveLogic": "selectiveLogic",
    "outletName": "outlet_name",
    "group": "group",
    "groupOverride": "group_override",
    "groupWeight": "group_weight",
    "scanDepth": "scan_depth",
    "caseSensitive": "case_sensitive",
    "matchWholeWords": "match_whole_words",
    "useGroupScoring": "use_group_scoring",
    "automationId": "automation_id",
    "role": "role",
    "vectorized": "vectorized",
    "sticky": "sticky",
    "cooldown": "cooldown",
    "delay": "delay",
    "matchPersonaDescription": "match_persona_description",
    "matchCharacterDescription": "match_character_description",
    "matchCharacterPersonality": "match_character_personality",
    "matchCharacterDepthPrompt": "match_character_depth_prompt",
    "matchScenario": "match_scenario",
    "matchCreatorNotes": "match_creator_notes",
    "ignoreBudget": "ignore_budget",
    "triggers": "triggers",
}

# 比对回读一致性时看这些字段（其余字段 ST 有默认值，缺也不算错）
COMPARE = ["key", "keysecondary", "comment", "content", "constant", "selective",
           "order", "disable", "position", "role", "depth", "group", "probability",
           "selectiveLogic", "caseSensitive", "excludeRecursion", "preventRecursion",
           "vectorized", "ignoreBudget"]


def native_to_v2(entries: dict, book_name: str) -> dict:
    """native entries（键是字符串序号）→ v2 character_book。"""
    out = []
    for key in sorted(entries, key=lambda k: int(k)):
        src = entries[key]
        ext = {v2key: src[src_key] for src_key, v2key in TO_EXT.items() if src_key in src}
        # position：v2 只认 before_char/after_char，完整值走 extensions.position
        pos = src.get("position", 0)
        ext["position"] = pos
        entry = {
            "id": src.get("uid", int(key)),
            "keys": list(src.get("key") or []),
            "secondary_keys": list(src.get("keysecondary") or []),
            "comment": src.get("comment", ""),
            "content": src.get("content", ""),
            "constant": bool(src.get("constant", False)),
            "selective": bool(src.get("selective", False)),
            "insertion_order": src.get("order", 100),
            "enabled": not src.get("disable", False),
            "position": "before_char" if pos == 0 else "after_char",
            "extensions": ext,
        }
        out.append(entry)
    return {"name": book_name, "entries": out, "extensions": {}}


def convert_character_book(book: dict) -> dict:
    """复刻 ST 的 convertCharacterBook（只保留我们比对用的字段）。"""
    result = {}
    for index, entry in enumerate(book.get("entries") or []):
        eid = entry.get("id", index)
        ext = entry.get("extensions") or {}
        pos = ext.get("position")
        if pos is None:
            pos = 0 if entry.get("position") == "before_char" else 1
        row = {
            "uid": eid,
            "key": entry.get("keys") or [],
            "keysecondary": entry.get("secondary_keys") or [],
            "comment": entry.get("comment") or "",
            "content": entry.get("content", ""),
            "constant": entry.get("constant") or False,
            "selective": entry.get("selective") or False,
            "order": entry.get("insertion_order"),
            "disable": not entry.get("enabled"),
            "position": pos,
        }
        for src_key, v2key in TO_EXT.items():
            if v2key in ext:
                row[src_key] = ext[v2key]
        result[eid] = row
    return result


def verify(native: dict, card: dict) -> list[str]:
    """回读比对：内嵌的书再被 ST 转一遍，应当与 original native 等价。"""
    back = convert_character_book(card["data"]["character_book"])
    problems = []
    for key in sorted(native, key=lambda k: int(k)):
        src = native[key]
        got = back.get(src.get("uid", int(key)))
        if got is None:
            problems.append(f"条目 {key} 回读后不见了")
            continue
        for field in COMPARE:
            want = src.get(field)
            if field == "position":
                want = src.get("position", 0)
            if want is None and field not in ("key", "keysecondary", "comment"):
                continue
            if got.get(field) != want:
                problems.append(f"条目 {key}.{field}: 源 {want!r} ≠ 回读 {got.get(field)!r}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="把 native 世界书内嵌进角色卡（character_book），做单文件交付。")
    ap.add_argument("--card", required=True, type=Path, help="v2 角色卡 JSON")
    ap.add_argument("--book", required=True, type=Path, help="native 世界书 JSON（entries 对象）")
    ap.add_argument("--name", help="内嵌书的名字；默认沿用世界书文件名，ST 缺省则用 <角色名>'s Lorebook")
    ap.add_argument("--out", type=Path, help="输出路径（不给就要求 --in-place）")
    ap.add_argument("--in-place", action="store_true", help="直接改写 --card")
    ap.add_argument("--dry-run", action="store_true", help="只回读比对，不写文件")
    args = ap.parse_args(argv)

    for path in (args.card, args.book):
        if not path.exists():
            print(f"找不到文件：{path}", file=sys.stderr)
            return 2
    card = json.loads(args.card.read_text(encoding="utf-8"))
    book = json.loads(args.book.read_text(encoding="utf-8"))
    entries = book.get("entries")
    if not isinstance(entries, dict) or not entries:
        print("世界书不是 native 形状（需要 {\"entries\": {\"0\": {...}}}）；"
              "卡内 v2 数组形状不能当输入。", file=sys.stderr)
        return 2
    if "data" not in card or card.get("spec") != "chara_card_v2":
        print("角色卡不是 v2（缺 data 或 spec != chara_card_v2），内嵌书没地方放。", file=sys.stderr)
        return 2
    if not (args.out or args.in_place):
        print("要么给 --out，要么显式 --in-place。", file=sys.stderr)
        return 2

    name = args.name or args.book.stem
    v2book = native_to_v2(entries, name)
    out = copy.deepcopy(card)
    if isinstance(out.get("character_book"), dict):
        print("注意：卡里原本已有 character_book，将被覆盖。", file=sys.stderr)
    out["character_book"] = v2book
    out["data"]["character_book"] = v2book

    world = (out["data"].get("extensions") or {}).get("world")
    if not world:
        print("注意：data.extensions.world 为空。ST 在「世界书未选」时保存角色会删掉 "
              "data.character_book（world-info.js:6105），记得导入后把世界书选上。",
              file=sys.stderr)

    problems = verify(entries, out)
    if not args.dry_run:
        target = args.card if args.in_place else args.out
        target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入 {target}：内嵌 {len(v2book['entries'])} 条，书名为 {name!r}")

    if problems:
        print(f"回读不一致 {len(problems)} 处：", file=sys.stderr)
        for line in problems[:20]:
            print(f"  - {line}", file=sys.stderr)
        print("这些字段 ST 转换时不认，导入后会静默走默认值。", file=sys.stderr)
        return 1
    print(f"回读一致：{len(entries)} 条全部字段与源世界书等价。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
