# SillyTavern 语义事实表

本文件只记**会静默失效的事**：写错了不报错、界面照样出来、卡照样能导，但那一块机制其实没跑。每条给三样东西——机制、源码锚点、失效表现。判据以本机 `D:/AI/SillyTavern`（v1.19.0，commit `06bde939f`）为准；换版本先重跑 `scripts/check_st_facts.py --verify`，锚点漂了就更新这里。

`scripts/validate_st_semantics.py` 按 `[S-xx]` 编号实现可机检的部分；标「肉眼」的只能人看。

---

## 一、正则脚本（`正则.json` 里的一条 = ST 的一个 `regexScript`）

**[S-01] `placement` 是数组，且只认 7 个整数**
`regex_placement = { MD_DISPLAY: 0(已废弃), USER_INPUT: 1, AI_OUTPUT: 2, SLASH_COMMAND: 3, WORLD_INFO: 5, REASONING: 6 }`，4 是 legacy sendAs（`public/scripts/extensions/regex/engine.js:281-290`）。
匹配判定是 `script.placement.includes(placement)`（`engine.js:374`）——写成单个整数 `2` 而不是 `[2]`，`.includes` 不存在于 number 上，**整条正则静默不跑**。`0` 写了等于没写。

**[S-02] `markdownOnly` / `promptOnly` 的真值表**
（`engine.js:350-355`）显示阶段看 markdownOnly，提示词阶段看 promptOnly。两项都开时两个阶段分别匹配；两项都关时只匹配这两个标志都未置位的原文处理调用。

**[S-03] `substituteRegex` 三档**
`NONE:0` 原样、`RAW:1` 先把 `{{char}}` 之类宏替换进 findRegex、`ESCAPED:2` 替换后还做正则转义；未知值只 `console.warn` 后按原样处理（`engine.js:398-407`）。写 `"1"` 字符串也能用（`Number()` 兜），写 `true` 会落到 default 分支。

**[S-04] `replaceString` 的捕获组语法**
`$1`…`$99` 与 `$<name>` 都支持，匹配式 `/\\$(\d+)|\\$<([^>]+)>/g`（`engine.js:422`）。
**引用了不存在的组，那一段替换成空字符串**（`if (!match) return ''`，`engine.js:436`）——不是保留字面量。所以 `$1$2` 里 `$2` 不存在时，前半段也一起没了。
附带坑：`$10` 按第 10 组解析（`\d+` 贪婪），不是「第 1 组 + 字面 0」。

**[S-05] `{{match}}` 是整个匹配的别名**
替换前先 `replaceString.replace(/{{match}}/gi, '$0')`（`engine.js:421`）。写 `{{match}}` 与 `$0` 等价；把 `{{match}}` 当普通宏写进文案里的人，会得到整段原文。

**[S-06] 替换结果最后还会过一遍宏替换**
`return substituteParams(replaceWithGroups)`（`engine.js:445`）。含义：`replaceString` 里任何 `{{char}}` / `{{user}}` / `{{description}}` 都会被**自动**替换掉；想在界面上显示字面 `{{char}}`，得写成 `{{noop}}` 之类绕开。同理，legacy 的 `<USER>` / `<BOT>` / `<CHAR>` / `<GROUP>` 也会被替换（`public/scripts/macros.js:625-629`）——界面 HTML 里出现 `<BOT>` 这种「标签」会被吃掉。

**[S-07] `minDepth` / `maxDepth` 的哨兵值**
（`engine.js:363-372`）在传入非负楼层深度时才做裁剪。负的 maxDepth 或 null 不限制上界；minDepth 小于 -1 或 null 不限制下界。有效下限大于有效上限时区间为空。

**[S-08] `runOnEdit` 只影响编辑重渲染**
`if (isEdit && !script.runOnEdit) return`（`engine.js:356`）。不填时用户手动改楼，该条正则不再作用于那一楼——以为「改一下就会重排」的界面会停在旧形态。

**[S-09] 正则按数组顺序串行，前一条的输出是后一条的输入**
`allRegex.forEach(...)` 逐条 `finalString = runRegexScript(...)`（`engine.js:346-380`）。顺序错 = 后一条永远匹配不到。

**[S-25] 卡端正则只认 camelCase，助手端的 snake_case 在这里等于没写**
ST 读的是 `findRegex` / `replaceString` / `placement` / `markdownOnly` / `promptOnly` / `substituteRegex` / `minDepth` / `maxDepth` / `runOnEdit` / `disabled` / `scriptName`（`engine.js:332-380` 的 `RegexParams` 与各分支）。酒馆助手导出的是另一套 `TavernRegex`（`find_regex` / `replace_string` / `markdown_only`…）——把助手端格式直接贴进 `正则.json`，**所有字段都不被读取，该条什么都不做，且不报错**。两边字段集互不兼容，转换要手工做。

