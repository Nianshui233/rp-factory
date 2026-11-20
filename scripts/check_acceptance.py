#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验收账本校验：六层证据，脚本不许给「真机」和「人眼」签字。

规则抄的是被反复踩的坑：自动化脚本跑绿了就宣布「在酒馆里验证通过」，而实际上
酒馆没开、界面没渲染、用户没看。所以账本把每个结论按来源分层，并且限制谁能签哪一层。

账本位置：`创作痕迹/验收.yaml`（格式见 references/acceptance.md）

    entries:
      - {layer: L2, item: 契约校验, evidence: "validate-contract.py → exit 0", verdict: pass, by: script}
      - {layer: L5, item: 真机导入, evidence: "手动导入后回读三件齐全；截图 12:31", verdict: pass, by: human}

检查：
    A00 账本能读
    A01 layer 在六层枚举里
    A02 verdict 只能是 pass / fail / skipped；skipped 必须写 why
    A03 L1/L2 的证据必须带退出码（脚本类结论的唯一凭据）
    A04 L5（真机）/ L6（人眼）只能由 human 签，脚本自签即失败
    A05 整本账里没有 L5/L6 的 pass → 警告（没经过人看的交付不算验收过）

用法：
    python scripts/check_acceptance.py <项目根>
    python scripts/check_acceptance.py <项目根> --json
退出码：0 无 error；1 有 error；2 参数错误。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LAYERS = {
    "L1": "源码/机制（读实现或官方文档得出的事实）",
    "L2": "脚本（本项目校验器的退出码）",
    "L3": "离线快照（固定输入的期望输出比对）",
    "L4": "浏览器（渲染/交互，未进酒馆）",
    "L5": "真机 ST（导入、挂书、开局实跑）",
    "L6": "人眼（用户或作者自己看过成品）",
}
VERDICTS = {"pass", "fail", "skipped"}
HUMAN_LAYERS = {"L5", "L6"}
EXIT_HINT = re.compile(r"exit\s*[=:]?\s*\d|退出码\s*\d|exit\s+code\s+\d", re.I)


def _findings() -> list:
    return []


def _load(path: Path):
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        return None, "缺少 PyYAML：pip install pyyaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"YAML 解析失败：{exc}"
    if not isinstance(data, dict):
        return None, "顶层不是映射（期望 `entries: [...]`）"
    return data, None


def check_project(root: Path) -> list[dict]:
    out: list[dict] = []

    def add(severity: str, code: str, message: str) -> None:
        out.append({"severity": severity, "code": code, "message": message})

    path = root / "创作痕迹" / "验收.yaml"
    if not path.is_file():
        path = root / "验收.yaml"
    if not path.is_file():
        add("error", "A00", "找不到 `创作痕迹/验收.yaml`：验收结论必须逐条落账，"
                           f"没有账本就是没有验收（格式见 references/acceptance.md）")
        return out

    data, err = _load(path)
    if err:
        add("error", "A00", f"账本读不了：{err}")
        return out

    entries = data.get("entries")
    if not isinstance(entries, list):
        add("error", "A00", "`entries` 必须是列表")
        return out

    has_human_pass = False
    for i, raw in enumerate(entries, 1):
        entry = raw if isinstance(raw, dict) else {}
        label = entry.get("item") or f"第 {i} 条"

        layer = entry.get("layer")
        if layer not in LAYERS:
            add("error", "A01", f"{label}：layer = {layer!r}，只能是 {' / '.join(LAYERS)}")
            continue

        verdict = entry.get("verdict")
        if verdict not in VERDICTS:
            add("error", "A02", f"{label}：verdict = {verdict!r}，只能是 pass / fail / skipped")
        elif verdict == "skipped" and not str(entry.get("why") or "").strip():
            add("error", "A02", f"{label}：skipped 必须写 why（没跑就说清为什么没跑）")

        evidence = str(entry.get("evidence") or "")
        if layer in {"L1", "L2"} and not EXIT_HINT.search(evidence):
            add("error", "A03", f"{label}：{layer} 的证据必须带退出码（例：`validate-contract.py → exit 0`），"
                                f"现在是 {evidence!r}")

        by = str(entry.get("by") or "").strip().lower()
        if layer in HUMAN_LAYERS:
            if by != "human":
                add("error", "A04", f"{label}：{layer}（{LAYERS[layer]}）只能由 human 签，"
                                    f"脚本自签等于没验（by = {by or '空'}）")
            elif verdict == "pass":
                has_human_pass = True

    if entries and not has_human_pass:
        add("warning", "A05", "整本账里没有 L5/L6 的 pass：没人真正看过成品，"
                             "脚本全绿不等于交付能用")
    return out


def main(argv: list[str]) -> int:
    as_json = False
    paths: list[str] = []
    for arg in argv:
        if arg == "--json":
            as_json = True
        elif arg in ("-h", "--help"):
            print(__doc__)
            return 0
        elif arg.startswith("-"):
            print(f"未知参数：{arg}", file=sys.stderr)
            return 2
        else:
            paths.append(arg)
    if not paths:
        paths = ["."]

    findings: list[dict] = []
    for raw in paths:
        root = Path(raw)
        if not root.exists():
            print(f"路径不存在：{root}", file=sys.stderr)
            return 2
        findings.extend(check_project(root))

    errors = [f for f in findings if f["severity"] == "error"]
    if as_json:
        print(json.dumps({"findings": findings, "errors": len(errors)}, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print(f"[{'FAIL' if f['severity'] == 'error' else 'WARN'}] {f['code']} {f['message']}")
        if not findings:
            print("验收账本没问题。")
        elif errors:
            print(f"\n{len(errors)} 条不成立。层见 references/acceptance.md。")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
