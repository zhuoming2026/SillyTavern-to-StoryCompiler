---
name: SillyTavern-Characters-importer
description: "导入SillyTavern角色卡（PNG/JSON），提取原始数据。职责单一：只做步骤1-2。触发词：解析角色卡、导入角色卡"
runAs: subagent
allowed-tools: read_file, write_file, bash
---

# SillyTavern-Characters-importer — 角色卡导入器

## 职责边界

**这个技能只做两件事：**

1. **提取完整 JSON** — 原始数据，零修改
2. **生成世界书概览 + 开场白** — 让用户能进入下一步选择

做完这两步就结束。**不生成设定文件、不做分类、不做风格提取。**

后续步骤（勾选条目→提取风格/变量→生成AGENTS）由 `Characters-to-world` 负责。

---

## 核心理念

**AI 不替用户做判断，也不自作主张往前多走一步。**

---

## 支持的格式

| 格式 | 检测方式 |
|:-----|:---------|
| `.png` | 文件头 tEXt/iTXt/zTXt 块（标准酒馆角色卡/世界书 PNG） |
| `.json` | 文件后缀（SillyTavern V2/V3 格式） |

---

## 工作流

### Step 0：环境检测

每次启动时，执行以下检测确定当前平台能力：

```
尝试 bash -c "echo ok"
  ↓ 成功 → env.shell = bash, env.has_exec = true
  ↓ 失败
确认 → env.shell = unavailable, env.has_exec = false
```

检测结果决定后续执行路径（见下文各步骤的兼容分支）。

---

### Step 0.5：预取角色名 → 创建故事目录

> 不先问用户"故事叫啥名"，直接从角色卡里读出名字，建好目录再干活。

#### 预取角色名

根据输入文件格式，快速提取角色名：

| 格式 | 提取方式 | 兼容性 |
|:-----|:---------|:-------|
| `.png`（bash 可用） | bash → 最小化 Python 脚本，只提取 name 字段 | bash ✅ |
| `.png`（bash 不可用） | 写入最小脚本 → 告知用户执行一次 | 手动 |
| `.json` | 直接 `read_file` 前几 KB，从 JSON 中提取 | 无需 bash |

**角色名提取逻辑（适用于所有格式）：**

```json
// 在 JSON 中按以下优先级找 name:
// 1. data.name（V2 格式）
// 2. name（V1 格式）
// 3. spec.name（特殊格式）
// 4. 都找不到 → 使用文件名（不含扩展名）
```

**PNG 最小化预取脚本**（仅提取 name，不等同完整解析）：
```python
import struct, base64, json, sys
with open(sys.argv[1], 'rb') as f:
    data = f.read()
pos = 8
while pos < len(data):
    length = struct.unpack('>I', data[pos:pos+4])[0]
    ct = data[pos+4:pos+8]
    cd = data[pos+8:pos+8+length]
    pos += 12 + length
    if ct == b'tEXt':
        ni = cd.find(b'\x00')
        if ni >= 0 and cd[:ni].decode('latin-1') == 'chara':
            d = json.loads(base64.b64decode(cd[ni+1:]))
            d2 = d.get('data', d)
            print('NAME:', d2.get('name', d.get('name', d.get('spec', {}).get('name', ''))))
            sys.exit(0)
print('NAME: 未命名角色')
```

**路径兼容创建故事目录：**

```
故事名 = 角色名（去除非法文件字符：\/:*?"<>|）
故事目录 = 故事/rp-{故事名}/
```

创建 `故事/rp-{故事名}/` 及子目录：
- `基础数据/` — 存放原始 PNG/JSON
- `设定/` — 存放提取后的 JSON 和生成文件
- `元数据/` `状态/` `写作/聊天记录` `写作/小说` `写作/规划` `配置/`

#### 用户确认（可选）

如果用户已经说了"故事名叫 XXX"，**跳过此步骤**，直接用用户指定的名字。

如果角色名提取结果和用户预期不符，用户可以在事后说"改名"来修改。

#### 将输入文件复制到故事目录

无论哪种路径，将输入的 PNG/JSON 复制到故事目录：
```
原始文件 → 故事/rp-{故事名}/基础数据/{故事名}.{png|json}
```

Step 1 的输入从此目录读取。

---

### Step 1：提取完整 JSON

#### 路径 A：bash 可用（macOS / Linux / Windows Git Bash）

