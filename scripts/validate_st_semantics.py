#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S 系列校验：只抓「不报错但机制没跑」的 SillyTavern 语义错误。

结构校验在 validate-st-package.py（C/R/W/X 系列），这里只查跨字段语义——
判据与源码锚点见 references/st-correctness.md。

    S-02 markdownOnly 与 promptOnly 同为 true          → 该条永远不匹配
    S-03 substituteRegex 不在 0/1/2                    → 只 warn 后按原样处理
    S-04 replaceString 引用了不存在的捕获组             → 那段替换静默变成空串
    S-07 maxDepth < 0 / minDepth < -1                  → 该条永远不生效
    S-10 position=4 缺 depth / position=7 缺 outletName → 注入位置失效
    S-11 order 缺失                                     → 排序 undefined
    S-13 keysecondary 非空但 selective 非 true          → 副关键词完全不参与
    S-19 未知宏                                         → 字面出现在聊天里（警告）
    S-20 用了酒馆助手宏但环境没有该扩展（需契约）        → 那行原样显示（警告）

用法：
    python scripts/validate_st_semantics.py <最终产物目录>
    python scripts/validate_st_semantics.py <卡.json> <正则.json> <世界书.json>
    python scripts/validate_st_semantics.py <目录> --contract 创作痕迹/contract.yaml
    python scripts/validate_st_semantics.py <目录> --json

退出码：0 无 error（warning 不算失败）；1 有 error；2 文件读不到 / 参数错误。
不依赖第三方库。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SEV_ERROR = "error"
SEV_WARN = "warning"

# S-19：ST 核心 + 酒馆助手会处理的宏名（大小写不敏感）。宁可放宽：这里只出警告。
KNOWN_MACROS = {
    # 角色/人格
    "char", "user", "persona", "description", "personality", "scenario", "group",
    "notchar", "model", "mesexamples", "charversion", "chardepthprompt", "creatornotes",
    "charprompt", "charjailbreak", "original", "personadescription", "match",
    # 变量
    "getvar", "setvar", "addvar", "incvar", "decvar", "getglobalvar", "setglobalvar",
    "addglobalvar", "incglobalvar", "decglobalvar",
    # 工具
    "newline", "trim", "noop", "input", "space", "random", "pick", "reverse",
    "time", "date", "weekday", "isotime", "isodate", "idle_duration",
    "datetimeformat", "time_utc", "outlet", "banned", "timediff", "roll",
    # 上下文
    "maxprompt", "maxprompttokens", "maxcontext", "maxcontexttokens",
    "maxresponse", "maxresponsetokens", "lastmessage", "lastmessageid",
    "lastusermessage", "lastcharmessage", "firstincludedmessageid",
    "firstdisplayedmessageid", "lastswipeid", "currentswipeid", "allchatrange",
    "lastgenerationtype", "ismobile",
    # 酒馆助手 / MVU
    "format_message_variable", "get_message_variable", "set_message_variable",
    "get_chat_variable", "set_chat_variable", "get_character_variable",
    "set_character_variable",
}

MACRO_RE = re.compile(r"\{\{(.+?)\}\}", re.S)
TAVERN_HELPER_MACRO_RE = re.compile(r"\{\{\s*format_message_variable\s*::")


# ------------------------------------------------------------------ 报告

class Report:
    def __init__(self) -> None:
        self.findings: list[dict] = []

    def add(self, severity: str, code: str, file: str, message: str) -> None:
        self.findings.append({"severity": severity, "code": code, "file": file, "message": message})

    def fail(self, code: str, file: str, message: str) -> None:
        self.add(SEV_ERROR, code, file, message)

    def warn(self, code: str, file: str, message: str) -> None:
        self.add(SEV_WARN, code, file, message)

    @property
    def errors(self) -> list[dict]:
        return [f for f in self.findings if f["severity"] == SEV_ERROR]

    @property
    def warnings(self) -> list[dict]:
        return [f for f in self.findings if f["severity"] == SEV_WARN]


# ------------------------------------------------------------------ 正则解析

