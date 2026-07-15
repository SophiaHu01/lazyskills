#!/usr/bin/env python3
"""字幕与 overlay 的共享原语:常量 + 纠错闭包 + 圆角阴影 + 换行 + 目录/时长工具。

captions.py 和 overlays.py 都从这里取(避免两处各拷一份 rounded_shadow,一改就漂)。
逻辑一律照搬自原 build.py,数值/几何一个不许改。
"""
import os, json, re
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VW,VH = 1080,1920
def _find_font():
    """跨平台中文字体:mac=Hiragino,Windows=微软雅黑,Linux=Noto/文泉驿。找不到给人话报错。"""
    import os
    for p in ("/System/Library/Fonts/Hiragino Sans GB.ttc",
              "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyh.ttf",
              "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"):
        if os.path.exists(p):
            return p
    raise SystemExit("没找到中文字体。装一个(如 Noto Sans CJK)或在 assets/style.json 的 caption.font_path 里指定路径。")


FP = _find_font()
ORANGE=(255,106,0); BLACK=(24,24,24); COLORS={"orange":ORANGE,"black":BLACK}
MAXC=22
YMAP={"top":60,"upper":300,"mid":1000}


def build_fix(cfg):
    """返回 fix 闭包:base corrections.json + cfg.corrections,顺序 replace(顺序敏感,别动)。

    ta 开关(2026-07-11,留学篇教训):讲 AI 的片子 whisper 把「它」写成「他」,老行为是全局
    他→它;但人物题材(教授/同学)全局替换会把人全变成「它」。cfg.ta="human" 关掉全局替换,
    该用「它」的个别处走 cfg.corrections 逐处纠;默认 "ai" 保持老行为。
    """
    base = json.load(open(os.path.join(os.path.dirname(__file__),"..","reference","corrections.json")))
    FIX = base + [tuple(x) for x in cfg.get("corrections",[])]
    ta_ai = cfg.get("ta", "ai") != "human"
    keep = cfg.get("ta_keep", [])   # ai 模式下仍要保住「他」的短语(如「他来画画」指人)
    def fix(t):
        for a,b in FIX: t=t.replace(a,b)
        if ta_ai:
            for i,k in enumerate(keep): t=t.replace(k, f"\x00{i}\x00")
            t = t.replace("他","它").replace("其它","其他")
            for i,k in enumerate(keep): t=t.replace(f"\x00{i}\x00", k)
        return t
    return fix


def rounded_shadow(im, radius=20, pad=44):
    tw,th=im.size; im=im.convert("RGBA")
    m=Image.new("L",(tw,th),0); ImageDraw.Draw(m).rounded_rectangle([0,0,tw-1,th-1],radius,fill=255); im.putalpha(m)
    cv=Image.new("RGBA",(tw+pad*2,th+pad*2),(0,0,0,0)); sh=Image.new("RGBA",cv.size,(0,0,0,0)); sm=Image.new("L",(tw,th),0)
    ImageDraw.Draw(sm).rounded_rectangle([0,0,tw-1,th-1],radius,fill=120); sh.paste((0,0,0,120),(pad,pad+7),sm)
    cv=Image.alpha_composite(cv,sh.filter(ImageFilter.GaussianBlur(15))); cv.alpha_composite(im,(pad,pad)); return cv


def panel_from(imgobj,w):
    s=w/imgobj.size[0]; return rounded_shadow(imgobj.resize((w,round(imgobj.size[1]*s)),Image.LANCZOS))


def wrap(text,mx):
    toks=re.findall(r'[A-Za-z0-9/_.\-]+|.',text); lines=[]; cur=""
    for tk in toks:
        if cur and len(cur)+len(tk)>mx: lines.append(cur); cur=tk
        else: cur+=tk
    if cur: lines.append(cur)
    return lines


def _wrap_px(text,font,maxw):
    d0=ImageDraw.Draw(Image.new("RGBA",(4,4)))
    toks=re.findall(r'[A-Za-z0-9/_.\-]+|.',text); lines=[]; cur=""
    for tk in toks:
        if cur and d0.textlength(cur+tk,font=font)>maxw: lines.append(cur); cur=tk
        else: cur+=tk
    if cur: lines.append(cur)
    return lines


def cx(PD,png):
    from PIL import Image as I; return (VW-I.open(PD+png).size[0])//2


def clear_pd(WD):
    """建 <WD>/ov/ 并清空里面所有文件,返回 PD。清一次(防静默 bug),captions/overlays 只写不清。"""
    PD=WD+"ov/"; os.makedirs(PD,exist_ok=True)
    for f in os.listdir(PD): os.remove(PD+f)
    return PD


def load_cutplan(WD):
    return json.load(open(WD+"cutplan.json"))


def compute_end(cfg,cutplan):
    """分段变速下的成片时长 + 结尾卡起点。END_CARD_START 里写死的 7 是故意的,别跟 endcard 的 hold 统一。"""
    SPEED = cfg.get("speed",1.0)
    _kept=cutplan["kept"]; _sps=cutplan.get("seg_speeds") or [SPEED]*len(_kept)
    end=round(sum((b-a)/s for (a,b),s in zip(_kept,_sps)),2)
    END_CARD_START=end-7
    return (end, END_CARD_START)
