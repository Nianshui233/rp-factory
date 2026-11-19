#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 RP-Factory 交付的 SillyTavern 包（角色卡 JSON + 世界书 JSON + 内嵌正则）。

规则抄自 SillyTavern 本体的：
- src/validator/TavernCardValidator.js       卡片 v1/v2/v3 必填字段
- src/endpoints/characters.js  importFromJson / readFromV2   顶层字段与 data 的同步关系
- src/endpoints/characters.js  convertCharacterBook           character_book 的形状
- public/scripts/world-info.js newWorldInfoEntryDefinition    世界书条目字段与类型
- public/scripts/extensions/regex/index.js                   正则脚本字段
- public/scripts/utils.js      regexFromString               正则能不能编译

用法：
    python scripts/validate-st-package.py <角色卡.json> [世界书.json]
    python scripts/validate-st-package.py <目录>          # 目录里自动找 *.json 与 *世界书*.json
    python scripts/validate-st-package.py <卡> <书> --json

退出码：0 全通过（警告不算失败）；1 有 FAIL；2 文件读不到。

不依赖任何第三方库。正则能否编译优先用 node 实测；没有 node 就退化成括号配平检查。
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- 常量（照抄 ST）

V1_FIELDS = ["name", "description", "personality", "scenario", "first_mes", "mes_example"]

# TavernCardValidator.#validateDataV2 的 requiredFields
V2_DATA_FIELDS = [
    "name", "description", "personality", "scenario", "first_mes", "mes_example",
    "creator_notes", "system_prompt", "post_history_instructions",
    "alternate_greetings", "tags", "creator", "character_version", "extensions",
]

# newWorldInfoEntryDefinition 里没被 excludeFromTemplate 掉的键，以及它们的默认类型
WORLD_INFO_ENTRY_FIELDS = {
    "key": list, "keysecondary": list, "comment": str, "content": str,
    "constant": bool, "vectorized": bool, "selective": bool, "selectiveLogic": int,
    "addMemo": bool, "order": (int, float), "position": int, "disable": bool,
    "ignoreBudget": bool, "excludeRecursion": bool, "preventRecursion": bool,
    "matchPersonaDescription": bool, "matchCharacterDescription": bool,
    "matchCharacterPersonality": bool, "matchCharacterDepthPrompt": bool,
    "matchScenario": bool, "matchCreatorNotes": bool, "delayUntilRecursion": (int, float),
    "probability": (int, float), "useProbability": bool, "depth": (int, float),
    "outletName": str, "group": str, "groupOverride": bool, "groupWeight": (int, float),
    "scanDepth": (int, type(None)), "caseSensitive": (bool, type(None)),
    "matchWholeWords": (bool, type(None)), "useGroupScoring": (bool, type(None)),
    "automationId": str, "role": int, "sticky": (int, float, type(None)),
    "cooldown": (int, float, type(None)), "delay": (int, float, type(None)),
    "triggers": list,
}

# world_info_position：0 角色前 / 1 角色后 / 2 作者注前 / 3 作者注后 / 4 按深度 / 5、6 示例消息 / 7 outlet
VALID_POSITIONS = set(range(8))

# regex_placement：1 用户输入 / 2 AI 输出 / 3 斜杠 / 5 世界书 / 6 思维链（0 已废弃）
VALID_PLACEMENTS = {0, 1, 2, 3, 5, 6}

REGEX_SCRIPT_FIELDS = {
    "id": str, "scriptName": str, "findRegex": str, "replaceString": str,
    "trimStrings": list, "placement": list, "disabled": bool,
    "markdownOnly": bool, "promptOnly": bool, "runOnEdit": bool,
    "substituteRegex": int, "minDepth": (int, type(None)), "maxDepth": (int, type(None)),
}

# 文件名里不能出现的字符（sanitize-filename 会干掉它们，干完就对不上 extensions.world 了）
BAD_FILENAME_CHARS = set('/\\:*?"<>|')

# 本包自己的预算：常驻条目合计字数（每轮都要进上下文）
CONST_BUDGET = 5000

# 本包自己的下限：每条绿灯条目至少这么多个关键词（宁宽勿漏）
MIN_KEYS = 8

TAG_RE = re.compile(r"<([^\s<>/][^<>]{0,60})>")


