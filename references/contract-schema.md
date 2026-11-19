# 契约规范

位置：`<工作区>/<世界名>/创作痕迹/contract.yaml`。骨架在 `templates/contract.yaml`。本文件说明它是什么、谁写、冲突怎么办。

## 一、定位

**契约是索引与命名权威，不是产物全量中间态。**

- 进契约的：项目元信息、每阶段状态、内容边界、**名字表**、已锁定的硬设定、待定项、用户决策、产物索引。
- 不进契约的：世界观正文、角色卡的 `psychology` / `behavior` / `speech`、数值系统的 `thresholds` / `calculation` / `boundaries`。这些存在产物里，由 `artifacts[]` 指向。

理由：把长篇设定复制进契约，就等于同一份内容维护两遍，改一处忘一处。

## 二、键区

| 键区 | 装什么 |
|---|---|
| `project` | 名字（`name` = 项目文件夹名）、**工作区绝对路径**（`workspace`）、模态（`text` / `engineering`）、RP 形式、语言、**本次要跑的阶段**（`stages_requested`）、**是否联网检索**（`web_research` / `source_ip`） |
| `stages` | 每阶段状态：`none` / `partial` / `done` / `skipped`（未勾选写 `skipped`） |
| `content_boundaries` | `nsfw`（开局第三问）、`rating`、`hard_no`、`soft_no` |
| `naming` | `world`、`factions[]`、`places[]`、`systems[]`、`axes[]`、`ui_tags`（表现层标签名） |
| `hard_settings` | 已锁定的硬设定，`source` 必须标 `用户确认` 或 `推导` |
| `pending` | 待定项汇总 |
| `decisions` | 用户拍过的板 |
| `artifacts` | 产物索引，`type` 只能是六类之一 |

## 三、独占写者

| 键区 | 独占写者 |
|---|---|
| `project.*`（含 `stages_requested` / `web_research` / `source_ip`）、`content_boundaries.*`（含 `nsfw`） | 主 skill（开局门与边界门） |
| `naming.world` / `factions` / `places` / `systems` | 阶段 1 |
| `naming`（角色相关新增项） | 阶段 2 |
| `naming.axes` | 阶段 4 接管；阶段 2 / 3 可写 `provisional: true` 的临时项 |
| `naming.ui_tags` | 阶段 5 写 `opening`，阶段 6 写 `status`；写定后不兼改 |
| `hard_settings` | 各阶段追加，只有用户确认的才 `locked` |

`artifacts` 与 `stages` 各阶段都写自己的那一项，不算冲突。`artifacts[].path` 用**相对项目根**的写法（`最终产物/world-bible.yaml`），不用绝对路径。表现层一份产物落两到三个文件，`type` 都写 `opening-ui` 或 `statusbar-ui`，靠 `path` 区分：界面 HTML、正则 JSON，以及可选的提示词条目 `frontend-prompt.yaml`（两个阶段共用一个文件名，后写的追加字段，不覆盖前一个；建卡向导通常不需要它）。

`project.workspace` 与 `project.name` 必须同时更新：前者是用户确认的**工作区**（父目录）绝对路径，后者是子文件夹名（= 世界名，未定时为 `未命名项目`）。项目实际路径 = `<workspace>/<name>/`。只改一个 = 指向一个不存在的目录。

## 四、冲突规则

- **写已存在的键 = 冲突。** 停下问用户，不许静默覆盖，不许"我判断他是想改名"。
- **`provisional: true`**：阶段 2 / 3 若需要轴名（好感度、堕落值等），可先写进 `naming.axes` 并标 `provisional: true`。阶段 4 接管时逐条确认或改名，接管后删除 `provisional` 键。
- **改名**：改 `naming` 里的一项后，必须回写所有已引用它的产物，并记入 `decisions`。只改契约不改产物 = 制造的正是本包要消灭的漂移。
- **`stages` 不是标量**：乱序进入合法，`stages.3: done` 不意味着 `stages.1` 已完成。

## 五、命名门要读两处

`naming.axes` 是投影，投影可能与 `axis-system.yaml` 正文不一致。所以命名门四步（见 `references/pipeline.md`）必须**同时读契约与产物**：只查契约会把"契约里叫 X、产物里写 Y"这种情况漏掉。

## 六、什么算硬设定

只有当它满足两条才算：会改变世界走向，且用户明确确认过。

- 用户明确说过的规则 → `source: 用户确认`
- 系统按判断推出来的 → `source: 推导`。推导项不享受"不可改"待遇，后续阶段可以推翻。
- 内容边界（`nsfw` / `rating` / `hard_no`）不叫硬设定，它们是边界门的一部分，优先级更高。

## 七、开局的值怎么锁

| 值 | 来源 | 变了怎么办 |
|---|---|---|
| `project.stages_requested` | 开局多选 | 追加就追加，把该阶段 `skipped` 改 `none`，记 `decisions`。已 `done` 的阶段不受影响 |
| `stages.n: skipped` | 没勾的阶段 | 只是"本次不跑"，不等于"不需要"；下游阶段缺输入时照旧走补采访问 |
| `project.web_research`（+ 需要时 `source_ip`） | 开局第四问 | 中途开/关都要记 `decisions`；开启时建 `创作痕迹/检索来源.md` 并从当前阶段起按 `references/web-research.md` 检索；关闭时停止检索，不补查旧账 |
| `content_boundaries.nsfw` + `rating` | 开局第三问 | 开关一次就重锁 `rating` 并记 `decisions`；关掉时必须清掉已交付产物里的越界内容，只改开关不算数 |
