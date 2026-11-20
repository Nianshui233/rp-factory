# 阶段 7 · 交付

产物 type：`st-card` / `st-regex` / `st-worldbook`（只有 SillyTavern 路线才产）。骨架：`templates/st-card.json`、`templates/regex-frontend.json`、`templates/st-worldbook.json`。

**这是最后一个阶段。** 前面所有阶段都跑完之后才进；用户中途说"打包"就先补完或明确跳过，不能拿半成品打包。

## 进入条件

- `project.stages_requested` 里的阶段都已 `done`（有 `partial` 就先问一句"还差 X，先打包还是补完"）。
- 要出酒馆包，必须有 `rolecard` 与 `world-bible`；缺任一个就只能走原生产物，或先回阶段 1 / 2。
- 阶段 `opening` / `statusbar` 没做也能打包：只是正则那一件少脚本，第一楼是纯文字开场。
- 做了 `mvu` → 卡里要带 `data.extensions.tavern_helper.scripts`（MVU 加载器 + 变量结构），`正则.json` 要带隐藏 `<UpdateVariable>` 的两条；交付说明里多一句"进酒馆助手把这两个脚本启用"。**不带脚本的 MVU 包等于没做变量系统**，而且不会报错。
- **`导入包/` 此刻应该是空的**。里面有任何东西（HTML、正则、卡）都是流程跑错了，先把它们挪回 `制作文件/产物/` 再进本阶段。

## 追问

**两问，按顺序。第一问路线，第二问要不要我动手导入。**

**问一（路线）三选项：**

| 选项 | 交出什么 | 谁用 |
|---|---|---|
| **原生产物**（默认） | 把 `制作文件/产物/` 里的 YAML + HTML 复制进 `导入包/` | 自己留着改、喂给别的 AI、当代稿 |
| **SillyTavern 三件套** | `<世界名>（纯净）.json` + `正则.json` + `<世界名> 世界书.json`，用户自己装配 | 想在酒馆里跑 |
| **两者都要** | 上面两份都留 | 想改又想在酒馆里跑 |

三件套是**分开的三份**，各自单独导入、由用户自己组合。不做单文件内嵌卡——那种卡改一处要重新导一次整卡，世界书和正则也没法单独迭代。

不问的：文件叫什么（默认 = `project.name`）、放哪（就是 `导入包/`）、要不要头像（不生成图片）、导入顺序（说明里给）。用户主动要别的名字时照填。

**问二（只在答案含酒馆包时问）：要不要我直接导进你正在跑的酒馆，并当场验一遍。**

| 选择 | 我做什么 | 交出什么 |
|---|---|---|
| **要，帮我导并测** | 先跑交付门校验器，再 `python scripts/st-import.py --st auto --pkg <三件套目录>`（逐件导入：卡 / 世界书 / 正则），有界面再 `node scripts/st-probe.js --char <卡名>` 量 iframe 高度 | 一行结论 + 逐项 PASS/WARN；没成就把卡在哪一步说清 |
| **不用，给我文件** | 只跑校验器与肉眼三条 | 文件 + 四句话（装配四步、渲染开关、世界书挂哪、触发词该出现在哪条消息） |

不问第二问的两种情况：`project.sillytavern` 是 `null`（没装）、或 `running_url` 是空（装了没在跑）。这时只说一句"现在没有在跑的实例，启动后要我导也说一声"，然后把文件交出去。

用户答"要"之后，若导入失败（版本太旧、端口不对、权限不足），**不要自己换地址重试到成功为止**：报一次实际错误，把可用地址与文件位置给用户，让他决定。

## 判断标准

- **三件各管一件事**：卡只装"每轮都要在的骨架"，世界书装"按需加载的细节"，正则装"把标签渲染成界面"。同一段话只在一处出现。
- **卡是纯净的**：`data.character_book` 不写，`data.extensions.regex_scripts` 写空数组。**唯一例外**是 `mvu` 阶段的 `extensions.tavern_helper.scripts`——它不是世界书也不是正则，是脚本本体，必须跟着卡走（或者单独发 `酒馆助手脚本-*.json`，两者选一，别都做）。卡里塞内嵌书会让"改一条设定"变成"重导整卡"，用户也没法单独换世界书。
- **世界书名三处一致**：`<世界名> 世界书.json` 的**文件名** = 酒馆里的书名（导入时用文件名建书）；卡里 `data.extensions.world` 写同一个名字。名字不一致，卡导进去后不会自动挂上书。
- **第一楼不是裸标签**：`first_mes` 里的标签必须能被 `正则.json` 里某个 `findRegex` 接住；接不住就把 `first_mes` 换成一句普通开场白。
- **界面看 DOM，不看消息文本**：`first_mes` 存的就是六个字 `<建卡向导>`，替换在显示层发生。所以"消息里只有标签"可能失败也可能正常——判据是那一楼有没有 iframe/控件、控制台有无报错。出来时 `TH-render` + iframe≈674px（`srcdoc` 约 1.9 万字），出不来时 iframe=0 且**毫无报错**（S-28）。
- **内容有预算**：`description` ≤8000 字（校验器 X01 盯着）。群像卡的主要篇幅在人物条目里，不在 `description`。
- **名字与契约一致**：卡名 = `delivery.st_name` = 卡文件名（不含"（纯净）"）；世界书名 = 书文件名 = `extensions.world`。

