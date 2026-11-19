---
name: rp-factory
description: 把 RP 构想编译成世界观、角色卡、场景卡、数值系统四类 YAML 设定产物，跨产物命名与硬设定保持一致；可选再产开局界面与状态栏两种酒馆前端（正则 + HTML），整条流程跑完可再打一个能直接导入 SillyTavern 的包（角色卡 JSON + 世界书 JSON + 正则）。支持粘贴用提示词条目与工程文件两种交付。仅在用户显式输入 /skill:rp-factory 时执行，不参与自然语言自动匹配。
disable-model-invocation: true
---

# RP-Factory

把 RP 构想编译成四类设定产物，需要前端时再产两个界面。本文件只管**判阶段、读写契约、派发纪律**——具体怎么做在阶段文件里，这里不复述。

## 一、路由

本 skill **只由 `/skill:rp-factory` 显式调用**，不做自然语言自动匹配——用户没输入斜杠命令就不接手。下表是**调用之后**按用户诉求判阶段用的，不是触发条件。

| 用户说的 | 进入 | 加载 |
|---|---|---|
| 「帮我做个世界观 / 世界观设定」 | 阶段 1 | `references/stage-1-world-bible.md` |
| 「设计一个角色 / 角色卡 / 人设」 | 阶段 2 | `references/stage-2-rolecard.md` |
| 「生成场景 / 地点卡 / 地图」 | 阶段 3 | `references/stage-3-scene-sheet.md` |
| 「好感度 / 堕落值 / 理智值 / 数值系统」 | 阶段 4 | `references/stage-4-axis-system.md` |
| 「开局界面 / 开场面板 / 首页 / 建卡向导 / 捏人」 | 阶段 5 | `references/stage-5-opening-ui.md` |
| 「状态栏 / 面板 / 每轮显示数值 / 血条」 | 阶段 6 | `references/stage-6-statusbar-ui.md` |
| 「打包 / 导入酒馆 / 要角色卡 json / 要世界书」 | 阶段 7（最后一个） | `references/stage-7-delivery.md` |
| 「做一张完整卡 / 一整套设定」 | 按 `project.stages_requested` 依次 | 按需逐个加载 |
| 只有模糊概念 | 阶段 0 判定后进入 | 先 `references/interview-protocol.md` |

判断不了就先按「只有模糊概念」处理：在开局第二问里让用户直接勾阶段，不猜。

## 二、开局四问（第一步）

**先问四件，一次问完，不分三轮。** 四件没问完，任何阶段都不动笔。

**问一：工作区在哪。** 问「项目放在哪个目录？」，给 2–3 个选项（当前目录 / 用户常用目录），每个选项说明会建成什么样，附一句「只要粘贴、不落文件也可以说一声」。确认后在其下建两层：

```
<工作区>/<世界名>/
  创作痕迹/  contract.yaml（命名权威+索引） · 项目档案.yaml（元信息+类型基调，不进终稿） · 创作记录.md（访谈、决策、卡点） · 检索来源.md（仅联网时）
  最终产物/  world-bible.yaml · rolecard.yaml · scene-sheet.yaml · axis-system.yaml · 表现层文件（按需）· st/（选了酒馆包才有）
```

- 名字未定 → 先建 `未命名项目/`，定名后重命名一次并回写 `project.name` 与 `project.workspace`；说「只要粘贴」→ `project.mode = text`，不建目录，此后不再问。
- 同名目录已存在 → 先列内容再问「续建还是换名」，**不覆盖**；`创作痕迹/` 不存 YAML 草稿副本，没跑到的阶段不预建空壳。

**问二：跑哪几个阶段（多选）**

六项可全选：`1 世界观` / `2 角色卡` / `3 场景卡` / `4 数值系统` / `5 开局前端` / `6 状态栏前端`。后两项是表现层，用户不懂就一句说明：需要装酒馆助手（JS-Slash-Runner），装了才有界面，没装只是代码块。**第七项（交付）不在这里问**，它排在最后（见第三节第 5 条与第十节）。

- 写 `project.stages_requested`（升序），未勾的在 `stages` 里写 `skipped`（本次不跑，不是没跑）。
- 执行顺序永远 1→2→3→4→5→6，不跳序；只勾下游而缺上游时，进该阶段走一次补采访问（≤3 问）。
- 一个都没勾 → 回问一次，仍不选按前四项走；中途加阶段 → 追加 `stages_requested`，把 `skipped` 改回 `none`，记 `decisions`。

