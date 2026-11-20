# 吸收 TavernWeave 经验（不照抄）实现计划

> **执行记录（已完成，2026-11-21）**：9 个任务全部落地，方式 = Native（本会话自己实现），逐任务 commit `094d515 → 12664b5`。
> 三条 Ruling：① 门统一 **14 道**、编号 0–13，`references/pipeline.md` 为唯一权威、`SKILL.md` 只留索引表；② 加载预算改为「不高于本次实测基线 + 绝对上限 26,000」，另设 `SKILL.md` ≤6,600、`pipeline.md` ≤4,700；③ `delivery` 基线 +414 tok（用户要求的世界书双入口，非漂移），绝对上限不变。
> 验证：`bash scripts/run_checks.sh` 全绿（85 tests + 加载预算）；`python scripts/check_st_facts.py` 26 个锚点全命中（ST 1.19.0 `06bde939f`）。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 TavernWeave 的几个**方法**（证据分级、决定四态、文风门、语义事实表、结构测试）改写成 rp-factory 自己的形状，使交付的 RP 包既「好玩」又「SillyTavern 语义正确」，同时**不增加常驻加载量**。

**Architecture:** 三层落点，不新增阶段、不改九阶段顺序。
- **L1 常驻**（`SKILL.md` + `references/pipeline.md`）：只许加一行指针；本次先把 `SKILL.md`「六、硬门」的重复内容回收，腾出预算。
- **L2 条件**（`references/*.md`）：新增 3 份，各只在对应场景加载（`st-correctness.md` / `decisions.md` / `acceptance.md`）。
- **L3 脚本**：新增 3 个校验器 + 1 个预算器。运行时 0 token，只在失败时输出。

**Tech Stack:** Markdown + YAML + Python 3（stdlib + PyYAML，现有依赖）+ Node（仅 `st-probe.js` 已有）。测试用 `unittest`（不引入 pytest）。

**Spec:** `docs/reviews/2026-11-20-爱情公寓实操复盘.md`（10 条体检 + 用户 6 条）；本计划的「概念 → 落点」映射见下方 Source Map。

## Source Map（吸收什么，怎么改，不抄什么）

| 来源概念 | 原形态 | rp-factory 形态（改写后） | 不抄的部分 |
|---|---|---|---|
| 验收分层 | 6 层证据 + `driver-accepted` 标 | `references/acceptance.md`：6 层表 + 收尾汇报 6 行；脚本永不自签「人已验收」 | 云端/DSH 宿主适配 |
| 需求四态 | `confirmed/proposed/pending/rejected` | `references/decisions.md`：四态 + 缺口分级 + **「未答 ≠ 委托」** | 持久化到客户端配置 |
| 去 AI 味 | 一份文风 skill | `scripts/check_prose.py`（8 条正则）+ pipeline 一行指针 | 人格化改写、长清单 |
| API 事实核验 | 一个 api-reference skill | `references/st-correctness.md`：**每条事实必须有出处**（ST 源码 file:line 或文档 URL + 读取日期） | 整本 API 手册 |
| 可执行路由测试 | 23 个 `*.test.mjs` | `tests/`：结构断言 + replay fixture（只测本包自己的约定） | 23 skill 路由表 |
| 性能预算 | 一份 performance skill | `scripts/measure_load.py`：每阶段加载量 + 硬上限 | 媒体/Live2D 体积预算 |

**明确不吸收**（会摊薄本包，已与用户确认）：Soul 人格、23 skill 广度、跨宿主打包（Claude/Codex/Antigravity/DSH）、Live2D 与媒体、照镜子、工作资料库、拆卡/组件库/PNG 回嵌。它们属于「维护卡」而非「把构想编译成包」。

## Global Constraints

- **不新增阶段**，九阶段顺序、7 个占位符、产物 type 枚举一律不动。
- **加载预算（硬）**：`SKILL.md` ≤ 6,600 tok；`references/pipeline.md` ≤ 4,400 tok；**任一阶段的 worst-case 加载 ≤ 22,000 tok**（由 `scripts/measure_load.py` 判定，tok 估算式 `cjk*1.15 + (chars-cjk)/3.6`）。
- **L1 只加一行指针**：任何细则落进 `SKILL.md` / `pipeline.md` 必须 ≤1 行且带路径。
- **规则优先做成脚本**；脚本判不了的才写文档，并在文档里标 `manual:`。
- **ST 事实必须可溯源**：`references/st-correctness.md` 每一行的「出处」列必须是 `public/...:line`、`data/...`、或 `https://...`（含读取日期）。禁止凭印象写。
- **自包含**：不引用包外路径；不出现源提示词文件名。
- **一次只做一个阶段**的运行时纪律不变（`阶段门`）。

