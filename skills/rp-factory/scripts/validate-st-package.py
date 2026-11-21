#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 RP-Factory 交付的 SillyTavern 三件套（纯净卡 / 正则 / 世界书）。

三件是分开的三份文件，用户自己装配：
  <世界名>（纯净）.json   角色卡 v2，不含 character_book，extensions.regex_scripts 为空
  正则.json               正则脚本**数组**（ST 的导入接口认数组，一次导完）
  <世界名> 世界书.json    native 形状 {"entries": {"0": {…}}}，文件名就是酒馆里的书名

规则抄自 SillyTavern 本体的：
- src/validator/TavernCardValidator.js       卡片 v1/v2 必填字段
- src/endpoints/characters.js  importFromJson / readFromV2   顶层字段与 data 的同步关系
- src/endpoints/worldinfo.js   /import        只查 'entries' 这一层，文件名即书名
- public/scripts/world-info.js newWorldInfoEntryDefinition    世界书条目字段与类型
- public/scripts/extensions/regex/index.js    onRegexImportFileChange 认数组 / 单个对象
- public/scripts/utils.js      regexFromString               正则能不能编译

用法：
    python scripts/validate-st-package.py <导入包目录>
    python scripts/validate-st-package.py <卡.json> <正则.json> <世界书.json>
    python scripts/validate-st-package.py <目录> --contract 制作文件/项目记录/contract.yaml
    python scripts/validate-st-package.py <目录> --json

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
    "automationId": str, "role": (int, type(None)), "sticky": (int, float, type(None)),
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

# 资料库式世界书：控制器条目用 getwi(null, '<条目名>') 按状态取用被 disable 的资料条目。
# 只认第一参数为 null/undefined 的调用（带书名的跨书引用不要求本地存在）。
GETWI_LOCAL = re.compile(r"""getwi\(\s*(?:null|undefined)\s*,\s*['"]([^'"]+)['"]""")

# 文件名里不能出现的字符（sanitize-filename 会干掉它们，干完就对不上 extensions.world 了）
BAD_FILENAME_CHARS = set('/\\:*?"<>|')

# 本包自己的预算：常驻条目合计字数（每轮都要进上下文）
CONST_BUDGET = 8000
# 逐字性检查：切出来的条目至少这么多行能在原稿里找到；原稿至少这么多行要进书
CUT_MIN_RATIO = 0.85
CUT_MIN_DRAFT = 0.6
MIN_LINE = 4
# 原稿目录里这些文件不是给模型看的设定（表现层提示词 / 台账）
NOT_BOOK_DRAFTS = {"frontend-prompt.yaml"}
DESC_SOFT = 6000
DESC_HARD = 8000

# 本包自己的下限：每条绿灯条目至少这么多个关键词（宁宽勿漏）
MIN_KEYS = 8

TAG_RE = re.compile(r"<([^\s<>/][^<>]{0,60})>")
PLACEHOLDERS = ["【AI补全·可替换】", "[待定", "【未知】"]


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
            if nxt.startswith("?:") or nxt.startswith("?=") or nxt.startswith("?!") \
                    or nxt.startswith("?<=") or nxt.startswith("?<!"):
                pass
            else:
                n += 1  # 包括命名组 (?<name>…)
    return n


def nested_get(d: dict, dotted: str):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


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


# ---------------------------------------------------------------- 卡片（纯净）

def validate_mvu_panel(script_list, rep):
    """核对最终发布的 AI 显示规则和替换后的内联脚本。"""
    marker = "<StatusPlaceHolderImpl/>"
    renderers = []
    pending = []
    for rule in script_list:
        if rule.get("disabled") or 2 not in (rule.get("placement") or []):
            continue
        if not rule.get("markdownOnly") or not _matches(str(rule.get("findRegex", "")), marker):
            continue
        body = str(rule.get("replaceString") or "")
        if PENDING_UI_MARK in body:
            pending.append(rule)
            continue
        if rule.get("promptOnly"):
            rep.fail("X07", "变量界面应只用于显示，HTML 不能发给模型")
        if type(rule.get("minDepth")) in (int, float) and rule["minDepth"] > 0:
            rep.fail("X07", "minDepth 排除了最新楼层的状态栏")
        if not body.strip():
            rep.fail("X07", "已启用的显示正则会移除 MVU 状态栏挂载标签")
            continue
        scripts = re.findall(r"<script\b[^>]*>(.*?)</script\s*>", body, re.I | re.S)
        code = "\n".join(scripts)
        reader = re.search(r"\b(?:getMvuData|getVariables|getAllVariables)\s*\(", code)
        if "<body" in body.lower() and reader and "stat_data" in code and "$1" not in body:
            renderers.append(rule)
    if not renderers and pending:
        rep.warn("X07", f"状态栏界面还是待粘贴态（{len(pending)} 条）：粘完后要满足——"
                        f"`<body>` 里读 stat_data、替换串不要用 $1、minDepth 留空")
        return
    if len(renderers) != 1:
        rep.fail("X07", f"需有一条 AI 显示正则把 {marker} 渲染为读 stat_data 的界面，实际 {len(renderers)} 条")
    else:
        rep.ok("X07", "MVU 挂载标签与最终界面的变量读取路径已静态核对")


