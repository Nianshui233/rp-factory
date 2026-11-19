# RP 设定编译系统（rp-factory）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 4 份面向酒馆的 RP 提示词重组成一个自包含的编码 agent skill 包，用契约保证世界观 / 角色卡 / 场景卡 / 数值系统四类产物之间命名与硬设定不漂移。

**Architecture:** 单 skill 目录。`SKILL.md` 只做路由（判阶段 → 读契约 → 派发 → 回写），不含任何设定内容生成逻辑。四个阶段各是一个 `references/stage-N-*.md`，统一六节结构；公共纪律（占位符、追问协议、契约读写、双模态渲染）在 4 个 `references/` 文件里，阶段文件只引用不复述。

**Tech Stack:** Markdown + YAML。无代码、无依赖、无脚本。验证靠 `wc -l` / `grep` / dry-run 推演。

**Spec:** `D:/AI/RP创作/参考/原始提示词/rp-factory/docs/specs/2026-11-20-rp-prompt-architect-design.md`

## Global Constraints

- **自包含**：`SKILL.md`、`references/**`、`templates/**` 中不得出现任何指向包外文件的路径，不得出现源文件名（`RP 世界观设计助手.md`、`AI-RP 角色架构师.md`、`AI-RP 系统架构师.md`、`RP场景生成器.md`、`非变量的HTML状态栏.md`）。源文件在验证通过后会被删除（spec §3.2）。
- **体量**：`SKILL.md` ≤ 120 行；每个 `references/stage-*.md` ≤ 200 行；`references/pipeline.md` ≤ 150 行。
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
Expected: `SKILL.md` ≤120；各 `stage-*.md` ≤200；`pipeline.md` ≤150。

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
