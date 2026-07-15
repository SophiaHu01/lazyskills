# Agent 指南(Cursor / Codex / Windsurf 等通用入口)

你是被要求帮用户剪视频的 AI 助手。本仓库的 `lazycut/SKILL.md` 是完整的工作流程与规则,
把它当作你的剪辑技能书:先读它,再按其中的主线八步执行;工具在 `lazycut/scripts/`
(每个文件头有用法),用户风格在 `lazycut/assets/style.json`,错题本机制见 SKILL.md
「习惯学习」一节——用户纠正你时,把判例写进 `lazycut/reference/lessons.local.md`。

硬规矩:产物只落本地+对话内报告,禁用任何用户未明示的外发通道(见 SKILL.md 通道禁令);任何外发先问用户。

首次使用:先跑 `python3 lazycut/scripts/doctor.py` 体检,再做六问风格问卷。
