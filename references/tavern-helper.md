# 酒馆助手（JS-Slash-Runner）接口速查

**锚定版本 4.12.1 / commit `f9c95ab`**。两处源码一致：参考仓库 `D:/AI/RP创作/参考/JS-Slash-Runner`、已安装副本 `D:/AI/SillyTavern/public/scripts/extensions/third-party/JS-Slash-Runner`。
官方 API 站点 `https://n0vi028.github.io/JS-Slash-Runner-Doc`；仓内权威定义是 `@types/**`（5,081 行 .d.ts），签名有疑问直接查那里，不要猜。

这份文件只回答一类问题：**为什么界面没出来、出来了不对、改了不生效**。所以每节都标了「静默失效点」。TH-01…TH-10 由 `scripts/check_st_facts.py` 守住，F10–F14 由 `scripts/validate-frontend.py` 守住。

---

## 一、一个 HTML 前端从消息文本到屏幕

1. 楼层 `message` 先过酒馆正则（`destination: display`），得到显示文本。
2. 酒馆助手遍历其中每个 `<pre>`，判定是否前端：`['html>', '<head>', '<body'].some(tag => content.includes(tag))`（**TH-01**）。
3. 是前端 → 把 `<pre>` 包进 `div.TH-render`，前面插 `.TH-collapse-code-block-button`，`<pre>` 自己 `hidden!`。
4. `createSrcContent(<code> 的文本)` 拼出完整 srcdoc（见第二节）。
5. 建 iframe，`id`/`name` 都是 `TH-message--<楼层号>`；挂载时发 `message_iframe_render_started`，`load` 时发 `message_iframe_render_ended`。
6. iframe 内 `predefine.js` 注入全局、`adjust_viewport.js` 维护 `--TH-viewport-height`、`adjust_iframe_height.js` 用 `body.scrollHeight` 撑高度（**TH-04**）。
7. iframe 真的挂上以后，折叠条给自己加 `hidden!`（**TH-08**）。

**两个现场可用的判据**：折叠条还在 = iframe 没挂上；折叠条消失 + 内容出来 = 渲染成功。别用「消息文本里有 `<html>`」当证据——那只能证明提示词到了。

---

## 二、srcdoc 外层包装：不要和它对抗

`createSrcContent()` 给你的 HTML 套了这一层（`src/panel/render/iframe.ts`）：

```html
<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*,*::before,*::after{box-sizing:border-box;}
html,body{margin:0!important;padding:0;overflow:hidden!important;max-width:100%!important;}   /* TH-02 */
.user_avatar,.user-avatar{background-image:url('<用户头像>')}
.char_avatar,.char-avatar{background-image:url('<角色头像>')}
</style>
<!-- third_party_message.html：本地 tailwind + CDN jQuery / jQuery UI / Vue / vue-router / fontawesome -->
<script src="predefine.js"></script><script src="adjust_viewport.js"></script>
<script src="adjust_iframe_height.js"></script>
</head><body>你的 HTML</body></html>
```

由此得到的硬约束：

- **`overflow:hidden` 加在最外层**：页面不会滚，高的内容靠 iframe 自身撑高。所以不要做「内部滚动容器 + 固定高度」除非你确实想要滚动条在自己元素上；`body{overflow:auto}` 会被 `!important` 压掉。
- **`height:Nvh` 不会被改写**。只有 `min-height:Nvh` 这个词法会被替换成 `var(--TH-viewport-height)`（CSS 声明、内联 `style`、`el.style.minHeight=`、`setProperty('min-height',…)` 四种写法都覆盖，**TH-03**）。想要「满屏」写 `min-height:100vh`，不要写 `height:100vh`（F05 会警告）。
- `--TH-viewport-height` 的值是 `window.parent.innerHeight`，窗口尺寸变化时父页发 `TH_UPDATE_VIEWPORT_HEIGHT` 重新同步（**TH-05**）。
- **`<base>` 只在 `use_blob_url` 打开时才有**。默认 srcdoc 模式下相对路径解析到 `about:srcdoc`，图片/字体全部 404 —— 用 data URI 内联，或酒馆内绝对路径 `/img/…`、`/characters/…`（F11）。
- 头像直接用 class：`.char_avatar` / `.user_avatar`（连字符写法同样支持）。
- 可用的第三方库（已在 head 里）：`_`（lodash）、`YAML`、`showdown`、`toastr`、`z`（zod）、`EjsTemplate`、Vue 2 运行版、vue-router、jQuery、jQuery UI、Tailwind（本地 `lib/tailwindcss.min.js`）、FontAwesome。**别自己再从 CDN 引一遍**（F02 会判失败）。

