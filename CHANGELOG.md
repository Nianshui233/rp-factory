# 变更记录

版本号写在 `SKILL.md` frontmatter 的 `metadata.version`；这份文件的第一条标题必须与它一致，
由 `tests/test_version.py` 守着。

## 1.4.14 — 2026-11-22

**修：选了 RP-Factory 预设、说一句「开始」，却被告知「这个环境没装 skill」。**

预设只给了人格，skill 仍是 `disable-model-invocation: true`：用户没敲斜杠时，模型读不到 SKILL.md，
却又被人格要求「先按 SKILL.md 判阶段」，于是去工作区和 DSH 安装目录翻文件，五个回合后如实报告
「rp-factory 没装上」——真机会话 `session-111be7e6-755f-40ae-b510-93a3a6abdcd5` 的现场。

- 预设里再挂一份 provider，带 `modelInvocable: true`：**选了预设就等于显式进流程**，模型可以直接
  `skill` 读到 SKILL.md；预设之外的会话仍是 host 层那份，只能斜杠命令进。
- 人格第一条改成「开工先 `skill` 读 `rp-factory`；读不到就一句话说明，别凭印象开工」，
  不再让它去磁盘找文件。
- 预设描述改成「选它就能开工」；测试 +1（预设必须挂上可读的那份）。

## 1.4.13 — 2026-11-22

**DSH 改成预设交付：装一个 `.tgz`，预设选择器里就多出一个 `RP-Factory`。**

DSH 里 skill 只能靠斜杠命令进（`disable-model-invocation: true`），可「一次只跑一个阶段」这个节奏
原先无处安放——模型可以自己连跑九段，也可以拿 subagent 把流程拆成并排的几个。宿主能钉这件事的地方
是 agent preset，所以把适配层从「只注册 skill provider」扩成「skill provider + 预设」。

- `host-adapters/dsh/plugin/cordis.patch.yml` 一次插两行：`rp-factory` 插件行（skill provider）
  与 `@deepseek-ai/dsh-agent-preset` 预设行（id `rp-factory`、名 `RP-Factory`、order 6）。
- 预设工具集按一阶段一停裁剪：带 `skill` / 文件读写搜索 / ask-user / todo / web / present，
  不带 subagent、workflow、plan mode、goal、schedule、jobs、office。
- 平台二选一（`!!js`）：Windows 上关 `tool-bash` 开 `tool-pwsh`，其余平台反过来。
- 只要 skill 不要预设：`DSH_RP_FACTORY_NO_PRESET=1` 时跳过预设行。
- 调用手势按宿主分开写：**DSH 是 `/rp-factory`**，Claude Code / Codex / Pi 才是 `/skill:rp-factory`
  （写进 README、预设人格、插件头注释；`SKILL.md` 里只说「斜杠命令」，不给模型塞宿主方言，
  `description` 与「一、路由」那两句顺手压短，加载预算一格没涨）。
- 测试 +3：补丁能解析且行 id 唯一、预设 id 与 skill 名对得上、预设里不许出现会自己跑完流程的工具。

## 1.4.12 — 2026-11-22

- `tavern-helper.md` 第九节补一条真机教训：`TavernHelper.createOrReplaceCharacter` 的
  `extensions` 是**整块覆盖**，传部分字段会把 `regex_scripts` 或 `tavern_helper` 抹掉
  （实测把一张卡的两条角色脚本清空）；局部改走 `writeExtensionField` 或
  `/api/characters/merge-attributes`，改完用 `/api/characters/get` 核对。

## 1.4.11 — 2026-11-22

**卡上还有四个字段也在每轮付费，而且内容早就写在书里了。** `角色设定摘要`(personality)、
`情景`(scenario)、`角色备注`(depth_prompt)、`对话示例`(mes_example) 默认必须留空——
书里的角色条目已经写了同样的事，写第二遍只是重复付费。

唯一例外是"必须贴着最新消息、书里又没有"的功能指令；状态栏标签要求正经的家是世界书条目。

- `stage-7-delivery.md` 字段表补明 X13；协议条目改由 `--merge-entries` 进书。
- `cut-worldbook.py` 新增 `--merge-entries`（可重复，文件里 `entries:` 列表或单条）。
- `validate-st-package.py` 新增 **X13**（四个字段非空 → 警告）、**X14**（有状态栏但没有
  任何条目要求输出 `<StatusPlaceHolderImpl/>` → 警告：第一楼之后就没有状态栏）。
- 示例包加 `制作文件/产物/协议/状态栏协议.yaml` 并重切世界书（20 → 21 条）。
- 测试 +5。

真机（极寒末日）：personality / scenario / mes_example 清空，状态栏协议进书（position 4、depth 2、常驻）。

## 1.4.10 — 2026-11-22

**`description` 每轮都在场，写什么都要按"每轮"付费。** 上一版把它当成设定仓库：住户索引、
地点索引、两轴读法全抄一遍，末尾还加一句「以上是设定，不是示例对话」——这些世界书里都有，
或者根本是元话。

