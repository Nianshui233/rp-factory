# 验收：六层证据，谁签哪一层

一个问题反复出现：**脚本跑绿了，就宣布「在酒馆里验证通过」**。实际上酒馆没开、iframe 没渲染、用户也没看过成品。事后复盘时谁也说不清「通过」是谁说的。

解法不是更严的自检，而是把结论按**来源**分层，并限制谁能签哪一层。账本落在 `创作痕迹/验收.yaml`，由 `scripts/check_acceptance.py` 检查。

---

## 一、六层

| 层 | 名称 | 证据形态 | 谁能签 |
|---|---|---|---|
| **L1** | 源码 / 机制 | 指向 ST 源码的 `文件:行` 或官方文档 URL + 日期 | 助手（必须给锚点） |
| **L2** | 脚本 | 命令 + 退出码（`validate-contract.py → exit 0`） | 助手 |
| **L3** | 离线快照 | 固定输入的期望输出比对（fixture 目录） | 助手 |
| **L4** | 浏览器 | 本机浏览器里渲染/交互的观察（未进酒馆） | 助手 |
| **L5** | 真机 ST | 导入、挂书、开局实跑、回读的观察 | **只能 human** |
| **L6** | 人眼 | 用户或作者自己读完成品给出的判断 | **只能 human** |

`A04` 就是这一条：L5 / L6 的 `by` 不是 `human` 直接判失败。**脚本自签等于没验**。

## 二、账本格式

```yaml
entries:
  - layer: L2
    item: 契约校验
    evidence: "python scripts/validate-contract.py 创作痕迹/contract.yaml → exit 0"
    verdict: pass
    by: script

  - layer: L1
    item: 正则分组语法
    evidence: "public/scripts/extensions/regex/engine.js:422（ST 1.19.0 / 06bde939f）"
    verdict: pass
    by: assistant

  - layer: L5
    item: 三件导入真机
    evidence: "手动导入后回读：卡在角色列表、书已挂到卡上、开局出现状态栏；截图 12:31"
    verdict: pass
    by: human

  - layer: L4
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

## 三、什么时候写

1. **阶段收尾**：把本阶段跑过的 L1–L4 结论各记一条（不用每条都记，记本次新增的）。
2. **交付门通过后**：`check-stage.py delivery` 全绿，记 L2；`validate_st_semantics.py` 的 S 系列同理。
3. **用户点头导入之后**：这是 L5 的唯一来源，`by` 必须是 `human`，`evidence` 写「看到了什么」而不是「跑通了」。
4. **用户说成品能用了**：L6。

## 四、和「真机验收」的关系

`scripts/st-import.py` + `scripts/st-probe.js` 是**流水线动作**：它们能把三件导入、能量 iframe 高度。但它们产出的是 L4 证据——机器看到的渲染，不是用户看到的成品。所以：

- 导入成功 → 记 L4 `pass`，**不要**顺手记 L5。
- 用户回「界面出来了，可以」→ 这才是 L5 / L6。
- 只有 L4 的交付，交付说明里必须写清「机器验过渲染，人还没看」。

## 五、常见糊弄与替代写法

| 糊弄 | 问题 | 换成 |
|---|---|---|
| 「已测试通过」 | 哪一层？谁签的？ | `L2: validate-st-package.py → exit 0` |
| 「界面正常」 | 机器渲染正常 ≠ 用户觉得能用 | L4 记渲染，L6 等用户说 |
| 「酒馆里没问题」但没截图/没描述 | 无法复核 | 写清看到什么：哪一屏、哪个标签、什么数值 |
| `skipped` 不写理由 | 下一轮没人知道为什么没跑 | `why: 本机没装酒馆助手` |