---

## 三、iframe 里现成的全局

`src/iframe/predefine.js` 把父窗口的这些东西搬进来（**TH-06**）：

- `_`、`YAML`、`showdown`、`toastr`、`z`、`EjsTemplate`、`TavernHelper`
- 消息 iframe 读本楼用 `getChatMessages(getCurrentMessageId())`。range 必填；事件订阅的生命周期与消息读取范围分别处理。
- `SillyTavern`：每次读都是新的 `getContext()`，额外多一个 `writeExtensionField`；包含 `chat`、`characters`、`name1`/`name2`、`characterId`、`chatId`、`chatMetadata`、`maxContext`、`eventSource`、`eventTypes`、`addOneMessage`、`deleteLastMessage`、`generate`、`stopGeneration`、`getTokenCountAsync`、`extensionPrompts`、`setExtensionPrompt(prompt_id, content, position, depth, scan, role, filter)`、`saveSettingsDebounced`、`reloadCurrentChat`
- `Mvu`：只在父窗口有 Mvu 时注入，赋值是空操作
- iframe 专属工具函数：`getAllVariables()`、`eventOn/eventOnce/eventEmit/eventEmitAndWait/eventRemoveListener/eventClearAll`、`getCurrentMessageId()`、`getIframeName()`、`reloadIframe()`

**生命周期**：iframe 卸载时 TH 只做 `eventClearAll()`。定时器、`ResizeObserver`、`requestAnimationFrame` 循环、第三方库实例都要自己清（F14 只查 `setInterval` 这一种，其余靠自觉）。`reloadIframe()` 等价 `location.reload()`，会撕掉分享到父窗口的接口——需要保状态就自己写 destroy/initialize。

---

## 四、变量

作用域是六个不同后端，写错不报错、只是「改了没变化」：

| `type` | 落在哪 | 注意 |
|---|---|---|
| `chat` | 当前聊天文件 | 换聊天就没了 |
| `character` | 角色卡 `data.extensions` | 没开卡时 `throw` |
| `message` | 楼层变量（配合 `message_id`，可负数取深度） | 越界 `throw`；MVU 的 `stat_data` 在这里 |
| `preset` | 当前预设 | |
| `global` | 全局 | |
| `script` | 当前脚本（`script_id` 可省） | 只在脚本内调 |
| `extension` | 指定扩展（`extension_id` 必填） | |

```js
getVariables(option)                        // 整表
replaceVariables(vars, option)              // 整表覆盖——少写一个键就是删掉它
updateVariablesWith(v => ({...}), option)   // 局部更新，推荐
insertOrAssignVariables(vars, option)       // 合并赋值
insertVariables(vars, option)               // 只补不存在的键
deleteVariable('角色.好感度', option)        // 点号路径，返回 {variables, delete_occurred}
registerVariableSchema(z.object({...}), {type})  // 只影响变量管理器 UI 校验，对代码零影响
```

`getAllVariables()`（iframe 专用）返回合并后的视图：**全局 → 角色卡 → 聊天 → 0 号楼层 → 中间各楼层 → 当前楼层**（脚本里则是 全局 → 角色卡 → 脚本 → 聊天 → 各楼层 → 最新楼层）。它是只读快照——改它不会写回任何一层。

---

## 五、聊天消息

```js
getChatMessages(range, {role, hide_state, include_swipes})
// range: 0 | -1（深度）| '0-{{lastMessageId}}'；返回按 message_id 升序
// include_swipes: true 时元素是 ChatMessageSwiped（含 swipe_id/swipes/swipes_data/swipes_info）
setChatMessages([{message_id, …}], {refresh})   // refresh: 'none' | 'affected'(默认) | 'all'
createChatMessages([...]) / deleteChatMessages(ids) / rotateChatMessages(...)
```

- `ChatMessage = {message_id, name, role, is_hidden, message, data, extra}`。
- **重渲染某一楼**的标准手法：`setChatMessages([{message_id: n}])`（空对象也算改动），默认 `refresh:'affected'` 只刷这一楼并发 `USER_MESSAGE_RENDERED`/`CHARACTER_MESSAGE_RENDERED`。
- **`refresh:'all'` 会重载整条聊天并触发 `CHAT_CHANGED`**，把同屏其它界面全刷一遍；除非你就是要全量（F13）。
- 改 `data`/`extra` 时先 `getChatMessages(-1)[0]` 取出来改，再整块写回，别指望深合并。

---

## 六、显示层（只影响本次显示）