## 生成

### 一、先定三件事（内部决定，不问）

| 值 | 取法 |
|---|---|
| `st_name` | `project.name`（未命名项目时用 `未命名项目`） |
| `first_mes` | 阶段 5 做向导 → `<建卡向导>`；做面板 → `<开局界面>` 加九字段数据块；没做前端 → 用场景卡 `概览` 与 `边界` 写一句 ≤120 字开场（含 `{{user}}`） |
| 条目清单 | 按下面第三节的切法表切 |

### 二、卡里装什么（`<世界名>（纯净）.json`）

| 字段 | 写什么 |
|---|---|
| `name` / `data.name` | `st_name` |
| `description` / `data.description` | 世界骨架：一句话世界 + 怎么玩 + `世界怎么运转` 的 AI 职责与自发动静 + 红线（`变更边界.硬设定`）+ **住户索引**（每人一行：名字·住处·身份·命门）+ **地点索引**（每地一行）+ **两轴读法**（轴名、范围、初始、每级一句话）+ 结尾一句"以上是设定，不是示例对话" |
| `personality` / `scenario` / `mes_example` | 留空——内容在 `description` 与世界书里，重复写只是翻倍占 token |
| `first_mes` / `data.first_mes` | 见上表三条规则 |
| `creator_notes` | 装配四步（见第五节）+ 全局设置推荐 + 版本 + `RP-Factory` |
| `system_prompt` | 项目档案「本文档对AI的核心指令」原文（`hard_settings` 里那条） |
| `post_history_instructions` | 留空 |
| `alternate_greetings` | `[]`；用户要备用开场才写 |
| `tags` / `data.tags` | 类型、基调、`rating` 各一个 |
| `creator` / `character_version` | `"RP-Factory"` / `"1.0"`（改一次设定加 0.1） |
| `spec` / `spec_version` | `"chara_card_v2"` / `"2.0"` |
| `data.extensions.world` | `<世界名> 世界书`——与世界书文件名逐字一致 |
| `data.extensions.regex_scripts` | `[]`（正则单独一份，不内嵌） |
| `data.extensions.talkativeness` / `fav` / `depth_prompt` | `"0.5"` / `false` / `{prompt: "", depth: 4, role: "system"}` |
| `create_date` | `YYYY-MM-DD` |

**默认不写 `character_book`**，书单独一份、靠 `extensions.world` 同名挂上。要给用户单文件交付时才启用第二入口：

```bash
python scripts/embed-book.py --card "<世界名>（纯净）.json" --book "<世界名> 世界书.json"     --name "<世界名> 世界书" --out "<世界名>（内嵌书）.json"
```

脚本把 native 条目反向映射成 v2 `character_book`（`keys`/`secondary_keys`/`insertion_order`/`enabled`，位置完整值放 `extensions.position`——ST 只认这条，见 `references/st-correctness.md` S-15），顶层与 `data` 各写一份，然后**回读比对**：自己复刻一遍 `convertCharacterBook`，逐字段核对，有任何字段 ST 不认就报出来（退出码 1）。三个必须交底的代价：

1. 导入后书名叫 `character_book.name`（缺省才是 `<角色名>'s Lorebook`），**必须与 `extensions.world` 逐字一致**，否则书落成另一个名字、一条都不激活（S-29；书已存在时连提示都不弹，S-24）。
2. 卡在世界书未选的状态下保存，ST 会删掉 `data.character_book`（S-16）。导入完必须把书选上再存。

顶层与 `data` 里同名字段都填同一份内容：ST 读 `data`，别的工具读顶层。

### 三、世界书装什么（`<世界名> 世界书.json`）