**[S-26] `replaceString` 必须存在；空串是合法的「删除」**
`regexScript.replaceString.replace(/{{match}}/gi, '$0')`（`engine.js:421`）直接对它的值调方法——**键缺失或为 `null` 会抛 TypeError**（该条不跑，控制台留错）。空串 `""` 没有错：匹配到的内容全删，这是正规用法，不要为了「总得替点东西」而硬填。

**[S-27] `findRegex` 为空串 = 这条静默跳过**
`if (!regexScript || !!(regexScript.disabled) || !regexScript?.findRegex || !rawString) return rawString;`（`engine.js:393`）。空串与缺失都命中这个短路——**不警告、不报错、什么都不做**。脚手架里留着空模板忘了填，就是这样丢一条正则的。

**[S-28] 卡内正则默认不生效，而且「取消一次」就永久静默**
卡里 `extensions.regex_scripts` 的脚本是 **scoped scripts**：只有 `extension_settings.character_allowed_regex` 里含该头像才参与匹配（`public/scripts/extensions/regex/engine.js:166` `isScopedScriptsAllowed`）。
授权只有一个入口：打开聊天时 `checkCharEmbeddedRegexScripts()` 跑一次（`public/scripts/extensions/regex/index.js:1606`），没授权就弹确认框——而 `accountStorage.setItem('AlertRegex_<头像>', 'true')` 写在**弹窗之前**（`:1617`），所以用户点一次「取消」，此后 `:1614-1616` 的双重条件永远不成立，**再也不提示**，界面永久不出现且没有任何报错。
真机实测（1.19.0，2026-11-21，`导入包/st/爱情公寓.json`）：未授权时消息正文就是 6 个字符的字面量 `<建卡向导>`，`#chat iframe = 0`，控制台干净；点「允许」后同一条消息变成 `TH-render` + 一个 674×664 的 iframe（`srcdoc` 19,504 字符），向导立刻能点。允许之后还要 `reloadCurrentChat()`（`:1623`）才重渲染，切走再切回等价。
**所以卡里带正则 = 把「界面出不出来」押在用户点没点对那个按钮上。**本流水线因此把正则放 `正则.json`（全局脚本，不受这条约束），卡里 `extensions.regex_scripts` 必须是 `[]`。

**[S-29] 内嵌书落盘时用 `character_book.name`，且必须与 `extensions.world` 相等**
真机实测（1.19.0，2026-11-21）：导入 `character_book.name = "爱情公寓 世界书"`、`extensions.world = "爱情公寓 世界书"` 的卡，ST 自动生成 `worlds/爱情公寓 世界书.json`（33 条 / 559,165 B），不必手工再导一次书。缺省名字才是 `<角色名>'s Lorebook`（`world-info.js:5744`）。
反过来：`character_book.name ≠ extensions.world` 时，书会落成另一个名字，而绑定只认 `extensions.world`（`:1128`），结果是**两本都对不上、一条都不激活**。`scripts/validate_st_semantics.py` 按 S-29 拦这一条。

**[S-30] 正则导入时选目标：全局 / 角色专属 / 预设，三选一，默认全局**
导入入口是 `regex/index.js:1750`，目标由三个 radio 决定（`:1754` 是 scoped 那个）。三个目标后果完全不同：

| 目标 | 生效范围 | 还要做什么 |
|---|---|---|
| 全局（默认） | 所有角色、所有聊天 | 不用授权，但状态栏正则跑到别人卡上也会命中 |
| 角色专属 | 只有当前角色 | 还要点一次「允许角色专属正则」（S-28），取消一次永久静音 |
| 预设 | 跟随预设 | 换预设就失效 |

本 skill 交付的 `正则.json` 一律**导入为角色正则**：打包成一张卡，就不该把状态栏逻辑留在别人的聊天里——全局正则会在所有角色上跑，别人卡里的 `<StatusPlaceHolderImpl/>` 一样会被我们的替换串接住。

代价是必须多走一步：首次进聊天时点「允许角色专属正则」（S-28）。**这一步没做，正则永久静默**——所以 `导入说明.txt` 必须写，`validate-contract.py` 的 C18 会拦没写的包。

---

## 二、世界书（`世界书.json` 里的一条 = ST 的一个 world info entry）

**[S-10] `position` 枚举是 8 个值，不只是「前/后」**
`{ before:0, after:1, ANTop:2, ANBottom:3, atDepth:4, EMTop:5, EMBottom:6, outlet:7 }`（`public/scripts/world-info.js:855`）。`4`（@D）必须同时给 `depth`；`7`（outlet）必须同时给 `outletName`，内容靠 `{{outlet::<name>}}` 宏取用（`macros.js:654`）。

