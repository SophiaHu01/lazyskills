#!/usr/bin/env python3
"""顶部章节进度条:给长口播片加一根细分段进度条+当前章节名,全程跟播放走。

用法: progress_bar.py <in.mp4> <out.mp4> <chapters.json>
chapters.json: {"chapters":[{"label":"① 没头绪","start":0,"end":62.5}, ...],
                可选 "bar_w":1000,"bar_h":6,"y":16,"steps":120}

机制(2026-07-11,不用教程学AI首用):ffmpeg drawbox 不吃 t 表达式,所以填充用
「N 个小台阶 png,各自 enable=gte(t,T_i)」实现(和字幕同一招,127 个 overlay 无压力)。
底轨=半透明暗条(章节交界留 2px 缝),台阶=品牌橙,章节名=条下方小字,按时段 enable。
产物验法:抽 3 帧(头/中/尾)看填充比例和章节名对不对。
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

VW = 1080
FP = "/System/Library/Fonts/Hiragino Sans GB.ttc"
ORANGE = (255, 106, 0, 255)


def main(inp, outp, chap_path):
    C = json.load(open(chap_path))
    chs = C["chapters"]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", inp], capture_output=True, text=True).stdout.strip())
    BW = C.get("bar_w", 1000); BH = C.get("bar_h", 6); Y = C.get("y", 16); N = C.get("steps", 120)
    X0 = (VW - BW) // 2
    wd = os.path.dirname(os.path.abspath(outp)) or "."
    pb = os.path.join(wd, "pbov"); os.makedirs(pb, exist_ok=True)
    total = chs[-1]["end"]

    # 底轨(章节交界留缝)
    tr = Image.new("RGBA", (BW, BH), (0, 0, 0, 0)); d = ImageDraw.Draw(tr)
    d.rounded_rectangle([0, 0, BW - 1, BH - 1], BH // 2, fill=(20, 20, 20, 110))
    for c in chs[:-1]:
        x = round(BW * c["end"] / total); d.rectangle([x - 1, 0, x + 1, BH], fill=(0, 0, 0, 0))
    tr.save(f"{pb}/track.png")

    # 填充台阶
    sw = BW / N
    step = Image.new("RGBA", (max(2, round(sw)), BH), ORANGE)
    m = Image.new("L", step.size, 255); step.putalpha(m); step.save(f"{pb}/step.png")

    # 章节名小字(条下方居中)
    ft = ImageFont.truetype(FP, 26)
    for i, c in enumerate(chs):
        t = c["label"]
        tw = round(ft.getlength(t))
        im = Image.new("RGBA", (tw + 28, 40), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
        dr.rounded_rectangle([0, 0, im.width - 1, 39], 10, fill=(20, 20, 20, 120))
        dr.text((14, 5), t, font=ft, fill=(255, 255, 255, 230))
        im.save(f"{pb}/lab{i}.png")

    inputs = ["-i", inp, "-i", f"{pb}/track.png", "-i", f"{pb}/step.png"]
    for i in range(len(chs)):
        inputs += ["-i", f"{pb}/lab{i}.png"]
    fc = [f"[0:v][1:v]overlay={X0}:{Y}[b0]"]
    prev = "b0"
    # 台阶:第 k 阶在 t>=k/N*total 时出现
    for k in range(N):
        tk = round(total * k / N, 2); xk = X0 + round(sw * k)
        fc.append(f"[{prev}][2:v]overlay={xk}:{Y}:enable='gte(t,{tk})'[s{k}]")
        prev = f"s{k}"
    for i, c in enumerate(chs):
        fc.append(f"[{prev}][{3+i}:v]overlay=(main_w-overlay_w)/2:{Y+BH+8}:"
                  f"enable='between(t,{c['start']},{c['end']})'[l{i}]")
        prev = f"l{i}"
    fcf = os.path.join(wd, "pb_fc.txt"); open(fcf, "w").write(";".join(fc))
    r = subprocess.run(["ffmpeg", "-y"] + inputs + ["-filter_complex_script", fcf,
                       "-map", f"[{prev}]", "-map", "0:a", "-c:v", "libx264", "-crf", "20",
                       "-preset", "veryfast", "-c:a", "copy", outp], capture_output=True, text=True)
    print("progress_bar ffmpeg", r.returncode)
    if r.returncode: print(r.stderr[-600:]); sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
