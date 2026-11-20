# 前端界面公约（`opening` / `statusbar` 共用）

表现层只做**动态版**：正则把标签换成 HTML 代码块，由酒馆助手（JS-Slash-Runner / Tavern-Helper）把它渲染成 iframe 再跑 JS。不做无插件的静态版。

没装酒馆助手就不要做表现层——直接告诉用户"这套界面需要酒馆助手，未安装时这段标签会以代码块形式显示"，然后问是装插件还是跳过本阶段。

## 一、为什么必须这样（机制事实，不要改写）

| 事实 | 出处 |
|---|---|
| ST 正则替换发生在 `messageFormatting()` 里，支持 `{{match}}`、`$1`…`$9`、`$<组名>` | `public/script.js` 的 `messageFormatting` + `extensions/regex/engine.js` 的 `runRegexScript` |
| 替换发生在**文本阶段**，随后才转 Markdown，最后才 sanitize：`regex → fixMarkdown → encode_tags → Showdown → afterMarkdown → DOMPurify` | `public/script.js:1769-1799`（`messageFormatting` 的流程注释与函数体）、`getRegexedString(mes, regexPlacement, { isMarkdown: true })` |
| 替换后的文本会过 `DOMPurify.sanitize()`，`ADD_TAGS` 只有 `custom-style` → 消息正文里的 `<script>` 被移除 | `public/script.js` 里 `const config = { MESSAGE_SANITIZE: true, ADD_TAGS: ['custom-style'] … }` |
| 消息里的 `<style>` 会被改名：每条选择器加 `.mes_text `，每个 `.class` 变 `.custom-class`，`@import` 删除，未开外部媒体时含 `://` 的声明清空 | `public/scripts/chats.js` 的 `encodeStyleTags` / `decodeStyleTags` |
| 酒馆助手只看 `<pre>`：文本含 `html>`、`<head>`、`<body` 任一个，就包进 `div.TH-render` 并换成 iframe | `src/util/is_frontend.ts` 的 `isFrontend` |
| iframe 内容 = 那段代码块的文本，外面再包一层文档，注入 `predefine`（把 `getChatMessages`、`eventOn`、`triggerSlash`、`tavern_events` 等挂到 window）与自动高度脚本 | `src/panel/render/iframe.ts` 的 `createSrcContent`、`src/iframe/predefine.js` |
| iframe 里可拿楼层号：`getCurrentMessageId()`；可拿 iframe 名：`getIframeName()` | `@types/iframe/util.d.ts` |
| 有总开关 `settings.render.enabled` 与渲染深度 `depth`，关掉就全是代码块 | `src/panel/Render.vue` |
| `replaceString` 里的 `$1`…`$9`、`$<名字>` 会被捕获组内容原样顶替（不转义），`trimStrings` 在顶替前过滤；最后整串 `replaceString` 还会过一次 `substituteParams()`（所以 HTML 里写 `{{char}}` 会被展开） | `public/scripts/extensions/regex/engine.js:391-443` |

由此推出三条硬规矩：

1. **正则必须"仅格式显示"**（`markdownOnly: true`）。否则消息原文被换掉，HTML 里 `getChatMessages()` 读到的是 HTML 而不是数据。
2. **代码块里必须出现 `<body>`**（或 `<head>`/`html>`），否则酒馆助手不认它是前端界面。
3. **纯 ST 没有 JS**。任何"解析数据再渲染"的思路都必须走酒馆助手 iframe，别设计成 $1 注入 + 内联脚本。

