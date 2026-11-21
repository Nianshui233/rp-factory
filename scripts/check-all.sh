#!/usr/bin/env bash
# 仓库级全检：单元测试 + 清单版本一致性 + skill 构建同步 + skill 自身的加载预算。
#
#   bash scripts/check-all.sh                 # 只查仓库
#   bash scripts/check-all.sh 某创作目录       # 再查该目录里的契约/三件/语义/验收
#
# 这是发布前唯一要跑的一条。skill 里那份 `run_checks.sh` 只查加载预算与产物，
# 单元测试和清单校验都在仓库这一层。
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SKILL="$REPO/skills/rp-factory"
PY="${PYTHON:-python}"
cd "$REPO" || exit 1

# Windows 控制台是 GBK：不指定 UTF-8 时，脚本里打印 `✗`/`—` 会 UnicodeEncodeError，
# 于是两条本来该过的测试红掉。这里统一钉死，别依赖当前终端。
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

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

run "单元测试（包结构 / 契约 / 校验器 / 清单）" "$PY" -X utf8 -m unittest discover -s tests -t . -q

if [ -f "$REPO/scripts/sync-manifests.py" ]; then
  run "清单版本一致性" "$PY" -X utf8 scripts/sync-manifests.py --check
fi

run "构建产物与仓库一致" "$PY" -X utf8 scripts/build-skill.py --check
run "加载预算与产物校验" bash "$SKILL/scripts/run_checks.sh" "$@"

if [ "$fails" -gt 0 ]; then
  printf '\n== 结论 ==\n%d 项没过。\n' "$fails"
  exit 1
fi
printf '\n== 结论 ==\n全绿。\n'