## Review Focus

1. 用户对追问沉默或说「你定」→ 产物必须走 `proposed` 并标 `【AI补全·可替换】`，不得写成 `confirmed` 硬设定。
2. 用户改了世界书文件名 → `extensions.world` 必须同步；不同步时 ST 静默不挂书，没有任何报错。
3. 卡内正则的 `replaceString` 用了 `$<name>` 而脚本里没有具名组 → 界面白屏但无报错（`engine.js:422` 支持两种写法，写错却不报错）。
4. 用户手改 `创作痕迹/产物/` 却不重跑 `check-stage.py` → 校验对象与交付内容不是同一份。
5. 新增规则的体积无人测量 → 本计划自己的纪律失效（由 Task 1 的预算器兜底）。

---

### Task 1: 加载预算器 + 回收 SKILL.md 硬门重复

**Files:**
- Create: `scripts/measure_load.py`
- Create: `tests/test_load_budget.py`
- Modify: `SKILL.md`（「## 六、硬门」整节压成索引表）
- Modify: `references/pipeline.md`（门编号修正：现自称「十一道门」，实际 0–11 共 12 项）

**Interfaces:**
- Produces: `measure_load.ALWAYS: list[str]`、`measure_load.LOAD_MAP: dict[str, list[str]]`、`measure_load.estimate(paths: list[str]) -> int`、`measure_load.report() -> list[tuple[str, int]]`；CLI `python scripts/measure_load.py [--stage NAME] [--json] [--max-tokens N]`，超预算退出码 1。
- 后续任务引用的硬上限常量：`MAX_STAGE_TOKENS = 22000`。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_load_budget.py
import importlib.util, pathlib, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
ml = load("measure_load", "scripts/measure_load.py")

class TestLoadBudget(unittest.TestCase):
    def test_every_stage_under_cap(self):
        rows = ml.report()                       # [("cast", 18417), ...]
        self.assertIn("cast", dict(rows))
        for stage, tok in rows:
            self.assertLessEqual(tok, ml.MAX_STAGE_TOKENS, f"{stage} 超预算：{tok}")

    def test_skill_md_too_big(self):
        self.assertLessEqual(ml.estimate(["SKILL.md"]), 6600)

    def test_pipeline_too_big(self):
        self.assertLessEqual(ml.estimate(["references/pipeline.md"]), 4400)

    def test_all_paths_exist(self):
        for paths in [ml.ALWAYS, *ml.LOAD_MAP.values()]:
            for p in paths:
                self.assertTrue((ROOT / p).exists(), p)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_load_budget -v`
Expected: FAIL —— `FileNotFoundError: scripts/measure_load.py`。

- [ ] **Step 3: 实现 `scripts/measure_load.py`**

`LOAD_MAP` 用 worst case（`web_research: true` 时的文件也算进去）。每个阶段都含 `references/pipeline.md` + `contract-schema.md` + 该阶段文件；`world` 加 `interview-protocol.md` 与 `web-research.md`；`cast`/`scenes`/`axes` 加 `interview-protocol.md`；`opening`/`statusbar` 加 `frontend-conventions.md` + `dual-mode.md`；`delivery` 加 `stage-7-delivery.md` + `worldbook-tuning.md` + `contract-schema.md`。表中键与 `pipeline.md` 阶段名一致：`world` `cast` `scenes` `axes` `mvu` `ejs` `opening` `statusbar` `delivery`。`estimate` 用上面的 tok 公式。

- [ ] **Step 4: 跑测试 —— 预期 `test_skill_md_too_big` 与 `test_every_stage_under_cap` 失败**

Run: `python scripts/measure_load.py`
Expected: 打印现有实测（`SKILL.md` ≈6,156，`statusbar` ≈24,286，`delivery` ≈25,715），退出码 1。

- [ ] **Step 5: 把 `SKILL.md`「## 六、硬门」压成索引表**

12 行（0–11），每行格式：`| N | 门名 | 一句话判据 | 细则 |`，细则列写 `references/pipeline.md#三-十二道门` 的具体段名。**不复述**「脚本查什么」——那部分本来就在 `pipeline.md` 与脚本里。目标：该节 ≤700 tok（现 1,399）。

- [ ] **Step 6: 修正 `pipeline.md` 的门计数**

标题改「## 三、十二道门」，正文按 0–11 逐一编号并与 `SKILL.md` 索引表逐行对齐（门名一字不差）。**门编号格式固定为 `**0. 开局门**`**（Task 8 的编号连续性测试依赖这个格式）。同时把 `SKILL.md` 里已删的细则在此处确认存在。

- [ ] **Step 7: 跑测试**

