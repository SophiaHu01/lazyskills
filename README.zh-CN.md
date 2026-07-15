[English](README.md) | 简体中文

# lazyskills · 挑战复刻 30 个 AI 产品

我会陆续复刻市面上 AI 产品的核心功能,做成开源 **skill**——装进 **AI 编程助手**
(AI coding assistant,即 Claude Code、Cursor、Windsurf、Codex 这类产品)就能达到
原产品约 **80% 的效果**。免费、全程本地、隐私(不上传任何内容)。
复刻成功=开源送你;复刻失败=拆解它的护城河给你看。

| 期数 | 复刻对象 | skill | 状态 |
|---|---|---|---|
| EP01 | ChatCut(AI 视频剪辑) | [lazycut](lazycut/) | 内测中 |

---

## EP01 · lazycut 详细介绍

### 能做什么

转录你的口播 → 自动挑掉重录和口误 → 按逐字稿剪辑(划掉哪句删哪句)→ 字幕(自然断句+
重点词标黄)→ 静音录屏智能变速 → 动效规划 → 机器质检 → **直出你惯用的剪辑软件的
可编辑工程**——开箱时会问你用哪款:剪映/CapCut 原生分轨草稿(支持最深),
DaVinci Resolve / Premiere / Final Cut 走 EDL/OTIO,其余给万能素材包。
完整能力表与工作原理:[lazycut/README.zh-CN.md](lazycut/README.zh-CN.md)。

### 框架与逻辑

三层结构,规则和工具分家:
- **SKILL.md(指令层)**:AI 读的主线——八步工序、三个硬停点(剪前/渲前/发送前必须
  经你确认)、通道禁令。
- **scripts/(工具层)**:30 个单文件确定性工具。判断交给 AI,执行交给代码。
- **assets/style.json(风格层)+ reference/lessons.local.md(错题本)**:你的口味是数据,
  规则从你的纠正里长出来。

两个核心机制:**转录锁**(只转录一次,锁死为真相源,剪辑靠时间映射推算——治「每转一遍
错字都不同」)和**模板克隆法**(读你本机的真实草稿当格式模板——不逆向、不硬编码,
剪辑软件怎么升级都不怕)。

### 引用的开源库

ffmpeg(视频引擎,必装)· Whisper 经 mlx-whisper/faster-whisper(转录,自动二选一)·
Pillow(字幕绘制,必装)· RapidOCR(非 macOS 的屏幕文字识别)· ClearVoice(人声增强,可选)·
Remotion(动效,可选)· OpenTimelineIO(时间线交换,可选)。
模型首次运行自动下载到本机(约 1-2GB,只下一次),之后离线可用。

### 你可能要安装什么

Python 3.10+、ffmpeg、若干 pip 包、可选 Node.js。**不用自己记**:跑
`python3 lazycut/scripts/doctor.py` 体检,把输出整段贴给你的 AI 编程助手,它会装齐。

### 机器要求

macOS(Apple 芯片最顺)与 Windows 都支持。Windows 尚未真机全链实测——跑通或跑挂
都请开 issue,首批实测者进 README 鸣谢。

---

## 通用玩法

**超级小白?** 看图文教程:[docs/tutorial.zh-CN.md](docs/tutorial.zh-CN.md)。

```bash
git clone https://github.com/SophiaHu01/lazyskills.git
cd lazyskills/lazycut && python3 scripts/doctor.py
```

**Claude Code**:把 `lazycut/` 拷进 `~/.claude/skills/`,对 AI 说「用 lazycut 帮我剪 <素材文件夹>」。
**Cursor / Windsurf / Codex**:仓库自带 `AGENTS.md`,打开项目即生效;或直接说
「读 lazycut/SKILL.md,按它的流程帮我剪视频」。

License: MIT