**[S-11] `order` 越大，装得越早、最终落在越靠下的位置**
排序是 `(a, b) => b.order - a.order`（`world-info.js:88`），先按降序取、再逐条 `unshift` 进位置桶（`world-info.js:5206` 起），所以**同一位置内最终是 order 升序**——order 越大越靠后（越强）。两条同 `order` 的相对位置不稳定。

**[S-12] 预算与激活门槛**
`world_info_budget = 25`（占上下文的百分比，`world-info.js:73`）、`world_info_budget_cap = 0`（不设绝对上限，`:81`）、`world_info_min_activations = 0`（`:70`）。单条可用 `ignoreBudget` 越过预算（`convertCharacterBook` 里 `ignoreBudget: entry.extensions?.ignore_budget ?? false`，`:5669`）。条目写太多不会报错，只会**悄悄被预算挤掉最后几条**。

**[S-13] `selectiveLogic` 四值**
`AND_ANY:0 / NOT_ALL:1 / NOT_ANY:2 / AND_ALL:3`（`world-info.js:33`）。`keysecondary` 非空但 `selective: false` 时，第二组关键词完全不参与判定。

**[S-14] 嵌入卡片的 `character_book` 不会自动生效**
卡里带 `data.character_book` 时，ST 只弹「是否导入」：导入才 `convertCharacterBook` 落成独立世界书文件，默认名是 `character_book.name` 或 `<角色名>'s Lorebook`（`world-info.js:5744-5756`），同名直接覆盖；导入后写回 `data.extensions.world` 完成绑定（`:1119-1128` 的 `primary` 分支只认 `extensions.world`）。**没绑定的书 = 一条都不会激活**，但卡看起来完全正常。所以本流水线一律：不写 `character_book`，单独交 `世界书.json`，并把 `extensions.world` 设成该文件名。

**[S-15] `convertCharacterBook` 的三个反直觉映射**
（`world-info.js:5617-5674`）

- `disable: !entry.enabled`（`:5640`）——**`enabled` 缺省 = 禁用**。V2 卡里省掉 `enabled: true` 的条目，导入后全是灰的。
- `position: entry.extensions?.position ?? (entry.position === 'before_char' ? 0 : 1)`（`:5636`）——字符串 `position` 只识别 `'before_char'`，`'after_char'` 靠 fallback 侥幸正确，其余任何字符串（如 `'before_an'`）**一律落到 after**。
- `order: entry.insertion_order`（`:5635`）——不写就是 `undefined`，排序随之失序；`extensions` 里那些键是 snake_case（`exclude_recursion` / `prevent_recursion` / `scan_depth` / `match_whole_words` / `group_override`…），写成 camelCase 会被当成没写。

**[S-31] 预算是硬墙，而且默认不报警**
`budget = Math.round(world_info_budget * maxContext / 100) || 1`（`world-info.js:4736`），`budget_cap > 0` 时取较小值（`:4738`）。装填循环里 `!entry.ignoreBudget && (textToScanTokens + 新条目 ≥ budget)` 时 `continue`（`:5061`）——**这条跳过、后面的继续试**，同时置 `token_budget_overflowed`，递归随之停下（`:5097`）。`world_info_overflow_alert` 默认 `false`（`:76`）：溢出只进 console，界面什么都不说。`world_info_budget > 100` 会被强制改回 25（`:946`）。

**[S-32] 同一轮命中的装填顺序：sticky 优先，其余按 `order` 降序**
`isBSticky - isASticky || (sortedEntriesIndex.get(a) - sortedEntriesIndex.get(b))`（`world-info.js:4999-5002`）。代码里**没有「常数优先于关键词」「直接命中优先于递归带出」这两条**——常驻条目先装只是因为我们习惯给它高 `order`。

**[S-33] 正文以 `@@` 开头会被当装饰器剥掉**
`parseDecorators`（`world-info.js:4635` 调用、`:4655` 定义）：`@@@` 是转义（`if (data.startsWith('@@@'))`，`:4659`），`@@activate` / `@@dont_activate` 是强制开关。一条正文以 `@@` 开头的条目，**导入后第一段凭空消失且不报错**。`comment` 上限 `MAX_COMMENT_LENGTH = 100`。

**[S-34] `include_names` 只加在「最近 N 条的发言者」身上**
`coreChat.map(x => world_info_include_names ? `${x.name}: ${x.mes}` : x.mes).reverse()`（`public/script.js:4624`）。默认 `true`（`world-info.js:74`）。关掉它，名字就只能靠正文里出现来命中——「角色一说话就点亮他的条目」这套玩法直接失效。

