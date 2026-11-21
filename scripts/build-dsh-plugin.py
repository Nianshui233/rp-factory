#!/usr/bin/env python3
"""打 DSH 插件包：把 skill 本体与宿主入口装进一个 `.tgz`。

DSH 从 npm 包加载插件（`dsh plugin add <tarball>`），所以这里做三件事：

1. 拷 `skills/rp-factory/` 到构建目录（生产环境读不到仓库，必须自带一份）；
2. 写 `package.json`（版本号从 `SKILL.md` 的 `metadata.version` 取，不手填）；
3. `npm pack` 出 `dist/rp-factory-dsh-v<版本>.tgz`，并做包内校验
   （index.js 能 import、skill 目录里 SKILL.md 的 name 与目录名一致）。

用法：
    python scripts/build-dsh-plugin.py            # 出包
    python scripts/build-dsh-plugin.py --check    # 只校验不打包
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "rp-factory"
ADAPTER = REPO / "host-adapters" / "dsh" / "plugin"
DIST = REPO / "dist"
VERSION_RE = re.compile(r"^  version:\s*(\d+\.\d+\.\d+)\s*$", re.M)


def skill_version() -> str:
    m = VERSION_RE.search((SKILL / "SKILL.md").read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("SKILL.md 里找不到 metadata.version")
    return m.group(1)


def check_smoke(build_root: Path) -> None:
    """在构建目录里跑一次 index.js：能 import、能读目录、name 与目录名一致。"""
    script = (
        "import('./index.js').then(m => {"
        "  const c = m.loadSkillCatalog('./skills');"
        "  if (c.length !== 1) throw new Error('expected 1 skill, got ' + c.length);"
        "  console.log('ok', c[0].name, c[0].invocation.modelInvocable);"
        "}).catch(e => { console.error(e.message); process.exit(1); })"
    )
    proc = subprocess.run(["node", "--input-type=module", "-e", script],
                          cwd=build_root, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"插件冒烟测试失败：\n{proc.stdout}{proc.stderr}")
    if "ok rp-factory" not in proc.stdout:
        raise SystemExit(f"插件冒烟测试输出异常：{proc.stdout}{proc.stderr}")


def stage(build_root: Path, version: str) -> None:
    shutil.copy2(ADAPTER / "index.js", build_root / "index.js")
    shutil.copy2(ADAPTER / "cordis.patch.yml", build_root / "cordis.patch.yml")
    shutil.copy2(REPO / "LICENSE", build_root / "LICENSE")
    readme = ADAPTER / "README.md"
    if readme.is_file():
        shutil.copy2(readme, build_root / "README.md")
    shutil.copytree(SKILL, build_root / "skills" / "rp-factory",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "dry-run-*"))

    pkg = json.loads((ADAPTER / "package.json").read_text(encoding="utf-8"))
    pkg["version"] = version
    pkg["private"] = False
    (build_root / "package.json").write_text(
        json.dumps(pkg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="打 DSH 插件 tarball")
    ap.add_argument("--check", action="store_true", help="只校验不打包")
    args = ap.parse_args(argv)

    if not (SKILL / "SKILL.md").is_file():
        print("找不到 skills/rp-factory/SKILL.md")
        return 2
    version = skill_version()
    print(f"rp-factory-dsh v{version}")

    with tempfile.TemporaryDirectory() as td:
        build = Path(td)
        stage(build, version)
        check_smoke(build)
        if args.check:
            print("冒烟测试通过（未打包）")
            return 0

        DIST.mkdir(exist_ok=True)
        npm = shutil.which("npm") or shutil.which("npm.cmd") or "npm"
        proc = subprocess.run(
            [npm, "pack", "--pack-destination", str(DIST)],
            cwd=build, capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stdout + proc.stderr)
            return 1
        produced = sorted(DIST.glob("rp-factory-dsh-*.tgz"), key=lambda p: p.stat().st_mtime)
        if not produced:
            print("npm pack 没产出 tgz")
            return 1
        src = produced[-1]
        target = DIST / f"rp-factory-dsh-v{version}.tgz"
        if src != target:
            if target.exists():
                target.unlink()
            src.rename(target)
        size = target.stat().st_size / 1024
        print(f"出包：{target.relative_to(REPO)}（{size:.0f} KB）")
        print("安装：dsh plugin --profile <profile> add " + str(target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
