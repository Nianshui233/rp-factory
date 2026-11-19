---
name: rp-factory
description: 把 RP 构想编译成世界观、角色卡、场景卡、数值系统四类 YAML 设定产物，跨产物命名与硬设定保持一致；支持粘贴用提示词条目与工程文件两种交付。仅在用户显式输入 /skill:rp-factory 时执行，不参与自然语言自动匹配。
disable-model-invocation: true
---

# RP-Factory

把 RP 构想编译成四类可交付设定产物。本文件只管**判阶段、读写契约、派发纪律**——具体怎么做在阶段文件里，这里不复述。

## 一、路由

本 skill **只由 `/skill:rp-factory` 显式调用**，不做自然语言自动匹配——用户没输入斜杠命令就不接手。下表是**调用之后**按用户诉求判阶段用的，不是触发条件。

| 用户说的 | 进入 | 加载 |
|---|---|---|
| 「帮我做个世界观 / 世界观设定」 | 阶段 1 | `references/stage-1-world-bible.md` |
| 「设计一个角色 / 角色卡 / 人设」 | 阶段 2 | `references/stage-2-rolecard.md` |
| 「生成场景 / 地点卡 / 地图」 | 阶段 3 | `references/stage-3-scene-sheet.md` |
| 「好感度 / 堕落值 / 理智值 / 数值系统」 | 阶段 4 | `references/stage-4-axis-system.md` |
| 「做一张完整卡 / 一整套设定」 | 按 `project.stages_requested` 依次 | 按需逐个加载 |
| 只有模糊概念 | 阶段 0 判定后进入 | 先 `references/interview-protocol.md` |

判断不了就先按「只有模糊概念」处理：在开局第二问里让用户直接勾阶段，不猜。

## 二、开局四问（第一步）

**先问四件，一次问完，不分三轮。** 四件没问完，任何阶段都不动笔。

**问一：工作区在哪。** 问「项目放在哪个目录？」，给 2–3 个选项（当前目录 / 用户常用目录），每个选项说明会建成什么样，附一句「只要粘贴、不落文件也可以说一声」。确认后在其下建两层：

```
<工作区>/<世界名>/
  创作痕迹/  contract.yaml（命名权威+索引） · 项目档案.yaml（元信息+类型基调，不进终稿） · 创作记录.md（访谈、决策、卡点） · 检索来源.md（仅同人向）
  最终产物/  world-bible.yaml · rolecard.yaml · scene-sheet.yaml · axis-system.yaml
```

- 名字未定 → 先建 `未命名项目/`，定名后重命名一次并回写 `project.name` 与 `project.workspace`；说「只要粘贴」→ `project.mode = text`，不建目录，此后不再问。
- 同名目录已存在 → 先列内容再问「续建还是换名」，**不覆盖**。
- `创作痕迹/` 不存 YAML 草稿副本；产物文件按需创建，没跑到的阶段不预建空壳。

**问二：跑哪几个阶段（多选）**

四项可全选：`1 世界观` / `2 角色卡` / `3 场景卡` / `4 数值系统`。

- 写 `project.stages_requested`（升序），未勾的在 `stages` 里写 `skipped`（本次不跑，不是没跑）。
- 执行顺序永远 1→2→3→4，不跳序；只勾下游而缺上游时，进该阶段走一次补采访问（≤3 问）。
- 一个都没勾 → 回问一次，仍不选按全套走；中途加阶段 → 追加 `stages_requested`，把 `skipped` 改回 `none`，记 `decisions`。

**问三：启用 NSFW 内容吗**

- **否** → `nsfw: false`，`rating` 写一般向，`hard_no` 加「任何性描写」；阶段 2 不写 `nsfw` 块；自检门的内容边界层整类跳过。
- **是** → `nsfw: true`，`rating` 须给明确档位（`R15` / `R18`），`hard_no` 至少一条硬底线；阶段 2 可写 `nsfw` 块，内容边界层必执行。
- 不答 → 按「否」锁，一句告知可随时开。中途开关 → 改 `nsfw` + 重锁 `rating` + 记 `decisions`；关掉时已交付产物里的越界内容必须清掉。

**问四：是同人向项目吗**

是 / 否，否就直接跳过本问后续。

- **否** → `project.fanwork: false`，原创处理，不联网检索。**是** → 再问两句：**原作是什么**（作品名 + 版本，写 `project.source_ip`）、**正典向还是 AU**（哪一点不同，写 `project.canon_stance`）。
- 同人向从这一刻起**全程主动联网检索**：每阶段开头先查原作硬底、专名、时间线，查完才落笔；每条记进 `创作痕迹/检索来源.md`（骨架 `templates/research-log.md`）。口径冲突的裁法、没网时怎么降级、版权边界，全在 `references/fanwork-research.md`——**进入任何阶段前先读它**。
- 不答 → 按「否」锁，一句告知可随时说是。中途才说是同人 → 回填三个值、补建检索记录、从当前阶段起开始查，记 `decisions`。

