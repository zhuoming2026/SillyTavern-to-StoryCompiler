import { registerMvuSchema } from 'https://testingcf.jsdelivr.net/gh/StageDog/tavern_resource/dist/util/mvu_zod.js';

// 定义通用的玩家/其他角色结构
const CharacterSchema = z.object({
  当前地点和动作: z.string().optional().prefault(''),
  当前衣物: z.record(z.string(), z.any()).optional().prefault({}),
  内心想法: z.string().optional().prefault(''),
  身体: z.string().optional().prefault(''),
}).passthrough(); // 允许包含其他未定义的字段

export const Schema = z.object({
  世界: z.object({
    当前时间: z.string(),
    天数: z.coerce.number().transform(v => _.clamp(v, 1, 9999)),
    剧情进度: z.string(),
  }),

  // 李慕雪定义
  李慕雪: z.object({
    当前地点和动作: z.string(),
    当前衣物: z.record(
      z.enum(['上身', '下身', '内衣', '内裤', '袜子', '鞋子']),
      z.string().or(z.literal('待初始化')).prefault('待初始化')
    ),
    内心想法: z.string(),
    身体: z.string(),

    // 基础数值
    好感度: z.coerce.number().transform(v => _.clamp(v, 0, 100)),
    堕落值: z.coerce.number().transform(v => _.clamp(v, 0, 100)),
    爱情值: z.coerce.number().transform(v => _.clamp(v, 0, 100)),

    // 每日增量
    好感度今日增量: z.coerce.number().transform(v => _.clamp(v, 0, 2)),
    好感度更新日期: z.coerce.number(),
    堕落值今日增量: z.coerce.number().transform(v => _.clamp(v, 0, 2)),
    堕落值更新日期: z.coerce.number(),
    爱情值今日降低: z.coerce.number().transform(v => _.clamp(v, 0, 3)),
    爱情值更新日期: z.coerce.number(),
  }).transform((data) => {
    // ⚠️ 注意：这里只进行不依赖外部变量的计算
    // 依赖"世界.天数"的重置逻辑移到根transform

    // 计算阶段
    const 好感度阶段 = Math.floor(data.好感度 / 5);
    const 堕落值阶段 = Math.floor(data.堕落值 / 5);

    // 计算下一阶段提示
    const 下一阶段好感度 = (好感度阶段 + 1) * 5;
    const 好感度下一阶段提示 = data.好感度 >= 100 ? "已满" : `需要${下一阶段好感度 - data.好感度}点 (${下一阶段好感度}点)`;

    // 计算爱情下一变化
    let 爱情下一变化 = "";
    if (data.爱情值 >= 95) 爱情下一变化 = "降至95点";
    else if (data.爱情值 >= 80) 爱情下一变化 = "降至80点";
    else if (data.爱情值 >= 60) 爱情下一变化 = "降至60点";
    else if (data.爱情值 >= 30) 爱情下一变化 = "降至30点";
    else 爱情下一变化 = "已到最低";

    // 态度映射
    const 好感态度映射 = {
      0: "礼貌接纳", 1: "初步关注", 2: "生活融入", 3: "情感交流",
      4: "特殊地位", 5: "自然亲近", 6: "情感寄托", 7: "界限松动",
      8: "依赖加深", 9: "情感动摇", 10: "心理认同", 11: "主动靠近",
      12: "亲密无间", 13: "优先选择", 14: "深度眷恋", 15: "情感觉醒",
      16: "内心挣扎", 17: "嫉妒心起", 18: "情感爆发", 19: "爱意难掩",
      20: "至死不渝"
    };

    const 堕落态度映射 = {
      0: "纯洁无暇", 1: "无意诱惑", 2: "身体觉醒", 3: "暧昧接触",
      4: "欲望苏醒", 5: "主动试探", 6: "情欲煎熬", 7: "理智崩塌",
      8: "肉体接触", 9: "口舌服侍", 10: "初次结合", 11: "日常性爱",
      12: "大胆偷情", 13: "完全淫荡", 14: "性爱奴隶", 15: "公开偷情",
      16: "受孕欲望", 17: "性爱狂热", 18: "彻底沦陷", 19: "背德极致",
      20: "完全堕落"
    };

    // 计算爱情态度
    let 爱情态度 = "";
    if (data.爱情值 >= 95) 爱情态度 = "贤妻良母";
    else if (data.爱情值 >= 80) 爱情态度 = "轻微不满";
    else if (data.爱情值 >= 60) 爱情态度 = "情感疏离";
    else if (data.爱情值 >= 30) 爱情态度 = "形同陌路";
    else 爱情态度 = "彻底决裂";

    return {
      ...data,
      好感度阶段,
      好感态度: 好感态度映射[Math.min(好感度阶段, 20)] || "未知",
      好感度下一阶段提示,
      堕落值阶段,
      堕落态度: 堕落态度映射[Math.min(堕落值阶段, 20)] || "未知",
      爱情态度,
      爱情下一变化
    };
  }),

  // 沈煜定义
  沈煜: z.object({
    当前地点和动作: z.string(),
    内心想法: z.string(),
    怀疑值: z.coerce.number().transform(v => _.clamp(v, 0, 100)),
  }).transform((data) => {
    // 这里的计算不依赖外部变量
    let 危险等级图标 = "";
    let 当前状态 = "";
    let 危险线提示 = "";

    if (data.怀疑值 >= 80) {
      危险等级图标 = "🔴极度危险";
      当前状态 = "玉石俱焚";
    } else if (data.怀疑值 >= 50) {
      危险等级图标 = "🟠高度警戒";
      当前状态 = "威胁警告";
    } else if (data.怀疑值 >= 20) {
      危险等级图标 = "🟡初步警告";
      当前状态 = "试探性询问";
    } else {
      危险等级图标 = "🟢安全";
      当前状态 = "毫无察觉";
    }

    if (data.怀疑值 < 20) 危险线提示 = `危险线: 距离下一阶段还有${20 - data.怀疑值}点容错`;
    else if (data.怀疑值 < 50) 危险线提示 = `危险线: 距离下一阶段还有${50 - data.怀疑值}点容错`;
    else if (data.怀疑值 < 80) 危险线提示 = `危险线: 距离下一阶段还有${80 - data.怀疑值}点容错`;
    else 危险线提示 = "已到最高危险等级";

    return { ...data, 危险等级图标, 当前状态, 危险线提示 };
  }),

  // 梁语嫣定义
  梁语嫣: z.object({
    当前地点和动作: z.string(),
    当前衣物: z.record(
      z.enum(['上身', '下身', '内衣', '内裤', '袜子', '鞋子']),
      z.string().or(z.literal('待初始化')).prefault('待初始化')
    ),
    内心想法: z.string(),
    身体: z.string(),
    性欲值: z.coerce.number().transform(v => _.clamp(v, 0, 100)),
    性欲值今日增量: z.coerce.number().transform(v => _.clamp(v, 0, 2)),
    性欲值更新日期: z.coerce.number(),
  }).transform((data) => {
    // 依赖"世界.天数"的重置逻辑移到根transform
    const 性欲阶段 = Math.floor(data.性欲值 / 5);
    const 下一阶段性欲值 = (性欲阶段 + 1) * 5;
    const 性欲下一阶段提示 = data.性欲值 >= 100 ? "已满" : `需要${下一阶段性欲值 - data.性欲值}点 (${下一阶段性欲值}点)`;

    const 欲望状态映射 = {
      0: "禁欲状态", 1: "本能苏醒", 2: "春潮暗涌", 3: "欲望觉醒",
      4: "自慰初体验", 5: "目光游移", 6: "衣着诱惑", 7: "无意勾引",
      8: "肌肤之亲", 9: "言语暗示", 10: "自慰成瘾", 11: "情趣玩具",
      12: "主动出击", 13: "诱惑升级", 14: "母子暧昧", 15: "道德沦丧",
      16: "淫母本性", 17: "主动献身", 18: "母狗觉醒", 19: "公开淫乱",
      20: "彻底沦陷"
    };

    return {
      ...data,
      欲望状态: 欲望状态映射[Math.min(性欲阶段, 20)] || "未知",
      性欲阶段,
      性欲下一阶段提示
    };
  }),

})
// 使用 catchall 捕获玩家（未知键名）
.catchall(CharacterSchema)
// ⚠️ 根级别 transform：处理跨变量逻辑（日期同步）
.transform((rootData) => {
  const currentDay = rootData.世界?.天数 || 1;

  // 处理李慕雪的日期重置
  if (rootData.李慕雪) {
    if (rootData.李慕雪.好感度更新日期 !== currentDay) {
      rootData.李慕雪.好感度今日增量 = 0;
      // 注意：这里只是修改输出数据，不回写数据库，回写需靠指令
    }
    if (rootData.李慕雪.堕落值更新日期 !== currentDay) {
      rootData.李慕雪.堕落值今日增量 = 0;
    }
    if (rootData.李慕雪.爱情值更新日期 !== currentDay) {
      rootData.李慕雪.爱情值今日降低 = 0;
    }
  }

  // 处理梁语嫣的日期重置
  if (rootData.梁语嫣) {
    if (rootData.梁语嫣.性欲值更新日期 !== currentDay) {
      rootData.梁语嫣.性欲值今日增量 = 0;
    }
  }

  return rootData;
});

$(() => {
  registerMvuSchema(Schema);
});