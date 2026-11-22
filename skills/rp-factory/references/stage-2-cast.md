# 阶段 2 · 角色 / NPC

产物 type：`rolecard`。骨架：`templates/rolecard.yaml`。标杆样本：`examples/rolecard-minimal.yaml`（自检门对标它）。格式与降级链回 `references/interview-protocol.md`。

## 进入条件

- 有 `contract.naming.world`：先读语言风格、禁忌、冲突类型、势力名单，用它约束角色的 `speech` 与 `attitudes`。
- 用户直接给出角色设定、无世界观：可按"补采访问"问一次（世界有无超常力量、社会结构大致形态），问不到就打 `[推断：…](待确认)`。
- 用户提交已有卡（`.json`/`.png`）或人物稿 + 修改需求：走“迭代”分支，不重走采集。

## 执行前置

**仅当 `project.web_research: true` 时执行本节，否则跳过直接进「追问」**。

**强制检索流程**（必须完整执行，不能跳过）：

- [ ] **1. 确认检索目标**：该角色可查的外部依据——
  - 基于已有作品：查官方设定 / 正式关系 / OOC 高频点
  - 真实题材：查身份对应的职业与年代细节
  - 原创角色：若名字/职业/文化背景有外部原型，先查再用
  - 按 `references/web-research.md` 表格，本阶段最低检索量：**每人 ≥1 条，主要角色 ≥2 条**

- [ ] **2. 执行检索**：
  - 使用 `web_search` 或 `fetch_content` 工具实际执行搜索
  - 每条检索写明：来源站点 + URL + 取用什么 + 可信度
  - 没检索到的记 `未检索到` 并说明下一步（问用户 / 标待确认）

- [ ] **3. 记录结果**：
  - 打开或追加 `制作文件/项目记录/检索来源.md`
  - 逐条追加：`[S##] 来源：... · 取用：<该角色的哪个设定> · 可信度：...`
  - **必须新增 ≥N 条记录**（N = 本轮角色数，主要角色 ×2）

- [ ] **4. 展示证据**：
  - 在回复中简要列出「本轮新增的检索条目」（编号 + 一句话）
  - 格式：`✓ 已检索 2 条并记入检索来源.md: [S04] 哈利·波特原著设定 / [S05] 1991年英国寄宿学校生活`

- [ ] **5. 确认完成**：
  - 自检：`检索来源.md` 进入本阶段后新增条目 ≥ 最低检索量？
  - 未满足 → **不许进「追问」，必须补齐**
  - 已满足 → 继续下一节「追问」

**↓ 完成上述 5 步后，才能继续下一节「追问」 ↓**

## 追问

**三维度充分性评估**（内部做，不展示表格）：

| 维度 | 充分标准 |
|---|---|
| 世界观 / 题材 | 能确定语言风格、禁忌、冲突类型 |
| 核心动机 & 恐惧 | 能转化为 ≥2 条 `behavior.rules` |
| 底线 / 价值排序 | 能推导出 `taboos` 与 `anti_ooc.never` |

**快速通道**：三维度均充分 → 跳过采集，直接进生成。

**采集强度**：缺 1 项 → 单轮 1 问；缺 2–3 项 → 最多 2 轮、每轮 ≤3 问。

**优先级**：P0 世界观/题材（决定语言风格、禁忌、冲突类型）→ P1 核心动机 & 恐惧（须能变成 `behavior.rules`）→ P2 底线/价值排序（决定 `taboos` / `anti_ooc`）。

每问 2–3 个可选项 + 其他，禁止开放式空问；无果走 `references/interview-protocol.md` 的降级链，不另造。

## 判断标准

### 可执行性三条自检（出版前必须执行）

**每条 `behavior.rules` 必须通过以下三项检验，否则重写：**

- [ ] **检验 1：`trigger` 必须外部可判定**——
  - ❓ **反例：**`trigger: 内心感到不安` → 重写为 `trigger: 听到身后脚步声 + 周围无人`
  - ❓ **反例：**`trigger: 感到悉伤` → 重写为 `trigger: 被明确拒绝 + 对方转身离开`
  - ✅ **正例：**`trigger: 被威胁` / `trigger: 看到队友受伤` / `trigger: 被问到家人`

- [ ] **检验 2：`action` 必须第三方可观察**——
  - ❓ **反例：**`action: 变得悲伤` → 重写为 `action: 低头沉默 + 反应变慢 + 简短回答`
  - ❓ **反例：**`action: 内心挣扎` → 重写为 `action: 停顿超过 3 秒 + 目光闪烁 + 然后强行同意`
  - ✅ **正例：**`action: 拔剑迎敌` / `action: 立刻冲到队友前面` / `action: 鼓励说“我们能行”`

