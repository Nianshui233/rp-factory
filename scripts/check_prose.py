#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""去 AI 味检查（P01–P09）：找「解释腔、情绪直说、陈词比喻、模板标签」。

定位：这是**自检门的辅助**，不是判分器。它抓的是可机检的八股形态，判不了"好不好看"。
默认只警告（退出码 0），`--strict` 才当失败用；命中之后怎么改由人判断——
把「他感到恐惧」改写成手抖、退半步、呼吸变浅，而不是删掉那句。

用法：
    python scripts/check_prose.py 创作痕迹/产物/world-bible.yaml
    python scripts/check_prose.py 最终产物 --json
    python scripts/check_prose.py <文件> --strict

跳过：代码块、以 # / | / > / 列表符号 开头的行、纯 YAML 键值行——那里不是散文。
退出码：0 通过（含仅有警告）；--strict 下有命中则 1；2 参数/读取错误。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RULES = {
    "P01": "破折号解释腔：用 —— 补解释，一句里连着解释两次以上",
    "P02": "抽象逃逸：某种 / 说不清 / 一股…涌上，把具体换成模糊",
    "P03": "情绪直说：感到 / 觉得 / 不禁 / 忍不住，直接报情绪不写表现",
    "P04": "排比总结：不是…而是…／既…又…，把叙事写成标语",
    "P05": "陈词比喻：眼睛像星星、时间仿佛静止一类现成比喻",
    "P06": "段末总结句：这一刻／或许，／他知道——替读者总结",
    "P07": "对话标签单调：淡淡地说、冷冷地道连着用",
    "P08": "三连形容堆叠：…的…的…的",
    "P09": "绝对化失衡：把「通常/多数」的尺子写成「绝不/一律/一定」",
}

# P09：绝对化词与对冲词（程度词）分开数。世界设定里绝大多数判断是倾向，
# 写成绝对句之后模型再也演不出例外——这跟 P02 的「模糊逃逸」正好相反。
# 真边界（taboos / anti_ooc 里的「绝不」是对的，不算问题）
BOUNDARY = re.compile(r"绝不|永远不|从不")
# 把倾向写成普遍规律的那几个词，才是 P09 要抓的
UNIVERSAL = re.compile(r"一律|一定|所有|任何|人人|每个|无一例外|毫无|总是|每次")
HEDGE = re.compile(r"通常|多数|有时|可能|大概|一般|往往|容易|倾向|或许|多半|常见|偶尔|极少|少数")
SENTENCE_SPLIT = re.compile("[。；！？]")

PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("P02", "抽象逃逸", re.compile(r"某种|说不出的?|说不上来的?|一股.{0,6}(?:涌上|涌起|升起)")),
    ("P03", "情绪直说", re.compile(r"(?:他|她|我|你|TA)(?:感到|觉得|意识到|察觉到)|不禁|忍不住|不由自主")),
    ("P04", "排比总结", re.compile(r"不是[^。；\n]{1,24}[，,]?\s*而是|既不?[^。；\n]{1,16}[，,]?\s*又")),
    ("P05", "陈词比喻", re.compile(
        r"眼睛像(?:星星|星辰|宝石)|时间仿佛静止|空气仿佛凝固|心像小鹿|"
        r"世界仿佛(?:只)?剩下|如同被.{0,6}(?:击中|抽走)|像被抽走了?(?:力气|魂魄)")),
    ("P06", "段末总结句", re.compile(
        r"^[\s「『\"']*(?:这一刻|那一刻|或许[，,]|他知道[，,]|她知道[，,]|而他不知道|从那以后)")),
    ("P07", "对话标签单调", re.compile(r"(?:淡淡|冷冷|轻轻|缓缓|幽幽|温柔|平静)地(?:说|道|开口|回答)")),
    ("P08", "三连形容堆叠", re.compile(r"[\u4e00-\u9fff]{1,2}的[、，]?[\u4e00-\u9fff]{1,2}的[、，]?[\u4e00-\u9fff]{1,2}的")),
]

DASH = "——"
SKIP_LINE = re.compile(r"^\s*(?:#|\||>|```|-\s+\w+:|\w[\w.\-]*:\s)")
FENCE = "```"


def _prose_lines(text: str) -> list[tuple[int, str]]:
    """挑出真正当散文读的行：跳代码块、表格、标题、YAML 键值。"""
    out: list[tuple[int, str]] = []
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(FENCE):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        if SKIP_LINE.match(line):
            continue
        out.append((number, line))
    return out


