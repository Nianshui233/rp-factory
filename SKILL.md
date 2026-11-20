---
name: rp-factory
description: 把 RP 构想编译成世界观、角色卡、场景卡、数值系统四类 YAML 设定产物，跨产物命名与硬设定保持一致；可选把数值投影成酒馆变量系统（MVU 的 zod 结构 + 初始化 + 更新条目）与按数值切换的分档控制器（EJS），可选再产开局界面与状态栏两种酒馆前端（正则 + HTML），整条流程跑完可再打一个能直接导入 SillyTavern 的包（角色卡 JSON + 世界书 JSON + 正则）。支持粘贴用提示词条目与工程文件两种交付。仅在用户显式输入 /skill:rp-factory 时执行，不参与自然语言自动匹配。
disable-model-invocation: true
---

# RP-Factory

把 RP 构想编译成四类设定产物，需要前端时再产两个界面。本文件只管**判阶段、读写契约、派发纪律**——具体怎么做在阶段文件里，这里不复述。

## 一、路由

本 skill **只由 `/skill:rp-factory` 显式调用**，不做自然语言自动匹配——用户没输入斜杠命令就不接手。下表是**调用之后**按用户诉求判阶段用的，不是触发条件。

| 用户说的 | 进入 | 加载 |
|---|---|---|
| 「帮我做个世界观 / 世界观设定」 | 阶段 `world` | `references/stage-1-world-bible.md` |
| 「设计一个角色 / 角色卡 / 人设」 | 阶段 `cast` | `references/stage-2-rolecard.md` |
| 「生成场景 / 地点卡 / 地图」 | 阶段 `scenes` | `references/stage-3-scene-sheet.md` |
| 「好感度 / 堕落值 / 理智值 / 数值系统」 | 阶段 `axes` | `references/stage-4-axis-system.md` |
| 「数值要记住 / 变量自己更新 / 变量管理器」 | 阶段 `mvu` | `references/stage-mvu.md` |
| 「按数值换人设 / 分档人设 / 到某档就换一套说法」 | 阶段 `ejs` | `references/stage-ejs.md` |
| 「开局界面 / 开场面板 / 首页 / 建卡向导 / 捏人」 | 阶段 `opening` | `references/stage-5-opening-ui.md` |
| 「状态栏 / 面板 / 每轮显示数值 / 血条」 | 阶段 `statusbar` | `references/stage-6-statusbar-ui.md` |
| 「打包 / 导入酒馆 / 要角色卡 json / 要世界书」 | 阶段 `delivery`（最后一个） | `references/stage-7-delivery.md` |
| 「做一张完整卡 / 一整套设定」 | 按 `project.stages_requested` 依次 | 按需逐个加载 |
| 只有模糊概念 | 阶段 0 判定后进入 | 先 `references/interview-protocol.md` |

判断不了就先按「只有模糊概念」处理：在开局第二问里让用户直接勾阶段，不猜。

## 二、开局四问（第一步）

**先问四件，一次问完，不分三轮。** 四件没问完，任何阶段都不动笔。

**问之前先静默探一次环境**：跑 `python scripts/detect-sillytavern.py --quiet`，**不报给用户、不占问题预算**；结果写进契约 `project.sillytavern`（安装目录 / 用户目录 / 是否在跑 / 版本 / 有没有酒馆助手），探不到就写 `null`。只有 `opening` / `statusbar` / `delivery` 真的要用它时才提。

**问一：工作区在哪。** 问「项目放在哪个目录？」，给 2–3 个选项（当前目录 / 用户常用目录），每个选项说明会建成什么样，附一句「只要粘贴、不落文件也可以说一声」。确认后在其下建两层：

```
<工作区>/<世界名>/
  创作痕迹/  contract.yaml（命名权威+索引） · 项目档案.yaml（元信息+类型基调，不进终稿） · 创作记录.md（访谈、决策、卡点） · 检索来源.md（仅联网时）
  创作痕迹/产物/  world-bible.yaml · rolecard/ · scene/ · axis/ · mvu/（schema 与条目） · ejs/（控制器与改写清单） · 表现层 HTML 与正则（过程产物一律在这）
  最终产物/  全程空着，只在第十节交付时写入
```

- 名字未定 → 先建 `未命名项目/`，定名后重命名一次并回写 `project.name` 与 `project.workspace`；说「只要粘贴」→ `project.mode = text`，不建目录，此后不再问。
- 同名目录已存在 → 先列内容再问「续建还是换名」，**不覆盖**；`创作痕迹/` 不存 YAML 草稿副本，没跑到的阶段不预建空壳。

**问二：跑哪几个阶段（多选）**

