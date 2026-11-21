# 世界书引擎：一条条目是怎么被选中、又怎么被塞进 prompt 的

这份文件讲机制，不讲配方。出包怎么填参数看 `references/worldbook-tuning.md`；正文写什么看 `references/worldbook-writing.md`。

**不进任何阶段的加载表**——排障、写新机制、或用户问"为什么这条没触发"的时候再读。

所有行号对应本机 `D:/AI/SillyTavern`，ST 1.19.0。

## 零、一句话版本

世界书不是数据库查询，是**每轮对最近 N 条消息做一次全文匹配**：命中的条目按 `order` 排好队，从上往下装，装到预算用完就停，剩下的就算命中也不插。没有"优先级最高的先插"这回事，只有"排在前面的先装"。

## 一、扫描缓冲：模型到底"看"了哪些字

`WorldInfoBuffer`（`public/scripts/world-info.js:5271` 附近）取 `depthBuffer.slice(startDepth, depth)`，即**从最新一条往前数 `scanDepth` 条消息**。

- `world_info_depth = 2`（`:68`）——单位是**消息条数**，不是"轮"也不是"对话对"。`2` 覆盖「你最新一句 + 角色上一句」。
- `scanDepth: 0` 的条目**只吃递归与作者注**，不吃聊天内容。想让它纯常驻就别写 `scanDepth: 0` 之外的怪值。
- `world_info_include_names = true`（`:74`）时，缓冲区里每条消息前面加 `名字: `（`public/script.js:4624`：`world_info_include_names ? \`${x.name}: ${x.mes}\` : x.mes`）。**所以"名字当关键词"只在最近 N 条消息里、且是发言者时才生效**。关掉它，正文里出现的名字仍然能被匹配，但"某人在说话"这个信号就没了。
- `case_sensitive`（`:76`）与 `match_whole_words`（`:84`）默认都关；中文没有空格分词，`matchWholeWords: true` 只会让命中变难。
- 读哪几本：`insertion_strategy`（`:27`）= 角色书优先（默认）/ 全局书优先 / 均匀。它只决定**多本书拼起来的遍历顺序**，压不过 `order` 与 `position`。

## 二、激活判定：逐条短路，顺序是固定的

主线在 `checkWorldInfo`（`:4709`），`while (scanState)` 最多跑 `max_recursion_steps` 轮（`0` = 不限）。每条按这个顺序短路：

```
disable → triggers → characterFilter(names/tags) → sticky/cooldown/delay
        → delayUntilRecursion(层级) → excludeRecursion(仅递归轮)
        → 装饰器(@@) → constant → sticky 残留 → 主关键词 → 次关键词(selectiveLogic)
```

四档 `selectiveLogic`（`:33`）：`AND_ANY` / `NOT_ALL` / `NOT_ANY` / `AND_ALL`。本包一律 `AND_ANY`。

`constant: true` 走到这一步就命中，**不看关键词、也不看扫描缓冲**——所以常驻条目放进来的东西，与最近聊了什么无关。

## 三、排序：sticky 优先，然后 order

本轮命中的条目排序在 `:4993`–`:5008`：

```js
return isBSticky - isASticky
    || (sortedEntriesIndex.get(a) ?? -1) - (sortedEntriesIndex.get(b) ?? -1);
```

`sortedEntriesIndex` 来自 `getSortedEntries()`（`:4590`），最终按 `sortFn = (a, b) => b.order - a.order`（`:87`）。

结论：**同轮命中里，sticky 的排最前，其余按 `order` 从大到小**。没有"常数优先于关键词"，也没有"直接命中优先于递归带出"——常数条目之所以先装，是因为我们习惯给它高 `order`。

## 四、预算：算得出来，而且默认不报警

```
budget = Math.round(world_info_budget * maxContext / 100) || 1     // :4736
if (world_info_budget_cap > 0 && budget > world_info_budget_cap) budget = world_info_budget_cap;  // :4738
```

- `world_info_budget = 25`（`:73`）是**百分比**；`world_info_budget > 100` 会被强制改回 25（`:946`）。
- `budget_cap = 0`（`:81`）= 不封顶。于是 `Context % = 100` 意味着**预算等于整个上下文**。
- 装填循环（`:5061`）：`textToScanTokens + newContent >= budget` 时 `continue` ——**这条被跳过，后面的继续试**；同时置 `token_budget_overflowed = true`，**递归也随之停**（`:5097`）。
- `ignoreBudget: true` 的条目不受此限（`:5039` 附近）。
- `world_info_overflow_alert = false`（`:75`）是默认值：**溢出只会进 console，界面上什么都不说**。这是全引擎最贵的一个默认值——"AI 突然忘了前文"经常就是这里。