**问三：启用 NSFW 内容吗**

- **否** → `nsfw: false`，`rating` 写一般向，`hard_no` 加「任何性描写」；阶段 2 不写 `nsfw` 块，自检门的内容边界层整类跳过。
- **是** → `nsfw: true`，`rating` 须给明确档位（`R15` / `R18`），`hard_no` 至少一条硬底线；阶段 2 可写 `nsfw` 块，内容边界层必执行。
- 不答 → 按「否」锁，一句告知可随时开；中途开关 → 改 `nsfw` + 重锁 `rating` + 记 `decisions`，关掉时已交付产物里的越界内容必须清掉。

**问四：需要联网吗**（是/否，问这次创作要不要主动查外部资料，与是否同人无关）

- **否** → `project.web_research: false`，全程不检索，也不许顺手搜。
- **是** → `project.web_research: true`，**不再问任何东西**。此后不管创作什么（世界观、角色、场景、数值、界面，含局部修改），落笔前都先检索再用；每条记进 `创作痕迹/检索来源.md`（骨架 `templates/research-log.md`）。查什么由阶段内容自己判断，冲突怎么裁、没网怎么降级、版权边界，全在 `references/web-research.md`——**进入任何阶段前先读它**。
- 不答 → 按「否」锁，一句告知可随时开。中途要开 → 回填开关、建检索记录、从当前阶段起开始查，记 `decisions`。

四问用结构化选项，**不用** `references/interview-protocol.md` 的问题块格式。写回细节见 `references/contract-schema.md` 第七节。

## 三、开工前

1. 读 `references/pipeline.md`：阶段表、7 个占位符、八道门、输出纪律。**这是唯一的公共脊，任何阶段文件里没有的东西都回这里查。**
2. 有契约就读契约（`templates/contract.yaml` + `references/contract-schema.md`）；没有就先建一份。
3. `project.web_research: true` → 先读 `references/web-research.md`，再进阶段（否则跳过，也不许搜）。
4. 定出**目标阶段**与**当前产物 type**（八选一：`world-bible` / `rolecard` / `scene-sheet` / `axis-system` / `opening-ui` / `statusbar-ui` / `st-card` / `st-worldbook`）；文本还是工程文件按 `references/dual-mode.md` 判，默认文本模态。
5. **收尾一步不要忘**：`stages_requested` 里的阶段全部结束后问一次交付形态（原生 / 酒馆包 / 两者都要），选酒馆包进阶段 7；用户没答按原生收尾，不自作主张打包。

## 四、做主 skill 的三件事

判阶段（目标阶段、有无前置产物、够不够开工）· 读写契约（`naming` 与 `hard_settings` 是权威，阶段文件要写已存在的键就停下问，不许静默覆盖）· 派发纪律（只加载当前阶段文件，由它决定问什么、怎么写、怎么退出）。

## 五、不做的事

不生成设定内容（世界、角色、场景、数值、界面全由阶段文件产出）；不替用户拍板硬设定；不重复 stage 文件里的规则（一旦本文件开始复述字段规范就是错的，删掉改成引用）；不预加载其他阶段文件。

## 六、硬门

0. **开局门**：先问四件——工作区、跑哪几个阶段（多选）、是否启用 NSFW、是否需要联网。四件都确认前不建目录、不落文件、不开工；NSFW 与联网不答都按「否」锁。
1. **边界门**：由开局门锁定 `content_boundaries`（`nsfw` + `rating` + `hard_no`）。阶段内只在必要时补问边界细节（≤2 题）。未锁定不产出任何设定正文。
2. **命名门**：交付前按 `references/pipeline.md` 四步核对契约与产物，名字不一致就停下问用户。
3. **补采访问**：上游缺项先补采访问（≤3 问），问不到才写 `[待定：<缺什么>]`。
4. **零回溯**：不引用任何包外路径、不登记源文件名。本包自包含，删掉任何外部文件都不影响运行。
5. **自检门**：每份设定产物交付前内部执行四类检查，不向用户展示检查过程。
6. **联网门（仅 `web_research: true`）**：每次落笔前先检索（不限阶段、含局部改动）、交付前复核一遍外部专名；查不到就记 `未检索到` 并改走确认清单，**不编造外部事实**。
7. **前端门（仅阶段 5 / 6）**：交付前按 `references/frontend-conventions.md` 第六节八条自检——标签三处一致、字段两处一致、`markdownOnly: true`、代码块含 `<body>`、数据路径自洽、无外链无 `eval`、无标签时留白、脏值转义。
8. **交付门（仅阶段 7）**：先跑 `python scripts/validate-st-package.py <卡> <世界书>`，退出码 0 才算过；脚本查六件事——两个 JSON 可解析且 `spec == "chara_card_v2"`；世界书条目 `content` 非空 / `key` 是数组 / `position` ∈ 0–7 / `uid` 与键一致；`extensions.world` == 世界书文件名；每条 `findRegex` 能用 JS 编译且 `$1` 与捕获组对得上；`first_mes` 的标签能被某个正则接住；常驻条目 ≤ 5000 字、关键词无重复。脚本挡不住的再肉眼过两条（`description` 的实体名都在 `naming` 里、导入四步齐全）。

