#!/usr/bin/env python3
"""S2 视觉轨:给视频建「画面索引」——场景切换/空白帧/亮度/运动 + 可选 OCR 屏幕文字。

解决(用户点名):流水线看不见画面 → 无语音素材没法剪、叠加时不知道画面是什么。
三层里的信号层+OCR层;语义层(视觉转录)由 agent 看 thumbs 目录的关键帧另行生成。

用法: visual_index.py <video> <outdir> [--interval 4] [--ocr] [--scene 0.30]
产出: outdir/visual_index.json + outdir/thumbs/*.jpg
index 条目: {t, scene(是否切换点), blank, dark, brightness, stddev, ocr:[...行]}
"""
import json
import os
import re
import subprocess
import sys

from PIL import Image

def _ocr_cmd():
    import sys
    binp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr")
    return [binp] if os.path.exists(binp) else [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr.py")]


OCR_BIN = None  # 统一走 _ocr_cmd()(macOS Vision 优先,RapidOCR 备胎)


def scene_times(video, thresh):
    r = subprocess.run(["ffmpeg", "-i", video, "-vf", f"select='gt(scene,{thresh})',showinfo",
                        "-f", "null", "-"], capture_output=True, text=True)
    return [round(float(m), 2) for m in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def grab(video, t, path):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", video,
                    "-frames:v", "1", "-vf", "scale=540:-2", path], check=True)


def analyze(path):
    im = Image.open(path).convert("L")
    px = list(im.getdata())
    n = len(px)
    mean = sum(px) / n
    var = sum((p - mean) ** 2 for p in px) / n
    std = var ** 0.5
    return {"brightness": round(mean, 1), "stddev": round(std, 1),
            "blank": std < 18 and mean > 160,   # 亮而无内容(空白窗/白屏)
            "dark": mean < 22}                   # 黑帧/黑屏


def ocr(path):
    r = subprocess.run(_ocr_cmd() + [path], capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l.strip()]


def main(video, outdir, interval=4.0, do_ocr=False, scene_thresh=0.30):
    os.makedirs(outdir, exist_ok=True)
    td = os.path.join(outdir, "thumbs")
    os.makedirs(td, exist_ok=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip())
    sc = scene_times(video, scene_thresh)
    ts = sorted(set([round(t, 2) for t in sc] +
                    [round(t * interval, 2) for t in range(int(dur / interval) + 1)]))
    idx = []
    for t in ts:
        if t >= dur - 0.1:
            continue
        p = os.path.join(td, f"f{t:08.2f}.jpg")
        try:
            grab(video, t, p)
        except subprocess.CalledProcessError:
            continue
        row = {"t": t, "scene": t in sc, **analyze(p)}
        if do_ocr and not row["dark"]:
            row["ocr"] = ocr(p)
            # 白底界面有文字 ≠ 真空白(实测:Claude 新对话页 std<18 但有输入框文字)
            if row["blank"] and len(row["ocr"]) >= 3:
                row["blank"] = False
        idx.append(row)
    out = os.path.join(outdir, "visual_index.json")
    json.dump(idx, open(out, "w"), ensure_ascii=False)
    n_blank = sum(1 for r in idx if r["blank"])
    n_dark = sum(1 for r in idx if r["dark"])
    print(f"视觉索引: {len(idx)} 帧(场景切换 {len(sc)}) 空白 {n_blank} 黑帧 {n_dark} → {out}")


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2],
         interval=float(a[a.index("--interval") + 1]) if "--interval" in a else 4.0,
         do_ocr="--ocr" in a,
         scene_thresh=float(a[a.index("--scene") + 1]) if "--scene" in a else 0.30)