形状是 native：`{"entries": {"0": {...}, "1": {...}}}`，键是字符串序号，条目 42 个字段见 `templates/st-worldbook.json`。**不要写成 `entries` 数组**（那是卡内 v2 形状，导进世界书面板参数会全丢）。

**参数怎么定、关键词怎么备、位置怎么选，一律看 `references/worldbook-tuning.md`**——那份是"调好"的部分（三灯、套餐、关键词、位置、递归、全局设置、十二条自查），这里只管"切哪几块"。

| 来源 | 条数 | `constant` | `order` | `position` | `key` |
|---|---|---|---|---|---|
| 世界规则 / 这栋楼的默契 / 变更边界 / 世界怎么运转 / AI即兴约束 | 3–6 条，各一条 | `true` | 100–94 | `0` | `[]` |
| 信息分层（防剧透） | 1 | `true` | 85 | `4` + `depth: 2` | `[]` |
| 数值与判定 | 1 | `true` | 84 | `4` + `depth: 2` | `[]` |
| 文本状态栏协议（仅标签路径） | 1 | `true` | 70 | `4` + `depth: 0` | `[]` |
| **每个角色**（`制作文件/产物/rolecard/*.yaml`） | 每人 1 条 | `false` | 80–78 | `0` | 本名 + `alias[]` + 关系指代 + 绰号（8–15 个） |
| **每个地点**（`制作文件/产物/scene/…` 或 scene-sheet） | 每地点 1 条 | `false` | 76–74 | `0` | 地点名 + 区域名 + 场景指代（8–15 个） |
| 势力 / 时间线 / 常识 / 名词 | 各 1 条 | `false` | 88–82 | `0` | `factions[].name` + `alias[]` |

规矩：

- **一个 key 只归一条**：同一个名字出现在两条里，那个名字就失去判别力。切完扫一遍重复。
- **人物条目写什么**：该卡的 `psychology` + `behavior` + `attitudes` + `speech`（删掉 `identity.appearance` 以外的外貌细节、删 `nsfw` 块——`nsfw` 分档留一份在「数值与判定」条目里写）。`content` 用 YAML 片段，键名保留。
- **地点条目写什么**：`概览` + `空间结构` + `关键区域.现场可见` + `出入口与安防` 的可判定物。这是"客厅只有一张长沙发""卫生间只有一个"能进上下文的唯一通道。
- **数值与判定条目写什么**：每条轴的 `range` / `initial` / `direction` / 各级 `label` 与 `behavioral_signs`（每级压成一句）+ `calc_mod` + `evaluation_order` + `anti_exploit`；多目标轴（`targets[]`）把每人一行初始值列在末尾。**没有这一条，数值系统在角色扮演里等于不存在。**
- 常驻条目总字数 ≤8000（校验器 X02），单条 ≤1000 字，超了拆条；`未决事项` 不进世界书（它是台账，留在 `制作文件/`）。
- 每个角色的名字、每个地点的名字都必须在某条的 `key` 里，否则被提及时不加载。
- `uid` == 键序号，`displayIndex` 同值；`excludeRecursion: true`（绿灯关键词别在递归里反复展开）。

### 四、正则装什么（`正则.json`）

一个 **数组**，一条正则一个对象，字段见 `templates/regex-frontend.json`（单对象文件也能导）。

- 阶段 5 有 → 一条：`scriptName` 带"建卡向导"，`findRegex` 只匹配标签（`/<建卡向导>/g`），`placement: [2]`（AI 输出）、`markdownOnly: true`、`runOnEdit: true`。
- 有 MVU：隐藏更新块的提示词与显示规则均启用。有变量状态栏就保留挂载标签；无面板时可用空替换隐藏它。
- 有状态栏：MVU 路径匹配 `<StatusPlaceHolderImpl/>`，替换成读取本楼 stat_data 的界面；文本路径匹配项目标签，按选定的数据路径配置捕获组。
- `replaceString` 的 HTML 用 `templates/wizard-ui.html` / `templates/statusbar.html` 填，改完留到收尾一检，不在这里单独跑。
- 内联脚本里需要 HTML 实体时用 `\u0026` 拼（`'\u0026amp;'`）——酒馆会把消息里的实体再解一次码，写 `&amp;` 会让脚本语法错误、界面塌成 2px。

### 五、装配四步（写进 `creator_notes`，也是交付说明里的四句话）

