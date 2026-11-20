<p align="center">
  <img src="https://img.shields.io/badge/version-1.1.00-blue?style=flat" alt="version" />
  <img src="https://img.shields.io/badge/tests-161%20passing-brightgreen?style=flat" alt="tests" />
  <img src="https://img.shields.io/badge/gates-14-8A2BE2?style=flat" alt="gates" />
  <img src="https://img.shields.io/badge/stages-9-ff69b4?style=flat" alt="stages" />
  <img src="https://img.shields.io/badge/SillyTavern-1.19.0-4EAA25?style=flat" alt="SillyTavern" />
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white" alt="python" />
  <img src="https://img.shields.io/badge/format-Agent%20Skill-000000?style=flat" alt="skill" />
</p>

<p align="center">
  <strong>RP-Factory</strong> — 把「我想做个 RP」编译成能直接导入 SillyTavern 的包。
</p>

> [!WARNING]
> **只从这一个仓库安装。** RP-Factory 是自用工具，没有 npm 包、没有市场条目、没有多语言镜像站。任何第三方转存、二次打包的副本都与本仓库无关，作者不审阅、不维护。安装方式只有两种：把本目录放进 skill 搜索路径，或用一个 junction 指过来。

## 装到 Pi

```bash
# 方式一（推荐）：junction 指向工作树，改完立刻生效
cmd //c mklink /J "C:\Users\<你>\.agents\skills\rp-factory" "D:\path\to\rp-factory"

# 方式二：拷一份快照（不会跟着改动更新）
cp -a rp-factory "C:\Users\<你>\.agents\skills\"
```

装完在会话里敲 `/skill:rp-factory`，不敲斜杠不会触发（`disable-model-invocation: true`）。

<details>
<summary><strong>为什么默认不自动触发</strong></summary>

这是一个**会写文件、会建目录、会花十几轮对话**的流程型 skill。自然语言里提到「角色卡」「世界观」的场合太多，自动匹配会把普通聊天拐进建卡流程。所以它只在显式调用时启动，`SKILL.md` 第一行就锁死了这条。

