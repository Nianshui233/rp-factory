#!/usr/bin/env bash
# 一键全检：包自身的不变量 + 加载预算（+ 给了创作目录时的产物校验）。
#
#   bash scripts/run_checks.sh                 # 只查包自身
#   bash scripts/run_checks.sh 某创作目录       # 再查该目录里的契约/三件/语义/验收
#
# Windows 下用 Git Bash 或 WSL 跑。退出码：0 全绿；1 有失败项。
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python}"
cd "$ROOT" || exit 1

# 版本号只有一处真相：SKILL.md 的 metadata.version（tests/test_version.py 守着）
VERSION="$(sed -n 's/^  version: *\([0-9.]*\).*/\1/p' SKILL.md | head -1)"
printf 'rp-factory v%s\n' "${VERSION:-unknown}"

fails=0
run() {
  local name="$1"; shift
  printf '\n== %s ==\n' "$name"
  if "$@"; then
    printf '   ok\n'
  else
    printf '   FAILED: %s\n' "$name"
    fails=$((fails + 1))
  fi
}

run "包结构不变量 + 单元测试" "$PY" -X utf8 -m unittest discover -s tests -t . -q
run "加载预算" "$PY" -X utf8 scripts/measure_load.py

if [ "$#" -ge 1 ]; then
  DIR="$1"
  if [ ! -d "$DIR" ]; then
    printf '\n!! 创作目录不存在：%s\n' "$DIR"
    fails=$((fails + 1))
  else
    [ -f "$DIR/contract.yaml" ] && run "契约" "$PY" -X utf8 scripts/validate-contract.py "$DIR"
    if [ -d "$DIR/最终产物" ]; then
      run "三件结构" "$PY" -X utf8 scripts/validate-st-package.py "$DIR/最终产物"
      run "ST 语义" "$PY" -X utf8 scripts/validate_st_semantics.py "$DIR/最终产物"
    fi
    [ -f "$DIR/验收.yaml" ] && run "验收账本" "$PY" -X utf8 scripts/check_acceptance.py "$DIR"
  fi
fi

printf '\n== 结论 ==\n'
if [ "$fails" -eq 0 ]; then
  printf '全绿。\n'
  exit 0
fi
printf '%s 项未通过。\n' "$fails"
exit 1