八项可全选，按执行顺序列：`world 世界观` / `cast 角色卡` / `scenes 场景卡` / `axes 数值系统` / `mvu 变量系统` / `ejs 分档控制器` / `opening 开局前端` / `statusbar 状态栏前端`。用户不懂就一句说明：`mvu` 要装酒馆助手（JS-Slash-Runner）才会跑，`ejs` 还要 Prompt Template，`opening`/`statusbar` 是界面——没装时产物仍是文件，只是不会自动生效。**第九项（`delivery` 交付）不在这里问**，它排在最后（见第三节第 5 条与第十节）。

- 写 `project.stages_requested`（按执行顺序写**名字**），未勾的在 `stages` 里写 `skipped`（本次不跑，不是没跑）。
- 执行顺序永远 `world → cast → scenes → axes → mvu → ejs → opening → statusbar`，不跳序；`mvu` 必须在 `ejs` 前。只勾下游而缺上游时，进该阶段走一次补采访问（≤3 问）。
- 一个都没勾 → 回问一次，仍不选按前四项走；中途加阶段 → 追加 `stages_requested`，把 `skipped` 改回 `none`，记 `decisions`。

**问三：启用 NSFW 内容吗**

- **否** → `nsfw: false`，`rating` 写一般向，`hard_no` 加「任何性描写」；阶段 2 不写 `nsfw` 块，自检门的内容边界层整类跳过。
- **是** → `nsfw: true`，`rating` 须给明确档位（`R15` / `R18`），`hard_no` 至少一条硬底线。**阶段 2 每张角色卡必须有 `nsfw` 块且七键齐全**——卡里没有块视为这一阶段没做完，自检门的内容边界层直接判失败，不是跳过。
- 不答 → 按「否」锁，一句告知可随时开；中途开关 → 改 `nsfw` + 重锁 `rating` + 记 `decisions`，关掉时已交付产物里的越界内容必须清掉。

**问四：需要联网吗**（是/否，问这次创作要不要主动查外部资料，与是否同人无关）

- **否** → `project.web_research: false`，全程不检索，也不许顺手搜。
- **是** → `project.web_research: true`，**不再问任何东西**。此后不管创作什么（世界观、角色、场景、数值、界面，含局部修改），落笔前都先检索再用；每条记进 `创作痕迹/检索来源.md`（骨架 `templates/research-log.md`）。查什么由阶段内容自己判断，冲突怎么裁、没网怎么降级、版权边界，全在 `references/web-research.md`——**进入任何阶段前先读它**。
- 不答 → 按「否」锁，一句告知可随时开。中途要开 → 回填开关、建检索记录、从当前阶段起开始查，记 `decisions`。
- **开了这个开关，检索就是每个阶段的前置动作**，不是想起来才做：动笔前按 `references/web-research.md` 第一节的逐阶段检索量查完并落条；交付前 `创作痕迹/检索来源.md` 必须比进入本阶段时多出至少 1 条，否则不许交付、不许进下一阶段。

四问用结构化选项，**不用** `references/interview-protocol.md` 的问题块格式。写回细节见 `references/contract-schema.md` 第七节。

## 三、开工前

1. 读 `references/pipeline.md`：阶段表、7 个占位符、十四道门、输出纪律。**这是唯一的公共脊，任何阶段文件里没有的东西都回这里查。**
2. 有契约就读契约（`templates/contract.yaml` + `references/contract-schema.md`）；没有就先建一份。
3. `project.web_research: true` → 先读 `references/web-research.md`，再进阶段（否则跳过，也不许搜）。
4. 定出**目标阶段**与**当前产物 type**（十四选一：`world-bible` / `rolecard` / `scene-sheet` / `axis-system` / `mvu-schema` / `mvu-initvar` / `mvu-entries` / `mvu-regex` / `ejs-controller` / `opening-ui` / `statusbar-ui` / `st-card` / `st-regex` / `st-worldbook`）；文本还是工程文件按 `references/dual-mode.md` 判，默认文本模态。
5. **收尾一步不要忘**：`stages_requested` 里的阶段全部结束后问一次交付形态（原生 / 酒馆包 / 两者都要），选酒馆包进 `delivery`；用户没答按原生收尾，不自作主张打包。
6. **一次只做一个阶段**：做完就停——汇总这一轮落下什么、把产物摆出来、写清「下一步是哪一阶段、等你说一声」。**不在同一条回复里连着做下一个阶段**，也不在交付后用选项弹窗替用户按下一步（见第六节第 9 条）。

## 四、做主 skill 的三件事

