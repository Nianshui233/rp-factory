# RP 设定编译系统（rp-factory）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 4 份面向酒馆的 RP 提示词重组成一个自包含的编码 agent skill 包，用契约保证世界观 / 角色卡 / 场景卡 / 数值系统四类产物之间命名与硬设定不漂移。

**Architecture:** 单 skill 目录。`SKILL.md` 只做路由（判阶段 → 读契约 → 派发 → 回写），不含任何设定内容生成逻辑。四个阶段各是一个 `references/stage-N-*.md`，统一六节结构；公共纪律（占位符、追问协议、契约读写、双模态渲染）在 4 个 `references/` 文件里，阶段文件只引用不复述。

**Tech Stack:** Markdown + YAML。无代码、无依赖、无脚本。验证靠 `wc -l` / `grep` / dry-run 推演。

**Spec:** `D:/AI/RP创作/参考/原始提示词/rp-factory/docs/specs/2026-11-20-rp-prompt-architect-design.md`

## Global Constraints

- **自包含**：`SKILL.md`、`references/**`、`templates/**` 中不得出现任何指向包外文件的路径，不得出现源文件名（`RP 世界观设计助手.md`、`AI-RP 角色架构师.md`、`AI-RP 系统架构师.md`、`RP场景生成器.md`、`非变量的HTML状态栏.md`）。源文件在验证通过后会被删除（spec §3.2）。
- **体量**：`SKILL.md` ≤ **300 行**（2026-11-20 用户拍板：九阶段 + 十一道门后前几轮上限都不够用，索性给足）；每个 `references/stage-*.md` ≤ 220 行；`references/pipeline.md` ≤ 150 行。
- **占位符只有 7 个**，定义在 `references/pipeline.md`，别处只引用不自造：`【未知】`、`【AI补全·可替换】`、`[待定]`、`[待定：<内容>]`、`[推断：<内容>](待确认)`、`[不适用]`、`[用户跳过]`。
- **产物 type 只有 4 个**：`world-bible`、`rolecard`、`scene-sheet`、`axis-system`。
- **门名只有 5 个**：`开工门`、`边界门`、`收敛门`、`自检门`、`命名门`。
- **阶段文件六节固定**：`## 进入条件` / `## 追问` / `## 判断标准` / `## 生成` / `## 写回契约` / `## 退出`，顺序不可变。
- **保真**：规则不可丢，只许合并同类 bullet 与把例子外移到 `templates/`；不许把"必须"降级为"建议"，不许删例外分支与否定式约束。
- **本期不出**：HTML / 正则 / 状态栏 / MVU / EJS。
- **产物一律 YAML**：四类产物模板与输出全为 `.yaml`，无 Markdown 产物。唯一例外是构建期说明 `examples/**/README.md`。

## Review Focus

1. 用户一开口就点名「我只要一张场景卡」，且没有任何世界观 → 应触发一次 ≤3 问的补采访问，而不是整张卡铺满 `[待定]`。
2. 用户中途改口（「教团改名成月蚀教」）→ `命名门` 必须发现旧名还在别的产物里，停下来问，不许静默只改一处。
3. 用户说「你来定」→ 产物里必须出现 `【AI补全·可替换】`，且末尾附补全清单；不许把自主补全伪装成用户确认的 `hard_settings`。
4. 用户要「给我能粘贴的」→ 文本模态输出必须是纯模板本体：无前言、无解释、无 `#` 注释行、无被注释掉的可选结构。
5. 源文件删掉后 → 全包 `grep` 源文件名与 `../` 路径必须为空；否则 skill 变成断链的死文档。

---

### Task 1: 覆盖清单与版本库

**Files:**
- Create: `D:/AI/RP创作/参考/原始提示词/rp-factory/docs/coverage-checklist.md`

**Interfaces:**
- Produces: 一份逐条编号的核对清单，后续每个 stage 任务结束时要回来打勾；Task 11 用它做终审。

- [ ] **Step 1: 建版本库**

```bash
cd "D:/AI/RP创作/参考/原始提示词/rp-factory"
git init
git add -A && git commit -m "chore: 设计文档入版本库"
```

不设 `.gitignore`——`docs/` 也要进历史，因为源文件将被删除，文档是唯一回溯依据。

- [ ] **Step 2: 抽取编号条目**

读这四段并逐条抄出编号与小标题（不要抄正文）：
- `../../RP 世界观设计助手.md:11-256` → 原则 1–18 的标题
- `../../RP 世界观设计助手.md:257-385` → 工作流程四步
- `../../RP 世界观设计助手.md:386-511` → 写作风格 5 节 + 特殊场景 8 条
- `../../AI-RP 角色架构师.md:24-124` → 阶段 0–3
- `../../AI-RP 角色架构师.md:126-262` → 字段规范 1–6
- `../../AI-RP 角色架构师.md:457-490` → 自检 4 类
- `../../RP场景生成器.md:3-23` → 依赖 5 条 + 流程 4 步 + 约束 2 条
- `../../RP场景生成器.md:25-167` → 场景卡 10 节
- `../../AI-RP 系统架构师.md:3-52` → 原则 4 条 + 流程 4 阶段
- `../../AI-RP 系统架构师.md:53-206` → 核心字段 6 个 + 扩展字段 4 个

- [ ] **Step 3: 写成清单**

`docs/coverage-checklist.md` 结构：

```markdown
# 覆盖清单

> 构建期产物，不随 skill 发布。源文件删除后本文件一并删除。

| # | 源 | 条目 | 落到 | 状态 |
|---|---|---|---|---|
| W01 | 世界观 | 原则 1 以可操作为核心 | references/stage-1-world-bible.md | [ ] |
| W02 | 世界观 | 原则 2 对 AI 可读性优先 | ... | [ ] |
```

- [ ] **Step 4: 核验条数**

Run: `grep -c '^| [WRSA][0-9]' docs/coverage-checklist.md`
Expected: ≥ 70（18+4+13+4+6+4+5+4+2+10+4+4+10 ≈ 88 条，含拆分的子条）

- [ ] **Step 5: 提交**

```bash
git add -A && git commit -m "docs: 覆盖清单与版本库"
```

---

### Task 2: 公共脊 `references/pipeline.md`

**Files:**
- Create: `references/pipeline.md`

**Interfaces:**
- Consumes: Task 1 的自检 4 类条目。
- Produces: 7 个占位符、5 个门名、阶段表（0–4 及其产物 type）、输出纪律、`命名门` 的四步流程。后续所有文件引用这些名字，不得另造。

- [ ] **Step 1: 写阶段表**

```markdown
| 阶段 | 负责文件 | 产物 type | 进入条件 | 退出条件 |
|---|---|---|---|---|
| 0 开工判定 | SKILL.md | — | 用户给出任何 RP 相关请求 | 判定出目标阶段与是否够开工 |
| 1 世界观 | references/stage-1-world-bible.md | world-bible | 用户给出题材/概念/世界构想 | 收敛门通过 + 用户确认终稿 |
| 2 角色卡 | references/stage-2-rolecard.md | rolecard | 有 naming.world 或用户直接给角色设定 | 自检门通过 |
| 3 场景卡 | references/stage-3-scene-sheet.md | scene-sheet | 有 naming.world 或用户直接给地点构想 | 自检门通过 |
| 4 数值系统 | references/stage-4-axis-system.md | axis-system | 有 naming.world 或用户直接给可量化维度 | 自检门通过 |
```

- [ ] **Step 2: 写占位符表**

7 个占位符，每个给一行用途与一行"什么情况下不许用"。例如 `[待定]` 的禁用条件：能补采访问到的、能合理推断的，都不许打 `[待定]`。

- [ ] **Step 3: 写五道门**

- `开工门`：判"够不够开工"——能否定出目标阶段。不单独提问（题目并入下游首轮）。
- `边界门`：`content_boundaries.rating` / `hard_no` 必须在任何产物落笔前锁定；渠道是下游阶段的首轮提问，≤2 题。
- `收敛门`：仅 stage-1 用，继承世界观原文的收敛信号条件。
- `自检门`：每份产物交付前内部执行、不向用户展示，四类检查（逻辑一致性 / 覆盖度 / 内容边界层 / 格式）。
- `命名门`：每次渲染产物前执行，四步见 Step 5。

- [ ] **Step 4: 写输出纪律**

终稿只输出模板本体；移除全部 `#` 注释行与被注释掉的可选结构；不写前言、不写结语、不写"以下是……"；`【AI补全·可替换】` 与 `[待定]` 保留在正文里，补全清单另附在代码块之外。

- [ ] **Step 5: 写命名门四步**

1. 从 `contract.naming` 取出全部名字（world / factions / places / systems / axes）。
2. 对每份待交付产物做字符串扫描：出现某实体但名字不匹配、或出现同义异名（如「蚀月教团」vs「月蚀教」）→ 停下。
3. 发现冲突：列出冲突双方所在产物 + 契约原始值，问用户保留哪个（一问，带建议）。
4. 用户选定后：改契约 → 回写所有已引用该名字的产物 → 记入 `decisions`。

- [ ] **Step 6: 核验**

Run: `wc -l references/pipeline.md && grep -n 'RP 世界观设计助手\|RP场景生成器\|AI-RP \|非变量的HTML' references/pipeline.md`
Expected: ≤150 行；grep 无输出

- [ ] **Step 7: 提交**

```bash
git add -A && git commit -m "feat: 公共脊 pipeline（阶段/占位符/五道门/命名门）"
```

---

### Task 3: 追问协议 `references/interview-protocol.md`

**Files:**
- Create: `references/interview-protocol.md`

**Interfaces:**
- Produces: 问题块的五条固定行、预算表、补采访问规则、降级链。stage 文件的 `## 追问` 节只写"首轮上限 N、必问项是什么"，格式与降级链一律指向本文件。

- [ ] **Step 1: 写问题块格式**

```markdown
【问题 N】<一句话问题，具体到当前项目，不空问>
- A：<选 A 之后世界/角色会变成什么样>
- B：<选 B 之后会变成什么样>
- C：<选 C 之后会变成什么样>
- 我的建议：A
  为什么：<基于哪条已锁定设定或哪条判断标准>
  影响：选 A 则 <下游哪个产物会变>；选 B 则 <下游哪个产物会变>
```

硬规则：每题 2–3 个选项 + 允许"其他"；禁止开放式空问；"我的建议 / 为什么 / 影响"三行不可省——这是与原文的差异点，原文只要求 2–3 选项。

