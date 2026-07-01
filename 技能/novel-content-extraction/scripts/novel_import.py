#!/usr/bin/env python3
"""
novel_import.py — 小说一键导入 Story Engine
用法: python3 novel_import.py <小说文件.txt> [--output 输出目录] [--top 15]

纯本地运行，无网络依赖，3MB 文件约 1-2 秒。
"""

import os, re, sys, argparse
from collections import Counter

STOP_WORDS = {
    '于是','然后','因此','所以','不过','可是','然而','虽然','但是','突然','忽然',
    '居然','竟然','终于','其实','可能','应该','可以','已经','正在','就要','快要',
    '刚才','现在','这里','那里','什么','怎么','哪里','多少','几个','哪个','哪些',
    '每个','任何','自己','对方','大家','别人','她们','他们','我们','你们','它们',
    '这个','那个','这些','那些','所有','一些','有些','一个','这种','那种',
    '一下','一样','一直','一起','一般','一边','一定','一点','不是','没有','不会',
    '不能','还有','就是','开始','继续','知道','觉得','认为','感到','发现','看到',
    '听到','想到','说道','笑着','看着','说着','闻言','此时','此刻','顿时','随即',
    '旋即','而后','听着','想着','望着','盯着','来到','回到','走进','走出','不知',
    '继续','然后','妈的','他妈','我去','我靠','我草','干嘛','咋了','得了','算了',
    '行了','完了','好了','够了','真的','假的','好吧','哈哈','嘿嘿','我去','天啊',
}

LOCATION_KEYWORDS = [
    '医院','学校','公司','集团','酒店','餐厅','商场','超市','公园','小区','公寓',
    '别墅','教室','办公室','会议室','大厅','走廊','卧室','客厅','厨房','卫生间',
    '厕所','阳台','天台','地下室','酒吧','KTV','健身房','游泳池','图书馆','网吧',
    '电影院','宿舍','操场','食堂','礼堂','体育馆','花园','庭院','停车场','诊所',
    '药店','银行','大厦','广场','中心','基地',
]