判阶段（目标阶段、有无前置产物、够不够开工）· 读写契约（`naming` 与 `hard_settings` 是权威，阶段文件要写已存在的键就停下问，不许静默覆盖）· 派发纪律（只加载当前阶段文件，由它决定问什么、怎么写、怎么退出）。

## 五、不做的事

不生成设定内容（世界、角色、场景、数值、界面全由阶段文件产出）；不替用户拍板硬设定；不重复 stage 文件里的规则（一旦本文件开始复述字段规范就是错的，删掉改成引用）；不预加载其他阶段文件。

## 六、硬门

十四道门，编号与判据以 `references/pipeline.md` 第三节为唯一权威，本表只做索引（细则、脚本参数、事故现场都在那份文件里）。

| # | 门 | 一句话判据 |
|---|---|---|
| 0 | 开工门 | 工作区 / 阶段 / NSFW / 联网四件确认后才动笔；NSFW 与联网不答按「否」锁 |
| 1 | 边界门 | `nsfw` + `rating` + `hard_no` 锁定前不产出任何设定正文 |
| 2 | 收敛门 | 仅 `world`：四要素齐、判定框架填、张力已定、无致命缺口 |
| 3 | 补采访问 | 上游缺项先问 ≤3 问，问不到才写 `[待定：…]` |
| 4 | 零回溯 | 不引用包外路径、不登记源文件名 |
| 5 | 自检门 | 每份产物交付前内部四类检查；正文不许留构建期占位符 |
| 6 | 命名门 | 交付前四步核对契约与产物，不一致就停下问 |
| 7 | 契约门 | 阶段收尾一检里跑 `validate-contract.py`，退出码 0 |
| 8 | 联网门 | 仅 `web_research: true`：落笔前检索、交付前复核、查不到记 `未检索到` |
| 9 | 前端门 | 仅 `opening`/`statusbar`：十条 + `validate-frontend.py` |
| 10 | 变量门 | 仅 `mvu`/`ejs`：`validate-mvu.py` / `validate-ejs.py`；没装助手别开 |
| 11 | 交付门 | 仅 `delivery`：`check-stage.py delivery` 退出码 0 |
| 12 | 阶段门 | 一次只推进一个阶段，做完就跑一检、然后停下等用户 |
| 13 | 自创字段门 | 新键先问、记 `decisions`；不许替换模板既有块 |

一条总则：**门是判定，不是提醒**——能交给脚本的都不许靠肉眼看（脚本清单见第七节）。

## 七、文件索引

| 文件 | 管什么 |
|---|---|
| `references/pipeline.md` | 阶段表、占位符、十四道门、自检四类、命名门四步、输出纪律 |
| `references/interview-protocol.md` | 问题块格式、每阶段预算、补采访问、降级链 |
| `references/contract-schema.md` | 契约定位、键区、独占写者、冲突规则 |
| `references/decisions.md` | 四态（confirmed / proposed / pending / rejected）、缺口三级、未答≠委托、交付四句 |
| `references/dual-mode.md` | 两种模态的对照、切换、渲染、注释剥离 |
| `references/st-correctness.md` | 会静默失效的 ST 语义事实（S-01…S-M3）：正则/世界书/卡/宏四类，每条带 `public/…:line` 源码锚点 |
| `references/frontend-conventions.md` | 表现层机制、HTML 骨架、正则 JSON、提示词条目、前端门 |
| `references/stage-1-world-bible.md` … `stage-4-axis-system.md` | 阶段 `world` / `cast` / `scenes` / `axes`：世界观 / 角色卡 / 场景卡 / 数值系统 |
| `references/stage-mvu.md` | 阶段 `mvu`：轴 → zod 结构 / `[initvar]` / 三条更新条目 / 两条隐藏正则 / 卡内脚本 |
| `references/stage-ejs.md` | 阶段 `ejs`：分档控制器 + 被控条目（含"什么时候不做"的判据） |
| `references/stage-5-opening-ui.md` | 阶段 `opening` 开局前端（登场面板 / 建卡向导两形态） |
| `references/stage-6-statusbar-ui.md` | 阶段 `statusbar` 状态栏前端（有 MVU 走变量、没有走标签） |
| `references/stage-7-delivery.md` + `worldbook-tuning.md` | 阶段 `delivery` 交付：两条路线、世界书切法、卡字段、导入四步；调优看 tuning（三灯、套餐、8–15 关键词、位置、预算、递归、概率、十二条自查） |
| `templates/*.yaml` | 契约 + 四份产物 + 项目档案，填完即交付（项目档案归 `创作痕迹/`，不进终稿） |
| `templates/*.html` / `regex-frontend.json` / `frontend-prompt.yaml` | 三个界面骨架、正则导入骨架、提示词条目骨架 |
| `templates/mvu-schema.js` / `mvu-initvar.yaml` / `mvu-entries.yaml` / `regex-mvu.json` / `tavern-script.json` / `ejs-controller.ejs` | 变量系统的五份骨架 + 分档控制器 |
| `scripts/check-stage.py` · `detect-sillytavern.py` · `st-import.py` · `st-probe.js` | 阶段收尾一检（按阶段自动调下面这些校验器）、环境探测、导入酒馆并实测 |
| `templates/st-card.json` / `regex-frontend.json` / `st-worldbook.json` · `scripts/validate-contract.py` · `validate-rolecard.py` · `validate-st-package.py` · `validate-frontend.py` · `validate-mvu.py` · `validate-ejs.py` · `validate_st_semantics.py` | 三件套骨架（纯净卡 / 正则数组 / native 世界书）+ 七个校验器（由 `check-stage.py` 在阶段收尾统一调用） |
| `scripts/detect-sillytavern.py` / `st-import.py` / `st-probe.js` | 找酒馆 → 导入 → 真机验收（探测静默跑；导入与验收只在用户点头后跑） |
| `scripts/check_prose.py` | P01–P08 去 AI 味提示（解释腔 / 情绪直说 / 陈词比喻 / 模板标签），自检门顺手跑 |
| `scripts/check_st_facts.py` + `tests/` | 复核 `st-correctness.md` 的源码锚点、加载量预算、全套单测（改完跑 `python -m unittest discover -s tests -t .`） |