四问用结构化选项，**不用** `references/interview-protocol.md` 的问题块格式。写回细节见 `references/contract-schema.md` 第七节。

## 三、开工前

1. 读 `references/pipeline.md`：阶段表、7 个占位符、六道门、输出纪律。**这是唯一的公共脊，任何阶段文件里没有的东西都回这里查。**
2. 有契约就读契约（`templates/contract.yaml` + `references/contract-schema.md`）；没有就先建一份。
3. `project.fanwork: true` → 先读 `references/fanwork-research.md`，再进阶段（其余情况跳过）。
4. 定出**目标阶段**与**当前产物 type**（四选一：`world-bible` / `rolecard` / `scene-sheet` / `axis-system`）；文本还是工程文件按 `references/dual-mode.md` 判，默认文本模态。

## 四、做主 skill 的三件事

- **判阶段**：目标阶段、是否已有前置产物、够不够开工。
- **读写契约**：`naming` 与 `hard_settings` 是权威；阶段文件要写已存在的键就停下问，不许静默覆盖。
- **派发纪律**：只加载当前阶段文件，由它决定问什么、怎么写、怎么退出。

## 五、不做的事

- **不生成任何设定内容**（世界、角色、场景、数值全由阶段文件产出）；**不替用户拍板硬设定**，会改变走向的必须用户点头。
- **不重复 stage 文件里的规则**（一旦本文件开始复述某阶段字段规范，就是错的，删掉改成引用）；**不预加载其他阶段文件**，一次只加载当前阶段那一份。

## 六、硬门

0. **开局门**：先问四件——工作区、跑哪几个阶段（多选）、是否启用 NSFW、是否同人向（是则问原作与正典立场）。四件都确认前不建目录、不落文件、不开工；NSFW 与同人向不答都按「否」锁。
1. **边界门**：由开局门锁定 `content_boundaries`（`nsfw` + `rating` + `hard_no`）。阶段内只在必要时补问边界细节（≤2 题）。未锁定不产出任何设定正文。
2. **命名门**：交付前按 `references/pipeline.md` 四步核对契约与产物，名字不一致就停下问用户。
3. **补采访问**：上游缺项先补采访问（≤3 问），问不到才写 `[待定：<缺什么>]`。
4. **零回溯**：不引用任何包外路径、不登记源文件名。本包自包含，删掉任何外部文件都不影响运行。
5. **自检门**：每份产物交付前内部执行四类检查，不向用户展示检查过程。
6. **检索门（仅同人向）**：`fanwork: true` 时，每阶段落笔前先检索、交付前复核一遍原作专名；查不到就记 `未检索到` 并改走确认清单，**不编造原作设定**。

## 七、文件索引

| 文件 | 管什么 |
|---|---|
| `references/pipeline.md` | 阶段表、占位符、六道门、自检四类、命名门四步、输出纪律 |
| `references/interview-protocol.md` | 问题块格式、每阶段预算、补采访问、降级链 |
| `references/contract-schema.md` | 契约定位、键区、独占写者、冲突规则 |
| `references/dual-mode.md` | 两种模态的对照、切换、渲染、注释剥离 |
| `references/fanwork-research.md` | 同人向：何时检索、怎么记、冲突怎么裁、没网怎么降级 |
| `references/stage-1-world-bible.md` | 阶段 1 世界观 |
| `references/stage-2-rolecard.md` | 阶段 2 角色卡 |
| `references/stage-3-scene-sheet.md` | 阶段 3 场景卡 |
| `references/stage-4-axis-system.md` | 阶段 4 数值系统 |
| `templates/*.yaml` | 契约 + 四份产物 + 项目档案，填完即交付（项目档案归 `创作痕迹/`，不进终稿） |

## 八、阶段文件约定

每个 `stage-*.md` 六节，顺序固定：`## 进入条件` / `## 追问` / `## 判断标准` / `## 生成` / `## 写回契约` / `## 退出`。

- 缺 `## 进入条件` 的阶段文件等于没有入口条件，不许存在；阶段文件里出现「见 `pipeline.md`」以外的重复定义，按第四节第 3 条处理。

## 九、交付形态

- 文本模态：一个 ```yaml 代码块，块外只允许设计说明、补全清单、待确认清单、运行示例；工程模态：写进 `<工作区>/<世界名>/最终产物/`，四个产物各一文件。

细节在 `references/dual-mode.md`。改模态只换渲染目标，不重跑阶段。
