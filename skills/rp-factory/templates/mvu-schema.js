// 变量结构 · MVU 的 zod schema
// 由 制作文件/产物/axis-system.yaml 投影生成。改数值先改轴，再回来改这里；两份不一致时以轴为准。
// 交付：本文件原文一份 + 用 templates/tavern-script.json 包一层塞进卡的 tavern_helper.scripts。
//
// 三条不许省的写法：
//   1) 数值一律 .catch(初值)：只写 z.coerce.number() 时，模型写个「很高」会先产出 NaN，
//      在 transform 之前就抛错，整条更新（这一楼的全部改动）被拒。
//   2) 夹取用 transform + _.clamp，不用 .min/.max（后者会拒绝越界值而不是夹住）。
//   3) 对象键用 .prefault({})，不用 .default({})：default 不给已存在对象的缺失键补值。

import { registerMvuSchema } from 'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js';

// 刻度(初值, 上界)：下界恒为 0；有负值的轴自己写 _.clamp(v, lo, hi)
const 刻度 = (初值, 上界) =>
  z.coerce.number().catch(初值).transform(v => _.clamp(v, 0, 上界)).prefault(初值);

// 一个 target 的数值：键名 = axis-system.yaml 里的轴名，逐字照抄
const 单人数值 = z.object({
  好感度: 刻度(20, 100),
  堕落度: 刻度(0, 100),
}).prefault({});

const Schema = z.object({
  世界: z.object({
    日期: z.string().catch('第 1 日'),
    时段: z.enum(['清晨', '上午', '午后', '傍晚', '夜', '深夜']).catch('傍晚'),
    地点: z.string().catch('未知'),
  }).prefault({}),

  主角: z.object({
    姓名: z.string().catch('旅人'),
    位置: z.string().catch('未知'),
  }).prefault({}),

  // 群像：每个角色一份；键名逐字等于人物设定里的 character.name
  角色: z.object({
    角色甲: 单人数值,   // ← 换成人物设定里的 character.name，逐字
    角色乙: 单人数值,   // ← 同上；人数 = cast 阶段的角色数
  }).prefault({}),

  // 可选：不要背包就整段删掉
  背包: z.record(z.string(), z.coerce.number().catch(1).transform(v => _.clamp(v, 0, 99))).prefault({}),
});

$(() => {
  registerMvuSchema(Schema);
});