- [ ] **Step 2: 写预算表**

| 阶段 | 首轮上限 | 后续每轮上限 | 轮数上限 |
|---|---|---|---|
| 0 开工判定 | 0 问（并入下游首轮）| — | — |
| 1 世界观 | 5–7（其中 ≤2 是边界/形式题）| 8 | 无限，收敛即提议出终稿 |
| 2 角色卡 | 3 | 3 | 2 |
| 3 场景卡 | 10 | 8 | 无限 |
| 4 数值系统 | 4 | 4 | 2 |

- [ ] **Step 3: 写补采访问规则**

任一阶段发现上游契约项缺失、且该缺失破坏本阶段可判定性时：允许发起一次补采访问，≤3 问，计入本轮预算，只问影响可判定性的项。问不到才写 `[待定：<缺什么>]`。

给 3 个典型触发例子（场景卡缺 `naming.world`、角色卡缺 `naming.systems`、数值系统缺 `rp_form`）。

- [ ] **Step 4: 写降级链**

追问无果 → 构造 A/B 两组对比设定供二选一（两组只在用户未明确维度上对比，已明确维度保持一致）→ 用户说"你来定"则自主补全并标 `【AI补全·可替换】` → 仍无回应则通用假设 + 标注 + 一句假设说明。

- [ ] **Step 5: 核验**

Run: `wc -l references/interview-protocol.md && grep -c '我的建议' references/interview-protocol.md`
Expected: ≤120 行；grep ≥ 3

- [ ] **Step 6: 提交**

```bash
git add -A && git commit -m "feat: 追问协议（问+建议→答 / 预算表 / 补采访问 / 降级链）"
```

---

### Task 4: 契约 `references/contract-schema.md` + `templates/contract.yaml`

**Files:**
- Create: `references/contract-schema.md`, `templates/contract.yaml`

**Interfaces:**
- Produces: 契约的键区定义、独占写者表、冲突规则、`naming.axes` 的 `provisional` 语义。`templates/contract.yaml` 是可直接复制填空的骨架，键名必须与本文档逐字一致。

- [ ] **Step 1: 写 `templates/contract.yaml`**

按 spec §6 逐字落地，含 `project` / `stages` / `content_boundaries` / `naming` / `hard_settings` / `pending` / `decisions` / `artifacts` 八个键区。每个键带一行 `#` 注释说明取值范围。

- [ ] **Step 2: 写 `references/contract-schema.md` 的定位段**

一句话钉死：契约是**索引与命名权威**，不是产物全量中间态。世界观正文、`psychology`、`calculation` 等正文一律不进契约，存在 `artifacts[]` 指向的产物里。

- [ ] **Step 3: 写独占写者表**

| 键区 | 独占写者 |
|---|---|
| `project.*`、`content_boundaries.*` | 主 skill（边界门） |
| `naming.world` / `factions` / `places` / `systems` | stage-1 |
| `naming`（角色相关新增）| stage-2 |
| `naming.axes` | stage-4 接管；stage-2/3 可写 `provisional: true` |
| `hard_settings` | 各阶段追加，只有用户确认才 `locked` |

- [ ] **Step 4: 写冲突与 provisional 规则**

- 写已存在的键 = 冲突 → 停下问用户，不许静默覆盖。
- `provisional: true` 的轴名，stage-4 接管时逐条确认或改名；改名必须回写所有已引用它的产物并记入 `decisions`。
- `stages` 是每阶段状态映射（`none|partial|done|skipped`），不是标量；乱序合法。

- [ ] **Step 5: 核验键名一致**

Run: `grep -o '^[a-z_]*:' templates/contract.yaml | sort -u` 与 `grep -o '`[a-z_.]*`' references/contract-schema.md | sort -u` 比对，确认 8 个键区名两边逐字一致。

- [ ] **Step 6: 提交**

```bash
git add -A && git commit -m "feat: 契约 schema 与骨架"
```

---

### Task 5: 双模态 `references/dual-mode.md`

**Files:**
- Create: `references/dual-mode.md`

**Interfaces:**
- Produces: `mode` 的两个取值（`text` / `engineering`）、切换触发词、渲染规则、注释剥离规则。stage 文件的 `## 退出` 节引用它决定交付形态。

- [ ] **Step 1: 写两种模态的对照表**

按 spec §8 的四行（交付 / 实现 / 附加 / 切换）落地。默认 `mode: text`。

- [ ] **Step 2: 写切换规则**

用户说「给我能粘贴的」「存成文件」「放到项目里」时切换；切换不重跑阶段，只换渲染目标。切换时把新 mode 写回 `contract.project.mode`。

- [ ] **Step 3: 写渲染规则**

