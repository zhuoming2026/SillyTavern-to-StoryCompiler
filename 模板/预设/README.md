# 预设目录

> 每个预设是一个**独立可复用**的 `扮演者-[名]-规则.md` 文件。
> Characters-to-world 构建新故事时注入 AGENTS.md。

## 预设列表

| 文件名 | 来源 | 覆盖 |
|:-------|:-----|:-----|
| `扮演者-TGbreak-规则.md` | TGbreak V3.0.8 | 身份（保持默认）+ 搞笑网文风格 + 地道中文纠错 |
| `扮演者-双人成行-规则.md` | 双人成行 v10.0 | 身份（Atri & Deach 双生写手） |

## 文件结构

每个预设文件包含四个固定段落：

```
# 扮演者预设：[名称]

## 身份覆盖      → 注入 AGENTS.md #0 {{IDENTITY_PRESET}}
## 文风规则      → 注入 AGENTS.md #4.1 叙事基调
## 语料库追加    → 注入 AGENTS.md #4.3 {{CORPUS_OVERRIDE}}
## 文风纠错追加  → 注入 AGENTS.md #4.4 {{STYLE_FIX_OVERRIDE}}
```

无内容的段落留空标注"（无追加）"。

## 添加新预设

1. 使用 `技能/preset-extractor` 从酒馆 JSON 提取，自动生成
2. 或手动创建符合上述结构的 Markdown 文件
