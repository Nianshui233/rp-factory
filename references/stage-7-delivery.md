# 阶段 7 · 交付

产物 type：`st-card` / `st-worldbook`（只有 SillyTavern 路线才产）。骨架：`templates/st-card.json`、`templates/st-worldbook.json`、`templates/st-character-book-entry.json`。

**这是最后一个阶段，只问一个问题。** 前面所有阶段都跑完之后才进；用户中途说"打包"就先补完或明确跳过，不能拿半成品打包。

## 进入条件

- `project.stages_requested` 里的阶段都已 `done`（有 `partial` 就先问一句"还差 X，先打包还是补完"）。
- 要出 SillyTavern 包，必须有 `rolecard` 与 `world-bible`；缺任一个就只能走原生产物，或先回阶段 1 / 2。
- 阶段 5 / 6 没做也能打包：只是包里没有正则，第一楼是纯文字。
- 用户明说"打包 / 导入酒馆 / 要角色卡 json / 要世界书"才进；没提就不问，原生路线是默认。

## 追问

**两问，按顺序。第一问路线，第二问要不要我动手导入。**

**问一（路线）三个选项：**

| 选项 | 交出什么 | 谁用 |
|---|---|---|
| **原生产物** | 现状：`最终产物/` 里的 YAML + HTML + 正则 JSON | 你自己留着改、喂给别的 AI、当代稿 |
| **SillyTavern 包**（默认推荐） | `<世界名>.json` 单文件：卡 + **内嵌世界书** + 内嵌正则；另给 `regex-*.json` 与两份 HTML 方便改 | 直接导进酒馆就能玩 |
| **两者都要** | 上面两份都留 | 想改又想在酒馆里跑 |

不问的：世界书名与角色卡名（默认 = `project.name`）、文件放哪（`最终产物/st/`）、要不要头像（不生成图片）。用户主动要给别的名字时照填。

**问二（只在答案含酒馆包时问）：要不要我直接导进你正在跑的酒馆，并当场验一遍。**

| 选择 | 我做什么 | 交出什么 |
|---|---|---|
| **要，帮我导并测** | 先跑交付门校验器，再 `python scripts/st-import.py --st auto --card <卡>` 导入（同名覆盖）、回读自检，有界面再 `node scripts/st-probe.js --char <卡名>` 量 iframe 高度 | 一行结论 + 逐项 PASS/WARN；没成就把卡在哪一步说清 |
| **不用，给我文件** | 只跑校验器与肉眼三条 | 文件 + 四句话（导入 / 渲染开关 / 世界书要不要单独导 / 触发词该出现在哪条消息） |

不问第二问的两种情况：`project.sillytavern` 是 `null`（没装）、或 `running_url` 是空（装了没在跑）。这时只说一句"现在没有在跑的实例，启动后要我导也说一声"，然后把文件交出去。

用户答"要"之后，若导入失败（版本太旧、端口不对、权限不足），**不要自己换地址重试到成功为止**：报一次实际错误，把可用地址与文件位置给用户，让他决定。

## 判断标准

- **一个文件进酒馆**：世界书和正则都挂在卡里（`data.character_book` + `data.extensions.regex_scripts`），导入一张卡、点一次"导入内嵌世界书"就齐了。**别做"先导世界书再导卡再手动绑定"那种三件套**——那是旧做法，用户会在第二步漏掉。
- **内容分三层，不许串层**：`description` = 每轮都必须在场的骨架；`character_book` = 按需加载的细节；`system_prompt` = 只有优先级最高的那几条指令。同一段话只在一层出现。
- **`description` 有预算**：≤8000 字（校验器 X03 盯着）。群像卡的主要篇幅在 `character_book` 的人物条目里，不在 `description`。
- **中文文件名照原样**：酒馆的 `sanitize-filename` 保留中文；但同一批文件里的括号、空格要统一（全用半角空格，不用全角括号混搭）。
- **名字与契约一致**：卡片名 = `st_name` = 卡片文件名；**世界书名 = `character_book.name` = `extensions.world`**，默认是 `<世界名> 世界书`。改名只改契约，再重出包。
- **第一楼不是裸文本**：`first_mes` 里的标签必须与正则 `findRegex` 对得上——对不上就把 `first_mes` 换成一句普通开场白，别留一个没人处理的标签。

## 生成

### 一、先定三件事（内部决定，不问）

| 值 | 取法 |
|---|---|
| `st_name` | `project.name`（未命名项目时用 `未命名项目`） |
| `first_mes` | 阶段 5 做向导 → `<建卡向导>`；做面板 → `<开局界面>` 加九字段数据块；没做前端 → 用场景卡 `概览` 与 `边界` 写一句 ≤120 字开场（含 `{{user}}`） |
| 条目清单 | 按下面第二节的三层分法切 |

