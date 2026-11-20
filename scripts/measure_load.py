#!/usr/bin/env python3
"""每阶段加载量预算器。

用途：把「这次改动有没有让 skill 变重」变成一条可执行断言，而不是感觉。
- ALWAYS / LOAD_MAP 描述每个阶段进入时实际会读到的文件（worst case：开关打开时也算进去）。
- tok 估算：cjk*1.15 + 非 cjk 字符数/3.6（够用即可，不追求与某家 tokenizer 对齐）。
- BASELINE 是 2026-11-21 改动前的实测值。任何阶段超过基线即为变重。
- 例外只记在案的两次：Ruling ③ 世界书双入口（delivery +414）；Ruling ④ 契约新增
  `player_agency`（每阶段 +63，加载在最共用的 `contract-schema.md`）与角色卡事实分级
  （cast 另 +94）。基线一律改为「该次改动实测值」，绝对上限 26,000 不变——
  新增功能要付的体积账写在提交信息里，而不是悄悄抬高上限。

CLI:
    python scripts/measure_load.py                # 全部阶段 + 结论
    python scripts/measure_load.py --stage cast    # 单阶段
    python scripts/measure_load.py --json          # 机器可读
    python scripts/measure_load.py --max-tokens N  # 覆盖绝对上限
退出码：0 全部在预算内；1 有阶段超基线或超上限；2 参数错误。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MAX_STAGE_TOKENS = 26000
SKILL_MD_MAX = 6600
PIPELINE_MAX = 4700

ALWAYS = ["SKILL.md", "references/pipeline.md"]

_CONTRACT = "references/contract-schema.md"
_INTERVIEW = "references/interview-protocol.md"
_WEB = "references/web-research.md"

# 每个阶段进入后会读到的文件（不含 ALWAYS）。按 references/pipeline.md 的阶段名。
LOAD_MAP: dict[str, list[str]] = {
    "world": [_INTERVIEW, _WEB, "references/stage-1-world-bible.md", _CONTRACT],
    "cast": [_INTERVIEW, _WEB, "references/stage-2-rolecard.md", _CONTRACT],
    "scenes": [_INTERVIEW, _WEB, "references/stage-3-scene-sheet.md", _CONTRACT],
    "axes": [_INTERVIEW, _WEB, "references/stage-4-axis-system.md", _CONTRACT],
    "mvu": ["references/stage-mvu.md", _CONTRACT],
    "ejs": ["references/stage-ejs.md", _CONTRACT],
    "opening": [
        "references/frontend-conventions.md",
        "references/dual-mode.md",
        "references/stage-5-opening-ui.md",
        _CONTRACT,
    ],
    "statusbar": [
        "references/frontend-conventions.md",
        "references/dual-mode.md",
        "references/stage-6-statusbar-ui.md",
        _CONTRACT,
    ],
    "delivery": [
        "references/stage-7-delivery.md",
        "references/worldbook-tuning.md",
        "references/dual-mode.md",
        _CONTRACT,
    ],
}

# 2026-11-21 实测（改动前），见 scripts/measure_load.py 首次运行的输出。
BASELINE: dict[str, int] = {
    "world": 23548,
    "cast": 20576,
    "scenes": 19279,
    "axes": 20241,
    "mvu": 16612,
    "ejs": 15582,
    "opening": 23533,
    "statusbar": 22523,
    "delivery": 25880,
}

_CJK = re.compile(r"[\u4e00-\u9fff]")


def estimate(paths: list[str], root: Path | None = None) -> int:
    """返回一组文件的 tok 估算值。"""
    base = root or ROOT
    total = 0
    for rel in paths:
        text = (base / rel).read_text(encoding="utf-8")
        cjk = len(_CJK.findall(text))
        total += int(cjk * 1.15 + (len(text) - cjk) / 3.6)
    return total


def stage_paths(stage: str) -> list[str]:
    return [*ALWAYS, *LOAD_MAP[stage]]


def report(root: Path | None = None) -> list[tuple[str, int]]:
    """返回 [(阶段名, worst-case tok)]，按 LOAD_MAP 定义顺序。"""
    return [(stage, estimate(stage_paths(stage), root)) for stage in LOAD_MAP]


def evaluate(rows: list[tuple[str, int]], max_tokens: int = MAX_STAGE_TOKENS) -> list[str]:
    """返回问题列表；空表示全部通过。"""
    problems = []
    for stage, tok in rows:
        base = BASELINE.get(stage)
        if base and tok > base:
            problems.append(f"{stage}: {tok} > 基线 {base}（+{tok - base}）")
        if tok > max_tokens:
            problems.append(f"{stage}: {tok} > 绝对上限 {max_tokens}")
    return problems


def main(argv: list[str]) -> int:
    stage = None
    as_json = False
    max_tokens = MAX_STAGE_TOKENS
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--stage":
            i += 1
            stage = argv[i] if i < len(argv) else None
            if stage not in LOAD_MAP:
                print(f"未知阶段：{stage}；可用：{', '.join(LOAD_MAP)}", file=sys.stderr)
                return 2
        elif a == "--json":
            as_json = True
        elif a == "--max-tokens":
            i += 1
            try:
                max_tokens = int(argv[i])
            except (IndexError, ValueError):
                print("--max-tokens 需要一个整数", file=sys.stderr)
                return 2
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            print(f"未知参数：{a}", file=sys.stderr)
            return 2
        i += 1

    rows = report()
    if stage:
        rows = [(s, t) for s, t in rows if s == stage]
    problems = evaluate(rows, max_tokens)
    skill_tok = estimate(["SKILL.md"])
    pipe_tok = estimate(["references/pipeline.md"])
    if skill_tok > SKILL_MD_MAX:
        problems.append(f"SKILL.md {skill_tok} > {SKILL_MD_MAX}")
    if pipe_tok > PIPELINE_MAX:
        problems.append(f"pipeline.md {pipe_tok} > {PIPELINE_MAX}")

    if as_json:
        print(json.dumps(
            {"stages": [{"stage": s, "tokens": t, "baseline": BASELINE.get(s)} for s, t in rows],
             "skill_md": estimate(["SKILL.md"]),
             "pipeline": estimate(["references/pipeline.md"]),
             "problems": problems},
            ensure_ascii=False, indent=2))
    else:
        print(f"{'阶段':<12}{'tok':>8}{'基线':>8}{'增量':>8}")
        for s, t in rows:
            base = BASELINE.get(s) or 0
            delta = f"{t - base:+d}" if base else "—"
            print(f"{s:<12}{t:>8}{base or '—':>8}{delta:>8}")
        print(f"{'SKILL.md':<12}{estimate(['SKILL.md']):>8}{SKILL_MD_MAX:>8}")
        print(f"{'pipeline':<12}{estimate(['references/pipeline.md']):>8}{PIPELINE_MAX:>8}")
        if problems:
            print("\n超预算：")
            for p in problems:
                print(f"  - {p}")
        else:
            print("\n全部阶段在预算内。")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