顺序那一条是关键：替换在前、Markdown 在后，所以 ```html 围栏里的 `<script>` 被 Showdown 转义成文本、再被 sanitize 保留下来，才轮到酒馆助手读 `pre > code` 的 `textContent` 去当 HTML 跑。若顺序反了（先 sanitize 再进代码块），整份 JS 会被当成真标签删掉。**所以不要把 payload 写成不包围栏的裸 HTML。**

判定用的是 `['html>', '<head>', '<body'].some(...)`：`<!DOCTYPE html>` 已含 `html>`，所以正常文档开头的 doctype 就够，不必刻意改名。代价是**对页面上所有 `<pre>` 生效**：正文里贴一段含 `<body` 的裸代码块也会被判成前端界面去渲染，所以不要在 RP 正文里示范裸 HTML。

## 二、数据怎么从 AI 流到界面

四条路径，按需选一条，别混用：

| 路径 | 怎么用 | 适合 | 代价 |
|---|---|---|---|
| **A 静态替换** | `findRegex` 命中一个触发词，`replaceString` 是整份 HTML，无数据 | 建卡向导、纯展示面板 | 界面里的信息全靠 HTML 写死 |
| **B `$1` 注入** | `findRegex` 带捕获组，HTML 里藏 `<textarea id="xx-raw" hidden>$1</textarea>`，JS 读 `.value` | 每轮状态栏、HUD、单楼面板 | 只能看本楼，**取不到上一层，所以做不了差值箭头** |
| **C 聊天 API** | `getChatMessages(getCurrentMessageId())[0].message` 拆标签 | 需要跨楼历史（差值、趋势、跨楼统计） | 依赖酒馆助手注入的 API；纯预览环境下拿不到 |
| **D 变量（MVU）** | `await waitGlobalInitialized('Mvu')` → `_.get(getAllVariables(), 'stat_data')` → `eventOn(Mvu.events.VARIABLE_UPDATE_ENDED, …)`；正则 `findRegex: '<StatusPlaceHolderImpl/>'`、`markdownOnly: true`、`maxDepth: 2` | 项目做了 `mvu` 阶段 | 依赖酒馆助手 + MVU 脚本；没启用脚本时 `Mvu` 不存在，界面要留白不要报错 |

- B 是最稳的一条：数据与 HTML 在同一个正则脚本里，不依赖楼层 API，`runOnEdit` 一开就连手改消息也跟着重算。模板默认“先试 B、B 空则回退 C”，两种环境都能跑。
- 选 C 就得写 `FOLLOW_LATEST`（跟随最新楼）与差值逻辑；选 B 就别写箭头，两个一起上只会互相抵销。
- 任何一条路径都不许从 `document` 里读别的消息 DOM：iframe 是隔离的，读不到。
- 走 D 时：`Mvu.getMvuData()` 是**同步**返回，不要 `await`；变量没初始化（新聊天、脚本没启用）时 `stat_data` 可能是空对象，界面按"未知"渲染，别整块报错。

**发送动作的三级降级**（点击按钮要发消息时才需要）：

```js
if (typeof triggerSlash === 'function') triggerSlash('/send ' + text);
else if (typeof SillyTavern !== 'undefined' && SillyTavern.triggerSlash) SillyTavern.triggerSlash('/send ' + text);
else {
  var box = document.querySelector('#send_textarea');   // 最后手段：往输入框里塞并点发送
  if (box) { box.value = text; box.dispatchEvent(new Event('input', { bubbles: true }));
             document.querySelector('#send_but')?.click(); }
}
```

发送前弹一个确认框（展示将要发出的文本）——按钮点错就发出一句话，在 RP 里收不回来。

**状态分四层，别混。** 数据状态（`stat_data`，只由 MVU 写）、草稿状态（输入框、未提交的选择）、UI 状态（当前 tab、折叠、滚动位置）、派生视图（进度条宽度、档位文字）。后两层**只能活在 DOM 里**：把 tab 或滚动位置写进变量，等于让界面状态污染世界状态；刷新时用 DOM 读回草稿，不要重新从变量生成覆盖用户输入。
「预览、校验、提交用同一个 builder」：界面上看到的就是将被提交的，别为预览另写一套拼字符串。

**数据畸形时显示诊断态，不要静默隐藏。** 缺字段、类型不对、枚举未知、超长文本——先归一化（`Number.isFinite` / 白名单 / `String(x ?? '')` / 钳制），归一化失败就渲染成「未知」并带一句原因，而不是把整块藏起来或抛异常。界面空白且无提示，是最难查的一类故障：用户只会说「坏了」。

## 三、HTML 骨架（每个界面都照这个来）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  /* 全部选择器以本界面命名空间开头，例如 .rp-sb- */
</style>
</head>
<body>
<div class="rp-sb" id="rp-sb-root">…</div>
<script>
(function () {
  'use strict';
  var NS = 'rp-sb';
  var TAG = '状态栏';
  var FIELDS = ['灯芯', '潮压'];            // 与 frontend-prompt.yaml 逐字一致

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '\x26amp;', '<': '\x26lt;', '>': '\x26gt;', '"': '\x26quot;', "'": '\x26#39;' }[c];
    });
  }
  function pick(block, name) {
    var m = block.match(new RegExp('<' + name + '>([\\s\\S]*?)<\\/' + name + '>'));
    return m ? m[1].trim() : '';
  }
  function parse(text) {
    var m = text.match(new RegExp('<' + TAG + '>([\\s\\S]*?)<\\/' + TAG + '>'));
    if (!m) return null;
    var out = {};
    FIELDS.forEach(function (f) { out[f] = pick(m[1], f); });
    return out;
  }
  function render() {
    var msg = getChatMessages(getCurrentMessageId())[0];
    var data = msg ? parse(msg.message) : null;
    var root = document.getElementById(NS + '-root');
    if (!data) { root.innerHTML = ''; return; }   // 本楼没有数据 → 整块留白，不报错
    root.innerHTML = '…按 data 渲染…';
  }
  render();
  if (typeof eventOn === 'function') {
    eventOn(tavern_events.CHARACTER_MESSAGE_RENDERED, render);
    eventOn(tavern_events.MESSAGE_SWIPED ?? 'message_swiped', render);
  }
})();
</script>
</body>
</html>
```

