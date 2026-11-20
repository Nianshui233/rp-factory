# 变更记录

版本号写在 `SKILL.md` frontmatter 的 `metadata.version`；这份文件的第一条标题必须与它一致，
由 `tests/test_version.py` 守着。

## 1.0.01 — 2026-11-21

首个带版本号的版本。此前四轮工作合并入 `main`。

**产物合规层**
- 十四道门统一编号 0–13，`references/pipeline.md` 为唯一权威；加载预算器 `scripts/measure_load.py`
  （绝对上限 26,000，九阶段各自基线）。
- 契约新增 `player_agency`（player-controlled / limited / delegated）与角色卡 `facts`（stable / temporary）。
- 世界书写作文档 `references/worldbook-writing.md`（句子功能、五档强度、知识度数、语义不变量）。

**质量层**
- `scripts/check_prose.py` P01–P09 去 AI 味（含真包校准：免疫区、内联长值、台词误报）。
- `references/rehearsal.md` 试演：四类证据分离、最小响应八种、四类判据（代演 / OOC / 口癖 / 数值闸门）。
- `references/acceptance.md` 六层证据 + `scripts/check_acceptance.py`（A00–A06，L4 十一维，L5/L6 只能人签）。

**SillyTavern 正确性层**
- `references/st-correctness.md`：S-01…S-29 会静默失效的语义事实，每条带 `public/…:line` 锚点。
- `scripts/validate_st_semantics.py`（S 系列机检）、`scripts/check_st_facts.py`（34 个 ST 锚点 + 10 个插件锚点）。
- `references/tavern-helper.md`：酒馆助手 4.12.1 接口速查（渲染链路、srcdoc 约束、iframe 全局、
  变量/消息/显示/事件/MVU、23 个命名空间索引、静默失效清单）。
- `scripts/validate-frontend.py` F01–F14（新增 F10–F14：事件名写字符串、相对路径、父文档、
  `refresh:'all'`、裸 `setInterval`）。

**工程**
- `scripts/run_checks.sh` 一键全检；`tests/` 143 个用例；`scripts/embed-book.py` 世界书双入口。
- 真机实证：卡内 scoped 正则默认不生效且取消一次永久静默（S-28）、内嵌书按 `character_book.name`
  落盘（S-29）、导入 API 用 `avatar` 字段。
