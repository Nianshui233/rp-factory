# 前端交互范式（从 TavernWeave 提取）

**何时使用本文档**：
- 用户要求「行动选择」「点击按钮执行行动」「建卡向导」「控制面板」
- 阶段 5/6 的"主动设计调研"判断出 `[交互需求: 需要交互]`

**何时不使用本文档**：
- 纯静态面板（欢迎页、登场面板无交互）
- 只读显示器（状态栏只显示数值，用户不可点击）

---

## 范式 1：行动选择（点击 → 直接发送）

**适用场景**：
- 尸变纪元的行动选择（点击"前往安全屋" → 直接发送消息，AI 立即响应）
- 快速决策场景（用户不需要二次确认）
- 单轮行动（点击后立即触发 AI 生成）

**关键点**：
1. 用 `createChatMessages()` 创建真实 user 楼层（不是 `generate()` 生成游离文本）
2. 用 `triggerSlash('/trigger')` 触发 ST 正常生成（不是直接 `generate()`）
3. 保留 action_id 用于对账（防止事件漏收）
4. 监听 `MESSAGE_SENT` / `GENERATION_STARTED` / `MESSAGE_RECEIVED` 事件，更新 UI 状态

**完整代码片段**：

```javascript
// ============ 范式 1：行动选择（点击 → 直接发送）============

let sending = false;
let activeActionId = null;

async function submitPlayerTurn(rawText) {
  const text = rawText.trim();
  if (!text || sending) return;

  sending = true;
  activeActionId = crypto.randomUUID();
  renderGenerationState('sending'); // 显示"发送中..."

  try {
    // 创建真实 user 楼层
    await createChatMessages([{
      role: 'user',
      message: text,
      data: { same_floor_ui: { action_id: activeActionId } }, // 用于对账
    }]);

    renderGenerationState('generating'); // 显示"AI 生成中..."
    
    // 触发 ST 正常生成
    await triggerSlash('/trigger');
  } catch (error) {
    sending = false;
    activeActionId = null;
    renderGenerationError(error);
  }
}

// 事件监听（重建 UI 状态）
function bindEvents() {
  const eventOnHost = window.eventOn || hostWindow().eventOn;
  const events = window.tavern_events || hostWindow().tavern_events || {};
  
  if (typeof eventOnHost !== 'function') return;
  
  // MESSAGE_SENT: 重读用户楼层，确认 action 已落库
  const d1 = eventOnHost(events.MESSAGE_SENT, () => {
    console.log('✓ 用户消息已发送');
  });
  
  // GENERATION_STARTED: 显示生成态、锁定重复提交
  const d2 = eventOnHost(events.GENERATION_STARTED, () => {
    renderGenerationState('generating');
  });
  
  // MESSAGE_RECEIVED: 重读完整聊天，提交 assistant 正文
  const d3 = eventOnHost(events.MESSAGE_RECEIVED, () => {
    console.log('✓ AI 回复已生成');
    reconcileFromRealChat(); // 重新读取聊天历史
  });
  
  // GENERATION_ENDED: 结束流式预览，做最终对账
  const d4 = eventOnHost(events.GENERATION_ENDED, () => {
    sending = false;
    activeActionId = null;
    renderGenerationState('idle'); // 恢复空闲状态
  });
  
  // GENERATION_STOPPED: 解锁并保留用户消息，提示可重试
  const d5 = eventOnHost(events.GENERATION_STOPPED, () => {
    sending = false;
    activeActionId = null;
    renderGenerationState('idle');
    showRetryHint();
  });
  
  // CHAT_CHANGED: 取消旧任务，重启 shell 会话
  const d6 = eventOnHost(events.CHAT_CHANGED, () => {
    sending = false;
    activeActionId = null;
    reconcileFromRealChat();
  });
  
  // 保存 disposers（用于清理）
  if (d1?.stop) disposers.push(() => d1.stop());
  if (d2?.stop) disposers.push(() => d2.stop());
  if (d3?.stop) disposers.push(() => d3.stop());
  if (d4?.stop) disposers.push(() => d4.stop());
  if (d5?.stop) disposers.push(() => d5.stop());
  if (d6?.stop) disposers.push(() => d6.stop());
}

// 示例：按钮点击
document.getElementById('action-btn-1').addEventListener('click', () => {
  submitPlayerTurn('我前往安全屋');
});

document.getElementById('action-btn-2').addEventListener('click', () => {
  submitPlayerTurn('我继续搜索物资');
});
```

