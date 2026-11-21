# 交互联动：界面能读、能写、能听、缺什么（写前端前读这一份）

界面不是截图。它活在酒馆助手的楼层 iframe 里，能读变量与消息、能写变量、能发玩家消息、能订阅事件——**但每一件都要先声明，再实现**。这一份只讲"能动"的部分；颜色版式见 `frontend-design.md`，机制与管线见 `frontend-conventions.md`，接口签名见 `tavern-helper.md`。

---

## 一、四栏声明：界面顶部必须写死

每个 HTML 的脚本最前面四行常量，缺一栏就等于没设计：

```js
var READS   = [{source: 'mvux', path: 'stat_data.灯芯', when: '每轮渲染'}];
var WRITES  = [{scope: 'message', path: 'stat_data.灯芯', when: '点「确认修改」'}];   // 只读就写 []
var LISTENS = ['CHARACTER_MESSAGE_RENDERED', 'MESSAGE_SWIPED'];
var NEEDS   = ['Mvu', 'getChatMessages', 'eventOn'];   // 缺哪个就显示「未接入」，不许静默降级
```

- `WRITES = []` 是一个**决定**，不是默认值。写空就等于承诺"这个界面永不改存档"，F19 会拿它跟实际调用对账。
- `NEEDS` 里任一接口缺失（`typeof Mvu === 'undefined'` 之类），界面显示一行"未接入：Mvu 未启用，本面板只读"，而不是留白、不报错、假装正常。
- `frontend-prompt.yaml` 里同步一节 `交互:`（读/写/听/依赖 + 一句话用途），交付时和界面一致。

## 二、三种联动形态，选一种，别混

| 形态 | 典型界面 | 读 | 写 | 关键纪律 |
|---|---|---|---|---|
| **只读显示器** | 状态栏、HUD | 本楼快照 / 变量 | **无** | 缺值显示未知，不补默认值；不因为"顺手"就初始化变量 |
| **写回控制器** | 控制中心、技能面板 | 变量 + 轴 | 变量（`replaceMvuData`） | 确认 → 快照 → 写 → 复读 → 失败保留输入；幂等防连点 |
| **开场注入** | 建卡向导、开局面板 | 组件自身状态 | 玩家消息（`triggerSlash('/send …')`） | 草稿只活 DOM/localStorage；提交只发一次；确认框展示将发出的原文 |

发送的三级降级（按钮要发消息时才需要）：

```js
if (typeof triggerSlash === 'function') triggerSlash('/send ' + text);
else if (typeof SillyTavern !== 'undefined' && SillyTavern.triggerSlash) SillyTavern.triggerSlash('/send ' + text);
else {
  var box = document.querySelector('#send_textarea');   // 最后手段：塞进输入框再点发送
  if (box) { box.value = text; box.dispatchEvent(new Event('input', { bubbles: true }));
             document.querySelector('#send_but')?.click(); }
}
```

发送前弹确认框展示将要发出的原文——点错就发出一句话，在 RP 里收不回来。

**状态栏永不带写按钮。** 要改数据就另做一个控制中心界面（`templates/control-center.html`），两者各挂一条正则，互不依赖。

## 三、写回五步（控制中心的全部逻辑）

```text
1. 确认        弹框展示「字段：旧值 → 新值」逐条差异，不展示整块 JSON
2. 快照        snapshot = JSON.stringify(当前 stat_data 的字段子集)
3. 写入        await Mvu.replaceMvuData(next, {type:'message', message_id: getCurrentMessageId()})
4. 复读        立刻 Mvu.getMvuData(...) 读回，逐字段比对；不等同就报"未生效"而不是显示成功
5. 失败       保留用户输入 + 一行「未写入：<原因>」，不重置表单、不静默回滚
```

三条硬要求：

