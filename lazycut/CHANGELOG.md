# Changelog

## [未发布]
- feat: 动效分段渲染(逐事件独立透明片段+版本号+manifest),用户可在剪辑器单独调;整条渲已废
- feat: 草稿字幕默认缩放 0.6(style.json caption.draft_scale),治模板克隆继承大字号
- rule: 开场动画叠脸不替脸(motion-rules)
- fix: 草稿画布跟素材实际宽高走(此前照抄模板,横屏素材必错)——狗粮实测抓出
- fix: 字幕断行上限按横竖屏自适应(13/22),style.json 可覆盖
- fix: audience_read 兼容 .srt(与流水线落盘格式打通)
- feat: 三个硬停点写进红线区(剪前逐字稿确认/渲前动效脚本确认/发送前去向确认)
- feat: 动效画布尺寸随 props(横屏视频可用)
- 从私人生产流水线去私有化:风格抽入 style.json,人称与路径通用化,个人纠错清除
- 新增 doctor.py 装前体检(mac/Windows)
- 已知欠账:faster-whisper/RapidOCR 备胎接线、Windows 草稿路径实测、新工具金标准、样例素材包
