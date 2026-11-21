#!/usr/bin/env python3
"""校验 references/st-correctness.md 里的源码锚点还站得住。

动机：那份文件里的每条判据都指到 ST 源码的某一行，ST 一升级行号就漂。漂了以后
文档仍然言之凿凿，读者却查不到原文——比没有文档更糟。所以把锚点写成可执行的表。

CLI:
    python scripts/check_st_facts.py                      # 用默认 ST 路径
    python scripts/check_st_facts.py --st-root D:/AI/SillyTavern
    python scripts/check_st_facts.py --th-root D:/path/to/JS-Slash-Runner
    python scripts/check_st_facts.py --tolerance 40        # 放宽行号漂移容忍
    python scripts/check_st_facts.py --json
退出码：0 全部命中；1 有漂移/缺失；2 参数错误。

锚点分两组：S-xx 指向 SillyTavern 本体（references/st-correctness.md），
TH-xx 指向酒馆助手插件（references/tavern-helper.md）。插件根目录不存在时
TH 组自动跳过，不算失败。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_ST_ROOT = os.environ.get("ST_ROOT", r"D:/AI/SillyTavern")
DEFAULT_TH_ROOT = os.environ.get("TH_ROOT", r"D:/AI/RP创作/参考/JS-Slash-Runner")

ENGINE = "public/scripts/extensions/regex/engine.js"
REGEX_INDEX = "public/scripts/extensions/regex/index.js"
WORLD_INFO = "public/scripts/world-info.js"
SCRIPT = "public/script.js"
MACROS = "public/scripts/macros.js"

# (相对路径, 唯一特征串, 期望行号, 对应事实编号)
FACTS: list[tuple[str, str, int, str]] = [
    (ENGINE, "export const regex_placement = {", 281, "S-01"),
    (ENGINE, "script.placement.includes(placement)", 374, "S-01"),
    (ENGINE, "(script.markdownOnly && isMarkdown)", 350, "S-02"),
    (ENGINE, "if (isEdit && !script.runOnEdit)", 356, "S-08"),
    (ENGINE, "export function getRegexedString(rawString, placement", 334, "S-01"),
    (ENGINE, "switch (Number(regexScript.substituteRegex))", 398, "S-03"),
    (ENGINE, "regexScript.replaceString.replace(/{{match}}/gi, '$0')", 421, "S-05"),
    (ENGINE, "replaceAll(/\\$(\\d+)|\\$<([^>]+)>/g", 422, "S-04"),
    (ENGINE, "return substituteParams(replaceWithGroups)", 445, "S-06"),
    (WORLD_INFO, "export const world_info_logic = {", 33, "S-13"),
    (WORLD_INFO, "export let world_info_budget = 25;", 73, "S-12"),
    (WORLD_INFO, "export let world_info_budget_cap = 0;", 81, "S-12"),
    (WORLD_INFO, "const sortFn = (a, b) => b.order - a.order;", 88, "S-11"),
    (WORLD_INFO, "export const world_info_position = {", 855, "S-10"),
    (WORLD_INFO, "export function convertCharacterBook(characterBook)", 5617, "S-15"),
    (WORLD_INFO, "keysecondary: entry.secondary_keys || [],", 5630, "S-15"),
    (WORLD_INFO, "position: entry.extensions?.position ?? (entry.position === 'before_char'", 5636, "S-15"),
    (WORLD_INFO, "const bookName = characters[chid]?.data?.character_book?.name", 5744, "S-14"),
    (WORLD_INFO, "if (characters[chid]?.data?.character_book) {", 5698, "S-24"),
    (WORLD_INFO, "export async function importEmbeddedWorldInfo(skipPopup = false)", 5730, "S-24"),
    (WORLD_INFO, "books.push(character.data.extensions.world);", 1128, "S-14"),
    (WORLD_INFO, "data.data.character_book = undefined;", 6114, "S-16"),
    (WORLD_INFO, "let budget = Math.round(world_info_budget * maxContext / 100) || 1;", 4736, "S-31"),
    (WORLD_INFO, "!entry.ignoreBudget && (textToScanTokens + (await getTokenCountAsync(newContent))) >= budget", 5061, "S-31"),
    (WORLD_INFO, "export let world_info_overflow_alert = false;", 76, "S-31"),
    (WORLD_INFO, "const isASticky = timedEffects.isEffectActive('sticky', a) ? 1 : 0;", 4999, "S-32"),
    (WORLD_INFO, "if (data.startsWith('@@@')) {", 4659, "S-33"),
    (WORLD_INFO, "export let world_info_include_names = true;", 74, "S-34"),
    (SCRIPT, "world_info_include_names ? `${x.name}: ${x.mes}` : x.mes", 4624, "S-34"),
    (WORLD_INFO, "export let world_info_recursive = false;", 75, "S-35"),
    (SCRIPT, "export const extension_prompt_roles = {", 494, "S-18"),
    (SCRIPT, "mes: getRegexedString(firstMes, regex_placement.AI_OUTPUT)", 7719, "S-22"),
    (MACROS, "export function evaluateMacros(content, env, postProcessFn)", 610, "S-19"),
    (MACROS, "{ regex: /<USER>/gi", 625, "S-06"),
    (ENGINE, "@typedef {{characterOverride?: string, isMarkdown?: boolean, isPrompt?: boolean, isEdit?: boolean, depth?: number }}", 332, "S-25"),
    (ENGINE, "const replaceString = regexScript.replaceString.replace(", 421, "S-26"),
    (ENGINE, "!(regexScript.disabled) || !regexScript?.findRegex", 393, "S-27"),
    (ENGINE, "export function isScopedScriptsAllowed(character) {", 166, "S-28"),
    (REGEX_INDEX, "async function checkCharEmbeddedRegexScripts() {", 1606, "S-28"),
    (REGEX_INDEX, "accountStorage.setItem(checkKey, 'true');", 1617, "S-28"),
    (REGEX_INDEX, "const template = await renderExtensionTemplateAsync('regex', 'embeddedScripts', {});", 1618, "S-28"),
    (WORLD_INFO, "const bookName = characters[chid]?.data?.character_book?.name", 5744, "S-29"),
    (REGEX_INDEX, "$('#import_regex_file').on('change', async function () {", 1750, "S-30"),
    (REGEX_INDEX, "template.find('#regex_import_target_scoped').on('input', () => (target = SCRIPT_TYPES.SCOPED));", 1754, "S-30"),
]

# 酒馆助手（JS-Slash-Runner 4.12.1 / f9c95ab）的锚点。插件才是把 HTML 送上屏的那一层，
# 所以它的行为比 ST 本体更容易被写错的文档带偏。路径相对插件仓库根。
TH_FACTS: list[tuple[str, str, int, str]] = [
    ("src/util/is_frontend.ts", "return ['html>', '<head>', '<body'].some(tag => content.includes(tag));", 2, "TH-01"),
    ("src/panel/render/iframe.ts", "html,body{margin:0!important;padding:0;overflow:hidden!important;max-width:100%!important;}", 89, "TH-02"),
    ("src/panel/render/iframe.ts", "const VARIABLE_EXPRESSION = `var(--TH-viewport-height)`;", 24, "TH-03"),
    ("src/iframe/adjust_iframe_height.js", "frameElement.style.height = `${height}px`;", 21, "TH-04"),
    ("src/iframe/adjust_viewport.js", "$('html').css('--TH-viewport-height', `${window.parent.innerHeight}px`);", 1, "TH-05"),
    ("src/iframe/predefine.js", "result = result.merge(_.pick(window.parent, ['EjsTemplate', 'TavernHelper', 'YAML', 'showdown', 'toastr', 'z']));", 12, "TH-06"),
    ("src/type/settings.ts", "export const setting_field = 'tavern_helper';", 3, "TH-07"),
    ("src/panel/render/use_collapse_code_block.ts", "if ($div.children('iframe').length > 0) {", 43, "TH-08"),
    ("@types/iframe/event.d.ts", "CHAT_CHANGED: 'chat_id_changed';", 206, "TH-09"),
    ("@types/iframe/exported.mvu.d.ts", "VARIABLE_UPDATE_ENDED: 'mag_variable_update_ended';", 115, "TH-10"),
    ("src/panel/script/Toolbar.vue", "script_tree.enabled = false;", 94, "TH-11"),
    ("src/panel/script/Toolbar.vue", "script_tree.id = uuidv4();", 95, "TH-11"),
]


def _find_line(path: Path, needle: str) -> int | None:
    """返回 needle 首次出现的 1-based 行号；找不到返回 None。"""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, start=1):
                if needle in line:
                    return number
    except FileNotFoundError:
        return None
    return None


def verify(rows, root: Path, tolerance: int = 25, label: str = "ST") -> list[str]:
    """返回问题列表；空表示全部锚点仍然成立。rows 允许 3 元组或 4 元组。"""
    problems: list[str] = []
    for row in rows:
        rel, needle, expected = row[0], row[1], row[2]
        code = row[3] if len(row) > 3 else ""
        path = Path(root) / rel
        if not path.exists():
            problems.append(f"{code} 文件不存在：{rel}（{label} 根目录对不上？）")
            continue
        found = _find_line(path, needle)
        if found is None:
            problems.append(f"{code} 找不到特征串：{rel} 里的 {needle!r}——{label} 改写了这段，事实表需要复核")
        elif abs(found - expected) > tolerance:
            problems.append(f"{code} 行号漂移：{rel}:{expected} → 实际 {found}（容差 {tolerance}，对照的是{label}副本）")
    return problems


def main(argv: list[str]) -> int:
    root = Path(DEFAULT_ST_ROOT)
    th_root = Path(DEFAULT_TH_ROOT)
    tolerance = 25
    as_json = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--st-root":
            i += 1
            if i >= len(argv):
                print("--st-root 需要一个路径", file=sys.stderr)
                return 2
            root = Path(argv[i])
        elif arg == "--th-root":
            i += 1
            if i >= len(argv):
                print("--th-root 需要一个路径", file=sys.stderr)
                return 2
            th_root = Path(argv[i])
        elif arg == "--tolerance":
            i += 1
            try:
                tolerance = int(argv[i])
            except (IndexError, ValueError):
                print("--tolerance 需要一个整数", file=sys.stderr)
                return 2
        elif arg == "--json":
            as_json = True
        elif arg in ("-h", "--help", "--verify"):
            if arg == "-h" or arg == "--help":
                print(__doc__)
                return 0
        else:
            print(f"未知参数：{arg}", file=sys.stderr)
            return 2
        i += 1

    problems = verify(FACTS, root, tolerance)
    th_problems = verify(TH_FACTS, th_root, tolerance, "酒馆助手") if th_root.exists() else []
    th_skipped = not th_root.exists()
    all_problems = problems + th_problems
    if as_json:
        print(json.dumps({"st_root": str(root), "tolerance": tolerance,
                          "anchors": len(FACTS),
                          "th_root": str(th_root), "th_anchors": len(TH_FACTS) if not th_skipped else 0,
                          "th_skipped": th_skipped,
                          "problems": all_problems},
                         ensure_ascii=False, indent=2))
    else:
        print(f"ST 根目录：{root}（容差 {tolerance} 行，{len(FACTS)} 个锚点）")
        if problems:
            for p in problems:
                print(f"  ✗ {p}")
        else:
            print("  全部锚点命中。")
        if th_skipped:
            print(f"酒馆助手：跳过（{th_root} 不存在，用 --th-root 指定插件仓库）")
        else:
            print(f"酒馆助手根目录：{th_root}（{len(TH_FACTS)} 个锚点）")
            if th_problems:
                for p in th_problems:
                    print(f"  ✗ {p}")
            else:
                print("  全部锚点命中。")
        if all_problems:
            print("\n有锚点失效：先复核 references/st-correctness.md 与 references/tavern-helper.md，再改这张表。")
    return 1 if all_problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