规则改成：`description` 只写**每轮都要在、且书里没有的**——一句话世界 + 怎么玩 + 扮演职责。

- `stage-7-delivery.md` 卡字段表的 `description` 行重写。
- `validate-st-package.py` 新增 **X12**：8 字滑窗与世界书比对，字面重叠 ≥20%（且描述 ≥300 字）
  → 警告「这些内容书里已经有了」；命中「以上是设定／不是示例对话」这类元话 → 警告。
- 示例包 `白潮（纯净）.json` 的 description 从 5,943 字压到 266 字（重叠 38% → 0）。
- 测试 +4。

真机（极寒末日）：description 1,196 → 279 字，卡内只剩世界一句话、怎么玩、怎么演四条。

## 1.4.9 — 2026-11-22

**卡里三个字段的活被搅在一起了。** 交付出去的卡把开场白写进了 `description`
（末段是「你刚把编号牌递进窗口…」），而真正的文字开场白一条也没有——`first_mes` 只有面板数据块，
玩家只能点入口按钮起头。

分工改成（对齐 `我，非我` 这类成熟卡的写法）：

| 字段 | 职责 |
|---|---|
| `description` | **总设定**：世界、规则、势力、住户索引、地点索引、两轴读法，结尾「以上是设定，不是示例对话」 |
| `first_mes` | 面板数据块（`<开局界面>`）或向导标签；**不放散文** |
| `alternate_greetings` | **文字开场白** 2–3 条，每条可独立开局，末尾 `<StatusPlaceHolderImpl/>` 带上状态栏 |

- `stage-7-delivery.md` 的卡字段表按上表重写。
- `validate-st-package.py` 新增 **X09**（`description` 结尾是「你…」的场景动作 → 警告）、
  **X10**（做了面板却没有文字开场白 → 警告）、**X11**（面板数据块混进 `alternate_greetings` → 失败）。
- 测试 +4。

真机（极寒末日）：`description` 从 211 字的半截开场白换成 1,153 字总设定；补 3 条散文开场白
（配给窗口／拾温队库房／冻港归途），新聊第 0 楼可左右切换，切到任一条都能正常出状态栏。

## 1.4.8 — 2026-11-22

**玩家改完数值，下一回合又变回去了。** 每层楼的 `stat_data` 是各自快照：状态栏在开局楼层
（第 0 楼）把 `体温` 从 82 改成 60，改的只是这一层，最新层仍是 82，模型读回 82 就当没改过。
真机实测：`floor0 = 60`、`floorLast = 82`。

- `templates/control-center.html` 与状态栏：读写一律 `message_id: 'latest'`。
- `validate-frontend.py` 新增 **F24**：写回（`replaceMvuData`）配 `getCurrentMessageId()` → 警告。
  只读 HUD 读自己那一楼不算（那一楼快照 + 与上一楼的差是有意义的）。
- `frontend-interaction.md` / `tavern-helper.md`（十一之二）补这条。

同时补一条交付期提示：

- `validate-st-package.py` 新增 **X08**：`first_mes` 里既有 `<开局界面>` 又有
  `<StatusPlaceHolderImpl/>` → 第一楼会多渲染一块状态栏；只想在回复末尾显示就删掉那行。
- 测试 +7（F24 四态、X08 三态）。

真机（极寒末日）：你跑的那条把 78/40 推到 韩秋 82/71、老鸦 66/58、白嬷嬷 88/63；
改完后三块界面都读最新层，数值一致。

## 1.4.7 — 2026-11-22

**状态栏显示「Mvu 未启用」，其实变量好好的。** 消息 iframe 里的 `window.Mvu` 是
`src/iframe/predefine.js:37` 在 iframe 创建那一刻判一次 `_.has(window.parent, 'Mvu')` 才定义的；
bundle 后到，这个 getter 永远不出现，该 iframe 里 `Mvu` 就是永久 undefined。起手写
`if (typeof Mvu === 'undefined') return '未接入'` 会把「还没到」显示成「没启用」。

- `templates/control-center.html`：加 `MvuApi()`（`window.Mvu || window.parent.Mvu`），
  `detectMissing()` 与四处调用都走它；boot 时若仍缺就 `waitGlobalInitialized('Mvu')` 再渲染。
- `tavern-helper.md` 新增「十一之二、读变量前必须等 Mvu 到（TH-13）」，写出机制与两种写法。
- `check_st_facts.py` 加 TH-13 两处锚点（`predefine.js:36` / `:37`）。
- `validate-frontend.py` 新增 **F23**：出现 `Mvu.` / `getMvuData` / `replaceMvuData`，
  却没有 `waitGlobalInitialized` 也没有 `parent.Mvu` → 失败。
- 测试 +5（直接判 typeof 被拦、两种正确写法放过、无关文件不报、两个模板必须过）。

真机（极寒末日）：同一楼从「未接入：Mvu 未启用」变成真数字（韩秋 78 / 40、老鸦 78 / 40、
白嬷嬷 78 / 40、寒蚀 平稳），iframes 里的 `Mvu` 也变成 object。

