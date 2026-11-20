#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""阶段收尾一检：一个命令跑完这个阶段该跑的全部校验器。

用法:
    python scripts/check-stage.py world     H:/RP创作/未命名项目
    python scripts/check-stage.py delivery  <项目根>
    python scripts/check-stage.py all       <项目根>     # 全部跑一遍（收尾复核用）

不给项目根时用当前目录。阶段名认 world / cast / scenes / axes / mvu / ejs /
opening / statusbar / delivery。

只在一个阶段**收尾时**跑一次。过程里不要每写一个文件就跑——校验器是"交卷前对一遍
答案"，不是编辑器的高亮。

退出码: 0 = 全过, 1 = 有失败, 2 = 用法/读取错误。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
STAGES = ["world", "cast", "scenes", "axes", "mvu", "ejs", "opening", "statusbar", "delivery"]


def run(script: str, args: list[str]) -> tuple[int, list[str]]:
    cmd = [sys.executable, str(HERE / script), *args]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    lines = [ln.rstrip() for ln in out.splitlines() if ln.strip()]
    # 只留下有信息量的行：FAIL / warn / 总结行
    keep = [ln for ln in lines if ("FAIL" in ln or "warn" in ln.lower() or "失败" in ln or "通过" in ln)]
    return p.returncode, (keep or lines[-2:])


def rel(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def contract_artifacts(root: Path, types: set[str]) -> list[Path]:
    """从契约里挑出指定 type 的产物路径（存在且是文件/目录）。"""
    cpath = root / "创作痕迹" / "contract.yaml"
    if not cpath.exists():
        return []
    try:
        import yaml  # noqa: PLC0415
    except ModuleNotFoundError:
        return []
    try:
        data = yaml.safe_load(cpath.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return []
    out: list[Path] = []
    for item in data.get("artifacts") or []:
        if not isinstance(item, dict) or item.get("type") not in types:
            continue
        raw = str(item.get("path") or "").strip()
        if not raw:
            continue
        p = (root / raw) if not Path(raw).is_absolute() else Path(raw)
        if p.exists():
            out.append(p)
    return out


def find_book(root: Path) -> Path | None:
    for d in (root / "最终产物", root / "创作痕迹" / "产物"):
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            if '"entries"' in text and "世界书" in p.name:
                return p
    return None


def plan(stage: str, root: Path) -> list[tuple[str, list[str]]]:
    """阶段 → [(脚本, 参数)]。契约永远查；其余按阶段追加。"""
    jobs: list[tuple[str, list[str]]] = []
    contract = root / "创作痕迹" / "contract.yaml"
    if contract.exists():
        jobs.append(("validate-contract.py", [str(contract)]))

    if stage in ("cast", "all"):
        cards = contract_artifacts(root, {"rolecard"})
        for p in cards:
            jobs.append(("validate-rolecard.py", [str(p)]))

    if stage in ("opening", "statusbar", "all"):
        types = {"opening": {"opening-ui"}, "statusbar": {"statusbar-ui"}}.get(stage, {"opening-ui", "statusbar-ui"})
        htmls = [p for p in contract_artifacts(root, types) if p.suffix == ".html"]
        if not htmls:
            pats = {"opening": ["wizard*", "opening*"], "statusbar": ["statusbar*"], "all": ["*.html"]}[stage]
            cand = []
            for d in (root / "创作痕迹" / "产物", root / "最终产物"):
                for pat in pats:
                    cand += list(d.glob(pat))
            htmls = [p for p in cand if p.suffix == ".html"]
        for p in htmls:
            jobs.append(("validate-frontend.py", [str(p)]))

    book = find_book(root)
    if stage in ("mvu", "all"):
        mvu_dir = root / "创作痕迹" / "产物" / "mvu"
        if mvu_dir.exists():
            args = [str(mvu_dir), "--contract", str(contract)] if contract.exists() else [str(mvu_dir)]
            if book:
                args += ["--book", str(book)]
            jobs.append(("validate-mvu.py", args))

    if stage in ("ejs", "all"):
        ctrls = sorted((root / "创作痕迹" / "产物" / "ejs").glob("*.ejs"))
        for c in ctrls:
            args = [str(c)]
            if book:
                args += ["--book", str(book)]
            jobs.append(("validate-ejs.py", args))

    if stage in ("delivery", "all"):
        final = root / "最终产物"
        has_card = False
        if final.exists():
            import json  # noqa: PLC0415
            for f in sorted(final.glob("*.json")):
                try:
                    if "spec" in json.loads(f.read_text(encoding="utf-8")):
                        has_card = True
                        break
                except Exception:  # noqa: BLE001
                    continue
        if has_card:
            args = [str(final)]
            if contract.exists():
                args += ["--contract", str(contract)]
            jobs.append(("validate-st-package.py", args))
            jobs.append(("validate_st_semantics.py", list(args)))
            ledger = root / "创作痕迹" / "验收.yaml"
            if ledger.exists():
                jobs.append(("check_acceptance.py", [str(ledger.parent)]))

    return jobs


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__)
        return 2
    stage = args[0]
    if stage not in STAGES + ["all"]:
        print(f"不认识的阶段：{stage!r}（可用：{' / '.join(STAGES)} / all）", file=sys.stderr)
        return 2
    root = Path(args[1]).expanduser().resolve() if len(args) > 1 else Path.cwd()

    jobs = plan(stage, root)
    if not jobs:
        print(f"[FAIL] 阶段 {stage}：没有任何可跑的检查——项目里缺 创作痕迹/contract.yaml？")
        return 1

    print(f"阶段收尾一检 · {stage} · {root}")
    print("-" * 56)
    failed = 0
    for script, sargs in jobs:
        code, lines = run(script, sargs)
        tag = "PASS" if code == 0 else "FAIL"
        target = next((Path(a).name for a in sargs if not a.startswith("-") and Path(a).suffix in
                       (".yaml", ".yml", ".json", ".html", ".ejs") or Path(a).is_dir()), "")
        print(f"[{tag}] {script}  {target}")
        if code != 0:
            failed += 1
            for ln in lines:
                print("      " + ln)
    print("-" * 56)
    if failed:
        print(f"{len(jobs)} 个检查：{failed} 个没通过。改完重跑这一条命令，别一条条跑。")
        return 1
    print(f"{len(jobs)} 个检查全过。这一阶段可以交了。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