def split_pattern(find_regex: str) -> tuple[str, str]:
    """把 `/body/flags` 拆成 (body, flags)；没有斜杠包装就整串当 body。"""
    text = find_regex.strip()
    if text.startswith("/"):
        last = text.rfind("/")
        if last > 0:
            return text[1:last], text[last + 1:]
    return text, ""


def scan_groups(body: str) -> tuple[int, set[str]]:
    """数捕获组数量并收集命名组名。跳过字符类、转义与非捕获结构。"""
    count = 0
    names: set[str] = set()
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "[":
            i += 1
            if i < n and body[i] in "^]":
                i += 1
            while i < n:
                if body[i] == "\\":
                    i += 2
                    continue
                if body[i] == "]":
                    i += 1
                    break
                i += 1
            continue
        if ch == "(":
            rest = body[i:i + 4]
            if body.startswith("(?:", i) or body.startswith("(?=", i) or body.startswith("(?!", i):
                i += 3
                continue
            if body.startswith("(?<=", i) or body.startswith("(?<!", i) or body.startswith("(?P=", i):
                i += 4
                continue
            if body.startswith("(?#", i):
                depth = 1
                i += 3
                while i < n and depth:
                    if body[i] == "\\":
                        i += 2
                        continue
                    if body[i] == "(":
                        depth += 1
                    elif body[i] == ")":
                        depth -= 1
                    i += 1
                continue
            m = re.match(r"\(\?(?:P)?<([A-Za-z_][A-Za-z0-9_]*)>", body[i:i + 60])
            if m:
                count += 1
                names.add(m.group(1))
                i += m.end()
                continue
            if re.match(r"\(\?[aiLmsux\-]*[:)]", body[i:i + 12]):
                i += 2
                continue
            count += 1
            i += 1
            continue
        i += 1
    return count, names


REF_NUM_RE = re.compile(r"\$(\d+)")
REF_NAME_RE = re.compile(r"\$<([^>]+)>")


def check_replace_groups(script: dict, file: str, rep: Report) -> None:
    find_regex = script.get("findRegex") or ""
    replace = script.get("replaceString") or ""
    if not find_regex or not isinstance(replace, str):
        return
    body, _flags = split_pattern(find_regex)
    total, names = scan_groups(body)
    label = script.get("scriptName") or script.get("id") or "未命名脚本"

    for raw in REF_NUM_RE.findall(replace):
        index = int(raw)
        if index == 0:
            continue
        if index > total:
            rep.fail("S-04", file,
                     f"[{label}] replaceString 引用了 ${index}，但 findRegex 只有 {total} 个捕获组："
                     f"ST 会把这一段替换成空串（不是保留字面量）。若本意是字面美元数字，写 $${raw} 或改文案。")
    for name in REF_NAME_RE.findall(replace):
        if name not in names:
            rep.fail("S-04", file,
                     f"[{label}] replaceString 引用了命名组 $<{name}>，但 findRegex 里没有该组"
                     f"（现有：{sorted(names) or '无'}）：整段会被替换成空串。")


def check_regex_scripts(scripts: list, file: str, rep: Report) -> None:
    for script in scripts:
        if not isinstance(script, dict):
            continue
        label = script.get("scriptName") or script.get("id") or "未命名脚本"

        if script.get("markdownOnly") is True and script.get("promptOnly") is True:
            rep.fail("S-02", file,
                     f"[{label}] markdownOnly 与 promptOnly 同时为 true：engine.js 的两个分支互斥，"
                     f"这一条永远不会匹配。按用途只留一个。")

        sub = script.get("substituteRegex", 0)
        try:
            sub_value = int(sub)
        except (TypeError, ValueError):
            sub_value = None
        if sub_value not in (0, 1, 2):
            rep.fail("S-03", file,
                     f"[{label}] substituteRegex = {sub!r}，只认 0(原样)/1(RAW 替换宏)/2(替换后转义)；"
                     f"其它值只 console.warn 后按原样处理。")

        max_depth = script.get("maxDepth")
        if isinstance(max_depth, (int, float)) and not isinstance(max_depth, bool) and max_depth < 0:
            rep.fail("S-07", file,
                     f"[{label}] maxDepth = {max_depth}：只有 >= 0 才生效，负数等于这一条永不执行"
                     f"（想表达不限就写 null）。")
        min_depth = script.get("minDepth")
        if isinstance(min_depth, (int, float)) and not isinstance(min_depth, bool) and min_depth < -1:
            rep.fail("S-07", file,
                     f"[{label}] minDepth = {min_depth}：只有 >= -1 才生效，越小越不可能是本意。")

        check_replace_groups(script, file, rep)