### 二、三层怎么分

| 层 | 放什么 | 为什么 |
|---|---|---|
| `description`（≤8000 字） | `元信息` / `类型与基调` / `时间地点与世界范围` / `信息分层` / `世界规则`摘要 / **住户速查（每人 ≤2 行：名字·id·住处·登场期·命门）** / **数值摘要（轴名 + 范围 + 初始 + 每级一句话）** / 场景速查（地点名 + 一句话） | 每轮都在，必须能让模型立刻知道"这是哪个世界、谁在场、数值怎么算" |
| `character_book` 条目 | 世界观全文（规则、默契、势力、时间线、常识）、**每个角色一条**、**每个地点一条**、势力、名词、数值与判定、状态栏协议 | 按需触发，不占每轮预算 |
| `system_prompt` | 项目档案「本文档对AI的核心指令」原文（`hard_settings` 里那条） | 优先级高于一切 |

**不要把 `description` 当成"把所有 YAML 拼在一起"**：那是单人卡的写法，群像卡拼 14 张卡就是 5 万 token，模型还没开始回话上下文就没了。

### 三、条目怎么切

**参数怎么定、关键词怎么备、位置怎么选，一律看 `references/worldbook-tuning.md`**——那份是"调好"的部分（套餐表、插入位置的风险、递归与概率、全局激活设置、十二条自查），这里只管"切哪几块"。

| 来源 | 条数 | `constant` | `order` | `position` | `keys` |
|---|---|---|---|---|---|
| 世界规则 / 这栋楼的默契 / 变更边界 / 世界怎么运转 / AI即兴约束 | 3–6 条，各一条 | `true` | 100–94 | `before_char` | `[]` |
| 信息分层（防剧透） | 1 | `true` | 85 | `4` + `depth: 2` | `[]` |
| 数值与判定 | 1 | `true` | 84 | `4` + `depth: 2` | `[]` |
| 状态栏协议（仅做了阶段 6） | 1 | `true` | 70 | `4` + `depth: 0` | `[]` |
| **每个角色**（`最终产物/角色卡/*.yaml`） | 每人 1 条 | `false` | 80–78 | `before_char` | 本名 + `alias[]` + 关系指代 + 绰号（8–15 个） |
| **每个地点**（`最终产物/scene/*.yaml` 或 scene-sheet） | 每地点 1 条 | `false` | 76–74 | `before_char` | 地点名 + 区域名 + 场景指代（8–15 个） |
| 势力 / 时间线 / 常识 / 名词 | 各 1 条 | `false` | 88–82 | `before_char` | `factions[].name` + `alias[]` |

规矩：

- **一个 key 只归一条**：同一个名字出现在两个条目里，那个名字就失去判别力。切完扫一遍重复。
- **人物条目写什么**：该卡的 `psychology` + `behavior` + `attitudes` + `speech`（删掉 `identity.appearance` 以外的外貌细节、删 `nsfw` 块——`nsfw` 块留一份在「数值与判定」条目里按轴分档写，避免 14 份重复）。`content` 用 YAML 片段，键名保留、缩进减 2 格。
- **地点条目写什么**：`概览` + `空间结构` + `关键区域.现场可见` + `出入口与安防` 的可判定物。这是"客厅只有一张长沙发""卫生间只有一个"能进上下文的唯一通道。
- **数值与判定条目写什么**：每条轴的 `range` / `initial` / `direction` / 各级 `label` 与 `behavioral_signs`（每级压成一句）+ `calc_mod` + `evaluation_order` + `anti_exploit`。多目标轴（`targets[]`）把每人一行初始值列在条目末尾。**没有这一条，数值系统在角色扮演里等于不存在。**
- 常驻条目总字数 ≤8000（校验器 C22），单条 ≤1000 字，超了拆条；`未决事项` 不进任何一层（它是台账，留在 `创作痕迹/`）。
- 场景条目的 `keys` 用场景名与别名；与地点条目撞名时合并成一条（地点条目 `content` 追加场景细节），一个名字只归一条。

### 四、两个形状，别混

酒馆有两种世界书 JSON 形状，**字段名不一样**，混了导入后参数全丢：

| | 卡内 `data.character_book.entries`（v2 规范） | 独立 `<世界名> 世界书.json`（native） |
|---|---|---|
| 形状 | **数组** | `{entries: {"0": {...}}}` |
| 关键词 | `keys` | `key` |
| 次序 | `insertion_order` | `order` |
| 位置 | `position: "before_char" / "after_char"`，深度用 `extensions.position` | `position: 0–7` 数字 |
| 开关 | `enabled: true` | `disable: false` |
| 高级项 | 全在 `extensions.*`（`depth` / `exclude_recursion` / `match_whole_words` / `probability` / `selectiveLogic` / `display_index`） | 平铺在条目上 |
| 主键 | `id` | `uid` |