Run: `python -m unittest tests.test_load_budget -v && python scripts/measure_load.py`
Expected: 4 项全 PASS；`SKILL.md` ≤6,600、任一阶段 ≤22,000。

- [ ] **Step 8: 提交**

```bash
git add scripts/measure_load.py tests/test_load_budget.py SKILL.md references/pipeline.md
git commit -m "feat(预算): 加载量预算器 + 回收 SKILL.md 硬门重复"
```

---

### Task 2: ST 语义事实表（每条必须可溯源）

**Files:**
- Create: `references/st-correctness.md`
- Create: `tests/test_fact_table.py`
- Modify: `references/pipeline.md`（「开工前」加一行：涉及 ST 字段时先读该表）

**Interfaces:**
- Produces: 一张 5 列表 `| # | 事实 | 静默失败表现 | 校验 | 出处 |`，`#` 形如 `S01`…`S20`；`校验` 列为 `S01`（有脚本）或 `manual: <肉眼看什么>`；`出处` 列为 `public/...:line` / `data/...` / `https://...`（读取 YYYY-MM-DD）。
- 后续 Task 3 按 `#` 列实现同名检查。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_fact_table.py
import re, pathlib, unittest
DOC = pathlib.Path(__file__).resolve().parents[1] / "references/st-correctness.md"
ROW = re.compile(r"^\|\s*(S\d{2})\s*\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|\s*$")

class TestFactTable(unittest.TestCase):
    def setUp(self):
        self.rows = [m.groups() for m in map(ROW.match, DOC.read_text(encoding="utf-8").splitlines()) if m]
    def test_has_twenty_rows(self):
        self.assertGreaterEqual(len(self.rows), 20)
    def test_ids_unique_and_contiguous(self):
        ids = [r[0] for r in self.rows]
        self.assertEqual(ids, [f"S{i:02d}" for i in range(1, len(ids) + 1)])
    def test_every_row_has_source(self):
        for rid, fact, fail, check, src in self.rows:
            self.assertTrue(src.startswith(("public/", "data/", "https://")), f"{rid} 出处不可溯源：{src}")
    def test_every_row_has_check(self):
        for rid, fact, fail, check, src in self.rows:
            self.assertRegex(check.strip(), r"^(S\d{2}|manual: .+)$", f"{rid} 校验列不合法")
    def test_silent_failure_stated(self):
        for rid, fact, fail, check, src in self.rows:
            self.assertGreater(len(fail.strip()), 8, f"{rid} 没写静默失败表现")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_fact_table -v`
Expected: FAIL —— `FileNotFoundError`。

- [ ] **Step 3: 逐条核验并写表**

读本机 ST（`python scripts/detect-sillytavern.py --quiet` 报 `D:/AI/SillyTavern (1.19.0)`）的源码，**逐条对照后再写**。本次已确认可引用的锚点（新事实继续在此加）：

- `public/scripts/extensions/regex/engine.js:422` —— `replaceString` 同时支持 `$1` 与 `$<name>`；写错不报错，只留下字面量。
- `public/scripts/extensions/regex/engine.js:398` —— `substituteRegex` 三档（`0` 原样 / `1` 转义 / `2` 替换），选错会让整条正则行为不同。
- `public/scripts/extensions/regex/engine.js:350-354` —— `markdownOnly` / `promptOnly` 的组合决定命中哪个管线；两个都不设只在「既非 markdown 也非 prompt」时生效。
- `public/scripts/extensions/regex/engine.js:374` —— `placement` 是数组，缺一项就等于该管线不生效。
- `public/scripts/world-info.js:855` —— `world_info_position` 枚举；写入非枚举值不会报错，只是位置按默认处理。
- `public/scripts/world-info.js:5698`、`:5744` —— 卡内 `character_book` 会被转成书并命名为 `<卡名>'s Lorebook`；与独立世界书并存时会出现两本。
- `public/scripts/char-data.js:65` —— `character_book` 属于 v2 `data` 字段。

必写的 S 系列（≥20 条）：卡 v2 必填字段与 `spec`/`spec_version`、`extensions.world` 与文件名一致、世界书 `uid`/`key` 对齐、`constant`+`selective` 组合、`position`/`depth`/`order` 三者优先级、`probability`+`useProbability`、`excludeRecursion`、`matchWholeWords`/`caseSensitive: null`、正则 `placement` 与 `markdownOnly`、`$1` vs `$<name>`、`{{match}}` → `$0`、`first_mes` 占位标签与 `encode_tags`、MVU `stat_data` 路径与 `.catch()`、`[initvar]` 禁用、EJS 由 ST-Prompt-Template 提供、酒馆助手 `tavern_helper.scripts` 需手动启用、导入接口 `preserved_name` 与同名覆盖、PNG 卡 `chara` 块。

