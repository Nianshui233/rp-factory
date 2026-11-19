#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把做好的酒馆包导进正在运行的 SillyTavern，并回读校验。

只做三件可回滚的事：导入角色卡（同名覆盖）、必要时导入世界书、读回来自检。
不动设置、不动已有聊天记录。

用法:
    python scripts/st-import.py --st auto --card 最终产物/st/白潮.json
    python scripts/st-import.py --st http://127.0.0.1:8000 --card ... --no-verify
    python scripts/st-import.py --st auto --card ... --worldbook "最终产物/st/白潮 世界书.json" --name 白潮

退出码: 0 = 导入并自检通过；1 = 失败；2 = 用法/文件问题。
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


class Client:
    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.token = ""
        self.cookies: dict[str, str] = {}

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"X-CSRF-Token": self.token}
        if self.cookies:
            h["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        if extra:
            h.update(extra)
        return h

    def _absorb(self, resp) -> None:
        for raw in resp.headers.get_all("Set-Cookie") or []:
            pair = raw.split(";", 1)[0]
            if "=" in pair:
                k, v = pair.split("=", 1)
                self.cookies[k.strip()] = v.strip()

    def post_json(self, path: str):
        req = urllib.request.Request(
            self.base + path,
            data=b"{}",
            headers=self._headers({"Content-Type": "application/json"}),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            self._absorb(r)
            return json.loads(r.read().decode("utf-8", "replace"))

    def handshake(self) -> None:
        req = urllib.request.Request(self.base + "/csrf-token", headers=self._headers())
        with urllib.request.urlopen(req, timeout=10) as r:
            self._absorb(r)
            self.token = json.loads(r.read().decode("utf-8", "replace")).get("token", "")

    def post_file(self, path: str, file: Path, fields: dict[str, str]) -> tuple[int, str]:
        boundary = "----rp-factory-" + uuid.uuid4().hex
        ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        body = bytearray()
        for k, v in fields.items():
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
        body += (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"avatar\"; filename=\"{file.name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode()
        body += file.read_bytes() + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            self.base + path,
            data=bytes(body),
            headers=self._headers({"Content-Type": f"multipart/form-data; boundary={boundary}"}),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                self._absorb(r)
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")


def resolve_base(st: str) -> str:
    if st != "auto":
        return st
    here = Path(__file__).resolve().parent
    import subprocess

    out = subprocess.run(
        [sys.executable, str(here / "detect-sillytavern.py")],
        capture_output=True, text=True, encoding="utf-8",
    ).stdout
    try:
        data = json.loads(out)
    except ValueError:
        return ""
    running = data.get("running") or {}
    return running.get("url", "")


def main() -> int:
    ap = argparse.ArgumentParser(description="导入酒馆包到运行中的 SillyTavern 并自检")
    ap.add_argument("--st", default="auto", help="auto 或 http://127.0.0.1:8000")
    ap.add_argument("--card", required=True, help="角色卡 JSON")
    ap.add_argument("--worldbook", help="独立世界书 JSON（卡内已内嵌 character_book 时不需要）")
    ap.add_argument("--name", help="保留的文件名（默认取卡名）；同名会覆盖")
    ap.add_argument("--no-verify", action="store_true", help="只导入不回读")
    args = ap.parse_args()

    card_path = Path(args.card)
    if not card_path.is_file():
        print(f"找不到角色卡: {card_path}", file=sys.stderr)
        return 2
    try:
        card = json.loads(card_path.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"角色卡不是合法 JSON: {e}", file=sys.stderr)
        return 2

    data = card.get("data", card)
    card_name = str(data.get("name") or card_path.stem)
    preserved = (args.name or card_name).strip()
    embedded = data.get("character_book") or {}
    entries = embedded.get("entries") or []
    regex_n = len((data.get("extensions") or {}).get("regex_scripts") or [])

    base = resolve_base(args.st)
    if not base:
        print("没找到正在运行的 SillyTavern：先启动它（启动脚本通常在安装目录下），或用 --st 指定地址", file=sys.stderr)
        return 2

    cli = Client(base)
    try:
        cli.handshake()
    except (urllib.error.URLError, OSError) as e:
        print(f"连不上 {base}: {e}", file=sys.stderr)
        return 2

    print(f"目标 {base} · 卡 {card_name} · 内嵌条目 {len(entries)} · 内嵌正则 {regex_n} → 文件名 {preserved}.png")
    status, body = cli.post_file(
        "/api/characters/import",
        card_path,
        {"file_type": "json", "preserved_name": f"{preserved}.png"},
    )
    if status != 200:
        print(f"导入失败 HTTP {status}: {body[:300]}", file=sys.stderr)
        return 1
    try:
        file_name = json.loads(body).get("file_name")
    except ValueError:
        file_name = None
    print(f"导入成功: {file_name or preserved}")

    if args.worldbook:
        wb = Path(args.worldbook)
        if not wb.is_file():
            print(f"找不到世界书: {wb}", file=sys.stderr)
            return 2
        st2, body2 = cli.post_file("/api/worldinfo/import", wb, {})
        print(f"世界书导入 HTTP {st2}: {body2[:120] or 'ok'}")

    if args.no_verify:
        return 0

    try:
        chars = cli.post_json("/api/characters/all")
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"回读失败: {e}", file=sys.stderr)
        return 1

    avatar = f"{file_name or preserved}.png"
    hit = next((c for c in chars if c.get("avatar") == avatar), None)
    if not hit:
        print(f"自检失败：实例里找不到 {avatar}", file=sys.stderr)
        return 1
    hdata = hit.get("data") or {}
    hbook = (hdata.get("character_book") or {}).get("entries") or []
    hregex = (hdata.get("extensions") or {}).get("regex_scripts") or []
    checks = [
        ("卡名一致", hit.get("name") == card_name, f"{hit.get('name')!r} vs {card_name!r}"),
        ("内嵌条目数一致", len(hbook) == len(entries), f"{len(hbook)} vs {len(entries)}"),
        ("内嵌正则数一致", len(hregex) == regex_n, f"{len(hregex)} vs {regex_n}"),
        ("first_mes 非空", bool(hdata.get("first_mes")), (hdata.get("first_mes") or "")[:20]),
    ]
    ok = True
    for label, passed, detail in checks:
        print(f"  {'PASS' if passed else 'FAIL'} {label}（{detail}）")
        ok = ok and passed

    # 角色专属正则要用户点头才生效：不在白名单里时，ST 会在进聊天时弹一次确认框
    try:
        settings = cli.post_json("/api/settings/get")
        allowed = ((settings.get("extension_settings") or {}).get("character_allowed_regex") or [])
    except (urllib.error.URLError, OSError, ValueError):
        allowed = None
    if allowed is not None:
        if avatar in allowed:
            print(f"  PASS {avatar} 已在角色专属正则白名单里（进聊天不会再弹确认）")
        else:
            print(
                f"  WARN {avatar} 不在 character_allowed_regex 里：第一次进这个聊天，"
                "酒馆会弹「是否允许角色专属正则」，点允许即可（只弹一次）"
            )

    first = (hdata.get("first_mes") or "")
    if hregex and first and "<" in first:
        pat = hregex[0].get("findRegex") or ""
        key = first.strip().strip("<>").split()[0] if first.strip() else ""
        if key and key in pat:
            print(f"  PASS 首条消息的标签 {key} 能被第一条正则接住")
        else:
            print(f"  WARN 首条消息是 {first[:24]!r}，但第一条正则的 findRegex 里没出现它")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
