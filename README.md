# lazyskills · 挑战复刻 30 个 AI 产品

每期视频复刻一个 AI 产品——不是做它的克隆,而是**开源一个 skill**,
让你的 AI 编程助手达到该产品 70-80% 的效果。免费、本地、隐私(不上传任何内容),
产出直接进你惯用的剪辑软件。

| 期数 | 复刻对象 | skill | 状态 |
|---|---|---|---|
| EP01 | ChatCut(AI 剪辑) | [lazycut](lazycut/) | 内测中 |

## 安装(三步)

```bash
git clone https://github.com/SophiaHu01/lazyskills.git
cd lazyskills/lazycut && python3 scripts/doctor.py   # 体检:缺什么贴给你的AI让它装
```

**Claude Code**:把 `lazycut/` 拷进 `~/.claude/skills/`,对 AI 说「用 lazycut 剪 <素材文件夹>」。
**Cursor / Windsurf / Codex 等**:仓库自带 `AGENTS.md`,在项目里打开即生效;
或直接对你的 AI 说:「读 lazycut/SKILL.md,按它的流程帮我剪视频」。
skill 本体就是 markdown 规则+python 脚本,任何能读文件、能跑命令的 AI 助手都能用。

## 机器要求

macOS(Apple 芯片最顺)与 Windows 都支持:转录双引擎(mlx-whisper/faster-whisper 自动选)、
OCR 双引擎(macOS Vision/RapidOCR)、中文字体自动探测(苹果丽黑/微软雅黑/Noto)。
Windows 尚未真机全链实测——你是 Windows 用户?跑通或跑挂都请开 issue,首批实测者会进 README 鸣谢。

License: MIT