- [ ] **Step 4: 跑测试**

Run: `python -m unittest tests.test_fact_table -v`
Expected: 5 项 PASS。

- [ ] **Step 5: 在 `pipeline.md`「开工前」加一行**

`涉及 ST 字段语义（正则 / 世界书 / 卡字段 / MVU / EJS）时先读 `references/st-correctness.md`；表里没有的字段不许凭印象写。`

- [ ] **Step 6: 提交**

```bash
git add references/st-correctness.md tests/test_fact_table.py references/pipeline.md
git commit -m "feat(ST): 语义事实表——每条事实可溯源到 1.19.0 源码"
```

---

### Task 3: S 系列语义校验器 + 正反 fixtures

**Files:**
- Create: `scripts/validate_st_semantics.py`
- Create: `tests/fixtures/semantics/good/`（一张卡 + 一本世界书 + 一份正则）
- Create: `tests/fixtures/semantics/bad/`（每个 S 编号一份只坏一处的变体）
- Create: `tests/test_st_semantics.py`
- Modify: `scripts/check-stage.py`（`delivery` 分支追加该校验器）

**Interfaces:**
- Consumes: Task 2 的 S 编号。
- Produces: `validate_st_semantics.validate(pkg_dir: Path, contract: Path | None) -> Result`，`Result.failures: list[tuple[str, str]]`（`(S 编号, 说明)`）、`Result.exit_code: int`；CLI `python scripts/validate_st_semantics.py <最终产物目录> [--contract 创作痕迹/contract.yaml]`。

- [ ] **Step 1: 写失败测试（只覆盖 3 条代表，其余同类补）**

```python
# tests/test_st_semantics.py
import unittest, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
def run(pkg):
    return subprocess.run([sys.executable, "scripts/validate_st_semantics.py", str(pkg)],
                          cwd=ROOT, capture_output=True, text=True)

class TestStSemantics(unittest.TestCase):
    def test_good_package_passes(self):
        r = run(ROOT / "tests/fixtures/semantics/good")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
    def test_world_filename_mismatch_fails(self):
        r = run(ROOT / "tests/fixtures/semantics/bad/world-mismatch")
        self.assertEqual(r.returncode, 1)
        self.assertIn("S", r.stdout)
    def test_named_group_without_group_fails(self):
        r = run(ROOT / "tests/fixtures/semantics/bad/regex-named-group")
        self.assertEqual(r.returncode, 1)
    def test_markdown_only_and_prompt_only_both_false_fails(self):
        r = run(ROOT / "tests/fixtures/semantics/bad/regex-no-pipeline")
        self.assertEqual(r.returncode, 1)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_st_semantics -v`
Expected: FAIL —— 脚本不存在。

- [ ] **Step 3: 先建 `good/` fixture 并让它过**

`good/` 用 `templates/st-card.json` + `templates/st-worldbook.json` + `templates/regex-frontend.json` 填一份最小可用包（1 角色 + 3 条目）。这一步必须先 0 退出，否则夹具本身是错的。

- [ ] **Step 4: 逐条实现 S 检查，每实现一条就加一个 `bad/` 变体**

每个 `bad/<name>/` 只坏一处，且文件名映射到 S 编号（写在脚本顶部的 `CHECKS` 字典里）。**不重复** `validate-st-package.py` 已查的 C 系列与 X 系列；此处只查「语义会静默失效」的那些（`st-correctness.md` 的 `校验` 列）。

- [ ] **Step 5: 接入 `check-stage.py`**

`delivery` 分支顺序：`validate-contract.py` → `validate-st-package.py` → `validate_st_semantics.py`。任一非 0 即该阶段不过。

- [ ] **Step 6: 跑测试**

Run: `python -m unittest tests.test_st_semantics -v && python scripts/check-stage.py delivery tests/fixtures/semantics/good`
Expected: 全 PASS；`check-stage delivery` 退出码 0。

- [ ] **Step 7: 提交**

```bash
git add scripts/validate_st_semantics.py scripts/check-stage.py tests/
git commit -m "feat(ST): S 系列语义校验器——覆盖静默失效而非格式"
```

---

### Task 4: 决定层（四态 / 缺口分级 / 未答≠委托）

**Files:**
- Create: `references/decisions.md`
- Create: `tests/test_decisions.py`
- Modify: `references/interview-protocol.md`（首节加 3 行指针）
- Modify: `references/contract-schema.md`（`decisions` 增 `state` 键）
- Modify: `SKILL.md`（仅「六、硬门」外补 1 行，指向 `decisions.md`）