**[S-35] 递归是全局设置，书里只有三个字段**
`world_info_recursive` 默认 `false`（`world-info.js:75`），`max_recursion_steps = 0` 表示不限层（`:82`）。书文件里能写的只有 `excludeRecursion`（不被拉入）、`preventRecursion`（不拉别人）、`delayUntilRecursion`（只在第 N 层命中）。**用户那边一开递归，这三个字段就是全部防线**——实测 `尸变纪元` 46 条启用条目里有 58 条「正文点名别人关键词」的边。

---

## 三、角色卡（`<世界名>（纯净）.json`）

**[S-16] `character_book` 属 V2 `data` 层，导出时会被 ST 清掉**
`data.data.character_book = undefined`（`world-info.js:6113-6114`）。也就是说「我塞进卡里了」在导出/再导入链路上不稳定——必须走独立世界书。

**[S-17] `extensions.regex_scripts` 不应留东西**
卡级 `extensions.regex_scripts` 会被读成「卡内自带正则」，绕过用户自己的正则列表；本流水线的正则统一走 `正则.json` 手动导入，所以卡里这个键必须是空数组（`validate-st-package.py` 已查）。

**[S-18] `role` 三值**
`extension_prompt_roles = { SYSTEM:0, USER:1, ASSISTANT:2 }`（`public/script.js:494-498`）。世界书 `atDepth` 条目的 `role` 用同一套；写 `"system"` 字符串在部分路径会被 `Number()` 成 `NaN` → 落回默认。

---

## 四、宏与前端渲染

**[S-19] 未知宏原样保留，不报错**
`evaluateMacros` 只逐条替换已注册的宏，没有任何「清除未知 `{{...}}`」的兜底（`public/scripts/macros.js:610-716`）。所以 `{{fmt_data}}` 这种拼错的宏会**字面出现在聊天里**。

**[S-20] `{{format_message_variable::stat_data}}` 不是 ST 核心宏**
ST 核心 grep 无此宏（`public/` 仅 `JS-Slash-Runner` 包里出现）。它由酒馆助手注册，数据存在 `message.variables[swipe_id]`（酒馆助手 `index.js`：`_.has(e?.variables?.[e.swipe_id ?? 0], 'stat_data')`）。**没装酒馆助手 = 这一行原样显示**，而 MVU 整套也就不会跑。

**[S-21] 酒馆助手的世界书位置用字符串词汇，与 ST 的整数枚举是两套**
酒馆助手把条目映射成 `before_character_definition` / `after_character_definition` / `before_example_messages` / `after_example_messages` / `before_author_note` / `after_author_note` / `at_depth_as_system|user|assistant`。写脚本时用错词汇（例如把 `'before_an'` 当合法值）不会报错，只落默认位置。

**[S-22] 首条消息也过正则**
`mes: getRegexedString(firstMes, regex_placement.AI_OUTPUT)`（`public/script.js:7719`）。开局要注入界面/状态栏，正则的 `placement` 必须含 `2`，否则第一楼没有标签可替换——用户会以为界面坏了。

**[S-23] 聊天渲染一律走 `AI_OUTPUT` / `USER_INPUT`**
`chatItem.is_user ? USER_INPUT : AI_OUTPUT`（`script.js:4503`），impersonate 也按 `USER_INPUT` 处理（`script.js:6481`）。写在 `REASONING(6)` 上的正则只作用于思维链，不会作用于正文。

**[S-24] 内嵌书不是「导卡就自动挂上」——触发有四个前提**
`checkEmbeddedWorld(chid)` 在打开角色卡时跑：卡上有 `data.character_book` 才继续；`extensions.world` 已指向一本存在的书时**连提示都不弹**（`world-info.js:5701-5703`）；用户设置里 `world_import_dialog` 关着（`power-user.js:210` 默认 true）就只给一条 toastr；每张卡只提示一次（`AlertWI_<头像>` 存在 accountStorage，`world-info.js:5702`）。真正的导入走 `importEmbeddedWorldInfo`（`:5730`），书名叫 `character_book.name`，缺省 `<角色名>'s Lorebook`（`:5744`）。**卡里 `extensions.world` 写的是外挂书的名字时，内嵌书永远不会被导入**——两个口子同时开必须让名字对得上。

---

## 五、肉眼项（脚本查不了的）

- **S-M1** 正则在 ST 里「开着」≠「生效」：用户在扩展面板把某条 toggle 关掉，`getRegexScripts({ allowedOnly: true })` 就取不到它（`engine.js:345`）。交付说明里必须写清「导入后要确认每条的开关」。
- **S-M2** 酒馆助手是否安装决定 `mvu` / `ejs` 是否真跑；`detect-sillytavern.py` 探到的 `tavern_helper` 字段要写进契约，别拿「文件都对」当「跑起来了」。
- **S-M3** 向量化（`vectorized`）与 `sticky` / `cooldown` / `delay` 依赖用户端已开向量存储/设置；这类条目在「裸 ST」里表现与在本机不同，交付说明要点明。
