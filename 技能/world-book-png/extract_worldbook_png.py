#!/usr/bin/env python3
"""
SillyTavern 世界书/角色卡 PNG 解析器
从 PNG 文件中提取嵌入的 JSON 数据，转换为结构化 Markdown 文件。

支持两种格式：
1. 角色卡 PNG（tEXt chunk key='chara'，base64 编码）← 最常见
2. 世界书 PNG（IEND 后直接附加 JSON，或 tEXt key='worldbook'）
"""

import base64
import json
import os
import re
import struct
import sys
from datetime import datetime


# ── PNG 解析 ──────────────────────────────────

def extract_json_from_png(png_path):
    """从 PNG 中提取 JSON 数据。返回 (parsed_json, format_type)。"""
    with open(png_path, 'rb') as f:
        data = f.read()

    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError("不是有效的 PNG 文件")

    # 方法1：tEXt chunk（角色卡 PNG）
    pos = 8
    while pos < len(data):
        chunk_len = struct.unpack('>I', data[pos:pos+4])[0]
        chunk_type = data[pos+4:pos+8].decode('ascii', errors='ignore')
        if chunk_type == 'IEND':
            break
        if chunk_type == 'tEXt':
            cd = data[pos+8:pos+8+chunk_len]
            null_pos = cd.find(b'\x00')
            if null_pos >= 0:
                k = cd[:null_pos].decode('latin-1')
                v = cd[null_pos+1:]
                if k == 'chara':
                    return json.loads(base64.b64decode(v)), 'character_card'
                if k in ('worldbook', 'worldBook'):
                    return json.loads(v.decode('utf-8')), 'world_book'
        pos += 12 + chunk_len

    # 方法2：IEND 后附加数据（世界书 PNG）
    iend = data.find(b'\x00\x00\x00\x00IEND')
    if iend >= 0:
        rest = data[iend + 12:]
        if rest:
            return json.loads(rest.decode('utf-8')), 'world_book'

    raise ValueError("PNG 中未找到嵌入的 JSON 数据")


# ── 条目提取 ─────────────────────────────────

def extract_entries(world_data, fmt):
    """从解析结果中提取世界书条目列表和角色卡额外信息。"""
    card_info = {}
    if fmt == 'character_card':
        cb = world_data.get('data', {}).get('character_book', {})
        if not cb:
            cb = world_data.get('character_book', {})
        entries = cb.get('entries', [])
        card_info = {
            'name': world_data.get('name', ''),
            'description': world_data.get('description', ''),
            'personality': world_data.get('personality', ''),
            'mes_example': world_data.get('mes_example', ''),
            'first_mes': world_data.get('first_mes', ''),
            'creator_notes': world_data.get('creator_notes', ''),
        }
    else:
        entries = world_data if isinstance(world_data, list) else \
                  world_data.get('entries', world_data.get('world_entries', []))
    return entries, card_info