**硬要求：**

- 单文件，CSS 与 JS 全内联；**不引用任何外链**（CDN、字体、图片 URL 一律不用）。需要图像就用内联 SVG 或 CSS 渐变。
- 所有 class 加命名空间前缀，避免两个界面互相串样式。
- 不用 `eval` / `new Function` / `document.write`。
- 数据一律先 `esc()` 再进 `innerHTML`；能不用 `innerHTML` 就不用。
- **HTML 里不要写 HTML 实体，JS 字符串里的实体用 `\x26` 拼。** 见下节。
- 用 `$1` 注入时，隐藏 textarea 必须放在 `<body>` 里、且 `$1` 前后不留空白字符（空白会被当作数据）；捕获内容里不能出现 `</textarea>`，所以数据块字段值禁止含 `<` `>`。
- 本楼没有标签时整块留白（`return`），不抛错、不显示占位红字。
- 高度别写死：内容多时让它自然高；需要限高时用 `max-height` + `overflow:auto`，不要把 `vh` 换算写死（酒馆助手会替换 `min-height: XXvh`）。
- 不做全屏遮罩、不夺焦点、不自动滚动外部聊天；界面在消息气泡内正常流淌。
- 无障碍：正文用真文本，不把信息只塞进 title；对比度至少 4.5:1；点击元素用 `<button>`。
- 中文界面默认 `lang="zh-CN"`；用户要英文界面时改 `lang` 与文案，字段名仍用中文（与产物一致）。

## 三之一、实体陷阱：`&amp;` 会被多吃一层

整条管线是 文本 → `encode_tags` → Showdown → 解析成 DOM → 再插回消息容器，**实体在中间被解码两次**。实测：`esc()` 里写 `'&': '&amp;'`，到了 iframe 里变成 `'&': '&'`，`"'": '&#39;'` 变成三个单引号连写，整段 `<script>` 直接 `SyntaxError: Invalid or unexpected token`，界面高度停在 2px（酒馆助手量的就是这个残骸）。

两条规矩：

1. **正文与 CSS 里不写实体**。要 `&` 就直接写 `&`（浏览器容忍），要空格用 `white-space: pre-wrap` 或 `\u00a0`，不要 `&nbsp;`。
2. **JS 字符串里的实体用 `\x26` 拼**：`'\x26amp;'`、`'\x26lt;'`、`'\x26gt;'`、`'\x26quot;'`、`'\x26#39;'`。`\x26` 在 JS 求值时才变 `&`，源码里没有字面 `&`，管线就没东西可吃。

自查：阶段收尾一检（`check-stage.py opening` / `statusbar`）里的 `validate-frontend.py` F04 专抓这条。

## 四、正则脚本 JSON

导入文件是 `RegexScriptData` 数组（SillyTavern 正则扩展的导入接受数组或单个对象）：

```json
[
  {
    "id": "rp-sb-statusbar",
    "scriptName": "RP · 状态栏",
    "findRegex": "/<状态栏>[\\s\\S]*?<\\/状态栏>/g",
    "replaceString": "```html\n<!DOCTYPE html>…整份 HTML…\n```",
    "trimStrings": [],
    "placement": [2],
    "disabled": false,
    "markdownOnly": true,
    "promptOnly": false,
    "runOnEdit": true,
    "substituteRegex": 0,
    "minDepth": null,
    "maxDepth": null
  }
]
```

规矩：