`/skill:rp-factory` 之后，用表格里的阶段关键字（见[开始用](#开始用)）决定跳到哪一步，不问「你想做什么」。
</details>

<details>
<summary><strong>junction 的副作用</strong></summary>

用 junction 时，skill 目录下还能看到 `node_modules/`（真机验收用的 `puppeteer-core`，约 32 MB）、`tests/`、`docs/`、`.git/`。Pi 只读 `SKILL.md` 与它按需加载的 `references/`，其余文件不会被读进上下文，但它们在盘上。

换成拷贝就看不到这些，代价是每次改完要重新拷。
</details>

# RP-Factory

模型能写角色卡，但它不知道角色卡的 `first_mes` 该多长、`alternate_greetings` 什么时候才该有、正则写进卡里会不会静默失效、世界书导进去为什么一条都不触发。RP-Factory 给的是一套**带证据的编译流程**：先定契约，再逐阶段产设定，每一步有判据、有校验器、有源码锚点，最后能打成一个真能导入的包。

```text
判阶段 → 定契约 → world → cast → scenes → axes → mvu → ejs → opening → statusbar → delivery
```

一次只做一个阶段。做完就停，把产物摆出来，等你说下一步。

> 门是判定，不是提醒。能交给脚本的，都不许靠肉眼看。

MIT 精神的自用工具，无担保。**它不能替你保证「好玩」**——那是人眼的事；它保证的是「不静默坏掉」：字段名对不对、正则会不会一声不响地被跳过、世界书会不会因为书名不匹配而一条都不挂、界面会不会只剩一段代码块。

| 内容 | 数量 | 给你什么 |
| --- | ---: | --- |
| 阶段 | 9 个 | `world` / `cast` / `scenes` / `axes` / `mvu` / `ejs` / `opening` / `statusbar` / `delivery` |
| 硬门 | 14 道 | 从开工门到自创字段门，编号 0–13，判据只写在 `references/pipeline.md` |
| 参考页 | 22 份 | 阶段做法、契约规范、ST 语义事实、酒馆助手接口、验收、试演、去 AI 味 |
| 骨架 | 21 份 | 契约 + 四类设定 + MVU 五件 + 两个界面 + 三件套，填完即交付 |
| 校验器 | 9 个 + 1 个总检 | 结构、语义、前端、变量、EJS、验收账本；`check-stage.py` 按阶段自动挑 |
| 断言 | 责任分散但**可数** | `C01–C17` / `R00–R06` / `W00–W16` / `X01–X07` / `S-01–S-29+S-M1–M3` / `TH-01–TH-10` / `F01–F14` / `P01–P09` / `A00–A06` |
| 单测 | 161 个 | `python -m unittest discover -s tests -t .` |
| 源码锚点 | 44 条 | 34 条 ST 1.19.0 + 10 条酒馆助手 4.12.1，漂了会红 |

## 开始用

先看你要做什么，不用看全目录。

| 你在做什么 | 从这里开始 |
| --- | --- |
| 只有个模糊概念 | `/skill:rp-factory`，进入阶段 0 判定 |
| 想要一个世界观 | 说「世界观设定」→ 阶段 `world` |
| 设计角色 / 人设 | 说「角色卡」→ 阶段 `cast` |
| 想要地点、地图、场景 | 说「场景卡」→ 阶段 `scenes` |
| 好感度 / 堕落值 / 理智值 | 说「数值系统」→ 阶段 `axes` |
| 数值要自己记住、自己更新 | 说「变量系统」→ 阶段 `mvu`（需要装酒馆助手） |
| 按数值换一套说法 | 说「分档人设」→ 阶段 `ejs`（还要 Prompt Template） |
| 开场界面 / 建卡向导 | 说「开局面板」→ 阶段 `opening` |
| 每轮显示数值 / 血条 | 说「状态栏」→ 阶段 `statusbar` |
| 打包、导入酒馆 | 说「打包」→ 阶段 `delivery`（最后一个） |
| 一张完整卡 / 一整套 | 说「做一整套」→ 按契约里勾的阶段依序走 |

<details>
<summary><strong>一次完整对话长什么样</strong></summary>

```text
/skill:rp-factory "盐湖上的守夜人"
  ↓ 开局四问（工作区 / 阶段 / NSFW / 联网），一次问完
  ↓ 建 制作文件/ 与契约，静默探测本机酒馆
world      → 世界观四要素、判定框架、三条硬设定
cast       → 角色卡：背景受控、事实分稳定/临时、演出许可三档
scenes     → 场景卡：强/弱结构，十块全填或按需
axes       → 双轴：灯芯 / 潮压，各自刻度与上界
mvu        → zod 结构（带 .catch()）+ [initvar] + 三条更新条目 + 两条隐藏正则
ejs        → 三档控制器，被控条目切「原件禁用 + 分档副本」
opening    → 建卡向导 HTML + 正则 + 提示词条目
statusbar  → 状态栏 HTML + 正则 + 提示词条目
delivery   → 白潮（纯净）.json / 正则.json / 白潮 世界书.json
```

每一阶段收尾都会跑一次该阶段的校验器，失败就停下改，不往下走。
</details>

<details>
<summary><strong>九个阶段各自管什么</strong></summary>

| 阶段 | 产物 | 一句话 |
| --- | --- | --- |
| `world` | `world-bible.yaml` | 地理、势力、规则、冲突源；**收敛门**要四要素齐且张力已定 |
| `cast` | `rolecard.yaml` | `description` / `personality` / `first_mes` / `mes_example` / `system_prompt`；NSFW 时 `nsfw` 块七键齐全 |
| `scenes` | `scene-sheet.yaml` | 地点、可达性、在场者、可发生事件、禁区；强结构给十块 |
| `axes` | `axis-system.yaml` | 轴的语义、范围、初值依据、触发事件、可见性 |
| `mvu` | `变量结构.js` `[initvar]…yaml` `变量规则.yaml` `regex-mvu.json` | 把轴投影成 zod + 初始化 + 更新条目 + 隐藏正则 + 卡内脚本 |
| `ejs` | `阶段控制器.ejs` + 分档条目 | 按数值换提示词；有「什么时候不该做」的判据 |
| `opening` | `*-ui.html` `regex-*.json` `frontend-prompt.yaml` | 登场面板 / 建卡向导两形态，靠酒馆助手渲染 |
| `statusbar` | 同上 | 有 MVU 走变量，没有走标签 |
| `delivery` | 三件套 | 纯净卡（无内嵌书）+ 正则数组 + native 世界书，放 `导入包/` 根下 |
</details>

## 十四道硬门

编号与判据的唯一权威是 `references/pipeline.md` 第三节，`SKILL.md` 只留这张索引表。

| # | 门 | 判据 |
| ---: | --- | --- |
| 0 | 开工门 | 工作区 / 阶段 / NSFW / 联网四件确认后才动笔；NSFW 与联网不答按「否」锁 |
| 1 | 边界门 | `nsfw` + `rating` + `hard_no` 锁定前不产出任何设定正文 |
| 2 | 收敛门 | 仅 `world`：四要素齐、判定框架填、张力已定、无致命缺口 |
| 3 | 补采访问 | 上游缺项先问 ≤3 问，问不到才写 `[待定：…]` |
| 4 | 零回溯 | 不引用包外路径、不登记源文件名 |
| 5 | 自检门 | 交付前四类检查；正文不许留构建期占位符 |
| 6 | 命名门 | 交付前四步核对契约与产物，不一致就停下问 |
| 7 | 契约门 | 阶段收尾跑 `validate-contract.py`，退出码 0 |
| 8 | 联网门 | 仅 `web_research: true`：落笔前检索、交付前复核，查不到记 `未检索到` |
| 9 | 前端门 | 仅 `opening`/`statusbar`：十条 + `validate-frontend.py` |
| 10 | 变量门 | 仅 `mvu`/`ejs`：`validate-mvu.py` / `validate-ejs.py`；没装助手别开 |
| 11 | 交付门 | 仅 `delivery`：`check-stage.py delivery` 退出码 0 |
| 12 | 阶段门 | 一次一个阶段，做完跑一检、停下等用户 |
| 13 | 自创字段门 | 新键先问、记 `decisions`；不许替换模板既有块 |

## 校验器

九个校验器加一个阶段总检，全部只用 Python 标准库（`st-probe.js` 例外，要 `puppeteer-core`）。

| 脚本 | 规则号 | 只查什么 |
| --- | --- | --- |
| `scripts/validate-contract.py` | `C00–C17` | 契约自洽：阶段状态、产物索引、交付路线、命名表、演出许可三档 |
| `scripts/validate-rolecard.py` | 1–12 | 角色卡骨架、占位符、事实分级（稳定 / 临时）、越界标记 |
| `scripts/validate-st-package.py` | `C` `R` `W` `X` | 三件套结构：卡字段、正则数组、世界书条目、跨文件绑定 |
| `scripts/validate_st_semantics.py` | `S-01–S-29` | **只抓静默失效**：两套正则方言、`$<name>`、书位置枚举、卡内 scoped 正则未授权、书名绑定 |
| `scripts/validate-frontend.py` | `F01–F14` | HTML 骨架、外链、危险 API、实体、事件名、相对路径、裸定时器 |
| `scripts/validate-mvu.py` | — | 变量结构可编译、`[initvar]` 与 schema 对齐、更新条目、隐藏正则 |
| `scripts/validate-ejs.py` | — | EJS 语法纪律、变量路径、被控条目存在且已禁用、边界连续 |
| `scripts/check_prose.py` | `P01–P09` | 解释腔、情绪直说、陈词比喻、模板标签、绝对化失衡（默认只警告） |
| `scripts/check_acceptance.py` | `A00–A06` | 验收账本：六层证据、L4 十一维、**脚本不许给 L5/L6 签字** |
| `scripts/check-stage.py` | — | 按阶段自动调上面这些，一个命令跑完该阶段全部检查 |

<details>
<summary><strong>为什么单列一个「静默失效」校验器</strong></summary>

SillyTavern 有一类错误不抛异常、不写日志、界面上也不报错，只是**机制没跑**：

- 正则用 `$1` 还是 `$<name>` 写错 → 只留下字面量
- 卡内正则默认不生效，取消过一次确认框后**永久静默**（`AlertRegex_<头像>` 先于弹窗写入）
- 世界书文件名与 `extensions.world` 不等 → 两本都对不上，一条都不挂
- 内嵌书不带 `name` → 落成 `<卡名>'s Lorebook`，与你写的名字不是同一个
- 前端代码块里没有 `html>` / `<head>` / `<body` → 判定不是界面，直接渲染成文字

这些坑每一条都对应 `references/st-correctness.md` 里的一行源码锚点，`check_st_facts.py` 会在 ST 升级后把这些锚点重新验一遍（44 条，含酒馆助手侧 10 条）。
</details>

## 产物长什么样

```text
<工作区>/<世界名>/
  制作文件/                # 原稿、源码、账本和检查材料全在这
    项目记录/              # contract.yaml（命名权威+索引+阶段状态+decisions）
                           # 项目档案.yaml / 创作记录.md / 检索来源.md
                           # 验收.yaml（六层证据，L5/L6 只能人签）/ 试演记录.yaml
    产物/                  # 四类设定 + MVU/EJS + 两个界面的 HTML
  导入包/                  # 交付成品，平铺，交付前必须空着
    白潮（纯净）.json
    正则.json
    白潮 世界书.json
```

根下只有这两个文件夹，不散落 README、清单、脚本或隐藏账本——`validate-contract.py` 的 **C17** 会查旧布局（`创作痕迹/`、`最终产物/`）与根目录散落文件。改名或迁移过的旧项目要先按新布局搬完再跑，不保留两套。

`examples/dry-run-盐湖守夜人/` 是九个阶段真跑一遍的完整产物，可以直接对比「规则写出来的东西长什么样」。

## 加载预算

skill 最容易悄悄变胖：每加一句话，每个阶段都多读一遍。

| 位置 | 实测 tok | 上限 |
| --- | ---: | ---: |
| 常驻（`SKILL.md` + `references/pipeline.md`） | 5,618 + 4,680 | 6,600 / 4,700 |
| 最挤的阶段（`delivery`，四个文件叠加） | 25,834 | 26,000 |
| 最轻的阶段（`ejs`） | 15,583 | 基线 15,637 |

`scripts/measure_load.py` 把这件事变成断言：九阶段的 worst case 各自与基线比对，超过即判「变重」。加内容时的顺序是——先在**同一个文件**里找等量冗余回收（`delivery` 是四文件叠加，任何两句以上新增都要先做这一步），抵不平才动基线，并且要在 docstring 里留一条 Ruling 说明为什么。

<details>
<summary><strong>需要时再加载的两份文件</strong></summary>

`references/tavern-helper.md`（269 行）与 `references/worldbook-writing.md`（135 行）**不在任何阶段的加载表里**，0 常驻。它们只在两种时刻被读：前端阶段查接口签名、交付阶段写世界书正文。

索引里留一个指针，正文不复制——这是这个包里唯一被允许的「重复」。
</details>

## 验收：六层证据

| 层 | 名字 | 谁能签 |
| --- | --- | --- |
| L1 | 源码事实 | 锚点脚本（`check_st_facts.py`） |
| L2 | 脚本断言 | 校验器与单测 |
| L3 | 离线产物 | `validate-*` 系列 |
| L4 | 浏览器实测 | `st-probe.js`，**必须写 11 维之一** |
| L5 | 真机酒馆 | 只能人 |
| L6 | 人眼手感 | 只能人 |

一条总则：**自动化不得自签 `driver-accepted`**。脚本跑绿了只能说明结构对，说明不了「在酒馆里能玩」。账本 `制作文件/项目记录/验收.yaml` 里 L5/L6 写 `skipped` 是诚实的，写 `passed` 而没有人的操作记录是伪造。

## 版本与变更

当前 **1.1.00**，唯一真相是 `SKILL.md` 的 `metadata.version`；`CHANGELOG.md` 首条必须与之对应，`scripts/run_checks.sh` 一启动就打印版本号。

`package.json` 里**故意不写版本号**：npm semver 不接受前导零（`1.0.01`），写进去会让 `npm install` 直接报 Invalid version。那份文件只声明 `puppeteer-core`。

<details>
<summary><strong>改动怎么验</strong></summary>

```bash
bash scripts/run_checks.sh                       # 包自身：结构 + 单测 + 加载预算
bash scripts/run_checks.sh <某创作目录>            # 再加：契约 / 三件套 / 语义 / 验收
PYTHONIOENCODING=utf-8 python scripts/check_st_facts.py   # 44 条源码锚点是否还站得住
python scripts/measure_load.py                    # 九阶段加载量 vs 基线
```

Windows 终端默认 GBK，跑会打印 `✗` 的脚本要带 `PYTHONIOENCODING=utf-8`。
</details>

<details>
<summary><strong>卸载</strong></summary>

```bash
rm "C:\Users\<你>\.agents\skills\rp-factory"      # 拷贝安装
cmd //c rmdir "C:\Users\<你>\.agents\skills\rp-factory"  # junction（只删链接，不动工作树）
```

RP-Factory 不往宿主机写任何隐藏状态：没有安装清单、没有全局配置、没有遥测。产物全部落在你自己指定的工作区目录里。
</details>

## 已知边界

- **只在中文 RP 上跑过。** 卡字段与 ST 语义是通用的，但 prompt 骨架、去 AI 味判据、试演话术都按中文写作习惯写。
- **L6 永远需要人。** 代演、OOC、口癖漂移、数值闸门失效四类判据能给你一张检查表，判不了「这段好不好看」。
- **真机验收要本机 Chrome + 在跑的酒馆。** 没有就降级到 L1–L3，并诚实记账。
- **一次性验证，不是持续测试。** 锚点脚本证明「文档与源码还对得上」，证明不了「你这次的卡一定能玩」。
- **方法论借鉴了 TavernWeave**（证据分级、四态决策、写作契约、状态切分），但不搬它的内容、不做跨宿主打包、不做拆卡与组件库。

## 文档索引

| 文件 | 管什么 |
| --- | --- |
| `SKILL.md` | 路由、开局四问、硬门索引、文件索引 |
| `references/pipeline.md` | 阶段表、占位符、十四道门、输出纪律（唯一公共脊） |
| `references/contract-schema.md` | 契约键区、独占写者、冲突规则 |
| `references/interview-protocol.md` | 问题块格式、每阶段预算、补采访问、降级链 |
| `references/decisions.md` | 四态决策、缺口三级、未答 ≠ 委托 |
| `references/acceptance.md` · `rehearsal.md` | 六层证据账本 · 试演四类判据 |
| `references/st-correctness.md` · `tavern-helper.md` | ST 1.19.0 语义事实 · 酒馆助手 4.12.1 接口 |
| `references/worldbook-writing.md` · `worldbook-tuning.md` | 条目正文契约 · 参数调优 |
| `references/frontend-conventions.md` · `dual-mode.md` | 表现层机制 · 文本 / 工程两种模态 |
| `references/stage-*.md` | 九个阶段各自的做法与退出条件 |
| `docs/plans/` · `docs/reviews/` · `docs/specs/` | 设计与计划 · 实操复盘 · 规格 |
| `docs/coverage-checklist.md` | 覆盖清单：哪些坑已经被断言守住 |

<p align="center">
  <sub>Built for SillyTavern 1.19.0 · JS-Slash-Runner 4.12.1 · Agent Skill format</sub>
</p>