**来源**：TavernWeave `C5_同层前端.md` § 5.2 最小发送骨架 + § 5.3 生成结束后的权威提交  
**置信度**：high `[运行时源码 + 类型声明]`

---

## 范式 2：行动选择（点击 → 填入输入框）

**适用场景**：
- 用户希望修改文本后再发送（如"前往安全屋"可能改成"小心前往安全屋"）
- 需要二次确认的场景（用户可以看到完整文本，决定是否发送）
- 辅助输入场景（不直接发送，只是帮用户填入预设文本）

**关键点**：
1. 这是版本敏感的私有 DOM 路线（`#send_textarea` / `#send_but` 不保证稳定）
2. 写入前记录输入框原内容，若用户已修改则取消覆盖（或询问用户是否覆盖）
3. 触发正常 input/change 事件（让 ST 识别输入变化）
4. **不直接 `generate()` 生成游离文本**

**完整代码片段**：

```javascript
// ============ 范式 2：行动选择（点击 → 填入输入框）============

function fillInputBox(actionText) {
  const textarea = parent.document.getElementById('send_textarea');
  if (!textarea) {
    console.warn('未找到 ST 输入框');
    return;
  }
  
  // 记录输入框原内容
  const originalValue = textarea.value;
  
  // 若用户已修改输入框，取消自动覆盖
  if (originalValue.trim() !== '') {
    const confirmed = confirm('输入框已有内容，是否覆盖？');
    if (!confirmed) return;
  }
  
  // 填入文本
  textarea.value = actionText;
  
  // 触发 input/change 事件（让 ST 识别输入变化）
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
  textarea.dispatchEvent(new Event('change', { bubbles: true }));
  
  // 可选：聚焦到输入框（让用户可以立即编辑）
  textarea.focus();
}

// 示例：按钮点击
document.getElementById('action-btn-1').addEventListener('click', () => {
  fillInputBox('我前往安全屋');
});

document.getElementById('action-btn-2').addEventListener('click', () => {
  fillInputBox('我继续搜索物资');
});
```

**来源**：TavernWeave `C10_开局页与自定义开局.md` § 10.4 输入框仲裁  
**置信度**：medium `[版本敏感的私有 DOM，不保证稳定]`

**常见错误**：
- ❌ 不触发 input/change 事件 → ST 不识别输入变化，发送时可能用旧内容
- ❌ 不检查输入框原内容 → 覆盖用户已输入的文本，体验差
- ❌ 直接调用 `generate()` → 生成游离文本，不创建真实楼层，破坏聊天历史

---

## 范式 3：建卡向导（收集输入 → 拼成消息）

**适用场景**：
- 建卡向导（收集角色姓名、年龄、背景 → 拼成一条消息）
- 多步骤表单（分步采集玩家设定 → 最终提交）
- 结构化输入（需要校验字段、显示预览）

**关键点**：
1. 草稿与聊天隔离（draft 不直接修改聊天，提交时才创建真实消息）
2. 校验、预览与唯一真相源（提交前必须校验，预览不等于提交）
3. 最终填入 ST 输入并走正常发送，不直接调用 `generate()`
4. 保留草稿到 message.data（方便后续回溯）

**完整代码片段**：

