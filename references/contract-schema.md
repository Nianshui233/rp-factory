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
| `project` | 名字（`name` = 项目文件夹名）、**工作区绝对路径**（`workspace`）、模态（`text` / `engineering`）、RP 形式、语言、**本次要跑的阶段**（`stages_requested`，按执行顺序写名字）、**是否联网检索**（`web_research` / `source_ip`）、**SillyTavern 探测结果**（`sillytavern`） |
| `stages` | 九阶段状态，**名字键**：`world` / `cast` / `scenes` / `axes` / `mvu` / `ejs` / `opening` / `statusbar` / `delivery`；值 `none` / `partial` / `done` / `skipped`（未勾选写 `skipped`） |
| `delivery` | `route`（`native` / `st` / `both`）、`st_name`（角色卡名，默 = `project.name`；世界书名另行取 `<st_name> 世界书`）、`files[]`（相对 `最终产物/`） |
| `content_boundaries` | `nsfw`（开局第三问）、`rating`、`hard_no`、`soft_no` |
| `naming` | `world`、`factions[]`、`places[]`、`systems[]`、`axes[]`、`schema_axes[]`（`mvu` 阶段实际投影进 zod 的轴名，供交付校验查漏）、`ui_tags`（表现层标签名） |
| `hard_settings` | 已锁定的硬设定，`source` 必须标 `用户确认` 或 `推导` |
| `pending` | 待定项汇总 |
| `decisions` | 用户拍过的板。两种形状都收：阶段决策 `{stage, question, answer}`、过程决策 `{date, item, choice, because}` |
| `artifacts` | 产物索引，`type` 只能是九类之一（见第六节表） |

## 三、独占写者

| 键区 | 独占写者 |
|---|---|
| `project.*`（含 `stages_requested` / `web_research` / `source_ip` / `sillytavern`）、`content_boundaries.*`（含 `nsfw`） | 主 skill（开局门与边界门） |
| `naming.world` / `factions` / `places` / `systems` | 阶段 1 |
| `naming`（角色相关新增项） | 阶段 2 |
| `naming.axes` | 阶段 4 接管；阶段 2 / 3 可写 `provisional: true` 的临时项 |
| `naming.schema_axes` | 阶段 `mvu`（写完就改其余阶段不许动）；它与 `axes` 不一致时以 `axes` 为准并回写 |
| `naming.ui_tags` | 阶段 5 写 `opening`，阶段 6 写 `status`；写定后不兼改 |
| `delivery.*` | 阶段 7（收尾那一问）；写定后改路线只改 `route`，不重命名 `st_name` |
| `hard_settings` | 各阶段追加，只有用户确认的才 `locked` |

`artifacts[].type` 只有十四类：`project-profile` / `world-bible` / `rolecard` / `scene-sheet` / `axis-system` / `mvu-schema` / `mvu-initvar` / `mvu-entries` / `mvu-regex` / `ejs-controller` / `opening-ui` / `statusbar-ui` / `st-card` / `st-regex` / `st-worldbook`。不许自造（一次实操里出现过 `role-cards`、`secret-layer`——前者该写 `rolecard`，后者根本不是产物）。

`artifacts` 与 `stages` 各阶段都写自己的那一项，不算冲突。`artifacts[].path` 用**相对项目根**的写法（`创作痕迹/产物/world-bible.yaml`），不用绝对路径、不许含 `..`、同一路径不许出现两次。**运行期所有产物都在 `创作痕迹/产物/` 下**；`最终产物/` 是交付目录，交付前必须为空（校验器 C13 盯着）。多张角色卡或有多张场景卡时，`path` 指向目录（`创作痕迹/产物/rolecard/`），`type` 仍是 `rolecard` / `scene-sheet`——文件数不改变产物类别，别为"有 14 张卡"另起一个类型。表现层一份产物落两到三个文件，`type` 都写 `opening-ui` 或 `statusbar-ui`，靠 `path` 区分：界面 HTML、正则 JSON，以及可选的提示词条目 `frontend-prompt.yaml`（两个阶段共用一个文件名，后写的追加字段，不覆盖前一个；建卡向导通常不需要它）。酒馆三件套同理：三个文件都写阶段 7，`type` 分别是 `st-card` / `st-regex` / `st-worldbook`，`path` 在 `最终产物/` 根下；`正则.json` 是装配用的导出件，阶段 5 / 6 的 HTML 与正则草稿仍记在 `创作痕迹/产物/` 下。