## 八、阶段文件约定

每个 `stage-*.md` 六节，顺序固定：`## 进入条件` / `## 追问` / `## 判断标准` / `## 生成` / `## 写回契约` / `## 退出`。缺 `## 进入条件` 的阶段文件不许存在。

## 九、交付形态

- 文本模态：设定产物是一个 ```yaml 代码块，块外只允许设计说明、补全清单、待确认清单、运行示例；工程模态写进 `<工作区>/<世界名>/创作痕迹/产物/`，每个产物一个文件。**`最终产物/` 在交付前必须空着**——那是交付目录，不是工作目录。
- 表现层例外：两个前端交付 **HTML（完整文档）+ 正则 JSON + 提示词条目 YAML** 三个代码块 / 三个文件；HTML 与 JSON 是对 ST 与酒馆助手的落地件，不套 YAML 骨架。
- 打包例外：`delivery` 阶段交**三件 JSON**（`<世界名>（纯净）.json` / `正则.json` / `<世界名> 世界书.json`），落在 `最终产物/` 根下，用户自己装配；`创作痕迹/产物/` 里的 YAML 与 HTML 原样保留。
细节在 `references/dual-mode.md`；改模态只换渲染目标，不重跑阶段。

## 十、收尾问（最后才问）

`project.stages_requested` 里的阶段全部 `done` 之后，**问一次、只问一次**：原生产物（默认，把 `创作痕迹/产物/` 复制进 `最终产物/`）/ SillyTavern 三件套（`<世界名>（纯净）.json` + `正则.json` + `<世界名> 世界书.json`，用户自己装配）/ 两者都要。

- 写 `delivery.route` 为 `native` / `st` / `both`；选酒馆包才进 `delivery`，选原生就把 `stages.delivery` 写 `skipped`。
- 不问名字（默认 `project.name`）、不问放哪（`最终产物/` 根下）、不生成头像。
- 用户没说“打包 / 导入酒馆 / 要角色卡 json / 要世界书”就不要主动提，原生是默认。
- 中途就要包也行，但必须先跑完已勾阶段；有 `partial` 先问“先打包还是补完”。

**路线问完，只要答案里有酒馆包，再问第二句：要不要我直接导进你正在跑的酒馆并实测。**

| 选择 | 做什么 |
|---|---|
| 要（推荐） | 先 `python scripts/validate-st-package.py`，再 `python scripts/st-import.py --st auto --card <卡>`（同名覆盖，导入后回读自检），有界面再 `node scripts/st-probe.js --char <卡名>` 量 iframe 高度；把 PASS / WARN 原样报给用户，界面上有确认框也一并说明 |
| 不要 | 只交文件 + 四句话（正则怎么导入、渲染开关在哪、世界书要不要单独导、触发词该出现在哪条消息） |

- `project.sillytavern.running_url` 为空（没在跑）或整段是 `null` → **不问这一句**，直接说“现在没有在跑的实例，启动后要我导也说一声”。
- 导入实测属于交付的一部分：用户答“要”时，没做成就不算交付完，要把卡在哪一步说清。
