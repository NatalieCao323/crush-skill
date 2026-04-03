# crush.skill

> "前任.skill 说：我会为了你一万次回到那个夏天。 但 crush.skill 想问：那个夏天，ta 到底有没有爱过你？"

![License MIT](https://img.shields.io/badge/License-MIT-blue.svg) ![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg) ![Claude Code](https://img.shields.io/badge/Claude-Code-orange.svg) ![AgentSkills Standard](https://img.shields.io/badge/AgentSkills-Standard-purple.svg)

*Inspired by [ex-skill](https://github.com/therealXiaomanChu/ex-skill)*

[安装](#安装) · [使用](#使用) · [示例](#使用案例) · [详细安装说明](INSTALL.md) · [English](README_EN.md)

---

你们还没在一起。
但你已经开始想 ta 发消息前要不要先想好说什么。
你记得 ta 说"改天吧"的语气，和说"要是你在就好了"时的语气，完全不一样。
你不确定 ta 是不是也在想你。
你只是想知道，这段暧昧，到底值不值得继续。

**把聊天记录喂给 AI，不是为了追到 ta，是为了看清楚。**

提供聊天记录（微信、iMessage、短信）、截图、社交媒体，加上你的主观描述
生成一个像 ta 一样说话的 AI crush
用贝叶斯概率分析 ta 的真实意图
诊断 ta 的依恋类型，给出下次聊天的逐字话术

---

## 它能做什么

**体检报告**：把聊天记录喂进去，AI 逐句打贝叶斯标签，输出升温指数、依恋类型诊断、心理环境分析、破局建议和逐字话术。

**演习模式**：AI 完全模仿对方的语气、回复节奏、常用表达，让你在实战前先彩排，避免踩雷。

**记忆引擎**：每条记忆都有三个贝叶斯标签——先验置信度、时间衰减系数、情绪关联强度。AI 像人脑一样，有选择性地记忆和遗忘。

**截图分析**：上传聊天截图，AI 自动识别文字内容，提取消息并进行贝叶斯分析，无需手动导出。

**主观描述**：用自己的语言描述 ta 的性格、口头禅、行为模式，AI 将其融入人格模型，补充聊天记录无法捕捉的细节。

---

## 贝叶斯记忆引擎

每条聊天记录会被自动打上三个标签：

| 标签 | 含义 | 示例 |
|---|---|---|
| **先验置信度 P(H)** | 这句话是否反映 ta 的核心态度 | "我不想谈恋爱" → 0.9；"改天吧" → 0.2 |
| **时间衰减系数 λ** | 这条记忆随时间的消退速度 | 深夜走心长谈 → 低衰减；日常打卡 → 高衰减 |
| **情绪关联强度 E** | 情绪权重 | 吃醋/调情 → +0.8；冷暴力/回避 → -0.8 |

动态激活权重：**W_t = P(H) × e^(-λΔt) × (1 + |E|)**

| 权重区间 | 解读 |
|---|---|
| W_t > 1.0 | 有戏，乘胜追击 |
| W_t 0.5–1.0 | 信号模糊，继续观察 |
| W_t < 0.5 | 别自我感动了 |

---

## 安装

### Claude Code

```bash
# 全局安装（推荐）
git clone https://github.com/NatalieCao323/crush-skill ~/.claude/skills/crush
cd ~/.claude/skills/crush && pip install -r requirements.txt

# 启动
claude
```

启动后输入 `/create-crush` 开始。

### OpenClaw

**方法 A：通过 ClawHub 安装（推荐）**

```bash
openclaw skills install crush
```

安装后重启 OpenClaw，在 Skills 面板中找到 crush.skill 并启用。

**方法 B：手动安装**

```bash
git clone https://github.com/NatalieCao323/crush-skill ~/.openclaw/skills/crush
pip install -r ~/.openclaw/skills/crush/requirements.txt
```

然后在 `~/.openclaw/openclaw.json` 中添加：

```json
{
  "skills": {
    "load": {
      "extraDirs": ["~/.openclaw/skills"]
    }
  }
}
```

重启 OpenClaw 后，在 Skills 面板中启用 crush.skill。

> **OpenClaw 注意事项**：
> - 需要 `python3` 在 PATH 中。Skill 在加载时会自动检测，未检测到则不加载。
> - macOS 用户可以在 Skills UI 中点击一键安装 `Pillow` 和 `piexif` 依赖。
> - 沙箱模式下，需要在容器内也安装 `python3`。可在 `agents.defaults.sandbox.docker.setupCommand` 中配置。
> - OpenClaw 中使用 `{baseDir}` 引用 Skill 目录（Claude Code 中使用 `${CLAUDE_SKILL_DIR}`）。

---

## 使用

### 创建 crush 档案

```
/create-crush
```

AI 会问你三个问题，然后引导你上传聊天记录。支持的格式：

| 平台 | 导出方式 | 格式 |
|---|---|---|
| 微信（Windows） | [WeChatMsg](https://github.com/LC044/WeChatMsg) | TXT / HTML |
| 微信（macOS） | 手动复制粘贴 | 纯文本 |
| QQ | QQ 内置导出功能 | TXT |
| 手动 | 直接粘贴到对话框 | 纯文本 |

最简单的格式（直接粘贴）：
```
小明: 要是你在就好了
我: 我也想你啊
小明: 哦，随便问问哈哈
```

### 命令列表

| 命令 | 说明 |
|---|---|
| `/create-crush` | 创建新的 crush 档案 |
| `/{slug}` | 演习模式：AI 模仿 ta 的语气和你聊天 |
| `/{slug}-report` | 军师模式：完整体检报告 + 破局建议 |
| `/list-crushes` | 列出所有档案 |
| `/update-crush {slug}` | 上传新聊天记录，更新档案 |
| `/versions {slug}` | 查看版本历史 |
| `/rollback {slug} {id}` | 回滚到之前的版本 |
| `/delete-crush {slug}` | 删除档案 |
| `/wake-up {slug}` | 清醒了，删除档案 |

---

## 使用案例

### 案例一：海王学长的贝叶斯体检

**背景**：聊了两个月，频繁互动但从不约出来见面。上传微信聊天记录（TXT 格式，共 847 条）。

**体检报告**：

```
贝叶斯升温指数：3.2 / 10

依恋类型：回避型（置信度 82%）
证据：三次约饭邀请均以"最近太忙"婉拒，但同日深夜主动发起聊天。

心理环境：
  主要：Options Maximizer（享受情绪价值，无进展意图）
  次要：Pursuit-Withdrawal Loop（用户主导追求，对方周期性回应维持关系）

风险预警：
  追求-退缩循环已持续 4 轮。继续追求将强化现有动态。

破局建议 1：
  行动：停止主动联系 10 天。
  理由：用户是追求方，对方在成本收益计算中处于高位。撤退重置计算。
  话术：不发任何消息。如果对方主动联系，简短回复，不问问题，先结束对话。

破局建议 2：
  行动：下次 ta 说"改天"，把主动权还给 ta。
  话术："好啊，你定时间，我看看有没有空。"然后不再追问。
```

**演习模式**：

```
你：睡了吗？
学长（AI）：还没，你呢
你：刚洗完澡
学长（AI）：哦
（AI 精准模拟了 ta 的低回应风格，帮你意识到这个对话模式的问题）
```

---

### 案例二：创伤防御型

**背景**：走心聊了很久，但一提"我们算什么"就消失三天。

**体检报告**：

```
贝叶斯升温指数：5.8 / 10

依恋类型：恐惧-回避型（置信度 79%）
证据：主动分享个人脆弱经历（高激活权重 1.42），但在用户表达明确好感后，
回复延迟从 10 分钟增加到 4 小时。

心理环境：
  主要：Post-Trauma Withdrawal（亲密触发防御机制）
  次要：Genuine Ambivalence（真实的不确定性，非策略性回避）

破局建议：
  行动：停止问"我们算什么"，改变沟通框架。
  话术："我不需要你现在给我答案。我只是想让你知道，我不会让你再经历那种事。"
  然后换话题，不要等待回应。
```

---

### 案例三：双向试探，临门一脚

**背景**：互相吃醋，高频互动，但缺乏临门一脚。

**体检报告**：

```
贝叶斯升温指数：7.1 / 10

依恋类型：安全型（置信度 71%）
证据：情绪表达直接，无明显回避行为，对用户的关心有明确的正向回应。

心理环境：
  主要：Mutual Approach-Avoidance（双方都在等对方先开口）

破局建议：
  行动：直球。
  话术："我发现我挺喜欢你的。你呢？"
  理由：对方是安全型，能坦诚回应。继续模糊只会消耗双方。
```

---

### 案例四：三次"改天"的贝叶斯判定

**背景**：对方第三次说"改天"。

```
三次"改天"的贝叶斯累积权重：W_t = 0.08

这不是忙，这是选择。

一个真的想见你的人，会在说"改天"的同时给你一个具体的时间。

建议：停止主动邀约，观察 ta 是否会主动提出见面。
如果 30 天内没有，你有了答案。
```

---

### 案例五：照片时间线分析

**背景**：对方发了很多照片，想分析 ta 的活动规律。

```
Photos analyzed: 23
Date range: 2024-01-15 to 2024-03-20

Timeline:
  2024-01-15  GPS: 上海静安区某咖啡馆  [周一 14:32]
  2024-02-03  GPS: 北京朝阳区某健身房  [周六 09:15]
  2024-03-01  GPS: 上海浦东某餐厅      [周五 19:44]

Pattern: 工作日白天在上海，周末偶尔在北京。健身习惯稳定（周六早晨）。
```

---

## 文件结构

```
crush.skill/
  SKILL.md              Skill 入口文件（Claude Code + OpenClaw）
  README.md             本文档（中文）
  README_EN.md          英文文档
  INSTALL.md            详细安装指南
  requirements.txt      Python 依赖
  LICENSE               MIT 协议
  prompts/
    intake.md           信息录入脚本（3 问引导）
    memory_builder.md   贝叶斯记忆文档构建模板
    memory_analyzer.md  记忆模式分析
    persona_builder.md  5 层人格构建模板
    persona_analyzer.md 依恋类型 + 10 类心理环境诊断
    bayesian_analysis.md 贝叶斯标签分析指令
    merger.md           合并生成最终 SKILL.md
    correction_handler.md 用户纠错 + 进化模式
  tools/
    wechat_parser.py    微信聊天记录解析（TXT / HTML / JSON）
    qq_parser.py        QQ 聊天记录解析
    social_parser.py    社交媒体文本解析
    photo_analyzer.py   照片 EXIF + GPS 时间线分析
    bayesian_tagger.py  贝叶斯标签引擎
    skill_writer.py     Skill 文件管理
    version_manager.py  版本快照 + 回滚
```

---

## 数据隐私

所有数据在本地处理。聊天记录、照片和个人信息不会上传到任何外部服务器。生成的 Skill 文件完全存储在你的设备上。

本项目仅用于个人情感分析和对话练习，不得用于骚扰、跟踪或侵犯他人隐私。

---

## 致谢

Inspired by [ex-skill](https://github.com/therealXiaomanChu/ex-skill) by therealXiaomanChu.

---

MIT License