## 1.4.6 — 2026-11-22

**正则也一样：默认该进「角色正则」，不是全局。** 全局正则会在所有角色、所有聊天里跑，
别人卡里的 `<StatusPlaceHolderImpl/>` 也会被我们的替换串接住。

- `templates/import-guide.txt` 第 3 步改成「目标选角色正则」+ 「首次进聊天点允许」，
  并写清漏点的后果（S-28：取消一次永久静音）。
- `stage-7-delivery.md` 装配段、`st-correctness.md` 的 S-30 结论同步。
- `validate-contract.py` 新增 **C18**：导入说明没写「角色正则」→ 失败；写了但没写「允许」→ 警告。

**MVU 三件套留在 制作文件/ 里等于没交。** 世界书里既没有 `[initvar]` 也没有
`[mvu_update]`，脚本读不到初值、模型收不到更新规则，数值永远不动——而且全绿。

- `cut-worldbook.py` 新增 `--merge-mvu <DIR>`：把 `变量规则.yaml` 的条目与
  `[initvar]变量初始化.yaml`（包成禁用条目、`ignoreBudget`）一起装进书。
- `validate-st-package.py` 新增 **W25**：契约里 `mvu: done`，而书里找不到 `[initvar]` /
  `[mvu_update]` → 失败。
- 示例包按 `--merge-mvu` 重切（21 → 25 条），`世界书切割.yaml` 顺带清掉单字与互为子串的关键词。
- 测试 +10（C18 三态、W25 拦截、`--merge-mvu` 四种情况、示例书必须带 MVU 条目）。

真机（极寒末日）：世界书重导后 19 条（15 设定 + 3 更新规则 + 1 初始化），正则改到角色正则。

## 1.4.5 — 2026-11-22

**脚本被当成全局脚本导入了。** 交付说明原来只写「脚本库 → 导入」，玩家自然点了第一栏
「全局脚本」——于是换张卡也在跑同一套变量逻辑，两张卡一起开就互相污染。

- `templates/import-guide.txt` 第 4 步改成分步写：先选中这张卡 → 点**「角色脚本」**那一栏的
  导入 → 打开该栏总开关 → 逐条打开；并写清为什么不能放全局。
- `stage-7-delivery.md` 第五节与装配第 4 步、`stage-mvu.md` 退出四句同步。
- `tavern-helper.md` 第九节加「三个脚本库」表：全局存插件设置、**角色脚本存这张卡的
  `data.extensions.tavern_helper`**（`writeExtensionField`）、预设存预设里；导入目标由你点哪一栏的
  导入决定（`Toolbar.vue` 的 `handleImport(target, …)`）。
- `validate-contract.py` 新增 **C17**：交付了酒馆助手脚本、而 `导入说明.txt` 没提「角色脚本」
  → 直接判失败。
- `check_st_facts.py` 加 TH-12 三处锚点（`Toolbar.vue:84`、`character.ts:34`/`:47`）。
- 示例包与测试内夹具同步；`tests/test_import_package.py` 加 3 个（骨架与示例必须点名、
  缺「角色脚本」时 C17 拦得住）。

真机验证（极寒末日）：脚本从全局搬进角色脚本后，重载页面 → 卡内 `data.extensions.tavern_helper`
里两条都在且 `enabled: true`、`script.enabled.characters` 含该头像；进聊天后两条脚本 iframe
（`TH-script--MVU--…` / `TH-script--ZOD--…`）都在跑，顶层 `window.Mvu` 是 object。

## 1.4.4 — 2026-11-22

**入口按钮点了没人回。** 玩家点开局面板的入口，消息确实进了聊天，模型却一句话不接，
必须自己手动点「重新生成」——`/send` 只 append 一条用户消息。

- `templates/opening-ui.html` 的发送改成两步：`/send` 送话 + `/trigger` 生成；
  两步都依赖酒馆助手注入的 `triggerSlash`（界面本来就只活在它的 iframe 里）。
  失败时放开按钮并显示一行提示，让玩家自己在输入框里发。
- 删掉「直接操作父窗口 `#send_textarea` + 点 `#send_but`」的兜底：它要碰 `parent.document`，
  F12 本来就不许，且在插件没接上时也不成立。
- `validate-frontend.py` 新增 **F22**：出现 `/send` 却没有 `/trigger` 直接判失败。
- 文档三处同步：`frontend-interaction.md` 第二节（两步发送 + 为什么不能只发 `/send`）、
  `frontend-conventions.md` 第二节、`stage-5-opening-ui.md`；
  `tavern-helper.md` 第十节补上源码位置（`slash-commands.js` 的 `sendUserMessageCallback` /
  `triggerGenerationCallback`）。
- `tests/test_frontend_design.py` +3：骨架里必须有 `/trigger`、只发 `/send` 被 F22 拦、
  两步齐全放行。

