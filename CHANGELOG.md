# 变更记录

版本号写在 `SKILL.md` frontmatter 的 `metadata.version`；这份文件的第一条标题必须与它一致，
由 `tests/test_version.py` 守着。

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
