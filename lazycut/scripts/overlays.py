#!/usr/bin/env python3
"""overlay 生成:老 card 模式(面板/badge/结尾卡) + 新模式(logos/texts,含 prompt/label 卡)。

find_time/_anchor_time 靠 words/segs 定位时间(重剪/变速后自动跟随)。
逻辑一律照搬自原 build.py,数值/几何一个不许改。返回 plan: [(png, x, y, s, e), ...]。
"""
import os
from PIL import Image, ImageDraw, ImageFont
from common import VW, VH, FP, BLACK, COLORS, YMAP, rounded_shadow, panel_from, _wrap_px, cx


def make_overlays(cfg, WD, fix, end, PD, segs, words):
    chars=[];cw=[]
    for i,(w,s,e) in enumerate(words):
        for ch in w:
            if ch.strip(): chars.append(ch); cw.append(i)
    wtext="".join(chars)
    def find_time(sub):
        idx=wtext.lower().find(sub.lower()); return None if idx<0 else words[cw[idx]][1]

    ov=cfg.get("overlay") or {}
    plan=[]  # (png, x, y, s, e)
    # 面板(切品牌卡)
    if ov.get("card"):
        card=Image.open(ov["card"]).convert("RGB")
        for k,p in enumerate(ov.get("panels",[])):
            cy=p["crop_y"]; crop=card.crop((24,cy[0],card.size[0]-24,cy[1]))
            panel_from(crop,p.get("width",860)).save(PD+f"pan{k}.png")
            t=find_time(p["appear_keyword"])
            if t is not None: plan.append((f"pan{k}.png",cx(PD,f"pan{k}.png"),46,round(t-0.3,2),round(t-0.3+p.get("hold",6.0),2)))
        # 命令 badge
        BF=ImageFont.truetype(FP,60); SF=ImageFont.truetype(FP,38)
        for k,b in enumerate(ov.get("badges",[])):
            fill=COLORS.get(b.get("color","black"),BLACK); cmd=b["cmd"]; how=b["how"]
            d0=ImageDraw.Draw(Image.new("RGBA",(10,10)))
            cb=d0.textbbox((0,0),cmd,font=BF); cw2,ch2=cb[2]-cb[0],cb[3]-cb[1]
            hb=d0.textbbox((0,0),how,font=SF); hw,hh=hb[2]-hb[0],hb[3]-hb[1]
            pw,ph=cw2+72,ch2+34; W=max(pw,hw)+72; H=24+ph+16+hh+28
            cardim=Image.new("RGBA",(W,H),(255,255,255,255)); d=ImageDraw.Draw(cardim); px=(W-pw)//2
            d.rounded_rectangle([px,24,px+pw,24+ph],ph//2,fill=fill+(255,))
            d.text((px+(pw-cw2)//2-cb[0],24+(ph-ch2)//2-cb[1]),cmd,font=BF,fill=(255,255,255,255))
            d.text(((W-hw)//2-hb[0],24+ph+16-hb[1]),how,font=SF,fill=(70,70,70,255))
            rounded_shadow(cardim,radius=30,pad=40).save(PD+f"bdg{k}.png")
            t=find_time(b["appear_keyword"])
            if t is not None: plan.append((f"bdg{k}.png",cx(PD,f"bdg{k}.png"),1030,round(t,2),round(t+2.6,2)))
        # 结尾卡
        ec=ov.get("endcard",{})
        panel_from(card,ec.get("width",720)).save(PD+"endcard.png")
        Image.new("RGBA",(VW,VH),(0,0,0,150)).save(PD+"endbg.png")
        plan.append(("endbg.png",0,0,end-ec.get("hold",7.0),end))
        plan.append(("endcard.png",cx(PD,"endcard.png"),60,end-ec.get("hold",7.0)+0.2,end))

    # ===== 通用 logo + 文字卡 overlay(终稿模式:标黄处放品牌卡/出处/prompt)=====
    def _labelcard(title,subs,idx,accent):
        TF=ImageFont.truetype(FP,54); SF=ImageFont.truetype(FP,34); d0=ImageDraw.Draw(Image.new("RGBA",(4,4)))
        tb=d0.textbbox((0,0),title,font=TF); subbs=[d0.textbbox((0,0),s,font=SF) for s in subs]
        cw=max([tb[2]-tb[0]]+[b[2]-b[0] for b in subbs]); pad=46; gap=12
        H=pad+(tb[3]-tb[1])+20+(sum((b[3]-b[1])+gap for b in subbs)-gap if subbs else 0)+pad
        card=Image.new("RGBA",(cw+pad*2,H),(255,255,255,247)); d=ImageDraw.Draw(card); W=cw+pad*2; y=pad
        d.text(((W-(tb[2]-tb[0]))//2-tb[0],y-tb[1]),title,font=TF,fill=accent+(255,)); y+=(tb[3]-tb[1])+20
        for s,b in zip(subs,subbs):
            d.text(((W-(b[2]-b[0]))//2-b[0],y-b[1]),s,font=SF,fill=(80,80,80,255)); y+=(b[3]-b[1])+gap
        p=PD+f"tx{idx}.png"; rounded_shadow(card,radius=30,pad=40).save(p); return os.path.basename(p)
    def _promptcard(header,body,idx):
        HF=ImageFont.truetype(FP,38); BF=ImageFont.truetype(FP,34); W=920; pad=44; maxw=W-pad*2
        bl=_wrap_px(body,BF,maxw); d0=ImageDraw.Draw(Image.new("RGBA",(4,4))); hb=d0.textbbox((0,0),header,font=HF); LH=48
        H=pad+(hb[3]-hb[1])+22+LH*len(bl)+pad; card=Image.new("RGBA",(W,H),(255,255,255,243)); d=ImageDraw.Draw(card)
        d.text((pad-hb[0],pad-hb[1]),header,font=HF,fill=(255,106,0,255)); y=pad+(hb[3]-hb[1])+22
        for ln in bl: d.text((pad,y),ln,font=BF,fill=(35,35,35,255)); y+=LH
        p=PD+f"tx{idx}.png"; rounded_shadow(card,radius=30,pad=40).save(p); return os.path.basename(p)
    def _logorow(files,idx,size=190,gap=54):
        ims=[rounded_shadow(Image.open(f).convert("RGBA").resize((size,size),Image.LANCZOS),radius=42,pad=24) for f in files]
        w=sum(i.size[0] for i in ims)+gap*(len(ims)-1); h=max(i.size[1] for i in ims)
        row=Image.new("RGBA",(w,h),(0,0,0,0)); x=0
        for im in ims: row.alpha_composite(im,(x,(h-im.size[1])//2)); x+=im.size[0]+gap
        p=PD+f"lg{idx}.png"; row.save(p); return os.path.basename(p)
    def _anchor_time(kw,fallback):  # 按字幕关键词定位时间(重剪/变速后自动跟随),找不到回退到写死的 at
        if not kw: return fallback
        for s,e,t in segs:
            if kw in fix(t): return round(s,2)
        print("!! overlay anchor 未找到,回退 at:",kw); return fallback
    for i,lg in enumerate(ov.get("logos",[])):
        nm=_logorow([os.path.expanduser(f) for f in lg["files"]],i); at=_anchor_time(lg.get("anchor"),lg["at"])
        plan.append((nm,cx(PD,nm),lg.get("y",YMAP.get(lg.get("pos","upper"),300)),round(at,2),round(at+lg.get("hold",4.5),2)))
    for i,tx in enumerate(ov.get("texts",[])):
        nm=_promptcard(tx["header"],tx["body"],i) if tx.get("kind")=="prompt" else _labelcard(tx["title"],tx.get("sub",[]),i,tuple(tx.get("accent",[255,106,0])))
        at=_anchor_time(tx.get("anchor"),tx["at"])
        plan.append((nm,cx(PD,nm),tx.get("y",YMAP.get(tx.get("pos","top"),60)),round(at,2),round(at+tx.get("hold",5),2)))
    return plan