真机复测（ST 1.19.0 + 酒馆助手 4.12.1，极寒末日）：点头部入口 → 用户消息入聊天 →
`/trigger` 发出生成请求 → 模型 API 返回 `Resource exhausted`（错误来自 API 配额，不是界面），
说明生成链路已经接通。

## 1.4.3 — 2026-11-22

**真机首测（`极寒末日`）抓到的四处「静态全绿、真机不亮」。** 前四条缺陷在离线校验里一条都
没报，全部是导入酒馆之后才现形的。

- **界面必须放围栏里**：`replaceString` 里塞裸 HTML 时，正则生效但 Showdown/sanitize 把
  `<script>` 吃掉，消息里只剩一段代码块——界面永远不出现。`templates/regex-frontend.json`
  的待粘占位改成围栏包着（`"```html
【尚未粘贴界面】…
```"`），`import-guide.txt`、
  `stage-7-delivery.md` 写明「围栏不能删」；`validate-contract.py` 与 `validate-st-package.py`
  的待粘判定从 `startswith` 改成 `in`，示例包的 `正则.json` 同步。
- **MVU 本体地址已死**：`StageDog/tavern_module/dist/MVU/index.js` 返回 404，`Mvu` 因此从不
  出现，界面只能显示「未接入」。换成 `MagicalAstrogy/MagVarUpdate/artifact/bundle.js`
  （572 KB，实测 200），并写明交付前要 `curl -sI` 验一遍。
- **脚本交付形状**：平铺的对象数组才跑得起来；包一层文件夹（`type: folder`）时 `Mvu` 一直
  缺，`stage-mvu.md` / `stage-7-delivery.md` 改成「两条别包」。
- **交付说明自相矛盾**：`stage-mvu.md` 的退出项还写着「卡里已经带了脚本」，与 C12（卡内
  不内嵌脚本）冲突，改成「脚本单独一份 + 去脚本库手动启用」。

新增 `tests/test_ui_paste.py`（5 个）：待粘占位必须在围栏里、围栏内不许再出现三反引号、
`stage-mvu.md` 必须用可用的 bundle 地址、全仓不许再引用失效路径、导入说明必须提围栏。

## 1.4.2 — 2026-11-22

**发布面的两个毛病。**

- npm 包里混进了 12 份 `__pycache__/*.pyc`（跑过校验器就有，删掉的 `embed-book.pyc` 也在）——
  `files` 字段加不上排除写法，改用 `!**/__pycache__/**` 与 `!**/*.pyc`，119 文件 → 107。
- 补 `references/takeover.md`（接手别人的卡/半成品：取证 → 拆成我们的形状 → 五条不破坏），
  并在阶段 2 加了指针；`tests/test_takeover.py` 5 个测试守着它不被当冗余删掉。
- `st-probe.js` 的交互探测与三处判定修正并入本版说明（原先记在 1.4.1 的提交里）。

## 1.4.1 — 2026-11-22

**界面从「能显示」到「能动」。** 上一版把界面做得好看了，但它仍然只是显示器：三个骨架里
没有一个会写 MVU 变量，校验器里没有一条规则管写回，`WRITES` 这种声明干脆不存在。接口
研究（`tavern-helper.md`）白摆着没用上。

- 新增 `references/frontend-interaction.md`（九节，**不进任何阶段的加载清单**）：四栏声明
  （`READS` / `WRITES` / `LISTENS` / `NEEDS`，只读必须显式写 `WRITES = []`）、三种联动形态
  （只读显示器 / 写回控制器 / 开场注入）、写回五步（确认 → 快照 → 写 → 复读 → 失败保留输入）、
  幂等与陈旧确认作废、事件订阅要覆盖「值被改的所有时刻」（只订 `VARIABLE_UPDATE_ENDED`
  会永远停在初值）、值的六种状态、预览模式禁写、写码前四问。
- 新增 `templates/control-center.html`：**第一份真会写变量的骨架**——读 `stat_data` →
  滑条改草稿 → 确认框只列差异（旧值 → 新值）→ `replaceMvuData` → 立刻 `getMvuData`
  复读逐字段比对 → 失败保留输入并显示「未写入：原因」→ 按钮 pending 禁用 + 一次性
  `draftId`。顶部写死四栏声明，预览分支一行写调用都没有。
- 三个旧骨架补四栏声明：`statusbar.html` 显式只读（`WRITES = []`），`opening-ui.html`
  声明它发玩家消息，`wizard-ui.html` 声明本地草稿 + 提交消息。
- `scripts/validate-frontend.py` 新增 **F18–F21**：F18 预览分支（`if (RP_PREVIEW)` 花括号块）
  里有写调用 → 失败；F19 有写调用却没 `WRITES` 声明、或声明 `[]` 却在写 → 失败；
  F20 `replaceMvuData` 之后没有 `getMvuData` 复读 → 警告；F21 有写调用但全文没有
  `disabled`（可连点重复写）→ 警告。
- `references/stage-6-statusbar-ui.md`「写回契约」补上真正缺的那句：**状态栏只读，写数据
  属控制中心**，另挂一条正则、走五步。