- `findRegex` 两种写法：**不带捕获组** `/<标签>[\s\S]*?<\/标签>/g`（路径 A，数据全在 HTML 里）；**带捕获组** `/<标签>([\s\S]*?)<\/标签>/g`（路径 B，配合 HTML 里的 `<textarea hidden>$1</textarea>`）。路径 A 的 `replaceString` 里不能出现 `$1`（会被当成空串抹掉）；路径 B 必须出现且只出现一次。
- `replaceString` 是 ```` ```html ```` 开头 + 完整 HTML + ```` ``` ```` 收尾；HTML 里不能出现三个反引号，也别在 HTML 里写注释行夹带反引号。**必须包围栏**：裸 HTML 会被 sanitize 拿掉 `<script>`（见第一节顺序那条）。
- `placement: [2]` 只作用于 AI 输出；用户楼层也要显示时写 `[1, 2]`。
- `markdownOnly: true`（仅格式显示），`promptOnly: false`。
- `runOnEdit: true`，用户手改消息后界面跟着重算。
- `substituteRegex: 0`（用原始正则）；`trimStrings` 用于把捕获内容里的多余字符裁掉，默认空数组。
- 开关给用户一句话：正则扩展 → 导入该 JSON → 确认"仅格式显示"已开；酒馆助手 → 设置里打开"消息渲染"。
- **草稿与交付分开**：`opening` / `statusbar` 各自写一份草稿（`创作痕迹/产物/regex-opening.json` / `regex-statusbar.json`，单对象即可）；`delivery` 交付时合并成一份 `最终产物/正则.json`（数组，一条界面一个对象）。合并只做拼装，不改 `findRegex` 与 `replaceString`。

## 五、提示词条目（`frontend-prompt.yaml`）

界面要能拿到数据，靠的是用户把一段提示词塞进 API 预设 / 世界书 / 角色卡。所以每份表现层都要交这一份 YAML：

```yaml
条目:
  名称: "状态栏输出规范"
  插入位置: "API 预设的越狱后置 / 世界书常驻条目"   # 二选一，按用户习惯
  内容: |
    每次回复末尾输出以下块，字段值只能是数字或短词，不解释：
    <状态栏>
    <灯芯>72</灯芯>
    <潮压>0.42</潮压>
    </状态栏>
字段:
  - 名称: "灯芯"
    类型: "整数 0-100"
    来源: "axis-system.axes[wick] 的当前值"
    缺省: "未知"
  - 名称: "潮压"
    类型: "小数 0.00-1.00"
    来源: "axis-system.axes[tide]"
    缺省: "未知"
一致性:
  标签: "状态栏"                 # 正则 findRegex、HTML 的 TAG、本条目 三处逐字一致
  字段: ["灯芯", "潮压"]          # 正则所在 HTML 的 FIELDS、本条目 两处逐字一致
```

`一致性` 一节是交付前自检的锚：三处标签名、两处字段名，逐字相同。

## 六、交付前自检（前端门）

1. 标签三处一致：`findRegex` 里的标签名、HTML 里的 `TAG`、`frontend-prompt.yaml` 的 `标签`。
2. 字段两处一致：HTML 的 `FIELDS`、`frontend-prompt.yaml` 的 `字段`；并且都能在对应产物里找到来源。
3. 正则 `markdownOnly: true`、`replaceString` 含 ```` ```html ````、HTML 含 `<body>`。
4. 数据路径自洽：走 D 时 `findRegex` 是 `<StatusPlaceHolderImpl/>` 且没有 `$1`；走 B 时 `findRegex` 有 `([\s\S]*?)` 且 HTML 里有 `<textarea … hidden>$1</textarea>`（只一处）；走 A 时 两者都没有；走 C 时无 `$1` 且 `FIELDS` 与消息里拆的字段同名。
5. HTML 无外链、无 `eval`、无 `document.write`；class 全带命名空间。
6. 本楼无标签时留白不报错（自己造一条不含标签的消息，看是否安静）；`$1` 未被替换（字面 `$1`）时也留白。
7. 走 D 时字段名必须能在 `mvu-schema.js` 的 `Schema` 里找到，`FIELDS` 的 min/max 逐项抄轴的 `range`（不一致就改界面，不改产物）。
8. 数据先转义：把字段值改成 `<b>x</b>` 试一次，界面里必须显示成字面文本；越界值不溢出。
9. 交用户四句话：正则怎么导入、渲染开关在哪、提示词条目贴哪里、触发词该出现在哪条消息里。
10. 阶段收尾一检 `python scripts/check-stage.py opening|statusbar <项目根>` 全过（内部跑 `validate-frontend.py`，F01–F08）（F04 专抓 `<script>` 里的 HTML 实体，那是唯一会让界面整份静默不显示的写法）。

## 九、正则只能界面导入

`extension_settings` 属于运行中的客户端：脚本 `POST /api/settings/save` 写进 `settings.json` 的正则，会在页面刷新或下一次自动保存时被内存里的旧数组覆盖。所以 `正则.json` 交出去就完了，别代用户装好——最多校验结构可编译。
