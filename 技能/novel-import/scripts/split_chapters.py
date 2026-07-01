"""切分中文小说章节。兼容多种章节标记格式。

用法: python3 split_chapters.py <输入文件> [输出目录]
默认输出目录: ./分析缓存/章节文件/
"""
import re, os, sys

filepath = sys.argv[1] if len(sys.argv) > 1 else "./novel.txt"
outdir = sys.argv[2] if len(sys.argv) > 2 else "./分析缓存/章节文件"
os.makedirs(outdir, exist_ok=True)

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 兼容: 第X章(阿拉伯/中文)、序章、前言、第 X 章(有空格)
chapter_pattern = re.compile(
    r'^\s*(第\s*[一二三四五六七八九十百千零\d]+\s*章|序章|前言)'
)

chapters = []
current_title = None
current_lines = []

for line in lines:
    stripped = line.strip()
    if chapter_pattern.match(stripped):
        if current_title is not None:
            chapters.append((current_title, current_lines))
        current_title = stripped
        current_lines = [line]
    elif current_title is not None:
        current_lines.append(line)
    else:
        current_lines.append(line)  # 序章前的内容

if current_title is not None:
    chapters.append((current_title, current_lines))

# 中文数字映射 (覆盖到70)
cn_map = {}
cn_list = ['零','一','二','三','四','五','六','七','八','九','十',
           '十一','十二','十三','十四','十五','十六','十七','十八','十九','二十',
           '二十一','二十二','二十三','二十四','二十五','二十六','二十七','二十八','二十九','三十',
           '三十一','三十二','三十三','三十四','三十五','三十六','三十七','三十八','三十九','四十',
           '四十一','四十二','四十三','四十四','四十五','四十六','四十七','四十八','四十九','五十',
           '五十一','五十二','五十三','五十四','五十五','五十六','五十七','五十八','五十九','六十',
           '六十一','六十二','六十三','六十四','六十五','六十六','六十七','六十八','六十九','七十']
for i, cn in enumerate(cn_list):
    if i > 0:
        cn_map[cn] = i

def normalize_title(title):
    title = title.strip()
    # 去掉空格: "第 171 章" -> "第171章"
    title = re.sub(r'第\s+', '第', title)
    title = re.sub(r'\s+章', '章', title)
    # 阿拉伯数字补零
    m = re.match(r'第(\d+)章(.*)', title)
    if m:
        return f"第{int(m.group(1)):03d}章{m.group(2)}"
    # 中文数字转阿拉伯
    m = re.match(r'第(.+?)章(.*)', title)
    if m:
        cn = m.group(1)
        rest = m.group(2)
        if cn in cn_map:
            return f"第{cn_map[cn]:03d}章{rest}"
    return title

index_lines = []
for title, content in chapters:
    norm = normalize_title(title)
    safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '', norm)
    if not safe_name:
        safe_name = f"misc"
    filename = f"{safe_name}.txt"
    filepath_out = os.path.join(outdir, filename)
    with open(filepath_out, "w", encoding="utf-8") as f:
        f.writelines(content)
    index_lines.append(f"{norm}|{filename}|{len(content)} lines")

with open(os.path.join(outdir, "_index.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(index_lines))

print(f"Split into {len(chapters)} chapters -> {outdir}/")
