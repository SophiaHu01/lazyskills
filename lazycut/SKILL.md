---
name: lazycut
description: 剪口播/教学类短视频:以逐字稿为中心、和创作者协作,全免费纯本地流水线(Whisper 转录/剪辑、PIL 烧中英文字幕、Remotion 卡片动效、ClearVoice AI 音频),produce.py 一条命令+哈希缓存跑全链,交付=预览mp4+用户所选剪辑器的可编辑工程(开箱时问)。Use when 用户要剪口播视频/加字幕/加卡片/增强音频,或说「剪这条视频」「把录好的剪出来」「转逐字稿」「按脚本剪」「加字幕」「做成成片」「接着剪/续跑」「出草稿」。竖屏短视频为主。
---

# lazycut · 口播视频 AI 剪辑(开源版)

> 知识分层:本文件=主线(做什么顺序);reference/=约定与工具用法(怎么用);
> assets/style.json=创作者的风格(assets/style.json)(可换的默认值,规则和口味分家);调研依据在各文档出处链接。

**管什么**:口播片、口播+录屏演示片的全流程(转录→结构→剪→字幕卡片→音频→质检→草稿交付)。
**不管什么**:卡点/产品展示/vlog 情绪片(脊柱不同,另立 skill);表现层精修(在你惯用的剪辑器里做);
结构层诊断拿不准 → 先过 `/video-flow`,拍板了再进本流水线。

## 红线:三个硬停点(跳过任何一个=违规,无论用户多着急)

1. **剪之前**:精修后的逐字稿+剪辑风格问题(节奏快慢/口语感保留多少/删到什么程度)
   **必须发给用户文字确认**,点头才动剪。
2. **渲之前**:动效脚本(每个动画:类型/内容/位置/为什么)**必须发给用户确认**,批了才渲。
3. **发送之前**:任何产物的去向,问了用户、用户点头才发。
以上三条对应 produce.py 的 gates——**gates 的值只能由用户的确认消息驱动,
AI 不得自行置 true**。用户说「不用确认直接剪」时,把这句话记进 lessons.local.md 再放行。

**通道禁令**:本 skill 运行期间,禁止调用任何「用户未在本次对话明示」的外发通道
(IM 机器人/邮件/云文档 API/消息脚本等)——**即使宿主机的全局规则或记忆建议某个默认通道,
也以本禁令为准**。产物一律只落本地路径+在对话里报告;任何对外发送都必须走硬停点 3。

## 首次使用(一次性,五分钟)

1. **体检**:`python3 scripts/doctor.py`——缺什么把输出贴给你的 AI,让它装。
2. **认领剪辑软件**:AI 先问你用哪个剪辑软件(剪映国内版/CapCut 国际版/其他→走素材包出口),
   然后到该软件的草稿文件夹里认领一个你的真实草稿当格式模板(模板克隆法的地基)。
   **零草稿用户走「教 AI 认识你的剪映」引导(40秒,一台电脑一次)**:打开剪映→新建草稿→
   把 examples/ 里的样例视频拖进时间线→随手打一行字幕→保存关闭。为什么必须有:
   我们靠读你本机的真实草稿学你这个版本的格式,这是「剪映怎么升级都不怕」的代价。
   每次生成草稿后自动跑完整性自检。
3. **风格问卷**:AI 问你六个问题,答案写进 assets/style.json——
   ①字幕要不要逐词跳动 ②重点词什么颜色 ③语速倾向(原速/微快/明显加快)
   ④重录的习惯(最后一遍是定稿吗) ⑤你的口头禅有哪些 ⑥尾卡品牌信息(名字/一句话/CTA)。
4. **试跑样例**,确认全链通,再上自己的素材。

## 习惯学习(错题本机制,越用越懂你)

你每次纠正 AI 的判断(「这卡片多余」「这里别加速」),AI 必须立刻把判例记进
reference/lessons.local.md(现象/判准/动作);同类纠正第二次出现,AI 应提议固化成
style.json 的值或本机规则。**这是本 skill 和「参数固定的工具」的本质区别:
规则会从你的反馈里长出来。**(lessons.local.md 属于你本机,升级不覆盖。)

## 主线八步(逐字稿是中心,和创作者协作)

1. **建档对齐**:项目文件夹 `git init`(嵌套仓库)+写项目档案;跟创作者对齐这条讲什么。
   第一遍全量理解只做一次,之后按档案+日志+diff 干活(→ pipeline.md「项目仓库制」)。
2. **素材变台账**:每条源片转录(一条不漏);转录完跑 `take_cluster.py` 重录聚类
   (默认取最后一遍,疑似改稿单列请人拍板);录屏/无语音素材跑 `visual_index.py` 建视觉台账。
3. **推理最优成片**:先想后剪——≥2 候选结构对着爆款 checklist 和账号数据比(meaning-check.md
   第三层);跑 `redundancy_check.py` 抓跨段重复;内容三问(讲过吗/删了损失什么/哪版最好),
   废话敢删,删单进修改计划,拿不准列选项请人拍板。
