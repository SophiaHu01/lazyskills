#!/usr/bin/env python3
"""分层素材包导出:流水线只管结构层,表现层交给用户在 CapCut 精修(2026-07-12 创作者拍板的分工)。

用法: export_pack.py <config.json> <输出目录> [--audio-from <带增强人声的mp4>]

产出(全部可独立编辑,不烧死):
  干净底片.mp4     定剪画面(无字幕无卡) + 增强人声(--audio-from 提供则换轨,否则原声)
  字幕.srt         纠错后逐句字幕(CapCut 直接导入,样式用户自己挑)
  卡片/*.png       全部 overlay 卡(带透明通道),配 卡片时间表.txt(出现秒/停留/内容)
  章节表.txt       章节边界(用户要进度条可在 CapCut 里重建)
"""
import json, os, shutil, subprocess, sys

def mmss(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

def main(cfg_path, outdir, audio_from=None):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from common import build_fix
    cfg = json.load(open(cfg_path))
    WD = cfg["workdir"].rstrip("/") + "/"
    fix = build_fix(cfg)
    os.makedirs(outdir, exist_ok=True)

    # 1) 干净底片:cut_locked 画面 + 增强人声(如给)
    base = os.path.join(outdir, "干净底片.mp4")
    if audio_from and os.path.exists(audio_from):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", WD + "cut_locked.mp4", "-i", audio_from,
                        "-map", "0:v", "-map", "1:a", "-c", "copy", "-shortest", base], check=True)
        print("干净底片: cut_locked 画面 + 增强人声轨")
    else:
        shutil.copy(WD + "cut_locked.mp4", base)
        print("干净底片: cut_locked 原声(没给增强音轨)")

    # 2) SRT(纠错后,句级)
    segs = json.load(open(WD + "cap_segs.json"))
    lines = []
    n = 0
    for s, e, t in segs:
        ft = fix(t).strip()
        if not ft or e - s < 0.2 or len(set(ft)) <= 1: continue
        n += 1
        lines.append(f"{n}\n{mmss(s)} --> {mmss(e)}\n{ft}\n")
    open(os.path.join(outdir, "字幕.srt"), "w").write("\n".join(lines))
    print(f"字幕.srt: {n} 句(已纠错)")

    # 3) 卡片 PNG + 时间表(锚点按纠错后字幕解析,和 overlays.py 同逻辑)
    cards_dir = os.path.join(outdir, "卡片"); os.makedirs(cards_dir, exist_ok=True)
    def anchor_time(anchor, at):
        for s, e, t in segs:
            if anchor and anchor in fix(t): return s
        return at
    rows = []
    for i, tx in enumerate(cfg.get("overlay", {}).get("texts", [])):
        src = WD + f"ov/tx{i}.png"
        if not os.path.exists(src): continue
        name = tx.get("title") or tx.get("header") or f"卡{i}"
        safe = "".join(c for c in name if c.isalnum() or "一" <= c <= "鿿")[:12] or f"卡{i}"
        dst = f"{i:02d}_{safe}.png"
        shutil.copy(src, os.path.join(cards_dir, dst))
        at = anchor_time(tx.get("anchor"), tx.get("at", 0))
        rows.append(f"{dst}  出现 {mmss(at)[:-4]}  停留 {tx.get('hold','?')}s  锚点「{tx.get('anchor','')}」")
    open(os.path.join(outdir, "卡片时间表.txt"), "w").write("\n".join(rows))
    print(f"卡片: {len(rows)} 张 + 时间表")

    # 4) 章节表
    ch = WD + "chapters.json"
    if os.path.exists(ch):
        cc = json.load(open(ch))["chapters"]
        open(os.path.join(outdir, "章节表.txt"), "w").write(
            "\n".join(f"{c['label']}  {mmss(c['start'])[:-4]} - {mmss(c['end'])[:-4]}" for c in cc))
        print(f"章节表: {len(cc)} 段")
    print("素材包完成:", outdir)

if __name__ == "__main__":
    af = None
    if "--audio-from" in sys.argv:
        i = sys.argv.index("--audio-from"); af = sys.argv[i + 1]
    main(sys.argv[1], sys.argv[2], af)