def validate_card(card: dict, card_path: Path | None, book_path: Path | None, rep: Report) -> dict:
    data = card.get("data") if isinstance(card.get("data"), dict) else {}

    spec = card.get("spec")
    if spec is None:
        rep.fail("C01", "缺 spec。ST 会当成 v1 卡导入，data 里的设定与扩展全丢")
    elif spec == "chara_card_v2":
        rep.ok("C01", "spec = chara_card_v2")
    elif spec == "chara_card_v3":
        rep.warn("C01", "spec = chara_card_v3。本包默认出 v2；第三方工具对 v3 支持还不齐")
    else:
        rep.fail("C01", f'spec = {spec!r}，只认 "chara_card_v2"')

    if card.get("spec_version") != "2.0" and spec == "chara_card_v2":
        rep.fail("C02", f'spec_version = {card.get("spec_version")!r}，v2 要求字符串 "2.0"')

    missing_v1 = [f for f in V1_FIELDS if f not in card]
    if missing_v1:
        rep.fail("C03", "顶层缺 v1 字段：" + ", ".join(missing_v1))
    elif data:
        rep.ok("C03", "顶层 v1 六字段齐全")

    if not data:
        rep.fail("C04", "缺 data 对象（v2 的正文全在 data 里）")
        return {}
    missing_v2 = [f for f in V2_DATA_FIELDS if f not in data]
    if missing_v2:
        rep.fail("C04", "data 缺必填字段：" + ", ".join(missing_v2))
    else:
        rep.ok("C04", "data 十四个必填字段齐全")

    if not isinstance(data.get("alternate_greetings"), list):
        rep.fail("C05", "data.alternate_greetings 必须是数组")
    if not isinstance(data.get("tags"), list):
        rep.fail("C05", "data.tags 必须是数组")
    if not isinstance(data.get("extensions"), dict):
        rep.fail("C05", "data.extensions 必须是对象")

    mismatched = []
    for field in ["name"] + V1_FIELDS:
        top, inner = card.get(field), data.get(field)
        if top is None or inner is None:
            continue
        if str(top) != str(inner):
            mismatched.append(field)
    if mismatched:
        rep.warn("C06", "顶层与 data 不一致（导入时以 data 为准）：" + ", ".join(mismatched))
    else:
        rep.ok("C06", "顶层与 data 同名字段一致")

    name = str(data.get("name") or card.get("name") or "")
    if not name.strip():
        rep.fail("C07", "data.name 为空，ST 会存成无标题卡")
    else:
        bad = sorted({c for c in name if c in BAD_FILENAME_CHARS})
        if bad:
            rep.fail("C07", f"data.name 含文件名非法字符 {bad}，导入时会被 sanitize 掉")
        else:
            rep.ok("C07", f"data.name = {name!r}")
    if card_path is not None:
        stem = card_path.stem.replace("（纯净）", "").replace("(纯净)", "").strip()
        if stem and stem != name:
            rep.warn("C08", f"文件名 {card_path.name!r} 与 data.name {name!r} 不同；用户找文件会混淆")

    # 纯净 = 不内嵌世界书
    if "character_book" in data and data.get("character_book") is not None:
        rep.fail("C09", "卡里有 data.character_book：本次交付是三件套，世界书单独一份。"
                        "内嵌会让“改一条设定”变成重导整卡，也违背逐件装配")
    else:
        rep.ok("C09", "卡里没有 character_book（纯净）")

    # 纯净 = 不内嵌正则
    scripts, has = nested_get(data, "extensions.regex_scripts")
    if not has:
        rep.ok("C10", "extensions.regex_scripts 不存在（纯净）")
    elif isinstance(scripts, list) and not scripts:
        rep.ok("C10", "extensions.regex_scripts = []（纯净）")
    else:
        rep.fail("C10", f"extensions.regex_scripts 里有 {len(scripts) if isinstance(scripts, list) else '未知'} 条脚本："
                        "三件套要求正则单独一份")

    # 纯净 = 不内嵌酒馆助手脚本（脚本单独一份，导入后在插件里开）
    th_scripts, th_has = nested_get(data, "extensions.tavern_helper.scripts")
    if not th_has or (isinstance(th_scripts, list) and not th_scripts):
        rep.ok("C12", "卡里没有 tavern_helper.scripts（脚本单独一份）")
    else:
        n = len(th_scripts) if isinstance(th_scripts, list) else "未知"
        rep.fail("C12", f"卡里内嵌了 {n} 条酒馆助手脚本：本次交付要求脚本单独一份"
                        f"（`<世界名> 酒馆助手脚本.json`）。内嵌脚本要进角色白名单才跑，"
                        f"和单独导入的同一份同时启用还会跑两遍")

    world = nested_get(data, "extensions.world")[0]
    if not world:
        rep.fail("C11", "data.extensions.world 为空：世界书导入后不会自动挂到卡上")
    elif book_path is not None and not book_path.exists():
        rep.warn("C11", f"extensions.world = {world!r}，但没给世界书文件")
    elif book_path is not None and world != book_path.stem:
        # ST 靠「书名 == extensions.world」绑定（world-info.js:1128 push 的是书名）；
        # 名字对不上时导入不报错、小地球不亮，只在聊天里表现为「设定全忘了」。
        rep.fail("C11", f"extensions.world = {world!r} ≠ 世界书文件名 {book_path.stem!r}："
                        "ST 按书名绑卡，对不上就静默不挂书。改卡里的 extensions.world，"
                        "或把世界书文件重命名成这个名字。")
    else:
        rep.ok("C11", f"extensions.world = {world!r}（与世界书文件名一致）")
    return data


