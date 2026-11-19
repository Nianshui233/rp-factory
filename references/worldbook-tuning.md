# 世界书怎么调

阶段 7 出包时按这份文件定参数。规则来自 SillyTavern 官方 World Info 文档与本机 `public/scripts/world-info.js` 的实现，凡与"社区习惯"冲突，以实现为准。

## 一、三个灯

| 灯 | 字段 | 行为 |
|---|---|---|
| 🔵 蓝 | `constant: true` | 不看关键词，每轮都插 |
| 🟢 绿 | `constant: false` + `selective: true` | 主关键词命中才插；配 `keysecondary` 时再按 `selectiveLogic` 判一轮 |
| 🔗 链 | `vectorized: true` | 允许被 embedding 相似度激活（需装 Vector Storage） |

本包只用蓝与绿。链的问题不是"不先进"，是**错触发方向错了**：语义相近却指错人，AI 会照着 A 的设定演 B，且很难发现。绿的关键词漏了是召回不足，加词就补回来了。

## 二、参数套餐

出包时按条目类型直接套，不要每条现想：

| 条目类型 | `constant` | `order` | `position` | `depth` | `excludeRecursion` | 关键词 |
|---|---|---|---|---|---|---|
| 骨架 / 常驻规则 | `true` | 95–100 | `0` | `4` | `false` | `[]` |
| 实体细节（势力 / 地点 / 系统） | `false` | 70–90 | `0` | `4` | **`true`** | 8–15 个 |
| 状态栏协议 | `true` | 70 | `4` | `2` | `false` | `[]` |
| 隐藏信息（防剧透） | `true` | 85 | `4` | `2` | `false` | `[]` |

其余字段一律：`selective: true`、`selectiveLogic: 0`（AND_ANY）、`probability: 100`、`useProbability: true`、`matchWholeWords: false`、`caseSensitive: null`、`disable: false`、`group: ""`、`groupWeight: 100`。

- `excludeRecursion: true` 只给关键词条目：常驻条目的正文里会点名一堆势力与地点，递归一开就会被它们顺次点亮，等于把关键词条目变成半个常驻。参考实现（`我，非我` 世界书 22 条）全书如此。
- `matchWholeWords: false` 要显式写。官方文档写"默认开启"，本机默认是 `false`；中文没有空格分词，开整词匹配只会更难命中。
- `depth` 只在 `position: 4` 时有意义，别的值填了也不读。

## 三、关键词

**每条绿灯条目 8–15 个**，宁宽勿漏。五个来源各取几个：

1. 本名 / 别名 / 绰号 / 译名（`守夜所`、`灯所`）
2. 关系性指代（`次席`、`老邵的上司`）
3. 场景指代（`巡堤`、`点灯`、`堤线`）
4. 同义与口语（`熄灯`、`断火`）
5. 跨场景关联词（`盐票`、`灯芯配额`）

规则：

- **纯文本关键词不支持逗号**——逗号是分隔符，想匹配带逗号的串只能用正则。
- 正则关键词写成 `/.../flags`，与普通关键词混排、并列生效：`/(?:守夜所|灯所)/i`。多词、可选词、中文标点都靠它。
- 别用标题词当关键词（`白潮的秘密`、`势力介绍`）——聊天里没人这么说。要按"这条内容会在什么对话里被需要"反推。
- 关键词只是索引：**条目标题与关键词都不进上下文**，所以正文必须自己站得住，别写"如上所述"。

## 四、插入位置

| `position` | 含义 | 什么时候用 |
|---|---|---|
| `0` | 角色定义之前（Before Char Defs） | 默认。世界、规则、势力、地点 |
| `1` | 角色定义之后（After Char Defs） | 需要压过角色卡时（世界规则与角色设定冲突） |
| `4` | 按深度插入 `depth` 条消息之上 | 状态栏协议、当轮临时状态；`depth: 0` = 提示词最底 |
| `5` / `6` | 示例消息前 / 后 | ⚠️ 会被**解析成示例对话**，不要拿来放设定 |
| `2` / `3` | 作者注顶 / 底 | ⚠️ 作者注关闭（Insertion Frequency 0）时整条被忽略 |
| `7` | Outlet，不自动插 | 想手动用 `{{outlet::名字}}` 指定位置；`outletName` 空 = 直接跳过 |

## 五、顺序与预算

- `order` 越大 → 插得越靠后 → 对输出影响越大。多个条目同轮激活时按它排。
- 预算默认 **25%（Context %）**，也可切成绝对 token。预算用完，剩下的条目就算命中也不插。
- 插入优先级：常驻 → 直接命中关键词的 → 被递归带出来的。所以常驻条目一多，关键词条目会被挤掉。
- 常驻条目合计 ≤5000 字是本包的预算线（校验器 W09）。超了就把可省段落改成关键词条目。

