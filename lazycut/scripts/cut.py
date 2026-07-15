#!/usr/bin/env python3
"""剪辑方案: python3 cut.py <config.json>
自动删静音/口头禅/结尾尾 + config.editorial_cuts 的编辑删减 → workdir/cutplan.json"""
import sys, json, subprocess, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vconfig import load
cfg = load(sys.argv[1])
WD = cfg["workdir"].rstrip("/")+"/"; SRC = cfg["video"]
SPEED = cfg.get("speed",1.0); SIL_DB = cfg.get("silence_db",-30)
KEEP_SENT = cfg.get("keep_sent",0.26); KEEP_MID = cfg.get("keep_mid",0.11); KEEP_WORDCUT = 0.06
FILLERS = cfg.get("filler_words",["然后"])

W = json.load(open(WD+"src_words.json"))
SENT = json.load(open(WD+"src_sents.json"))
VIDEO_END = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
              "-of","csv=p=0",SRC],capture_output=True,text=True).stdout.strip())
LAST_WORD_END = W[-1][2] if W else VIDEO_END

chars=[]; char_word=[]
for wi,(w,s,e) in enumerate(W):
    for ch in w:
        if ch.strip(): chars.append(ch); char_word.append(wi)
text="".join(chars)
def find_span(sub, near=None):
    idx=-1; best=None
    while True:
        idx=text.find(sub, idx+1)
        if idx<0: break
        i=char_word[idx]; j=char_word[idx+len(sub)-1]
        if near is None: return (i,j)
        if best is None or abs(W[i][1]-near)<abs(W[best[0]][1]-near): best=(i,j)
    return best
def near_sent(t): return any(abs(t-x)<0.30 for x in SENT)

ranges=[]
# 1) 编辑删减(用户反馈的:废话段/重复)—— 源秒 或 短语
for ec in cfg.get("editorial_cuts",[]):
    if isinstance(ec, list):
        ranges.append([float(ec[0]), float(ec[1])]); continue
    p = ec.get("phrase"); until = ec.get("until_phrase")
    if not p: continue
    i1 = text.find(p)
    if i1<0: print("!! editorial 未找到:",p); continue
    wa = char_word[i1]
    if until:
        i2 = text.find(until, i1+len(p))
        wb = char_word[i2] if i2>=0 else min(wa+40,len(W)-1)
        a = W[wa-1][2]+KEEP_WORDCUT if wa>0 else 0; b = W[wb][1]-0.02
    else:
        wb = char_word[i1+len(p)-1]
        a = W[wa-1][2]+KEEP_WORDCUT if wa>0 else 0; b = (W[wb+1][1]-0.02) if wb+1<len(W) else VIDEO_END
    ranges.append([round(a,3),round(b,3)])
# 2) 口头禅
for fw in FILLERS:
    _idx=-1
    while True:
        _idx=text.find(fw,_idx+1)
        if _idx<0: break
        i=char_word[_idx]; j=char_word[_idx+len(fw)-1]
        a=(W[i-1][2]-0.02) if i>0 else W[i][1]; b=(W[j+1][1]+0.02) if j+1<len(W) else W[j][2]
        ranges.append([round(a,3),round(b,3)])
# 3) 静音处理。三档 silence_mode:
#    "aggressive"(单条原片,默认)= 句子边界留话口、句内收紧
#    "gentle"(终稿拼接片)= 只砍很长的死气口(>0.8s)、保留自然停顿
#    "off" = 完全不动停顿(只切编辑删减+口头禅)
SIL_MODE = cfg.get("silence_mode","aggressive")
if SIL_MODE != "off":
    out=subprocess.run(["ffmpeg","-i",SRC,"-af",f"silencedetect=noise={SIL_DB}dB:d=0.12","-f","null","-"],
                       capture_output=True,text=True).stderr
    sil=[]; cur=None
    for line in out.splitlines():
        m=re.search(r'silence_start: ([\d.]+)',line); n=re.search(r'silence_end: ([\d.]+)',line)
        if m: cur=float(m.group(1))
        if n and cur is not None: sil.append((cur,float(n.group(1)))); cur=None
    for s,e in sil:
        if e<=0.35: ranges.append([round(max(0,e-0.30),3), round(e-0.10,3)]); continue
        if s>=LAST_WORD_END-0.3: continue
        if SIL_MODE=="gentle":
            if e-s>0.7: ranges.append([round(s+0.22,3), round(e-0.22,3)])   # 只砍>0.7s长气口→留~0.45s;短停顿不动
        else:
            keep = KEEP_SENT if near_sent(e) else KEEP_MID
            if e-s>keep+0.03:
                ranges.append([round(s+keep*0.4,3), round(e-keep*0.6,3)])

def merge(rs, gap=0.10):
    rs=[r for r in rs if r[1]-r[0]>0.015]; rs.sort(); m=[]
    for a,b in rs:
        if m and a<=m[-1][1]+gap: m[-1][1]=max(m[-1][1],b)
        else: m.append([a,b])
    return m
merged=merge(ranges)
# 结尾:end_keep 或 自动到最后一个词后
END_KEEP = cfg.get("end_keep") or round(LAST_WORD_END+0.10,2)
merged=[[a,b] for a,b in merged if b<=END_KEEP]
merged.append([END_KEEP,VIDEO_END]); merged=merge(merged)

kept=[]; cur=0.0
for a,b in merged:
    if a>cur+0.02: kept.append([round(cur,3),round(a,3)])
    cur=b
if cur<VIDEO_END-0.02: kept.append([round(cur,3),round(VIDEO_END,3)])
# 分段变速:介绍段(intro_until_phrase 之前的 kept 段)单独提到 intro_speed,其余用 SPEED
INTRO_SPEED = cfg.get("intro_speed"); seg_speeds = None
if INTRO_SPEED:
    iu = cfg.get("intro_until_phrase",""); bt = None
    if iu:
        _i = text.find(iu)
        if _i >= 0: bt = W[char_word[_i]][1]
    if bt is not None:
        seg_speeds = [round(INTRO_SPEED,3) if b <= bt else SPEED for a,b in kept]
        print(f"分段变速:介绍段(<{bt:.1f}s)={INTRO_SPEED}x,其余={SPEED}x")
    else:
        print("!! intro_until_phrase 未找到,分段变速跳过")
json.dump({"cuts":merged,"kept":kept,"speed":SPEED,"seg_speeds":seg_speeds}, open(WD+"cutplan.json","w"))
tot=sum(b-a for a,b in merged)
_dur=sum((b-a)/(seg_speeds[i] if seg_speeds else SPEED) for i,(a,b) in enumerate(kept))
print(f"{len(merged)} 刀,剪 {tot:.1f}s,保留 {len(kept)} 段 → 成片 ≈ {_dur:.0f}s")