- **不以"请求已发出"当成功**：`replaceMvuData` 是 Promise，但它只说明命令递交了；界面显示的值必须来自第 4 步的复读结果。
- **幂等**：按钮进入 `pending` 后 `disabled`，同一次提交带一次性 `draftId`，重复点击/重复回车直接丢弃。F21 查这个。
- **陈旧确认作废**：确认框打开期间，若聊天被切走、楼层变化、或用户点了另一个 swipe，原确认作废（对比 `chatId` 与 `getCurrentMessageId()`）。切走再切回不算同一个上下文。

## 四、事件：订阅要覆盖"值被改的所有时刻"

状态栏与控制器都要订阅，否则会停在初值：

- `CHARACTER_MESSAGE_RENDERED` / `USER_MESSAGE_RENDERED` —— 每轮新消息
- `MESSAGE_SWIPED` —— 换 swipe（**只订 `VARIABLE_UPDATE_ENDED` 会漏掉它**）
- `MESSAGE_EDITED` —— 手改消息后
- `CHAT_CHANGED` —— 切聊天，必须重读而不是沿用旧值

规矩：`eventOn` 必须配 `pagehide` 里的 `eventClearAll()`；重渲染入口要清 `setInterval`（F14）。**只给"更新结束"一个事件，界面能显示但永远停在打开那一刻的值**——这是最常见的"看起来没坏"。

## 五、读：四种路径的副作用不一样

- 变量（`Mvu.getMvuData` → `stat_data`）：**不要无脑拼 `stat_data.`**，reader 已经返回子树时就别再加前缀。取不到就显示未知。
- 消息（`getChatMessages`）：读本楼用 `getCurrentMessageId()`；要跨楼历史才读范围，读完不许把结果写回变量当缓存。
- 显示层（`retrieveDisplayedMessage`）：只在需要读渲染后文本时用，换了聊天就失效。
- 草稿（DOM / localStorage）：只服务"还没提交的输入"，键名带项目前缀（`rpwz:<项目名>:`），永不同步进 `stat_data`。

## 六、值的六种状态，各给显示

合法 `0` / `false` / 空串 / 缺失（字段不存在）/ `null` / 非法（类型不对、枚举未知）——**六种都要各自有行为**，不许用真值判断把"缺失"变成"0"。

- 缺失 → `未知`，不是 `0`、不是 `-`
- 非法 → 诊断态（`未知（非数字）`），**不许就近归到某一档**
- 越界 → 条钳到边界，**数字照原样显示**（钳制只影响视觉，不改数据、不掩盖漂移）
- 进度条只在有范围意义时用；颜色不许单独表意，更不许用颜色暗示角色的同意/知情

## 七、预览模式：一行副作用都不许产生

`RP_PREVIEW`（`window.self === window.top`）为真时：不 `replaceMvuData`、不 `setChatMessages`、不 `triggerSlash`、不 `SillyTavern.generate`。**只有 localStorage 的界面草稿可以写**（那是浏览器本地，不是存档）。

F18 会扫描 `if (RP_PREVIEW) { … }` 的花括号块，块内出现写调用直接判失败；F19 拿 `WRITES` 声明与实际调用对账。

## 八、写码前四问

1. 这个界面**要不要动存档**？动 → 走三形态里的控制器，先写 `WRITES`，再写五步。
2. 用户**怎么知道写成功了**？——答案不能是"看起来变了"，得是复读比对。
3. 写失败时**用户看到什么**？——保留输入 + 原因，不是弹回原样。
4. 切聊天、切楼层、点错一次，**会不会写错地方**？——陈旧确认作废 + 幂等。

## 九、机检对照（`validate-frontend.py`）

| 规则 | 级别 | 抓什么 |
|---|---|---|
| F18 | 失败 | `if (RP_PREVIEW)` 块里出现写调用（预览会改存档 / 发消息） |
| F19 | 失败 | 有写调用却没有 `WRITES` 声明，或声明为 `[]` 却在写 |
| F20 | 警告 | `replaceMvuData` 之后没有 `getMvuData` 复读 |
| F21 | 警告 | 有写调用但全文没有 `disabled` / `pending`（可连点重复写） |