```javascript
// ============ 范式 3：建卡向导（收集输入 → 拼成消息）============

// 草稿 schema
const draft = {
  name: '',
  age: '',
  background: '',
  appearance: '',
};

// 收集用户输入
function collectDraft() {
  draft.name = document.getElementById('char-name').value.trim();
  draft.age = document.getElementById('char-age').value.trim();
  draft.background = document.getElementById('char-bg').value.trim();
  draft.appearance = document.getElementById('char-appearance').value.trim();
}

// 校验草稿
function validateDraft() {
  if (!draft.name) {
    showError('角色名不能为空');
    return false;
  }
  
  if (!draft.age || isNaN(draft.age)) {
    showError('年龄必须是数字');
    return false;
  }
  
  if (!draft.background) {
    showError('背景不能为空');
    return false;
  }
  
  return true;
}

// 预览消息（不创建真实楼层）
function previewMessage() {
  collectDraft();
  
  const message = `我的角色是${draft.name}，今年${draft.age}岁。${draft.background}${draft.appearance ? `\n外貌：${draft.appearance}` : ''}`;
  
  document.getElementById('preview-box').innerText = message;
  document.getElementById('preview-panel').style.display = 'block';
}

// 提交草稿（创建真实 user 楼层）
async function submitDraft() {
  collectDraft();
  
  // 校验
  if (!validateDraft()) return;
  
  // 拼成最终消息
  const message = `我的角色是${draft.name}，今年${draft.age}岁。${draft.background}${draft.appearance ? `\n外貌：${draft.appearance}` : ''}`;
  
  // 创建真实 user 楼层（同范式 1）
  try {
    await createChatMessages([{
      role: 'user',
      message: message,
      data: { opening_draft: draft }, // 保留草稿到 message.data
    }]);
    
    // 触发 ST 正常生成
    await triggerSlash('/trigger');
    
    // 关闭建卡向导面板
    closeWizardPanel();
  } catch (error) {
    showError('提交失败：' + error.message);
  }
}

// 示例：按钮绑定
document.getElementById('preview-btn').addEventListener('click', previewMessage);
document.getElementById('submit-btn').addEventListener('click', submitDraft);
```

**来源**：TavernWeave `C10_开局页与自定义开局.md` § 4.1 草稿 schema + § 10 提交事务  
**置信度**：high `[生产验证标准写法]`

**常见错误**：
- ❌ 预览时直接创建楼层 → 用户只是想看看效果，不应该污染聊天历史
- ❌ 不校验字段 → 提交后发现格式错误，用户体验差
- ❌ 不保留草稿到 message.data → 后续无法回溯用户填写的原始数据

---

## 范式 4：控制面板（修改变量 → 写回）

**适用场景**：
- 控制中心（点击"+5 好感度" → 修改 MVU 变量）
- 调试面板（手动调整变量，测试不同分支）
- GM 工具（管理员可以修改玩家状态）

**关键点**：
1. 不直接修改 `Mvu.stat_data`（只读快照）
2. 用 `generateRaw()` 生成 `<UpdateVariable>` 块（让 AI 按规则修改变量）
3. 用 `Mvu.parseMessage()` 解析变量更新
4. 用 `Mvu.replaceMvuData()` 写回

**完整代码片段**：

```javascript
// ============ 范式 4：控制面板（修改变量 → 写回）============

// 读取当前楼变量
function getCurrentMvuData() {
  const Mvu = window.Mvu || hostWindow().Mvu;
  if (!Mvu?.getMvuData) throw new Error('MVU 未就绪');
  return Mvu.getMvuData({ type: 'message', message_id: 'latest' });
}

// 三段式写回：generateRaw → parseMessage → replaceMvuData
async function writeVariableFix(instruction) {
  const helper = window.TavernHelper || hostWindow().TavernHelper;
  const generateRaw = helper?.generateRaw || window.generateRaw || hostWindow().generateRaw;
  if (typeof generateRaw !== 'function') throw new Error('generateRaw 不可用');

  const oldData = getCurrentMvuData();
  
  // 用 AI 生成 <UpdateVariable> 块
  const raw = String(await generateRaw({
    should_silence: true,
    max_chat_history: 0,
    ordered_prompts: [
      { role: 'system', content: '只输出一个 <UpdateVariable> 块（内含 JSONPatch）。' },
      { role: 'user', content: '当前变量：' + JSON.stringify(oldData) + '\n修正：' + instruction },
    ],
  }) || '').trim();

  if (!/<UpdateVariable/i.test(raw)) throw new Error('结果未含 <UpdateVariable> 块');

  // 解析变量更新
  const Mvu = window.Mvu || hostWindow().Mvu;
  const nextData = await Mvu.parseMessage(raw, oldData);
  if (!nextData) throw new Error('未能解析变量更新');

  // 写回
  await Mvu.replaceMvuData(nextData, { type: 'message', message_id: 'latest' });
  
  console.log('✓ 变量已更新：', nextData);
}

// 示例：控制面板按钮
document.getElementById('add-affection-btn').addEventListener('click', async () => {
  await writeVariableFix('好感度 +5');
  showSuccessHint('好感度 +5');
});

document.getElementById('sub-hp-btn').addEventListener('click', async () => {
  await writeVariableFix('生命值 -10');
  showSuccessHint('生命值 -10');
});

document.getElementById('reset-gold-btn').addEventListener('click', async () => {
  await writeVariableFix('金币重置为 100');
  showSuccessHint('金币已重置');
});
```