- `templates/frontend-prompt.yaml` 增加 `交互:` 一节（读 / 写 / 听 / 依赖），与界面顶部常量对账。
- `tests/test_frontend_interaction.py`（21 个）：四栏声明四态、预览分支误写、写后复读、
  pending 防护、控制中心模板自洽、示例产物零失败。

## 1.4.0 — 2026-11-21

**界面从"能跑"到"像被人设计过"。** 之前三个 HTML 骨架是能用的默认值：五六个颜色、
零个动效、一种字体——产物照着它长，所以界面永远"简陋"。

- 新增 `references/frontend-design.md`（十节，**不进任何阶段的加载清单**）：推色法（三意象 +
  一光源 → 强调色 / 明度三档色板 / 底饱和 ≤12% / 每个色值要有出处，附光源→色相映射表）、
  十种风格配方（铅字报纸 / 冷硬终端 / 霓虹赛博 / 暗黑血污 / 纸本版画 / 泛黄胶片 / 极简单色 /
  古风卷轴 / 仪表盘 / 手绘涂鸦，每种给纹理·边框 / 字体 / 动效 / 禁忌）、系统字体栈
  （五个 `--font-*`，不联网）、八种版式原型（按 700/360 两档画线框）、动效三条规则 + 时长表、
  层级与间距、AI 味 12 条、可访问性下限、写码前五问。
- 三个骨架重做：语义层 `--c-*` / `--f-*` / `--s-*` 与组件层分离；纸纹与硬投影；
  刻度条与 `tabular-nums`；危险态加标记不只换色；圆角收到 2px；全都有
  `prefers-reduced-motion`。
- **预览守卫**：`window.self === window.top` 分流——楼层 iframe 读真实数据，双击打开时走
  `MOCK` + 画布（`--canvas-w`，`?w=360` 看窄屏），且预览里不写 `localStorage`、不真发消息。
  新增 `scripts/make-preview.py` 把成品复制到 `制作文件/产物/preview/`。
- 校验新增 **F15**（有 MOCK 无守卫、或 MOCK 不在 `if (RP_PREVIEW)` 里 → 失败）、
  **F16**（组件层写死色值 / 没有语义色板 → 警告）、**F17**（没有画布变量 → 警告）。
  顺手修 F07 的误判：`<header>` 曾被算成未闭合的 `<head>`。
- 阶段 `opening` / `statusbar` 的判断标准加一条：**先出三版设计稿再写码**，定稿原样进
  `frontend-prompt.yaml`。
- `frontend-conventions.md` 补「预览副本」一节；示例包的两个界面同步升级。
- 体积账：`opening` 23762 / 23771、`statusbar` 22758 / 22761（都在基线内）——
  净增靠同文件回收（`frontend-conventions` 删重复解释、`SKILL.md` 索引行改写）抵平。

## 1.3.1 — 2026-11-21

发布到 npm 的收尾：

- **版本号统一三位 `x.y.z`**。之前用 `1.3.00`，npm 会归一成 `1.3.0`（发布时告警
  `"version" was cleaned`），而 `1.3.09` 和 `1.3.9` 会撞成同一个版本——从此不再带前导零。
- `package.json` 加 `publishConfig.registry`，指向 `https://registry.npmjs.org/`：
  本机全局 registry 是淘宝镜像（只读），不写死会在发布时报错。
- 首次发布在 npm 上留下了 `0.0.0-stage` 占位版（分阶段发布机制的产物），
  内容为空；真正的版本是 1.3.1。

## 1.3.0 — 2026-11-21

**仓库变成多宿主包：Claude Code / Codex / DSH / Pi 四家都能"一条命令装、宿主自己发现更新"。**

skill 本体挪进 `skills/rp-factory/`，仓库根只放清单与工具。这是破坏性改动（脚本路径全变），
换来的是四家宿主原生的目录约定——它们默认都去 `skills/<name>/SKILL.md` 找 skill，
只有搬进子目录才不用给每家用一套私有指法。

- **目录**：`SKILL.md` / `references/` / `templates/` / `scripts/` / `examples/` → `skills/rp-factory/`；
  仓库根新增 `scripts/`（构建与发版工具）、`host-adapters/dsh/`、四份宿主清单、`LICENSE`（MIT）。
- **Claude Code**：`.claude-plugin/{plugin,marketplace}.json`。`plugin.json` 的 `skills: ["."]`
  表示"插件根就是 skill 目录"；市场清单用**相对路径** `"./"`，于是市场仓库就是插件仓库，
  安装不必再 clone 一次。实测 `claude plugin install rp-factory@rp-factory` → `plugin details`
  显示 `Skills (1) rp-factory`。
- **Codex**：`.codex-plugin/plugin.json`（`skills: "./skills/rp-factory/"`）+ 仓库级市场
  `.agents/plugins/marketplace.json`（`source: {source:"local", path:"./"}`）。实测
  `codex plugin marketplace add` + `codex plugin add rp-factory@rp-factory` → `installed, enabled 1.3.00`。