class Report:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []  # (level, code, message)

    def ok(self, code: str, msg: str) -> None:
        self.items.append(("OK", code, msg))

    def warn(self, code: str, msg: str) -> None:
        self.items.append(("WARN", code, msg))

    def fail(self, code: str, msg: str) -> None:
        self.items.append(("FAIL", code, msg))

    @property
    def failures(self) -> list[tuple[str, str, str]]:
        return [i for i in self.items if i[0] == "FAIL"]

    @property
    def warnings(self) -> list[tuple[str, str, str]]:
        return [i for i in self.items if i[0] == "WARN"]

    def dump(self, as_json: bool = False) -> None:
        if as_json:
            print(json.dumps(
                [{"level": l, "code": c, "message": m} for l, c, m in self.items],
                ensure_ascii=False, indent=2))
            return
        marks = {"OK": "  ok ", "WARN": " warn", "FAIL": " FAIL"}
        for level, code, msg in self.items:
            print(f"[{marks[level]}] {code:<4} {msg}")
        print()
        print(f"共 {len(self.items)} 项：{len(self.failures)} 失败，{len(self.warnings)} 警告")
        if self.failures:
            print("结论：不通过。按上面的 FAIL 逐条改，不要带着错误导进酒馆。")


# ---------------------------------------------------------------- 小工具

def js_check_regex(patterns: list[str]) -> list[str | None]:
    """用 node 实测每个 findRegex 能否编译（regexFromString 同款解析）。返回逐条错误信息。"""
    if not patterns:
        return []
    node = shutil.which("node")
    if not node:
        return [None] * len(patterns)  # 调用方退化成静态检查

    script = r"""
const patterns = JSON.parse(process.argv[1]);
const out = patterns.map(p => {
  try {
    const m = p.match(/(\/?)(.+)\1([a-z]*)/i);
    if (m[3] && !/^(?!.*?(.).*?\1)[gmixXsuUAJ]+$/.test(m[3])) { new RegExp(p); return null; }
    new RegExp(m[2], m[3]);
    return null;
  } catch (e) { return String(e.message || e); }
});
console.log(JSON.stringify(out));
"""
    try:
        proc = subprocess.run([node, "--eval", script, json.dumps(patterns, ensure_ascii=False)],
                              capture_output=True, text=True, encoding="utf-8", timeout=30)
        if proc.returncode != 0:
            return [None] * len(patterns)
        return json.loads(proc.stdout.strip() or "[]")
    except Exception:
        return [None] * len(patterns)


def static_regex_problem(pattern: str) -> str | None:
    """没有 node 时的退化检查：只看分隔符与括号配平。"""
    if not pattern.strip():
        return "空的 findRegex"
    body = pattern
    if pattern.startswith("/"):
        last = pattern.rfind("/")
        if last <= 0:
            return "以 / 开头但没有闭合的 /"
        body = pattern[1:last]
    depth = 0
    escaped = False
    in_class = False
    for ch in body:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
        elif ch == "[":
            in_class = True
        elif ch == "]":
            in_class = False
        elif not in_class and ch == "(":
            depth += 1
        elif not in_class and ch == ")":
            depth -= 1
            if depth < 0:
                return "右括号多于左括号"
    if depth != 0:
        return f"括号不配平（差 {depth} 个）"
    return None


def count_capture_groups(pattern: str) -> int:
    body = pattern
    if pattern.startswith("/"):
        last = pattern.rfind("/")
        if last > 0:
            body = pattern[1:last]
    n = 0
    escaped = False
    in_class = False
    prev = ""
    for i, ch in enumerate(body):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
        elif ch == "[":
            in_class = True
        elif ch == "]":
            in_class = False
        elif not in_class and ch == "(":
            nxt = body[i + 1: i + 3]
            if nxt.startswith("?:"):
                pass
            elif nxt.startswith("?=") or nxt.startswith("?!") or nxt.startswith("?<=") or nxt.startswith("?<!"):
                pass
            else:
                n += 1  # 包括命名组 (?<name>…)
        prev = ch
    return n


def nested_get(d: dict, dotted: str):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


# ---------------------------------------------------------------- 卡片