# ------------------------------------------------------------------ 世界书

def check_worldbook(book: dict, file: str, rep: Report) -> None:
    entries = book.get("entries")
    if isinstance(entries, dict):
        items = list(entries.items())
    elif isinstance(entries, list):
        items = list(enumerate(entries))
    else:
        return

    for key, entry in items:
        if not isinstance(entry, dict):
            continue
        label = entry.get("comment") or f"#{key}"

        position = entry.get("position")
        if position == 4:
            depth = entry.get("depth")
            if not isinstance(depth, (int, float)) or isinstance(depth, bool):
                rep.fail("S-10", file,
                         f"[{label}] position=4（按深度注入）但没有数字 depth：条目会落到默认位置，"
                         f"以为插在聊天流里的内容其实插在角色定义后面。")
        if position == 7:
            outlet = entry.get("outletName")
            if not isinstance(outlet, str) or not outlet.strip():
                rep.fail("S-10", file,
                         f"[{label}] position=7（outlet）但 outletName 为空：内容不会被任何 "
                         f"{{{{outlet::…}}}} 取到。")

        order = entry.get("order")
        if not isinstance(order, (int, float)) or isinstance(order, bool):
            rep.fail("S-11", file,
                     f"[{label}] order 缺失或不是数字：世界书按 order 倒序插入，undefined 会让排序失效。")

        logic = entry.get("selectiveLogic", 0)
        if logic not in (0, 1, 2, 3):
            rep.fail("S-13", file,
                     f"[{label}] selectiveLogic = {logic!r}，只认 0(and_any)/1(not_all)/2(not_any)/3(and_all)。")
        secondary = entry.get("keysecondary") or []
        if isinstance(secondary, list) and secondary and entry.get("selective") is not True:
            rep.fail("S-13", file,
                     f"[{label}] 有 keysecondary 但 selective 不是 true：副关键词完全不参与判定，"
                     f"要么开 selective，要么删掉副关键词。")


# ------------------------------------------------------------------ 未知宏

def check_macros(text: str, file: str, rep: Report, where: str) -> None:
    for raw in MACRO_RE.findall(text or ""):
        token = raw.strip()
        if not token or token.startswith("/"):
            continue
        name = re.split(r"::|:", token, maxsplit=1)[0].strip().lower()
        if not name or name in KNOWN_MACROS:
            continue
        if re.fullmatch(r"[-+]?\d+", name):
            continue
        rep.warn("S-19", file,
                 f"[{where}] 未知宏 {{{{{token[:40]}}}}}：ST 只替换已注册的宏，未知宏会字面出现在聊天里。")


def check_tavern_helper(text: str, file: str, rep: Report, where: str,
                        tavern_helper: bool | None) -> None:
    if tavern_helper is False and TAVERN_HELPER_MACRO_RE.search(text or ""):
        rep.warn("S-20", file,
                 f"[{where}] 用了 {{{{format_message_variable::…}}}}，但契约里 "
                 f"project.sillytavern.tavern_helper = false：没装酒馆助手时这行原样显示，MVU 也不会跑。")


# ------------------------------------------------------------------ 项目遍历

def _read_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def find_files(root: Path) -> dict[str, Path]:
    """在项目或最终产物目录里认出三件套。"""
    out_dir = root / "最终产物" if (root / "最终产物").is_dir() else root
    found: dict[str, Path] = {}
    regex_path = out_dir / "正则.json"
    if regex_path.is_file():
        found["regex"] = regex_path
    cards = [p for p in sorted(out_dir.glob("*.json"))
             if "世界书" not in p.name and p.name not in {"正则.json", "frontend-prompt.json"}
             and "（纯净）" in p.name]
    if not cards:
        cards = [p for p in sorted(out_dir.glob("*.json"))
                 if "世界书" not in p.name and p.name != "正则.json"]
    if cards:
        found["card"] = cards[0]
    books = [p for p in sorted(out_dir.glob("*.json")) if "世界书" in p.name]
    if books:
        found["book"] = books[0]
    return found


