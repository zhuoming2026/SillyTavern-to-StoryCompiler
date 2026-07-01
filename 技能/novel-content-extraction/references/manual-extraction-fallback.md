# Manual Extraction Fallback (no script)

When `novel_import.py` is unavailable or the user asks for ad-hoc analysis (e.g. "解析这本小说"), use this workflow instead of requiring the script.

## macOS Pitfall: grep -P not available

macOS built-in `grep` does NOT support `-P` (PCRE). You will get `grep: invalid option -- P`.

Alternatives:
- Use `grep -E` for extended regex (ERE)
- Use Python (`re` module) for complex patterns
- Use `python3 -c` one-liners for inline text processing

## Step-by-Step Manual Workflow

### 1. File overview
```bash
wc -c -m -l "novel.txt"   # bytes, chars, lines
```

### 2. Read metadata (title, author, tags, synopsis)
Usually the first 10-20 lines. Use `read_file(limit=20)`.

### 3. Read ending
Use `read_file(offset=<near_end>, limit=60)` to see where the story ends up.

### 4. Extract chapter markers
```bash
grep -E '^第[0-9]+章' "novel.txt"
```
Note: Some novels use `第N章` without `^` anchor (indented content). Try without anchor if count is 0.

### 5. Character frequency analysis
```python
# First pass: guess names from context (read a few chapters)
# Then count known names:
names = ['张三', '李四', '王五']
for n in names:
    c = text.count(n)
    if c > 0:
        print(f'  {n}: {c}')
```

### 6. Per-chapter word count
```python
import re
ch_positions = []
for m in re.finditer(r'^第(\d+)章.*', text, re.MULTILINE):
    ch_positions.append((int(m.group(1)), m.start(), m.group(0).strip()))

for i, (num, pos, title) in enumerate(ch_positions):
    end = ch_positions[i+1][1] if i+1 < len(ch_positions) else len(text)
    ch_text = text[pos:end]
    chars = len(re.sub(r'\s', '', ch_text))
    print(f'第{num}章  {chars}字  {title}')
```

### 7. Faction/story-arc analysis
```python
# Count faction-related mentions per chapter range
tianlian = len(re.findall(r'天莲|柳若莲|柳清雪', text))
xuannv = len(re.findall(r'玄女|洛玄冰|洛清婉', text))
```

### 8. Total Chinese character count
```python
clean = re.sub(r'[\s\W]', '', text)
print(f'总中文字符: {len(clean)}')
```

## Output Format (Chinese terminal style)

User profile: prefers Chinese, no markdown, concise terminal output. Structure the report as:

```
========================================
  《书名》
  作 者：XXX
========================================
【基本信息】  (chars, lines, chapters, avg per chapter)
【世界观设定】(world, power system, key rules)
【主要人物】  (grouped by faction, with mention counts)
【故事线分析】(chapter ranges, faction dominance)
【小说特点】  (narrative style, unique features)
========================================
```