- 文本模态：输出且仅输出一个 ```yaml 代码块，内容 = `templates/<type>` 填完后的结果；不用 Markdown 表格、不用 `- **字段**：` 列表。代码块之外只允许两样东西——`【AI补全·可替换】` 补全清单、`[待定]` 待确认清单。
- 工程模态：写到 `contract.project.name` 命名的目录下，文件名 `world-bible.yaml` / `rolecard.yaml` / `scene-sheet.yaml` / `axis-system.yaml`。
- 两模态共用同一份草稿，改一处不会出现两个版本。

- [ ] **Step 4: 写注释剥离规则**

`templates/*.yaml` 保留原文的 `# 例：…` 注释（便于填）；渲染时移除全部 `#` 注释行与被注释掉的可选结构；`[不适用]` 的模块整段移除而不是留空。

- [ ] **Step 5: 核验**

Run: `wc -l references/dual-mode.md`
Expected: ≤ 90 行

- [ ] **Step 6: 提交**

```bash
git add -A && git commit -m "feat: 双模态渲染规则"
```

---

### Task 6: 主路由 `SKILL.md`

**Files:**
- Create: `SKILL.md`

**Interfaces:**
- Consumes: Task 2–5 的全部名字（7 占位符、5 门名、4 产物 type、5 个 references 文件名、4 个 stage 文件名）。
- Produces: 触发条件、路由表、加载指引、硬门。任何 stage 文件都由它按需加载。

- [ ] **Step 1: 写 frontmatter**

```yaml
---
name: rp-factory
description: 把一句话 RP 构想编译成世界观、角色卡、场景卡、数值系统四类设定产物，跨产物命名与硬设定保持一致；支持输出可粘贴进酒馆的提示词条目，也支持直接落成工程文件。用户说「帮我做个世界观」「设计一张角色卡」「生成场景卡」「做一套好感度系统」「我只有个概念」时使用。
---
```

- [ ] **Step 2: 写路由表**

| 用户说的 | 进入 | 加载 |
|---|---|---|
| 「帮我做个世界观 / 世界观设定 / 世界设定卡」 | 阶段 1 | `references/stage-1-world-bible.md` |
| 「设计一个角色 / 角色卡 / 人设」 | 阶段 2 | `references/stage-2-rolecard.md` |
| 「生成场景 / 地点卡 / 地图」 | 阶段 3 | `references/stage-3-scene-sheet.md` |
| 「好感度 / 堕落值 / 理智值 / 数值系统」 | 阶段 4 | `references/stage-4-axis-system.md` |
| 「做一张完整卡 / 一整套设定」 | 阶段 1 → 依次 | 全部 |
| 只有模糊概念 | 阶段 0 判定后进入 | 先 `references/interview-protocol.md` |

- [ ] **Step 3: 写主 skill 的三件事与不做的事**

做：判阶段、读写契约、派发纪律。
不做：不生成任何设定内容；不替用户拍板硬设定；不重复 stage 文件里的规则（要复述就说明是错的）。

- [ ] **Step 4: 写硬门清单**

1. 落笔前先锁 `content_boundaries`（边界门）。
2. 交付前先过 `命名门`（`references/pipeline.md` 四步）。
3. 缺失上游项先补采访问（≤3 问），问不到才 `[待定]`。
4. 源文件不存在、不引用任何包外路径。
5. 一次只加载当前阶段文件，不预加载其他阶段。

- [ ] **Step 5: 核验**

Run: `wc -l SKILL.md && grep -c 'references/' SKILL.md`
Expected: ≤120 行；grep ≥ 6（4 个 stage + pipeline + interview-protocol）

- [ ] **Step 6: 提交**

```bash
git add -A && git commit -m "feat: 主路由 SKILL.md"
```

---

### Task 7: 阶段 1 世界观

**Files:**
- Create: `references/stage-1-world-bible.md`, `templates/world-bible.yaml`

**Interfaces:**
- Consumes: `pipeline.md` 的占位符与门名、`interview-protocol.md` 的格式与降级链、`contract-schema.md` 的 stage-1 独占键区。
- Produces: 产物 type `world-bible`；`contract.naming.world` / `factions[]` / `places[]` / `systems[]`；`stages.1`。
- 六节结构：`进入条件` / `追问` / `判断标准` / `生成` / `写回契约` / `退出`。

- [ ] **Step 1: 读源并标注**

读 `../../RP 世界观设计助手.md:11-511`。按 §3.1 保真策略处理 18 条原则：能合并的合并（保留编号），例子外移到 `templates/world-bible.yaml` 注释。

- [ ] **Step 2: 写 `## 判断标准`**

承载 18 条原则 + 写作风格 5 节 + 特殊场景 8 条。每条一行规则句，句首保留原文编号（`原则 3：`）。禁止保留源文件名。

压缩尺度：合并后仍保留全部 18 个编号；例子（“例如……”“反例……”）一律移进 `templates/world-bible.yaml` 注释，本节只留规则句。本节行数 ≤ 90。

- [ ] **Step 3: 写 `## 追问`**

首轮 5–7 问（其中 ≤2 是边界/形式题）；必问项：题材与基调、时空范围、核心矛盾方向、超自然/科技系统有无；快车道：用户首次输入已覆盖 4 项中 3 项以上则跳过纯提问、直接出粗版并在其后附 ≤5 个补充问题。后续每轮 ≤8 问。

- [ ] **Step 4: 写 `## 进入条件` / `## 写回契约` / `## 退出`**

- 进入：用户给出题材/概念/世界构想即可；已有 `naming.world` 则直接进迭代。
- 写回：`naming.world`、`naming.factions[]`、`naming.places[]`、`naming.systems[]`、`stages.1`；`hard_settings` 只在用户确认时追加并标 `source: 用户确认`。
- 退出：收敛门通过 → 提议出终稿 → 用户明确确认后才输出完整终稿 YAML。

- [ ] **Step 5: 落地 `templates/world-bible.yaml`**

把 `../../RP 世界观设计助手.md:514-767` 的 YAML 模版原样搬过来，保留全部 `#` 注释与可选结构示例。九大块：元信息 / 类型与基调 / 时间地点与世界范围 / 核心矛盾 / 世界规则 / 势力与社会结构 / 常识清单 / 关键历史与时间线 / 变更边界。

- [ ] **Step 6: 核验**

Run: `wc -l references/stage-1-world-bible.md && grep -c '^原则 ' references/stage-1-world-bible.md && grep -n 'RP 世界观设计助手' references/stage-1-world-bible.md templates/world-bible.yaml`
Expected: ≤200 行；原则数 = 18；grep 无输出

- [ ] **Step 7: 回覆盖清单打勾**

把 `docs/coverage-checklist.md` 里 W 开头的行全部改成 `[x]`。

- [ ] **Step 8: 提交**

```bash
git add -A && git commit -m "feat: 阶段 1 世界观（18 原则 + 9 块模板）"
```

---

### Task 8: 阶段 2 角色卡

**Files:**
- Create: `references/stage-2-rolecard.md`, `templates/rolecard.yaml`, `examples/rolecard-minimal.yaml`

**Interfaces:**
- Consumes: 同 Task 7 的四个公共文件。
- Produces: 产物 type `rolecard`；`naming`（角色相关新增）；`stages.2`；`naming.axes` 的 `provisional: true` 临时项（如好感度）。

- [ ] **Step 1: 写 `## 进入条件` 与 `## 追问`**

- 进入：有 `naming.world`（读语言风格、禁忌、冲突类型）或用户直接给角色设定。
- 追问：阶段 0 评估三维度（世界观/题材、核心动机与恐惧、底线与价值排序）任一缺失即追问；缺失 1 项 → 单轮 1 问；缺失 2–3 项 → ≤2 轮 ×≤3 问。

- [ ] **Step 2: 写 `## 判断标准`**

承载字段规范 6 条（`behavior.rules` 三类句式 + 三个反例、`psychology.values` 排序推导、`taboos`/`anti_ooc` 逻辑一致、语言层三项互证、`background` 受控、语言使用规则）。反例（循环定义 / trigger 不可外部判定 / reason 无额外信息）保留在文件里——它们是判断标准，不是例子。

- [ ] **Step 3: 写 `## 生成` 与档位表**

四档：精简 40–60 行 / 标准 80–120 行（默认）/ 扩展 150–200 行 / 定制。指向 `templates/rolecard.yaml`。

- [ ] **Step 4: 落地 `templates/rolecard.yaml`**

搬 `../../AI-RP 角色架构师.md:263-456`，保留身份层 / 心理层 / 行为层 / 语言层 / `anti_ooc` / 扩展区（世界观、关系、成长弧）的分节注释。

- [ ] **Step 5: 落地 `examples/rolecard-minimal.yaml`**

搬 `../../AI-RP 角色架构师.md:491-EOF` 的参考示例原文。这是唯一 worked ground truth，`自检门` 拿它对标。

- [ ] **Step 6: 写 `## 写回契约` 与 `## 退出`**

写回：`naming`（角色相关）、`stages.2`。若用户在追问中确定了可量化维度（如「他在意好感度」），写 `naming.axes` 并标 `provisional: true`，注明由 stage-4 接管。
退出：自检门四类通过；`【AI补全·可替换】` 逐条列出。

- [ ] **Step 7: 核验**

Run: `wc -l references/stage-2-rolecard.md && grep -c '❌' references/stage-2-rolecard.md`
Expected: ≤200 行；grep = 3（三个反例）

- [ ] **Step 8: 回覆盖清单打勾 + 提交**

```bash
git add -A && git commit -m "feat: 阶段 2 角色卡（字段规范 + 四档 + 最小示例）"
```

---

### Task 9: 阶段 3 场景卡

**Files:**
- Create: `references/stage-3-scene-sheet.md`, `templates/scene-sheet.yaml`

**Interfaces:**
- Consumes: 同前；额外读 `contract.naming.places[]` / `factions[]` 保证与世界观对齐。
- Produces: 产物 type `scene-sheet`；`naming.places[]` 追加；`stages.3`；YAML 根键 = `<场景名称>`。

- [ ] **Step 1: 写 `## 进入条件`**

- 有 `naming.world` → 读硬规则、常识、科技/魔法上限、势力结构、禁忌边界，不得写出与之冲突的内容。
- 无 `naming.world` → 触发补采访问一次（≤3 问，只问影响场景可判定性的项），问不到才 `[待定]`。
- 场景细节深度按玩法决定：日常/对话导向 → 轻结构（关键区域 + 氛围 + NPC）；潜入/推理/战术/密室 → 强结构（出入口、拓扑、门禁、巡逻、线索分布、时间表）。

- [ ] **Step 2: 写 `## 追问`**

首轮 ≤10 问：场景类型、规模、玩法重心、危险度、是否需要地图级结构、内容限制。后续每轮 ≤8 问。

- [ ] **Step 3: 写 `## 判断标准`**

四条可判定性要求：任何影响行动选择的要素（距离/通路/权限/风险/代价/可观察性）必须可明确判断；允许"未列出的区域"按生成规则补全；不得一次性写死全部细节；场景规则与世界硬规则对齐。

- [ ] **Step 4: 把 Markdown 模版转写为 YAML**

读 `../../RP场景生成器.md:25-167`，输出 `templates/scene-sheet.yaml`。这是本计划唯一需要结构转写的地方（其余三份模板原文就是 YAML）。

转写规则：

1. 根键 = `<场景名称>:`（尖括号占位风格与世界观卡一致）。
2. 原 10 节 → 10 个二级键，名字固定：`概览` / `空间结构` / `关键区域` / `出入口与安防` / `生态` / `资源与可破坏物` / `线索` / `时间与事件` / `规则` / `边界`。
3. 原 `- **字段**：` → `字段: ""`；原缩进子弹列表 → 该键下的 list 或 object。
4. 原文括号提示（`（例：…）`）→ 移到该键后的 `#` 注释；结构位留空字符串。
5. `关键区域` 是列表：每项 `{名称, 功能, 现场可见, 可互动点, 风险与限制, 连接到}`，原 3 个编号区域保留前三项作示例，另加一行 `# 建议 5–12 个`。
6. **一个原字段都不能丢**。转完逐条对照原模版数一遍。

- [ ] **Step 5: 写 `## 写回契约` 与 `## 退出`**

写回：`naming.places[]` 追加本场景（`{id, name, scope}`）；若引入了新势力，走冲突规则问用户；`stages.3`。
退出：自检门；输出约束为"最终交付物必须是场景卡模板，除模版本体不附加任何内容"，且是一个 ```yaml 代码块。

- [ ] **Step 6: 核验**

```bash
wc -l references/stage-3-scene-sheet.md
grep -cE '^  (概览|空间结构|关键区域|出入口与安防|生态|资源与可破坏物|线索|时间与事件|规则|边界):' templates/scene-sheet.yaml
grep -n '\*\*' templates/scene-sheet.yaml
```
Expected: ≤200 行；十个二级键 = 10；最后一条无输出（YAML 里不应再有 `**加粗**`）

- [ ] **Step 7: 回覆盖清单打勾 + 提交**

```bash
git add -A && git commit -m "feat: 阶段 3 场景卡（Markdown 模板转写为 YAML）"
```

---

### Task 10: 阶段 4 数值系统

**Files:**
- Create: `references/stage-4-axis-system.md`, `templates/axis-system.yaml`

**Interfaces:**
- Consumes: `contract.naming.axes[]`（含 stage-2/3 留下的 `provisional: true` 项）。
- Produces: 独占接管 `naming.axes[]`（去掉 provisional 标记）；`stages.4`。产物 type `axis-system`。

- [ ] **Step 1: 写 `## 进入条件`**

可从阶段 1 直接进入（不需要角色卡在前）。有 `naming.axes` 的 provisional 项则逐条确认或改名；改名必须回写已引用它的产物并记入 `decisions`。

- [ ] **Step 2: 写 `## 追问`**

充分性评估三项全满足则直接生成：至少 1 个可量化维度名称、可推断数值范围与变化方向、可确定系统作用于谁。否则追问 ≤2 轮 ×≤4 问。

- [ ] **Step 3: 落地 `templates/axis-system.yaml`**

搬 `../../AI-RP 系统架构师.md:53-206`：核心字段 6 个（`meta` / `axes` / `thresholds` / `calculation` / `boundaries` / `runtime`）+ 扩展字段 4 个（`context_modifiers` / `decay` / `anti_exploit` / `interactions`），保留全部字段注释。

- [ ] **Step 4: 写 `## 判断标准`**

四条核心原则（闭环 / 可计算 / 可观察 / 显式标注）+ 下列硬规则：阈值 ≥3 级且无间隙无重叠；`ascending` 时 `calc_mod.negative` 必须为 0，`descending` 时 `calc_mod.positive` 必须为 0；至少 1 种反直觉事件；数值字段为纯数字，修正系数 `1.0` = 无修正；变量名全小写英文下划线。

- [ ] **Step 5: 写 `## 退出` 的两段交付**

1. 输出四件套：YAML 卡 / 设计说明 ≤5 句 / 补全清单 / 运行示例（≥1 正面 + 1 负面，展示完整计算过程）。
2. 末尾一段"落地路线"：说明本卡可落地到三条路线，本包只做路线 C（纯提示词）——A（MVU 变量框架）与 B（EJS 多阶段）需要本包之外的能力，属出界。不点名具体外部条目。

- [ ] **Step 6: 核验**

Run: `wc -l references/stage-4-axis-system.md && grep -c 'runtime:' templates/axis-system.yaml`
Expected: ≤200 行；grep = 1

- [ ] **Step 7: 回覆盖清单打勾 + 提交**

```bash
git add -A && git commit -m "feat: 阶段 4 数值系统（核心 6 字段 + 扩展 4 字段）"
```

---

### Task 11: 自包含扫描与 dry-run

**Files:**
- Create: `examples/dry-run-盐湖守夜人/` 下的 `contract.yaml`、`world-bible.yaml`、`rolecard.yaml`、`scene-sheet.yaml`、`axis-system.yaml`、`README.md`（README 是构建期说明，不算产物）

**Interfaces:**
- Consumes: 全部前序产物。
- Produces: 验证证据 + 收敛后的覆盖清单。

- [ ] **Step 1: 自包含扫描**

```bash
grep -rn 'RP 世界观设计助手\|RP场景生成器\|AI-RP 角色架构师\|AI-RP 系统架构师\|非变量的HTML状态栏' SKILL.md references templates examples
grep -rn '\.\./\.\./' SKILL.md references templates
grep -rn '待补充\|TBD\|适当\|酌情' SKILL.md references templates
```
Expected: 三条命令均无输出。

- [ ] **Step 2: 体量检查**

```bash
wc -l SKILL.md references/*.md
```
Expected: `SKILL.md` ≤300；各 `stage-*.md` ≤220；`pipeline.md` ≤150。

- [ ] **Step 3: dry-run 概念**

用一个虚构概念：「盐湖上的守夜人」。自演用户，从阶段 0 走到阶段 4，把每一步的产物按模态写到 `examples/dry-run-盐湖守夜人/`。角色卡与场景卡只需各一份，不必穷举。

- [ ] **Step 4: 逐条验证 Review Focus 五项**

- 直接说「我只要一张盐湖的守夜人哨塔场景卡」→ 检查是否触发 ≤3 问补采访问，而不是整张卡 `[待定]`。
- 把「守夜人」改名成「夜巡者」→ 检查命名门是否指出所有引用点并问用户。
- 说「你来定」→ 检查产物里 `【AI补全·可替换】` 是否出现且末尾有清单。
- 要求「给我能粘贴的」→ 检查输出无前言、无 `#` 注释、无被注释掉的可选结构。
- 检查 `examples/` 里四个产物对同一实体用同一个名字。

- [ ] **Step 5: 写 `examples/dry-run-盐湖守夜人/README.md`**

记录：哪些地方卡住了、哪条规则不足以产出、哪个文件需要补。

- [ ] **Step 6: 修掉 dry-run 暴露的问题**

按 README 的记录逐条改对应文件；改完重跑 Step 1、Step 2。

- [ ] **Step 7: 覆盖清单终审**

逐行核对 `docs/coverage-checklist.md`，确认无 `[ ]`。

- [ ] **Step 8: 提交**

```bash
git add -A && git commit -m "test: dry-run 盐湖守夜人 + 自包含扫描通过"
```

---

# 追加任务（2026-11-20）：表现层

依据：`docs/specs/2026-11-20-rp-prompt-architect-design.md` §14。只做动态版（酒馆助手 + ST 正则），拆成阶段 5 / 6 两个独立阶段。

## 追加 Global Constraints

- 正则必须 `markdownOnly: true`（仅格式显示），否则 `getChatMessages` 读到的是 HTML 而不是数据。
- 代码块必须含 `<body>`，否则酒馆助手不渲染成 iframe。
- HTML 单文件、无外链、无 `eval` / `document.write`、class 全带命名空间前缀。
- 标签三处一致、字段两处一致、数据路径自洽（`前端门` 八条，见 `references/frontend-conventions.md` 第六节）。
- 产物一律 YAML 的规则对表现层不适用：交 HTML / JSON / YAML 三份。

### Task 12: 表现层公约 + 两个阶段文件

- [x] **Step 1: 写 `references/frontend-conventions.md`**（机制事实表、数据流、HTML 骨架、正则 JSON、`frontend-prompt.yaml`、前端门七条）
- [x] **Step 2: 写 `references/stage-5-opening-ui.md`**（九字段、入口 `显示文本|实际发送`、`triggerSlash('/send …')`）
- [x] **Step 3: 写 `references/stage-6-statusbar-ui.md`**（字段表抄轴 `range`/`direction`、危险区、变化箭头、越界钳条）
- [x] **Step 4: 头部核验**：两份 stage 文件各六节，`grep -c '^## '` = 6

### Task 13: 骨架与接线

- [x] **Step 1: `templates/statusbar.html` / `templates/opening-ui.html` / `templates/regex-frontend.json` / `templates/frontend-prompt.yaml`**
- [x] **Step 2: 契约接线**：`stages: 1..6`、`naming.ui_tags`、`artifacts.type` 六类（`templates/contract.yaml` + `references/contract-schema.md`）
- [x] **Step 3: 公共脊**：`pipeline.md` 阶段表 5/6、六道门→七道门、输出纪律表现层例外
- [x] **Step 4: 路由与预算**：`SKILL.md` 路由两行、开局第二问六项、硬门第 7 条、文件索引；`interview-protocol.md` 预算表 5/6 行；`dual-mode.md` 第四节表现层例外
- [x] **Step 5: 核验**：`grep -n '六道门' -r .` 无输出；`grep -c '^## ' references/stage-5-opening-ui.md references/stage-6-statusbar-ui.md` 各 6

### Task 14: dry-run 阶段 6

- [x] **Step 1: `examples/dry-run-盐湖守夜人/最终产物/statusbar-ui.html`**（灯芯 0–100 `down` warn 34 / danger 15；潮压 0–100 `up` warn 60 / danger 82）
- [x] **Step 2: `regex-statusbar.json`**（`replaceString` 内嵌同一份 HTML，由脚本生成，避免手抄漂移）
- [x] **Step 3: `frontend-prompt.yaml`**（四字段 + `一致性` 段）
- [x] **Step 4: 三种误数据 + 一致性脚本**：缺字段 / 越界 140 / 脏值 `<b>x</b>` / 无标签留白；`TAG` 三处、`FIELDS` 两处逐项比对
- [x] **Step 5: 写回契约**：`stages.6: done`、`stages.5: skipped`、`ui_tags.status`、`H06`、三条 `decisions`、三条 `artifacts`
- [x] **Step 6: README 第五节 + 创作记录阶段 6**，记录三条暴露的问题
- [x] **Step 7: 提交**

```bash
git add -A && git commit -m "feat: 表现层——阶段 5 开局前端 / 阶段 6 状态栏前端（动态版）"
```

### Task 15: 开局前端双形态（照参考实现补强）

**Files:**
- Create: `templates/wizard-ui.html`
- Modify: `references/frontend-conventions.md`、`references/stage-5-opening-ui.md`、`references/stage-6-statusbar-ui.md`、`templates/statusbar.html`
- Test: `examples/dry-run-盐湖守夜人/最终产物/wizard-ui.html`（DOM 桩）

**Interfaces:**
- Consumes: 阶段 2 的字段分组、`axis-system.axes[].range/initial`、`contract.naming.ui_tags.opening`
- Produces: `artifacts[type=opening-ui]` 三条（HTML / 正则 JSON / 提示词 YAML）、`hard_settings` 的触发约定

- [x] **Step 1: `frontend-conventions.md` 第二节改成三条数据路径表**（A 静态 / B `$1` 注入 / C `getChatMessages`），加"发送三级降级"代码与确认框理由；硬要求补 `$1` textarea 的三条限制；第四节补两种 `findRegex` 写法与 `substituteRegex: 0`；第六节前端门 7 → 8 条
- [x] **Step 2: `templates/wizard-ui.html`**（`PROJECT`/`TITLE`/`SUBTITLE`/`OUTRO` + `STEPS`；`kind: lore|form|summary`；字段 `{k,label,type,options,custom,req,ph}`；进度条可跳、`localStorage` 键 `rpwz:<PROJECT>:data|:step`、`select __custom__` + `-custom` 输入、总览必填缺口提示、Markdown 导出、`clipboard` → `execCommand` 兜底、`esc()`；路径 A 默认不含捕获组占位符）
- [x] **Step 3: 阶段 5 整份重写**（A/B 双形态、进入条件、可问五类、判断标准、A 九字段与七段界面、B 三段式与必做四件事、触发二选一、写回契约、退出验项）
- [x] **Step 4: 阶段 6 认两种规模与两条数据路径**（细条 / 分页 HUD；正则 B 带捕获组、C 不带）；示例数值由 `0.42` 改 `42`，前端门改八条
- [x] **Step 5: `templates/statusbar.html` 与 dry-run 状态栏加 `$1` 通道**（`rawFromDollar1()` 优先、`getChatMessages` 兜底、有 `$1` 时不做箭头）
- [x] **Step 6: dry-run 补建卡向导**（`wizard-ui.html` 8 步 + `regex-opening.json` 路径 A 静态替换）；契约写回 `stages.5: done`、`ui_tags.opening = 建卡向导`、`H07`、三条 decisions、两条 artifacts；README 第六节 + 创作记录阶段 5 补跑
- [x] **Step 7: 核验**

```bash
node --check .tmp-js/x.js                       # 抽 <script> 后语法通过（模板与 dry-run 各一次）
node .tmp-js/check-wizard.js examples/dry-run-盐湖守夜人/最终产物/wizard-ui.html   # 13 项断言全 PASS
python -c "import yaml,glob;[yaml.safe_load(open(f,encoding='utf-8')) for f in glob.glob('templates/*.yaml')+glob.glob('examples/**/*.yaml',recursive=True)]"
grep -c '$1' templates/wizard-ui.html            # 期望 0（路径 A）
python -c "import json;d=json.load(open('examples/dry-run-盐湖守夜人/最终产物/regex-statusbar.json',encoding='utf-8'))[0];print('(' in d['findRegex'], '$1' in d['replaceString'])"   # 期望 True True（路径 B）
```

**Ruling**：`rolecard.yaml` 不含 `first_mes`，所以"开场白即向导"必须由用户在 ST 里手改一处——写进阶段 5 与 `H07`，不做角色卡 JSON 导出。

### Task 16: 收尾交付（阶段 7 · 酒馆包）

**Files**
- Create: `references/stage-7-delivery.md`、`templates/st-card.json`、`templates/st-worldbook.json`、`scripts/validate-st-package.py`
- Modify: `SKILL.md`（路由 / 开工第 5 步 / 硬门 8 / 文件索引 / 第十节）、`references/pipeline.md`（阶段表、八道门、交付门）、`references/contract-schema.md`（`stages: 1..7`、`delivery`）、`templates/contract.yaml`、`references/interview-protocol.md`、`references/dual-mode.md`
- Test: dry-run 两个 JSON + 校验器

- [x] **Step 1: 阶段表加第 7 行、门 7 → 8**（交付门；阶段 7 例外：只能最后进）
- [x] **Step 2: `stage-7-delivery.md` 六节**（收尾一问 / 世界书切法 / 卡片字段表 / 正则两条路 / 导入四步 / 交付门）
- [x] **Step 3: 两个 JSON 骨架**（`st-card.json` 全字段空值；`st-worldbook.json` 用 ST 的 `newWorldInfoEntryDefinition` 默认值）
- [x] **Step 4: 契约扩到 `stages: 1..7` + `delivery{route,st_name,files}`**
- [x] **Step 5: `validate-st-package.py`**（C01–C18 / W01–W09 / X01；node 实测正则；退出码 0/1/2）
- [x] **Step 6: dry-run 出包**（`最终产物/st/白潮.json`、`白潮 世界书.json`；10 条世界书；两条正则内嵌）
- [x] **Step 7: 核验**

```bash
python scripts/validate-st-package.py "examples/dry-run-盐湖守夜人/最终产物/st/白潮.json" "examples/dry-run-盐湖守夜人/最终产物/st/白潮 世界书.json"   # 12 项全过，exit 0
python -c "import json;d=json.load(open('templates/st-card.json',encoding='utf-8'));print(d['spec'],len(d['data']))"                                                     # chara_card_v2 14
python -c "import json;d=json.load(open('templates/st-worldbook.json',encoding='utf-8'));print(len(d['entries']['0']))"                                               # 41
grep -c "交付门" references/pipeline.md SKILL.md
```

**Ruling 1**：世界书名取"世界书文件名"而不是卡名——ST 导入世界书用文件名当书名，写成卡名会导致"导入成功但没挂上"，而这一步用户很难自己发现。
**Ruling 2**：不做内嵌 `character_book`。它和独立世界书只能二选一；选独立的那份，改设定时不会漏。
**Ruling 3**：正则两条路都给（卡内嵌 + 独立 JSON），并在交付说明里写清代价：内嵌要弹窗允许，全局导入会作用于所有角色。

### Task 17: 世界书调优（参数 + 校验）

**Files**
- Create: `references/worldbook-tuning.md`
- Modify: `references/stage-7-delivery.md`, `templates/st-worldbook.json`, `scripts/validate-st-package.py`, `SKILL.md`（文件索引）

**Step 1**: 写 tuning 十一节，每条规则都注明依据（官方文档 / 本机实现 / 参考包），不写"经验上最好"。
**Step 2**: stage-7 切法表补 `order`/`depth`/`excludeRecursion`，并加一句"参数一律看 tuning"。
**Step 3**: 模板默认值改成绿灯实体套餐。
**Step 4**: 校验器加 W10–W16（关键词 <8 / 未 excludeRecursion / 整词匹配 / position 2·3·5·6 / 关键词含逗号 / order 全同 / selective false）。
**Step 5**: 重生成 dry-run 世界书，跑

```
python scripts/validate-st-package.py "examples/dry-run-盐湖守夜人/最终产物/st/白潮.json" "examples/dry-run-盐湖守夜人/最终产物/st/白潮 世界书.json"
```

Expected: `0 失败，0 警告`，退出码 0。

**Ruling**：不新增第 8 个阶段——"调好世界书"不是新产物，是阶段 7 的参数质量；写成独立 reference 是因为它同时被 stage-7（生成）与交付门（校验）引用，塞进 stage-7 会让那份文件同时承担两件事。

### Task 17: 打包形态改成单文件（卡内嵌世界书）

**Files**: Modify `references/stage-7-delivery.md`（整份重写三层分法）、`templates/st-card.json`、`scripts/validate-st-package.py`、`examples/dry-run-盐湖守夜人/最终产物/st/白潮.json`；Create `templates/st-character-book-entry.json`。

**Step 1**: stage-7 改三层（`description` ≤8000 / `character_book` / `system_prompt`），切法表补"每个角色一条、每个地点一条、数值与判定一条"，两形状对照表。
**Step 2**: `st-card.json` 加 `character_book`；新增 v2 条目骨架模板。
**Step 3**: 校验器加 C19–C23、X01–X03，`--contract` 读轴名；预算 8000。
**Step 4**: dry-run 重生成（`description` 13,632 → 5,998；内嵌 12 条；单独世界书文件删除），README 第六节与创作记录同步。

```
python scripts/validate-st-package.py "examples/dry-run-盐湖守夜人/最终产物/st/白潮.json" --contract "examples/dry-run-盐湖守夜人/创作痕迹/contract.yaml"
```

Expected: `0 失败，0 警告`，17 项。

**Ruling**：默认只出单文件。独立世界书文件仅在用户明确要"能单独改 / 拿去别处"时生成，且在交付说明写明"导了卡别再导它，重名会覆盖"——两个文件同源是纪律，不是可选。

### Task 18: 流程门（阶段门 / 联网门 / NSFW / 自创字段）

**Files**: Modify `SKILL.md`、`references/pipeline.md`、`references/stage-2-rolecard.md`、`references/stage-4-axis-system.md`、`templates/rolecard.yaml`、`examples/rolecard-minimal.yaml`；Create `scripts/validate-rolecard.py`。

**Step 1**: `SKILL.md` 加硬门 9（阶段门）与 10（自创字段门），开工前第 6 条，NSFW 与联网两段改口径。
**Step 2**: `pipeline.md` 加阶段门、联网门加"必须有新增条目"。
**Step 3**: stage-2 加"先抄模板再填"、NSFW 块必写、退出跑校验器；stage-4 加多目标三选一。
**Step 4**: 新增 `validate-rolecard.py`，模板与示例的 `unknown_handling` 改运行时口径，示例 `never` 改中文以对齐 `taboos`。

```
python scripts/validate-rolecard.py examples/rolecard-minimal.yaml
```

Expected: 0 失败（WARN 可带着走），退出码 0。

### Task 19: 模板与契约收口

- [x] `templates/world-bible.yaml`：`核心矛盾` → `张力从哪来`（含 `张力形态` 与三类张力）；新增 `世界怎么运转`、`日常生活的质地`
- [x] `references/stage-1-world-bible.md`：四大要素第 ③ 改「张力形态」；新增「题材分支」表；原则 3/5/11 与极简版措辞同步
- [x] `templates/axis-system.yaml`：轴加 `targets` / `targets_initial`
- [x] 新建 `scripts/validate-contract.py`（C01–C12）
- [x] `references/contract-schema.md` 补第八节；`pipeline.md` 十道门 + 契约门；`SKILL.md` 阶段门加跑校验器
- [x] dry-run 补三个场景条目、删 `场景速查`、契约去掉 `st-worldbook`
- [x] 验证：`validate-contract.py` 0 失败；`validate-st-package.py` 0 失败 0 警告；全部 YAML/JSON 可解析

**Ruling**：`核心矛盾` 只改名不删字段——旧的 `矛盾各方` / `升级路径` 原样保留在块内，因为单一引擎题材（战争、生存、悬疑）确实需要它们；改名是为了让"多源日常"这种形态在模板里有位置，而不是为了否定旧形态。

### Task 20: 前端实体陷阱与界面校验器

- [x] `references/frontend-conventions.md`：新增「三之一 实体陷阱」（根因 + 两条规矩 + 自查）；骨架里的 `esc()` 改 `&` 写法；前端门 8 → 9 条
- [x] `templates/wizard-ui.html` / `statusbar.html` / `opening-ui.html`：`esc()` 改 `&` 拼接；`opening-ui` 的 `getChatMessages` 包 try/catch
- [x] 新建 `scripts/validate-frontend.py`（F01–F08）；`pipeline.md` / `stage-5` / `stage-6` / `SKILL.md` 退出项加"跑校验器"
- [x] dry-run 两个界面同步修掉实体；`validate-frontend.py templates examples` 0 失败 0 警告；`node --check` 五个文件全过
- [x] 真机验证：`爱情公寓.png` 重导入后，`http://127.0.0.1:8000` 里建卡向导从 2px 黑边变成正常 674px，序章 / 基础身份 / 外观 / 总览四步可点，填完能导出档案

