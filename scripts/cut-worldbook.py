#!/usr/bin/env python3
"""原稿切割器：把设定原稿按节切开，原样装进世界书条目。

为什么要有这一步：手写条目时最容易发生的事就是「顺手压缩」——把
《常见误解或谣言》压成「有一些谣言」、把每级 `behavioral_signs` 压成一句，
结果模型做判断时唯一的依据没了。长度不是问题（关键词条目只在命中时才
进上下文），丢信息才是问题。

所以这里不做摘要、不改写、不重排：`content` 是原稿的**逐行切片**，缩进与
措辞原样保留。模型只负责在 `--plan` 里做选择（哪一节、叫什么、什么关键词、
什么顺序），切的动作交给脚本。

用法：
    python scripts/cut-worldbook.py --plan 制作文件/项目记录/世界书切割.yaml \
        --draft-root 制作文件/产物 --out "导入包/白潮 世界书.json" [--dry-run]

plan 的形状见 `templates/worldbook-plan.yaml`。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("需要 pyyaml：pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

DEFAULTS = {
    "constant": False,
    "selective": True,
    "exclude_recursion": True,
    "position": 0,
    "role": None,
    "depth": 4,
    "probability": 100,
    "match_whole_words": False,
    "case_sensitive": None,
    "use_regex": False,
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def section_spans(text: str, indent: int = 2):
    """按 `indent` 个空格缩进的 `名字:` 行切节，返回 [(名字, 起始行号, 结束行号)]。

    行号从 0 起，区间为 [start, end)；末尾空行不计入。
    """
    lines = text.split("\n")
    pattern = re.compile(r"^ {%d}([^#\s\-][^:]*?):(?:\s+.*)?$" % indent)
    starts: list[tuple[str, int]] = []
    in_block = False
    for i, line in enumerate(lines):
        # YAML 块标量与多行字符串里不该被误切：只认「上一行不是块标量开头」的位置
        if in_block:
            if line.strip() == "" or line.startswith(" " * (indent + 1)):
                continue
            in_block = False
        m = pattern.match(line)
        if m:
            starts.append((m.group(1).strip(), i))
            if line.rstrip().endswith(("|", ">", "|-", ">-")):
                in_block = True
    spans = []
    for idx, (name, start) in enumerate(starts):
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(lines)
        while end > start + 1 and lines[end - 1].strip() == "":
            end -= 1
        spans.append((name, start, end))
    return lines, spans


def slice_lines(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start:end]).rstrip()


def build_entry(uid: int, item: dict, content: str, defaults: dict) -> dict:
    def pick(key: str, fallback):
        return item.get(key, defaults.get(key, fallback))

    keys = item.get("keys") or []
    if isinstance(keys, str):
        keys = [keys]
    return {
        "uid": uid,
        "key": [str(k) for k in keys],
        "keysecondary": [str(k) for k in (item.get("keys_secondary") or [])],
        "comment": item.get("comment") or item.get("section") or item.get("whole") or f"条目 {uid}",
        "content": content,
        "constant": bool(pick("constant", False)),
        "vectorized": False,
        "selective": bool(pick("selective", True)),
        "selectiveLogic": 0,
        "addMemo": True,
        "order": item.get("order", 100 - uid),
        "position": pick("position", 0),
        "disable": bool(item.get("disable", False)),
        "excludeRecursion": bool(pick("exclude_recursion", True)),
        # 常驻条目每轮都在，是唯一稳定往递归缓冲里灌东西的来源：默认反向锁死。
        # 关键词条目默认放开（它本来就是要靠正文点出关联实体才拉人的）。
        "preventRecursion": bool(pick("prevent_recursion", bool(pick("constant", False)))),
        "delayUntilRecursion": False,
        "probability": pick("probability", 100),
        "useProbability": True,
        "depth": pick("depth", 4),
        "group": item.get("group", ""),
        "groupOverride": False,
        "groupWeight": 100,
        "scanDepth": None,
        "caseSensitive": pick("case_sensitive", None),
        "matchWholeWords": pick("match_whole_words", False),
        "useGroupScoring": None,
        "automationId": "",
        "role": pick("role", None),
        "sticky": 0,
        "cooldown": 0,
        "delay": 0,
        "ignoreBudget": bool(pick("ignore_budget", False)),
        "outletName": "",
        "triggers": [],
        "matchPersonaDescription": False,
        "matchCharacterDescription": False,
        "matchCharacterPersonality": False,
        "matchCharacterDepthPrompt": False,
        "matchScenario": False,
        "matchCreatorNotes": False,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="原稿切割：按节切开装进世界书条目（不改写、不摘要）")
    ap.add_argument("--plan", required=True, help="切割计划 YAML（见 templates/worldbook-plan.yaml）")
    ap.add_argument("--draft-root", default="制作文件/产物", help="原稿所在目录，默认 制作文件/产物")
    ap.add_argument("--out", help="输出世界书 JSON；不给就只打印切割结果")
    ap.add_argument("--section-indent", type=int, default=2, help="原稿里一节的缩进空格数，默认 2")
    ap.add_argument("--book-name", help="世界书名；默认取 plan 的 book_name 或输出文件名")
    ap.add_argument("--merge-protocol", metavar="BOOK",
                    help="从已有的世界书里带上协议条目（comment 以 [ 开头的：变量初始化 / 更新块 / 阶段控制器），"
                         "追加在切割条目之后。协议条目来自阶段 6 的模板，不是设定原稿，所以不走切割")
    ap.add_argument("--dry-run", action="store_true", help="只打印每条的名称与字数，不写文件")
    args = ap.parse_args(argv)

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"plan 不存在：{plan_path}", file=sys.stderr)
        return 2
    plan = yaml.safe_load(read_text(plan_path)) or {}
    items = plan.get("entries") or []
    if not items:
        print("plan 的 entries 是空的", file=sys.stderr)
        return 2

    root = Path(args.draft_root)
    defaults = {**DEFAULTS, **(plan.get("defaults") or {})}

    cache: dict[Path, tuple[list[str], list[tuple[str, int, int]]]] = {}
    used: dict[str, set[str]] = {}
    entries: dict[str, dict] = {}
    errors: list[str] = []

    for uid, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"第 {uid} 项不是对象")
            continue
        if "whole" in item:
            path = root / item["whole"]
            if not path.exists():
                errors.append(f"原稿不存在：{path}")
                continue
            content = read_text(path).rstrip()
            used.setdefault(str(path), set()).add("*")
        elif "section" in item:
            rel = item.get("from") or plan.get("default_from") or "world-bible.yaml"
            path = root / rel
            if not path.exists():
                errors.append(f"原稿不存在：{path}")
                continue
            if path not in cache:
                cache[path] = section_spans(read_text(path), args.section_indent)
            lines, spans = cache[path]
            hit = [s for s in spans if s[0] == item["section"]]
            if not hit:
                errors.append(
                    f"{rel} 里没有节「{item['section']}」；现有节："
                    + "、".join(s[0] for s in spans)
                )
                continue
            if len(hit) > 1:
                errors.append(f"{rel} 里节「{item['section']}」出现多次（缩进 {args.section_indent} 的行）")
                continue
            name, start, end = hit[0]
            if name in used.setdefault(str(path), set()):
                errors.append(f"{rel} 的节「{name}」被切了两次")
                continue
            used[str(path)].add(name)
            content = slice_lines(lines, start, end)
        else:
            errors.append(f"第 {uid} 项既没有 section 也没有 whole")
            continue

        if not content.strip():
            errors.append(f"条目 {uid}（{item.get('comment') or item.get('section')}）切出来是空的")
            continue
        entries[str(uid)] = build_entry(uid, item, content, defaults)

    if errors:
        for e in errors:
            print(f"[FAIL] {e}", file=sys.stderr)
        return 1

    # 没被切走的节/文件：必须报出来，否则「丢设定」就是这么发生的
    uncovered: list[str] = []
    for rel in sorted({str(p.name) for p in root.glob("*.yaml")} | {Path(i["from"]).name for i in items if i.get("from")}):
        path = root / rel
        if not path.exists():
            continue
        if rel in plan.get("skip", []):
            continue
        if str(path) not in used:
            uncovered.append(f"{rel}（整份没进书）")
            continue
        if "*" in used[str(path)]:
            continue
        lines, spans = cache.get(path) or section_spans(read_text(path), args.section_indent)
        missing = [name for name, _s, _e in spans if name not in used[str(path)]]
        if missing:
            uncovered.append(f"{rel}：{'、'.join(missing)}")

    for uid in sorted(entries, key=int):
        e = entries[uid]
        flag = "常驻" if e["constant"] else f"{len(e['key'])} 键"
        print(f"  {uid:>3} {e['comment'][:20]:<22} {len(e['content']):>6} 字  {flag}  order {e['order']}")
    total = sum(len(e["content"]) for e in entries.values())
    const = sum(len(e["content"]) for e in entries.values() if e["constant"])
    print(f"\n共 {len(entries)} 条，{total} 字（常驻 {const} 字）")

    if uncovered:
        print("\n[WARN] 这些原稿内容没进书（是有意不给模型看，还是漏了？plan 的 skip 里可以明示）：")
        for u in uncovered:
            print(f"  - {u}")

    if args.dry_run or not args.out:
        return 0

    if args.merge_protocol:
        src = Path(args.merge_protocol)
        if not src.exists():
            print(f"--merge-protocol 的源书不存在：{src}", file=sys.stderr)
            return 2
        old = json.loads(read_text(src)).get("entries") or {}
        kept = [e for _k, e in sorted(old.items(), key=lambda kv: int(kv[0]))
                if str(e.get("comment", "")).lstrip().startswith("[")]
        if kept:
            names = "、".join(str(e.get("comment")) for e in kept)
            print(f"带上 {len(kept)} 条协议条目：{names}")
        for e in kept:
            item = dict(e)
            item.setdefault("exclude_recursion", True)
            entries[str(len(entries))] = build_entry(len(entries), item, str(e.get("content", "")), defaults)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    name = args.book_name or plan.get("book_name") or out.name.replace(".json", "")
    out.write_text(json.dumps({"entries": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n写出 {out}（书名 {name}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
