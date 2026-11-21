#!/usr/bin/env python3
"""把版本号同步到所有宿主清单。

版本号只有一处真相：`skills/rp-factory/SKILL.md` 的 `metadata.version`。
其余四处都是它的副本，宿主靠这些副本判断"有没有更新"——所以它们必须相等，
否则会出现"GitHub 上是新版、Claude Code 认为是旧版、于是永不更新"这种最难查的故障。

用法：
    python scripts/sync-manifests.py            # 写入
    python scripts/sync-manifests.py --check    # 只比对，漂移退出码 1
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL_FILE = REPO / "skills" / "rp-factory" / "SKILL.md"
CHANGELOG = REPO / "CHANGELOG.md"

VERSION_RE = re.compile(r"^  version:\s*(\S+)\s*$", re.M)

# (文件, 取/写版本的函数说明)
TARGETS = [
    "package.json",
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    "host-adapters/dsh/plugin/package.json",
]


def skill_version() -> str:
    m = VERSION_RE.search(SKILL_FILE.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("SKILL.md 里找不到 metadata.version")
    return m.group(1)


def places(data: dict) -> list[tuple]:
    """一份 JSON 里所有存版本号的位置：(读, 写)。"""
    out = []
    if "version" in data:
        out.append((lambda d: d.get("version"), lambda d, v: d.__setitem__("version", v)))
    for plugin in data.get("plugins", []) or []:
        if isinstance(plugin, dict) and "version" in plugin:
            out.append((lambda d, p=plugin: p.get("version"),
                        lambda d, v, p=plugin: p.__setitem__("version", v)))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="同步宿主清单里的版本号")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    version = skill_version()
    drift = []
    for rel in TARGETS:
        p = REPO / rel
        if not p.is_file():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        found = [get(data) for get, _ in places(data)]
        if not found:
            continue
        if all(v == version for v in found):
            continue
        drift.append((rel, found))
        if not args.check:
            for _, setter in places(data):
                setter(data, version)
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    head = re.search(r"^##\s+([0-9]+\.[0-9]+\.[0-9]+)", CHANGELOG.read_text(encoding="utf-8"), re.M)
    changelog_ok = bool(head) and head.group(1) == version

    if args.check:
        for rel, found in drift:
            print(f"[漂移] {rel}: {found} != {version}")
        if not changelog_ok:
            print(f"[漂移] CHANGELOG.md 首条不是 {version}")
        if drift or not changelog_ok:
            print("\n跑 python scripts/sync-manifests.py 同步版本号。")
            return 1
        print(f"清单一致（v{version}）")
        return 0

    for rel, found in drift:
        print(f"已同步 {rel}: {found} → {version}")
    if not changelog_ok:
        print(f"注意：CHANGELOG.md 首条不是 {version}，记得补一条")
        return 1
    print(f"清单一致（v{version}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