**Ruling**：不做"在正则里把实体再转义一遍"的绕法——那要求每个界面各自记住一套转义规则，且 `$1` 注入路径会二次转义。统一在写法层面禁止实体，规则只有一条，校验器能拦。

### Task 21: 开局静默探测 + 收尾导入实测

- [x] 新建 `scripts/detect-sillytavern.py`：环境变量 / 家目录 / 各盘与 `AI/` 下一层 / `config.yaml` 端口 / 多端口 `/version` 指纹；输出 installation（路径、版本、用户目录、酒馆助手）与 running（url、版本、分支）；`--quiet` 一行摘要；找不到退出码仍 0
- [x] 新建 `scripts/st-import.py`：CSRF 握手 + multipart 导入（`preserved_name`）+ 回读五项自检 + `character_allowed_regex` 白名单检查 + 可选世界书；`--st auto` 复用探测
- [x] 新建 `scripts/st-probe.js`：puppeteer-core + 本机 Chrome，点开卡读 iframe 高度与内容，三条判定（正常 / 没 iframe / 2px），可选截图
- [x] `templates/contract.yaml` 与 `references/contract-schema.md` 加 `project.sillytavern`（含三种"探不到"的写法）
- [x] `SKILL.md`：开局四问前静默探测（不占预算）；第十节收尾加第二问（两种不问的情形）；文件索引加三个脚本
- [x] `references/stage-7-delivery.md`：追问改两问、新增「导入并实测」节（命令 / 判据 / 依赖 / 报告格式 / 失败不硬试）；`references/pipeline.md` 阶段 7 行与交付门同步
- [x] 真机验证：探测出 `D:/AI/SillyTavern` 1.19.0 + 运行中 8000 + 酒馆助手有；`st-import.py` 导入 dry-run 的 `白潮.json` 五项 PASS（另有一条白名单 WARN 属预期）；`st-probe.js` 对 `爱情公寓` 量到 674px、iframe 内有住户登记向导文字