- **DSH**：`host-adapters/dsh/plugin/index.js` 注册一个 skill provider（`rank: 600`，目录当资源基），
  `scripts/build-dsh-plugin.py` 打 `.tgz`（内含一份 skill 副本 + 冒烟测试）。实测插件模块：
  `loadSkillCatalog` 读出 1 条 skill、`modelInvocable: false`（照 SKILL.md 的 `disable-model-invocation`）。
- **Pi**：`package.json` 的 `pi.skills: ["./skills/rp-factory"]` + `pi-package` 关键字。
  实测 `pi install ./` 写入用户包列表。
- **npm**：`package.json` 补齐 name/version/license/author/repository/keywords/files，
  `files` 只含 `skills/rp-factory/`（发布后 `npm install -g` 与 `pi install npm:rp-factory` 都可用）。
- **版本一处真相**：`scripts/sync-manifests.py` 从 SKILL.md 的 `metadata.version` 写进五处清单，
  `--check` 比对漂移；`tests/test_manifests.py`（13 个）把"版本不一致"变成红的。
- **构建**：`scripts/build-skill.py` 从 `skills/rp-factory/` 取源；仓库级 `scripts/check-all.sh`
  串起「单元测试 → 清单一致 → 构建同步 → 加载预算」。
- `run_checks.sh` 不再跑单元测试（那是仓库的事，skill 里没有 `tests/`）。

## 1.2.04 — 2026-11-21

**skill 目录不再等于仓库：新增 `scripts/build-skill.py`。**

skill 目录原来是仓库的 junction，于是 `docs/plans/`、`docs/reviews/`、`tests/`、`node_modules/`、
`.git/` 全都出现在 skill 路径下——它们不占 token（模型只读 `SKILL.md` 与按需的 `references/`），
但确实是「技能里有开发资料」。

- 新增 `scripts/build-skill.py`：白名单构建，只拷 `SKILL.md` + `references/` + `templates/` +
  `scripts/` + `examples/*.yaml`，共 70 文件 / 673 KB；`--check` 比对漂移、`--dry-run` 只看清单；
  目标里若有 `.git` 拒绝清理，链接（junction/symlink）只摘链接不动目标。
- 新增 `tests/test_build_skill.py`（8 个）：白名单不含开发物、文档提到的路径必须真在 skill 里、
  构建后 `--check` 干净、故意制造「缺 / 多 / 旧」三种漂移都能报出、拒绝清理 git 仓库。
- 引用完整性测试当场抓到一个悬空引用：`references/stage-7-delivery.md` 还在提已删的
  `scripts/embed-book.py`，改成「这条第二入口 v1.2.00 删了（脚本已不在仓库）」。
- `SKILL.md` 文件索引里 `check_st_facts.py` + `tests/` 改成 `check_st_facts.py` · `measure_load.py`
  （`tests/` 不在 skill 里，不该让模型去找）。
- README 安装段重写：junction 两种装法 → `git clone` + `build-skill.py`，并说明为什么不直接 junction。
- 体积：九阶段全部低于基线（world −14、delivery −22），SKILL.md 5,565。

## 1.2.03 — 2026-11-21

**把「角色卡」这个词拆开：阶段 2 产的是角色/NPC，不是卡。**

「角色卡」在 SillyTavern 里指那张导入的 `.json`/`.png`。原来阶段 2 也叫「角色卡」，
于是「阶段 2 输出角色卡」这句话在模型那里可以被读成「每个 NPC 各产一张卡」——14 个 NPC
就是 14 个互不相识的导入项。同一个坑还有「场景卡」：ST 根本没有场景卡这个导入项。

- 用词：阶段 2 = **角色/NPC**（产物是 `.yaml` 人物设定，一个包可以有很多个）；阶段 3 =
  **场景**；「角色卡」只保留给交付里那**一张** ST 导入文件。
- `references/stage-2-rolecard.md` → **`stage-2-cast.md`**（文件名与阶段语义对齐）。
- **新增阶段 2 守卫**：`validate-rolecard.py` 扫目录时，出现 `.json` / `.png` / `.webp` /
  `.jpg` / `.charx` 直接 **FAIL**，文案指出「一个包只有一张角色卡，在阶段 7 生成」。
  入口是目录才算（`check-stage.py cast` 走的就是目录）。
- 连带改动：`SKILL.md` 描述与阶段标签、`pipeline.md` 阶段表、`interview-protocol.md`、
  `contract-schema.md`、`contract.yaml`、`stage-3/4/5/6/7`、`web-research.md` 的检索表、
  三个 templates、`check_prose.py` / `measure_load.py` 的注释、README 与 coverage 清单。
  校验器输出从「共 N 张卡」改成「共 N 份人物设定」。

## 1.2.02 — 2026-11-21

**世界书知识补到机制层：先弄清引擎怎么选条目，再谈怎么配。**

