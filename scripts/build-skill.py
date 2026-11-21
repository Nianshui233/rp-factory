#!/usr/bin/env python3
"""把仓库里「模型运行时要用的部分」拷成一份 skill 目录。

仓库是开发物：`docs/`（计划、复盘、规格）、`tests/`、`node_modules/`、`.git/`。
skill 是运行物：只有 `SKILL.md`、`references/`、`templates/`、`scripts/`、`examples/*.yaml`。
两者不能共用同一个目录——否则 `docs/plans/` 里那些内部笔记会跟着 skill 一起被看见。

用法：
    python scripts/build-skill.py                 # 默认写到 ~/.agents/skills/rp-factory
    python scripts/build-skill.py --dest D:/x/y   # 指到别处
    python scripts/build-skill.py --check         # 只比对，不写；有漂移退出码 1
    python scripts/build-skill.py --dry-run       # 打印会拷什么

`--check` 的用途：改完仓库忘了同步 skill 时会被测试拦下（`tests/test_build_skill.py`）。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "rp-factory"

# 进 skill 的东西，白名单制——新增产物目录时必须来这一行登记，
# 否则模型看不到它（`tests/test_build_skill.py` 会检查引用完整性）。
INCLUDE_FILES = ["SKILL.md"]
INCLUDE_DIRS = ["references", "templates", "scripts"]
# examples 只带标杆样本，不带整包 dry-run（那份是给人看的验收示范，1.6 MB）
INCLUDE_GLOBS = ["examples/*.yaml"]

SKIP_NAMES = {"__pycache__", ".pytest_cache", ".DS_Store"}
SKIP_SUFFIX = {".pyc", ".pyo", ".pyz"}

DEFAULT_DEST = Path.home() / ".agents" / "skills" / "rp-factory"


def collect(root: Path) -> dict[str, Path]:
    """返回 {相对路径: 源文件}，按白名单挑选。"""
    out: dict[str, Path] = {}
    for name in INCLUDE_FILES:
        p = root / name
        if p.is_file():
            out[name] = p
    for d in INCLUDE_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            if set(rel.parts) & SKIP_NAMES:
                continue
            if p.suffix.lower() in SKIP_SUFFIX:
                continue
            out[rel.as_posix()] = p
    for pattern in INCLUDE_GLOBS:
        for p in sorted(root.glob(pattern)):
            if p.is_file():
                out[p.relative_to(root).as_posix()] = p
    return out


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def is_linkish(p: Path) -> bool:
    """目录 junction / 符号链接都算——这两种用 os.rmdir 只会摘链接，不动目标。"""
    if p.is_symlink():
        return True
    isjunction = getattr(os.path, "isjunction", None)
    if isjunction is not None:
        return bool(isjunction(p))
    try:  # Python < 3.12 没有 isjunction，用 os.readlink 试探
        os.readlink(p)
        return True
    except OSError:
        return False


def clear_dest(dest: Path) -> None:
    """清掉旧 skill 目录。绝不碰仓库。"""
    if not dest.exists() and not dest.is_symlink():
        return
    # 链接（junction / symlink）先摘掉——只摘链接，不动它指向的仓库
    if is_linkish(dest):
        os.rmdir(dest)
        return
    # 保险：目标里若有 .git，多半是有人把 --dest 指到了仓库本身
    if (dest / ".git").exists():
        raise SystemExit(f"拒绝清理 {dest}：里面是 git 仓库，--dest 指错了？")
    shutil.rmtree(dest)


def build(dest: Path, files: dict[str, Path], dry_run: bool = False) -> None:
    if dry_run:
        total = sum(p.stat().st_size for p in files.values())
        print(f"会拷 {len(files)} 个文件 / {total / 1024:.0f} KB 到 {dest}")
        for rel in sorted(files):
            print("  +", rel)
        return
    clear_dest(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for rel, src in files.items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    total = sum((dest / rel).stat().st_size for rel in files)
    print(f"已构建 {dest}")
    print(f"  {len(files)} 个文件 / {total / 1024:.0f} KB")


def check(dest: Path, files: dict[str, Path]) -> int:
    if not dest.is_dir():
        print(f"[缺] {dest} 不存在，先跑一次 python scripts/build-skill.py")
        return 1
    have = {p.relative_to(dest).as_posix(): p for p in dest.rglob("*") if p.is_file()}
    missing = sorted(set(files) - set(have))
    extra = sorted(set(have) - set(files))
    stale = sorted(rel for rel in set(files) & set(have) if digest(files[rel]) != digest(have[rel]))
    for rel in missing:
        print(f"[缺] {rel}")
    for rel in extra:
        print(f"[多] {rel}（skill 里有、白名单里没有）")
    for rel in stale:
        print(f"[旧] {rel}")
    if missing or extra or stale:
        print(f"\nskill 与仓库不一致：缺 {len(missing)} / 多 {len(extra)} / 旧 {len(stale)}")
        print("跑 python scripts/build-skill.py 同步。")
        return 1
    print(f"skill 与仓库一致（{len(files)} 个文件）")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="把仓库构建成 skill 目录")
    ap.add_argument("--dest", default=str(DEFAULT_DEST))
    ap.add_argument("--check", action="store_true", help="只比对不写，有漂移退出码 1")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    files = collect(SKILL)
    if "SKILL.md" not in files:
        print("找不到 SKILL.md，仓库结构不对")
        return 2
    dest = Path(args.dest).expanduser()
    if args.check:
        return check(dest, files)
    build(dest, files, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