**Interfaces:**
- Produces: 四态枚举 `confirmed` / `proposed` / `pending` / `rejected`；缺口分级表 4 行（低风险可逆 / 影响方案 / 冲突 / 不可逆成本）；`contract.decisions[].state` 取值受 `validate-contract.py` 约束。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_decisions.py
import pathlib, re, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
D = (ROOT / "references/decisions.md").read_text(encoding="utf-8")

class TestDecisions(unittest.TestCase):
    def test_four_states_defined(self):
        for s in ("confirmed", "proposed", "pending", "rejected"):
            self.assertIn(s, D)
    def test_silence_is_not_delegation(self):
        self.assertIn("未答", D); self.assertIn("不是委托", D)
    def test_interview_protocol_links(self):
        p = (ROOT / "references/interview-protocol.md").read_text(encoding="utf-8")
        self.assertIn("references/decisions.md", p)
    def test_contract_schema_has_state(self):
        c = (ROOT / "references/contract-schema.md").read_text(encoding="utf-8")
        self.assertIn("state", c)
    def test_pipeline_gate_mentions_it(self):
        p = (ROOT / "references/pipeline.md").read_text(encoding="utf-8")
        self.assertIn("decisions.md", p)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_decisions -v`
Expected: FAIL —— `FileNotFoundError`。

- [ ] **Step 3: 写 `references/decisions.md`（≤120 行）**

四节：① 四态与写回字段；② 缺口分级表（沿用 TavernWeave 的**判据**，用自己的口径重写，不搬原文）；③ 「未答 ≠ 委托」硬规则 + 三句固定话术（沉默 / 「你定」/ 「随便」）；④ 停止条件（预算、批次、权限、需用户决定）。明确：`proposed` 必须在产物里落 `【AI补全·可替换】`，`pending` 必须进 `contract.pending[]`。

- [ ] **Step 4: 接入三处**

`interview-protocol.md` 首节 3 行指针；`contract-schema.md` 的 `decisions[]` 加 `state`（四态之一，默认 `confirmed`）；`pipeline.md` 的 `自检门` 段加一行「产物里所有 `【AI补全·可替换】` 必须能在 `decisions[].state == proposed` 里找到对应项」。

- [ ] **Step 5: 让 `validate-contract.py` 校验 `state` 枚举**

在现有契约检查里加一项 `C2x`：`decisions[].state` ∉ 四态 → FAIL。测试用一个坏契约 fixture 断言退出码 1（放在 `tests/fixtures/contract/bad-state.yaml`）。

- [ ] **Step 6: 跑测试**

Run: `python -m unittest tests.test_decisions -v`
Expected: 5 项 PASS。

- [ ] **Step 7: 提交**

```bash
git add references/decisions.md references/interview-protocol.md references/contract-schema.md references/pipeline.md scripts/validate-contract.py tests/
git commit -m "feat(决定): 四态与缺口分级——未答不是委托"
```

---

### Task 5: 文风校验器（去 AI 味 / 去解释腔）

**Files:**
- Create: `scripts/check_prose.py`
- Create: `tests/fixtures/prose/dirty.md`、`tests/fixtures/prose/clean.md`
- Create: `tests/test_check_prose.py`
- Modify: `references/pipeline.md`（`自检门` 四类里加第五类「文风」，1 行 + 命令）
- Modify: `references/stage-2-rolecard.md`、`references/stage-3-scene-sheet.md`（`## 生成` 首句加一行「写前跑 `check_prose.py` 自查」）

**Interfaces:**
- Produces: 规则 ID `P01`–`P08`；`check_prose.scan(text: str) -> list[tuple[str, int, str]]`（`(规则ID, 行号, 命中片段)`）；CLI `python scripts/check_prose.py <path...> [--max P02=3] [--json]`，默认任一条硬规则 >0 或 `P02` 密度 >3/千字即退出码 1。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_check_prose.py
import importlib.util, pathlib, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cp", ROOT / "scripts/check_prose.py")
cp = importlib.util.module_from_spec(spec); spec.loader.exec_module(cp)

