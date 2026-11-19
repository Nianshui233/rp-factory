#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 RP-Factory 的三件套（纯净卡 / 正则 / 世界书）导进正在运行的 SillyTavern，并回读校验。

三件里两件能脚本导，正则只能校验（`extension_settings` 在运行中的客户端手上，服务端写完会被盖掉）：
  角色卡   POST /api/characters/import   （字段 avatar，preserved_name = <卡名>.png，同名覆盖）
  世界书   POST /api/worldinfo/import    （字段 avatar，**文件名即书名**）
  正则     只验（scriptName / findRegex 齐全、node 能编译、$1 有捕获组）→ 让用户去界面导

用法:
    python scripts/st-import.py --st auto --pkg 最终产物
    python scripts/st-import.py --st http://127.0.0.1:8000 --pkg . --no-verify
    python scripts/st-import.py --st auto --card a.json --regex r.json --worldbook w.json

退出码: 0 = 导入并自检通过；1 = 失败；2 = 用法/文件问题。
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import subprocess
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

    def post_json(self, path: str, payload: dict | None = None):
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload or {}, ensure_ascii=False).encode("utf-8"),
            headers=self._headers({"Content-Type": "application/json"}),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            self._absorb(r)
            raw = r.read().decode("utf-8", "replace")
        try:
            return json.loads(raw)
        except ValueError:
            return raw

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
            with urllib.request.urlopen(req, timeout=120) as r:
                self._absorb(r)
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")


def resolve_base(st: str) -> str:
    if st != "auto":
        return st
    here = Path(__file__).resolve().parent
    out = subprocess.run(
        [sys.executable, str(here / "detect-sillytavern.py")],
        capture_output=True, text=True, encoding="utf-8",
    ).stdout
    try:
        data = json.loads(out)
    except ValueError:
        return ""
    return (data.get("running") or {}).get("url", "")


def find_pkg(pkg: Path) -> tuple[Path | None, Path | None, Path | None]:
    card = regex = book = None
    for f in sorted(pkg.glob("*.json")):
        low = f.name.lower()
        if "世界书" in f.name or "worldbook" in low:
            book = book or f
        elif "正则" in f.name or "regex" in low:
            regex = regex or f
        elif "（纯净）" in f.name or "(纯净)" in f.name or "pure" in low:
            card = card or f
        else:
            card = card or f
    return card, regex, book