**来源**：TavernWeave `C2_前端应用-状态栏与控制中心.md` § 5.9 MVU 变量读写三段式范式（v2.9.9）  
**置信度**：high (generateRaw / 三段式流程)；medium·单源孤证 (parseMessage / replaceMvuData 接口)

**常见错误**：
- ❌ 直接修改 `Mvu.stat_data` → 只是修改了快照，不会写回真实变量
- ❌ 不用 `generateRaw()` → 自己拼 JSONPatch 容易出错，且不符合 MVU 规则
- ❌ 不用 `Mvu.parseMessage()` → 自己解析 `<UpdateVariable>` 块容易漏掉边界情况

---

## 动态数据读取（适用于所有范式）

**读取当前楼层消息**：

```javascript
// 读取最近 10 条消息
function getRecentMessages(count = 10) {
  const messages = getChatMessages(`{{lastMessageId - count + 1}}-{{lastMessageId}}`);
  return messages.filter(m => m.message_id !== 0);
}

// 读取当前楼层的 AI 回复
function getCurrentAssistantMessage() {
  const messages = getChatMessages('{{lastMessageId}}-{{lastMessageId}}');
  return messages.find(m => m.is_user === false);
}
```

**读取 MVU 变量**：

```javascript
// 读取当前楼层 MVU 变量
function getCurrentStats() {
  const Mvu = window.Mvu || hostWindow().Mvu;
  if (!Mvu?.getMvuData) {
    console.warn('MVU 未就绪，无法读取变量');
    return null;
  }
  
  const data = Mvu.getMvuData({ type: 'message', message_id: 'latest' });
  return data?.stat_data || null;
}

// 读取特定字段
function getStat(key) {
  const stats = getCurrentStats();
  return stats?.[key] || 0;
}

// 示例：显示当前状态
function updateStatusBar() {
  const hp = getStat('hp');
  const mp = getStat('mp');
  const gold = getStat('gold');
  
  document.getElementById('hp-value').innerText = hp;
  document.getElementById('mp-value').innerText = mp;
  document.getElementById('gold-value').innerText = gold;
}
```

**来源**：TavernWeave `frontend-conventions.md` 第三节"HTML 骨架"  
**置信度**：high `[类型声明 + 运行时源码]`

---

## 辅助函数

**宿主窗口与文档**：

```javascript
function hostWindow() {
  return window !== window.parent ? window.parent : window;
}

function hostDocument() {
  return hostWindow().document;
}
```

**API 发现链**：

```javascript
function worldbookApiHost() {
  const candidates = [
    window.TavernHelper,
    hostWindow().TavernHelper,
    window.SillyTavern?.getContext?.()?.eventSource,
    hostWindow().SillyTavern?.getContext?.()?.eventSource,
  ];
  
  return candidates.find(c => c && typeof c.updateWorldbookWith === 'function');
}
```

**来源**：TavernWeave `C2_前端应用-状态栏与控制中心.md` § 4 API 发现链  
**置信度**：high `[运行时源码]`