# ---------------------------------------------------------------- 世界书（native）

def norm_line(s: str) -> str:
    return " ".join(s.split())


def check_cut_fidelity(entries: dict, draft_root: Path, rep: Report) -> None:
    """W17 / W18：世界书条目必须是原稿的切片，不是它的摘要。

    手写条目最常见的病是「顺手压缩」——《常见误解或谣言》压成「有一些谣言」、
    每级 `behavioral_signs` 压成一句，模型做判断时的唯一依据就没了。
    这里按**行**比对：切出来的条目每一行都能在原稿里逐字找到；原稿的每一行
    也该在某条里出现（除非有意不给模型看）。判定只给数字与警告，不阻断。
    """
    files = {p.name: p for p in sorted(draft_root.glob("*.yaml")) if p.name not in NOT_BOOK_DRAFTS}
    if not files:
        rep.warn("W17", f"找不到原稿（{draft_root}/*.yaml），逐字性没查")
        return
    per_file: dict[str, list[str]] = {}
    blob_parts: list[str] = []
    for name, p in files.items():
        lines = [norm_line(l) for l in p.read_text(encoding="utf-8", errors="ignore").splitlines()]
        per_file[name] = [l for l in lines if len(l) >= MIN_LINE]
        blob_parts += per_file[name]
    draft_blob = "\n".join(blob_parts)
    draft_set = set(blob_parts)

    def traced(line: str) -> bool:
        return line in draft_set or (len(line) >= 12 and line in draft_blob)

    book_lines: list[str] = []
    rewritten: list[str] = []
    for uid, e in entries.items():
        if not isinstance(e, dict):
            continue
        body = [norm_line(l) for l in str(e.get("content") or "").splitlines()]
        body = [l for l in body if len(l) >= MIN_LINE]
        book_lines += body
        if str(e.get("comment") or "").lstrip().startswith("["):
            continue  # 协议条目（变量初始化 / 更新块 / 阶段控制器）来自阶段 6 模板，不是设定原稿
        if len(body) < 3:
            continue
        hit = sum(1 for l in body if traced(l))
        ratio = hit / len(body)
        if ratio < CUT_MIN_RATIO:
            rewritten.append(f"{e.get('comment')}({ratio:.0%})")
    if rewritten:
        rep.warn("W17", f"这些条目不像原稿切片（逐字命中不到 {CUT_MIN_RATIO:.0%}）："
                         f"{'、'.join(rewritten)}。要用 `scripts/cut-worldbook.py` 按节切，"
                         "别手写摘要——压掉的每一句都是模型判断时的唯一依据")
    else:
        rep.ok("W17", "设定条目都是原稿切片（逐字命中 ≥" f"{CUT_MIN_RATIO:.0%}）")

    book_set = set(book_lines)
    book_blob = "\n".join(book_lines)
    dropped: list[str] = []
    for name, lines in per_file.items():
        if len(lines) < 10:
            continue
        hit = sum(1 for l in lines if l in book_set or (len(l) >= 12 and l in book_blob))
        ratio = hit / len(lines)
        if ratio < CUT_MIN_DRAFT:
            dropped.append(f"{name} {ratio:.0%}（{len(lines) - hit} 行没进书）")
    if dropped:
        rep.warn("W18", f"原稿有大段没进世界书：{'；'.join(dropped)}。"
                         "要么补切一条，要么在 plan 的 skip 里写明「有意不给模型看」")
    else:
        rep.ok("W18", "原稿的每一节都能在书里找到")


