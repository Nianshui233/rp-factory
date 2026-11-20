#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""前端界面自检：查 HTML 骨架、外链、危险 API、内联脚本里的 HTML 实体。

用法:
    python scripts/validate-frontend.py 最终产物/statusbar-ui.html
    python scripts/validate-frontend.py 最终产物/          # 递归找 *.html

退出码: 0 = 全过或只有警告, 1 = 有失败, 2 = 用法/读取错误。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ENTITY_RE = re.compile(r"&(?:[a-zA-Z][a-zA-Z0-9]{1,10}|#\d{1,6}|#x[0-9a-fA-F]{1,6});")
SCRIPT_RE = re.compile(r"<script\b[^>]*>([\s\S]*?)</script>", re.I)
TAG_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)")

# 这些标签允许留在静态 HTML 里（我们只做片段级检查，不追求完整 DOM）
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


def check(path: Path) -> tuple[list[str], list[str], list[str]]:
    fail: list[str] = []
    warn: list[str] = []
    ok: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")

    # F01 骨架：酒馆助手靠这三个串判定"是不是前端界面"
    missing = [t for t in ("<!DOCTYPE html", "<html", "<head", "<body") if t.lower() not in text.lower()]
    if missing:
        fail.append(f"F01 缺前端骨架标记: {', '.join(missing)}（isFrontend 只认 html> / <head> / <body）")
    else:
        ok.append("F01 骨架齐（doctype / html / head / body）")

    # F02 外链：iframe 里断网就废，且酒馆助手不建议外链
    ext = []
    for m in re.finditer(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", text, re.I):
        url = m.group(1).strip()
        if url.startswith(("http://", "https://", "//")):
            ext.append(url[:60])
    if re.search(r"@import\s", text):
        ext.append("@import")
    for m in re.finditer(r"url\(\s*['\"]?(https?:)?//", text, re.I):
        ext.append("url(" + m.group(0)[:40])
    if ext:
        fail.append(f"F02 引用了外链（{len(ext)} 处）: {', '.join(sorted(set(ext)))}")
    else:
        ok.append("F02 无外链")

    # F03 危险 API
    bad = [k for k in ("eval(", "new Function", "document.write") if k in text]
    if bad:
        fail.append(f"F03 用了 {', '.join(bad)}")
    else:
        ok.append("F03 无 eval / new Function / document.write")

    # F04 内联脚本里的 HTML 实体（会把整段 JS 变成 SyntaxError）
    hit = []
    for i, m in enumerate(SCRIPT_RE.finditer(text)):
        for em in ENTITY_RE.finditer(m.group(1)):
            line = m.group(1)[: em.start()].count("\n") + 1
            hit.append((i, line, em.group(0)))
    if hit:
        sample = ", ".join(f"script#{i}:{ln} {ent}" for i, ln, ent in hit[:5])
        fail.append(
            f"F04 内联脚本里有 {len(hit)} 处 HTML 实体（{sample}）：消息管线会多吃一层解码，"
            "`&amp;` 变 `&`、`&#39;` 变 `'`，整段 JS 语法错误、界面空白。改用 '\\x26amp;' 这类写法"
        )
    else:
        ok.append("F04 内联脚本无 HTML 实体")

    # F05 硬编码 vh（酒馆助手会改 min-height，写死会错位）
    vh = re.findall(r"(?:min-|max-)?height\s*:\s*[\d.]+vh", text)
    if vh:
        warn.append(f"F05 硬编码视口高度 {len(vh)} 处（{', '.join(vh[:3])}）：酒馆助手会替换 min-height，建议用自然高度或 max-height")
    else:
        ok.append("F05 无硬编码 vh 高度")

    # F06 用 innerHTML 但没定义 esc()
    if "innerHTML" in text and not re.search(r"function\s+esc\s*\(", text):
        warn.append("F06 用了 innerHTML 却没有 esc()：字段值里的 < > & 会破坏结构")

    # F07 标签配平（只看块级容器，不校验嵌套顺序）
    stack: list[str] = []
    broken = None
    for m in TAG_RE.finditer(text):
        name = m.group(1).lower()
        if name in VOID or name in ("script", "style"):
            continue
        end = text.find(">", m.end())
        raw = text[m.start(): end + 1] if end != -1 else ""
        if raw.rstrip().endswith("/>"):
            continue
        close = f"</{name}>"
        # 自闭合的成对标签用简单计数法
        if text.count(f"<{name}") > text.count(close) and name not in stack:
            stack.append(name)
        elif close in text and name in stack:
            stack.remove(name)
    if stack:
        warn.append(f"F07 可能未闭合的标签: {', '.join(sorted(set(stack))[:5])}（无误可忽略）")

    # F08 单文件自足：不该有 <link rel=stylesheet> 指向本地也找不到的文件
    for m in re.finditer(r"""<link[^>]*href\s*=\s*["']([^"']+)["'][^>]*>""", text, re.I):
        href = m.group(1)
        if not href.startswith(("http", "//", "data:")):
            fail.append(f"F08 引用了外部样式文件 {href}：必须内联")
    if not any(f.startswith("F08") for f in fail):
        ok.append("F08 样式与脚本均内联")

    # F09 可访问的最小两条：键盘能到、有可访问名（其余十条靠人看，见 references/frontend-conventions.md）
    clickable = re.findall(r"<(div|span)([^>]*onclick\s*=[^>]*)>", text, re.I)
    keyboardless = [m[1][:60] for m in clickable
                    if not re.search(r"role\s*=|tabindex\s*=", m[1], re.I)]
    if keyboardless:
        warn.append(f"F09 {len(keyboardless)} 个 onclick 挂在 div/span 上且没有 role/tabindex："
                    f"键盘与读屏都到不了，换成 <button> 或补 role+tabindex+键盘处理")
    empty_btn = re.findall(r"<button[^>]*>\s*</button>", text, re.I)
    if empty_btn:
        warn.append(f"F09 {len(empty_btn)} 个 <button> 里没有文字也没有图标标签："
                    f"补 aria-label，否则读屏只念「按钮」")
    if not keyboardless and not empty_btn:
        ok.append("F09 可点击元素键盘可达、有可访问名")

    # F10 手写事件名字符串：eventOn / eventSource.on 的常量值是别名，键名 ≠ 字符串
    #   tavern_events.CHAT_CHANGED 的值是 'chat_id_changed'，CHARACTER_DELETED 的值是 'characterDeleted'
    literal_events = []
    for pat in (
        r"\bevent(?:On|Once|Emit|EmitAndWait|RemoveListener|OnButton)\(\s*['\"]",
        r"\beventSource\.(?:on|once|emit|removeListener)\(\s*['\"]",
    ):
        literal_events.extend(m.group(0)[:40] for m in re.finditer(pat, text))
    if literal_events:
        warn.append(
            f"F10 {len(literal_events)} 处事件名写成了字符串（{literal_events[0]}…）："
            "常量值不等于键名（CHAT_CHANGED 实际是 'chat_id_changed'，CHARACTER_DELETED 是 'characterDeleted'），"
            "手写必错，改用 tavern_events.* / iframe_events.* / Mvu.events.*（references/tavern-helper.md 第七节）"
        )
    else:
        ok.append("F10 事件名走常量")

    # F11 相对路径资源：srcdoc 模式不加 <base>，相对路径会落到 about:srcdoc
    rel = []
    for m in re.finditer(r"<(?:img|script|iframe|source|audio|video|embed)\b[^>]*\bsrc\s*=\s*['\"]([^'\"]+)['\"]", text, re.I):
        url = m.group(1).strip()
        if url.startswith(("http://", "https://", "//", "/", "data:", "blob:", "#")) or url.startswith("{{"):
            continue
        rel.append(url[:50])
    for m in re.finditer(r"url\(\s*['\"]?([^)'\"]+)", text, re.I):
        url = m.group(1).strip()
        if url.startswith(("http://", "https://", "//", "/", "data:", "blob:", "#", "var(")) or url.startswith("{{"):
            continue
        rel.append(url[:50])
    if rel:
        warn.append(
            f"F11 {len(rel)} 处相对路径资源（{', '.join(sorted(set(rel))[:3])}）："
            "楼层 iframe 默认用 srcdoc，不带 <base>，相对路径解析到 about:srcdoc 会 404。"
            "改成 data: URI 内联，或酒馆内绝对路径 /img/…、/characters/…（tavern-helper.md 第二节）"
        )
    else:
        ok.append("F11 无相对路径资源")

    # F12 直接操作父窗口文档：跨 frame 写 DOM 会绕开渲染与事件链
    if re.search(r"\b(?:window\.)?(?:parent|top)\.document\b", text):
        warn.append(
            "F12 直接操作父窗口 document：楼层 iframe 是同源但独立渲染上下文，"
            "改父文档不会触发酒馆的重渲染与事件，也会在切换聊天后残留。"
            "改用 setChatMessages({message_id}) 重渲染本楼，或走 TavernHelper 接口（tavern-helper.md 第五节）"
        )
    else:
        ok.append("F12 不直接操作父文档")

    # F13 refresh:'all'：整条聊天重载并触发 CHAT_CHANGED，是「刷新一楼」的重锤
    if re.search(r"refresh\s*:\s*['\"]all['\"]", text):
        warn.append(
            "F13 用了 refresh: 'all'：会重载整条聊天、触发 CHAT_CHANGED 并打断其它界面。"
            "只想刷新被改的楼层就用 'affected'（默认值）（tavern-helper.md 第五节）"
        )
    else:
        ok.append("F13 没有用 refresh:'all'")

    # F14 定时器泄漏：iframe 卸载时 TH 只自动清事件监听，定时器要自己收
    if "setInterval(" in text and "clearInterval(" not in text:
        warn.append(
            "F14 起了 setInterval 却没有 clearInterval：界面反复重渲染后旧定时器还在跑，"
            "会重复写变量、抢 DOM。在 pagehide 或重渲染入口里清掉（tavern-helper.md 第三节）"
        )
    else:
        ok.append("F14 无裸定时器")

    return fail, warn, ok


def main() -> int:
    ap = argparse.ArgumentParser(description="前端界面自检（骨架/外链/实体/危险 API）")
    ap.add_argument("paths", nargs="+", help="HTML 文件或目录")
    ap.add_argument("--quiet", action="store_true", help="只打印失败与警告")
    args = ap.parse_args()

    files: list[Path] = []
    for p in map(Path, args.paths):
        if p.is_dir():
            files.extend(sorted(p.rglob("*.html")))
        elif p.is_file():
            files.append(p)
        else:
            print(f"找不到 {p}", file=sys.stderr)
            return 2
    if not files:
        print("没有找到 .html 文件", file=sys.stderr)
        return 2

    total_fail = total_warn = 0
    for f in files:
        fail, warn, ok = check(f)
        total_fail += len(fail)
        total_warn += len(warn)
        print(f"\n== {f}")
        if not args.quiet:
            for line in ok:
                print(f"  ok   {line}")
        for line in warn:
            print(f"  WARN {line}")
        for line in fail:
            print(f"  FAIL {line}")

    print(f"\n{len(files)} 个文件 · 失败 {total_fail} · 警告 {total_warn}")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