1. **世界书**：世界书面板 → 导入 → 选 `<世界名> 世界书.json`。**文件名就是书名**（改文件名 = 换书名）。
2. **角色卡**：角色页 → 导入 → 选 `<世界名>（纯净）.json`。导完在卡片设置里把世界书选成 `<世界名> 世界书`（卡里已写 `extensions.world`，同名时自动挂上，小地球会变绿）。
3. **正则**：设置 → 扩展 → 正则 → 导入 → 选 `正则.json`。导入时问"导入为全局 / 角色专属 / 预设"，选**全局**（不用白名单）。这一件必须界面点，脚本写 `settings.json` 会被运行中的客户端盖掉。
4. **渲染**：设置 → 扩展 → 酒馆助手 → 打开"消息渲染"（`render.enabled`）。回聊天，第一条消息应出现建卡向导。
5. **脚本**（只有做了 `mvu`）：酒馆助手 → 脚本库 → 把卡里的两条脚本**启用**（`script.enabled.characters` 要包含这个卡）。不启用时 MVU 静默不跑，变量永远是初值。

### 六、文件放哪

**`导入包/` 在选定路线之前必须是空的**——过程产物一律在 `制作文件/` 里，交付时才复制过来：

```
<项目>/制作文件/产物/            # 运行期的终稿，一直在这
  world-bible.yaml · rolecard/*.yaml · scene/*.yaml · axis/*.yaml
  opening-ui.html · regex-opening.json（草稿）· statusbar-ui.html

<项目>/导入包/                 # 交付前：空；选定路线后才有内容
  # 路线 = st
  <世界名>（纯净）.json
  正则.json
  <世界名> 世界书.json
  # 路线 = native → 把 制作文件/产物/ 的树原样复制过来（YAML + HTML）
  # 路线 = both → 上面两套都在
```

复制用 `cp -r`，别移动：`制作文件/产物/` 是唯一可回溯的源，丢了就没法重出。

## 写回契约

- `stages.7` → `done` / `skipped`（用户选纯原生路线时也 `done`——交付这一刻确实发生了；`skipped` 只在没做交付时用）。
- `delivery.route` → `native` / `st` / `both`；`delivery.st_name`；`delivery.files[]` 写**相对 `导入包/`** 的文件名（`白潮（纯净）.json`、`正则.json`、`白潮 世界书.json`）。
- `artifacts` 追加三条：`st-card`（`path` = `导入包/白潮（纯净）.json`）、`st-regex`、`st-worldbook`。
- `decisions` 记：路线、`first_mes` 来源、条目清单（每人/每地一条还是合并）、`description` 字数、世界书名。
- `hard_settings` 不动——打包不产生新设定；缺设定回对应阶段补，不在这一阶段现编。

## 导入并实测（用户答「要」才做）

三个脚本分工：`detect-sillytavern.py` 开局静默跑（找安装与实例）；`st-import.py` 逐件导入并回读；`st-probe.js` 用无头 Chrome 打开酒馆点开卡，量界面高度。

```
python scripts/st-import.py --st auto --pkg "导入包"
node scripts/st-probe.js --st http://127.0.0.1:8000 --char "<卡名>"
```

`st-import.py --pkg <目录>` 认三件套并逐件处理：

1. 卡：`POST /api/characters/import`（`preserved_name` = 卡名，同名覆盖旧卡），回读 `/api/characters/all` 比卡名 / `first_mes` / `extensions.world`。
2. 世界书：`POST /api/worldinfo/import`（字段名 `avatar`，**文件名即书名**），回读 `/api/worldinfo/get` 比条目数、常驻字数。
3. 正则：**只校验，不动设置**（`scriptName` / `findRegex` 齐不齐、`node --eval "new RegExp(...)"` 能不能编译、用了 `$1` 有没有捕获组），然后交代用户自己去界面导。

**为什么正则不能脚本代劳**：运行中的酒馆是**客户端**持有 `extension_settings`。脚本 `POST /api/settings/save` 写进去 2 条，磁盘上能查到；但页面一刷新、或客户端下一次自动保存，就用内存里的旧数组把文件盖回去了——实测写完再打开一次角色卡，磁盘又变回 0 条。所以这一件只能界面导（`扩展 → 正则 → 导入`，选数组文件会一次导完），或者等酒馆关掉再改 `settings.json`。**不要**对用户说"正则已经导好了"。

`st-probe.js` 先找本机 Chrome（`--chrome` 可指定），打开 `--st` 地址、点侧栏里名字含 `--char` 的卡、等 6 秒，读第一条消息的 `iframe` 高度与 iframe 内文字：