def validate_worldbook(book: dict, book_path: Path, rep: Report, mvu_done: bool = False) -> int:
    entries = book.get("entries")
    if not isinstance(entries, dict):
        rep.fail("W01", '顶层必须是 {"entries": {…}}——这是 native 形状；entries 数组是卡内 v2 形状，'
                         "导进世界书面板参数会全丢")
        return 0
    if not entries:
        rep.fail("W01", "entries 里一条都没有")
        return 0
    rep.ok("W01", f"entries 形状正确（native），共 {len(entries)} 条")

    all_keys: list[str] = []
    const_chars = 0
    orders: list[float] = []
    tune = {"keys": [], "rec": [], "mww": [], "pos": [], "sel": []}
    # W19–W22 用：单字关键词、正文开头的 @@ 装饰器、常驻条目正文里点了谁的关键词
    shorts: list[str] = []
    at_prefix: list[tuple[str, bool]] = []  # (uid, 是否 @@@ 转义)
    const_bodies: dict[str, tuple[str, list[str]]] = {}
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
        disabled = e.get("disable") is True or e.get("enabled") is False
        if e.get("constant") is False and not keys and not disabled:
            rep.fail("W05", f"{tag} 既非常驻又没有关键词：永远不会触发（要么给关键词，要么 disable: true）")
        if e.get("position") not in VALID_POSITIONS:
            rep.fail("W06", f"{tag}.position = {e.get('position')!r}，合法值 0–7")
        if e.get("position") == 4 and not isinstance(e.get("depth"), (int, float)):
            rep.fail("W06", f"{tag} 用 atDepth（position 4）但没有数字 depth")
        if e.get("role") not in (0, 1, 2, None):
            rep.fail("W06", f"{tag}.role = {e.get('role')!r}，合法值 0 系统 / 1 用户 / 2 助手（或 null 不指定）")
        prob = e.get("probability", 100)
        if isinstance(prob, (int, float)) and not 0 <= prob <= 100:
            rep.fail("W07", f"{tag}.probability = {prob}，应在 0–100")
        if e.get("constant"):
            const_chars += len(content)
        all_keys += [k for k in keys if isinstance(k, str) and k.strip()]

        # 调优项
        plain = [k for k in keys if isinstance(k, str) and k.strip() and not (k.startswith("/") and k.endswith("/"))]
        shorts += [k for k in plain if len(k.strip()) == 1]
        head = content.lstrip()
        if head.startswith("@@"):
            at_prefix.append((str(uid), head.startswith("@@@")))
        if e.get("constant") and e.get("preventRecursion") is not True:
            const_bodies[str(uid)] = (content, plain)
        if isinstance(e.get("order"), (int, float)):
            orders.append(float(e["order"]))
        if not e.get("constant") and not disabled:
            if e.get("selective") is False:
                tune["sel"].append(str(uid))
            if len(plain) < MIN_KEYS:
                tune["keys"].append(f"{uid}({len(plain)})")
            if e.get("excludeRecursion") is not True:
                tune["rec"].append(str(uid))
        if e.get("matchWholeWords") is not False and re.search(r"[\u4e00-\u9fff]", content + "".join(plain)):
            tune["mww"].append(str(uid))
        if e.get("position") in (5, 6):
            rep.fail("W13", f"{tag} position={e['position']}：5/6 是示例消息位置，设定会被当示例对话解析")
        elif e.get("position") in (2, 3):
            tune["pos"].append(str(uid))
        for k in plain:
            if "," in k:
                rep.fail("W14", f"{tag} 的关键词 {k!r} 带逗号：逗号是分隔符，要匹配就写成 /…/ 正则")
                break

    if tune["keys"]:
        rep.warn("W10", f"关键词少于 {MIN_KEYS} 个：{', '.join(tune['keys'])}。"
                        "绿灯条目宁宽勿漏（本名/别名/关系指代/场景指代/同义口语）")
    if tune["rec"]:
        rep.warn("W11", f"关键词条目没设 excludeRecursion: true：{', '.join(tune['rec'])}")
    if tune["mww"]:
        rep.warn("W12", f"含中文但 matchWholeWords 不是 false：{', '.join(tune['mww'])}")
    if tune["pos"]:
        rep.warn("W13", f"position 2/3（作者注）的条目：{', '.join(tune['pos'])}——作者注关闭时整条被忽略")
    if tune["sel"]:
        rep.warn("W16", f"关键词条目 selective=false：{', '.join(tune['sel'])}——UI 上会显示成蓝灯行为")
    if len(orders) >= 3 and len(set(orders)) == 1:
        rep.warn("W15", f"所有条目 order 都是 {orders[0]:g}：没分档，按 95–100 / 70–90 / 70 三档排")

    if shorts:
        rep.warn("W19", f"单字关键词：{sorted(set(shorts))}。在任意句子里都成立，"
                          "include_names 关着时会把整条 3k 字的条目拉进来；改用双字以上的词或正则加边界")

    # W20：短词是长词的子串（灯 / 灯所）——短词一命中，长词那条也跟着亮。同一条目内的互含无害，不计。
    owner: dict[str, set[str]] = {}
    for uid, e in entries.items():
        if not isinstance(e, dict):
            continue
        for k in e.get("key", []) or []:
            if isinstance(k, str) and k.strip() and not (k.startswith("/") and k.endswith("/")):
                owner.setdefault(k.strip(), set()).add(str(uid))
    plain_keys = sorted(owner)
    wide = sorted({(s, l) for s in plain_keys if len(s) <= 2
                   for l in plain_keys if s != l and s in l and owner[s] != owner[l]})
    if wide:
        shown = "；".join(f"{s} ⊂ {l}（条目 {'/'.join(sorted(owner[s]))} → {'/'.join(sorted(owner[l]))}）"
                          for s, l in wide[:6])
        rep.warn("W20", f"关键词互为子串且不同属一条：{shown}。短词一命中，长词那条也跟着亮。"
                          "只留长的，或把短的删掉重配")

    if at_prefix:
        for uid, escaped in at_prefix:
            if escaped:
                rep.warn("W21", f"条目 {uid} 的正文以 @@@ 开头：那是转义，前三个字符会被解析成 `@@`，"
                                 "正文实际从第三行开始")
            else:
                rep.fail("W21", f"条目 {uid} 的正文以 @@ 开头：ST 会把它当装饰器（@@activate / @@dont_activate）"
                                 "整段剥离，正文第一段凭空消失。要真的以 @@ 开头就写 @@@")

    # W22：常驻条目点名了别的条目的关键词——递归一开，它每轮都在，等于永久点亮器
    fanout = []
    for uid, (body, own) in const_bodies.items():
        for k in sorted(set(all_keys) - set(own)):
            if len(k) >= 2 and k in body:
                fanout.append(f"{uid}→{k}")
    if fanout:
        rep.warn("W22", f"常驻条目没加 preventRecursion 却在正文里点了别的条目的关键词：{fanout[:8]}。"
                          "递归开着时它们每轮都在，等于永久点亮器（把关键词条目变成半个常驻）")

    # W23/W24：资料库式（disable 条目 + 控制器 getwi 取用）的两条断链点
    #   控制器取的名字在书里不存在 → getwi 静默返回空，界面上像“这一段没写”
    #   disable 的[data]/[阶段]条目没人取 → 死数据，白占文件、白给模型当误导
    local_refs: set[str] = set()
    for e in entries.values():
        if isinstance(e, dict):
            local_refs |= set(GETWI_LOCAL.findall(str(e.get("content", ""))))
    comments = {str(e.get("comment", "")).strip() for e in entries.values() if isinstance(e, dict)}
    missing = sorted(r for r in local_refs if r not in comments)
    if missing:
        rep.fail("W24", f"getwi() 取的条目名在书里不存在：{missing}——控制器会静默拿到空串，界面像"
                          "“这段没写”。名字必须与条目 comment 逐字相同（含 [] 前缀与·分隔符）")
    orphans = sorted(str(e.get("comment", "")).strip() for e in entries.values()
                     if isinstance(e, dict) and (e.get("disable") is True or e.get("enabled") is False)
                     and str(e.get("comment", "")).strip().startswith(("[data]", "[阶段]"))
                     and str(e.get("comment", "")).strip() not in local_refs)
    if orphans:
        rep.warn("W23", f"disable 的[data]/[阶段]条目没有任何控制器取用：{orphans}——它们永远不会进上下文。"
                          "要么写进控制器的 getwi()，要么删掉")

    # W25：开了 MVU 却把三件套留在 制作文件/ 里，书里一条都没有——脚本读不到初值、模型收不到更新规则
    if mvu_done:
        comments = [str(e.get("comment", "")).lower() for e in entries.values() if isinstance(e, dict)]
        missing = [n for n in ("[initvar]", "[mvu_update]") if not any(n in c for c in comments)]
        if missing:
            rep.fail("W25", f"契约里 mvu 是 done，但世界书里找不到 {missing} 条目——"
                            "变量初始值与更新规则必须作为条目随书交付，放在 制作文件/ 里等于没交。"
                            "打包时加 --merge-mvu 制作文件/产物/mvu")
        else:
            rep.ok("W25", "MVU 条目已在书里（[initvar] + [mvu_update]）")

    dupes = sorted({k for k in all_keys if all_keys.count(k) > 1})
    if dupes:
        rep.fail("W08", f"关键词在多条里重复，会失去判别力：{dupes[:10]}")
    else:
        rep.ok("W08", f"{len(all_keys)} 个关键词无重复")

    # 预算不设上限：只把数字摆出来，判定留给用户（MVU 三件套会把常驻顶到 9k 上下，那是"该写的都写了"）
    rep.ok("W09", f"常驻条目合计 {const_chars} 字（参考值 {CONST_BUDGET}，不判定）")
    return len(entries)


