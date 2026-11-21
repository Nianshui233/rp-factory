# 验收：六层证据，谁签哪一层

一个问题反复出现：**脚本跑绿了，就宣布「在酒馆里验证通过」**。实际上酒馆没开、iframe 没渲染、用户也没看过成品。事后复盘时谁也说不清「通过」是谁说的。

解法不是更严的自检，而是把结论按**来源**分层，并限制谁能签哪一层。账本落在 `制作文件/项目记录/验收.yaml`，由 `scripts/check_acceptance.py` 检查。

---

## 一、六层

| 层 | 名称 | 证据形态 | 谁能签 |
|---|---|---|---|
| **L1** | 源码 / 机制 | 指向 ST 源码的 `文件:行` 或官方文档 URL + 日期 | 助手（必须给锚点） |
| **L2** | 脚本 | 命令 + 退出码（`validate-contract.py → exit 0`） | 助手 |
| **L3** | 离线快照 | 固定输入的期望输出比对（fixture 目录） | 助手 |
| **L4** | 浏览器 | 本机浏览器里渲染/交互的观察（未进酒馆），**必须写 `dimension`** | 助手 |
| **L5** | 真机 ST | 导入、挂书、开局实跑、回读的观察 | **只能 human** |
| **L6** | 人眼 | 用户或作者自己读完成品给出的判断 | **只能 human** |

`A04` 就是这一条：L5 / L6 的 `by` 不是 `human` 直接判失败。**脚本自签等于没验**。

---

## 二、账本格式

L4 条目比其它层多一个必填字段 `dimension`（见第三节）。

```yaml
entries:
  - layer: L2
    item: 契约校验
    evidence: "python scripts/validate-contract.py 制作文件/项目记录/contract.yaml → exit 0"
    verdict: pass
    by: script

  - layer: L1
    item: 正则分组语法
    evidence: "public/scripts/extensions/regex/engine.js:422（ST 1.19.0 / 06bde939f）"
    verdict: pass
    by: assistant

  - layer: L4
    dimension: dom
    item: 状态栏挂载
    evidence: "st-probe 报 1 个 iframe、高 412px、preCount 0、页面错误 0"
    verdict: pass
    by: assistant

  - layer: L5
    item: 三件导入真机
    evidence: "手动导入后回读：卡在角色列表、书已挂到卡上、开局出现状态栏；截图 12:31"
    verdict: pass
    by: human

  - layer: L4
    dimension: responsive
    item: 状态栏在窄屏下的布局
    evidence: "没测：本机没有手机视口"
    verdict: skipped
    why: 用户只要桌面端
```

规则（`check_acceptance.py` 逐条查）：

- `A01` `layer` 只能是 L1–L6。
- `A02` `verdict` 只能是 `pass` / `fail` / `skipped`；`skipped` 必须写 `why`。
- `A03` L1 / L2 的证据必须带退出码或锚点形态——「看起来没问题」不算证据。
- `A04` L5 / L6 只能 human 签。
- `A05` 整本账没有 L5 或 L6 的 `pass` → 警告：没人看过成品。
- `A06` L4 必须写 `dimension`，且值在下面 11 项内。

---

## 三、L4 十一维

L4 是最容易糊弄的一层：「浏览器里看着行」不说明行在**哪一维**。所以 L4 每条必须写 `dimension`，只记这次改动相关的那几维——十一维全填一遍，账本会变成没人读的清单。

前四维脚本能抓，`st-probe.js --json` 直接产出这四个键；其余七维只能人看，看了写看到什么。

| dimension | 写什么 | 谁抓 |
|---|---|---|
| `import` | 卡在侧栏、名字与版本对得上 | 脚本 |
| `fresh_chat` | 新聊天首条消息真渲染出内容，不是空壳 | 脚本 |
| `console` | 没有新增因果错误或未处理 rejection | 脚本 |
| `dom` | 挂载数量对、无重复挂载、没有裸代码块漏出 | 脚本 |
| `dependencies` | 宿主扩展、嵌入脚本、远端加载器按台账到位 | 人 |
| `style` | 计算尺寸、`display`、`overflow`、类名变换 | 人 |
| `interaction` | 点击 / 键盘 / 表单 / 关闭 / 重复操作 | 人 |
| `data` | 改的是目标楼层与作用域，回读确认已持久化 | 人 |
| `lifecycle` | 重载、滑铲、编辑、切聊天不丢行为、不重复挂载 | 人 |
| `responsive` | 窄屏与宽屏、长中文不裁切 | 人 |
| `security` | 用户 / 模型文本保持惰性，无密钥外泄 | 人 |

`prototype` 不算一维：为定位问题临时注入的 DOM 或脚本不是交付物，用完要撤，撤完从干净状态重跑。

### 脚本怎么交这四维

```
node scripts/st-probe.js --char 白潮 --json --report 制作文件/probe.json
```

报告里 `dimensions` 是四个键，直接对应上表的 `import` / `fresh_chat` / `console` / `dom`，每项带 `ok` 与 `detail`。写账本时抄 `detail`，不要重写成「正常」。

---

## 四、什么时候写

1. **阶段收尾**：把本阶段跑过的 L1–L4 结论各记一条（不用每条都记，记本次新增的）。
2. **交付门通过后**：`check-stage.py delivery` 全绿，记 L2；`validate_st_semantics.py` 的 S 系列同理。
3. **用户点头导入之后**：这是 L5 的唯一来源，`by` 必须是 `human`，`evidence` 写「看到了什么」而不是「跑通了」。
4. **用户说成品能用了**：L6。

---

## 五、和「真机验收」的关系

`scripts/st-import.py` + `scripts/st-probe.js` 是**流水线动作**：它们能把三件导入、能量 iframe 高度、能抓控制台错误、能数挂载。但它们产出的是 L4 证据——机器看到的渲染，不是用户看到的成品。所以：

- 导入成功 → 记 L4 `pass`（`dimension: import`），**不要**顺手记 L5。
- 用户回「界面出来了，可以」→ 这才是 L5 / L6。
- 只有 L4 的交付，交付说明里必须写清「机器验过渲染，人还没看」。

---

## 六、常见糊弄与替代写法

| 糊弄 | 问题 | 换成 |
|---|---|---|
| 「已测试通过」 | 哪一层？谁签的？ | `L2: validate-st-package.py → exit 0` |
| 「界面正常」 | 机器渲染正常 ≠ 用户觉得能用 | L4 记 `dom`，L6 等用户说 |
| 「酒馆里没问题」但没截图/没描述 | 无法复核 | 写清看到什么：哪一屏、哪个标签、什么数值 |
| L4 只写「渲染正常」 | 渲染正常在哪一维？ | `dimension: dom` + 数字（iframe 数、高度、preCount） |
| `skipped` 不写理由 | 下一轮没人知道为什么没跑 | `why: 本机没装酒馆助手` |