**Ruling**：探测放在开局而不是阶段 5——阶段 5/6 要知道"有没有装酒馆助手"，阶段 7 要知道"有没有在跑的实例"，两次探测会有两次不确定；开局一次写进契约，后面只读。

### Task 22: 交付改三件套 + 最终产物空目录规则

- [x] `references/stage-7-delivery.md` 整份重写：三件各管一件事、卡必须纯净、世界书 native 形状、正则数组、装配四步、`最终产物` 空规则、校验器新口径
- [x] `templates/st-card.json` 去掉 `character_book`；`templates/regex-frontend.json` 改数组（两条骨架）；`templates/st-worldbook.json` 改 native 42 字段骨架；删 `templates/st-character-book-entry.json`
- [x] `scripts/validate-st-package.py` 重写为三件模式（P01 / C09–C11 / W01–W16 / R01–R06 / X01–X05），支持传目录自动认件
- [x] `scripts/validate-contract.py` 新增 C13（最终产物交付前空、交付后三件齐）、`st-regex` 类型、`STAGE_ARTIFACT[7]` 三选一
- [x] `scripts/st-import.py` 加 `--pkg` 三件逐件导入（卡 / 书 / 正则），正则走 settings 读写并备份
- [x] 路径总迁移：运行期产物一律 `创作痕迹/产物/`（`SKILL.md` / `pipeline.md` / `dual-mode.md` / `contract-schema.md` / `stage-1·3·5·6` / `interview-protocol.md` / `frontend-conventions.md`）
- [x] dry-run 重构：产物挪进 `创作痕迹/产物/`，`最终产物/` 只剩三件；契约 `route: st`、三条 artifacts
- [x] 验证：`validate-st-package.py examples/dry-run-盐湖守夜人/最终产物 --contract …` → 19 项 0 失败 0 警告；`validate-contract.py` → 14 项 0 失败

