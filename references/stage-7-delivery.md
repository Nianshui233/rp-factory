# 阶段 7 · 交付

产物 type：`st-card` / `st-worldbook`（只有 SillyTavern 路线才产）。骨架：`templates/st-card.json`、`templates/st-worldbook.json`。

**这是最后一个阶段，只问一个问题。** 前面所有阶段都跑完之后才进；用户中途说"打包"就先补完或明确跳过，不能拿半成品打包。

## 进入条件

- `project.stages_requested` 里的阶段都已 `done`（有 `partial` 就先问一句"还差 X，先打包还是补完"）。
- 要出 SillyTavern 包，必须有 `rolecard` 与 `world-bible`；缺任一个就只能走原生产物，或先回阶段 1 / 2。
- 阶段 5 / 6 没做也能打包：只是包里没有正则，第一楼是纯文字。
- 用户明说"打包 / 导入酒馆 / 要角色卡 json / 要世界书"才进；没提就不问，原生路线是默认。

## 追问

**只问一句，两个（或三个）选项：**

| 选项 | 交出什么 | 谁用 |
|---|---|---|
| **原生产物** | 现状：`最终产物/` 里的 YAML + HTML + 正则 JSON | 你自己留着改、喂给别的 AI、当代稿 |
| **SillyTavern 包** | 两个 JSON：`<世界名>.json`（角色卡）+ `<世界名> 世界书.json`，外带 `regex-*.json` 与两份 HTML | 直接导进酒馆就能玩 |
| **两者都要** | 上面两份都留 | 想改又想在酒馆里跑 |

不问的：世界书名与角色卡名（默认 = `project.name`）、文件放哪（`最终产物/st/`）、要不要头像（不生成图片）。用户主动要给别的名字时照填。

## 判断标准

- **导入即能用**：世界书先导、角色卡后导，进聊天就能看见设定与第一条消息；不需要用户手动填字段。
- **一条设定只写一处**：同一条规则不在 `description` 与世界书里各写一份；只有"对 AI 的核心指令"两边都留（世界书管上下文，`system_prompt` 管优先级）。
- **中文文件名照原样**：酒馆的 `sanitize-filename` 保留中文；但同一批文件里的括号、空格要统一（全用半角空格，不用全角括号混搭）。
- **名字与契约一致**：卡片名 = `st_name` = 卡片文件名；**世界书名 = 世界书文件名 = `extensions.world`**，默认是 `<世界名> 世界书`。改名只改契约，再重出包。
- **第一楼不是裸文本**：`first_mes` 里的标签必须与正则 `findRegex` 对得上——对不上就把 `first_mes` 换成一句普通开场白，别留一个没人处理的标签。

## 生成

### 一、先定三件事（内部决定，不问）

| 值 | 取法 |
|---|---|
| `st_name` | `project.name`（未命名项目时用 `未命名项目`） |
| `first_mes` | 阶段 5 做向导 → `<建卡向导>`；做面板 → `<开局界面>` 加九字段数据块；没做前端 → 用场景卡 `概览` 与 `边界` 写一句 ≤120 字开场（含 `{{user}}`） |
| 世界书条目 | 按下面第二节的映射切 |

### 二、世界书怎么切

**参数怎么定、关键词怎么备、位置怎么选，一律看 `references/worldbook-tuning.md`**——那份是"调好"的部分（套餐表、八种插入位置的风险、递归与概率、全局激活设置、十条自查），这里只管"从产物切哪几块"。

一个 section 一条（不拆到字段级，拆了会把同一段设定写两遍）。`content` 放该 section 的 YAML 片段（键名保留，缩进整体减 2 格）；`comment` 用 section 名。

| `world-bible.yaml` 的 section | `constant` | `order` | `position` / `depth` | `key`（从 `contract.naming` 取，不手写） |
|---|---|---|---|---|
| `世界规则` | `true` | `100` | `0` | `[]` |
| `变更边界` | `true` | `98` | `0` | `[]` |
| `AI即兴角色约束` | `true` | `96` | `0` | `[]` |
| `核心矛盾` | `true` | `95` | `1` | `[]` |
| `常识清单` | `true` | `94` | `0` | `[]` |
| `关键历史与时间线` | `true` | `92` | `0` | `[]` |
| `信息分层`（防剧透） | `true` | `85` | `4` / `2` | `[]` |
| `时间地点与世界范围` | `false` | `80` | `0` | `places[].name` + 场景指代 |
| `势力与社会结构` | `false` | `88` | `0` | `factions[].name` + `alias[]` + 关系指代 |
| `种族与物种`（有才出） | `false` | `78` | `0` | 种族名 |
| `跨世界规则`（有才出） | `true` | `90` | `0` | `[]` |
| `未决事项` | — | — | — | **不进世界书**：它是建构期台账，还在说明设定没写完 |
| 状态栏协议（做了阶段 6 才有） | `true` | `70` | `4` / `2` | `[]` |