## 七、文件索引

| 文件 | 管什么 |
|---|---|
| `references/pipeline.md` | 阶段表、占位符、八道门、自检四类、命名门四步、输出纪律 |
| `references/interview-protocol.md` | 问题块格式、每阶段预算、补采访问、降级链 |
| `references/contract-schema.md` | 契约定位、键区、独占写者、冲突规则 |
| `references/dual-mode.md` | 两种模态的对照、切换、渲染、注释剥离 |
| `references/web-research.md` | 联网检索：何时查、怎么记、冲突怎么裁、没网怎么降级 |
| `references/frontend-conventions.md` | 表现层机制、HTML 骨架、正则 JSON、提示词条目、前端门 |
| `references/stage-1-world-bible.md` … `stage-4-axis-system.md` | 阶段 1–4：世界观 / 角色卡 / 场景卡 / 数值系统 |
| `references/stage-5-opening-ui.md` | 阶段 5 开局前端（登场面板 / 建卡向导两形态） |
| `references/stage-6-statusbar-ui.md` | 阶段 6 状态栏前端 |
| `references/stage-7-delivery.md` | 阶段 7 交付：原生 / 酒馆包两条路线，世界书切法、角色卡字段、导入四步 |
| `templates/*.yaml` | 契约 + 四份产物 + 项目档案，填完即交付（项目档案归 `创作痕迹/`，不进终稿） |
| `templates/*.html` / `regex-frontend.json` / `frontend-prompt.yaml` | 三个界面骨架、正则导入骨架、提示词条目骨架 |
| `templates/st-card.json` / `st-worldbook.json` · `scripts/validate-st-package.py` | 酒馆包两个 JSON 骨架 + 校验器（交付门用它把关） |

## 八、阶段文件约定

每个 `stage-*.md` 六节，顺序固定：`## 进入条件` / `## 追问` / `## 判断标准` / `## 生成` / `## 写回契约` / `## 退出`。缺 `## 进入条件` 的阶段文件不许存在。

## 九、交付形态

- 文本模态：设定产物是一个 ```yaml 代码块，块外只允许设计说明、补全清单、待确认清单、运行示例；工程模态写进 `<工作区>/<世界名>/最终产物/`，每个产物一个文件。
- 表现层例外：两个前端交付 **HTML（完整文档）+ 正则 JSON + 提示词条目 YAML** 三个代码块 / 三个文件；HTML 与 JSON 是对 ST 与酒馆助手的落地件，不套 YAML 骨架。
- 打包例外：阶段 7 的 `st-card` / `st-worldbook` 是 JSON，落在 `最终产物/st/`，两个文件加四步导入说明；原生路线不受影响，YAML 与 HTML 原样保留。
细节在 `references/dual-mode.md`；改模态只换渲染目标，不重跑阶段。

## 十、收尾问（最后才问）

`project.stages_requested` 里的阶段全部 `done` 之后，**问一次、只问一次**：原生产物（默认，维持 `最终产物/` 现状）/ SillyTavern 包（`<世界名>.json` 角色卡 v2 + `<世界名> 世界书.json`，外带 `regex-*.json` 与 HTML）/ 两者都要。

- 写 `delivery.route` 为 `native` / `st` / `both`；选酒馆包才进阶段 7，选原生就把 `stages.7` 写 `skipped`。
- 不问名字（默认 `project.name`）、不问放哪（`最终产物/st/`）、不生成头像。
- 用户没说“打包 / 导入酒馆 / 要角色卡 json / 要世界书”就不要主动提，原生是默认。
- 中途就要包也行，但必须先跑完已勾阶段；有 `partial` 先问“先打包还是补完”。