**Ruling**：`最终产物/` 严格空——不是"只放终稿"，是"交付前什么都没有"。理由：一旦允许半成品进去，"这是终稿还是草稿"就没人分得清，而 `创作痕迹/` 本来就是给过程用的，多一层目录比多一次判断便宜。
- [x] 追记：`st-import.py` 的正则改为"只校验不写设置"，`references/stage-7-delivery.md` 与 `frontend-conventions.md` 写明原因（运行中的客户端会盖掉 `settings.json`）


---

# 追加任务（2026-11-20）：变量系统（阶段 `mvu` / `ejs`）

依据：`docs/specs/2026-11-20-rp-prompt-architect-design.md` §24–§26（本轮补写）。取证来源：`D:/AI/RP创作/参考/` 下 `二十一人会`、`高塔：2080`、`呕吐内心的少女`、`尸变纪元`、`时雨不终-太阁立志`、`苏玉` 六个实例，以及 `SillyTavern预设结构参考/他人撰写的预设.json`。

## 追加 Global Constraints

- 结构脚本固定两行骨架：`import { registerMvuSchema } from 'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js';` 与 `$(() => { registerMvuSchema(Schema); });`。`z` 与 `_` 由酒馆助手自动注入，**不写 `import z`**。
- zod 里凡是数值一律 `z.coerce.number()`，不许 `z.number()`；上下界用 `z.coerce.number().transform(v => _.clamp(v, 0, 100))`，不许 `.min()/.max()`（后者会拒掉整条更新，前者只夹一次）。
- `[initvar]` 条目：`disable: true`、`position: 0`、`depth: 4`、`constant: false`。**不许加 `$meta`**（六个实例零使用）。
- `[mvu_update]` 三条（更新规则 / 输出格式 / 输出格式强调）与 `变量列表`：`constant: true`、`position: 4`、`depth: 0`、`order: 200`、`recursion.prevent_incoming: true`、`recursion.prevent_outgoing: true`。
- `变量列表` 内容必须逐字符等于 `---\n<status_current_variables>\n{{format_message_variable::stat_data}}\n</status_current_variables>\n`（98 字节），生成期用 `==` 比较。
- EJS 只允许三样：`<%_ _%>`、`if (typeof x === 'undefined') var x = getvar('stat_data.…', { defaults: … });`、`<%- await getwi(null, '条目名') %>`。被 `getwi` 加载的条目一律 `disable: true`。
- 变量系统产物写 `创作痕迹/产物/<阶段>/`；`最终产物/` 交付前保持空（沿用 Task 22 的规则）。
- 数值只准从 `axis-system.yaml` 投影，不许在 `mvu` 阶段重新发明一条轴。

## Review Focus（变量系统）

1. `axes` 改了范围而 zod 没跟着改 → 模型写 120 被夹成 100，界面显示"从没到过 100"，人以为是卡坏了。钉在 Task 23 的 M04（schema 边界 == 轴 `range`）与 Step 9 的越界用例。
2. `[initvar]` 忘了关 → 初值条目被当常驻设定塞进上下文，每轮多烧 1.5k 字。钉在 Task 23 的 M03。
3. `变量列表` 被写成 `get_message_variable`（裸 JSON）→ 模型看不到描述，改值全靠猜。钉在 Task 23 的 M07。
4. EJS 分支边界留缝（`< 30` 与 `> 30`）→ 恰好 30 时没有任何人设，模型自由发挥。钉在 Task 24 的 E06。
5. 被控条目没关 → 三个阶段人设同时进上下文，人格自相矛盾。钉在 Task 24 的 E05。

### Task 23: 阶段 `mvu`（变量系统）

**Files:**
- Create: `references/stage-mvu.md`、`templates/mvu-schema.js`、`templates/mvu-initvar.yaml`、`templates/mvu-entries.yaml`、`templates/tavern-script.json`、`scripts/validate-mvu.py`
- Test: `examples/dry-run-盐湖守夜人/创作痕迹/产物/mvu/`（三个文件）

**Interfaces:**
- Consumes: `axis-system.yaml` 的 `axes[]`（`name` / `range` / `initial` / `direction` / `thresholds` / `targets` / `targets_initial`）、`rolecard` 的 `identity`、`contract.naming.axes`
- Produces: `变量结构.js`（zod，导出脚本用 `templates/tavern-script.json` 包一层）、`[initvar]变量初始化.yaml`、`变量规则.yaml`（三条 `[mvu_update]` 条目 + `变量列表` 固定内容）；`artifacts[type=mvu-schema]`、`artifacts[type=mvu-initvar]`、`artifacts[type=mvu-entries]`

- [ ] **Step 1: 写 `references/stage-mvu.md` 六节**

`## 进入条件` / `## 追问` / `## 判断标准` / `## 生成` / `## 写回契约` / `## 退出`，标题必须裸写（`grep -c '^## '` = 6）。判断标准里写清"什么时候不该做 MVU"：轴 < 2 条、单人线性叙事、不做状态栏也不做分档人设——三条全中就直接 `skipped`。

- [ ] **Step 2: 追问表（首轮 5 问，不占阶段预算的只有开局三问）**

| 问题 | 选项（A/B/C + 我的建议） | 落进 |
|---|---|---|
| 轴要不要换成"每角色一份" | A 全局一份（≤2 人）/ B 每人一份（3–15 人）/ C 分 2–4 组 | `targets` |
| 时间推进要不要可写 | A 只读展示 / B 可写（日期/时段/天气三件） | `世界` 块 |
| 要不要物品栏 | A 不要 / B 固定键 / C 动态键（`z.record`） | `背包` 块 |
| 数值变动频率 | A 每轮微调 ±(1~3) / B 每场结算 ±(3~6) / C 只在关键事件 | `check` 里写死 |
| 要不要"输出格式强调"条目 | A 不建（默认）/ B 建但禁用 / C 建并启用 | 产物第 5 件 |

- [ ] **Step 3: `templates/mvu-schema.js`**

骨架只留四段：两行 import 与注册、`const 轴 = { … }`（从 `axes[]` 逐条投影，`transform` 里 `_.clamp(0, range[1])`）、`const Schema = z.object({ … })`（顶层键 = 世界 / 主角 / 各角色 / 背包）、末尾 `$(() => { registerMvuSchema(Schema); });`。文件头注释写"本文件由 `axis-system.yaml` 投影生成，改数值先改轴"。

- [ ] **Step 4: `templates/mvu-initvar.yaml`**

纯 YAML，值与轴 `initial` / `targets_initial` 逐项对齐；文件头注释写"必须作为 `[initvar]` 条目导入且 `disable: true`"。

- [ ] **Step 5: `templates/mvu-entries.yaml`**

三个条目的骨架，每条上方用注释钉死配置：`[mvu_update]变量更新规则`（`constant/depth 0/order 200/recursion 双向`）、`变量列表`（内容逐字符等于固定串）、`[mvu_update]变量输出格式`（含 `<UpdateVariable>` + `<Analysis>` + `<JSONPatch>`，`delta` op 要写进去）。文件名前缀 `[mvu_update]` 是 MVU 的识别条件，不许省。

- [ ] **Step 6: `templates/tavern-script.json`**

酒馆助手脚本导出格式：`{type: "script", enabled: true, name: "变量结构", id: "<uuid>", content: "<整个 js>", info: "", button: {...}, data: {}, export_with: {...}}`。

- [ ] **Step 7: `scripts/validate-mvu.py`**

参数 `--contract`（可选）。检查项：
M01 三个文件齐；M02 `变量结构.js` 含 `registerMvuSchema` 与 `$(() =>`；M03 `[initvar]` 的条目配置 `disable == True` 且无 `$meta`；M04 每条轴 `range` 与 zod 里 `_.clamp(…, <hi>)` 的 `<hi>` 一致（正则抽 `_.clamp(v, 0, N)`），轴名在 schema 里出现；M05 数值字段没有 `z.number()`（只查 `z.object` 之后、`transform` 之前，避免误报）；M06 `变量规则.yaml` 里三条条目配置正确；M07 `变量列表` 内容逐字符等于固定串（FAIL 级）；M08 输出格式含 `<UpdateVariable>`、`<JSONPatch>`、`delta`；M09 占位符 `【AI补全·可替换】` / `[待定` / `【未知】` 计数为 0；M10 `node --check`（拷到临时 `.mjs` 再跑）。退出码 0/1/2。

- [ ] **Step 8: dry-run 出三件**

`examples/dry-run-盐湖守夜人/创作痕迹/产物/mvu/` 下：`变量结构.js`（轴 `wick` 0–100 clamp、`tide` 0–100 clamp，顶层 `世界`/`主角`/`祁昭`）、`[initvar]变量初始化.yaml`（`wick: 62`、`tide: 18`，与 `axis-system.yaml` 的 `initial` 一致）、`变量规则.yaml`（三条目 + `变量列表`）。

- [ ] **Step 9: 越界用例与核验**

在同一目录加 `mvu-越界用例.md`：写 120 / -5 / 字符串 `"高"` 三个输入，期望都被 `transform` 夹成 `100` / `0` / 保持数字或缺省，不进"整条更新被拒"的分支。