def check_text(text: str, *, dash_per_chars: int = 600) -> list[dict]:
    """返回命中列表：{code, rule, line, excerpt, message}。"""
    findings: list[dict] = []
    lines = _prose_lines(text)
    body = "\n".join(line for _, line in lines)
    chars = max(1, len(re.sub(r"\s", "", body)))

    # P01 密度：破折号解释腔
    dash_hits = body.count(DASH)
    allowed = max(1, chars // dash_per_chars)
    if dash_hits > allowed:
        findings.append({
            "code": "P01", "rule": RULES["P01"], "line": 0,
            "excerpt": f"{dash_hits} 处 —— / {chars} 字",
            "message": f"{RULES['P01']}（本段 {dash_hits} 处，阈值 {allowed}）："
                       f"破折号后面多半是作者在解释刚写的动作，删掉解释让动作自己说话。",
        })

    unique_tags: set[str] = set()
    for number, line in lines:
        for code, name, pattern in PATTERNS:
            for match in pattern.finditer(line):
                if code == "P07":
                    unique_tags.add(match.group(0))
                findings.append({
                    "code": code, "rule": RULES[code], "line": number,
                    "excerpt": match.group(0),
                    "message": f"{RULES[code]}：命中「{match.group(0)}」",
                })

    # P09 绝对化失衡：文件级（全是绝对句，一个对冲词都没有）+ 句级（一句里叠两个）
    universal_hits = UNIVERSAL.findall(body)
    hedge_hits = HEDGE.findall(body)
    if len(universal_hits) >= 3 and not hedge_hits:
        findings.append({
            "code": "P09", "rule": RULES["P09"], "line": 0,
            "excerpt": f"{len(universal_hits)} 处绝对化 / 0 处程度词",
            "message": f"{RULES['P09']}（{len(universal_hits)} 处绝对化，对冲词 0）："
                       f"绝大多数世界判断是倾向。写成「一律/绝不」之后模型再也演不出例外，"
                       f"把该松的改成「通常/多数/可能」。",
        })
    for number, line in lines:
        for sentence in SENTENCE_SPLIT.split(line):
            found = UNIVERSAL.findall(sentence) + BOUNDARY.findall(sentence)
            if len(found) >= 2 and UNIVERSAL.search(sentence):
                findings.append({
                    "code": "P09", "rule": RULES["P09"], "line": number,
                    "excerpt": sentence.strip()[:60],
                    "message": f"{RULES['P09']}：一句里叠了 {' / '.join(found)}——"
                               f"留一个绝对句，其余改成程度词或条件句。",
                })

    # P07 只看「同段里连着换标签」：三种以上不同标签同时出现才算单调
    if len(unique_tags) >= 3:
        findings.append({
            "code": "P07", "rule": RULES["P07"], "line": 0,
            "excerpt": " / ".join(sorted(unique_tags)),
            "message": f"{RULES['P07']}：同一份稿子里出现 {len(unique_tags)} 种「…地说」，"
                       f"换成动作或直接不加标签。",
        })
    return findings


def _iter_files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(sorted(p.rglob("*.md")))
            out.extend(sorted(p.rglob("*.yaml")))
            out.extend(sorted(p.rglob("*.txt")))
        elif p.is_file():
            out.append(p)
    return out


def main(argv: list[str]) -> int:
    paths: list[str] = []
    as_json = False
    strict = False
    for arg in argv:
        if arg == "--json":
            as_json = True
        elif arg == "--strict":
            strict = True
        elif arg in ("-h", "--help"):
            print(__doc__)
            return 0
        elif arg.startswith("-"):
            print(f"未知参数：{arg}", file=sys.stderr)
            return 2
        else:
            paths.append(arg)

    if not paths:
        print(__doc__)
        return 2

    files = _iter_files(paths)
    if not files:
        print("没有可检查的 .md / .yaml / .txt 文件", file=sys.stderr)
        return 2

    report: list[dict] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"读不了 {path}：{exc}", file=sys.stderr)
            return 2
        for hit in check_text(text):
            hit["file"] = path.name
            report.append(hit)

    if as_json:
        print(json.dumps({"findings": report, "count": len(report)}, ensure_ascii=False, indent=2))
    else:
        for hit in report:
            where = f"{hit['file']}:{hit['line']}" if hit["line"] else f"{hit['file']}"
            print(f"[{hit['code']}] {where}  {hit['message']}")
        if report:
            codes = sorted({h["code"] for h in report})
            print(f"\n{len(report)} 处命中（{' '.join(codes)}）。这是提示不是判决："
                  f"改法是写出表现，不是删句。")
        else:
            print("九类形态都没命中。")

    if strict and report:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
