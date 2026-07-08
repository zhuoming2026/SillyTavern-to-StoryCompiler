---
name: statusbar-validator
description: "校验并修复状态栏.html中的JS语法错误和酒馆API残留。触发词：校验状态栏、修复状态栏、检查状态栏"
runAs: subagent
allowed-tools: read_file, write_file, bash, grep, glob
---

# statusbar-validator — 状态栏 HTML 校验修复器

## 职责边界

**对任意已生成的 `状态/状态栏.html` 进行 JS 语法校验和自动修复。**

定位：独立于 Characters-to-world，可单独对任何状态栏文件运行。
输入：`状态/状态栏.html` 文件路径。
输出：校验通过的 HTML 文件（如有修复，标注修改内容）。

---

## 校验清单（9 项）

```markdown
□ 1. 花括号 {} 是否配对（打开/关闭数量一致）
□ 2. 圆括号 () 是否配对（特别是 function 调用和 innerHTML 赋值）
□ 3. 无残留酒馆 API（getAllVariables、waitGlobalInitialized、eventOn、Mvu.、TavernHelper）
□ 4. 无残留 jQuery $() 调用（应全部替换为 document.querySelector/getElementById）
□ 5. 无残留 .html() 调用（应全部替换为 .innerHTML =）
□ 6. 无孤立的 ); 残留（原 `$('#xxx').html(...)` 替换后多余的闭合括号）
□ 7. `<script src="stat_data.js"></script>` 引用是否存在
□ 8. statData 变量是否采用 `var` 声明（而非 const，确保模块脚本可访问）
□ 9. DOM 操作在 `DOMContentLoaded` 事件后进行
```

---

## 执行流程

### Step 1：读取文件

读取用户指定的 `状态/状态栏.html` 文件。

### Step 2：逐项校验

逐项检查 9 项清单，记录问题：

```
[校验报告]
✅ 1. 花括号: 57 {, 57 } — 平衡
⚠️ 3. 酒馆API残留: getAllVariables() 在 L184
✅ 4. jQuery: 无残留
❌ 6. 孤立 );: 2 处 (L217, L234)
...
```

### Step 3：逐一修复

对每项发现的问题进行修复：

| 问题 | 修复方法 |
|:-----|:---------|
| 残留 `getAllVariables()` | 替换为 `statData` |
| 残留 `waitGlobalInitialized('Mvu')` | 删除整行（含 await） |
| 残留 `eventOn(Mvu.events.xxx, ...)` | 替换为 `document.addEventListener('DOMContentLoaded', ...)` |
| 残留 `Mvu.events.*` | 删除 |
| 残留 `TavernHelper.*` | 替换为 `statData` |
| 残留 `$('#xxx')` | 替换为 `document.getElementById('xxx')` |
| 残留 `$('.xxx')` | 替换为 `document.querySelector('.xxx')` |
| 残留 `.html(` | 替换为 `.innerHTML = ` |
| 孤立的 `);`（非函数调用） | 替换为 `;` |
| 缺少 `<script src="stat_data.js">` | 在第一个 `<script>` 前插入 |
| `const statData` | 改为 `var statData` |
| `$(errorCatched(fn))` | 替换为 `document.addEventListener('DOMContentLoaded', fn)` |
| 缺少 `DOMContentLoaded` | 将 populate/init 调用包在事件监听中 |

### Step 4：二次校验

修复后重新校验，确认 9 项全部通过。

### Step 5：输出报告

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 状态栏校验报告

文件: 状态/状态栏.html
结果: ✅ 全部通过

修复内容:
  - L184: getAllVariables() → statData
  - L217: 移除孤立 );
  - L234: 移除孤立 );

校验清单:
  ✅ 1. 花括号配对
  ✅ 2. 圆括号配对
  ✅ 3. 无酒馆 API 残留
  ✅ 4. 无 jQuery 残留
  ✅ 5. 无 .html() 残留
  ✅ 6. 无孤立 );
  ✅ 7. 有 stat_data.js 引用
  ✅ 8. statData 用 var 声明
  ✅ 9. DOM 操作在 DOMContentLoaded 后

⚠️ 注意：校验只检查 JS 语法正确性，不保证视觉效果与原始设计一致。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 使用示例

```
用户: "校验状态栏 故事/rp-拯救母猪/状态/状态栏.html"
→ 执行上述流程，返回校验报告

用户: "修复状态栏 故事/rp-女奴训练师/状态/状态栏.html"
→ 校验→修复→二次校验→输出报告
```