```js
retrieveDisplayedMessage(message_id)          // JQuery<HTMLDivElement>，可直接 .text() / .append()
formatAsDisplayedMessage(text, {message_id})  // 按显示管线处理（宏 + 显示正则）
refreshOneMessage(message_id, $mes?)          // 强刷某楼；传 $mes 还能让它显示别楼内容
```

`retrieveDisplayedMessage().text('…')` **不写盘**，重新渲染或刷新网页就回原样。要持久化必须走 `setChatMessages`。这个区别是「状态栏点了没反应」这类 bug 的常见来源：显示改了、变量没改，下一次重渲染就被覆盖。

---

## 七、事件

```js
eventOn(type, fn)      // 返回 {stop()}
eventOnce(type, fn) / eventEmit(type, ...args) / eventEmitAndWait / eventRemoveListener / eventClearAll
eventOnButton(button_name, fn)   // 脚本按钮点击
```

`iframe_events`：`MESSAGE_IFRAME_RENDER_STARTED:'message_iframe_render_started'`、`MESSAGE_IFRAME_RENDER_ENDED`、`GENERATION_REQUESTED:'js_generation_requested'`、`GENERATION_STARTED`、`STREAM_TOKEN_RECEIVED_FULLY`、`STREAM_TOKEN_RECEIVED_INCREMENTALLY`、`GENERATION_ENDED`。

`tavern_events` 常用项（**值是别名，不等于键名**，TH-09）：

| 常量 | 实际字符串 |
|---|---|
| `tavern_events.CHAT_CHANGED` | `chat_id_changed` |
| `tavern_events.CHARACTER_DELETED` | `characterDeleted` |
| `tavern_events.APP_READY` | `app_ready` |
| `tavern_events.MESSAGE_RECEIVED` | `message_received` |
| `tavern_events.MESSAGE_SENT` | `message_sent` |
| `tavern_events.MESSAGE_SWIPED` | `message_swiped` |
| `tavern_events.MESSAGE_EDITED` | `message_edited` |
| `tavern_events.MESSAGE_UPDATED` | `message_updated` |
| `tavern_events.MESSAGE_DELETED` | `message_deleted` |
| `tavern_events.CHARACTER_FIRST_MESSAGE_SELECTED` | `character_first_message_selected` |
| `tavern_events.USER_MESSAGE_RENDERED` / `CHARACTER_MESSAGE_RENDERED` | 同名 |
| `tavern_events.GENERATION_STARTED` / `STOPPED` / `ENDED` | 同名 |
| `tavern_events.WORLDINFO_ENTRIES_LOADED` / `WORLDINFO_SCAN_DONE` | 同名 |

**没有 `VARIABLE_*` 事件**——变量变更的通知在 `Mvu.events` 里。手写字符串一律是 bug（F10）。

---

## 八、MVU 与 EJS

```js
Mvu.getMvuData({type:'message', message_id})   // MvuData = {initialized_lorebooks, stat_data, …}
Mvu.replaceMvuData(data, option)               // 写回，Promise
Mvu.parseMessage(message, old_data)            // 从文本解析 <UpdateVariable>，返回新 MvuData
Mvu.isDuringExtraAnalysis()
```

`Mvu.events`（**TH-10**）：

| 常量 | 实际字符串 |
|---|---|
| `VARIABLE_INITIALIZED` | `mag_variable_initiailized`（源码里就是拼错的） |
| `VARIABLE_UPDATE_STARTED` | `mag_variable_update_started` |
| `COMMAND_PARSED` | `mag_command_parsed` |
| `VARIABLE_UPDATE_ENDED` | `mag_variable_update_ended` |
| `BEFORE_MESSAGE_UPDATE` | `mag_before_message_update` |

命令类型 `set/insert/delete/add/move`，每条带 `full_match`、`args`（字面量字符串，`set` 可带 `expected_old_value` 做条件写）、`reason`。

`EjsTemplate.Features` 里与「界面出不来」直接相关的开关：`enabled`、`render_enabled`、`code_blocks_enabled`、`raw_message_evaluation_enabled`、`depth_limit`（-1 = 无限）、`sandbox`、`compile_workers`。

---

## 九、脚本库与按钮

```js
getScriptTrees({type:'global'|'preset'|'character'})            // 脚本树
replaceScriptTrees(trees, option) / updateScriptTreesWith(fn, option)
getScriptButtons() / replaceScriptButtons([{name, visible}])    // 只在本脚本内可用
updateScriptButtonsWith(fn) / appendInexistentScriptButtons(btns)
getButtonEvent('按钮名') → eventOnButton(...)
getScriptName() / getScriptInfo() / replaceScriptInfo(text)
getAllEnabledScriptButtons()  // {script_id: [{button_id, button_name}]}
```