```bash
python scripts/validate-mvu.py "examples/dry-run-盐湖守夜人/创作痕迹/产物/mvu" --contract "examples/dry-run-盐湖守夜人/创作痕迹/contract.yaml"
grep -c 'registerMvuSchema' examples/dry-run-盐湖守夜人/创作痕迹/产物/mvu/变量结构.js   # 期望 1
grep -c '\$meta' examples/dry-run-盐湖守夜人/创作痕迹/产物/mvu/*.yaml                  # 期望 0
```

Expected: `0 失败`，M01–M10 全过，退出码 0。

**Ruling 1**：结构用 zod 脚本、`[initvar]` 只放初始值——六个实例里 `[initvar]` 一个 `$meta` 都没有，结构全在 zod 脚本里；`$meta` 是"没有脚本时的退化路线"，不是标准做法。
**Ruling 2**：`mvu` 只做投影，不重新设计数值。轴的定义权在 `axes` 阶段，`mvu` 只负责把 `range` / `initial` / `thresholds` 翻译成可执行的 `clamp` 与 `check`。否则同一个数有两份真相。
**Ruling 3**：`变量结构.js` 交 `.js` 原文 + `tavern-script.json` 两个形状——前者能直接读能改，后者能一键导入；只给 JSON 的话人没法 review。

### Task 24: 阶段 `ejs`（分档控制器）

**Files:**
- Create: `references/stage-ejs.md`、`templates/ejs-controller.ejs`、`scripts/validate-ejs.py`
- Test: `examples/dry-run-盐湖守夜人/创作痕迹/产物/ejs/阶段控制器.ejs`

**Interfaces:**
- Consumes: `contract.naming.axes`、`axis-system.yaml` 的 `thresholds`、已被 `cast` / `scenes` 产出的分档内容条目名（改写对象）
- Produces: `阶段控制器.ejs`（世界书条目正文）+ `改写清单.yaml`（被控条目名、阶段边界、改写前后字数）；`artifacts[type=ejs-controller]`

- [ ] **Step 1: 写 `references/stage-ejs.md` 六节**

判断标准里写死能力边界（照抄预设那张做不到清单）：能做"按变量切条目 / 切关键词 / 切日期"；不能做 JSON 解析、复杂数组操作、网络、定时任务、`includes`/`endsWith`/`startsWith` 之外的字符串处理。越界就退回静态分档，并在 `decisions` 记一笔。

- [ ] **Step 2: 追问表（首轮 4 问）**

| 问题 | 选项 | 落进 |
|---|---|---|
| 控制器切什么 | A 人设/称谓 / B 场景可见细节 / C 两样都要（两个控制器） | 条目数 |
| 阶段边界 | A 用轴的 `thresholds` 原值 / B 自己定 3–5 档 | `阶段边界` |
| 无 MVU 时降级 | A 不做（推荐）/ B 用 `[InitialVariables]` + 模型输出 `setvar`（可靠性低一档） | `mode` |
| 被控条目怎么来 | A 从已有条目改写（默认）/ B 新写 | `改写清单` |

- [ ] **Step 3: `templates/ejs-controller.ejs`**

三段：读变量（`typeof` 守卫 + `var`）、`if/else` 分支（每个分支一行 `<%- await getwi(null, '条目名') %>`）、末尾不使用 `else` 兜底到最高档以外的情况（边界由 E06 保证不重合不遗漏）。文件头注释写"控制条目 `constant/after_char order 100/recursion 双向`，被控条目 `disable: true`"。

- [ ] **Step 4: 改写清单格式**

`创作痕迹/产物/ejs/改写清单.yaml`：`条目名` / `改动类型`（拆分·合并·改称谓·只加禁用）/ `改前字数` / `改后字数`。整份世界书改写前备份到 `创作痕迹/产物/改写前/`。

- [ ] **Step 5: `scripts/validate-ejs.py`**

参数 `--book`（世界书 JSON，用来查被控条目存在且 `disable: true`）。检查项：
E01 只用 `<%_ … _%>`（出现 `<% ` 或 `<%=` 即 FAIL）；E02 每个变量都有 `typeof … === 'undefined'` 守卫且声明为 `var`；E03 所有 `getvar(` 的路径以 `stat_data.` 开头（带 `--no-mvu` 时降为 WARN，且要求前缀是 `initial.` 或 `stat_data.`）；E04 每个 `getwi` 带 `await`，条目名能在 `--book` 里找到；E05 被控条目 `disable == true`（FAIL 级）；E06 数值边界连续性——抽取所有 `>=` / `>` / `<=` / `<` 的数字，按升序检查相邻区间"上界 + 1 == 下界"或"上界 == 下界"，有缝或重叠即 FAIL；E07 无 `JSON.parse` / `fetch` / `require` / `new Function` / `eval`；E08 占位符计数为 0。退出码 0/1/2。

- [ ] **Step 6: dry-run 出控制器**

以 `tide` 轴（0–100，`warn 60`、`danger 82`）做三档人设控制器，被控条目写成 `[阶段]祁昭·低潮` / `[阶段]祁昭·涨潮` / `[阶段]祁昭·漫堤`，三条 `disable: true` 追加进 dry-run 世界书。

- [ ] **Step 7: 边界用例**

在 `阶段控制器.ejs` 同目录加 `边界用例.md`：`tide = 59 / 60 / 81 / 82` 四处，逐个写"命中哪一档"，用来验证 E06 的区间无缝。

- [ ] **Step 8: 核验**

```bash
python scripts/validate-ejs.py "examples/dry-run-盐湖守夜人/创作痕迹/产物/ejs/阶段控制器.ejs" --book "examples/dry-run-盐湖守夜人/最终产物/白潮 世界书.json"
grep -c 'await getwi' examples/dry-run-盐湖守夜人/创作痕迹/产物/ejs/阶段控制器.ejs   # 期望 3
grep -c 'typeof' examples/dry-run-盐湖守夜人/创作痕迹/产物/ejs/阶段控制器.ejs        # 期望 >= 1
```

Expected: `0 失败`，E01–E08 全过，退出码 0。

**Ruling 1**：`ejs` 只做"控制器 + 被控条目"，不新写内容——分档内容本来就该在 `cast` / `scenes` 阶段产出，`ejs` 只负责把它变成"按变量生效"。这也就是"允许改写前序条目"的适用范围：只改称谓与拆分粒度，不改人设事实。
**Ruling 2**：允许"只 EJS 无 MVU"档，但必须在交付说明里写明可靠性低一档（模型得自己吐 `setvar`，漏一轮就断档），并记进 `decisions`。

### Task 25: 接线（阶段表 / 门 / 契约 / 路由 / 文档）

**Files:**
- Modify: `SKILL.md`、`references/pipeline.md`、`references/contract-schema.md`、`templates/contract.yaml`、`references/interview-protocol.md`、`references/frontend-conventions.md`、`references/stage-6-statusbar-ui.md`、`docs/coverage-checklist.md`、`docs/specs/2026-11-20-rp-prompt-architect-design.md`、`docs/plans/2026-11-20-rp-prompt-architect.md`、`README.md`、`examples/dry-run-盐湖守夜人/README.md`、`examples/dry-run-盐湖守夜人/创作痕迹/contract.yaml`、`examples/dry-run-盐湖守夜人/创作痕迹/创作记录.md`、`scripts/validate-contract.py`

- [ ] **Step 1: `stages` 从数字键改成名字键**

九个阶段：`world` / `cast` / `scenes` / `axes` / `mvu` / `ejs` / `opening` / `statusbar` / `delivery`。`templates/contract.yaml` 与 `contract-schema.md` 同步；`validate-contract.py` 同时接受旧的数字键（读到时给 WARN「`stages.1` 是旧写法，请改成 `world`」）。`project.stages_requested` 存名字数组。

- [ ] **Step 2: 阶段表与门**

`pipeline.md` 阶段表加 `mvu`（`axes` 之后）、`ejs`（`mvu` 之后、`opening` 之前）；十道门 → 十一道门，新增 `变量门`（跑两个校验器，占位符 0，被控条目全禁用）。`ejs` 可以单独跑（无 `mvu` 时走降级档），`mvu` 不行。

- [ ] **Step 3: `SKILL.md`**

路由行加两条；开局第二问从七项变九项；文件索引加 `stage-mvu.md` / `stage-ejs.md` / 两个校验器；硬门 11（变量门）；上限从 150 放宽到 **170**，并在 spec §26 写理由（阶段 7 → 9、硬门 10 → 11，压不回 150；把门挪去别的文件等于读两处才知道能不能开工）。

- [ ] **Step 4: 契约与预算**

`artifacts.type` 加 `mvu-schema` / `mvu-initvar` / `mvu-entries` / `ejs-controller`；`naming` 加 `schema_axes: []`（zod 里用到的轴名，供 X02 用）；`interview-protocol.md` 预算表加 `mvu`（5 问）/ `ejs`（4 问）两行。

- [ ] **Step 5: 状态栏与前端公约**

`frontend-conventions.md` 的三条数据路径表加第 4 条 **D：MVU 全局变量**（`waitGlobalInitialized('Mvu')` + `getAllVariables()` + `Mvu.events.VARIABLE_UPDATE_ENDED`，`findRegex: '<StatusPlaceHolderImpl/>'`，`maxDepth: 2`）；`stage-6` 的「数据源」一节改成「有 `mvu` 就走 D，没有就走 A/B/C」。

- [ ] **Step 6: 覆盖清单**

加「变量系统（阶段 `mvu`/`ejs`）」一节：M01–M12、E01–E10，每条对应一份源材料或一条实例证据。

- [ ] **Step 7: spec §24–§26**

§24 变量系统为什么是两个阶段（含三件取证结论：zod 而非 `$meta`、状态栏绑 MVU、控制器 + 被控条目）；§25 与表现层的边界（状态栏读哪份数据）；§26 阶段改名与文件上限调整的理由。

- [ ] **Step 8: dry-run 契约与记录**

契约写回 `stages.mvu: done`、`stages.ejs: done`、三条 `decisions`、四条 `artifacts`；`创作记录.md` 补两轮（问了几问、改写了哪几条、边界用例结果）；`examples/.../README.md` 与仓库 `README.md` 的目录树补 `创作痕迹/产物/{mvu,ejs}/`。

- [ ] **Step 9: 全量核验**