class TestCheckProse(unittest.TestCase):
    def test_dirty_hits_explanation_dash(self):
        t = (ROOT / "tests/fixtures/prose/dirty.md").read_text(encoding="utf-8")
        ids = [h[0] for h in cp.scan(t)]
        self.assertIn("P02", ids)          # 「——」解释腔
        self.assertIn("P03", ids)          # 「值得注意的是」类
    def test_clean_is_clean(self):
        t = (ROOT / "tests/fixtures/prose/clean.md").read_text(encoding="utf-8")
        self.assertEqual(cp.scan(t), [])
    def test_cli_exit_codes(self):
        import subprocess, sys
        ok = subprocess.run([sys.executable, "scripts/check_prose.py",
                             "tests/fixtures/prose/clean.md"], cwd=ROOT, capture_output=True)
        bad = subprocess.run([sys.executable, "scripts/check_prose.py",
                              "tests/fixtures/prose/dirty.md"], cwd=ROOT, capture_output=True)
        self.assertEqual(ok.returncode, 0); self.assertEqual(bad.returncode, 1)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_check_prose -v`
Expected: FAIL —— 脚本不存在。

- [ ] **Step 3: 建 fixtures**

`dirty.md` 从复盘里那批「——解释腔」与八股句各摘 5 句（改写避开真实作品名）；`clean.md` 是同样内容的人工版本。**这条 fixture 是本任务的核心证据**：它必须让 `P02` 命中数量接近复盘记录的 160 处量级比例。

- [ ] **Step 4: 实现 8 条规则**

`P01` 「不是……而是……」；`P02` `——` 后接解释性从句；`P03` 「值得注意的是/需要指出的是/某种意义上/可以说」；`P04` 「不仅……而且」堆叠；`P05` 「让我们/接下来我们」；`P06` 空修辞（「仿佛在诉说着」「空气中弥漫着」）；`P07` 三段排比模板；`P08` 「总之/综上/总而言之」。正则一律加单元测试覆盖的样例。

- [ ] **Step 5: 接入 pipeline 与两个 stage 文件**

`pipeline.md` 的 `自检门` 加：`文风：产物正文跑 python scripts/check_prose.py <file>，退出码 0 才算过`。两个 stage 的 `## 生成` 首句加同一条（写前自查，不是写后）。**不新建 `prose.md`**——8 条规则住在脚本里，文档只留一条指针。

- [ ] **Step 6: 跑测试 + 跑预算**

Run: `python -m unittest tests.test_check_prose -v && python scripts/measure_load.py`
Expected: 3 项 PASS；加载量增量 ≤ +50 tok（只有一行指针）。

- [ ] **Step 7: 提交**

```bash
git add scripts/check_prose.py tests/ references/pipeline.md references/stage-2-rolecard.md references/stage-3-scene-sheet.md
git commit -m "feat(文风): 8 条去AI味规则落成校验器"
```

---

### Task 6: 证据分级与收尾汇报模板

**Files:**
- Create: `references/acceptance.md`
- Create: `tests/test_acceptance.py`
- Modify: `references/stage-7-delivery.md`（交付门一节引用，加 6 行汇报模板）
- Modify: `SKILL.md`（收尾第 5 条：一句话指向 `acceptance.md`）

**Interfaces:**
- Produces: 6 层枚举 `source` / `auto` / `offline` / `browser` / `real_st` / `human`；每层「谁签」「证据长什么样」「不得替代谁」。收尾汇报固定 6 行。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_acceptance.py
import pathlib, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
A = (ROOT / "references/acceptance.md").read_text(encoding="utf-8")

class TestAcceptance(unittest.TestCase):
    def test_six_layers(self):
        for k in ("source", "auto", "offline", "browser", "real_st", "human"):
            self.assertIn(k, A)
    def test_no_self_sign(self):
        self.assertIn("不得自签", A)          # 脚本/自动化不能写「人已验收」
    def test_delivery_stage_links_it(self):
        s = (ROOT / "references/stage-7-delivery.md").read_text(encoding="utf-8")
        self.assertIn("references/acceptance.md", s)
    def test_skill_md_points_once(self):
        s = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(s.count("references/acceptance.md"), 1)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_acceptance -v`
Expected: FAIL —— 文件不存在。

- [ ] **Step 3: 写 `references/acceptance.md`（≤80 行）**

一张 6 行表 + 三条硬规则：① 脚本输出只能证明 `auto`/`offline`；② `real_st` 必须贴 `st-import.py` / `st-probe.js` 的实际输出（PASS/WARN 原样，不改写）；③ `human` 只能由用户说，模型不得代填；④ 汇报缺层 = 未交付完，必须点名缺哪层。

- [ ] **Step 4: 接入 stage-7 与 SKILL.md**

`stage-7-delivery.md` 交付门末尾加 6 行汇报模板；`SKILL.md` 收尾第 5 条加一句「汇报按 `references/acceptance.md` 分六层，缺层要点名」。

- [ ] **Step 5: 跑测试 + 预算**

Run: `python -m unittest tests.test_acceptance -v && python scripts/measure_load.py`
Expected: 4 项 PASS；`delivery` 阶段增量 ≤ +400 tok 且仍 ≤22,000。

- [ ] **Step 6: 提交**

```bash
git add references/acceptance.md references/stage-7-delivery.md SKILL.md tests/test_acceptance.py
git commit -m "feat(验收): 六层证据分级——自动化不得自签"
```

---

### Task 7: 试演门（演出质量，手工判定）

**Files:**
- Create: `references/rehearsal.md`
- Create: `tests/test_rehearsal.py`
- Modify: `references/stage-2-rolecard.md`（`## 退出` 加一行：用户同意时跑试演）
- Modify: `references/pipeline.md`（`自检门` 后加 1 行指针）