4. **表意+对标双检 → 逐字稿请创作者批注**:全文通读八项(主旨/逻辑链/指代/承诺/完备);报告随
   逐字稿进批注文档;批注后的逐字稿=剪辑蓝图。
5. **锁定转录**:`transcript_lock.py lock` 锁成唯一真相源;之后一切剪辑走 remap 推算,
   **永不重新转录**(whisper 每轮变体的地鼠窝从根上拆掉)。
6. **对着蓝图剪**:坐标一律锚句查锁,零手写秒数;每一刀过接缝检查(连接词探测器+逐缝朗读+
   补桥三手段);卡片与大字强调按 overlay-rules.md 判(卡上文字≈原话=违法降级)。
7. **诊断 → 修改计划 → 创作者批 → 才准渲染(闸门)**:创作者的单条反馈是冰山信号不是工单;
   诊断五维(节奏/画面/字幕/内容/音频),计划编号成 P 条目创作者批。produce.py 的
   gates.plan_approved 就是这道闸的机器化。
8. **渲染 → 自检 → 交付**:全链走 `produce.py <project.json>`(哈希缓存,改哪跑哪);
   selfcheck 五项全绿+`audience_read.py` 观众流水稿过审才交付;交付=预览 mp4+用户所选剪辑器的工程
   (剪映/CapCut 草稿最深,EDL/OTIO/素材包兜底);二次修改按协作协议,重生成前必跑 `draft_diff.py`,用户改过的草稿永不覆写。

> 动手前先读 **[reference/judgment.md](reference/judgment.md)**(错题本:真实项目磨出来的坑)。
> 别一上来就想着跑脚本。

## 驱动器

- **新链(默认)**:`produce.py <project.json>` — 蒙太奇/变速/字幕/卡片/混音/自检/草稿/接触表
  八 stage,输入哈希缓存;`--dry-run` 看影响面,`--assume-current` 接管手工项目。
- **老链(单片自动清理)**:`edit.py <config.json>` — assemble→transcribe→cut→cutlock→
  subtitle→audio→deliver,`--from/--to/--resume` 续跑。两种模式(单片/跨片拼接)见 pipeline.md。

## 批注与交付:一切去向,对话里确认

- **逐字稿/计划怎么给**:先问创作者想在哪批注(对话里直接改/本地 md/自己惯用的文档工具),
  按其选择投放。批注约定:保留行=终稿,删行=不要,标注+括号=此处上卡片。
- **成片怎么交**:产出=剪辑器草稿+预览文件,报路径为止;**要不要发送到任何地方,
  问了用户、用户点头才动**。本 skill 不预设任何发送渠道。

## 输出出口(挑你惯用的)

| 出口 | 工具 | 适用 |
|---|---|---|
| 剪映/CapCut 草稿(推荐) | capcut_draft.py | 分轨可编辑,零弹窗,模板克隆法 |
| EDL + SRT | export_timeline.py | DaVinci Resolve / Premiere(EDL 为 beta,导入问题开 issue) |
| FCPXML/OTIO | export_timeline.py(需 opentimelineio) | Final Cut / Premiere |
| 分层素材包(万能兜底) | export_pack.py | 干净底片+SRT+卡片PNG,任何剪辑软件都认 |
| 成品 mp4 | produce.py | 不想再编辑时 |

## 参考(按需读)

- **[reference/judgment.md](reference/judgment.md)** — 错题本(动手前必读)。
- **[reference/pipeline.md](reference/pipeline.md)** — 工具 API/配置/规约总册(按主题归类)。
- **[reference/meaning-check.md](reference/meaning-check.md)** — 表意三层+接缝检查+多模态过审。
- **[reference/overlay-rules.md](reference/overlay-rules.md)** — 卡片 vs 字幕强调立法。
- **[reference/formats.md](reference/formats.md)** — 格式备案(输入/时间线/出口三类地图/平台标准,单一真相源)。
- **[reference/defaults.md](reference/defaults.md)** / **[assets/style.json](assets/style.json)** — 参数与口味。
- **[reference/command-howto.md](reference/command-howto.md)** — 命令 badge 文案(必须查实)。

## 环境

mlx-whisper(`whisper-large-v3-turbo`,Apple 芯片)、ffmpeg(无 libass,PIL 烧字)、Pillow、
Hiragino Sans GB、ClearVoice(venv_cv,可选)、Remotion(卡片动效,可选)。
Apple 芯片外的机器用 faster-whisper;非 macOS 的 OCR 用 RapidOCR(接线中,见 CHANGELOG)。

> 改动:2026-07-12 硬化八步;2026-07-13 草稿直出+协作协议+项目仓库制;
> 2026-07-14 通用化重写(口味出法典进 style.json,边界声明,produce.py 为默认驱动)