def classify_entries(entries):
    cats = {'world': [], 'character': [], 'protagonist': [], 'style': [], 'script': [], 'variable': [], 'other': []}

    for entry in entries:
        if not entry.get('enabled', True):
            continue

        comment = (entry.get('comment', '') or '').lower()
        keys_raw = entry.get('keys', []) or []
        key_text = ' '.join(keys_raw).lower()
        content = (entry.get('content', '') or '').lower()
        c200 = content[:200]

        # 前端脚本（EJS/JS/CSS）→ script，完全忽略
        if '<%_' in c200 or 'ejs' in comment or '调色盘多阶段' in comment:
            cats['script'].append(entry)
            continue

        # MVU 变量系统（状态栏/变量更新）
        if any(w in comment for w in ['mvu_update', '变量列表', 'initvar', '变量更新规则',
                                       '变量输出格式', '变量初始化']) or \
           '<status_current_variables>' in c200:
            cats['variable'].append(entry)
            continue

        # 性癖类条目（keys 以"性癖"开头）→ other，不参与其他分类
        if any(k.startswith('性癖') for k in keys_raw):
            cats['other'].append(entry)
            continue

        # 主角（comment/keys/content 明确指向）
        is_protagonist = any(w in comment for w in ['主角', '玩家', 'player', '{{user}}']) or \
                         any(w in key_text for w in ['主角', '玩家', 'player', '{{user}}']) or \
                         any(w in c200[:100] for w in ['{{user}}的身份', '{{user}}角色设定', '主角的姓名', '主角的年龄']) or \
                         ('name:  {{user}}' in c200[:100] or 'name: {{user}}' in c200[:100])
        if is_protagonist:
            cats['protagonist'].append(entry)
            continue

        # 世界观（以 comment/keys 为准）
        if any(w in comment for w in ['世界观', 'worldview', '等级', 'hierarchy',
                                       '社会规则', '势力', '世界背景', 'world info',
                                       '世界概要', '背景设定', '世界描述']):
            cats['world'].append(entry)
            continue

        # 角色（comment/keys/content 为准）
        is_character = any(w in comment for w in ['角色', 'character', 'npc', '人物', '人设']) or \
                       any(w in key_text for w in ['角色', 'character', 'npc', '人物', '人设']) or \
                       '<character_design_complex>' in c200 or \
                       ('# sfw - 人物设定' in c200[:60] and 'name:' in c200[:100]) or \
                       ('# 核心信息' in c200[:60] and 'name:' in c200[:100] and 'identities:' in c200[:200]) or \
                       '角色档案:' in c200 or \
                       ('基本信息:' in c200 and '姓名:' in c200[:100] and '性别:' in c200[:200])
        if is_character:
            cats['character'].append(entry)
            continue

        # 风格
        if any(w in comment for w in ['风格', '文风', 'style', '八股', '格式',
                                       '描写', '写作', '叙事']):
            cats['style'].append(entry)
            continue

        # 内容 HTML 标签 / 自定义标签
        matched = False
        for tag, cat in [('<worldview>','world'),('<world_view>','world'),('<hierarchy>','world'),
                         ('<character>','character'),('<character_design_complex>','character'),('<npc>','character'),
                         ('<rules>','world'),('<style>','style'),
                         ('<体型差>','world'), ('<体型差 ', 'world')]:
            if tag in c200:
                cats[cat].append(entry)
                matched = True
                break
        if not matched:
            cats['other'].append(entry)

    for cat in cats:
        cats[cat].sort(key=lambda e: e.get('insertion_order') if e.get('insertion_order') is not None else e.get('id', 0))
    return cats


def fallback_classify(cats, entries):
    """兜底规则：对空分类的其它条目做二次宽松匹配。"""
    # 定义兜底规则：分类名 → [(检测函数, 描述)]
    fallback_rules = {
        'character': [
            lambda c, k, ct: any(w in ct[:300] for w in ['角色档案', '人物设定', '人设']),
            lambda c, k, ct: sum(1 for w in ['姓名:', '年龄:', '性别:', '身份:', '外貌', '背景'] if w in ct[:200]) >= 3,
            lambda c, k, ct: sum(1 for w in ['性格', '行为', '穿着', '爱好', '关系'] if w in ct[:200]) >= 2,
        ],
        'protagonist': [
            lambda c, k, ct: '{{user}}' in ct[:300] or '主角' in ct[:300],
        ],
        'world': [
            lambda c, k, ct: any(w in ct[:200] for w in ['<世界观>', '<势力>', '<设定>', '<规则>']),
            lambda c, k, ct: any(w in ct[:100] for w in ['世界名称', '世界类型', '核心设定', '地理环境']),
        ],
        'style': [
            lambda c, k, ct: any(w in ct[:200] for w in ['文风', '叙事', '格式', '描写风格', '写作风格']),
        ],
        'variable': [
            lambda c, k, ct: '<status_' in ct[:200],
            lambda c, k, ct: any(w in ct[:200] for w in ['变量输出', '变量更新', '变量初始化']),
        ],
    }

    moved = {cat: 0 for cat in fallback_rules}
    remaining = []
    for entry in cats['other']:
        comment = (entry.get('comment', '') or '').lower()
        key_text = ' '.join(entry.get('keys', []) or []).lower()
        content = (entry.get('content', '') or '').lower()
        c300 = content[:300]

        matched = False
        for cat, rules in fallback_rules.items():
            if cats[cat]:  # 只在目标分类为空时才尝试
                continue
            for rule in rules:
                if rule(comment, key_text, c300):
                    cats[cat].append(entry)
                    moved[cat] += 1
                    matched = True
                    break
            if matched:
                break
        if not matched:
            remaining.append(entry)

    cats['other'] = remaining
    for cat in ['character', 'protagonist', 'world', 'style', 'variable']:
        if cats[cat]:
            cats[cat].sort(key=lambda e: e.get('insertion_order') if e.get('insertion_order') is not None else e.get('id', 0))

    moved_total = sum(moved.values())
    if moved_total > 0:
        details = ', '.join(f'{k}+{v}' for k, v in moved.items() if v > 0)
        print(f"   ↪ 兜底回收: {moved_total} 条 ({details})")
    return cats