之前只有「三灯、套餐、关键词、位置、预算」这张参数表，缺的是「谁先被选中、装到哪
一步停下」。照着参数表配，遇到「条目全在里面但 AI 像没看见」就无从下手。

- 新增 `references/worldbook-engine.md`（按需读，不进任何阶段加载表）：扫描缓冲与
  `include_names` 的真实语义、逐条激活判定顺序、`sticky` 优先 + `order` 降序的装填
  顺序、预算公式与 `continue` 语义、`sortFn` + `unshift` 的组装结果、递归的三个字段、
  `@@` 装饰器、**大卡的四种真实做法**（含实测 8 张实例卡的数字）与六类静默失效。
- `references/worldbook-tuning.md` 修正四处错：合并两个重复的「五、顺序与预算」；
  删掉「常数 > 关键词 > 递归带出」这条不存在的优先级（代码里只看 `order`）；预算改写成
  `Context % × 上下文` 的公式；套餐表补 `preventRecursion` / `ignoreBudget` 两列，
  常驻条目改为 `excludeRecursion: true`（原来写 `false`，与示例书自相矛盾）。
- 新规则 **W19**（单字关键词）/ **W20**（关键词互为子串且不同属一条）/ **W21**
  （正文以 `@@` 开头 → 会被当装饰器剥掉，`FAIL`）/ **W22**（常驻条目没加
  `preventRecursion` 却在正文里点了别人的关键词）。
- 新事实 **S-31…S-35**：预算默认不报警、装填只看 sticky 与 `order`、`@@` 剥离正文、
  `include_names` 只加在发言者、递归是全局设置。锚点 44 + 12 = 56 条。
- 示例包按新规则整改：删掉单字关键词（`他`、`祁`、`轴`）与残词（`夜班的`、`灯室里的`）、
  跨条目子串（`盐镇`/`白盐镇`、`灯油`/`灯油税`）、常驻条目全部加 `preventRecursion`。
- **资料库式**写清楚它不是交付路线、而是一种「条目怎么被选中」的实现：`disable: true` 的
  `[data]` / `[阶段]` 条目 + 控制器 `getwi()` 取用。我们自己早就在用它的窄版本
  （`[ejs]阶段控制器` 按 `wick` 取三条 `[阶段]` 条目），现在把范围讲开、把两个断链点做成规则：
  **W23**（disable 的 `[data]`/`[阶段]` 条目没人取 → 死数据，`WARN`）、**W24**
  （`getwi()` 取的名字与条目 `comment` 不完全一致 → 静默拿到空串，`FAIL`）。
  `references/worldbook-writing.md` 末尾加「条目是数据行」的写法与换用判据。

## 1.2.01 — 2026-11-21

**世界书条目改成「原稿整节切」，不许手写摘要。**

之前交付说明写的是「人物条目写 psychology + behavior（删掉外貌细节、删 nsfw）」
「每级 behavioral_signs 压成一句」——这就是压缩。照这份说明做出来的包，条目读起来
干净，模型的反刍依据也没了。

- 新增 `scripts/cut-worldbook.py` + `templates/worldbook-plan.yaml`：plan 只写选择
  （哪一节、叫什么、关键词、顺序、是否常驻），脚本把那一节**逐行照搬**进 `content`；
  `--merge-protocol` 把阶段 6 的协议条目带过来，不手抄。没切走的原稿内容会被抖出来，
  要么补切、要么写进 `skip`。
- 新规则 **W17**（设定条目逐字命中原稿 <85% 就报）/ **W18**（原稿某份文件大段没进书
  就报）。协议条目按 `[` 前缀豁免。
- 阶段 1 加「结构要切得动」：每节自包含、节名即条目名、一节一件事。
- `worldbook-writing.md` 加第零节：不摘要 / 不合并 / 不润色，改稿回原稿改。
- 示例包重切：`白潮 世界书.json` 21 条（12 条设定由四份原稿整节切出 + 9 条协议），
  19,238 字，`W17`/`W18` 全过；`制作文件/项目记录/世界书切割.yaml` 是它的 plan。
- 参考实现对照：`我，非我` 22 条 / 42,945 字 / 单条均 1,952 / 最长 6,184，整节搬。

## 1.2.00 — 2026-11-21

**交付路线改成「分包不内嵌」：卡、世界书、正则、脚本、界面 html、导入说明各一份。**

| 之前 | 现在 |
|---|---|
| 卡里内嵌 `tavern_helper.scripts`（MVU 两条跟卡走） | 脚本独立成 `<世界名> 酒馆助手脚本.json`，导入后在插件里打开 |
| `正则.json` 的替换里塞满 HTML | 替换是 `【尚未粘贴界面】…` 占位，HTML 另发一份供手动粘贴 |
| 交付三件 | 五槽：卡 / 世界书 / 正则 / 脚本（条件）/ 导入说明，另加两个 html 粘贴素材 |

