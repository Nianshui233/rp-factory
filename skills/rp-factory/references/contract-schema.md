# 契约规范

位置：`<工作区>/<世界名>/制作文件/项目记录/contract.yaml`。骨架在 `templates/contract.yaml`。本文件说明它是什么、谁写、冲突怎么办。

## 一、定位

**契约是索引与命名权威，不是产物全量中间态。**

- 进契约的：项目元信息、每阶段状态、内容边界、**名字表**、已锁定的硬设定、待定项、用户决策、产物索引。
- 不进契约的：世界观正文、人物设定的 `psychology` / `behavior` / `speech`、数值系统的 `thresholds` / `calculation` / `boundaries`。这些存在产物里，由 `artifacts[]` 指向。

理由：把长篇设定复制进契约，就等于同一份内容维护两遍，改一处忘一处。

## 二、键区

| 键区 | 装什么 |
|---|---|
| `project` | 名字（`name` = 项目文件夹名）、**工作区绝对路径**（`workspace`）、模态（`text` / `engineering`）、RP 形式、语言、**本次要跑的阶段**（`stages_requested`，按执行顺序写名字）、**是否联网检索**（`web_research` / `source_ip`）、**SillyTavern 探测结果**（`sillytavern`） |
| `stages` | 九阶段状态，**名字键**：`world` / `cast` / `scenes` / `axes` / `mvu` / `ejs` / `opening` / `statusbar` / `delivery`；值 `none` / `partial` / `done` / `skipped`（未勾选写 `skipped`） |
| `delivery` | `route`（`native` / `st` / `both`）、`st_name`（角色卡名，默 = `project.name`；世界书名另行取 `<st_name> 世界书`）、`files[]`（相对 `导入包/`） |
| `content_boundaries` | `nsfw`（开局第三问）、`rating`、`hard_no`、`soft_no` |
| `player_agency` | 演出许可：`mode`（`player-controlled` / `limited` / `delegated`）、`allowed`、`excluded`、`scope`、`duration`、`source`。缺省 = `player-controlled` |
| `naming` | `world`、`factions[]`、`places[]`、`systems[]`、`axes[]`、`schema_axes[]`（`mvu` 阶段实际投影进 zod 的轴名，供交付校验查漏）、`ui_tags`（表现层标签名） |
| `hard_settings` | 已锁定的硬设定，`source` 必须标 `用户确认` 或 `推导` |
| `pending` | 待定项汇总（`partial` 阶段必须有一条，否则 C14 失败） |
| `decisions` | 谁拍的板：阶段决策 `{stage, question, answer}` 或过程决策 `{item, choice, because}`，可挂 `state` 四态；`proposed` 必须带 `why`，写着「没回答」的条目不许是 `confirmed`（C13）。见 `references/decisions.md` |

## 三、独占写者

| 键区 | 独占写者 |
|---|---|
| `project.*`（含 `stages_requested` / `web_research` / `source_ip` / `sillytavern`）、`content_boundaries.*`（含 `nsfw`） | 主 skill（开局门与边界门） |
| `player_agency` | 主 skill（边界门）写 `player-controlled`；`opening` 阶段仅在用户明确要求时放宽，并在 `decisions` 记一条 |
| `naming.world` / `factions` / `places` / `systems` | 阶段 1 |
| `naming`（角色相关新增项） | 阶段 2 |
| `naming.axes` | 阶段 4 接管；阶段 2 / 3 可写 `provisional: true` 的临时项 |
| `naming.schema_axes` | 阶段 `mvu`（写完就改其余阶段不许动）；它与 `axes` 不一致时以 `axes` 为准并回写 |
| `naming.ui_tags` | 阶段 `opening` 写 `opening`，阶段 `statusbar` 写 `status`；写定后不兼改 |
| `delivery.*` | 阶段 `delivery`（收尾那一问）；写定后改路线只改 `route`，不重命名 `st_name` |
| `hard_settings` | 各阶段追加，只有用户确认的才 `locked` |

`artifacts[].type` 只有十五类：`project-profile` / `world-bible` / `rolecard` / `scene-sheet` / `axis-system` / `mvu-schema` / `mvu-initvar` / `mvu-entries` / `mvu-regex` / `ejs-controller` / `opening-ui` / `statusbar-ui` / `st-card` / `st-regex` / `st-worldbook` / `st-script`。不许自造（实操里出现过 `role-cards`、`secret-layer`——前者该写 `rolecard`，后者不是产物）。

`artifacts` 与 `stages` 各阶段都写自己的那一项，不算冲突。`artifacts[].path` 用**相对项目根**的写法（`制作文件/产物/world-bible.yaml`），不用绝对路径、不许含 `..`、同一路径不许出现两次。**运行期产物都在 `制作文件/产物/`**；`导入包/` 交付前必须为空（C15）。有多张同类卡时 `path` 指向目录（`制作文件/产物/rolecard/`），`type` 仍是 `rolecard` / `scene-sheet`——文件数不改变产物类别，别为卡多另起类型。表现层一份产物可落两三个文件，`type` 都写 `opening-ui` 或 `statusbar-ui`，靠 `path` 区分（界面 HTML、正则 JSON、可选 `frontend-prompt.yaml`——两阶段共用文件名，后写的追加字段不覆盖）。酒馆分包同理：卡 / 正则 / 世界书 / 脚本四个文件都算 `delivery` 的产物，`type` 分别为 `st-card` / `st-regex` / `st-worldbook` / `st-script`，`path` 在 `导入包/` 根下；`导入说明.txt` 与界面 `.html`（粘贴素材）也是交付件，但只是 `delivery.files[]` 里的一项，不必各占一个 type。正则草稿与界面源文件仍记在 `制作文件/产物/`。

