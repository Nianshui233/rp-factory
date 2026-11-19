# 契约规范

骨架在 `templates/contract.yaml`。本文件说明它是什么、谁写、冲突怎么办。

## 一、定位

**契约是索引与命名权威，不是产物全量中间态。**

- 进契约的：项目元信息、每阶段状态、内容边界、**名字表**、已锁定的硬设定、待定项、用户决策、产物索引。
- 不进契约的：世界观正文、角色卡的 `psychology` / `behavior` / `speech`、数值系统的 `thresholds` / `calculation` / `boundaries`。这些存在产物里，由 `artifacts[]` 指向。

理由：把长篇设定复制进契约，就等于同一份内容维护两遍，改一处忘一处。

## 二、键区

| 键区 | 装什么 |
|---|---|
| `project` | 名字、模态（`text` / `engineering`）、RP 形式、语言 |
| `stages` | 每阶段状态：`none` / `partial` / `done` / `skipped` |
| `content_boundaries` | `rating`、`hard_no`、`soft_no` |
| `naming` | `world`、`factions[]`、`places[]`、`systems[]`、`axes[]` |
| `hard_settings` | 已锁定的硬设定，`source` 必须标 `用户确认` 或 `推导` |
| `pending` | 待定项汇总 |
| `decisions` | 用户拍过的板 |
| `artifacts` | 产物索引，`type` 只能是四类之一 |

## 三、独占写者

| 键区 | 独占写者 |
|---|---|
| `project.*`、`content_boundaries.*` | 主 skill（边界门） |
| `naming.world` / `factions` / `places` / `systems` | 阶段 1 |
| `naming`（角色相关新增项） | 阶段 2 |
| `naming.axes` | 阶段 4 接管；阶段 2 / 3 可写 `provisional: true` 的临时项 |
| `hard_settings` | 各阶段追加，只有用户确认的才 `locked` |

`artifacts` 与 `stages` 各阶段都写自己的那一项，不算冲突。

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
- 内容边界（`rating` / `hard_no`）不叫硬设定，它们是边界门的一部分，优先级更高。
