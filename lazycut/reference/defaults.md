# 调好的默认参数(真实项目磨出来的,别乱动)

## 剪辑(cut.py)
- `speed = 1.0` —— **不提速**(创作者嫌快)。想快靠删静音,别靠加速。
- `keep_sent = 0.26` —— 句子/话题前留的话口(创作者要连贯但别封死)。
- `keep_mid = 0.11` —— 句内小停顿收到这么紧。
- `silence_db = -30`,d=0.12 —— 静音检测阈值。
- 结尾静音尾自动砍;`end_keep` 让创作者指定停在哪句。
- 合并阈值 0.10s —— 治切口碎片(whisper 会在碎片上脑补「那/就是」连接词)。

## 字幕(build.py)
- 整句为先:按 whisper 句段,>22 字才在**词缝**拆两屏,**绝不拆英文词/命令**。
- 字号:正文 64,结尾卡区 42(小)。每行 ≤11 字(小号 ≤16)。白字 + 6px 黑边。
- 位置:正文底部(VH-270-H);结尾卡那几秒缩小移到最底(VH-85-H)。
- **字幕永远最上层**(overlay 先叠、字幕后叠),否则会被结尾卡挡。
- 滤掉 <0.35s 的碎字幕 + 结尾幻觉「呀/啊」。
- 纠错:base(`corrections.json`)+ config.corrections。**whisper 切口脑补的连接词从字幕清掉即可**(音频没有)。

## overlay(build.py)
- 面板:切品牌卡橙栏头那块,860 宽,顶部 y46,讲到关键词时冒出 hold 6s。
- 命令 badge:白卡 + 命令药丸(MCP 橙 / 命令黑)+「怎么开」(核实!见 command-howto.md),中部 y1030,hold 2.6s。
- 结尾卡:整卡 720 宽,顶部 y60,压暗背景,end-7 到 end,当「截图收藏屏」。

## 音频(enhance_audio.py)
- 默认 `ai`(ClearVoice MossFormer2_SE_48K,播客级)。**别用 afftdn/deesser 重降噪 → 发闷**。
- 备选 `loud`(只 loudnorm -14 最保真)/ `bright`(loudnorm+presence EQ+treble 提亮)。
- 目标响度 -14 LUFS(社媒标准);原声常偏轻(-30)。

## 环境(首次装)
- ClearVoice:`uv venv --python 3.13 <skill目录>/venv_cv && uv pip install --python <skill目录>/venv_cv/bin/python clearvoice`(resemble-enhance 锁死老 torch 装不上,用这个)。
- 首次跑 MossFormer2 会下模型权重(~几秒)。