- 新规则 **C12**（`validate-st-package.py`）：卡里有 `tavern_helper.scripts` 直接失败——内嵌脚本要进角色白名单才跑，和单独导入的同一份同时启用会跑两遍。
- 新规则 **R07**：带界面的正则替换是空的就失败（空替换等于删掉这行），待粘占位则通过；隐藏类正则（变量更新块）允许空替换。
- `validate-contract.py` 的 **C15** 扩成五槽：平铺无子目录、按内容嗅探核对文件名与内容（世界书里装的是卡会被点名）、待粘占位必须配 `.html`、缺导入说明直接失败。
- 新骨架 `templates/import-guide.txt`；`templates/regex-frontend.json` 的替换改为待粘占位。
- 示例包重排：卡摘掉 `tavern_helper`，新增 `白潮 酒馆助手脚本.json`（文件夹形）、两个 html、`导入说明.txt`。
- 删掉 `scripts/embed-book.py`（内嵌书第二入口）：它造出的卡正是 C09 要拦的。S-16 / S-24 / S-29 三条事实保留。
- 新事实 **S-30**（正则导入的三个目标：全局 / 角色专属 / 预设，本 skill 一律用全局）、**TH-11**（插件导入脚本时强制 `enabled=false` 并重生成 `id`，导入 ≠ 在跑）；锚点数据到 36 + 12 条。
- 加载量在 `delivery` 阶段一度超上限，靠删内嵌书章节与收紧措辞抵平（**基线未动**）。

## 1.1.00 — 2026-11-21

**破坏性变更：作品目录改成两层。** 旧项目要搬一次，脚本会拦着不让你两套并存。

| 旧 | 新 |
|---|---|
| `创作痕迹/` | `制作文件/`（原稿、源码、检查材料） |
| `创作痕迹/{contract, 项目档案, 创作记录, 检索来源, 验收, 试演记录}` | `制作文件/项目记录/` 下同名文件 |
| `创作痕迹/产物/` | `制作文件/产物/`（不变） |
| `最终产物/` | `导入包/`（交付成品，平铺） |

- 作品根下只许 `制作文件/` 与 `导入包/`（新门 **C17**）：发现 `创作痕迹/` 或 `最终产物/` 直接失败并给迁移提示，根目录散落文件记警告。
- `validate-contract.py` 接受项目根、`制作文件/`、`制作文件/项目记录/`、契约文件四种入口。
- `scripts/run_checks.sh`、`check-stage.py`、`check_acceptance.py`、`validate-st-package.py`、
  `validate_st_semantics.py`、`check_prose.py`、`st-import.py`、`st-probe.js` 全部改指新路径。
- 示例包重排：`examples/dry-run-盐湖守夜人/{制作文件/项目记录, 制作文件/产物, 导入包}`，原 `README.md` 移入 `制作文件/试跑记录.md`。
- 新增 `tests/test_layout.py`（旧布局阻断、根目录清洁、账本归位、导入包平铺）。
- 加载量在改名后涨了 190 tok；靠 `SKILL.md` 与 `references/pipeline.md` 就地回收冗余抵平（**基线未动**）。

## 1.0.01 — 2026-11-21

首个带版本号的版本。此前四轮工作合并入 `main`。

**产物合规层**
- 十四道门统一编号 0–13，`references/pipeline.md` 为唯一权威；加载预算器 `scripts/measure_load.py`
  （绝对上限 26,000，九阶段各自基线）。
- 契约新增 `player_agency`（player-controlled / limited / delegated）与角色卡 `facts`（stable / temporary）。
- 世界书写作文档 `references/worldbook-writing.md`（句子功能、五档强度、知识度数、语义不变量）。

**质量层**
- `scripts/check_prose.py` P01–P09 去 AI 味（含真包校准：免疫区、内联长值、台词误报）。
- `references/rehearsal.md` 试演：四类证据分离、最小响应八种、四类判据（代演 / OOC / 口癖 / 数值闸门）。
- `references/acceptance.md` 六层证据 + `scripts/check_acceptance.py`（A00–A06，L4 十一维，L5/L6 只能人签）。

**SillyTavern 正确性层**
- `references/st-correctness.md`：S-01…S-29 会静默失效的语义事实，每条带 `public/…:line` 锚点。
- `scripts/validate_st_semantics.py`（S 系列机检）、`scripts/check_st_facts.py`（34 个 ST 锚点 + 10 个插件锚点）。
- `references/tavern-helper.md`：酒馆助手 4.12.1 接口速查（渲染链路、srcdoc 约束、iframe 全局、
  变量/消息/显示/事件/MVU、23 个命名空间索引、静默失效清单）。
- `scripts/validate-frontend.py` F01–F14（新增 F10–F14：事件名写字符串、相对路径、父文档、
  `refresh:'all'`、裸 `setInterval`）。

**工程**
- `scripts/run_checks.sh` 一键全检；`tests/` 143 个用例；`scripts/embed-book.py` 世界书双入口。
- 真机实证：卡内 scoped 正则默认不生效且取消一次永久静默（S-28）、内嵌书按 `character_book.name`
  落盘（S-29）、导入 API 用 `avatar` 字段。