## 五、组装：同位置内 order 越大越靠下

`:5206` 起：

```js
[...allActivatedEntries.values()].sort(sortFn).forEach(entry => { ... unshift ... });
```

按 order 从大到小取，逐条 `unshift` 进各自位置桶 → **同一个 `position` 内最终是 order 升序**，order 越大越靠近上下文底部、影响越强。atDepth 按 `(depth, role)` 分组，`depth ?? DEFAULT_DEPTH(=4)`（`:100`），`role ?? extension_prompt_roles.SYSTEM`。

位置枚举（`:855`）：`0` 角色定义前 / `1` 后 / `2` 作者注前 / `3` 作者注后 / `4` atDepth / `5` `6` 示例消息前·后（**会被当示例对话解析**）/ `7` outlet。

## 六、递归：全局开关 + 每条三个字段

递归是**全局设置**（`world_info_recursive`，默认 `false`），不存在于书文件里。书里只能写每条：

| 字段 | 作用 |
|---|---|
| `excludeRecursion` | 不能被别的条目拉进来（递归轮里直接跳过） |
| `preventRecursion` | 这条被激活后，不许再拿它的正文去拉别人 |
| `delayUntilRecursion` | 只在第 N 层递归才可能命中（做"第二层真相"） |

官方最小例子：`贝西` 条正文写「贝西是一头奶牛，和鲁弗斯是朋友」→ 开递归时带出关键词为 `鲁弗斯` 的那条。

**扇出是真的会发生的**（实测本机参考库）：`尸变纪元` 46 条启用条目里有 58 条"正文提到别人的关键词"的边；`我，非我` 21 条里有 62 条。后者只给 11/22 写了 `excludeRecursion`——因为作者默认用户不会开递归。**递归开着而 `excludeRecursion` 没写满，就是一份会雪崩的书。**

## 七、`@` 装饰器：写在正文开头会被吃掉

`parseDecorators`（`:4655`）看 content 开头：`@@activate` 强制激活、`@@dont_activate` 强制不激活、`@@@` 是转义（真想要正文以 `@@` 开头才用它）。`comment` 上限 `MAX_COMMENT_LENGTH = 100`。

出包时这条最容易变成"内容凭空少了一行"：正文第一行以 `@@` 开头，导入后前两个字符消失。`validate-st-package.py` 的 **W21** 拦这一条。

## 八、大卡怎么做：四种真实做法

扫查了 `D:/AI/RP创作/参考` 下 8 张实例卡 + 我们自己的示例（`scripts/validate-st-package.py` 只查形状，下列数字是人工清的）：

| 世界书 | 条 | disable | 常驻 | `getwi()` | position 主用 | order 用法 | 正文中位 | keys 中位 |
|---|--:|--:|--:|--:|---|---|--:|--:|
| 时雨不终·太阁立志 | 422 | **410** | 13 | **529** | `0`×414 | 60/250/300 | 786 | 1 |
| 高塔 CP2080 | 355 | 76 | 16 | 13 | **`4`×293** | 100–1000 十八档 | 1,463 | 2 |
| 尸变纪元 | 50 | 4 | 17 | 0 | **`1`×34** | 100×35 | 1,416 | 2 |
| 二十一人会 | 32 | 1 | **19** | 0 | `0`×24 | 98/99/100 | 1,561 | 0 |
| 我，非我 | 22 | 1 | 11 | 0 | `0`×13 | 70→100 逐条递减 | 1,662 | 2 |
| 我当系统？ | 11 | 1 | **11** | 0 | — | — | — | 0 |
| 白潮（我们的示例） | 21 | 5 | 10 | 0 | `0`×18 | 70–200 | 1,008 | 3 |

八本**没有一本**用了 inclusion group / sticky / cooldown / `probability < 100`，`selectiveLogic` 全是 `0`。中小卡用不到那些开关。