- [ ] **检验 3：`reason`/`condition`/`cost` 必须提供额外信息**——
  - ❓ **反例：**`trigger: 被威胁` / `action: 反击` / `reason: 因为被威胁了` → `reason` 重复了 `trigger`，无额外信息
  - ✅ **正例：**`reason: 因为信奉“不先动手就是输”` → 揭示价值观，可追溯至 `values.ranking`
  - ✅ **正例：**`condition: 周围有队友时` → 给出触发的额外条件
  - ✅ **正例：**`cost: 会暴露位置，导致后续围攻` → 明确后果

**自检时机：出粗版、中间版、终稿前均必须执行。**

**不通过处理：**标记 `【待转化为可执行规则】` + 给出 2–3 个可执行版本供用户选择。

---

### 规范 1：`behavior.rules`（≥4 条，覆盖四类场景）

四类场景必须各至少 1 条：合作（协助他人、团队配合）、冲突（对抗、分歧、争执）、压力（危险、失败、时间紧迫）、道德困境（价值观冲突、两难选择）。

三种句式，每条选一：
- 格式 A 价值驱动：`trigger` + `action` + `reason`（价值依据，须可追溯至 `values.ranking`）
- 格式 B 条件约束：`trigger` + `action` + `condition`（前置条件/约束）
- 格式 C 代价权衡：`trigger` + `action` + `cost`（代价/后果）

质量标准三条：`trigger` 必须外部可判定（非内部情绪状态）；`action` 必须第三方可观察（非重述触发条件）；`reason`/`condition`/`cost` 必须提供额外信息（非重述 `action`）。

三个反例，以下写法一律重写：

❌ 循环定义——`action` 重述 `trigger`：`trigger: 感到悲伤` / `action: 变得悲伤`。

❌ `trigger` 不可外部判定：`trigger: 内心感到不安` / `action: 保持警惕`。

❌ `reason` 无额外信息：`trigger: 被威胁` / `action: 反击` / `reason: 因为被威胁了`。

### 规范 2：`psychology.values`（≥3 项排序 + 推导说明）

`ranking` 写 `A > B > C`，`rationale` 一句话说清排序理由，且必须能推导出 ≥2 条 `behavior.rules` 的取舍逻辑。

自检口径：`ranking` 每对相邻价值之间的取舍，至少对应 1 条规则。

### 规范 3：`taboos` 与 `anti_ooc.never` 逻辑一致

- `taboos`：角色**绝不会做**的具体可观察行为（如"绝不伤害儿童"）。
- `anti_ooc.never`：`taboos` 的**超集**，两类条目——**底线映射**（`taboos` 每项的直接对应，保证 `taboos ⊆ never`）+ **价值推导**（`values` 排序推出的额外禁止行为，`taboos` 未显式列出但违反核心价值）。

三条验证：`taboos` 每项都能在 `never` 找到对应；`never` 中超出 `taboos` 的条目都能从 `values` 排序推出；`never` 不得出现与 `values` 或 `taboos` 矛盾的条目。

### 规范 4：语言层三项互证

- `speech.style`：`tone`（语气基调）+ `structure`（句式习惯）+ `vocabulary`（用词倾向），三项都必须可观察。
- `speech.rules`：≥4 条，覆盖 `structure` / `forbidden` / `emotion_shift` / `addressing` 四类，每条须能在 `quotes` 中找到体现。
- `speech.quotes`：≥3 条，每条含 `line` + `context`，且同时体现 `style` 与 ≥1 条 `rule`。

`quotes` 可带 `demonstrates`（体现哪条 rule），仅内部验证用，可不输出。

`catchphrases` 用词须符合 `style` 的 `tone` 与 `vocabulary`；`stress_response` 的语言变化不得违背 `emotion_shift` 规则。

### 规范 5：`background` 受控，事实分稳定/临时

`background` 默认 1–2 句，只写对当前行为有直接影响的信息；未确认的标 `【AI补全·可替换】`。禁止把关键行为逻辑埋在背景里——那类内容必须转译进 `behavior.rules` 或 `psychology`。

事实分级：**稳定事实**（身份、体质、长期能力、已确立的关系）进卡；**会过期的状态**（当前位置、进行中的任务、暂时的伤、正在被追）不进卡——写 `facts.temporary` 且必须给 `expires_when`，或直接移到开场/状态层。把「正在被追杀」写进背景，第一轮过去就自相矛盾，而卡已过全部结构校验。

### 规范 6：语言使用规则

规则/逻辑类字段用英文（`trigger` / `action` / `reason` / `condition` / `cost` / `type`）；描述类字段跟随用户语言（`motivations` / `fears` / `background` / `quotes.line`）；专有名词保持原语言。

## 生成