def check_regex_file(regex_path: Path) -> tuple[bool, str, list[str]]:
    """只校验正则文件，不写设置。

    为什么不写 settings.json：运行中的酒馆是**客户端**持有 extension_settings，
    服务端写完文件后，页面一刷新/一保存就会用内存里的旧数组把它盖掉（实测：
    写完 2 条，打开一次角色卡后磁盘又变回 0 条）。正则只能从界面导入，
    或者等酒馆关掉再写文件。
    """
    try:
        scripts = json.loads(regex_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return False, f"读不了：{e}", []
    if isinstance(scripts, dict):
        scripts = [scripts]
    if not isinstance(scripts, list) or not scripts:
        return False, "形状不对：应该是一个数组", []

    names: list[str] = []
    for i, s in enumerate(scripts, 1):
        if not isinstance(s, dict):
            return False, f"第 {i} 条不是对象", names
        name = str(s.get("scriptName") or "").strip()
        pattern = str(s.get("findRegex") or "")
        if not name:
            return False, f"第 {i} 条没有 scriptName", names
        if not pattern:
            return False, f"第 {i} 条没有 findRegex", names
        # 用 node 真编译一遍，比看字符串靠谱
        try:
            r = subprocess.run(["node", "--eval",
                                "new RegExp(process.argv[1]);process.exit(0)", pattern],
                               capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as e:
            return False, f"第 {i} 条没法验证（{e}）", names
        if r.returncode != 0:
            msg = (r.stderr or "").strip().splitlines()
            return False, f"第 {i} 条 findRegex 编译失败：{msg[-1] if msg else '?'}", names
        if "$1" in str(s.get("replaceString") or "") and not re.search(r"\([^?]", pattern):
            return False, f"第 {i} 条用了 $1，但 findRegex 没有捕获组", names
        names.append(name)
    return True, f"{len(names)} 条，findRegex 都能编译", names


def main() -> int:
    ap = argparse.ArgumentParser(description="把三件套导进运行中的 SillyTavern 并自检")
    ap.add_argument("--st", default="auto", help="auto 或 http://127.0.0.1:8000")
    ap.add_argument("--pkg", help="三件套所在目录（自动认卡 / 正则 / 世界书）")
    ap.add_argument("--card", help="角色卡 JSON（覆盖 --pkg 的自动识别）")
    ap.add_argument("--regex", help="正则 JSON")
    ap.add_argument("--worldbook", help="世界书 JSON")
    ap.add_argument("--name", help="保留的文件名（默认取卡名）；同名会覆盖")
    ap.add_argument("--no-verify", action="store_true", help="只导入不回读")
    args = ap.parse_args()

    card_path = regex_path = book_path = None
    if args.pkg:
        pkg = Path(args.pkg)
        if not pkg.is_dir():
            print(f"找不到目录: {pkg}", file=sys.stderr)
            return 2
        card_path, regex_path, book_path = find_pkg(pkg)
    card_path = Path(args.card) if args.card else card_path
    regex_path = Path(args.regex) if args.regex else regex_path
    book_path = Path(args.worldbook) if args.worldbook else book_path

    if card_path is None or not card_path.is_file():
        print(f"找不到角色卡: {card_path}（用 --pkg 或 --card 指定）", file=sys.stderr)
        return 2
    try:
        card = json.loads(card_path.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"角色卡不是合法 JSON: {e}", file=sys.stderr)
        return 2

    data = card.get("data", card)
    card_name = str(data.get("name") or card_path.stem)
    preserved = (args.name or card_name).strip()
    world = str(((data.get("extensions") or {}).get("world")) or "")

    own_names: list[str] = []
    if regex_path and regex_path.is_file():
        try:
            src = json.loads(regex_path.read_text(encoding="utf-8"))
            src = src if isinstance(src, list) else [src]
            own_names = [str(s.get("scriptName") or "") for s in src
                         if isinstance(s, dict) and s.get("scriptName")]
        except (OSError, ValueError):
            own_names = []

    if data.get("character_book"):
        print("提醒：卡里有 character_book，但三件套交付不该内嵌；导入后会有两本同名书", file=sys.stderr)

    base = resolve_base(args.st)
    if not base:
        print("没找到正在运行的 SillyTavern：先启动它，或用 --st 指定地址", file=sys.stderr)
        return 2

    cli = Client(base)
    try:
        cli.handshake()
    except (urllib.error.URLError, OSError) as e:
        print(f"连不上 {base}: {e}", file=sys.stderr)
        return 2

    print(f"目标 {base} · 卡 {card_name} · 世界书名 {world or '（未写）'}")

    # 1 角色卡
    status, body = cli.post_file(
        "/api/characters/import",
        card_path,
        {"file_type": "json", "preserved_name": f"{preserved}.png"},
    )
    if status != 200:
        print(f"卡导入失败 HTTP {status}: {body[:300]}", file=sys.stderr)
        return 1
    try:
        file_name = json.loads(body).get("file_name")
    except ValueError:
        file_name = None
    print(f"  卡       导入成功 → {file_name or preserved}.png")

    # 2 世界书
    book_ok = None
    if book_path and book_path.is_file():
        st2, body2 = cli.post_file("/api/worldinfo/import", book_path, {})
        book_ok = st2 == 200
        print(f"  世界书   {'导入成功' if book_ok else f'导入失败 HTTP {st2}'} → 书名取文件名 {book_path.stem!r}")
        if not book_ok:
            print(f"           {body2[:200]}", file=sys.stderr)

    # 3 正则：只校验，界面导入（服务端写设置会被运行中的客户端盖掉）
    regex_ok = None
    regex_note = ""
    if regex_path and regex_path.is_file():
        regex_ok, regex_note, _ = check_regex_file(regex_path)
        print(f"  正则     {'校验通过' if regex_ok else '校验失败'}：{regex_note}")

    if args.no_verify:
        return 0 if (book_ok is not False and regex_ok is not False) else 1

    ok = True

    # 回读：卡
    try:
        chars = cli.post_json("/api/characters/all")
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"回读角色失败: {e}", file=sys.stderr)
        return 1
    avatar = f"{file_name or preserved}.png"
    hit = next((c for c in chars if isinstance(c, dict) and c.get("avatar") == avatar), None)
    if not hit:
        print(f"  FAIL 实例里找不到 {avatar}", file=sys.stderr)
        return 1
    hdata = hit.get("data") or {}
    embeds = (hdata.get("character_book") or {}).get("entries") or []
    checks = [
        ("卡名一致", hit.get("name") == card_name, f"{hit.get('name')!r} vs {card_name!r}"),
        ("first_mes 非空", bool(hdata.get("first_mes")), (hdata.get("first_mes") or "")[:24]),
        ("extensions.world 一致", str(((hdata.get("extensions") or {}).get("world")) or "") == world,
         str(((hdata.get("extensions") or {}).get("world")) or "")),
        ("卡里没内嵌世界书", not embeds, f"内嵌 {len(embeds)} 条"),
    ]

    # 回读：世界书
    if book_ok:
        try:
            book = cli.post_json("/api/worldinfo/get", {"name": book_path.stem})
            ents = (book or {}).get("entries") or {}
            checks.append(("世界书条目数 > 0", bool(ents), f"{len(ents)} 条"))
            const_chars = sum(len(str(e.get("content") or "")) for e in ents.values()
                              if isinstance(e, dict) and e.get("constant"))
            checks.append(("常驻条目 ≤ 8000 字", const_chars <= 8000, f"{const_chars} 字"))
        except (urllib.error.URLError, OSError, ValueError) as e:
            checks.append(("世界书可回读", False, str(e)[:40]))

    # 回读：正则只能验文件（界面导入是用户动作，脚本看不到）
    if regex_ok:
        checks.append(("正则文件可导入", True, regex_note))

    for label, passed, detail in checks:
        print(f"  {'PASS' if passed else 'FAIL'} {label}（{detail}）")
        ok = ok and passed

    first = str(hdata.get("first_mes") or "")
    if regex_ok and first.strip() and "<" in first:
        tag = first.strip().strip("<>").split()[0]
        try:
            src = json.loads(regex_path.read_text(encoding="utf-8"))
            src = src if isinstance(src, list) else [src]
            pats = [str(s.get("findRegex") or "") for s in src if isinstance(s, dict)]
            if any(tag in p for p in pats):
                print(f"  PASS 首条消息的标签 {tag} 能被已导入的正则接住")
            else:
                print(f"  WARN 首条消息是 {first[:24]!r}，没有正则的 findRegex 里出现 {tag}")
        except (urllib.error.URLError, OSError, ValueError):
            pass

    print("  下一步 打开酒馆：设置 → 扩展 → 正则 → 导入，选那份正则文件（数组会一次导完）；再确认「消息渲染」已打开")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