**装了不等于跑了**：脚本开关在 `extension_settings.tavern_helper.script.enabled.{global, presets[], characters[]}`（设置字段名 `tavern_helper`，**TH-07**）。卡包自带脚本时，`script.enabled.characters` 里没有这张卡就不会执行——这是「数值系统一动不动」的第一嫌疑。

**导入的脚本默认是关的**（TH-11）：`src/panel/script/Toolbar.vue:94` 在解析文件后直接 `script_tree.enabled = false;`，下一行还把 `id` 换成新的 uuid（`:95`）。所以「成功导入脚本」这个提示不等于它在跑：

- 单脚本 → 导入后在脚本库里把那条打开；
- 文件夹（`{type:'folder', scripts:[…]}`）→ **文件夹本身**是关的，`enabled` 过滤发生在文件夹这一层（`src/store/scripts.ts:86`：`.filter(item => item.enabled)`），里面的子脚本各自的 `enabled` 只在文件夹打开后才起作用；
- 导入目标同样三选一：全局 / 角色 / 预设���选「角色」才跟这张卡绑定。

`id` 被重生成意味着**不能靠 id 判断是不是同一份脚本**；同一份内容导入两次会得到两条独立脚本，两条都开就会跑两遍。

---

## 十、生成、注入、宏、正则

```js
generate(config) / generateRaw(config)
// config: {preset_name:'in_use'|string, user_input, max_chat_history:'all'|number,
//          should_stream, should_silence, should_return_reasoning,
//          overrides, injects, ordered_prompts, custom_api, generation_id, image, tools}
// 返回 string，或（should_return_reasoning / tools 时）详情对象：用 typeof result === 'string' 分辨
stopGenerationById(id) / stopAllGeneration() / getModelList(custom_api?) / getProxyPresetNames()
injectPrompts(prompts, {once}) → {uninject}     // 只在当前聊天有效；换聊天要监听 CHAT_CHANGED 重注
uninjectPrompts(ids)
registerMacroLike(/<count_lines>(.*?)<\/count_lines>/gi, ctx => …) → {unregister}
substitudeMacros('{{char}}') / getLastMessageId() / getMessageId() / errorCatched(fn)
formatAsTavernRegexedString(text, 'ai_output'|'user_input'|'slash_command'|'world_info'|'reasoning',
                            'display'|'prompt', {depth, character_name})
getTavernRegexes(option) / replaceTavernRegexes(list, option) / updateTavernRegexesWith(fn, option)
isCharacterTavernRegexesEnabled()
triggerSlash('/trigger')   // 走斜杠命令，返回命令输出字符串
builtin.addOneMessage / copyText / renderMarkdown / duringGenerating / reloadChatWithoutEvents /
        reloadAndRenderChatWithoutEvents / parseRegexFromString / renderPromptManager / saveSettings / uuidv4
```

`TavernRegex` 字段是 snake_case（`find_regex`、`replace_string`、`trim_strings`、`source{user_input,ai_output,slash_command,world_info,reasoning}`、`destination{display,prompt}`、`run_on_edit`、`min_depth`、`max_depth`），与**卡内**正则的 camelCase（`findRegex`、`replaceString`…）不是同一套——混用会静默失效（见 `references/st-correctness.md` 的 S-25）。

---

## 十一、其余命名空间索引（签名查 `@types/function/<名字>.d.ts`）