```bash
python scripts/validate-contract.py "examples/dry-run-盐湖守夜人/创作痕迹/contract.yaml"
python scripts/validate-st-package.py "examples/dry-run-盐湖守夜人/最终产物" --contract "examples/dry-run-盐湖守夜人/创作痕迹/contract.yaml"
python scripts/validate-mvu.py "examples/dry-run-盐湖守夜人/创作痕迹/产物/mvu" --contract "examples/dry-run-盐湖守夜人/创作痕迹/contract.yaml"
python scripts/validate-ejs.py "examples/dry-run-盐湖守夜人/创作痕迹/产物/ejs/阶段控制器.ejs" --book "examples/dry-run-盐湖守夜人/最终产物/白潮 世界书.json"
python scripts/validate-frontend.py templates examples
grep -c '^## ' references/stage-mvu.md references/stage-ejs.md          # 各 6
grep -rn 'RP 世界观设计助手\|RP场景生成器\|AI-RP 角色架构师\|非变量的HTML状态栏' .   # 期望 0
wc -l SKILL.md                                                           # <= 170
```

Expected: 四个校验器 `0 失败`，自包含 grep 零命中，退出码全 0。

- [ ] **Step 10: 提交**

```bash
git add -A && git commit -m "feat: 变量系统——阶段 mvu（zod 结构 + initvar + 三条目）与 ejs（控制器 + 被控条目）"
```

**Ruling 1**：`stages` 改名字键而不是继续加数字——九个阶段靠数字记住顺序不可能，而名字键让"`mvu` 在 `ejs` 前"这种约束写进枚举就能校验。
**Ruling 2**：门数从 10 涨到 11，但门本身不合并；合并等于降低某一道的检查强度，而每一道都对应一次真实的失败。

---

## 实验后修订（2026-11-20 · 《爱情公寓》实操验证）

一次真机实验（14 人格群像、两条轴、MVU + EJS 手搓、导入真实酒馆跑两轮生成）打出十处需要改的地方。实验记录在 `H:/RP创作/未命名项目/创作痕迹/产物/mvu-ejs-实验报告.md`，这里只记改动。

### 四条新 Ruling（用户已拍）

- **Ruling 4：常量预算不设上限。** `validate-st-package.py` 的「常驻条目 ≤ N 字」从判定项降为**只打印数字**（`INFO`，不进失败也不进警告）。理由：实测 MVU 三件套把常驻从 4.7k 顶到 8.7k，而那是"该写的都写了"的结果；卡字数换上下文是用户自己的取舍。
- **Ruling 5：`ejs` 默认不建。** 判据只有一条——**整段文本要随状态整体切换**（同一份内容放书里 N 份会 N 份全进上下文）。"报个档名"不算，书里的 `thresholds` 已经够用。不满足就 `skipped`，并在 `decisions` 写一句"轴表已够，不建控制器"。
- **Ruling 6：数值上限遇 OOC 放行且静默。** `caps`（单次 / 单场）只是给模型的建议，玩家显式命令改数值时照办：不夹、不告警、不记 `decisions`。理由：玩家手动调数值是常见诉求，事后追账没有收益。
- **Ruling 7：`<StatusPlaceHolderImpl/>` 默认藏。** 交付正则里默认带一条 `markdownOnly` 空替换；只有做了 `statusbar` 阶段的项目才撤掉这条。

### Task 23（`mvu`）增补

- **Step 3 骨架**：数值一律 `z.coerce.number().catch(初值).transform(v => _.clamp(v, 0, 上界)).prefault(初值)`。只写 `z.coerce.number()` 时，模型写一个 `"很高"` 会先产出 `NaN`，在 `transform` 之前就拒绝**整条**更新（实测复现）。
- **Step 3 骨架**：`世界` / `主角` 的字符串字段用 `z.string().catch(默认值)`，枚举用 `.catch(默认值)`，避免一个脏字段整条作废。
- **Step 5 之后新增 Step 5b：交付正则两件**（写进 `templates/regex-mvu.json`，随卡一起交）：
  - `[不发送]去除变量更新`：`findRegex: /<(update(?:variable)?)>(?:(?!.*<\/\1>)(?:(?!<\1>).)*$|(?:(?!<\1>).)*<\/\1?>)/gsi`，`replaceString: ""`，`placement: [1,2]`，`promptOnly: true`，`markdownOnly: false`
  - `[不显示]变量更新`：同上 `findRegex`，`promptOnly: false`，`markdownOnly: true`
  - 缺第一条：模型下一轮会看到自己上次的补丁；缺第二条：玩家看到 JSONPatch 原文。
- **Step 7 `validate-mvu.py` 增三项**：
  - `M11`：导出 native 世界书时 **`uid` 必须等于 `entries` 的键**（连续 `0..N-1`）。实测错位时 ST 面板按 uid 取条目取不到，条目**静默消失**且刷新不恢复（本次丢了 9 条）。
  - `M12`：`[initvar]` 的键集合必须与 zod `Schema` 的键集合一致；且 dry-run 示例里的值**必须与 `prefault` 不同**（本次两边都是 20，导致"initvar 到底读没读"白验一轮）。
  - `M13`：`templates/regex-mvu.json` 两条正则齐备，且 `findRegex` 能被 `node --eval "new RegExp(...)"` 编译。
- **Step 8 dry-run**：`[initvar]` 的 `wick` 写 `33`（轴 `initial` 是 62 也无所谓，关键是**与 zod `prefault` 不同**），让"读没读到"一眼可分。
- **Step 9 越界用例**补 `null` 与 `[]` 两行（`.catch` 要接得住）。

### Task 24（`ejs`）增补

- **Step 1 判断标准**加"不做"判据（见 Ruling 5）与 `skipped` 分支；`## 退出` 允许 "`skipped` + 一句理由"。
- **Step 3 模板**：分支链末尾**允许** `else` 兜底（不是必须写死 `<= 100`）；开头注释写清"被控条目必须 `disable: true`"。
- **Step 5 `validate-ejs.py` 三处修正**（都是本次实测的误报）：
  - `E02`：只数**首个 `<%_ … _%>` 块**里的 `var` 声明，循环里的局部变量不计。
  - `E06`：末尾是 `else` 兜底时不要求"最后一条上界盖到 100"；仍要求升序、不重合。
  - `E01`：判定前先把 `<%-` 归一成 `<%_`，否则 `<%- x %>` 会被误判成"无下划线标签"。

### Task 25（接线）增补

- **Step 2 门**：交付门加两条——`delivery.route == mvu` 时①卡必须内嵌 `extensions.tavern_helper.scripts`（至少 `MVU` + 变量结构两个），②交付说明里必须有"**在酒馆助手里给该角色启用脚本**"这一步。缺这一步，MVU 静默不跑且不报错（本次实测）。
- **Step 5 前端公约**：第四条数据路径 D（MVU 全局变量）旁边补一句——`Mvu.getMvuData()` 是**同步**返回，不要 `await`。
- **Step 6 覆盖清单**：M 组补 M11–M13、E 组补"不做判据"与三处校验器修正。

### 交付形态（Task 16 / 22）改口

MVU 路线是**四件 + 一个开关**，不再是三件套：

| 件 | 内容 |
|---|---|
| 卡 | 内嵌 `tavern_helper.scripts`（`MVU` 一行 import + 变量结构 js） |
| 世界书 | 独立 JSON，`uid` 与键连续对齐 |
| 正则 | 开局正则 + 两条隐藏更新块（+ `<StatusPlaceHolderImpl/>` 隐藏） |
| 开关 | 酒馆助手 → 该角色 → 启用脚本（一次性，非文件） |

`validate-st-package.py` 增 `P07`：`route == mvu` 时卡内必须有脚本、且交付说明含"启用脚本"字样；三件套路线（`route == text`）不查。

### 核验追加

```bash
python scripts/validate-mvu.py "examples/dry-run-盐湖守夜人/创作痕迹/产物/mvu" --contract "examples/dry-run-盐湖守夜人/创作痕迹/contract.yaml"
python -c "import json;d=json.load(open('examples/dry-run-盐湖守夜人/最终产物/白潮 世界书.json',encoding='utf-8'));assert all(str(v['uid'])==k for k,v in d['entries'].items()),'uid 与键不一致'"
grep -c 'StatusPlaceHolderImpl' templates/regex-mvu.json      # 期望 >= 1
grep -c 'promptOnly' templates/regex-mvu.json                 # 期望 >= 1
```

---

## 追加任务（2026-11-20）：校验节奏收敛成一个口

**起因**：用户问「关于检验，是不是一步一检？」——是。契约门写着"每次写完契约、以及每个阶段收尾"，前端门写着"改完跑一次"，`mvu`/`ejs` 各自在 Step 6 又跑一次，`delivery` 再跑两次。同一个动作在七个地方各有触发点，实操里会退化成"写一个文件跑一次"，既慢又没人真看输出。

**Task 26 · 一个阶段一次校验**
1. 新建 `scripts/check-stage.py <阶段> <项目根>`：按阶段分派——契约永远查，`cast` 加 `validate-rolecard.py`，`opening`/`statusbar` 加 `validate-frontend.py`，`mvu` 加 `validate-mvu.py`，`ejs` 加 `validate-ejs.py`，`delivery` 加 `validate-st-package.py`；`all` 全跑。参数从契约 `artifacts[]` 里取，取不到就按约定路径兜底。
2. `pipeline.md` 新增「校验的节奏：一个阶段一次」段；`契约门` 措辞由"每次写完契约"改为"阶段收尾一检时一并跑"；`自检门` 注明它是"读一遍自己的稿"，不算校验轮次。
3. 九个阶段文件的「退出」统一改成跑 `check-stage.py <阶段>`；`frontend-conventions.md` 自检第 10 条与 `contract-schema.md` 第八节同步。
4. `SKILL.md` 硬门 8/9/10 改成"由阶段收尾那一检跑"，文件索引加 `check-stage.py`。

**Ruling 8（节奏）**：**阶段完成后统一检验**，不是一步一检，也不是一切完成后才检。理由：脚本能查的错（契约漂移、`uid` 错位、占位符漏进正文）都会污染下游，等到最后才发现要回头重做三四个阶段；而在阶段内每写一个文件就跑，得到的是"这一行合不合法"，不是"这一阶段能不能交"。

**核验追加**

```bash
python scripts/check-stage.py all "examples/dry-run-盐湖守夜人"     # 期望：6 个检查全过
python scripts/check-stage.py cast "examples/dry-run-盐湖守夜人"    # 期望：2 个检查全过
```