- **① 全常驻**（`我当系统？` 11/11、`二十一人会` 19/32）：条目全是规则与总览，零关键词。规模上限就是上下文，10–30 条。
- **② 一人一条 + 名字关键词**（`尸变纪元` 50 条）：`[独特角色]白羽月`、`keys: ["白羽月","月"]`、`position: 1`、`order: 100`（全同档）、`depth: 4`、正文 2.3–3.4k 字。8 个独特角色 ≈ 24k 字。它成立的前提是 position 1 + 每条 2–3k + 预算给足；代价是单字关键词（`月`、`枫`）在 `include_names` 关着时会被任意句子点亮。
- **③ atDepth 深度阶梯**（`高塔 CP2080` 355 条里 293 条 atDepth）：`order` 100–1000 分十八档、`depth` 分 1–5 档。把"这条多强、要贴多近"编码成两个维度。
- **④ 世界书当数据库 + 控制器动态取用**（`时雨不终` 410/422 条 `disable: true`）：条目命名 `[data]人物资料·<国>`，从不参与扫描；一个常驻控制器条目（16,070 字）按变量分支取用：

```ejs
<% if (loc === '尾张') { %>
<%- await getwi(null, '[data]人物资料·尾张') %>
<%- await getwi(null, '[data]城池资料·尾张') %>
<% } else if (loc === '美浓') { %>
<%- await getwi(null, '[data]人物资料·美浓') %>
<% } %>
```

`loc` 来自 `getvar('stat_data.世界.当前位置.所在国')`，全书 529 次 `getwi()`。

**这不是一条"交付路线"，是一种"条目怎么被选中"的实现方式。** 它和关键词条目不互斥、也不二选一：同一本书里可以既有常驻规则、又有靠关键词命中的设定、还有一片 disable 的资料条目由控制器取用。它改变的是"这条什么时候进上下文"，不是"这包走哪条路"。

我们自己已经在用它的窄版本：`[ejs]阶段控制器·守夜所` 按 `wick` 取 `[阶段]守夜所·清醒 / ·磨损 / ·空壳` 三条 disable 条目。**把"取三个档位"扩成"取任意资料组"，就是做法④**——不需要新开关、新分支，只需要多几组 disable 条目和一个按状态分组的控制器。

它有两个唯一的断链点，`validate-st-package.py` 各有一条规则：

| 断链 | 后果 | 规则 |
|---|---|---|
| 控制器写的名字与条目 `comment` 不完全一致（含 `[]` 前缀与 `·`） | `getwi` 静默返回空串，界面像"这段没写" | **W24**（FAIL） |
| `disable` 的 `[data]` / `[阶段]` 条目没人取 | 死数据，白占文件、还误导后来的维护者 | **W23**（WARN） |

`[initvar]` / `[statusbar]` / `[mvu]` 这类协议条目由 MVU 与正则读，不经 `getwi`，W23 不查它们。

规模无上限，**代价是必须先有可检索的状态**——这正是 `axes` + `mvu` 两个阶段在做的事。没有变量可读时，控制器只能写死一条分支，那就不如直接常驻。

选择：条目 ≲60 用 ②，60–200 用 ③ 或拆书，>200 只有 ④ 撑得住。

## 九、六类静默失效（机制层面，没有一处会报错）

1. **预算溢出**：`Alert on overflow` 默认关，超了只进 console，表现是"AI 忘了前文"。
2. **`order` 分档失效**：所有条目同 `order` 时按创建时间排，作者的意图全部丢失。
3. **`@` 装饰器吃正文**：以 `@@` 开头的第一行静默消失。
4. **递归雪崩**：全局开着而 `excludeRecursion` 没写满，命中一条 → 拉进一片。
5. **单字 / 泛词关键词**：`月`、`家`、`城` 在任意句子里都成立，一条 3k 字的条目就这样被拉进来。
6. **`include_names` 关着时用名字当关键词**：只要聊天里没人说出这个名字，条目永不触发。

## 十、源码索引

| 位置 | 内容 |
|---|---|
| `public/scripts/world-info.js:68-84` | 全局默认值（depth 2 / budget 25 / include_names / recursive / case / whole words） |
| `:27` / `:33` / `:855` | 插入策略 / 四档逻辑 / 七种位置枚举 |
| `:4590` `getSortedEntries` | 拼多本书并按 `sortFn` 排 |
| `:4635` `parseDecorators` 调用点 / `:4655` 定义 | `@@` 装饰器 |
| `:4709` `checkWorldInfo` | 主循环与逐条判定顺序 |
| `:4736` / `:4738` | 预算公式与 cap |
| `:4993`–`:5008` | sticky 优先 + order 排序 |
| `:5061` | 预算逐个 `continue` + 停递归 |
| `:5206` | `sortFn` + `unshift` 组装 |
| `public/script.js:4624` | `名字: 内容` 前缀（`include_names`） |
| `public/scripts/extensions/JS-Slash-Runner/...` | 见 `references/tavern-helper.md`（`getwi` 的签名与返回值） |