- 高度 ≥60px 且 iframe 内有字 → 渲染成功。
- 没有 iframe → 正则没生效（插件没装 / 消息渲染关了 / 正则没导入），按这三条说。
- iframe 只有 2px → 内联脚本语法错误，多半是 HTML 实体被解码，跑 `python scripts/validate-frontend.py <界面.html>` 看 F04。

**依赖**：`st-probe.js` 要 `npm i puppeteer-core`（只装驱动，不下载 Chromium）；没装就如实说"验不了渲染，文件与导入结果都在"，别假装测过。

**报告格式**（别贴长日志）：

```
导入：白潮（卡 1 / 世界书 15 条）→ 已进 D:/AI/SillyTavern（1.19.0）
自检：卡名 · first_mes · extensions.world · 书条目数 · 常驻字数 · 正则文件可导入   6 项 PASS
验收：建卡向导 iframe 674px，序章/基础身份/外观/总览 可点
要你做两步：① 设置 → 扩展 → 正则 → 导入 `正则.json`（选全局）；② 进聊天若弹"允许角色专属正则"，点允许。
```

## 试演（用户说「能用」之前）

导入成功只证明「机器能看到界面」。要判断「跑起来像不像」，按 `references/rehearsal.md` 跑试演：≤5 轮、每轮一个症状（R1 代演玩家 / R2 OOC / R3 口癖漂移 / R4 数值闸门）、只改一处并记进 `制作文件/试演日志.yaml`。**禁止整卡重写**——那会把已过校验的合规结构一起冲掉。结论记 L5/L6（`by: human`）。

## 退出

**跑校验器，别肉眼对：**

```
python scripts/check-stage.py delivery <项目根>
```

它内部先跑 `validate-contract.py` 再跑 `validate-st-package.py`（想看单条输出也可以单独跑这两个，但判定以这一条命令为准）。

脚本在**本 skill 包**的 `scripts/` 下，不在用户项目里；当前目录不是包根时用绝对路径。第一个参数给 `导入包/`（也接受单给某个文件）。退出码 0 才叫过。它查的事：

1. **三件都在、不多不少**：`<世界名>（纯净）.json`、`正则.json`、`<世界名> 世界书.json`。
2. 卡：`spec == "chara_card_v2"`、`spec_version == "2.0"`、`data` 十四必填字段齐全；**不许有 `character_book`（C19）**；`data.extensions.regex_scripts` 必须为空（C20）；`extensions.world` 非空（C21）。
3. 书：`entries` 是**对象**不是数组（W01）；每条 `uid` == 键、`content` 非空、`key` 是数组、`position` ∈ 0–7、`order` 是数字、`disable` 是布尔；非常驻且无 `key` = 失败；常驻合计 ≤8000（X02）。
4. 正则：数组（R01）；每条 `scriptName` 非空、`findRegex` 能被 JS 编译（有 node 就实测）、`placement` 数组、`markdownOnly: true`；用了 `$1` 却没捕获组 = 失败。
5. 交叉：`extensions.world` == 世界书文件名（去 `.json`）（X03）；做了 `mvu` 时卡里必须有 `tavern_helper.scripts` 且正则里有隐藏更新块的规则（X06）；`first_mes` 里的标签能被某条正则接住（X04）；三件的占位符 0 命中（X05）。
6. 调优：绿灯关键词 <8、未 `excludeRecursion`、`position` 2·3·5·6、`key` 带逗号、`order` 全同、`selective: false` 给 WARN；常驻字数只打印不判定（`W09`）。

还有四条肉眼过：

- `description` 里出现的势力名、地名、系统名、轴名，逐个能在 `contract.naming` 里找到。
- 装配四步齐全（书 → 卡 → 正则 → 渲染开关），且没写"手动建世界书"。
- **进聊天后那条消息真的有界面**（能点，不是六个字符）。卡里带正则时（违反纯净，C10 会报）必须先点「允许角色专属正则」；`AlertRegex_<头像>` 只弹一次，点过取消就永久不弹（S-28）。
- 每个角色的名字都在某条的 `key` 里；每个地点也是。缺一个，那个角色被提及时就不会加载设定。

只要粘贴版（用户明确说"别写文件"）→ 三个代码块给全（卡 / 正则 / 书），路径写进契约但标 `pending: 未落盘`。

用户答「要，帮我导并测」→ 按上一节跑完 `st-import.py` 与（有界面时）`st-probe.js`，把结论报出来才算收尾；答「不用」→ 四句话交代清楚即可。