def validate_card(card: dict, card_path: Path, book_path: Path | None, rep: Report) -> None:
    spec = card.get("spec")

    if spec is None:
        rep.fail("C02", "缺 spec。ST 会当成 v1 卡导入，data 里的设定与扩展全丢")
    elif spec == "chara_card_v2":
        rep.ok("C02", "spec = chara_card_v2")
    elif spec == "chara_card_v3":
        rep.warn("C02", "spec = chara_card_v3。本包默认出 v2；ST 存 PNG 时会自动补 ccv3 块，"
                        "但第三方工具对 v3 的支持还不齐")
    else:
        rep.fail("C02", f'spec = {spec!r}，只认 "chara_card_v2"')

    if spec == "chara_card_v3":
        if not re.fullmatch(r"3(\.\d+)*", str(card.get("spec_version", ""))):
            rep.fail("C03", f'spec_version = {card.get("spec_version")!r}，v3 要求 3.x')
    elif card.get("spec_version") != "2.0":
        rep.fail("C03", f'spec_version = {card.get("spec_version")!r}，v2 要求字符串 "2.0"')

    missing_v1 = [f for f in V1_FIELDS if f not in card]
    if missing_v1:
        rep.fail("C04", "顶层缺 v1 字段：" + ", ".join(missing_v1))
    else:
        rep.ok("C04", "顶层 v1 六字段齐全")

    data = card.get("data")
    if not isinstance(data, dict):
        rep.fail("C05", "缺 data 对象（v2 的正文全在 data 里）")
        return

    missing_v2 = [f for f in V2_DATA_FIELDS if f not in data]
    if missing_v2:
        rep.fail("C06", "data 缺必填字段：" + ", ".join(missing_v2))
    else:
        rep.ok("C06", "data 十四个必填字段齐全")

    if not isinstance(data.get("alternate_greetings"), list):
        rep.fail("C07", "data.alternate_greetings 必须是数组")
    if not isinstance(data.get("tags"), list):
        rep.fail("C07", "data.tags 必须是数组")
    if not isinstance(data.get("extensions"), dict):
        rep.fail("C07", "data.extensions 必须是对象")

    # importFromJson → readFromV2 会用 data.* 覆盖顶层，两边不一致就会在控制台刷警告并以后者为准
    mismatched = []
    for field in ["name"] + V1_FIELDS:
        top = card.get(field)
        inner = data.get(field)
        if top is None or inner is None:
            continue
        if str(top) != str(inner):
            mismatched.append(field)
    if mismatched:
        rep.warn("C08", "顶层与 data 不一致（导入时以 data 为准）：" + ", ".join(mismatched))
    else:
        rep.ok("C08", "顶层与 data 同名字段一致")

    name = data.get("name") or card.get("name") or ""
    if not name.strip():
        rep.fail("C09", "data.name 为空，ST 会存成无标题卡")
    else:
        bad = sorted({c for c in name if c in BAD_FILENAME_CHARS})
        if bad:
            rep.fail("C09", f"data.name 含文件名非法字符 {bad}，导入时会被 sanitize 掉，与 extensions.world 对不上")
        else:
            rep.ok("C09", f"data.name = {name!r}")

    world = nested_get(data, "extensions.world")[0]
    if not world:
        rep.warn("C11", "data.extensions.world 为空：世界书不会自动挂到卡上，需要手动在角色卡里选")
    elif book_path is not None:
        book_stem = book_path.stem
        if world == book_stem:
            rep.ok("C11", f"extensions.world = 世界书文件名 = {world!r}")
        else:
            rep.fail("C11", f"extensions.world = {world!r}，世界书文件叫 {book_stem!r}；"
                            "两者必须同名，否则导入后不会自动挂载")
    if card_path is not None and card_path.stem != name:
        rep.warn("C10", f"文件名 {card_path.name!r} 与 data.name {name!r} 不同；ST 能导入，但用户找文件会混淆")

    # character_book（可选）
    cb = data.get("character_book")
    if cb is not None:
        if not isinstance(cb, dict):
            rep.fail("C12", "data.character_book 必须是对象")
        else:
            for key in ("entries", "extensions"):
                if key not in cb:
                    rep.fail("C12", f"data.character_book 缺 {key}（convertCharacterBook 直接读它）")
            if isinstance(cb.get("entries"), list):
                ids = [e.get("id") for e in cb["entries"] if isinstance(e, dict)]
                if len(ids) != len(set(ids)):
                    rep.fail("C12", "character_book.entries 里有重复 id")
                if any(not isinstance(e, dict) or not str(e.get("content", "")).strip()
                       for e in cb["entries"]):
                    rep.fail("C12", "character_book 有条目缺 content")
                rep.ok("C12", f"character_book 内嵌 {len(cb['entries'])} 条")
            elif "entries" in cb:
                rep.fail("C12", "character_book.entries 必须是数组（v2 规范），不是 {uid: …} 映射")
        if cb is not None and book_path is not None:
            rep.warn("C13", "同时给了内嵌 character_book 和独立世界书文件：导入后可能有两本书，"
                            "改设定时容易只改一本。二选一，本包默认用独立世界书")

    # 内嵌正则
    scripts = nested_get(data, "extensions.regex_scripts")[0]
    if scripts is None:
        rep.warn("C14", "data.extensions.regex_scripts 缺失：前端不会自动出现，需另导 regex-*.json")
        return
    if not isinstance(scripts, list):
        rep.fail("C14", "data.extensions.regex_scripts 必须是数组")
        return
    if not scripts:
        rep.warn("C14", "data.extensions.regex_scripts 是空数组：卡里没有正则，第一楼会是裸标签")
        return

    patterns = []
    for i, s in enumerate(scripts):
        tag = f"regex_scripts[{i}]"
        if not isinstance(s, dict):
            rep.fail("C15", f"{tag} 不是对象")
            continue
        for key, typ in REGEX_SCRIPT_FIELDS.items():
            if key not in s:
                rep.fail("C15", f"{tag} 缺 {key}（正则编辑器按这些字段渲染）")
                continue
            if not isinstance(s[key], typ):
                rep.fail("C15", f"{tag}.{key} 类型不对：要 {typ}，实际 {type(s[key]).__name__}")
        bad_place = [p for p in s.get("placement", []) if p not in VALID_PLACEMENTS]
        if bad_place:
            rep.fail("C15", f"{tag}.placement 含非法值 {bad_place}（合法：1 用户输入 / 2 AI 输出 / 3 斜杠 / 5 世界书 / 6 思维链）")
        if s.get("markdownOnly") is not True:
            rep.warn("C15", f"{tag} markdownOnly 不是 true：替换后的 HTML 会进提示词与聊天记录")
        patterns.append(str(s.get("findRegex", "")))

    errors = js_check_regex(patterns)
    for i, (s, err) in enumerate(zip(scripts, errors)):
        pattern = str(s.get("findRegex", ""))
        if err is None and not err:
            continue
        if err is None:
            problem = static_regex_problem(pattern)
            if problem:
                rep.fail("C16", f"regex_scripts[{i}].findRegex 编译不了：{problem}（{pattern[:60]!r}）")
            continue
        rep.fail("C16", f"regex_scripts[{i}].findRegex 编译不了：{err}（{pattern[:60]!r}）")
    if patterns and any(e is None for e in errors):
        rep.ok("C16", f"{len(patterns)} 条 findRegex 可编译（node 实测）")

    # 捕获组与 $1 的对应
    for i, s in enumerate(scripts):
        if not isinstance(s, dict):
            continue
        groups = count_capture_groups(str(s.get("findRegex", "")))
        repl = str(s.get("replaceString", ""))
        uses_dollar = bool(re.search(r"\$\{?[1-9]", repl))
        if uses_dollar and groups == 0:
            rep.fail("C17", f"regex_scripts[{i}] 用了 $1 但 findRegex 没有捕获组：数据会整段丢失")
        if groups > 0 and not uses_dollar:
            rep.warn("C17", f"regex_scripts[{i}] 有 {groups} 个捕获组但 replaceString 没引用 $1："
                            "捕获到的数据被丢掉了（若是有意为之可忽略）")
        if groups > 0 and "${1}" not in repl and "$1" in repl and s.get("substituteRegex") != 0:
            rep.warn("C17", f"regex_scripts[{i}].substituteRegex 非 0：$1 之外的内容还会被宏替换，容易二次注入")

    # 第一楼能不能被某个正则接住
    first_mes = str(data.get("first_mes") or card.get("first_mes") or "")
    if first_mes.strip():
        matched = [i for i, s in enumerate(scripts)
                   if isinstance(s, dict) and _matches(str(s.get("findRegex", "")), first_mes)]
        if matched:
            rep.ok("C18", f"first_mes 能被 regex_scripts[{matched[0]}] 接住")
        else:
            tags = TAG_RE.findall(first_mes)
            if tags:
                rep.fail("C18", f"first_mes 里的标签 {['<' + t + '>' for t in tags]} 没有任何正则能匹配："
                                "第一楼会是裸标签。改 first_mes 或改正则")
            else:
                rep.ok("C18", "first_mes 是纯文本，不依赖正则")