# ---------------------------------------------------------------- 正则

# 界面还没粘进来时的标记，写在 replaceString 开头——忘粘时聊天里显示的就是这句话，
# 比留空（等于删掉这行）或留标签（只剩 <建卡向导> 六个字）好排查得多。
PENDING_UI_MARK = "【尚未粘贴界面】"


def looks_like_ui(repl: str) -> bool:
    """替换串是不是一段界面：```html 围栏，或整段 HTML 文档。"""
    if "```html" in repl:
        return True
    low = repl.lower()
    return "<html" in low and "</html>" in low

def validate_regex_pack(scripts, path: Path | None, rep: Report) -> list[dict]:
    if scripts is None:
        return []
    if isinstance(scripts, dict):
        rep.warn("R01", "正则文件是单个对象（能导，参考包就是一条一个文件）；本包默认给数组，一次导完")
        scripts = [scripts]
    if not isinstance(scripts, list):
        rep.fail("R01", "正则文件必须是数组（[{…}]）或单个对象")
        return []
    if not scripts:
        rep.fail("R01", "正则数组是空的：第一楼会是裸标签")
        return []
    rep.ok("R01", f"正则文件可解析，共 {len(scripts)} 条")

    patterns: list[str] = []
    for i, s in enumerate(scripts):
        tag = f"正则[{i}]"
        if not isinstance(s, dict):
            rep.fail("R02", f"{tag} 不是对象")
            continue
        for key, typ in REGEX_SCRIPT_FIELDS.items():
            if key not in s:
                rep.fail("R02", f"{tag} 缺 {key}（正则编辑器按这些字段渲染）")
                continue
            if not isinstance(s[key], typ):
                rep.fail("R02", f"{tag}.{key} 类型不对：要 {typ}，实际 {type(s[key]).__name__}")
        if not str(s.get("scriptName") or "").strip():
            rep.fail("R02", f"{tag}.scriptName 为空：导入时会被拒（onRegexImportObjectChange 第一句就查它）")
        bad_place = [p for p in s.get("placement", []) if p not in VALID_PLACEMENTS]
        if bad_place:
            rep.fail("R03", f"{tag}.placement 含非法值 {bad_place}（1 用户输入 / 2 AI 输出 / 3 斜杠 / 5 世界书 / 6 思维链）")
        elif 2 not in (s.get("placement") or []):
            rep.warn("R03", f"{tag}.placement 不含 2（AI 输出）：界面不会出现在回复里")
        bookkeeping = any(t in str(s.get("findRegex", ""))
                          for t in ("update", "UpdateVariable", "StatusPlaceHolder"))
        if s.get("markdownOnly") is not True and not bookkeeping:
            rep.warn("R04", f"{tag} markdownOnly 不是 true：替换后的 HTML 会进提示词与聊天记录")
        patterns.append(str(s.get("findRegex", "")))

    errors = js_check_regex(patterns)
    compiled_ok = 0
    for i, (s, err) in enumerate(zip([x for x in scripts if isinstance(x, dict)], errors)):
        pattern = str(s.get("findRegex", ""))
        if err:
            rep.fail("R05", f"正则[{i}].findRegex 编译不了：{err}（{pattern[:60]!r}）")
            continue
        problem = static_regex_problem(pattern)
        if problem:
            rep.fail("R05", f"正则[{i}].findRegex 编译不了：{problem}（{pattern[:60]!r}）")
            continue
        compiled_ok += 1
    if compiled_ok:
        rep.ok("R05", f"{compiled_ok} 条 findRegex 可编译" + ("（node 实测）" if shutil.which("node") else "（静态检查）"))

    for i, s in enumerate([x for x in scripts if isinstance(x, dict)]):
        groups = count_capture_groups(str(s.get("findRegex", "")))
        repl = str(s.get("replaceString", ""))
        uses_dollar = bool(re.search(r"\$\{?[1-9]", repl))
        if uses_dollar and groups == 0:
            rep.fail("R06", f"正则[{i}] 用了 $1 但 findRegex 没有捕获组：数据会整段丢失")
        bookkeeping = any(t in str(s.get("findRegex", ""))
                          for t in ("update", "UpdateVariable", "StatusPlaceHolder"))
        if groups > 0 and not uses_dollar and not bookkeeping:
            rep.warn("R06", f"正则[{i}] 有 {groups} 个捕获组但 replaceString 没引用 $1（若有意为之可忽略）")
        pending = PENDING_UI_MARK in repl
        if uses_dollar and not looks_like_ui(repl) and not pending:
            rep.warn("R06", f"正则[{i}] 的 replaceString 既不是 ```html 围栏也不是整段 HTML："
                            f"酒馆助手不会把它当界面渲染")
        hiding = bookkeeping or any(w in str(s.get("scriptName", "")) for w in ("隐藏", "不显示", "不发送"))
        if pending:
            rep.ok("R07", f"正则[{i}] 界面待粘贴（导入包里带了 html，按导入说明粘）")
        elif not repl.strip() and not hiding and s.get("markdownOnly") and 2 in (s.get("placement") or []):
            rep.fail("R07", f"正则[{i}] 的 replaceString 是空的：空替换等于把这行字删掉，"
                            f"界面和内容都不会出现")
    return [s for s in scripts if isinstance(s, dict)]