关键词条目的 `excludeRecursion` 一律 `true`、`matchWholeWords` 一律 `false`；常驻条目这两项分别是 `false` 与 `false`。理由见 `references/worldbook-tuning.md` 第二、七节。

用户要"一个势力一条"时才拆：把 `势力与社会结构.势力列表` 每项单独成条，`势力关系` 与 `社会阶层与日常秩序` 合成一条常驻。默认不拆。

规矩：

- **一个 key 只归一条**：同一个名字出现在两个条目里，那个名字就失去判别力。切完扫一遍重复。
- `position`：`0` 角色卡之前、`1` 角色卡之后、`4` 按深度插入（配 `depth`）。值用数字，不用 `"before_char"` 字符串。
- 常驻条目（`constant: true`）总字数按 5000 字预算（校验器 W09 盯着）；单条正文 ≤1000 字，超了拆条。
- 每条绿灯条目备 8–15 个关键词（本名 / 别名 / 关系指代 / 场景指代 / 同义口语），宁宽勿漏；纯文本关键词不支持逗号，要匹配带标点的串就写 `/.../flags` 正则。
- 别用 `position: 2 / 3`（作者注关了就没）和 `5 / 6`（会被当示例对话解析）。
- 角色卡本身不进世界书：角色是 `description` 的活，世界书管世界。
- 场景卡不进世界书，除非用户要"场景随关键词切换"——那时每张场景卡一条，`key` 用场景名。

### 三、两个文件

**`<世界名> 世界书.json`**

```json
{ "entries": { "0": { … }, "1": { … } } }
```

每条用 `templates/st-worldbook.json` 里的完整字段（酒馆编辑器靠这些字段渲染，缺字段会在面板里显示空白）。必填非空：`uid`、`comment`、`content`；`uid` 从 0 连号。

**`<世界名>.json`**（角色卡）

| 字段 | 写什么 |
|---|---|
| `name` / `data.name` | `st_name` |
| `description` / `data.description` | 世界观 YAML 全文 + 一条分隔 + 角色卡 YAML 全文（保留中文键名，删 `#` 注释），结尾一句"以上是设定，不是示例对话" |
| `personality` / `scenario` | 留空——内容都在 `description` 里，重复写会翻倍占 token |
| `first_mes` / `data.first_mes` | 见上表三条规则 |
| `mes_example` | 留空；角色卡的 `speech` 已经在 `description` 里 |
| `creator_notes` / `data.creator_notes` | 导入四步（见第五节）+ 版本 + `RP-Factory` |
| `system_prompt` | 项目档案的「本文档对AI的核心指令」（`hard_settings` 里 `H0x` 那条） |
| `post_history_instructions` | 留空 |
| `alternate_greetings` | `[]`；用户要备用开场才写 |
| `tags` / `data.tags` | 类型、基调、`rating` 各一个 |
| `creator` | `"RP-Factory"` |
| `character_version` | `"1.0"`，改一次设定加 0.1 |
| `spec` / `spec_version` | `"chara_card_v2"` / `"2.0"` |
| `data.extensions.world` | 世界书的文件名去掉 `.json`，默认 `"<世界名> 世界书"`（ST 导入世界书时用文件名当书名，同名才会自动挂载；别写成 `st_name`） |
| `data.extensions.regex_scripts` | 阶段 5 / 6 的正则数组原样搬进来（见第四节） |
| `data.extensions.talkativeness` / `fav` | `"0.5"` / `false` |
| `data.extensions.depth_prompt` | `{prompt: "", depth: 4, role: "system"}` |
| `create_date` | `YYYY-MM-DD` |

顶层与 `data` 里同名字段都要填同一份内容：ST 读 `data`，但别的工具（酒馆助手、导出器、第三方站）读顶层。

### 四、正则怎么带（两条路，都给）

- **卡内嵌**：`data.extensions.regex_scripts` = 阶段 5 / 6 产出的数组原样。进聊天时 ST 会弹"这张卡内嵌了正则，是否允许角色专属正则"，**必须点允许**，否则不生效。
- **全局导入**：`regex-opening.json` / `regex-statusbar.json` 单独导入（设置 → 扩展 → 正则 → 导入）。不需要点允许，但会作用于所有角色。

交付说明里两条都写，让用户自己选。内嵌那份的 `id` 用 UUID，别用中文（有些第三方工具只认 ASCII）。