---

## 使用指南

### 1. 判断使用哪个范式

| 场景 | 推荐范式 |
|------|---------|
| 用户点击行动选项，立即执行 | 范式 1（直接发送）|
| 用户点击行动选项，可修改后再发送 | 范式 2（填入输入框）|
| 建卡向导、多步骤表单 | 范式 3（收集输入）|
| 控制面板、修改变量 | 范式 4（修改变量）|
| 只读显示器（无交互）| 不需要本文档，只用动态数据读取 |

### 2. 范式组合

可以在同一个前端里组合多个范式：

```javascript
// 状态栏：只读显示（动态数据读取）
function updateStatusBar() {
  const hp = getStat('hp');
  const mp = getStat('mp');
  document.getElementById('hp-value').innerText = hp;
  document.getElementById('mp-value').innerText = mp;
}

// 行动选择：范式 1（直接发送）
document.getElementById('action-btn-1').addEventListener('click', () => {
  submitPlayerTurn('我前往安全屋');
});

// 控制面板：范式 4（修改变量）
document.getElementById('add-hp-btn').addEventListener('click', async () => {
  await writeVariableFix('生命值 +10');
  updateStatusBar(); // 更新状态栏显示
});
```

### 3. 事件监听最佳实践

**必须监听的事件**：

| 事件 | 用途 |
|-----|------|
| `MESSAGE_SENT` | 重读用户楼层，确认 action 已落库 |
| `GENERATION_STARTED` | 显示生成态、锁定重复提交 |
| `MESSAGE_RECEIVED` | 重读完整聊天，提交 assistant 正文 |
| `GENERATION_ENDED` | 结束流式预览，做最终对账 |
| `GENERATION_STOPPED` | 解锁并保留用户消息，提示可重试 |
| `CHAT_CHANGED` | 取消旧任务，重启 shell 会话 |

**事件监听骨架**：

```javascript
function bindEvents() {
  const eventOnHost = window.eventOn || hostWindow().eventOn;
  const events = window.tavern_events || hostWindow().tavern_events || {};
  
  if (typeof eventOnHost !== 'function') {
    console.warn('eventOn 不可用，无法监听事件');
    return;
  }
  
  [events.MESSAGE_SENT, events.GENERATION_STARTED, events.MESSAGE_RECEIVED, 
   events.GENERATION_ENDED, events.GENERATION_STOPPED, events.CHAT_CHANGED]
    .filter(Boolean)
    .forEach(name => {
      try {
        const d = eventOnHost(name, () => {
          console.log('✓ 事件触发：', name);
          reconcileFromRealChat(); // 重新读取聊天历史
        });
        if (d?.stop) disposers.push(() => d.stop());
      } catch (err) {
        console.warn('事件监听失败：', name, err);
      }
    });
}
```

### 4. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|-----|------|---------|
| 直接调用 `generate()` | 生成游离文本，不创建真实楼层 | 用 `createChatMessages()` + `triggerSlash('/trigger')` |
| 不监听事件 | UI 状态不同步，用户不知道 AI 在生成 | 监听 `GENERATION_STARTED` / `MESSAGE_RECEIVED` |
| 不校验输入 | 提交后发现格式错误，体验差 | 提交前必须校验，显示错误提示 |
| 直接修改 `Mvu.stat_data` | 修改无效（只读快照）| 用 `generateRaw()` + `Mvu.replaceMvuData()` |
| 不保留草稿到 message.data | 后续无法回溯原始数据 | 在 `createChatMessages()` 时保留 `data: { draft }` |

---

## 参考资料

- TavernWeave `C5_同层前端.md`：同层前端发送链路、事件监听、Swipe 切换
- TavernWeave `C10_开局页与自定义开局.md`：建卡向导、草稿 schema、输入框仲裁
- TavernWeave `C2_前端应用-状态栏与控制中心.md`：控制中心、MVU 变量读写、事件绑定
- TavernWeave `frontend-conventions.md`：HTML 骨架、动态数据读取、API 发现链
