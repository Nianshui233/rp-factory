# 阶段 `mvu` · 变量系统（MVU）

产物 type：`mvu-schema` / `mvu-initvar` / `mvu-entries`。骨架：`templates/mvu-schema.js` / `mvu-initvar.yaml` / `mvu-entries.yaml` / `regex-mvu.json` / `tavern-script.json`。格式与降级链回 `references/interview-protocol.md`。

## 进入条件

- **必须先有 `axis-system.yaml`**。本阶段只做投影：把轴的定义翻译成可执行的字段与夹取，**不重新设计数值**（重新设计 = 同一份数两处真相）。
- `naming.axes` 已收口（无 `provisional: true`）。还在 `provisional` 就先回阶段 4。
- 需要酒馆助手（JS-Slash-Runner）+ MVU 脚本。契约 `project.sillytavern.extension_tavern_helper: false` 或整段 `null` → 先说明"这条路要装酒馆助手，没装的话 MVU 不跑"，再问要不要退回纯提示词（本阶段 `skipped`，只交轴表）。
- `project.web_research: true`：查过 MVU 的现行字段口径（例如有没有官方推荐的 `stat_data` 结构）再动笔，记 `制作文件/项目记录/检索来源.md`。
- 用户明说"数值要记住 / 每轮别忘 / 变量会自己更新 / 想要变量管理器"才进；只是"每个角色有好感度"属阶段 4，不是本阶段。

## 追问

**充分性评估**三问全部可答则直接生成：

1. **投影范围**：哪些轴要进变量、每个轴作用在谁身上（从 `axis-system.yaml` 的 `targets` 直接推）
2. **变动粒度**：每轮微调、每场结算，还是只在关键事件后结算
3. **世界层**：时间（日期 / 时段 / 地点）要不要可写、要不要背包

不满足则追问，**最多 2 轮、每轮 ≤5 问**，每题 2–3 选项 + 其他：

| 问题 | 选项 | 落进 |
|---|---|---|
| 轴上要不要"每人一份" | A 全局一份（≤2 人）/ B 每人一份（3–15 人）/ C 分 2–4 组 | `Schema.角色` 的键 |
| 时间推到多细 | A 不写 / B 日期 + 时段 / C 日期 + 时段 + 地点 | `世界` 块 |
| 背包要不要 | A 不要 / B 固定几格 / C 动态键 | `背包` 块 |
| 数值一次能动多少 | A 每轮 ±(1~3) / B 每场 ±(3~6) / C 只在关键事件 | 更新规则里写死 |
| 要不要"输出格式强调"条目 | A 不建（默认）/ B 建但禁用 / C 建并启用 | 产物第 3 件 |

## 判断标准

### 什么时候不做 MVU

三条**全中**就直接 `skipped`，并在 `decisions` 写一句理由：

- 轴少于 2 条，且没有 `targets`（单值单轴用不着持久化）
- 一次性短局，不跨多轮推进
- 既不做状态栏、也不做分档人设（没有任何东西要读这些值）

### 结构：写进 zod 脚本，不写 `$meta`

六个稳定实例里 `[initvar]` 一个 `$meta` 都没有，结构全在卡内脚本里。`$meta` 是"不写脚本时的退化路线"，不是本包的做法。

```js
import { registerMvuSchema } from 'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js';
const Schema = z.object({ … });
$(() => { registerMvuSchema(Schema); });
```

### 数值字段的四段式（少一段就出事故）

```js
好感度: z.coerce.number().catch(20).transform(v => _.clamp(v, 0, 100)).prefault(20)
```

- `.catch(初值)` 是**必须**的：只写 `z.coerce.number()` 时，模型写一个 `"很高"` 会先产出 `NaN`，在 `.transform` 之前就抛错，**整条更新被拒**——不是这一个字段，是这一楼全部改动都没了。
- 夹取的两端都取轴的 range。非零下限用显式 clamp，例如 _.clamp(v, -50, 100)。
- `.prefault(初值)` 让"没提到这个字段"时有值。`.default()` 不给对象键补值，这里要 `prefault`。
- 字符串与枚举同样要接住脏值：`z.string().catch('未知')`、`z.enum([...]).catch('傍晚')`。
- 不要用 `.min()/.max()`：那会**拒绝**越界值并作废整条更新，而我们要的是夹住。

### 三层结构

```
Schema
├── 世界     日期 / 时段（枚举）/ 地点，可选 天气
├── 主角     姓名 / 位置（用户侧，能少则少）
├── 角色     每个 target 一份（群像 3–15 人），每人几个轴
└── 背包     可选：物品名 → 数量
```

- 角色键名逐字用角色卡里的 `character.name`；改名要同时改 schema、`[initvar]`、更新规则三处，且回写契约。
- 轴名逐字用 `naming.axes`；**`naming.schema_axes` 写本阶段实际用到的轴名**（交付校验按它查 `description` 有没有漏）。
- 顶层只有一个 `Schema`，不要给每个角色各注册一次。

### `[initvar]` 只放初始值

- 条目名必须含 `[initvar]`（MVU 只认 `entry.comment.toLowerCase().includes('[initvar]')`）。
- **必须 `disable: true`**：它只在开聊时读一次，之后留在上下文里就是白占字数。
- 内容与 schema 的键一一对应；值可以与环境不同——**dry-run 示例里刻意写成与 `prefault` 不同的值**（例如轴 `initial` 是 62，示例写 33），否则"读没读到"根本验不出来。
- 书名：`extensions.world` == 世界书文件名，默认 `<世界名> 世界书`。两处不一致，卡不会自动挂书。