`project.workspace` 与 `project.name` 必须同时更新：前者是用户确认的**工作区**（父目录）绝对路径，后者是子文件夹名（= 世界名，未定时为 `未命名项目`）。项目实际路径 = `<workspace>/<name>/`。只改一个 = 指向一个不存在的目录。

## 四、冲突规则

- **写已存在的键 = 冲突。** 停下问用户，不许静默覆盖，不许"我判断他是想改名"。
- **`provisional: true`**：阶段 2 / 3 若需要轴名（好感度、堕落值等），可先写进 `naming.axes` 并标 `provisional: true`。阶段 4 接管时逐条确认或改名，接管后删除 `provisional` 键。
- **改名**：改 `naming` 里的一项后，必须回写所有已引用它的产物，并记入 `decisions`。只改契约不改产物 = 制造的正是本包要消灭的漂移。
- **`stages` 不是标量**：乱序进入合法，`stages.scenes: done` 不意味着 `stages.world` 已完成。
- **阶段名不许翻译**：写 `cast` 不写 `角色卡`，写 `mvu` 不写 `变量系统`。旧的数字键仍能读（按七阶段编号解释），但校验器会提醒改——`5` 在旧契约里指 `opening`、在新枚举里指 `mvu`，这种错位不会报错，只会静默算错。

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
| `stages.<名字>: skipped` | 没勾的阶段 | 只是"本次不跑"，不等于"不需要"；下游阶段缺输入时照旧走补采访问 |
| `project.web_research`（+ 需要时 `source_ip`） | 开局第四问 | 中途开/关都要记 `decisions`；开启时建 `创作痕迹/检索来源.md` 并从当前阶段起按 `references/web-research.md` 检索；关闭时停止检索，不补查旧账 |
| `content_boundaries.nsfw` + `rating` | 开局第三问 | 开关一次就重锁 `rating` 并记 `decisions`；关掉时必须清掉已交付产物里的越界内容，只改开关不算数 |

## 八、写完就跑校验器

```
python scripts/validate-contract.py <创作痕迹/contract.yaml>
```

它查 C01–C13：`project` 必填与 `stages_requested` 枚举、九个阶段名各自的取值在 `none/partial/done/skipped` 内、`artifact.type` 在十四类枚举内、`path` 相对且真实存在、**`done` 的阶段有对应产物**（`mvu` 至少要有 `mvu-schema`/`mvu-initvar`/`mvu-entries` 之一，`ejs` 要有 `ejs-controller`）、`delivery.route` 与 `files` 自洽、`naming` 收口（阶段 4 完成后 `axes` 不许再带 `provisional`）、`hard_settings.source` 以 `用户确认`/`推导` 开头、`最终产物/` 在交付前必须空。

`partial` 不会被判失败，但必须出现在 `pending[]` 里（哪一项、为什么、缺什么才到 `done`）——一次实操里 `stages.1` 停在 `partial` 再没人回头，后面三个阶段全建在没收口的世界观上。

## 九、`project.sillytavern`：开局静默探测

开局问四件之前，先跑一次 `python scripts/detect-sillytavern.py`（**不告诉用户、不占问题预算**），把结果写进这一段；之后各阶段读契约，不重复探测。

```yaml
sillytavern:
  install: "D:/AI/SillyTavern"      # 安装目录
  user_dir: "D:/AI/SillyTavern/data/default-user"
  running_url: "http://127.0.0.1:8000"   # 没在跑写 ""
  pkg_version: "1.19.0"
  extension_tavern_helper: true
```

写回规矩：

- 探测不到安装 → 整段写 `sillytavern: null`，**不追问**、不提示用户去装；阶段 5/6 照常做（产物是文件），阶段 7 只交文件。
- 有安装没在跑 → 其余照填，`running_url: ""`；阶段 7 的「导入并实测」不问（问了也做不了），改为一句"启动后要我导也说一声"。
- 只写探测到的事实，不写推测（端口拿不到就是空着，不写 8000）。
- 中后期用户自己装了/换端口了 → 重跑一次脚本、覆盖这一段，记 `decisions` 一条即可。
