# 变更记录

版本号写在 `SKILL.md` frontmatter 的 `metadata.version`；这份文件的第一条标题必须与它一致，
由 `tests/test_version.py` 守着。

## 1.1.00 — 2026-11-21

**破坏性变更：作品目录改成两层。** 旧项目要搬一次，脚本会拦着不让你两套并存。

| 旧 | 新 |
|---|---|
| `创作痕迹/` | `制作文件/`（原稿、源码、检查材料） |
| `创作痕迹/{contract, 项目档案, 创作记录, 检索来源, 验收, 试演记录}` | `制作文件/项目记录/` 下同名文件 |
| `创作痕迹/产物/` | `制作文件/产物/`（不变） |
| `最终产物/` | `导入包/`（交付成品，平铺） |

- 作品根下只许 `制作文件/` 与 `导入包/`（新门 **C17**）：发现 `创作痕迹/` 或 `最终产物/` 直接失败并给迁移提示，根目录散落文件记警告。
- `validate-contract.py` 接受项目根、`制作文件/`、`制作文件/项目记录/`、契约文件四种入口。
- `scripts/run_checks.sh`、`check-stage.py`、`check_acceptance.py`、`validate-st-package.py`、
  `validate_st_semantics.py`、`check_prose.py`、`st-import.py`、`st-probe.js` 全部改指新路径。
- 示例包重排：`examples/dry-run-盐湖守夜人/{制作文件/项目记录, 制作文件/产物, 导入包}`，原 `README.md` 移入 `制作文件/试跑记录.md`。
- 新增 `tests/test_layout.py`（旧布局阻断、根目录清洁、账本归位、导入包平铺）。
- 加载量在改名后涨了 190 tok；靠 `SKILL.md` 与 `references/pipeline.md` 就地回收冗余抵平（**基线未动**）。

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