- **character**：`getCharacterNames / getCharacterIds / getCurrentCharacterName / getCurrentCharacterId / createCharacter / createOrReplaceCharacter / deleteCharacter / getCharacter(avatar?) / replaceCharacter / updateCharacterWith` — 写卡会落盘，`updateCharacterWith` 比 `replaceCharacter` 安全。
- **persona**：`getPersonaNames / getPersonaIds / getCurrentPersonaName / getCurrentPersonaId / getPersonaAvatarPath / getPersona / createPersona / createOrReplacePersona / deletePersona / replacePersona / updatePersonaWith`。
- **preset**：`getPresetNames / getLoadedPresetName / loadPreset / getPreset / createPreset / createOrReplacePreset / deletePreset / renamePreset / replacePreset / updatePresetWith / setPreset / isPresetNormalPrompt / isPresetSystemPrompt / isPresetPlaceholderPrompt / default_preset`。
- **worldbook**：`getWorldbookNames / getGlobalWorldbookNames / rebindGlobalWorldbooks / getCharWorldbookNames / rebindCharWorldbooks / getChatWorldbookName / rebindChatWorldbook / getOrCreateChatWorldbook / createWorldbook / createOrReplaceWorldbook / deleteWorldbook / getWorldbook / replaceWorldbook / updateWorldbookWith / createWorldbookEntries / deleteWorldbookEntries` — `rebind*` 才是「挂书」的那一下，改文件名不会自动改绑定。
- **lorebook / lorebook_entry**：`getLorebookSettings / setLorebookSettings / getLorebooks / createLorebook / deleteLorebook / getCharLorebooks / getCurrentCharPrimaryLorebook / setCurrentCharLorebooks / getChatLorebook / setChatLorebook / getOrCreateChatLorebook`；条目级 `getLorebookEntries / replaceLorebookEntries / updateLorebookEntriesWith / setLorebookEntries / createLorebookEntries / deleteLorebookEntries`。
- **raw_character**：`RawCharacter / getCharData / getCharAvatarPath / getChatHistoryBrief / getChatHistoryDetail` — 读原始字段，不经 ST 的转换。
- **extension**：`isAdmin / getTavernHelperExtensionId / getExtensionType / getExtensionInstallationInfo / isInstalledExtension / installExtension / uninstallExtension / reinstallExtension / updateExtension`。
- **file**：`getTavernFile / uploadTavernFile / deleteTavernFile`。
- **import_raw**：`importRawCharacter / importRawChat / importRawPreset / importRawWorldbook / importRawTavernRegex` — 直接喂 JSON/字符串建对象，不经过文件导入对话框。
- **audio**：`playAudio / pauseAudio / getAudioList / replaceAudioList / appendAudioList / getAudioSettings / setAudioSettings / getCurrentAudio`。
- **global**：`initializeGlobal(name, value)` / `waitGlobalInitialized(name)` — 等 `Mvu`、`TavernHelper` 这类全局就绪，比 `setTimeout` 靠谱。
- **version**：`getTavernHelperVersion() / getTavernVersion()` — 运行时自检用，比读 manifest 可靠。

---

## 十二、静默失效清单

| 现象 | 原因 | 自查 |
|---|---|---|
| 消息里只剩几个字或一段裸文本 | 代码块没被判定为前端 | 有没有 `<!DOCTYPE html>` / `<body>`（TH-01、F01） |
| 折叠条在，界面没有 | iframe 没挂上（脚本语法错、CSP、模板里塞了 `</script>`） | 控制台 + 折叠条判据（TH-08） |
| 界面出来了但高度 0 / 被裁一半 | 靠 `height:100vh`、或内容写死在 body 外层 | 改 `min-height:100vh`（TH-03） |
| 图片、字体全 404 | srcdoc 无 `<base>`，相对路径落到 `about:srcdoc` | 内联 data URI 或 `/img/…`（F11） |
| `eventOn` 写了但回调不跑 | 手写事件名（值≠键名） | 用 `tavern_events.*`（F10、TH-09） |
| 改了变量，界面没变 | 写在 `chat` 但读的是 `message`；或改了显示没改数据 | 对齐作用域；用 `setChatMessages` 重渲染 |
| 刷新一楼后状态丢 | 状态只在 DOM 里 | 落变量，再靠重渲染重建视图 |
| 数值系统一动不动 | 没有 MVU 脚本，或脚本没在 `script.enabled.characters` 里 | `tavern_helper.script.enabled`（TH-07） |
| 卡内正则不生效 | 角色专属正则未授权，取消一次永久静默 | `references/st-correctness.md` S-28 |
| 世界书没挂上 | `character_book.name` 与 `extensions.world` 不一致 | S-29 |
| 切换聊天后界面堆叠 / 定时器还在跑 | 没清 interval，没监听 `CHAT_CHANGED` | F14 + `eventClearAll` |
| 其它楼层的界面被一起刷掉 | 用了 `refresh:'all'` | 改 `'affected'`（F13） |
| 改了 UI 但消息内容没变 | 直接操作父文档或 `retrieveDisplayedMessage` | 走 `setChatMessages`（F12） |

---

## 十三、自查命令

```bash
python scripts/validate-frontend.py 导入包/            # F01–F14
PYTHONIOENCODING=utf-8 python scripts/check_st_facts.py   # S-xx（ST 本体）+ TH-xx（插件）
PYTHONIOENCODING=utf-8 python scripts/check_st_facts.py --th-root "D:/AI/RP创作/参考/JS-Slash-Runner"
```

锚点失效的含义是「插件或酒馆改了实现」，不是「文档写错了」——先回头看源码，再改这张表。