def read_file(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def split_chapters(text):
    pattern = re.compile(r'^\s*(第[一二三四五六七八九十百千零\d]+章.*|序章.*|前言.*|引言.*)', re.MULTILINE)
    markers = list(pattern.finditer(text))
    if not markers:
        return [("全文", text)]
    chapters = []
    if markers[0].start() > 0:
        prefix = text[:markers[0].start()].strip()
        if prefix:
            chapters.append(("前缀", prefix))
    for i, m in enumerate(markers):
        start = m.start()
        end = markers[i+1].start() if i+1 < len(markers) else len(text)
        chapters.append((m.group(0).strip(), text[start:end]))
    return chapters


def normalize_chapter_num(title):
    cn_map = {}
    cn_list = ['零','一','二','三','四','五','六','七','八','九','十',
               '十一','十二','十三','十四','十五','十六','十七','十八','十九','二十',
               '二十一','二十二','二十三','二十四','二十五','二十六','二十七','二十八','二十九','三十',
               '三十一','三十二','三十三','三十四','三十五','三十六','三十七','三十八','三十九','四十',
               '四十一','四十二','四十三','四十四','四十五','四十六','四十七','四十八','四十九','五十',
               '五十一','五十二','五十三','五十四','五十五','五十六','五十七','五十八','五十九','六十',
               '六十一','六十二','六十三','六十四','六十五','六十六','六十七','六十八','六十九','七十']
    for i, cn in enumerate(cn_list):
        if i > 0: cn_map[cn] = i
    m = re.match(r'第(\d+)章', title)
    if m: return int(m.group(1))
    m = re.match(r'第(.+?)章', title)
    if m and m.group(1) in cn_map: return cn_map[m.group(1)]
    if '引言' in title: return 0
    return -1


def extract_locations(text):
    locs = Counter()
    for kw in LOCATION_KEYWORDS:
        for m in re.finditer(r'([\u4e00-\u9fff]{1,6}' + re.escape(kw) + r')', text):
            loc = m.group(1)
            if len(loc) > len(kw):
                locs[loc] += 1
    return locs


def extract_character_names(text, chapters):
    """
    两步法提取人名：
    1. 从 'XX说/道/问/笑/怒...' 模式提取候选（跳过中间的副词）
    2. 验证候选名在全文中独立出现 >= 3次
    """
    candidates = Counter()
    pat = re.compile(r'([\u4e00-\u9fff]{2,3})(?:[又也就都才却也还再更最很太]*)[说道喊问答笑怒骂喝叫叹哭]')
    for _, content in chapters:
        for m in pat.finditer(content):
            name = m.group(1)
            candidates[name] += 1

    BLACKLIST = {
        '不是','没有','不会','不能','不知','不想','不敢','不要','不过','不如',
        '什么','怎么','哪里','多少','几个','哪个','她们','他们','我们','你们',
        '自己','对方','大家','别人','这个','那个','这些','那些','所有','一个',
        '一边','一点','一样','一下','一直','一起','一般','突然','忽然','居然',
        '竟然','终于','其实','可能','应该','可以','已经','正在','就要','快要',
        '于是','然后','因此','所以','可是','然而','虽然','但是','刚才','现在',
        '真的','假的','好吧','继续','说道','笑着','看着','说着','此时','此刻',
        '妈的','他妈','我去','我靠','我草','继续','知道','觉得','认为','感到',
        '还有','就是','不会','只是','还是','但是','真是','就是','那是','这是',
        '听到','看到','想到','发现','来到','走进','走出','回到','闻言','顿时',
        '随即','望着','盯着','想着','听着','忽然','突然','自然','果然','虽然',
        '既然','依然','竟然','当然','不然','否则','或者','或许','也许','大概',
        '毕竟','反正','不管','无论','也好','罢了','而已','甚至','何况','况且',
        '一边','反而','反倒','居然','固然','尽量','尽管','即使','既然','哪怕',
        '只好','只得','不得不','不止','不料','不觉','不胜','不免','何不','何尝',
        '何妨','何况','何止','不必','不曾','不得','不可','不堪','不当',
        '不但','不仅','不论','不管','不拘','不料','不消','不过','不然','不独',
        '与会','与其','两个','之中','之间','之所以','事关','二话','什么',
        '从不','从来','以前','以外','以后','以内','任凭','任何','似的','但是',
        '但凡','作为','何以','何况','何止','何尝','你们','俺们','咱们','人们',
        '什么','不仅','不久','不比','不屑','不经','不觉','不问','不料','不过',
        '且说','且慢','与其','两个','也罢','也好','也许','了解','人们','什么',
        '以后','以来','以外','以前','以及','以外','任凭','任何','似的','但是',
        '一边','已经','不觉','不禁','不由','不仅','不知','不错','不过','不问',
        '不得了','说不定','说不得','差不多','恨不得','不见得','了不得','怪不得',
        '不由得','不得不','不像话','不好意思',
        '心里','眼中','眼里','面前','身后','身边','旁边','眼前','头上','背后',
        '嘴里','怀中','手中','脚下','门外','屋内','屋外','车内','车外',
        '忍不住','不由得','不知不觉','莫名其妙','毫不犹豫',
        '妈妈','爸爸','哥哥','姐姐','弟弟','妹妹','叔叔','阿姨','爷爷','奶奶',
        '老师','师父','老板','经理','总裁','主任','院长','校长','部长','市长',
    }

    valid = {}
    for name, cnt in candidates.most_common(100):
        if name in BLACKLIST or name in STOP_WORDS:
            continue
        if len(name) < 2 or len(name) > 3:
            continue
        if not re.match(r'^[\u4e00-\u9fff]+$', name):
            continue
        if name[0] in '说叫喊问笑哭怒骂听看走跑来去吃喝睡站坐躺趴跪让给被把将从到那这我你他她':
            continue
        if name[-1] in '说道知觉感得着了过的地得来去上下进出回起又也就都才却也还再更最很太':
            continue
        standalone = len(re.findall(
            r'(?:^|[，。！？\s""「\n])' + re.escape(name) + r'(?:[，。！？\s""」\n的了在和与被把将从到])',
            text
        ))
        if standalone >= 3:
            valid[name] = cnt
    return valid


def merge_name_variants(names_with_counts):
    sorted_names = sorted(names_with_counts.items(), key=lambda x: -len(x[0]))
    merged = {}
    used = set()
    for name, cnt in sorted_names:
        if name in used:
            continue
        merged[name] = cnt
        for other_name, other_cnt in sorted_names:
            if other_name != name and other_name in name and other_name not in used:
                merged[name] += other_cnt
                used.add(other_name)
    return merged


def extract_dialogue_for_name(name, chapters, max_n=3):
    dialogues = []
    pat = re.compile(
        re.escape(name) +
        r'(?:说|道|喊|问道|答道|笑道|怒道|冷笑道|叹道|冷道|哭道|叫道|骂道|喝道)'
        r'(?:道|着|到|说)?[""「]([^""」]{4,80})[""」]'
    )
    for _, content in chapters:
        for m in pat.finditer(content):
            d = m.group(1).strip()
            if d and d not in dialogues:
                dialogues.append(d)
            if len(dialogues) >= max_n:
                return dialogues
    if not dialogues:
        pat2 = re.compile(re.escape(name) + r'[^。\n]{0,30}[""「]([^""」]{4,60})[""」]')
        for _, content in chapters:
            for m in pat2.finditer(content):
                d = m.group(1).strip()
                if d and d not in dialogues:
                    dialogues.append(d)
                if len(dialogues) >= max_n:
                    return dialogues
    return dialogues[:max_n]


def main():
    parser = argparse.ArgumentParser(description='小说一键导入 Story Engine')
    parser.add_argument('input', help='小说文件路径 (.txt)')
    parser.add_argument('--output', '-o', default='./提取数据', help='输出目录')
    parser.add_argument('--top', '-n', type=int, default=15, help='输出角色数量')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 文件不存在 {args.input}")
        sys.exit(1)

    print(f"[1/5] 读取: {os.path.basename(args.input)}")
    text = read_file(args.input)
    print(f"      {len(text)} 字符")

    print(f"[2/5] 切分章节...")
    chapters = split_chapters(text)
    print(f"      {len(chapters)} 章")

    print(f"[3/5] 提取角色...")
    raw_names = extract_character_names(text, chapters)
    merged = merge_name_variants(raw_names)
    top_chars = sorted(merged.items(), key=lambda x: -x[1])[:args.top]
    top_names = [name for name, _ in top_chars]
    print(f"      {len(top_names)} 个角色: {', '.join(top_names[:8])}")

    print(f"[4/5] 全文分析...")
    char_counts = {n: text.count(n) for n in top_names if text.count(n) > 0}
    system_kws = ['积分','任务','职业','系统','商城','道具','药剂','属性','等级',
                   '技能','天赋','面板','好感度','亲密度','掌控者','玩家','堕落','认主','调教']
    system_counts = {kw: text.count(kw) for kw in system_kws if text.count(kw) > 0}
    all_locations = extract_locations(text)

    last_20 = chapters[-20:] if len(chapters) >= 20 else chapters
    last_text = "\n".join(c for _, c in last_20)
    late_names = {n: last_text.count(n) for n in top_names if last_text.count(n) > 0}
    late_locs = extract_locations(last_text)

    print(f"[5/5] 生成输出...")
    os.makedirs(args.output, exist_ok=True)

    lines = ["# 角色库\n"]
    lines.append(f"按提及次数排序，共 {len(top_names)} 个主要角色。\n\n---\n")
    for name in top_names:
        cnt = char_counts.get(name, 0)
        late = late_names.get(name, 0)
        first_ch = '?'
        last_ch = '?'
        for title, content in chapters:
            num = normalize_chapter_num(title)
            if name in content:
                if first_ch == '?': first_ch = num
                last_ch = num
        dialogues = extract_dialogue_for_name(name, chapters[-30:], 3)
        lines.append(f"# {name}\n")
        lines.append(f"提及: {cnt}次 | 首现: 第{first_ch}章 | 后期: {late}次\n")
        if dialogues:
            lines.append("对话:\n")
            for d in dialogues:
                lines.append(f'- "{d}"\n')
        lines.append("\n---\n")
    with open(os.path.join(args.output, '角色.md'), 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    wlines = ["# 世界背景\n"]
    if system_counts:
        wlines.append("## 系统/设定关键词\n")
        for kw, cnt in sorted(system_counts.items(), key=lambda x: -x[1]):
            wlines.append(f"- {kw}: {cnt}次")
        wlines.append("")
    if all_locations:
        wlines.append("## 地点\n")
        for loc, cnt in all_locations.most_common(15):
            wlines.append(f"- {loc}: {cnt}次")
    with open(os.path.join(args.output, '世界背景.md'), 'w', encoding='utf-8') as f:
        f.write("\n".join(wlines))

    slines = ["# 剧情状态\n"]
    slines.append(f"- 总章节: {len(chapters)}")
    slines.append(f"- 最后章节: {chapters[-1][0]}\n")
    slines.append("## 角色活跃度（最后20章）\n")
    for name, cnt in sorted(late_names.items(), key=lambda x: -x[1])[:10]:
        slines.append(f"- {name}: {cnt}次")
    slines.append("")
    if late_locs:
        slines.append("## 后期地点\n")
        for loc, cnt in late_locs.most_common(10):
            slines.append(f"- {loc}: {cnt}次")
        slines.append("")
    slines.append("## 最后20章标题\n")
    for title, _ in last_20:
        slines.append(f"- {title}")
    with open(os.path.join(args.output, '剧情状态.md'), 'w', encoding='utf-8') as f:
        f.write("\n".join(slines))

    with open(os.path.join(args.output, '章节索引.md'), 'w', encoding='utf-8') as f:
        f.write("# 章节索引\n\n")
        for title, _ in chapters:
            f.write(f"- {title}\n")

    print(f"\n完成! {args.output}/")
    for fn in sorted(os.listdir(args.output)):
        sz = os.path.getsize(os.path.join(args.output, fn))
        print(f"  {fn} ({sz/1024:.1f}KB)")


if __name__ == '__main__':
    main()