`project.workspace` 与 `project.name` 必须同时更新：前者是用户确认的**工作区**（父目录）绝对路径，后者是子文件夹名（= 世界名，未定时为 `未命名项目`）。项目实际路径 = `<workspace>/<name>/`。只改一个 = 指向一个不存在的目录。

## 四、冲突规则

- **写已存在的键 = 冲突。** 停下问用户，不许静默覆盖，不许"我判断他是想改名"。
- **`provisional: true`**：阶段 2 / 3 若需要轴名（好感度、堕落值等），可先写进 `naming.axes` 并标 `provisional: true`。阶段 4 接管时逐条确认或改名，接管后删除 `provisional` 键。
- **改名**：改 `naming` 里的一项后，必须回写所有已引用它的产物，并记入 `decisions`。只改契约不改产物 = 制造的正是本包要消灭的漂移。
- **`stages` 不是标量**：乱序进入合法，`stages.scenes: done` 不意味着 `stages.world` 已完成。
- **阶段名不许翻译**：写 `cast` 不写「角色」，写 `mvu` 不写 `变量系统`。旧的数字键仍能读（按七阶段编号解释），但校验器会提醒改——`5` 在旧契约里指 `opening`、在新枚举里指 `mvu`，这种错位不会报错，只会静默算错。

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
| `project.stages_requested` | 开局多选 | 追加时把该阶段 `skipped` 改 `none` 并记 `decisions`；已 `done` 的不受影响 |
| `stages.<名字>: skipped` | 没勾的阶段 | 只是「本次不跑」，不等于「不需要」；下游缺输入照旧走补采访问 |
| `project.web_research`（+ `source_ip`） | 开局第四问 | 中途开关都记 `decisions`；开启即建 `制作文件/项目记录/检索来源.md` 并按 `references/web-research.md` 检索，关闭就停、不补旧账 |
| `content_boundaries.nsfw` + `rating` | 开局第三问 | 开关一次就重锁 `rating` 并记 `decisions`；关掉时必须清掉已交付产物里的越界内容，只改开关不算数 |

## 八、写完就跑校验器

```
python scripts/check-stage.py <阶段名> <项目根>      # 阶段收尾一检，内部会跑契约校验
python scripts/validate-contract.py <制作文件/项目记录/contract.yaml>   # 只看契约时单独跑
```

它查 C01–C16：`project` 必填与 `stages_requested` 枚举、九个阶段名各自的取值在 `none/partial/done/skipped` 内、`artifact.type` 在十四类枚举内、`path` 相对且真实存在、**`done` 的阶段有对应产物**（`mvu` 至少要有 `mvu-schema`/`mvu-initvar`/`mvu-entries` 之一，`ejs` 要有 `ejs-controller`）、`delivery.route` 与 `files` 自洽、`naming` 收口（阶段 4 完成后 `axes` 不许再带 `provisional`）、`hard_settings.source` 以 `用户确认`/`推导` 开头、`导入包/` 交付前须空（C15）、`player_agency` 三档自洽（C16）；C13/C14 见上表。

`partial` 不会被判失败，但必须出现在 `pending[]` 里（哪一项、为什么、缺什么才到 `done`）——一次实操里 `stages.1` 停在 `partial` 再没人回头，后面三个阶段全建在没收口的世界观上。

## 九、`project.sillytavern`：开局静默探测

开局问四件之前先跑 `python scripts/detect-sillytavern.py`（**不告诉用户、不占问题预算**），结果写进这一段；之后各阶段读契约，不重复探测。

```yaml
sillytavern:
  install: "D:/AI/SillyTavern"      # 安装目录
  user_dir: "D:/AI/SillyTavern/data/default-user"
  running_url: "http://127.0.0.1:8000"   # 没在跑写 ""
  pkg_version: "1.19.0"
  extension_tavern_helper: true
```

- 探测不到安装 → 整段 `sillytavern: null`，**不追问**、不提示去装；`opening` / `statusbar` 照常做（产物是文件），`delivery` 只交文件。
- 有安装没在跑 → 其余照填，`running_url: ""`；`delivery` 的「导入并实测」不问，改为一句「启动后要我导也说一声」。
- 只写探测到的事实（端口拿不到就空着，不写 8000）；用户后来装了或换端口 → 重跑脚本覆盖这一段，记 `decisions` 一条。

## 十、`player_agency`：能不能替玩家写

缺省 `player-controlled`（不写这一段 = 不替玩家做任何事，老契约合法）。三档：`player-controlled` / `limited`（只写 `allowed` 那几处）/ `delegated`（整段代跑，须给 `duration`）。

放宽不是推断出来的：放宽到后两档必须 `source: 用户确认…`，且 `allowed` 非空（C16）；放宽时记一条 `decisions`。三档的完整纪律与判据见 `references/decisions.md` 第六节。