def _matches(pattern: str, text: str) -> bool:
    try:
        if pattern.startswith("/"):
            last = pattern.rfind("/")
            body, flags = pattern[1:last], pattern[last + 1:]
        else:
            body, flags = pattern, ""
        f = 0
        for ch in flags:
            f |= {"i": re.I, "m": re.M, "s": re.S}.get(ch, 0)
        return re.search(body, text, f) is not None
    except re.error:
        return False


# ---------------------------------------------------------------- 世界书

def validate_worldbook(book: dict, book_path: Path, rep: Report) -> None:
    entries = book.get("entries")
    if not isinstance(entries, dict):
        rep.fail("W01", "顶层必须是 {\"entries\": {…}}（ST 导入接口只查这一层）")
        return
    if not entries:
        rep.fail("W01", "entries 里一条都没有")
        return
    rep.ok("W01", f"entries 形状正确，共 {len(entries)} 条")

    all_keys: list[str] = []
    const_chars = 0
    for uid, e in entries.items():
        tag = f"条目 {uid}"
        if not isinstance(e, dict):
            rep.fail("W02", f"{tag} 不是对象")
            continue
        if str(e.get("uid")) != str(uid):
            rep.fail("W02", f"{tag}.uid = {e.get('uid')!r}，与键 {uid!r} 不一致（编辑器按 uid 索引）")
        for key, typ in WORLD_INFO_ENTRY_FIELDS.items():
            if key not in e:
                rep.warn("W03", f"{tag} 缺 {key}（编辑器会显示空白或 undefined）")
                continue
            if not isinstance(e[key], typ):
                rep.fail("W03", f"{tag}.{key} 类型不对：要 {typ}，实际 {type(e[key]).__name__}")
        content = str(e.get("content", ""))
        if not content.strip():
            rep.fail("W04", f"{tag} 的 content 为空（不会触发，也不会显示）")
        if not str(e.get("comment", "")).strip():
            rep.warn("W04", f"{tag} 没有 comment（comment 就是条目名，addMemo 靠它）")
        keys = e.get("key", [])
        if not isinstance(keys, list):
            rep.fail("W05", f"{tag}.key 必须是数组")
            keys = []
        if any(not isinstance(k, str) or not k.strip() for k in keys):
            rep.fail("W05", f"{tag}.key 里有空值或非字符串")
        if e.get("constant") is False and not keys:
            rep.fail("W05", f"{tag} 既非常驻又没有关键词：永远不会触发")
        if e.get("position") not in VALID_POSITIONS:
            rep.fail("W06", f"{tag}.position = {e.get('position')!r}，合法值 0–7")
        if e.get("position") == 4 and not isinstance(e.get("depth"), (int, float)):
            rep.fail("W06", f"{tag} 用 atDepth（position 4）但没有数字 depth")
        if e.get("role") not in (0, 1, 2):
            rep.fail("W06", f"{tag}.role = {e.get('role')!r}，合法值 0 系统 / 1 用户 / 2 助手")
        prob = e.get("probability", 100)
        if isinstance(prob, (int, float)) and not 0 <= prob <= 100:
            rep.fail("W07", f"{tag}.probability = {prob}，应在 0–100")
        if e.get("constant"):
            const_chars += len(content)
        all_keys += [k for k in keys if isinstance(k, str) and k.strip()]

    # ---- 调优项：关键词宽度、递归、整词匹配、位置风险、order 分档 ----
    orders: list[float] = []
    tune_issues = {"keys": [], "rec": [], "mww": [], "pos": [], "order": [], "sel": []}
    for uid, e in entries.items():
        if not isinstance(e, dict):
            continue
        content = str(e.get("content", ""))
        keys = [k for k in e.get("key", []) if isinstance(k, str) and k.strip()]
        is_const = e.get("constant") is True
        if isinstance(e.get("order"), (int, float)):
            orders.append(float(e["order"]))
        if not is_const:
            if e.get("selective") is False:
                tune_issues["sel"].append(str(uid))
            plain = [k for k in keys if not (k.startswith("/") and k.endswith("/"))]
            if len(plain) < MIN_KEYS:
                tune_issues["keys"].append(f"{uid}({len(plain)})")
            if e.get("excludeRecursion") is not True:
                tune_issues["rec"].append(str(uid))
        if e.get("matchWholeWords") is not False and re.search(r"[一-鿿]", content + "".join(keys)):
            tune_issues["mww"].append(str(uid))
        if e.get("position") in (5, 6):
            rep.fail("W13", f"条目 {uid} position={e['position']}：5/6 是示例消息位置，正文会被解析成示例对话，别用来放设定")
        elif e.get("position") in (2, 3):
            tune_issues["pos"].append(str(uid))
        for k in keys:
            if "," in k and not k.startswith("/"):
                rep.fail("W14", f"条目 {uid} 的关键词 {k!r} 带逗号：纯文本关键词不支持逗号（逗号是分隔符），要匹配就写成 /.../ 正则")
                break

    if tune_issues["keys"]:
        rep.warn("W10", f"关键词少于 {MIN_KEYS} 个：{', '.join(tune_issues['keys'])}。"
                        "绿灯条目宁宽勿漏，按 8–15 个备（本名/别名/关系指代/场景指代/同义口语）")
    if tune_issues["rec"]:
        rep.warn("W11", f"关键词条目没设 excludeRecursion: true：{', '.join(tune_issues['rec'])}。"
                        "常驻条目正文会点名实体，递归一开就会顺次点亮它们")
    if tune_issues["mww"]:
        rep.warn("W12", f"含中文但 matchWholeWords 不是 false：{', '.join(tune_issues['mww'])}")
    if tune_issues["pos"]:
        rep.warn("W13", f"position 2/3（作者注）的条目：{', '.join(tune_issues['pos'])}——作者注关闭时整条被忽略")
    if tune_issues["sel"]:
        rep.warn("W16", f"关键词条目 selective=false：{', '.join(tune_issues['sel'])}——UI 上会显示成蓝灯行为")
    if len(orders) >= 3 and len(set(orders)) == 1:
        rep.warn("W15", f"所有条目 order 都是 {orders[0]:g}：没分档。按 95–100 / 70–90 / 70 三档排，越靠后影响越大")

    dupes = sorted({k for k in all_keys if all_keys.count(k) > 1})
    if dupes:
        rep.fail("W08", f"关键词在多条里重复，会失去判别力：{dupes}")
    else:
        rep.ok("W08", f"{len(all_keys)} 个关键词无重复")

    if const_chars > CONST_BUDGET:
        rep.warn("W09", f"常驻条目合计 {const_chars} 字，超过本包 {CONST_BUDGET} 字预算："
                        "把可省的段落挪成关键词条目")
    else:
        rep.ok("W09", f"常驻条目合计 {const_chars} 字（预算 {CONST_BUDGET}）")


