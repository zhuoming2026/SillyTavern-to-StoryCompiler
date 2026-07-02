---
name: novel-content-extraction
description: "快速扫描中文小说，提取角色/世界观/剧情状态等结构化数据。纯脚本执行，不调用LLM，秒出结果。触发词：小说内容提取、提取小说、扫描小说、小说分析"
runAs: subagent
allowed-tools: read_file, bash, grep
---

# Novel Content Extraction — 小说内容提取器

从中文小说中提取角色、世界观、剧情状态，输出结构化 Story Engine 数据。

## 核心工具

脚本路径：小说文件所在目录下的 `novel_import.py`

```bash
python3 novel_import.py 小说.txt           # 默认输出到 ./提取数据/
python3 novel_import.py 小说.txt -o out    # 自定义输出目录
python3 novel_import.py 小说.txt -n 20     # 提取前20个角色
```

输出文件：
- `角色.md` — 按提及次数排序，含首现/后期章节、对话示例
- `世界背景.md` — 系统关键词 + 地点频率
- `剧情状态.md` — 后期角色活跃度 + 地点 + 最后20章标题
- `章节索引.md` — 全部章节标题

## 脚本位置

脚本已包含在本技能目录下的 `scripts/novel_import.py`，直接使用即可。

## 工作流

1. 确认小说文件存在
2. 运行 `python3 novel_import.py <file> --output <dir>`
3. 检查输出质量（角色列表是否干净）
4. 如需更深度分析（世界观/伏笔/导演笔记），用输出文件作为上下文，结合 LLM 补充

## 何时用脚本 vs 何时用 LLM

- **脚本**：快速扫描、角色统计、章节切分、关键词频率（1-2秒）
- **LLM**：深度世界观分析、角色性格推断、伏笔识别、剧情状态推理（需要阅读内容）
- **组合**：先脚本提取骨架 → 再 LLM 补充血肉
- **手动 fallback**：脚本不可用时，用 terminal + execute_code 手动提取，详见 `references/manual-extraction-fallback.md`

## macOS 注意

macOS 的 `grep` 不支持 `-P`（PCRE），用 `grep -E` 或 Python `re` 模块代替。详见 fallback 文档。

## 中文人名提取的坑

详见 `references/chinese-name-extraction.md`

## 注意事项

- 脚本纯本地运行，无网络依赖
- 不续写小说、不总结章节、不评价作品
- 大文件（>1MB）脚本秒出结果，不会超时