### 五、导入顺序（`creator_notes` 与交付说明都写这四步）

1. 世界书：`世界书` 页 → 导入 → 选 `<世界名> 世界书.json`。
2. 角色卡：`角色` 页 → 导入 → 选 `<世界名>.json`。`extensions.world` 与已导入的世界书同名时 ST 自动挂上；没挂就在角色卡编辑页的「世界书」下拉里选同名那本。
3. 正则：看到"允许角色专属正则"的弹窗点允许；没弹窗就设置 → 扩展 → 正则 → 导入 `regex-*.json`。
4. 酒馆助手：设置里打开"消息渲染"，回到聊天，第一条消息应该出现建卡向导或登场面板。

### 六、文件放哪

`最终产物/st/` 下：

```
<世界名>.json
<世界名> 世界书.json
regex-opening.json          # 有阶段 5 才有
regex-statusbar.json        # 有阶段 6 才有
开场前端.html / 状态栏前端.html   # 可选，方便改完再生成正则
```

原生路线的 `最终产物/*.yaml` 原样保留，不走 `st/`。

## 写回契约

- `stages.7` → `done` / `skipped`（用户选原生路线就是 `skipped`，因为阶段 7 的产物是打包）。
- `delivery.route` → `native` / `st` / `both`；`delivery.st_name`、`delivery.files[]`（相对 `最终产物/st/`）。
- `artifacts` 追加两条：`st-card`、`st-worldbook`（`path` 形如 `最终产物/st/<世界名>.json`）。
- `decisions` 记：路线、`first_mes` 来源（向导 / 面板 / 无前端时的开场白）、正则带法（内嵌 / 全局 / 都带）。
- `hard_settings` 不动——打包不产生新设定；若打包时发现某条设定缺失，回对应阶段补，不在这一阶段现编。

## 退出

**交付门六条。跑校验器，别肉眼对：**

```
python scripts/validate-st-package.py "最终产物/st/<世界名>.json" "最终产物/st/<世界名> 世界书.json"
```

脚本在**本 skill 包**的 `scripts/` 下，不在用户项目里；当前目录不是包根时用脚本的绝对路径。只给一个目录也行：`python scripts/validate-st-package.py "最终产物/st"`（自动认出卡与书）。

退出码 0 才叫过；有 `FAIL` 就改到没有。脚本抄的是酒馆本体的规则（`TavernCardValidator` 的必填字段、`readFromV2` 的顶层/`data` 同步、`convertCharacterBook` 的 `character_book` 形状、`newWorldInfoEntryDefinition` 的条目字段、`regexFromString` 的编译），再加本包自己的五条预算。警告可以带着走，但要知道自己在忽略什么。

它查的七件事：

1. 两个 JSON 能解析；`spec == "chara_card_v2"`、`spec_version == "2.0"`；`data` 十四个必填字段齐全。
2. 世界书每条 `content` 非空、`key` 是数组、`position` ∈ 0–7、`uid` 与键一致、必填字段齐全；常驻且无关键词 = 失败。
3. `data.extensions.world` == 世界书文件名（去 `.json`）；卡名含 `/ \ : * ? " < > |` 会失败。
4. 每条 `findRegex` 能用 JS 编译（有 node 就实测）；用了 `$1` 却没捕获组 = 失败。
5. `first_mes` 里的标签能被某个正则接住；接不住 = 失败（第一楼会变裸标签）。
6. 常驻条目合计字数 ≤ 5000（本包预算），关键词无跨条目重复。
7. 调优项：绿灯关键词 <8（W10）、`excludeRecursion` 不是 `true`（W11）、含中文却开了整词匹配（W12）、`position` 用了 2/3 或 5/6（W13，5/6 直接失败）、关键词带逗号（W14，失败）、`order` 全同（W15）、绿灯 `selective: false`（W16）。

3–7 的判据与后果都在 `references/worldbook-tuning.md`；W10–W16 全绿才算"调好"，只有 W 警告可以带着走，但要说得清忽略的是哪条。

另外三条肉眼过：

- `description` 里出现的势力名、地名、系统名、轴名，逐个能在 `contract.naming` 里找到；找不到说明打包时改名了，回头改契约再重出。
- 交付说明四步齐全，且写清"内嵌正则要允许"这一句。
- 交付说明附上 `worldbook-tuning.md` 第六节那张全局设置表（扫描深度 / 预算 / 递归 / 整词匹配几项的推荐值与理由）。

只要粘贴版（用户明确说"别写文件"）→ 两个 JSON 各给一个代码块，路径写进契约但标 `pending: 未落盘`。