**Interfaces:**
- Produces: 4 类判据 + 一张「症状 → 改哪个字段」映射表（`behavior.rules` / `speech.rules` / `anti_ooc.never` / 轴 `thresholds`）；报告格式固定 4 行（轮次 / 症状 / 定位到的字段 / 改法）。**本任务不产脚本**——演出质量无法机械判定，全部标 `manual:`。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_rehearsal.py
import pathlib, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
R = (ROOT / "references/rehearsal.md").read_text(encoding="utf-8")

class TestRehearsal(unittest.TestCase):
    def test_four_symptoms(self):
        for k in ("代演玩家", "OOC", "口癖漂移", "数值闸门失效"):
            self.assertIn(k, R)
    def test_maps_to_fields_not_rewrite(self):
        for f in ("behavior.rules", "speech.rules", "anti_ooc.never", "thresholds"):
            self.assertIn(f, R)
    def test_is_manual_not_script(self):
        self.assertIn("manual:", R)
        self.assertFalse((ROOT / "scripts/check_rehearsal.py").exists())
    def test_optional_and_bounded(self):
        self.assertIn("≤5 轮", R)
    def test_stage2_exit_links_it(self):
        s = (ROOT / "references/stage-2-rolecard.md").read_text(encoding="utf-8")
        self.assertIn("references/rehearsal.md", s)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_rehearsal -v`
Expected: FAIL —— 文件不存在。

- [ ] **Step 3: 写 `references/rehearsal.md`（≤100 行）**

四节：① 触发条件（`cast` 已 `done` + **用户同意**；≤5 轮样例；用户不答就不做，不代跑）；② 四类判据，每类给「症状原句长什么样」而不是抽象定义；③ 症状 → 字段映射表（**禁止整卡重写**：代演玩家改 `behavior` 的边界条，口癖漂移改 `speech.rules`，越界改 `anti_ooc.never`，闸门失效改 `thresholds` 或 `behavior.rules` 的代价条）；④ 报告 4 行格式。

- [ ] **Step 4: 接入两处**

`stage-2-rolecard.md` 的 `## 退出` 加一行；`pipeline.md` 的 `自检门` 段后加一行指针（不新增门编号，避免与 Task 1 的十二门计数冲突——试演是 `cast` 的退出选项，不是全局门）。

- [ ] **Step 5: 跑测试 + 预算**

Run: `python -m unittest tests.test_rehearsal -v && python scripts/measure_load.py`
Expected: 5 项 PASS；`cast` 阶段增量 ≤ +700 tok 且仍 ≤22,000。

- [ ] **Step 6: 提交**

```bash
git add references/rehearsal.md references/stage-2-rolecard.md references/pipeline.md tests/test_rehearsal.py
git commit -m "feat(试演): 四类演出判据与纠偏映射，手工判定"
```

---

### Task 8: 结构测试与 replay fixture（把上面全部钉住）

**Files:**
- Create: `tests/test_structure.py`
- Create: `tests/fixtures/replay/cast-no-answer/`（契约 + 一份「用户沉默」记录）
- Create: `scripts/run_checks.sh`（一条命令跑全部）
- Modify: `.gitignore`（如需）

**Interfaces:**
- Consumes: Task 1–7 全部产物。
- Produces: `bash scripts/run_checks.sh` 一条命令跑 `unittest` + 全部校验器 + `measure_load`，任一失败退出码 1。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_structure.py
import pathlib, re, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]

class TestStructure(unittest.TestCase):
    def test_stage_files_have_six_sections(self):
        for f in ROOT.glob("references/stage-*.md"):
            t = f.read_text(encoding="utf-8")
            for sec in ("## 进入条件", "## 追问", "## 判断标准", "## 生成", "## 写回契约", "## 退出"):
                self.assertIn(sec, t, f"{f.name} 缺 {sec}")
    def test_gate_numbers_contiguous(self):
        p = (ROOT / "references/pipeline.md").read_text(encoding="utf-8")
        nums = sorted({int(n) for n in re.findall(r"\*\*`?(\d+)\.", p)})
        self.assertEqual(nums, list(range(len(nums))), f"门编号不连续：{nums}")
    def test_referenced_scripts_exist(self):
        text = "\n".join(f.read_text(encoding="utf-8") for f in [ROOT/"SKILL.md", *ROOT.glob("references/*.md")])
        for name in set(re.findall(r"scripts/([a-z_-]+\.(?:py|js))", text)):
            self.assertTrue((ROOT / "scripts" / name).exists(), f"文档提到不存在的脚本 {name}")
    def test_no_outer_paths(self):
        text = "\n".join(f.read_text(encoding="utf-8") for f in [ROOT/"SKILL.md", *ROOT.glob("references/*.md")])
        self.assertNotIn("../", text)

