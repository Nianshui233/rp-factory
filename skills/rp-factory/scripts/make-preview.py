#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把成品界面复制一份到 `preview/`，供本机双击预览。

为什么是复制而不是改：守卫（`window.self === window.top`）写在 HTML 自己里面，
所以同一份文件在酒馆楼层 iframe 里读真实数据、直接打开时走 MOCK + 画布。
复制只是给用户一个稳定的"双击这个"路径，顺便把守卫缺失挡在门口。

用法:
    python scripts/make-preview.py 制作文件/产物/statusbar-ui.html
    python scripts/make-preview.py 制作文件/产物/            # 目录：全部 *.html
    python scripts/make-preview.py a.html --out ../预览
    python scripts/make-preview.py a.html --check           # 只检查守卫，不写文件

输出目录默认是源文件同级的 `preview/`（即 `制作文件/产物/preview/`）。
退出码: 0 写好或检查通过, 1 守卫缺失/源文件不存在, 2 用法错误。
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 守卫的两个必要条件：判自己是不是顶层窗口，且 MOCK 只在预览分支里用
GUARD_RE = re.compile(r"window\.self\s*===\s*window\.top")
MOCK_RE = re.compile(r"\bMOCK\b")


def guard_problems(text: str) -> list[str]:
    """返回守卫问题列表；空表示合格。"""
    problems: list[str] = []
    if not GUARD_RE.search(text):
        problems.append("没有 `window.self === window.top` 守卫：同一份文件在聊天里和预览里会读到不同的东西")
    if MOCK_RE.search(text) and not re.search(r"if\s*\(\s*RP_PREVIEW\s*\)|RP_PREVIEW\s*\?", text):
        problems.append("有 MOCK 但没有 `if (RP_PREVIEW)` 分支：假数据会在正式聊天里被渲染出来")
    if not re.search(r"--canvas-w", text):
        problems.append("没有 `--canvas-w` 画布变量：预览时看不到 700/360 两档宽度")
    return problems


def targets(src: Path) -> list[Path]:
    if src.is_dir():
        return sorted(p for p in src.glob("*.html") if p.is_file())
    return [src]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="复制界面到 preview/ 供本机预览")
    ap.add_argument("src", help="HTML 文件或目录")
    ap.add_argument("--out", help="输出目录（默认源文件同级 preview/）")
    ap.add_argument("--check", action="store_true", help="只检查守卫，不写文件")
    args = ap.parse_args(argv)

    src = Path(args.src)
    if not src.exists():
        print(f"[FAIL] 找不到 {src}", file=sys.stderr)
        return 1

    files = targets(src)
    if not files:
        print(f"[FAIL] {src} 下没有 .html", file=sys.stderr)
        return 1

    bad = 0
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        problems = guard_problems(text)
        if problems:
            bad += 1
            print(f"[FAIL] {f}")
            for p in problems:
                print(f"       - {p}")
            continue
        if args.check:
            print(f"[OK] {f} 守卫齐")
            continue
        out_dir = Path(args.out) if args.out else (f.parent / "preview")
        out_dir.mkdir(parents=True, exist_ok=True)
        dst = out_dir / f.name
        shutil.copyfile(f, dst)
        print(f"[OK] {dst}")

    if bad:
        return 1

    if not args.check:
        print("\n双击打开预览文件，地址栏加 `?w=360` 看手机宽度：")
        for f in files:
            out_dir = Path(args.out) if args.out else (f.parent / "preview")
            print(f"  file:///{(out_dir / f.name).as_posix()}?w=360")
        print("预览里按钮不发消息、不写 localStorage；正式聊天里 MOCK 永不触发。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