def contract_tavern_helper(contract_path: Path | None) -> bool | None:
    if contract_path is None or not contract_path.is_file():
        return None
    try:
        text = contract_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"tavern_helper\s*:\s*(true|false)", text, re.I)
    if not m:
        return None
    return m.group(1).lower() == "true"


def check_project(root: Path, contract: Path | None = None) -> list[dict]:
    rep = Report()
    files = find_files(root)
    if contract is None:
        auto = root / "创作痕迹" / "contract.yaml"
        contract = auto if auto.is_file() else None
    helper = contract_tavern_helper(contract)

    if "card" in files:
        card = _read_json(files["card"])
        name = files["card"].name
        if isinstance(card, dict):
            data = card.get("data") if isinstance(card.get("data"), dict) else card
            for field in ("description", "first_mes", "mes_example", "system_prompt",
                          "post_history_instructions", "scenario", "personality"):
                value = data.get(field)
                if isinstance(value, str):
                    check_macros(value, name, rep, field)
                    check_tavern_helper(value, name, rep, field, helper)
            for alt in data.get("alternate_greetings") or []:
                if isinstance(alt, str):
                    check_macros(alt, name, rep, "alternate_greetings")
                    check_tavern_helper(alt, name, rep, "alternate_greetings", helper)

    if "regex" in files:
        payload = _read_json(files["regex"])
        name = files["regex"].name
        scripts = payload if isinstance(payload, list) else (
            [payload] if isinstance(payload, dict) else [])
        check_regex_scripts(scripts, name, rep)
        blob = json.dumps(scripts, ensure_ascii=False)
        check_tavern_helper(blob, name, rep, "正则", helper)
        check_macros(blob, name, rep, "正则")

    if "book" in files:
        book = _read_json(files["book"])
        name = files["book"].name
        if isinstance(book, dict):
            check_worldbook(book, name, rep)
            entries = book.get("entries")
            values = entries.values() if isinstance(entries, dict) else (entries or [])
            for entry in values:
                if not isinstance(entry, dict):
                    continue
                label = entry.get("comment") or "条目"
                content = entry.get("content")
                if isinstance(content, str):
                    check_macros(content, name, rep, label)
                    check_tavern_helper(content, name, rep, label, helper)

    return rep.findings


# ------------------------------------------------------------------ CLI

def _collect(argv: list[str]) -> tuple[list[str], Path | None, bool]:
    paths: list[str] = []
    contract: Path | None = None
    as_json = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--contract":
            i += 1
            if i < len(argv):
                contract = Path(argv[i])
        elif arg == "--json":
            as_json = True
        elif arg in ("-h", "--help"):
            print(__doc__)
            raise SystemExit(0)
        elif arg.startswith("-"):
            print(f"未知参数：{arg}", file=sys.stderr)
            raise SystemExit(2)
        else:
            paths.append(arg)
        i += 1
    return paths, contract, as_json


def main(argv: list[str]) -> int:
    paths, contract, as_json = _collect(argv)
    if not paths:
        paths = ["."]
    findings: list[dict] = []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            print(f"路径不存在：{path}", file=sys.stderr)
            return 2
        findings.extend(check_project(path, contract))

    errors = [f for f in findings if f["severity"] == SEV_ERROR]
    warnings = [f for f in findings if f["severity"] == SEV_WARN]

    if as_json:
        print(json.dumps({"findings": findings, "errors": len(errors), "warnings": len(warnings)},
                         ensure_ascii=False, indent=2))
    else:
        for f in findings:
            mark = "FAIL" if f["severity"] == SEV_ERROR else "WARN"
            print(f"[{mark}] {f['code']} {f['file']}：{f['message']}")
        if errors:
            print(f"\n{len(errors)} 个会让机制静默失效的问题（{len(warnings)} 条警告）。"
                  f"判据见 references/st-correctness.md。")
        elif warnings:
            print(f"\n结构没问题，{len(warnings)} 条警告值得看一眼。")
        else:
            print("S 系列全过：没发现会静默失效的写法。")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
