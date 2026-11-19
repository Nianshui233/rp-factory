# 前端界面公约（阶段 5 / 6 共用）

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

由此推出三条硬规矩：

1. **正则必须"仅格式显示"**（`markdownOnly: true`）。否则消息原文被换掉，HTML 里 `getChatMessages()` 读到的是 HTML 而不是数据。
2. **代码块里必须出现 `<body>`**（或 `<head>`/`html>`），否则酒馆助手不认它是前端界面。
3. **纯 ST 没有 JS**。任何"解析数据再渲染"的思路都必须走酒馆助手 iframe，别设计成 $1 注入 + 内联脚本。

顺序那一条是关键：替换在前、Markdown 在后，所以 ```html 围栏里的 `<script>` 被 Showdown 转义成文本、再被 sanitize 保留下来，才轮到酒馆助手读 `pre > code` 的 `textContent` 去当 HTML 跑。若顺序反了（先 sanitize 再进代码块），整份 JS 会被当成真标签删掉。**所以不要把 payload 写成不包围栏的裸 HTML。**

判定用的是 `['html>', '<head>', '<body'].some(...)`：`<!DOCTYPE html>` 已含 `html>`，所以正常文档开头的 doctype 就够，不必刻意改名。代价是**对页面上所有 `<pre>` 生效**：正文里贴一段含 `<body` 的裸代码块也会被判成前端界面去渲染，所以不要在 RP 正文里示范裸 HTML。

## 二、数据怎么从 AI 流到界面

```
AI 每轮回复末尾输出  →  <标签> …字段… </标签>
ST 正则（仅格式显示）  →  把整个标签替换成 ```html 代码块
酒馆助手              →  代码块变 iframe，执行其中 JS
HTML                  →  getChatMessages(本楼) 取原文 → 拆标签 → 渲染
```

- 取本楼用 `getChatMessages(getCurrentMessageId())[0].message`。
- 要"跟随最新楼"（状态栏固定在页面某处、永远显示当前状态）时，改读 `getChatMessages(-1)[0].message`，并 `eventOn(tavern_events.CHARACTER_MESSAGE_RENDERED, …)` 重新渲染。
- 严禁从 `document` 里读别的消息 DOM：iframe 是隔离的，读不到。

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
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
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

硬要求：

- 单文件，CSS 与 JS 全内联；**不引用任何外链**（CDN、字体、图片 URL 一律不用）。需要图像就用内联 SVG 或 CSS 渐变。
- 所有 class 加命名空间前缀，避免两个界面互相串样式。
- 不用 `eval` / `new Function` / `document.write`。
- 数据一律先 `esc()` 再进 `innerHTML`；能不用 `innerHTML` 就不用。
- 本楼没有标签时整块留白（`return`），不抛错、不显示占位红字。
- 高度别写死：内容多时让它自然高；需要限高时用 `max-height` + `overflow:auto`，不要把 `vh` 换算写死（酒馆助手会替换 `min-height: XXvh`）。
- 不做全屏遮罩、不夺焦点、不自动滚动外部聊天；界面在消息气泡内正常流淌。
- 无障碍：正文用真文本，不把信息只塞进 title；对比度至少 4.5:1；点击元素用 `<button>`。
- 中文界面默认 `lang="zh-CN"`；用户要英文界面时改 `lang` 与文案，字段名仍用中文（与产物一致）。

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

- `findRegex` 用 `/<标签>[\s\S]*?<\/标签>/g`，**不加捕获组**（动态版不需要传数据）。
- `replaceString` 是 ```` ```html ```` 开头 + 完整 HTML + ```` ``` ```` 收尾；HTML 里不能出现三个反引号，也别在 HTML 里写注释行夹带反引号。**必须包围栏**：裸 HTML 会被 sanitize 拿掉 `<script>`（见第一节顺序那条）。
- `placement: [2]` 只作用于 AI 输出；用户楼层也要显示时写 `[1, 2]`。
- `markdownOnly: true`（仅格式显示），`promptOnly: false`。
- `runOnEdit: true`，用户手改消息后界面跟着重算。
- 开关给用户一句话：正则扩展 → 导入该 JSON → 确认"仅格式显示"已开；酒馆助手 → 设置里打开"消息渲染"。

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
4. HTML 无外链、无 `eval`、无 `document.write`；class 全带命名空间。
5. 本楼无标签时留白不报错（自己造一条不含标签的消息，看是否安静）。
6. 数据先转义：把字段值改成 `<b>x</b>` 试一次，界面里必须显示成字面文本。
7. 交用户三句话：正则怎么导入、渲染开关在哪、提示词条目贴哪里。