`templates/st-character-book-entry.json` 是 v2 那个形状的空骨架；`templates/st-worldbook.json` 是 native 形状的完整字段骨架。**两形状由同一份条目清单生成**，不许手抄两遍（改一处漏一处就是漂移）。

默认只出**卡内嵌**那一份；用户要"单独的世界书文件"或要拿去改，再额外生成独立文件，并说明"导了卡就别再导这个独立文件，重名会覆盖"。

### 五、角色卡字段

| 字段 | 写什么 |
|---|---|
| `name` / `data.name` | `st_name` |
| `description` / `data.description` | 见第二层的 `description`（≤8000 字），结尾一句"以上是设定，不是示例对话" |
| `personality` / `scenario` / `mes_example` | 留空——内容都在 `description` 与条目里，重复写会翻倍占 token |
| `first_mes` / `data.first_mes` | 见上表三条规则 |
| `data.character_book` | `{"name": "<世界名> 世界书", "entries": [...]}`，v2 形状 |
| `creator_notes` / `data.creator_notes` | 导入三步（见第六节）+ 全局设置推荐 + 版本 + `RP-Factory` |
| `system_prompt` | 项目档案「本文档对AI的核心指令」 |
| `post_history_instructions` | 留空 |
| `alternate_greetings` | `[]`；用户要备用开场才写 |
| `tags` / `data.tags` | 类型、基调、`rating` 各一个 |
| `creator` / `character_version` | `"RP-Factory"` / `"1.0"`（改一次设定加 0.1） |
| `spec` / `spec_version` | `"chara_card_v2"` / `"2.0"` |
| `data.extensions.world` | **必须等于 `character_book.name`**，默认 `"<世界名> 世界书"`。ST 导入内嵌书时按这个名字建世界，名字不一致就不会自动挂上 |
| `data.extensions.regex_scripts` | 阶段 5 / 6 的正则数组原样搬进来（见第七节） |
| `data.extensions.talkativeness` / `fav` / `depth_prompt` | `"0.5"` / `false` / `{prompt: "", depth: 4, role: "system"}` |
| `create_date` | `YYYY-MM-DD` |

顶层与 `data` 里同名字段都要填同一份内容：ST 读 `data`，但别的工具读顶层。

### 六、导入三步（`creator_notes` 与交付说明都写这三步）

1. 角色卡：`角色` 页 → 导入 → 选 `<世界名>.json`。
2. 弹「这张卡内嵌了世界书，要现在导入吗」→ **点 Yes**。ST 会按 `character_book.name` 建世界书并自动绑定（小地球变绿）。
3. 弹「这张卡内嵌了正则，是否允许角色专属正则」→ 点允许。没弹窗就 设置 → 扩展 → 正则 → 导入 `regex-*.json`。

然后 设置里打开「消息渲染」，回聊天，第一条消息应出现建卡向导。**没让我们自己建世界书、没让我们手动绑定**——如果交付说明里写了这两步，说明包做错了。

### 七、正则怎么带

- **卡内嵌**（默认）：`data.extensions.regex_scripts` = 阶段 5 / 6 的正则数组原样。内嵌那份的 `id` 用 ASCII（`rp-factory-opening-0` 这种），别用中文。
- **单独导入**：`regex-opening.json` / `regex-statusbar.json` 给人改完再导。两条路都写进交付说明，用户自己选。

### 八、文件放哪

```
最终产物/st/
  <世界名>.json                 # 卡 + 内嵌世界书 + 内嵌正则（主交付）
  regex-opening.json            # 有阶段 5 才有
  regex-statusbar.json          # 有阶段 6 才有
  开场前端.html / 状态栏前端.html  # 可选，方便改完再生成正则
  <世界名> 世界书.json            # 可选，用户要单独的世界书时才出
```

原生路线的 `最终产物/*.yaml` 原样保留，不走 `st/`。

## 写回契约

- `stages.7` → `done` / `skipped`（用户选原生路线就是 `skipped`，因为阶段 7 的产物是打包）。
- `delivery.route` → `native` / `st` / `both`；`delivery.st_name`、`delivery.files[]`（相对 `最终产物/st/`）。
- `artifacts` 追加 `st-card`（`path` = `最终产物/st/<世界名>.json`）；出了独立世界书再加 `st-worldbook`。
- `decisions` 记：路线、`first_mes` 来源、正则带法、条目清单（每人/每地一条还是合并）、`description` 字数。
- `hard_settings` 不动——打包不产生新设定；缺设定回对应阶段补，不在这一阶段现编。

## 导入并实测（用户答「要」才做）

