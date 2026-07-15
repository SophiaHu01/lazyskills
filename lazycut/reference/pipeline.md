# 流水线总册:驱动器 / 工具 API / 配置 / 规约(按主题归类)

> 「怎么想」在 [judgment.md](judgment.md);口味参数在 [../assets/style.json](../assets/style.json)
> (规则和口味分家:这里写「为什么有这个机制」,那里写「创作者选了什么值」)。

## 一、驱动器(两代)

### produce.py(默认,2026-07-14)

`produce.py <project.json>`:project.json 收拢全部决定(蒙太奇/速度/卡片/BGM/fx/草稿名/闸门),
八 stage:montage→speed→captions→cards→mix→check→draft→sheet,按输入哈希缓存,改哪跑哪。
- `gates.plan_approved=false` → montage 之后一律拒跑(「计划没批不准渲染」的机器化)。
- draft 前自动 draft_diff:用户手改过 → 自动换版本名,绝不覆写。
- sheet = 六帧接触表一张图目检(省 token 的 QC 形态)。
- `--dry-run` 先看影响面;`--assume-current` 接管手工跑过的项目。
- 验收实录:改一张卡文字 → 只重跑 cards 起的五个 stage。

### edit.py(老链,单片自动清理场景仍用)

assemble→transcribe→cut→cutlock→subtitle→audio→deliver;`--from/--to/--only/--resume/--list`。
开跑前 vconfig 校验素材齐全;每 stage 校验产物真出来(返回 0 但产物缺=失败,wired≠working)。
两种模式配置自动判断:**单片**(silence_mode=aggressive 自动清理)/**跨片拼接**(有 assemble 块,
按批注过的终稿逐字稿拼)。模板 `config.single/assemble.template.json`。

| stage | 脚本 | 输出 |
|---|---|---|
| assemble | assemble.py | assembled.mp4(纯文本匹配拼接,inject 还原漏选过渡句) |
| transcribe | transcribe.py | src_words/segs/sents.json |
| cut | cut.py | cutplan.json(静音/口头禅/editorial_cuts,分段变速) |
| cutlock | build.py --cut-only | cut_locked.mp4 + cap_*(字幕数据来自 cut_locked 自己,别跳过) |
| subtitle | build.py | ov/*.png + final.mp4(HAS_ENDCARD 反向决定字幕字号,非纯字幕步) |
| audio | enhance_audio.py | 定稿(ClearVoice;别用重降噪 afftdn 会发闷) |
| deliver | deliver.py | 压缩版+桌面全画质+快照 |

## 二、脚本地图(单文件工具,文件头有完整用法)

**转录与真相源**
- transcribe.py — mlx-whisper 词级转录(唯一不吃 config 的脚本)。
- transcript_lock.py — S1 锁定:`lock` 纠错后锁成唯一真相源;`remap-cutplan/remap-pieces`
  按剪辑推算新时间轴,**永不重转**;覆盖前自动留 .prev。
- take_cluster.py — 重录聚类:整句重复/卡顿起头默认取最后一遍;疑似改稿(紧邻+同开头+中等相似)
  单列请人拍板;排比防误报(开头不同或隔句远)。实测:120段3真0误/260段8真1改稿。
- redundancy_check.py — 跨段语义重复报告(同一内容讲两次),报告逐条表态,喂修改计划。

**画面理解**
- visual_index.py — 视觉台账:场景切换/空白帧/OCR 屏幕文字(录屏场景阈值用 0.08)。
- ocr(swift 产物) — macOS Vision 帧 OCR,`--boxes` 出坐标;重编译 `swiftc -O ocr.swift -o ocr`。
- demo_pacing.py — 无声演示信息节拍变速(死时间/打字/出结果三档)+隐私黑名单遮罩
  (Sign in/密码/通知),产出 .plan.json 供计划展示。配速与体面是两道独立工序。

**剪辑执行**
- montage_build.py — 文本锚点蒙太奇:pieces 用锚句起止查锁,**杜绝手写秒数**;渲后自动
  remap 字幕+校验(插段区窜词=0/尾段 expect_tail)+打印 quiet-zones。防呆闸:锁时长≠底片时长拒跑。
- gap_tighten.py — 气口收紧(>0.45s 停顿压到 ~0.24s),silencedetect→cutplan→render_cut 自动重映射。
- cut.py / render.py / build.py / common.py / captions.py / overlays.py — 老链实体
  (render_cut 在锁存在时自动走 remap,不再重转)。

**质检**
- selfcheck.py — 渲后五项:接缝黑帧/爆音、冻帧抽查、字幕>3s 空洞、静默区声底
  (mean_volume<-50dB 报警——豁免了机器豁免不了观众)、响度。退出码非零=不许交付。
  `--quiet-zones` 豁免已知静默插段的冻帧/空洞误报(但声底检查不豁免)。
- audience_read.py — 观众流水稿:字幕+卡片按时间轴合流,交付前对它重跑表意八项
  (新名词有头吗/条件分支有着落吗)。局部合法≠全局成立的机器抓手。
- _golden_test.py — 金标准回归(老链字幕路径;新工具的哨兵在 EP01 清单里,已知欠账)。

**交付**
- capcut_draft.py — CapCut 草稿直出(见第五节)。
- draft_diff.py — 读回用户在 CapCut 的手改(生成快照 vs 现状,锚句人话报告)。
- draft_wrap_captions.py — 草稿字幕平衡断行(只动流水线生成的字幕,带写锁保险)。
- export_pack.py — 分层素材包(干净底片/srt/卡片PNG/时间表),用户要全手工精修时用。
- enhance_audio.py / fx_pass.py — 人声增强;音效+BGM 混音(loudnorm 必须最后一步,
  必须在 ClearVoice 之后跑否则音效被吃)。
- progress_bar.py — 顶部章节进度条(可选)。

## 三、配置字段(config.json,老链+字幕层共用)

没填的 vconfig 兜默认(`speed=1.0 · silence_db=-30 · filler_words 见 style.json · audio="ai"`)。

| 字段 | 说明 |
|---|---|
| video / workdir / title | 源片 / 工作目录 / 成片名 |
| silence_mode | aggressive(单片默认)/gentle(只砍>0.7s)/off(拼接默认) |
| speed / intro_speed / intro_until_phrase | 全局与介绍段变速 |
| editorial_cuts | 删段:{phrase}/{phrase,until_phrase}/[起,止],phrase 用原始转录用词 |
| corrections | 纠错(base 在 reference/corrections.json,顺序敏感) |
| ta / ta_keep | 人称替换:ai(他→它,讲AI默认)/human(人物题材必设);keep=例外短语 |
| emphasis | 字幕重点词(大字标黄,值见 style.json) |
| subtitle_size / subtitle_bottom / subtitle_line_chars | 字号/底部偏移/行字数(安全区用) |
| assemble / overlay / audio / deliver | 拼接块 / 卡片(见四) / 音频档 / 交付路径 |

## 四、字幕与卡片

**字幕**:纠错=base+per-video 顺序 replace;whisper 在切口脑补的连接词(那/就是/然后)是幻觉,
清掉;长句在中间三分之一找停顿平衡拆,不断英文词;断句唯一实现=caption_pages.py(段边界必断)。
**安全区**(竖屏,右侧点赞栏):左右各留 ≥130px;PIL 用 subtitle_line_chars(9-13),Remotion
maxWidth 820,CapCut 草稿由 _balance_wrap 平衡断行(≤13字/行,避英文词,标点后优先,免孤字尾)。
**卡片立法**见 [overlay-rules.md](overlay-rules.md)(卡=拿走的参考物;原话复读=违法降级为大字)。
**overlay 定位**:anchor=字幕关键词,自动跟随重剪/变速;`at` 只兜底;命令文案必须查实
([command-howto.md](command-howto.md))。

## 五、CapCut 草稿(交付形态 A)

**直出**(capcut_draft.py):不吐死 mp4,写可编辑工程(视频轨分段+变速/字幕轨/卡片轨)。
- **模板克隆法**:深拷贝用户本机真实草稿的 segment/material 骨架再替换——不逆向、不依赖
  第三方库过期 schema、剪映升级天然免疫。draft_info.json 明文 JSON,时间单位微秒。
- **身份链**(File not accessible 的真凶):CapCut 按素材池身份解析媒体,不按路径。
  videos.local_material_id ↔ meta 素材池条目 id ↔ draft_virtual_store child_id 三方必须自洽;
  克隆模板绝不能把旧素材的身份证抄进来。key_value.json 逐段登记同样要生成。
- **素材进草稿夹用 APFS 克隆(cp -c)**:沙盒免弹窗(CapCut 只免弹窗读自家树+~/Movies)+
  独立快照(硬链接会被流水线 ffmpeg -y 隔空篡改)+删草稿不留孤儿。跨卷退回真复制。
- 带不过去的:PIL 字幕样式/Remotion 动效(进去是默认文本,用户套一次样式);BGM 不放(用户音乐库选)。

**写锁(铁律)**:动创作者打开过的草稿文件前必须确认 CapCut 完全退出(pgrep -x CapCut);
draft_wrap_captions 已内置此闸;流程=请创作者 Cmd+Q→回「关了」→动手→创作者重开。

**二次修改协作协议**:交付双件套(预览 mp4+草稿)。创作者三种改法:①直接在 CapCut 改(零 token,
改完 draft_diff 读回);②字幕原话/时间点指路(原话即坐标,改状态文件重生成);③结构性大改回
逐字稿层。**重生成前必跑 draft_diff**:有手改→合并进真相源或换新版本名,绝不无声抹掉创作者的劳动。

## 六、素材理解层规约(创作者拍板 2026-07-13/14)

- **重录**:转录后必跑聚类;默认取最后一遍(行业默认,policy 可配);对照表随粗剪计划。
- **插画面(口播当导演)**:嘴上讲到的对象=展示(原速/放大),画面在动但没讲细节=加速,
  无关+死时间=剪掉。默认配好用户删多余;主次=操作演示画面全屏+人像小窗或画中画,观点句人像全屏;
  插画面清单在定稿时同步生成(决策在脚本层);画面素材永不预剪碎(叠加轨引用 in/out,非破坏)。
- **录屏压缩**:信息节拍变速(自研)为主;缩放规划抄 Screenize(按打字/点击/滚动分类 zoom),待建。
- **台账兜底**:OCR 为主;画面没文字时用视觉描述模型(CLIP/BLIP 类)兜底——第一次真遇到再接。
- 对标片机器台账走 video-flow 的 benchmark-scan.md(复用本 skill 的 transcribe/visual_index)。

## 七、Remotion 动效层(卡片/整句静态字幕,可选)

工程在 `<你的 remotion 工程路径>(config remotion_dir 指定)`(VidCaption,1080x1920,暖调纸卡)。
要点:props 由 remotion_props.py 生成(词级纠错+latin 词片合并+按 cap_segs 打 br);src 置空=
透明层模式;渲染必须四 flag 齐全:`--codec=prores --prores-profile=4444 --image-format=png
--pixel-format=yuva444p10le`(少一个=无 alpha 糊黑),ffprobe 验 pix_fmt 含 yuva;合成用
overlay format=auto;验收抽帧看「无卡处画面没变黑」。大文件交付:720p 预览+全画质各留路径,去向对话里问用户。

## 八、项目仓库制

每个视频项目=嵌套 git 仓库+项目档案。①首剪建仓写档案(素材地图/结构用锚句/检查结论/
append-only 修改日志),状态文件逐文件 add,媒体 gitignore;②每次修改读档案+日志→只改 diff
涉及的→只重跑受影响 stage→日志追加+commit;③新会话读档案+git log 即拥有全部历史;
④只有结构性大改允许重看素材并更新基线。

## 九、交互边界(创作者拍板 2026-07-14)

**不做任何面板/网页前端**。交互三样:CapCut 草稿(用户动手)/逐字稿批注(用户指路)/
一条命令流水线(执行)。省 token:机械重跑派便宜子模型、QC 用接触表、报告短话说。

---
> 沿革:2026-07-11 emphasis/ta/后处理;07-12 硬化 S1-S5+演示段+分层素材包;07-13 草稿直出+
> 写锁+协作协议+项目仓库制+安全区+素材理解规约;07-14 重录聚类+一键 produce+交互边界+
> 通用化重写(口味分离进 style.json)。原始层积岩备份在 ~/.claude/backups/2026-07-14-skill通用化/。
