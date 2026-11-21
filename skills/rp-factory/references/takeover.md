# 接手别人的包

用户给你的不是我们的产物：别人的角色卡、半成品目录、导出的 PNG，甚至只有一张截图。要在这上面继续做，缺的不是创作能力，是**取证纪律**——先弄清手里是什么，再决定改哪里。

只在下述情形读这一份：用户说「我有一张卡想改」「这是别人做的」「接着这个往下做」。从零开始的正常流程不需要它。

## 一、先别改，先取证

三件事做完之前，任何写入都算破坏证据。

1. **只读快照**：原文件复制一份到 `制作文件/产物/takeover/original/`，记 `sha256` 与大小，之后所有操作只在副本上做，原文件字节不动。
2. **资产清单**：卡里有什么、书在哪、正则几条、脚本几条、界面藏在哪条正则的 `replaceString` 里。
3. **能跑的先跑一遍**：把卡导入一次，看它**实际**长什么样——不导入就下结论，等于拿字段名猜行为。

```bash
sha256sum "原卡.json" > 制作文件/产物/takeover/original/SHA256
python - <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
data = d.get("data", d)
ext = data.get("extensions") or {}
book = data.get("character_book") or {}
print("卡名:", data.get("name"), "| 首条:", len(data.get("first_mes") or ""), "字")
print("内嵌书:", book.get("name"), "|", len(book.get("entries") or []), "条")
print("绑定书:", ext.get("world"))
print("正则:", len(ext.get("regex_scripts") or []), "条")
print("助手脚本:", [s.get("name") for s in ((ext.get("tavern_helper") or {}).get("scripts") or [])])
PY
```

**只用 `st-probe.js` 看四维不够**：界面在不在、变量动不动，要按 `references/acceptance.md` 的 L4 逐维记。已见到最常见的一种坏包：卡能导入、书挂上了、界面是六个字符的占位标签，正则在卡里但从未被授权（`references/st-correctness.md` 的 S-28）。

## 二、拆成我们的形状

| 卡里的东西 | 落到哪 | 注意 |
|---|---|---|
| `description` / `personality` / `scenario` / `mes_example` | `制作文件/产物/rolecard/*.yaml` | 原文照抄进字段，不要摘要；`first_mes` 单独走开局 |
| `first_mes` + 内嵌书 + 正则 | `制作文件/产物/**` + `world-bible.yaml` | 先判断它属于「世界设定」还是「剧情事实」 |
| `character_book` | `<世界名> 世界书.json` | 它是**别人压过的版本**，不是原稿；改它之前先找原始设定 |
| `extensions.regex_scripts` | `正则.json` | 卡内是 camelCase，助手端是 snake_case，见 `references/st-correctness.md` 的 S-25 |
| `extensions.tavern_helper.scripts` | `酒馆助手脚本.json` | 导入后 `enabled` 是 false、`id` 会重生成（TH-11） |
| `replaceString` 里的界面 | `<世界名> 前端/*.html` | 从替换串里提出来另存，仓里留占位（`PENDING_UI_MARK`） |

拆出来的东西一律标来源：`制作文件/项目记录/项目档案.yaml` 加 `接手:` 一节，写原文件、sha256、拆出日期、作者（若有）。**哪些是我们写的、哪些是原作者的**，必须能在账本里分开读。

## 三、五条不破坏的规矩

违反任何一条，用户回不到原状。

1. **原文件字节不动**：只读它的副本，原文件连换个编码都不行。
2. **快照与工作区分开**：`original/` 只进不出，改出来的东西放 `decoded/`，两者不互相覆盖。
3. **不提原路径**：产物里不要写「见 D:\…」这类绝对路径，换机器就断。
4. **回读比对**：改完把新卡导入一次、读回字段，确认改的生效了、没改的没变；`roundtrip/` 里放前后对照。
5. **记 adapter 版本**：你按哪个版本的 ST / 助手插件语义拆的，写进档案——半年后语义变了，这条是唯一的解释。

## 四、改的时候

- **一次一处**：先改看得见的那一处，验证生效，再改下一处。批量改完一起导入，失败时不知道是谁坏的。
- **别重写**：接手最常见的失败是把别人的卡「顺手改得更好」——改的是他没提的部分，用户回不去。用户点名的才改（同 `references/rehearsal.md` 的最小响应集合）。
- **内嵌书不等于原稿**：它可能是删节版，也可能已经丢了条目。要扩写就得找回原始设定；找不到就明说「只能在这个压缩版上改」。
- **改完要重新导入**：酒馆读的是导入时那份，磁盘上的 json 变了不会自动生效。

## 五、收尾交付什么

1. 改好的包（走正常的交付门 `check-stage.py delivery`）。
2. `制作文件/项目记录/项目档案.yaml` 里的 `接手:` 一节 + `takeover/original/SHA256`。
3. 一张「改了什么」清单：每一行写「原值 → 新值 → 依据用户哪句话」。
4. 明确说出哪些没动、为什么没动。
