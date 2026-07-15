#!/usr/bin/env python3
"""按终稿跨片拼接 → assembled.mp4(终稿模式 step 4,纯机械:文本匹配+拼接,不做剪辑判断)。
  python3 assemble.py <config.json>

config.assemble:
  clips:       [{name, file}]              源片(口播+录屏);顺序无所谓,匹配靠文本
  script_xml:  批注文档导出的 xml(终稿保留行);或用 script_lines 直接给列表
  script_lines:[".."]                       (可选)不走文档工具时的保留行列表
  skip_lines:  [".."]                       终稿里要丢的行(开头钩子等)
  inject:      [{after_line_contains:[..], line:".."}]
               原片有、终稿漏选的过渡句,还原到"第一条含这些词的行"之前(接顺逻辑用)
  corrections: [[a,b]]                       匹配用(终稿和源段两边都纠才对得上)
  out:         默认 <workdir>/assembled.mp4  (= config.video)
"""
import sys, json, re, os, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vconfig import load
cfg = load(sys.argv[1]); WD = cfg["workdir"].rstrip("/")+"/"
A = cfg["assemble"]; CLIPS = A["clips"]; idx = {c["name"]: i for i, c in enumerate(CLIPS)}

base = json.load(open(os.path.join(os.path.dirname(__file__), "..", "reference", "corrections.json")))
FIX = base + [tuple(x) for x in A.get("corrections", [])] + [tuple(x) for x in cfg.get("corrections", [])]
def fix(t):
    for a, b in FIX: t = t.replace(a, b)
    return t.replace("他", "它").replace("其它", "其他").strip()

# 1) 每条源片:有缓存 <name>_segs.json 就用,否则转录
TRANS = os.path.join(os.path.dirname(__file__), "transcribe.py")
segdb = {}
for c in CLIPS:
    sp = WD + c["name"] + "_segs.json"
    if not os.path.exists(sp):
        subprocess.run([sys.executable, TRANS, c["file"], WD + c["name"]], check=True)
    segdb[c["name"]] = [(s, e, fix(t)) for s, e, t in json.load(open(sp))]

# 2) 终稿保留行(顺序) + [m:ss] 消歧
def parse_xml(path):
    d = json.load(open(path)); ct = d["data"]["document"]["content"]
    ct = re.sub(r'<span background-color[^>]*>(.*?)</span>', r'\1', ct)  # 去标黄壳
    out = []
    for m in re.finditer(r'<li[^>]*>(.*?)</li>', ct):
        raw = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        ts = re.search(r'\[(\d+):(\d+)', raw)          # 容错:缺右括号也认
        sec = int(ts.group(1))*60 + int(ts.group(2)) if ts else None
        t = re.sub(r'^\[[\d:]+\]?\s*', '', raw); t = re.sub(r'[（(【].*$', '', t).strip()  # 去时间戳+括号备注
        if t: out.append((fix(t), sec))
    return out
zg = parse_xml(A["script_xml"]) if A.get("script_xml") else [(fix(l), None) for l in A.get("script_lines", [])]

# 3) 丢开头钩子等
skip = A.get("skip_lines", [])
zg = [(l, s) for l, s in zg if not any(sk in l for sk in skip)]

# 4) 注入原片有、终稿漏选的过渡句(接顺逻辑;还原到第一条含 after_line_contains 全部词的行之前)
for inj in A.get("inject", []):
    kws = inj["after_line_contains"]
    for i, (l, s) in enumerate(zg):
        if all(k in l for k in kws): zg.insert(i, (fix(inj["line"]), None)); break