三个脚本分工：`detect-sillytavern.py` 开局静默跑（找安装与实例）；`st-import.py` 导入并回读；`st-probe.js` 用无头 Chrome 打开酒馆点开卡，量界面高度。

```
python scripts/st-import.py --st auto --card "最终产物/st/<世界名>.json"
node scripts/st-probe.js --st http://127.0.0.1:8000 --char "<卡名>"
```

`st-import.py` 会做这几件事并逐条打印：导入（`preserved_name` = 卡名，同名覆盖旧卡）→ 回读 `/api/characters/all` → 比卡名 / 内嵌条目数 / 内嵌正则数 / `first_mes` 非空 / 首条标签能被正则接住 → 查 `character_allowed_regex` 白名单（不在名单里会 WARN：第一次进聊天酒馆会弹一次"是否允许角色专属正则"，点允许即可）。

`st-probe.js` 先找本机 Chrome（`--chrome` 可指定），打开 `--st` 地址、点侧栏里名字含 `--char` 的卡、等 6 秒，然后读第一条消息的 `iframe` 高度与 iframe 内文字：

- 高度 ≥60px 且 iframe 内有字 → 渲染成功。
- 没有 iframe → 正则没生效（插件没装 / 消息渲染关了 / 白名单没允许），按这三条说。
- iframe 只有 2px → 内联脚本语法错误，多半是 HTML 实体被解码，跑 `python scripts/validate-frontend.py <界面.html>` 看 F04。

**依赖**：`st-probe.js` 要 `npm i puppeteer-core`（只装驱动，不下载 Chromium）；没装就如实说"验不了渲染，文件与导入结果都在"，别假装测过。

**报告格式**（别贴长日志）：

```
导入：白潮（内嵌 15 条 / 正则 2 条）→ 已进 D:/AI/SillyTavern（1.19.0）
自检：卡名 / 条目数 / 正则数 / first_mes / 标签接正则  5 项 PASS
验收：建卡向导 iframe 674px，序章/基础身份/外观/总览 可点
一步要你做：第一次进聊天若弹"允许角色专属正则"，点允许。
```

## 退出

**跑校验器，别肉眼对：**

```
python scripts/validate-st-package.py "最终产物/st/<世界名>.json" --contract 创作痕迹/contract.yaml
python scripts/validate-contract.py 创作痕迹/contract.yaml
```

脚本在**本 skill 包**的 `scripts/` 下，不在用户项目里；当前目录不是包根时用脚本的绝对路径。出了独立世界书就再跟一个路径，脚本会顺带查两份是否同源。

退出码 0 才叫过；有 `FAIL` 就改到没有。它查的事：

1. 卡能解析；`spec == "chara_card_v2"`、`spec_version == "2.0"`；`data` 十四个必填字段齐全。
2. **卡里有 `data.character_book`，`entries` 非空，`name` 非空且 == `data.extensions.world`**。
3. 条目：`content` 非空、`keys` 是数组、`position` ∈ `before_char` / `after_char`、`insertion_order` 是数字、`enabled` 是布尔；常驻且无关键词（`constant: true` 且 `keys` 空）允许，反过来（非常驻且无关键词）失败。
4. `description` ≤8000 字（>6000 警告），且含 `contract.naming.axes` 的每个轴名。
5. 正文里 `【AI补全·可替换】` / `[待定` / `【未知】` 0 命中。
6. 每条 `findRegex` 能用 JS 编译（有 node 就实测）；用了 `$1` 却没捕获组 = 失败。
7. `first_mes` 里的标签能被某个正则接住；接不住 = 失败（第一楼会变裸标签）。
8. 卡名含 `/ \ : * ? " < > |` 会失败。
9. 常驻条目合计 ≤5000 字；关键词无跨条目重复；绿灯关键词 <8 / 未 `exclude_recursion` / 整词匹配 / `position` 2·3·5·6 / 关键词带逗号 / `order` 全同 / 绿灯 `selective: false` 按调优项给 W 或 FAIL。

还有三条肉眼过：

- `description` 里出现的势力名、地名、系统名、轴名，逐个能在 `contract.naming` 里找到。
- 交付说明三步齐全（导卡 → Yes → 允许正则），且没有"先导世界书再手动绑定"的旧步骤。
- 每个角色的名字都在某条目的 `keys` 里；每个地点也都在。缺一个，那个角色被提及时就不会加载设定。

只要粘贴版（用户明确说"别写文件"）→ 一个 JSON 代码块给全（内嵌世界书与正则都在里面），路径写进契约但标 `pending: 未落盘`。

用户答「要，帮我导并测」→ 按上一节跑完 `st-import.py` 与（有界面时）`st-probe.js`，把结论报出来才算收尾；答「不用」→ 四句话交代清楚即可。