**第一步先把模板抄下来再填**：把 `templates/rolecard.yaml` 的键树整份复制，逐个键填值；**不许新增顶层键**，也**不许用自创块替换既有块**（例如另起 `intimacy` 顶替 `nsfw`——那是同一次实操里真实发生过的失败）。模板的键不够用时，信息往扩展位塞（`lore` / `relationships` / `growth_arc`），要真需要新键，先问用户、同意后写进 `contract.decisions` 并在交付说明里点名。

**档位**（用户未指定时默认标准）：

| 档位 | 包含字段 | 适用 |
|---|---|---|
| 精简 | `psychology` + `behavior` + `speech` + `anti_ooc` | 快速原型、轻量 RP，40–60 行 |
| 标准 | 模板全部基础字段；`content_boundaries.nsfw: true` 时**必须附加 `nsfw` 块（七键齐全）** | 通用（默认），80–120 行 |
| 扩展 | 标准 + `lore` + `relationships` + `growth_arc` | 长线叙事、复杂世界观，150–200 行 |
| 定制 | 仅用户指定字段 | 用户点名要某几块 |

**生成后交付三件**：① 完整人物设定 YAML ② 简要设计说明 ≤5 句（价值排序理由、关键规则的推导逻辑）③ 有 `【AI补全·可替换】` 就逐条列出待确认。说明文字与补全清单的位置按 `references/dual-mode.md`，都不夹进 YAML 正文。

**接手别人的成品**：用户给的是别人的卡 / 半成品 / 导出的 PNG 时，先读 `references/takeover.md`（取证 → 拆成我们的形状 → 五条不破坏），再走下面的迭代。

**迭代**（用户提交已有卡 + 修改需求）：
1. 定位直接修改项。
2. 级联影响分析——改某字段要连带检查的字段见下表。
3. 输出方案：列直接修改项 + 列需级联调整的字段及理由，用户确认后执行。
4. 输出更新后的完整 YAML + 变更摘要（哪些被直接改、哪些被级联调整）。

| 修改字段 | 必须连带检查 |
|---|---|
| `psychology.values` | `behavior.rules` 的 `reason`、`taboos`、`anti_ooc.never` |
| `psychology.fears` | `behavior.stress_response`、`internal_conflict` |
| `psychology.taboos` | `anti_ooc.never` |
| `speech.style` | `speech.rules`、`speech.quotes`、`catchphrases` |
| `behavior.rules` | `attitudes` 的行为模式一致性 |
| `background` | `psychology.motivations`、`fears` 的因果链 |

## 写回契约

- `naming`：角色名进 `decisions`（`question: 角色名` / `answer: …`）；若归属某势力，确认该 `factions[].id` 已在契约里，没有则先回问阶段 1 或补采一次。
- `stages.2` → `partial` / `done`。
- 用户提到可量化维度（"他在意好感度""堕落值会变"）→ 写 `naming.axes` 并标 `provisional: true`，同时在 `decisions` 记"由阶段 4 接管确认"。阶段 4 接手后删除 `provisional`。
- `hard_settings[]`：用户明确确认的角色底线追加为硬设定，`source: 用户确认`。
- `content_boundaries`：落笔前必须已锁定 `nsfw` / `rating` / `hard_no`（开局就锁了，缺则回边界门）。`nsfw: false` → 卡里不写 `nsfw` 块，`taboos` 与 `anti_ooc.never` 里加一条"不做任何性行为"。
- `player_agency`：`behavior.rules` 只写到角色自己的动作与台词为止——不得有「玩家犹豫时角色替玩家点头」。放宽时按 `references/decisions.md` 第六节写 `allowed` / `scope` / `duration` 并记 `decisions`。

## 退出

- 自检门四类（见 `references/pipeline.md`）全通过。内容边界层按开关判，**不按产物自己有没有字段判**：
  - `nsfw: true` → 每张卡必须有 `nsfw` 块且七键齐全；**缺块 = 这一阶段失败**，回生成步补，不是跳过检查。
  - `nsfw: false` → 卡里不得出现 `nsfw` 块；`taboos` 与 `anti_ooc.never` 必须含「不做任何性行为」。
- 产物正文里不许出现构建期占位符（`【AI补全·可替换】` / `[待定]` / `【未知】`）——模板里的 `unknown_handling` 要改写成运行时口径（「从 `values.ranking` 推断，依据不写进正文」），不能把「标占位符」这句话原样留在卡里。
- `【AI补全·可替换】` 逐条列出，交用户确认。
- **阶段收尾一检** `python scripts/check-stage.py cast <项目根>`（先查契约，再逐张跑 `validate-rolecard.py`），退出码 0 才算过。校验项就是上面这些结构要求 + `facts` 分级形状（若有）+ 正文占位符 0 命中，逐条打印，不用背。
- 命名门四步通过（角色名、势力名、地点名与契约一致）→ 交付 → 回写契约 → 阶段结束。
- 用户只要精简档位时不强推标准档；只在交付时一句说明精简档会让 AI 即兴补全更多。
