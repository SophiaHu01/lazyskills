#!/usr/bin/env python3
"""渲染 + 字幕 + overlay(薄壳:编排 common / render / captions / overlays)。
  python3 build.py <config.json> --cut-only   # 出 cut_locked.mp4 + 转录成片
  python3 build.py <config.json>              # 出 final.mp4(字幕+overlay)

拆分后各模块职责:
  common    共享原语(常量/fix/rounded_shadow/wrap/目录与时长工具)
  render    所有 ffmpeg 调用(render_cut / compose)
  captions  字幕分段 + 渲染字幕 PNG
  overlays  card 模式 + logos/texts 模式的 overlay PNG
PD 只在这里清一次(clear_pd);captions/overlays 只写不清——防静默 bug 的关键。
"""
import sys, json
from vconfig import load
from common import VH
import common, captions, overlays, render


def main(argv):
    cfg = load(argv[1]); WD = cfg["workdir"].rstrip("/")+"/"; CUTONLY = "--cut-only" in argv
    if CUTONLY:
        render.render_cut(cfg); return None
    fix = common.build_fix(cfg)
    segs = json.load(open(WD+"cap_segs.json")); words = json.load(open(WD+"cap_words.json"))
    cutplan = common.load_cutplan(WD); end, END_CARD_START = common.compute_end(cfg, cutplan)
    HAS_ENDCARD = bool((cfg.get("overlay") or {}).get("card"))  # 只有结尾卡遮挡时字幕才缩小
    PD = common.clear_pd(WD)
    capev, cap_h = captions.make_captions(cfg, WD, fix, end, END_CARD_START, HAS_ENDCARD, PD)
    plan = overlays.make_overlays(cfg, WD, fix, end, PD, segs, words)
    # 字幕位置按成片实际分辨率算(支持横屏);竖屏 1080x1920 时 CAPX=0、VID_H=1920,与原写死值一致
    import subprocess
    _pr=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height",
                        "-of","csv=p=0:s=x",WD+"cut_locked.mp4"],capture_output=True,text=True)
    VID_W,VID_H=[int(z) for z in _pr.stdout.strip().split("x")]
    CAPX=(VID_W-common.VW)//2   # 字幕 PNG 宽=VW,横屏时水平居中;竖屏 =0
    BOTTOM=cfg.get("subtitle_bottom",270)   # 字幕底部偏移可配(默认270=竖屏原值);横屏调小=更贴底
    # 合成:overlay 先叠,字幕最上层(items 里 plan 在前 capstream 在后)
    capstream=[(f"cap{i:03d}.png",s,e,CAPX,(VID_H-85-cap_h[i]) if s>=END_CARD_START else (VID_H-BOTTOM-cap_h[i])) for i,(s,e,t) in enumerate(capev)]
    # overlay x 加 CAPX:overlays.cx 在 VW(1080)内居中,横屏时 +CAPX 变成实际画面宽内居中(竖屏 CAPX=0 不变)
    items=[(PD+p,s,e,x+CAPX,y) for (p,x,y,s,e) in plan]+[(PD+p,s,e,x,y) for (p,s,e,x,y) in capstream]
    r=render.compose(cfg,WD,items)
    print("字幕",len(capev),"| overlay",len(plan),"| ffmpeg",r.returncode)
    if r.returncode: print(r.stderr[-1200:])
    return {"cfg":cfg,"WD":WD,"end":end,"END_CARD_START":END_CARD_START,"HAS_ENDCARD":HAS_ENDCARD,
            "PD":PD,"fix":fix,"capev":capev,"cap_h":cap_h,"plan":plan,"capstream":capstream,"items":items}


if __name__ == "__main__":
    main(sys.argv)