通过 bash 调用 Python 脚本解析 PNG：

```
输入：基础数据/*.png 或 *.json
    ↓
提取 JSON（bash → python 解析 PNG chunk → base64 解码 → JSON）
    ↓
保存：设定/角色卡原始数据_完整版.md
     设定/角色卡原始数据.json
```

**产出文件：**
- `设定/角色卡原始数据_完整版.md` — 完整 JSON，格式化但零修改
- `设定/角色卡原始数据.json` — JSON 副本

#### 路径 B：bash 不可用，仅文件工具

> ⚠️ **此路径下 PNG 格式角色卡无法自动解析。**
> 技能通过文件工具可处理 `.json` 格式角色卡。

**执行流程：**

1. 检测输入文件格式
   - 如果是 `.json` → 直接读取 JSON → 输出到 `设定/角色卡原始数据.json` → 进入 Step 2
   - 如果是 `.png` → 进入下方 **PNG 手动提取流程**

**PNG 手动提取流程：**

1. 将解析脚本写入 `.reasonix/tmp/extract_chara.py`
2. 告知用户手动执行：
   ```
   python .reasonix/tmp/extract_chara.py "基础数据/角色卡.png" "设定/角色卡原始数据.json"
   ```
3. 用户执行完后，检查文件是否存在，存在则继续 Step 2

**写入的 Python 脚本内容：**
```python
import struct, base64, json, sys, os
with open(sys.argv[1], 'rb') as f:
    data = f.read()
pos = 8
while pos < len(data):
    length = struct.unpack('>I', data[pos:pos+4])[0]
    chunk_type = data[pos+4:pos+8]
    chunk_data = data[pos+8:pos+8+length]
    pos += 12 + length
    if chunk_type == b'tEXt':
        null_idx = chunk_data.find(b'\x00')
        if null_idx >= 0:
            key = chunk_data[:null_idx].decode('latin-1')
            value = chunk_data[null_idx+1:].decode('latin-1')
            if key == 'chara':
                decoded = base64.b64decode(value)
                parsed = json.loads(decoded)
                out_path = sys.argv[2] if len(sys.argv) > 2 else 'output.json'
                with open(out_path, 'w', encoding='utf-8') as fout:
                    json.dump(parsed, fout, ensure_ascii=False, indent=2)
                print(f'OK: {os.path.basename(out_path)}')
                sys.exit(0)
print('ERR: no chara chunk found')
sys.exit(1)
```

---

### Step 2：生成世界书概览 + 开场白

#### 2a. 开场白提取（100%完整）

从 JSON 中提取：
- `first_mes` → 主开场白
- `alternate_greetings` → 备选开场白列表
- `mes_example` → 对话样例

写入 `设定/🎬 开场白.md`，保持原文，不做修改。

**产出文件：**
- `设定/🎬 开场白.md` — 所有开场白原文，零修改

#### 2b. 世界书概览

从 `character_book.entries[]` 生成勾选清单：

```
# 世界书概览

> 共 XX 条世界书条目 | 已启用 XX 条 | 已禁用 XX 条

请勾选你要保留的词条，未勾选的将被排除：

- [x] **#0** 「条目名称」
  - 触发词: `关键词`
  - 摘要: 内容前 80 字...
  - 备注: 分类/说明

- [ ] **#1** ...
```

**规则：**
- 每条 entry 一行
- 启用/禁用用 `[x]` / `[ ]` 标记
- 内容只截取前 80 字，不修改原文
- 不判断"这是什么类型"
- 格式要求：概览与说明之间空行，清单缩进统一

**产出文件：**
- `设定/世界书概览.md` — 勾选清单，用户手动打勾后保存

---

### Step 2 完成后汇报

```
✅ 角色卡导入完成！

📦 设定/角色卡原始数据_完整版.md  ← 完整 JSON
📦 设定/角色卡原始数据.json       ← JSON 副本
📦 设定/🎬 开场白.md              ← X 个开场白
📦 设定/世界书概览.md             ← XX 条世界书条目（待勾选）

下一步：请在 世界书概览.md 中勾选你要保留的词条，然后调用 Characters-to-world 继续。
```

---

## 绝对禁令

- ❌ 禁止对 JSON 做任何识别、分类、修改
- ❌ 禁止生成除上述三个文件外的任何文件
- ❌ 禁止调用 Characters-to-world 或其他技能——只做提取
