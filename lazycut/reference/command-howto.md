# 命令 badge 的「怎么开」(已核实官方文档 2026-07)

> ⚠️ 教学视频里教「怎么开」**必须准确**。做新视频若涉及新命令/新功能,**先派 claude-code-guide agent 查官方文档核实**,别凭记忆写。以下为示例条目,做自己的视频时逐条重新核实。

| 功能 | badge how 文案 | 说明 |
|---|---|---|
| MCP | `终端运行 claude mcp add` | CLI 用 `claude mcp add --transport [类型] [名] [URL]`;会话内 `/mcp` 管理。Claude Desktop 才是设置里 Connectors(别混) |
| /goal | `直接输入 /goal 交目标` | 真内置命令,输入 `/goal [完成条件]`,自动循环到满足 |
| auto mode | `Shift + Tab 切权限模式` | Shift+Tab 在权限模式间循环(default/acceptEdits/plan/auto/dontAsk/bypass) |
| /schedule | `直接输入 /schedule 建任务` | 真内置命令,建 routines(云端定时/触发) |
| remote-control | `输入 /remote-control 启用` | 会话内 `/remote-control` 或 `/rc`;CLI `claude remote-control`;手机 app/浏览器连 session |

来源:code.claude.com/docs 的 permission-modes / goal / routines / remote-control / mcp。
