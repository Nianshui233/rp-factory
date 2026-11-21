# 变更记录

版本号写在 `SKILL.md` frontmatter 的 `metadata.version`；这份文件的第一条标题必须与它一致，
由 `tests/test_version.py` 守着。

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