# 5) 匹配:纠错后终稿行 == 纠错后源段(含),[m:ss] 消歧
def match(line, sec, prev_clip, prev_end):
    # 按「匹配质量」分级:精确==0 > line包含于txt==1 > txt包含于line==2 > 前缀弱匹配==3。
    # 弱前缀(line[:8] in txt)不再与精确匹配平起平坐——否则跨片撞前缀会误插(如"Claude C"撞开场账单句)。
    cands = []
    for clip, segs in segdb.items():
        for s, e, txt in segs:
            if e - s < 0.15: continue                  # 跳过零长度退化段
            if not line: continue
            if line == txt: q = 0
            elif line in txt: q = 1
            elif len(txt) >= 4 and txt in line: q = 2
            elif line[:8] in txt: q = 3
            else: continue
            cands.append((q, clip, s, e))
    if not cands: return None
    # 排序:先质量,再「与上一句同片」(script_lines 无时间戳时靠内容顺序局部性消歧),再时间就近
    def keyf(c):
        q, clip, s, e = c
        same = 0 if clip == prev_clip else 1
        tdist = abs(s - sec) if sec is not None else (abs(s - prev_end) if clip == prev_clip else 9e9)
        return (q, same, tdist)
    cands.sort(key=keyf); b = cands[0]; return (b[1], b[2], b[3])
plan = []; miss = []
prev_clip, prev_end = None, 0.0
for line, sec in zg:
    r = match(line, sec, prev_clip, prev_end)
    if r: plan.append(list(r)); prev_clip, prev_end = r[0], r[2]
    else: miss.append(line)
print(f"终稿 {len(zg)} 行,匹配 {len(plan)},漏 {len(miss)}")
for m in miss: print("  ❌未匹配:", m)

# 6) 合并同片连续(gap<0.8),边界留足(头 -0.05 尾 +0.25,不削字)
merged = []
for clip, s, e in plan:
    if merged and merged[-1][0] == clip and s - merged[-1][2] < 0.8:
        merged[-1][2] = max(merged[-1][2], e)
    else: merged.append([clip, s, e])
print(f"合并 {len(merged)} 段")

# 7) ffmpeg 拼接(每段归一到 canvas/30fps/48k;ffmpeg 默认 autorotate 处理旋转标记,原朝向不变形)
#    canvas 默认 1080x1920(竖屏,不写=旧行为不变);横屏 deck 录屏设 "1920x1080",各源片按比例缩放居中、两侧/上下补黑不变形
CW, CH = (cfg.get("canvas", "1080x1920").lower().split("x") + ["1920"])[:2]
CW, CH = int(CW), int(CH)

# 逐段响度归一:各源片录制电平差很多(实测最大差 27dB→"一会大一会小"),拼接前把每片
# 拉到统一集成响度(默认 -16 LUFS),各段一致。用固定增益(不用单遍 loudnorm 免抽水/呼吸)。
LT = cfg.get("loudness_target", -16.0); MAXB = cfg.get("loudness_max_boost", 24.0)
gain = {}
for c in CLIPS:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", c["file"],
                        "-af", "loudnorm=print_format=summary", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"Input Integrated:\s*(-?[\d.]+)", r.stderr)
    if m:
        g = LT - float(m.group(1)); g = max(-MAXB, min(MAXB, g))
    else:
        g = 0.0
    gain[c["name"]] = round(g, 1)
    print(f"  响度 {c['name']}: {m.group(1) if m else '?'} LUFS → 增益 {gain[c['name']]:+.1f}dB")

inp = []
for c in CLIPS: inp += ["-i", c["file"]]
fc = []; labs = []
for i, (clip, s, e) in enumerate(merged):
    ci = idx[clip]; ss = max(0, s - 0.05); ee = e + 0.25
    fc.append(f"[{ci}:v]trim={ss}:{ee},setpts=PTS-STARTPTS,scale={CW}:{CH}:force_original_aspect_ratio=decrease,pad={CW}:{CH}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}]")
    fc.append(f"[{ci}:a]atrim={ss}:{ee},asetpts=PTS-STARTPTS,aresample=48000,volume={gain[clip]}dB[a{i}]")
    labs.append(f"[v{i}][a{i}]")
fc.append("".join(labs) + f"concat=n={len(merged)}:v=1:a=1[vo][ao]")
open(WD + "asm_fc.txt", "w").write(";".join(fc))
out = A.get("out", WD + "assembled.mp4")
r = subprocess.run(["ffmpeg", "-y"] + inp + ["-filter_complex_script", WD + "asm_fc.txt", "-map", "[vo]", "-map", "[ao]",
    "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-c:a", "aac", "-b:a", "192k", out], capture_output=True, text=True)
dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip()
print("ffmpeg", r.returncode, "→", out, dur, "s")
if r.returncode: print(r.stderr[-800:])