### 三条条目

| 条目 | 配置 | 内容要点 |
|---|---|---|
| `[mvu_update]变量更新规则` | `constant: true`、`position: 4`（depth 0）、`order: 200`、递归双向 prevent | 每个变量写 `type` / `range` / `format` / `check`；对模型是建议不是护栏 |
| `变量列表` | 同上 | 内容逐字符等于 `{{format_message_variable::stat_data}}`，不加空格不加换行 |
| `[mvu_update]变量输出格式` | 同上 | `<UpdateVariable>` + `<Analysis>` + `<JSONPatch>`，把 `delta` op 写进去 |

`[mvu_update]` 前缀是 MVU 的识别条件，不许省。第四条"输出格式强调"默认**不建**，只在实测漏输出时才建，并且建了就 `enabled: false` 备用。

### 两条正则 + 一条占位符

`templates/regex-mvu.json` 里三条，随卡一起交：

| 名字 | `findRegex` | 配置 | 缺了会怎样 |
|---|---|---|---|
| `[不发送]去除变量更新` | `/<(update(?:variable)?)>(?:(?!.*<\/\1>)(?:(?!<\1>).)*$|(?:(?!<\1>).)*<\/\1?>)/gsi` | `promptOnly: true`、`replaceString: ""` | 模型下一轮会看到自己上次的补丁 |
| `[不显示]变量更新` | 同上 | `markdownOnly: true`、`replaceString: ""` | 玩家看到 JSONPatch 原文 |
| `[不显示]状态占位符` | `/<StatusPlaceHolderImpl\/>/g` | `markdownOnly: true`、`replaceString: ""` | 每条回复尾巴挂一个标签 |

做了 `statusbar` 阶段的项目，第三条撤掉——状态栏要读它。

### 卡内脚本必须内嵌，且必须手动启用

- 卡里 `data.extensions.tavern_helper.scripts` 放两条：`MVU`（一行 import）与变量结构脚本（`templates/tavern-script.json` 的形状：`{type, enabled, name, id, content}`）。
- **导入后脚本默认不跑，也不报错。** 要在酒馆助手 → 脚本 → 该角色里启用一次（`enabled.characters` 白名单含该 avatar）。交付说明必须点名这一步，否则用户以为坏了。
- 卡内脚本跑在独立 iframe 里，`Mvu` 挂在 `window.parent`；脚本内部用 `Mvu.xxx` 即可。

## 生成

**Step 1 · 投影轴**（`templates/mvu-schema.js`）

| 轴字段 | 落到 zod |
|---|---|
| `name` | 字段名（中文照抄） |
| `range: [lo, hi]` | `_.clamp(v, lo, hi)` |
| `initial` | `.catch(初值)` 与 `.prefault(初值)` 两处 |
| `targets[]` | `角色` 下的键；没有 `targets` 就一个全局字段 |
| `thresholds` | 不进 schema（那是叙事档位），只进更新规则的 `check` 文字 |

**Step 2 · 初值**（`templates/mvu-initvar.yaml`）：逐轴、逐 target 一项，值 = `initial` / `targets_initial`。

**Step 3 · 三条条目**（`templates/mvu-entries.yaml`）：配置逐字抄注释里那三行，不要"优化"。

**Step 4 · 正则**：`cp templates/regex-mvu.json 制作文件/产物/mvu/regex-mvu.json`，把第三条按是否做状态栏决定去留。

**Step 5 · 卡内脚本**：`templates/tavern-script.json` 包一层 `mvu-schema.js` 的全文；`MVU` 那条的 `content` 是一行 `import 'https://testingcf.jsdelivr.net/gh/StageDog/tavern_module/dist/MVU/index.js';`。

**Step 6 · 自检**：本阶段的脚本校验不在过程里跑，留到收尾：`python scripts/check-stage.py mvu <项目根>`（内部跑 `validate-mvu.py`）。单独跑时用 `python scripts/validate-mvu.py 制作文件/产物/mvu --contract 制作文件/项目记录/contract.yaml`，再 `node --check` 一遍脚本。

## 写回契约

- `stages.mvu` → `partial` / `done`。
- `artifacts[]` 三条：`type: mvu-schema`（`path: 制作文件/产物/mvu/变量结构.js`）、`mvu-initvar`（`…/[initvar]变量初始化.yaml`）、`mvu-entries`（`…/变量规则.yaml`）；正则若也交，记 `type: mvu-regex`。
- `naming.schema_axes`：本阶段实际用到的轴名数组（交付校验 X02 读它）。
- `decisions[]`：抽不抽背包、时间写了哪几层、为什么某些轴没进 schema。

## 退出

- 变量门（本阶段的退出条件）：阶段收尾一检 `python scripts/check-stage.py mvu <项目根>` 退出码 0（内部跑 `validate-mvu.py` M01–M13）。
- `node --check` 过（`mvu-schema.js` 是 ES module，先改名到临时 `.mjs`）。
- 命名门：轴名与 `axis-system.yaml`、`naming.axes` 三处一致；角色键名与角色卡 `character.name` 逐字一致。
- 交付说明里**必须有四句**：① 卡里已经带了脚本；② 导入后要去酒馆助手给这个角色**启用脚本**；③ 世界书要单独导入（`importFromJson` 不会把 `character_book` 落成书）；④ 没启用脚本时 MVU 静默不跑、不报错。
- `project.web_research: true` 时确认本阶段 `检索来源.md` 有新增条目。