# ---------------------------------------------------------------- 入口

def find_files(arg: str) -> tuple[Path | None, Path | None]:
    p = Path(arg)
    if p.is_dir():
        card = None
        book = None
        for f in sorted(p.glob("*.json")):
            if "世界书" in f.name or "worldbook" in f.name.lower():
                book = book or f
            else:
                card = card or f
        return card, book
    return p, None


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2

    card_path, book_path = find_files(args[0])
    if len(args) > 1:
        book_path = Path(args[1])

    if card_path is None or not card_path.exists():
        print(f"读不到角色卡：{card_path}", file=sys.stderr)
        return 2

    rep = Report()
    try:
        card = json.loads(card_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"角色卡不是合法 JSON：{exc}", file=sys.stderr)
        return 2
    if not isinstance(card, dict):
        print("角色卡顶层必须是对象", file=sys.stderr)
        return 2

    book = None
    if book_path is not None and book_path.exists():
        try:
            book = json.loads(book_path.read_text(encoding="utf-8"))
        except Exception as exc:
            rep.fail("W00", f"世界书不是合法 JSON：{exc}")
        else:
            if not isinstance(book, dict):
                rep.fail("W00", "世界书顶层必须是对象")
                book = None

    validate_card(card, card_path, book_path if book is not None else None, rep)
    if book is not None:
        validate_worldbook(book, book_path, rep)
    else:
        rep.warn("W00", "没给世界书文件：只校了卡片。酒馆包里两个文件都要过")

    # 跨文件：轴名、势力名等是否在卡片的 description 里（本包自己的交付门第 5 条）
    if book is not None:
        desc = str((card.get("data") or {}).get("description", ""))
        if desc.strip():
            rep.ok("X01", f"description {len(desc)} 字")
        else:
            rep.fail("X01", "data.description 为空：卡里没有设定正文")

    rep.dump(as_json)
    return 0 if not rep.failures else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    sys.exit(main(sys.argv[1:]))