class TestReplay(unittest.TestCase):
    def test_silence_yields_proposed_not_confirmed(self):
        c = (ROOT / "tests/fixtures/replay/cast-no-answer/contract.yaml").read_text(encoding="utf-8")
        self.assertIn("state: proposed", c)
        self.assertNotIn("state: confirmed", c)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m unittest tests.test_structure -v`
Expected: FAIL（replay fixture 不存在 / 门编号不连续或脚本缺失）。

- [ ] **Step 3: 建 replay fixture**

复刻复盘里「阶段 3 四问未选 → 模型直接做完 9 张场景卡」那段：`contract.yaml` 里 `decisions[].state: proposed`、`pending[]` 有该阶段、产物带 `【AI补全·可替换】`。这是唯一一个行为型断言，其余都是结构断言。

- [ ] **Step 4: 写 `scripts/run_checks.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m unittest discover -s tests -v
python scripts/measure_load.py
python scripts/check-stage.py all examples/dry-run-盐湖守夜人 2>/dev/null || echo "（无完整项目时跳过）"
```

- [ ] **Step 5: 跑全套**

Run: `bash scripts/run_checks.sh`
Expected: 全部 unittest PASS；`measure_load` 退出码 0。

- [ ] **Step 6: 提交并更新 README 索引**

```bash
git add tests/ scripts/run_checks.sh
git commit -m "test: 结构断言 + replay fixture + 一键全检"
```

---

### Task 9（可选，需用户拍板）：世界书双入口

**Files:**
- Modify: `references/stage-7-delivery.md`、`scripts/validate-st-package.py`、`skills 无`
- 测试：`tests/test_dual_book.py`

**Interfaces:**
- Produces: `delivery` 新增可选参数 `--embed-book`，产出「卡内 `character_book` + 独立世界书」双份；默认行为不变（纯净卡）。

- [ ] **Step 1: 先问用户要不要**

这是唯一会改变默认交付形态的任务。不拍板就不做——复盘第二节 #7 的对照表里，参考包是双份，但本包禁止内嵌是有理由的（改一条设定不用重导整卡）。方案：默认纯净，`--embed-book` 时额外产一份 `<世界名>（内嵌书）.json` 放在 `最终产物/st/`，并在交付说明里写清两条导入路径的差别。

- [ ] **Step 2: 写失败测试 → 实现 → 跑 `check-stage.py delivery` → 提交**

（步骤同 Task 3 的 5 步节奏；实现前必须确认 `world-info.js:5698` 的 `character_book` 转换行为，并在 `st-correctness.md` 补一行出处。）

---

## 验收总纲

1. `bash scripts/run_checks.sh` 全绿。
2. `python scripts/measure_load.py` 任一阶段 ≤22,000 tok，`SKILL.md` ≤6,600。
3. 拿 `examples/dry-run-盐湖守夜人` 跑一遍 `check-stage.py all`，退出码 0；再故意改坏 `extensions.world`、把 `$1` 写成 `$<n>`，两次都必须被 `validate_st_semantics.py` 拦下。
4. 用复盘里的「——解释腔」样本跑 `check_prose.py`，命中数与原记录量级一致。
5. `references/st-correctness.md` 每一行都能点开出处；表里没有的字段，文档中不出现断言。
6. 拿一份真包做一次试演（`references/rehearsal.md`），四条报告能落到具体字段；且没有触发任何整卡重写。

## 体积账（预期）

| 项 | 增量 |
|---|---|
| `SKILL.md` | **−1,000**（硬门回收）＋ 2 行指针 |
| `pipeline.md` | +3 行指针（约 +80） |
| `stage-2` / `stage-3` | 各 +1 行（约 +40） |
| `stage-7` | +400 |
| 新增 L2 文件（`st-correctness` / `decisions` / `acceptance` / `rehearsal`） | 仅按需加载：`world` **0 增量**，`cast` +700（试演表） |
| 新增 L3 脚本 | 0 |
| **最坏阶段（delivery）** | **−560** |
| **cast 阶段** | **−260**（−1,000 硬门 + 700 试演 + 40 指针） |

即：功能变多，加载量反而比现在低。