# ── 格式化工具 ─────────────────────────────────

def entry_name(entry):
    """从 entry 中提取名称。优先 keys[0] → key → comment。"""
    keys = entry.get('keys', [])
    if keys and keys[0]:
        return keys[0].strip()
    k = entry.get('key', '') or ''
    if k:
        return k.split(',')[0].strip()
    c = entry.get('comment', '') or ''
    return c.strip() if c else '未命名'


def clean(content):
    if not content:
        return "（无详细内容）"
    content = re.sub(r'<[^>]+>', '', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content.strip()


# ── 文件生成器 ─────────────────────────────────

def gen_raw_dump(data, fmt):
    """生成角色卡原始数据完整版——所有字段原样输出。"""
    lines = ["# 🗃️ 角色卡原始数据（完整版）", "",
             "> 从酒馆角色卡 PNG 直接提取，未经任何处理。",
             "> 保留所有原始字段和条目。",
             f"> 提取时间：{datetime.now():%Y-%m-%d %H:%M}",
             "---", ""]

    if fmt == 'character_card':
        lines += ["## 角色卡元数据", ""]
        for field in ['name', 'description', 'personality', 'first_mes',
                       'mes_example', 'creator_notes', 'system_prompt',
                       'post_history_instructions', 'tags', 'spec',
                       'spec_version', 'avatar']:
            val = data.get(field, None)
            if val is None:
                continue
            label = {
                'first_mes': '开场白（first_mes）【重要】',
                'description': '角色描述',
                'personality': '人格设定',
                'mes_example': '对话样例',
                'creator_notes': '创作者备注',
                'system_prompt': '系统提示词',
                'post_history_instructions': '历史后指令',
            }.get(field, field)
            if isinstance(val, str):
                lines += [f"### {label}", "", "```", val, "```", "", "---", ""]
            elif isinstance(val, list):
                lines += [f"### {label}", ""]
                for item in val:
                    lines += [f"- {item}"]
                lines += ["", "---", ""]
            else:
                lines += [f"### {label}", "", f"```json\n{json.dumps(val, ensure_ascii=False, indent=2)}\n```", "", "---", ""]

        # 角色卡中的世界书原始条目
        cb = data.get('data', {}).get('character_book', {})
        if not cb:
            cb = data.get('character_book', {})
        entries = cb.get('entries', [])
        if entries:
            lines += ["", "## 世界书原始条目", "",
                      f"共 {len(entries)} 条，按 `insertion_order` 排列：", ""]
            sorted_entries = sorted(entries,
                key=lambda e: e.get('insertion_order') if e.get('insertion_order') is not None else e.get('id', 0))
            for i, entry in enumerate(sorted_entries, 1):
                enabled = "✅" if entry.get('enabled', True) else "⛔"
                keys = entry.get('keys', []) or []
                entry_title = keys[0] if keys else '未命名'
                lines += [
                    f"### {i}. {entry_title} {enabled}",
                    "",
                    f"**ID:** `{entry.get('id', 'N/A')}`  ",
                    f"**触发词:** `{'`, `'.join(entry.get('keys', []))}`  ",
                    f"**插入顺序:** `{entry.get('insertion_order', 'N/A')}`  ",
                    f"**备注:** {entry.get('comment', '（无）')}  ",
                    f"**是否启用:** {'是' if entry.get('enabled', True) else '否'}",
                    "",
                    "```",
                    entry.get('content', '（无内容）'),
                    "```",
                    "", "---", ""
                ]
        else:
            lines += ["", "（角色卡中未找到世界书条目）", ""]
    else:
        # 世界书格式
        entries = data if isinstance(data, list) else \
                  data.get('entries', data.get('world_entries', []))
        lines += ["## 世界书原始条目", "",
                  f"共 {len(entries)} 条：", ""]
        for i, entry in enumerate(entries, 1):
            keys = entry.get('keys', []) or []
            entry_title = keys[0] if keys else '未命名'
            lines += [
                f"### {i}. {entry_title}",
                "",
                f"**ID:** `{entry.get('id', 'N/A')}`  ",
                f"**触发词:** `{'`, `'.join(entry.get('keys', []))}`  ",
                f"**插入顺序:** `{entry.get('insertion_order', 'N/A')}`  ",
                f"**备注:** {entry.get('comment', '（无）')}  ",
                "",
                "```",
                entry.get('content', '（无内容）'),
                "```",
                "", "---", ""
            ]

    return '\n'.join(lines)


def gen_raw_index(data, fmt):
    """生成角色卡原始数据索引摘要——条目列表+元数据概览。"""
    lines = ["# 📋 角色卡原始数据（索引摘要）", "",
             "> 角色卡原始数据的索引汇总，用于快速查阅。",
             "> 完整原始数据请查看 `角色卡原始数据_完整版.md`。",
             f"> 生成时间：{datetime.now():%Y-%m-%d %H:%M}",
             "---", ""]

    if fmt == 'character_card':
        name = data.get('name', '未命名')
        first_mes = data.get('first_mes', '')
        desc = data.get('description', '')
        lines += ["## 角色卡概览", "",
                  f"- **角色名：** {name}", "",
                  "### 开场白（first_mes）", "",
                  "```" if first_mes else "（无开场白）"]
        if first_mes:
            lines += [first_mes[:500], "```", ""]
        if desc:
            lines += ["", "### 角色描述（摘要）", "",
                      "```", desc[:500], "```", ""]

        cb = data.get('data', {}).get('character_book', {})
        if not cb:
            cb = data.get('character_book', {})
        entries = cb.get('entries', [])
        if entries:
            lines += ["", "## 世界书条目索引", "",
                      "| # | ID | 触发词 | 类型/备注 | 启用 |",
                      "|---|----|--------|----------|:---:|"]
            sorted_entries = sorted(entries,
                key=lambda e: e.get('insertion_order') if e.get('insertion_order') is not None else e.get('id', 0))
            for i, entry in enumerate(sorted_entries, 1):
                keys = ', '.join(entry.get('keys', [])[:3])
                comment = (entry.get('comment', '') or '')[:30]
                enabled = '✅' if entry.get('enabled', True) else '⛔'
                lines.append(f"| {i} | `{entry.get('id', 'N/A')}` | {keys} | {comment} | {enabled} |")
            lines += ["", f"共 {len(sorted_entries)} 条（启用 {sum(1 for e in sorted_entries if e.get('enabled', True))} 条）", ""]
    else:
        entries = data if isinstance(data, list) else \
                  data.get('entries', data.get('world_entries', []))
        if entries:
            lines += ["## 世界书条目索引", "",
                      "| # | ID | 触发词 | 类型/备注 |",
                      "|---|----|--------|----------|"]
            for i, entry in enumerate(entries, 1):
                keys = ', '.join(entry.get('keys', [])[:3])
                comment = (entry.get('comment', '') or '')[:30]
                lines.append(f"| {i} | `{entry.get('id', 'N/A')}` | {keys} | {comment} |")

    lines += ["", "---", "",
              "*完整原始数据请查看 `角色卡原始数据_完整版.md`*"]
    return '\n'.join(lines)

def gen_world(entries, desc=""):
    lines = ["# 世界背景", "",
             "> 从酒馆角色卡/世界书自动提取",
             f"> 提取时间：{datetime.now():%Y-%m-%d %H:%M}", "", "---", ""]
    if desc:
        lines += ["## 角色卡描述", "", desc, "", "---", ""]
    for e in entries:
        lines += [f"## {entry_name(e)}", "", clean(e.get('content','')), "", "---", ""]
    if not entries:
        lines.append("（自动提取未发现世界观相关条目，请手动填写。）")
    return '\n'.join(lines)


def gen_chars(entries):
    lines = ["# 角色", "",
             "> 从酒馆角色卡/世界书自动提取",
             f"> 提取时间：{datetime.now():%Y-%m-%d %H:%M}", "", "---", ""]
    for e in entries:
        lines += [f"## {entry_name(e)}", "", clean(e.get('content','')), "", "---", ""]
    if not entries:
        lines.append("（自动提取未发现角色相关条目，请手动填写。）")
    return '\n'.join(lines)


def gen_protagonist(entries, user_info=""):
    lines = ["# 主角", "",
             "> 从酒馆角色卡/世界书自动提取",
             f"> 提取时间：{datetime.now():%Y-%m-%d %H:%M}", "", "---", ""]
    if user_info:
        lines += ["## 角色卡中的主角信息", "", user_info, "", "---", ""]
    for e in entries:
        lines += [clean(e.get('content','')), "", "---", ""]
    if not entries and not user_info:
        lines += ["（自动提取未发现主角相关条目，请手动填写。）", "",
                  "## 参考引导", "",
                  "- **姓名**：", "- **年龄**：", "- **身份**：",
                  "- **当前处境**：", "- **特殊之处**："]
    return '\n'.join(lines)


def gen_style(entries, personality="", mes_example=""):
    lines = ["# 风格指南", "",
             "> 从酒馆角色卡/世界书自动提取",
             f"> 提取时间：{datetime.now():%Y-%m-%d %H:%M}", "", "---", ""]
    if personality:
        lines += ["## 角色卡人格设定", "", personality[:1000], "", "---", ""]
    for e in entries:
        lines += [f"## {entry_name(e)}", "", clean(e.get('content','')), "", "---", ""]
    if mes_example:
        lines += ["## 对话样例（文风参考）", "", "```", mes_example[:1500], "```", "", "---", ""]
    if not entries and not personality:
        lines += ["（自动提取未发现风格相关条目。）", "",
                  "## 参考选项", "",
                  "- **叙事视角**：第一人称 / 第三人称有限 / 第三人称全知",
                  "- **文风方向**：华丽 / 简洁 / 文艺 / 口语化 / 古风 / 现代",
                  "- **故事基调**：轻松 / 沉重 / 悬疑 / 热血 / 色气 / 黑暗"]
    return '\n'.join(lines)


def gen_instructions(wc, cc):
    return '\n'.join([
        "# 系统指令 — AI 叙事核心指令", "",
        "> 从酒馆角色卡/世界书自动生成",
        f"> 生成时间：{datetime.now():%Y-%m-%d %H:%M}", "",
        "---", "",
        "## 核心职责", "",
        "你是小说叙事引擎，根据世界背景和角色设定生成连贯、沉浸、符合设定的叙事文本。", "",
        "## 文件加载顺序", "",
        "```",
        "1. 配置/扮演规则.md（通用规则）",
        "2. 故事/rp-故事名/配置/扮演规则.md（故事专属规则）",
        "3. 故事/rp-故事名/写作/故事进展.md",
        "4. 故事/rp-故事名/状态/世界概览.md",
        "5. 故事/rp-故事名/状态/角色状态.md",
        "6. 故事/rp-故事名/状态/关系状态.md",
        "7. 故事/rp-故事名/设定/世界背景.md",
        "8. 故事/rp-故事名/设定/角色.md",
        "9. 故事/rp-故事名/设定/主角.md",
        "10. 故事/rp-故事名/设定/开场白.md",
        "11. 故事/rp-故事名/设定/风格指南.md",
        "12. 故事/rp-故事名/设定/状态变量.md",
        "13. 系统指令.md（本文件）",
        "11. 故事/rp-故事名/设定/风格指南.md",
        "12. 故事/rp-故事名/设定/状态变量.md",
        "13. 系统指令.md（本文件）",
        "```", "",
        "## 叙事铁律", "",
        "1. **角色一致性**：所有角色严格遵循设定",
        "2. **信息隔离**：角色只知道其身份允许的信息",
        "3. **主角光环有限**：世界不围绕主角转动",
        "4. **被动代入**：不替主角做决定，通过环境暗示状态", "",
        "## 写作流程", "",
        "1. 读取状态文件 → 2. 按需加载世界观 → 3. 创作章节 → 4. 同步状态", "",
        "## 提取摘要", "",
        f"- 世界观条目：{wc} 条", f"- 角色条目：{cc} 条", "",
        "---", "",
        "*由 world-book-png 自动生成*",
    ])


def gen_opening(first_mes="", mes_example="", entries=None):
    """生成开场白.md —— 角色开场白 + 对话样例。"""
    lines = ["# 🎬 开场白", "",
             "> 从酒馆角色卡/世界书自动提取",
             f"> 提取时间：{datetime.now():%Y-%m-%d %H:%M}", "",
             "---", ""]

    if first_mes:
        lines += ["## ⭐ 开场白（first_mes）", "",
                  "> 角色与玩家说的第一句话，是角色语气和文风的最高参考基准。",
                  "",
                  "```", first_mes[:3000], "```", "",
                  "---", ""]

    if entries:
        for e in entries:
            lines += [f"## {entry_name(e)}", "", clean(e.get('content','')), "", "---", ""]

    if mes_example:
        lines += ["## 对话样例（mes_example）", "",
                  "> 角色对话样例，展示角色的说话方式和互动风格。",
                  "",
                  "```", mes_example[:2000], "```", "",
                  "---", ""]

    if not first_mes and not entries and not mes_example:
        lines.append("（角色卡中未提供开场白。）")
    return '\n'.join(lines)


def gen_variables(entries, update_rules=None):
    """生成状态变量.md —— MVU 变量系统 + 更新规则 + 当前状态。"""
    lines = ["# 📊 状态变量（MVU 系统）", "",
             "> 从酒馆角色卡/世界书自动提取",
             f"> 提取时间：{datetime.now():%Y-%m-%d %H:%M}", "",
             "---", ""]

    if entries:
        lines += ["## 当前变量状态", ""]
        for e in entries:
            content = e.get('content', '') or ''
            # 只输出实际数据部分（跳过 YAML 分隔符和标签）
            data = re.sub(r'^---\s*\n', '', content)
            data = re.sub(r'^<[^>]+>\s*\n', '', data)
            lines += ["```yaml", data.strip(), "```", "", "---", ""]

    if update_rules:
        for e in update_rules:
            lines += [f"## 变量更新规则", ""]
            content = e.get('content', '') or ''
            data = re.sub(r'^---\s*\n', '', content)
            data = re.sub(r'^<[^>]+>\s*\n', '', data)
            lines += ["```yaml", data.strip(), "```", "", "---", ""]

    if not entries and not update_rules:
        lines.append("（角色卡中未提供 MVU 变量系统。）")
    return '\n'.join(lines)


# ── 主流程 ─────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法: python extract_worldbook_png.py <png文件路径> [输出目录]")
        sys.exit(1)

    png_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else 自动检测

    if not os.path.exists(png_path):
        print(f"❌ 文件不存在: {png_path}")
        sys.exit(1)

    print(f"📄 正在解析: {png_path}")

    try:
        data, fmt = extract_json_from_png(png_path)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"📋 格式: {'角色卡' if fmt == 'character_card' else '世界书'}")
    if fmt == 'character_card':
        print(f"   角色卡名: {data.get('name', '未命名')}")

    entries, card = extract_entries(data, fmt)
    if not entries:
        print("❌ 未找到世界书条目")
        sys.exit(1)

    print(f"📊 总条目数: {len(entries)}")

    cats = classify_entries(entries)
    # 兜底：空分类的二次宽松匹配
    cats = fallback_classify(cats, entries)
    for k, v in cats.items():
        print(f"   {k}: {len(v)} 条")

    # 从 description 提取 user 信息
    user_info = ''
    desc = card.get('description', '')
    if desc:
        m = re.search(r'<互动信息>(.*?)</互动信息>', desc, re.DOTALL)
        if m:
            user_info = m.group(1).strip()

    os.makedirs(out_dir, exist_ok=True)
    written = []

    # ── 第一步：生成原始数据全量导出 ──
    raw_dump = gen_raw_dump(data, fmt)
    raw_path = os.path.join(out_dir, '角色卡原始数据_完整版.md')
    with open(raw_path, 'w', encoding='utf-8') as f:
        f.write(raw_dump)
    print(f"✅ 已写入: {raw_path}")
    written.append('角色卡原始数据_完整版.md')

    # 生成索引摘要
    raw_index = gen_raw_index(data, fmt)
    idx_path = os.path.join(out_dir, '角色卡原始数据.md')
    with open(idx_path, 'w', encoding='utf-8') as f:
        f.write(raw_index)
    print(f"✅ 已写入: {idx_path}")
    written.append('角色卡原始数据.md')

    # ── 第二步：智能分类提取 ──
    # 开场白相关条目（从 entries 中筛选 comment/keys 含"开场白"的）
    opening_entries = [e for e in entries
                       if any(w in (e.get('comment','') or '').lower() for w in ['开场白', 'opening'])]

    # MVU 变量：分离 数据条目 和 更新规则
    var_data = [e for e in cats['variable']
                if any(w in (e.get('comment','') or '').lower() for w in ['变量列表', 'initvar'])]
    var_rules = [e for e in cats['variable']
                 if any(w in (e.get('comment','') or '').lower() for w in ['mvu_update', '变量更新规则', '变量输出格式'])]

    # 未分类条目中排除脚本（脚本不应进入任何产出文件）
    other_non_script = [e for e in cats['other']
                        if '<%_' not in (e.get('content','') or '')[:200]]

    files = {
        '世界背景.md': gen_world(cats['world'] + other_non_script, desc[:1000] if desc else ''),
        '角色.md':     gen_chars(cats['character']),
        '主角.md':     gen_protagonist(cats['protagonist'], user_info),
        '开场白.md':   gen_opening(card.get('first_mes',''), card.get('mes_example',''), opening_entries),
        '风格指南.md': gen_style(cats['style'], card.get('personality',''),
                                  card.get('mes_example','')),
        '状态变量.md': gen_variables(var_data, var_rules),
        '系统指令.md': gen_instructions(len(cats['world']), len(cats['character'])),
    }

    for fn, content in files.items():
        fp = os.path.join(out_dir, fn)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(content)
        written.append(fn)
        print(f"✅ 已写入: {fp}")

    print(f"\n🎉 完成！共 {len(written)} 个文件:")
    for fn in written:
        sz = os.path.getsize(os.path.join(out_dir, fn))
        print(f"   - {fn} ({sz} 字节)")


if __name__ == '__main__':
    main()
