// 变量结构 · 白潮
// 由 创作痕迹/产物/axis-system.yaml 投影生成（wick 0–100 初值 68 / tide 0–100 初值 22）。
// 交付时同时给两份：本文件原文 + templates/tavern-script.json 包一层塞进卡的 tavern_helper.scripts。

import { registerMvuSchema } from 'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js';

// 刻度(初值, 上界)：非数字与越界都接住——.catch 挡 NaN，clamp 挡越界，prefault 挡缺字段
const 刻度 = (初值, 上界) =>
  z.coerce.number().catch(初值).transform(v => _.clamp(v, 0, 上界)).prefault(初值);

const 单人数值 = z.object({
  wick: 刻度(68, 100),   // 灯芯：100 记忆完整 ↔ 0 忘尽，只降不升
  tide: 刻度(22, 100),   // 潮压：0 静潮 ↔ 100 漫潮
}).prefault({});

const Schema = z.object({
  世界: z.object({
    日期: z.string().catch('潮历四十七年 · 第三次涨潮'),
    时段: z.enum(['晨', '昼', '暮', '夜']).catch('夜'),
    地点: z.string().catch('第七塔'),
  }).prefault({}),

  主角: z.object({
    姓名: z.string().catch('旅人'),
    位置: z.string().catch('第七塔 · 塔基'),
  }).prefault({}),

  角色: z.object({
    祁昭: 单人数值,
  }).prefault({}),
});

$(() => {
  registerMvuSchema(Schema);
});
