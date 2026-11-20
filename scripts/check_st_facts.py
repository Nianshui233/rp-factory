#!/usr/bin/env python3
"""校验 references/st-correctness.md 里的源码锚点还站得住。

动机：那份文件里的每条判据都指到 ST 源码的某一行，ST 一升级行号就漂。漂了以后
文档仍然言之凿凿，读者却查不到原文——比没有文档更糟。所以把锚点写成可执行的表。

CLI:
    python scripts/check_st_facts.py                      # 用默认 ST 路径
    python scripts/check_st_facts.py --st-root D:/AI/SillyTavern
    python scripts/check_st_facts.py --tolerance 40        # 放宽行号漂移容忍
    python scripts/check_st_facts.py --json
退出码：0 全部命中；1 有漂移/缺失；2 参数错误。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_ST_ROOT = os.environ.get("ST_ROOT", r"D:/AI/SillyTavern")

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


def verify(rows, root: Path, tolerance: int = 25) -> list[str]:
    """返回问题列表；空表示全部锚点仍然成立。rows 允许 3 元组或 4 元组。"""
    problems: list[str] = []
    for row in rows:
        rel, needle, expected = row[0], row[1], row[2]
        code = row[3] if len(row) > 3 else ""
        path = Path(root) / rel
        if not path.exists():
            problems.append(f"{code} 文件不存在：{rel}（ST 根目录对不上？）")
            continue
        found = _find_line(path, needle)
        if found is None:
            problems.append(f"{code} 找不到特征串：{rel} 里的 {needle!r}——ST 改写了这段，事实表需要复核")
        elif abs(found - expected) > tolerance:
            problems.append(f"{code} 行号漂移：{rel}:{expected} → 实际 {found}（容差 {tolerance}）")
    return problems


def main(argv: list[str]) -> int:
    root = Path(DEFAULT_ST_ROOT)
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
    if as_json:
        print(json.dumps({"st_root": str(root), "tolerance": tolerance,
                          "anchors": len(FACTS), "problems": problems},
                         ensure_ascii=False, indent=2))
    else:
        print(f"ST 根目录：{root}（容差 {tolerance} 行，{len(FACTS)} 个锚点）")
        if problems:
            for p in problems:
                print(f"  ✗ {p}")
            print("\n有锚点失效：先复核 references/st-correctness.md，再改这张表。")
        else:
            print("  全部锚点命中。")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