# ---------------------------------------------------------------- 入口

def find_files(arg: str) -> tuple[Path | None, Path | None, Path | None, Path | None]:
    """从目录里认出四件：卡 / 正则 / 世界书 / 酒馆助手脚本（按文件名，内容由 sniff 兜底）。"""
    p = Path(arg)
    if not p.is_dir():
        return p, None, None, None
    card = regex = book = script = None
    files = sorted(p.glob("*.json")) or sorted(p.glob("*/*.json"))
    for f in files:
        low = f.name.lower()
        if "世界书" in f.name or "worldbook" in low:
            book = book or f
        elif "正则" in f.name or "regex" in low:
            regex = regex or f
        elif "酒馆助手脚本" in f.name or "tavern-helper" in low or "tavern_helper" in low:
            script = script or f
        elif "（纯净）" in f.name or "(纯净)" in f.name or "pure" in low:
            card = card or f
        elif '"spec"' in f.read_text(encoding="utf-8", errors="ignore")[:600]:
            card = card or f  # 没按命名惯例，但确实是张卡
    return card, regex, book, script


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    contract = None
    contract_path = None
    if "--contract" in argv:
        idx = argv.index("--contract")
        try:
            cpath = Path(argv[idx + 1])
        except IndexError:
            print("--contract 后面要跟契约路径", file=sys.stderr)
            return 2
        try:
            import yaml
            contract = yaml.safe_load(cpath.read_text(encoding="utf-8"))
            contract_path = cpath
        except Exception as exc:  # noqa: BLE001
            print(f"读不到契约 {cpath}：{exc}", file=sys.stderr)
            return 2
        argv = argv[:idx] + argv[idx + 2:]
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2

    card_path, regex_path, book_path, script_file = find_files(args[0])
    if len(args) > 1:
        regex_path = Path(args[1])
    if len(args) > 2:
        book_path = Path(args[2])

    if card_path is None or not card_path.exists():
        here = Path(args[0])
        seen = sorted(x.name for x in here.iterdir()) if here.is_dir() else []
        print("读不到角色卡。交付件要放在 `导入包/` 根下："
              "  <世界名>（纯净）.json · 正则.json · <世界名> 世界书.json"
              " · <世界名> 酒馆助手脚本.json · <世界名> 开局前端.html · 导入说明.txt"
              f"当前目录里的东西：{seen or '（空）'}"
              "子目录里的旧包（单文件卡 / st/ 里那一坨）要按新规矩重打一次，别原地改。",
              file=sys.stderr)
        return 2

    rep = Report()
    try:
        card = json.loads(card_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"角色卡不是合法 JSON：{exc}", file=sys.stderr)
        return 2
    if not isinstance(card, dict):
        print("角色卡顶层必须是对象", file=sys.stderr)
        return 2

    # P01 三件齐全
    missing = []
    if not book_path or not book_path.exists():
        missing.append("世界书")
    if not regex_path or not regex_path.exists():
        missing.append("正则")
    if missing:
        rep.fail("P01", f"三件套缺 {' 与 '.join(missing)}：本包交付就是「纯净卡 + 正则 + 世界书」三份，"
                         "缺一件用户就得自己补")
    else:
        rep.ok("P01", f"三件齐全：{card_path.name} / {regex_path.name} / {book_path.name}")

    book = {}
    if book_path and book_path.exists():
        try:
            book = json.loads(book_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            rep.fail("W00", f"世界书不是合法 JSON：{exc}")
            book = {}
        if book and not isinstance(book, dict):
            rep.fail("W00", "世界书顶层必须是对象")
            book = {}

    scripts = None
    if regex_path and regex_path.exists():
        try:
            scripts = json.loads(regex_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            rep.fail("R00", f"正则文件不是合法 JSON：{exc}")
            scripts = None

    data = validate_card(card, card_path, book_path, rep)
    stages = (contract or {}).get("stages") or ((contract or {}).get("project") or {}).get("stages") or {}
    mvu_done = str(stages.get("mvu", "")) == "done"
    entry_count = validate_worldbook(book, book_path, rep, mvu_done) if book else 0
    if book and isinstance(book.get("entries"), dict):
        draft_root = None
        if contract_path is not None and contract_path.name == "contract.yaml":
            root = contract_path.parent.parent.parent  # …/制作文件/项目记录/contract.yaml
            draft_root = root / "制作文件" / "产物"
        if draft_root is None and card_path is not None:
            guess = card_path.parent.parent / "制作文件" / "产物"
            draft_root = guess if guess.is_dir() else None
        if draft_root is not None and draft_root.is_dir():
            check_cut_fidelity(book["entries"], draft_root, rep)
    script_list = validate_regex_pack(scripts, regex_path, rep)

    # ---- 交叉检查 ----
    desc = str(data.get("description") or "")
    if not desc.strip():
        rep.fail("X01", "data.description 为空：卡里没有设定正文")
    elif len(desc) > DESC_HARD:
        rep.fail("X01", f"description {len(desc)} 字，超过硬上限 {DESC_HARD}："
                        "群像卡的主要篇幅应在世界书条目里")
    elif len(desc) > DESC_SOFT:
        rep.warn("X01", f"description {len(desc)} 字，超过建议值 {DESC_SOFT}")
    else:
        rep.ok("X01", f"description {len(desc)} 字（上限 {DESC_HARD}）")

    # X02 轴名必须能在卡或书里找到
    axis_names = []
    if isinstance(contract, dict):
        naming = contract.get("naming") or {}
        for ax in naming.get("axes") or []:
            if isinstance(ax, dict) and str(ax.get("name") or "").strip():
                axis_names.append(str(ax["name"]).strip())
    if not axis_names:
        rep.warn("X02", "没给 --contract 或契约里没有 naming.axes：轴名完整性跳过")
    else:
        blob = desc + " " + " ".join(
            str(e.get("content") or "") for e in (book.get("entries") or {}).values() if isinstance(e, dict))
        miss = [a for a in axis_names if a not in blob]
        if miss:
            rep.fail("X02", f"轴名在卡与世界书里都找不到：{'、'.join(miss)}。"
                            "数值系统没有进包，慢热与阈值在扮演里等于不存在")
        else:
            rep.ok("X02", f"{len(axis_names)} 个轴名都在包里")

    # X03 world 名 == 世界书文件名（导入时用文件名建书）
    world = str(nested_get(data, "extensions.world")[0] or "")
    if world and book_path and book_path.exists():
        if world != book_path.stem:
            rep.fail("X03", f"extensions.world = {world!r}，世界书文件叫 {book_path.stem!r}："
                            "两者必须同名，否则导入后卡不会自动挂上书")
        else:
            rep.ok("X03", f"世界书名一致：{world!r}")

    # X04 first_mes 能被某个正则接住
    first_mes = str(data.get("first_mes") or card.get("first_mes") or "")
    if first_mes.strip():
        matched = [i for i, s in enumerate(script_list)
                   if _matches(str(s.get("findRegex", "")), first_mes)]
        if matched:
            rep.ok("X04", f"first_mes 能被正则[{matched[0]}] 接住")
        else:
            tags = TAG_RE.findall(first_mes)
            if tags:
                rep.fail("X04", f"first_mes 里的标签 {['<' + t + '>' for t in tags]} 没有正则能匹配："
                                "第一楼会是裸标签")
            else:
                rep.ok("X04", "first_mes 是纯文本，不依赖正则")

    # X05 占位符（三件都要干净）
    chunks = [desc, str(data.get("system_prompt") or ""), str(data.get("creator_notes") or ""),
              str(first_mes)]
    chunks += [str(e.get("content") or "") for e in (book.get("entries") or {}).values() if isinstance(e, dict)]
    chunks += [str(s.get("replaceString") or "")[:200000] for s in script_list]
    hits = sorted({ph for chunk in chunks for ph in PLACEHOLDERS if ph in chunk})
    if hits:
        rep.fail("X05", f"包里有构建期占位符（{'、'.join(hits)}）：模型会把它当设定读，甚至写进回复")
    else:
        rep.ok("X05", "三件里都没有构建期占位符")

    # X06 做了 mvu 阶段就得把东西带齐：独立脚本文件（含 MVU 加载器）、两条隐藏正则
    stages = (contract or {}).get("stages") if isinstance(contract, dict) else {}
    stages = stages if isinstance(stages, dict) else {}
    stage_mvu = stages.get("mvu") if isinstance(stages, dict) else None
    if stage_mvu == "done":
        scripts = nested_get(data, "extensions.tavern_helper.scripts")[0]
        if isinstance(scripts, list) and scripts:
            rep.ok("X06", f"卡内脚本 {len(scripts)} 条（C12 会另判这是不是该单独发）")
        elif script_file is None:
            rep.fail("X06", "`stages.mvu: done` 但既没有卡内脚本也没有 "
                            "`<世界名> 酒馆助手脚本.json`：MVU 不跑、变量永远是初值，而且不报错")
        else:
            body = script_file.read_text(encoding="utf-8")
            if "MVU" not in body.upper():
                rep.warn("X06", "脚本文件里没有名字含 MVU 的那条（一般是 import 一行 bundle 的加载器）")
            else:
                rep.ok("X06", f"独立脚本文件 {script_file.name} 里有 MVU 加载器")
        if not script_list:
            rep.fail("X06", "`stages.mvu: done` 但正则文件缺失")
        else:
            pats = " ".join(str(x.get("findRegex", "")) for x in script_list)
            if "(update" not in pats.lower():
                rep.fail("X06", "正则里没有隐藏 <UpdateVariable> 的规则：模型下一轮会读到自己的补丁")
            elif not any(x.get("markdownOnly") for x in script_list):
                rep.warn("X06", "没有 markdownOnly 的隐藏规则：玩家会看到 JSONPatch 原文")
            else:
                rep.ok("X06", "两条隐藏更新块的正则都在")

    if stage_mvu == "done" and stages.get("statusbar", stages.get(6, stages.get("6"))) == "done":
        validate_mvu_panel(script_list, rep)

    rep.dump(as_json)
    return 0 if not rep.failures else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    sys.exit(main(sys.argv[1:]))