## 六、全局激活设置（交付时给用户这张表）

| 设置 | 推荐 | 本机默认 | 说明 |
|---|---|---|---|
| Scan Depth | 2–4 | `2` | 太大等于把旧设定反复塞进来 |
| Context % / Budget | 25% | `25` | 不够再调；先调关键词 |
| Recursive Scan | 关 | `false` | 本包条目之间靠常驻 + 关键词覆盖，不靠递归 |
| Min Activations | `0` | `0` | 与 Max Recursion Steps 互斥 |
| Max Recursion Steps | `0` | `0` | 开了递归才有效 |
| Include Names | 开 | `true` | 名字进扫描缓冲，才能用名字当关键词 |
| Case Sensitive | 关 | `false` | 中文无大小写，无影响 |
| Match Whole Words | **关** | `false` | 中文必须关（见第二节） |
| Use Group Scoring | 关 | `false` | 开了 inclusion group 才需要 |
| Alert on Overflow | 开 | `false` | 预算爆了要能立刻知道 |
| Lore Insertion Strategy | Character Lore First | `character_first` | 卡绑的书优先于全局书 |

## 七、递归：想用才用

条目正文提到别条关键词 → 那条会被一起插进来。这是唯一"不写关键词也能带出设定"的机制。

- 想要它：给"事件"条写正文时故意点出关联实体（`伏击者为湖心教团` 会带出教团条目）。
- 不想要它：给每条绿灯设 `excludeRecursion: true`（本包默认），并且别开全局 Recursive Scan。
- `preventRecursion: true` 是反向锁：这条被激活后不许再触发别人。适合"大段规则"这类最容易漏出关键词的条目。
- `delayUntilRecursion` 让条目只在递归轮次命中，用来做"第二层真相"。

## 八、随机与互斥

- `probability < 100`：命中后仍按概率决定插不插。做天气、谣言、随机事件。
- `group` 同名的多条同时命中，只插一条（按 `groupWeight` 抽）；一个条目可属于多个组（逗号分隔）。
- `useGroupScoring: true` → 命中关键词多的优先；`prioritizeInclusion: true` → 直接取 `order` 最大的那条，不抽签。
- 用法：`天气` 组里放"晴/雨/盐雾"三条，各 33 权重；`谣言` 组同理。

## 九、时间效果

单位是**消息条数**，`0` = 无效。

- `sticky: N` — 激活后再常驻 N 条，期间忽略概率。
- `cooldown: N` — 激活后 N 条内不再激活（可与 sticky 叠加：sticky 结束后进冷却）。
- `delay: N` — 聊天至少 N 条才可能激活（`delay: 1` = 开局那条不算）。

用法：一次性的"潮水已漫过堤线"用 `sticky: 3`；"第一夜之后才会出现的传闻"用 `delay: 10`。

## 十、附加匹配源与绑卡

- 附加匹配源（`matchCharacterDescription` / `matchCharacterPersonality` / `matchScenario` / `matchPersonaDescription` / `matchCharacterDepthPrompt` / `matchCreatorNotes`）让条目能被"卡里写的字"点亮，不用等聊天里出现。适合跨卡共用的世界观书。
- `characterFilter.names` 精确绑卡名，`characterFilter.tags` 按标签绑一组；`exclude` 模式反转。
- 绑定顺序：角色管理面板的 🌐 按钮选一本 = 主世界书，**只有主本随卡导出**；`Shift`+点或 `More… → Link World Info` 加挂的不会导出。
- 改名世界书时 ST 会提示重新链接所有引用它的角色，**选是**，否则绑定静默失效。
- 群聊的全局世界书**只能挂一本**——所有共享设定要合进同一本。

## 十一、出包前十条自查

1. 每条绿灯 8–15 个关键词？关键词是聊天里真会出现的词？
2. 常驻是否只装了"不常驻就演错"的东西（规则、常识、约束）？
3. 关键词条目是否都 `excludeRecursion: true`？
4. `matchWholeWords` 是否显式 `false`？
5. `position` 有没有误用 2 / 3（作者注）或 5 / 6（示例消息）？
6. `position: 4` 的条目是否都写了数字 `depth`？
7. `order` 是否分了三档（95–100 / 70–90 / 70）而不是全 100？
8. 常驻合计字数是否 ≤5000？单条正文是否 ≤1000 字（超了拆条）？
9. 需要随机或互斥的条目，是否用了 `probability` / `group` 而不是写死在正文里？
10. 交付说明里是否给了第六节那张全局设置表？
