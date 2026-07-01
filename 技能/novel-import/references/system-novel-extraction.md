# 系统文提取技巧

## 高效发现系统面板的方法

系统文的属性面板通常用特殊缩进格式（如全角空格 `　　　　`），搜索这种格式比正则匹配关键词更精准。

### 搜索代码示例

```python
# 找出所有系统面板块（连续缩进行）
system_panels = []
i = 0
while i < len(lines):
    stripped = lines[i].strip()
    if lines[i].startswith('　　　　') or lines[i].startswith('        '):
        block_lines = []
        while i < len(lines) and (lines[i].startswith('　　　　') or lines[i].startswith('        ') or lines[i].strip() == ''):
            if lines[i].strip():
                block_lines.append(lines[i].strip())
            i += 1
        if len(block_lines) >= 2:
            text = ' | '.join(block_lines)
            if any(kw in text for kw in ['属性', '技能', '等级', '天运', '力量', '敏捷', '体力', '精力']):
                system_panels.append((i - len(block_lines) + 1, text))
    else:
        i += 1
```

### 关键搜索词

- 属性面板：力量/敏捷/体力/精力/专注力/友善度/服从度
- 系统消息：系统等级/属性点/天运值/系统资金/解锁/激活
- 任务系统：任务完成/奖励/触发/发布
- 特殊能力：特性/被动/天赋/血脉

## 女性角色专属属性

很多系统文会给女性角色额外属性：
- 服从度（0-100）
- 奴性（未开发/已开发，主人绑定）
- 善意度/敌意度

这些属性是角色状态的核心指标，必须完整记录。

## 特性/被动能力

系统文的特性往往比基础属性更重要，需要单独列表：
- 特性名
- 获得方式（哪个任务/什么条件）
- 具体效果（用原文描述）
- 持有者
