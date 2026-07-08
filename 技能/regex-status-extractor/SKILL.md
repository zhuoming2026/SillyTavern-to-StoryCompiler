---
name: regex-status-extractor
description: "从角色卡JSON提取正则状态栏和变量系统。触发词：提取状态栏、检测正则、提取MVU"
runAs: subagent
allowed-tools: read_file, write_file, bash, grep, glob
---

# regex-status-extractor — 正则状态栏提取器

> 不关心是不是 MVU。只关心有没有正则替换、有没有变量追踪。
> 输出放到故事的 `状态/` 目录。

---

## Step 1: Detect — 扫描角色卡

读取 `设定/角色卡原始数据.json`，扫描两类东西：

### 1a. 正则状态栏（`extensions.regex_scripts[]`）

遍历所有正则脚本，按 `findRegex` 分类：

| findRegex 特征 | 类型 | 说明 |
|:---------------|:-----|:-----|
| `<StatusPlaceHolderImpl/>` | MVU 状态栏 | 最常见 |
| `<status>` 或 `</status>` | 自定义状态标签 | 其他状态栏 |
| 包含完整 HTML template | 直接 HTML 替换 | 无标签，直接替换 |

输出检测报告：

```
[状态栏检测]
- 正则脚本总数: 7
- 含 StatusPlaceHolderImpl: 2 个
  · "状态栏" — 渲染版（30KB HTML）
  · "对AI隐藏状态栏" — promptOnly
- 含其他 HTML 模板: 1 个
- 其他正则（非状态栏）: 4 个
```

### 1b. 变量系统（`extensions.tavern_helper`）

检查是否有变量引擎（注意 dict 和数组对两种格式）：

| 特征 | 含义 |
|:-----|:-----|
| `MagVarUpdate` + `bundle.js` | MVU 引擎 |
| `registerMvuSchema` | Zod Schema 定义 |
| 两者皆有 | 完整 MVU |
| 皆无 | 无变量追踪 |

### 1c. 初始变量（`character_book.entries[]` + `first_mes`）

| 来源 | 检测 |
|:-----|:-----|
| 世界书条目 `comment` 含 `[initvar]` | initvar 数据 |
| `first_mes` / `alternate_greetings` 含 `<UpdateVariable>` | 开场白内嵌变量 |

---

## Step 2: Extract — 原样提取，不做转换

将检测到的原始数据复制到 `状态/` 目录，**不做任何修改**：

| 文件 | 条件 | 内容 |
|:-----|:-----|:-----|
| `状态/mvu/engine.js` | 检测到 MVU 引擎 | 原始脚本内容 |
| `状态/mvu/schema.js` | 检测到 Zod Schema | 原始 Schema 代码 |
| `状态/mvu/statusbar_raw.html` | 检测到状态栏 | 原始 HTML（反引号块提取） |
| `状态/mvu/initvar.json` | 检测到 initvar | 解析后的 JSON5 数据 |

> ⚠️ 此步骤只复制，不转换、不脱酒馆化。

---

## Step 3: Export — 生成结构化数据

### 3a. 生成 `状态/stat_data.js`

基于 initvar + Schema，生成 JavaScript 数据文件：

```javascript
// 由 regex-status-extractor 自动生成
// 更新方式: #更新状态
var statData = {
  // ... 从 initvar 提取的变量结构
};
```

**无 initvar 时的策略：**
- 有 Schema 无 initvar → 从 Schema prefault 生成默认值
- 有 initvar 无 Schema → 从 initvar 结构推断类型
- 都没有 → 不生成此文件，标注"无变量系统"

### 3b. 生成 `状态/状态数据.md`

与 stat_data.js 等价的 Markdown 表格。

### 3c. 生成 `状态/变量规则.md`（★ 有 Schema 时必须生成）

读取 Zod Schema 代码，提取以下规则写成 AI 可读的 Markdown：

**提取内容：**
- `_.clamp(v, min, max)` → 基础值范围
- `.transform()` → 派生计算逻辑（阶段/态度映射）
- 每日增量上限（`今日增量` 的 clamp）
- 跨天重置逻辑（`更新日期 !== 当前天数 → 今日增量 = 0`）

**格式：**

```markdown
# 变量更新规则

> AI 修改 stat_data.js 时遵守以下约束。
> 派生值（阶段/态度）不直接修改——改基础值后自动推算。

## 基础值范围
| 变量 | 范围 | 单日上限 |
|:-----|:-----|:---------|
| 好感度 | 0~100 | +2/天 |
| ...

## 派生值（阶段→态度映射表）
### 好感度
| 阶段 | 范围 | 态度 |
|:-----|:-----|:-----|
| 0 | 0~4 | 礼貌接纳 |
| ...

## 跨天重置
- 更新日期 ≠ 当前天数 → 今日增量 = 0
```

> 此文件在 `#更新状态` 时供 AI 参考。

### 3b. 生成 `状态/状态数据.md`

与 stat_data.js 等价的 Markdown 表格。

---

## Step 4: HTML（可选，默认跳过）

> 只做检测，不做转换。用户单独调用 `statusbar-validator` 做转换。

展示选项：

```markdown
[状态栏处理]

检测到状态栏 "天下风云录"（中国风水墨风格，30KB）

处理方式：
  A. 跳过 — 先不生成 HTML（90% 的卡选这个就够了）
  B. AI 重绘 — 基于变量结构重新生成一个干净的状态栏
  C. 保留原版 — 提取原始 HTML 到 状态/状态栏.html（需要后续脱酒馆化）
```

---

## Step 5: 输出报告

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 状态栏提取报告

[正则状态栏]
- 状态栏: ✅ 天下风云录（中国风水墨）
- 隐藏层: 1 个（promptOnly）

[变量系统]
- MVU 引擎: ✅ (MagVarUpdate)
- Zod Schema: ✅ (复杂度: 中)
- initvar: ✅ (世界书 + 5 个开场白)

[生成文件]
- 状态/mvu/engine.js
- 状态/mvu/schema.js
- 状态/mvu/initvar.json
- 状态/stat_data.js
- 状态/状态数据.md

[状态栏 HTML]
⏸ 跳过（用户选择 A）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
