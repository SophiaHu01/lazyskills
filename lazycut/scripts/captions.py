#!/usr/bin/env python3
"""字幕:分段(wseg/split) + 过滤(_junk) + 渲染字幕 PNG(cap_png)。

隐藏耦合:字号由 HAS_ENDCARD + END_CARD_START 决定(结尾卡遮挡时字幕缩小),
这两个值由调用方(build.py)传入。逻辑一律照搬自原 build.py,数值一个不许改。
"""
import json, re
from PIL import Image, ImageDraw, ImageFont
from common import VW, FP, MAXC, wrap

NF=ImageFont.truetype(FP,64); SFc=ImageFont.truetype(FP,42)


def make_captions(cfg, WD, fix, end, END_CARD_START, HAS_ENDCARD, PD):
    segs=json.load(open(WD+"cap_segs.json")); words=json.load(open(WD+"cap_words.json"))
    # 正文字幕字号可配(默认 64=竖屏原值,不填=不变);横屏可调小。LH/描边/每行字数随字号等比,视觉宽度稳定
    NF_SIZE=int(cfg.get("subtitle_size",64)); _r=NF_SIZE/64
    NFc=ImageFont.truetype(FP,NF_SIZE); NF_LH=round(88*_r); NF_SW=max(3,round(6*_r)); NF_MX=round(11*64/NF_SIZE)
    # 安全区(2026-07-13 用户要求:右侧点赞栏会挡字幕):cfg.subtitle_line_chars 可压每行字数(如 9-10),默认不变
    NF_MX=int(cfg.get("subtitle_line_chars", NF_MX))
    def wseg(s,e): return [(w,a,b) for w,a,b in words if s<=(a+b)/2<=e]
    def split(ws):
        txt=re.sub(r'(.)\1{2,}$','',fix("".join(w for w,_,_ in ws)).strip())  # 去结尾重复字幻觉(咱咱咱/呀呀)
        if len(txt)<=MAXC or len(ws)<2: return [(ws[0][1],ws[-1][2],txt)]
        # 在中间三分之一找最大停顿拆(平衡两半),连续语速也不会从头剥单字
        lo=max(1,len(ws)//3); hi=max(lo+1,min(len(ws), 2*len(ws)//3+1))
        _lat=lambda c: c.isascii() and c.isalpha()
        cands=[k for k in range(lo,hi) if not (ws[k-1][0] and ws[k][0] and _lat(ws[k-1][0][-1]) and _lat(ws[k][0][0]))]  # 不在英文词中间断(Code→C+ode)
        if not cands: cands=list(range(lo,hi))
        gi=max(cands, key=lambda k: ws[k][1]-ws[k-1][2])
        return split(ws[:gi])+split(ws[gi:])
    def _junk(t):
        t=t.strip(); return (not t) or len(set(t))<=1  # 空 / 全同一个字(幻觉)
    capev=[]
    for s,e,_ in segs:
        ws=wseg(s,e)
        if ws: capev+=split(ws)
    capev=[c for c in capev if c[0]<end-0.2 and (c[1]-c[0])>=0.35 and not _junk(c[2])]
    # 重点词强调(2026-07-11,用户要的「重点变大标黄」):cfg.emphasis=[词组..],命中的子串
    # 用 1.22 倍字号+黄色渲染,行内混排、按基线对齐。没配 emphasis 时走原路径,数值不动。
    EMPH=cfg.get("emphasis",[])
    EF=ImageFont.truetype(FP,round(NF_SIZE*1.22)); EYELLOW=(255,214,10,255)
    def _runs(ln):
        runs=[(ln,False)]
        for kw in EMPH:
            out=[]
            for txt,em in runs:
                if em or kw not in txt: out.append((txt,em)); continue
                parts=txt.split(kw)
                for j,pp in enumerate(parts):
                    if pp: out.append((pp,False))
                    if j<len(parts)-1: out.append((kw,True))
            runs=out
        return runs
    def cap_png(text,idx,small):
        font=SFc if small else NFc; LH=58 if small else NF_LH; mx=16 if small else NF_MX; sw=4 if small else NF_SW
        lines=wrap(text,mx); H=(24 if small else 36)+LH*len(lines)
        use_emph = EMPH and not small and any(kw in text for kw in EMPH)
        if use_emph: H+=round(NF_SIZE*0.25)
        img=Image.new("RGBA",(VW,H),(0,0,0,0)); d=ImageDraw.Draw(img)
        for i,ln in enumerate(lines):
            if not use_emph:
                bb=d.textbbox((0,0),ln,font=font); x=(VW-(bb[2]-bb[0]))//2-bb[0]
                d.text((x,16+i*LH),ln,font=font,fill=(255,255,255,255),stroke_width=sw,stroke_fill=(0,0,0,255))
                continue
            runs=_runs(ln)
            widths=[d.textlength(t,font=(EF if em else font)) for t,em in runs]
            x=(VW-sum(widths))//2; ybase=16+round(NF_SIZE*0.25)+i*LH+NF_SIZE
            for (t,em),w in zip(runs,widths):
                f=EF if em else font; col=EYELLOW if em else (255,255,255,255)
                swx=max(sw,round(sw*1.22)) if em else sw
                d.text((x,ybase),t,font=f,fill=col,stroke_width=swx,stroke_fill=(0,0,0,255),anchor="ls")
                x+=w
        p=PD+f"cap{idx:03d}.png"; img.save(p); return (p,H)
    _cp=[cap_png(t,i, HAS_ENDCARD and s>=END_CARD_START) for i,(s,e,t) in enumerate(capev)]
    cap_h=[h for p,h in _cp]
    return (capev, cap_h)
