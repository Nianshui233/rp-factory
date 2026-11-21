#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""静默探测本机的 SillyTavern 与运行实例。

开局跑一次，结果写进契约 `project.sillytavern`；之后各阶段读契约，不再重复探测。

用法:
    python scripts/detect-sillytavern.py          # 打印 JSON
    python scripts/detect-sillytavern.py --quiet  # 只在找到时打印一行摘要

退出码恒为 0：找不到不是错误，只是 `found: false`。
"""
from __future__ import annotations

import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TIMEOUT = 0.6
PORT_SCAN = (8000, 8001, 8080, 8081, 5000, 3000)
SKIP_DIRS = {"node_modules", ".git", "$recycle.bin", "windows", "program files", "program files (x86)"}
TAVERN_HELPER_HINTS = ("JS-Slash-Runner", "Tavern-Helper", "tavern_helper", "TavernHelper")


def looks_like_st(path: Path) -> bool:
    try:
        if not (path / "server.js").exists():
            return False
        if not (path / "package.json").exists():
            return False
        pkg = json.loads((path / "package.json").read_text(encoding="utf-8", errors="replace"))
        name = str(pkg.get("name", "")).lower()
        if "sillytavern" in name:
            return True
        return (path / "src" / "server-main.js").exists() and (path / "public" / "index.html").exists()
    except (OSError, ValueError):
        return False


def read_config(path: Path) -> dict:
    """从 config.yaml 里抠几个值（不引 yaml 依赖）。"""
    out: dict = {}
    cfg = path / "config.yaml"
    if not cfg.exists():
        return out
    try:
        for line in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^(\w+):\s*(\S+)", line)
            if m and m.group(1) in {"port", "listen", "whitelistMode", "basicAuthMode", "dataRoot"}:
                out[m.group(1)] = m.group(2)
    except OSError:
        pass
    return out


def package_version(path: Path) -> str | None:
    try:
        pkg = json.loads((path / "package.json").read_text(encoding="utf-8", errors="replace"))
        return str(pkg.get("version") or "") or None
    except (OSError, ValueError):
        return None


def user_dirs(path: Path) -> list[Path]:
    data = path / "data"
    if not data.is_dir():
        return []
    return sorted(p for p in data.iterdir() if p.is_dir() and not p.name.startswith("_"))


def has_tavern_helper(path: Path) -> bool:
    third_party = path / "public" / "scripts" / "extensions" / "third-party"
    if not third_party.is_dir():
        return False
    for child in third_party.iterdir():
        if any(h.lower() in child.name.lower() for h in TAVERN_HELPER_HINTS):
            return True
    return False


def candidates() -> list[Path]:
    seen: list[Path] = []

    def add(p: str | Path | None) -> None:
        if not p:
            return
        path = Path(p).expanduser()
        if path.is_dir() and path not in seen:
            seen.append(path)

    for env in ("SILLYTAVERN_PATH", "ST_PATH", "SILLYTAVERN_DIR"):
        add(os.environ.get(env))
    home = Path.home()
    add(home / "SillyTavern")
    add(home / "Documents" / "SillyTavern")
    add(home / "Desktop" / "SillyTavern")

    roots = [Path("C:/"), Path("D:/"), Path("E:/"), Path("F:/"), Path("G:/"), Path("H:/")]
    for root in roots:
        if not root.exists():
            continue
        add(root / "SillyTavern")
        add(root / "AI" / "SillyTavern")
        # 再往下两层：D:/AI/xxx/SillyTavern 这种摆法很常见
        for depth1 in _safe_iterdir(root):
            if depth1.name.lower() in SKIP_DIRS:
                continue
            add(depth1 / "SillyTavern")
            if depth1.name.lower() in {"ai", "ai apps", "tools", "apps"}:
                for depth2 in _safe_iterdir(depth1):
                    add(depth2 / "SillyTavern")
                    add(depth2)
    return seen


def _safe_iterdir(path: Path):
    try:
        return [p for p in path.iterdir() if p.is_dir()]
    except OSError:
        return []


def probe(port: int) -> dict | None:
    url = f"http://127.0.0.1:{port}"
    try:
        with urllib.request.urlopen(f"{url}/version", timeout=TIMEOUT) as r:
            body = json.loads(r.read().decode("utf-8", "replace"))
        if "pkgVersion" not in body and "agent" not in body:
            return None
        return {
            "url": url,
            "port": port,
            "pkg_version": body.get("pkgVersion"),
            "agent": body.get("agent"),
            "git_branch": body.get("gitBranch"),
        }
    except (urllib.error.URLError, socket.timeout, ValueError, OSError):
        return None


def main() -> int:
    quiet = "--quiet" in sys.argv
    installs = []
    for path in candidates():
        if not looks_like_st(path):
            continue
        cfg = read_config(path)
        users = user_dirs(path)
        installs.append(
            {
                "path": str(path).replace("\\", "/"),
                "pkg_version": package_version(path),
                "config_port": int(cfg["port"]) if str(cfg.get("port", "")).isdigit() else 8000,
                "auth": "basic" if cfg.get("basicAuthMode", "false").strip("'\"") == "true" else "none",
                "users": [u.name for u in users],
                "user_dir": str((users[0] if users else path / "data" / "default-user")).replace("\\", "/"),
                "tavern_helper": has_tavern_helper(path),
            }
        )

    ports: list[int] = []
    for block in installs:
        if block["config_port"] not in ports:
            ports.append(block["config_port"])
    for p in PORT_SCAN:
        if p not in ports:
            ports.append(p)
    running = None
    for p in ports:
        found = probe(p)
        if found:
            running = found
            break

    result = {
        "found": bool(installs),
        "installs": installs,
        "running": running,
        "ready": bool(installs) and running is not None,
    }

    if quiet:
        if installs:
            first = installs[0]
            tail = f" · 运行中 {running['url']} ({running['pkg_version']})" if running else " · 未运行"
            print(f"ST: {first['path']} ({first['pkg_version'] or '?'}) · 酒馆助手 {'有' if first['tavern_helper'] else '无'}{tail}")
        else:
            print("ST: 未找到安装")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
