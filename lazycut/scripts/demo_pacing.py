#!/usr/bin/env python3
"""无声演示段智能配速 + 内容体面黑名单(2026-07-12 创作者验收过的两次试剪的正式封装)。

两道独立工序,都过了才算演示段处理完:
  配速(节奏):帧差+OCR文字增量切「信息节拍」——死时间快进、打字中速、新内容出现放慢
  体面(黑名单):OCR 命中 Sign in/登录/密码/通知 → 持续横幅按坐标遮罩;瞬时弹窗剪帧

用法: demo_pacing.py <video> <lo秒> <hi秒> <out.mp4> [--step 2] [--canvas 1080x1920]
产出: out.mp4(静音,变速+遮罩) + <out>.plan.json(节拍方案与黑名单命中,供修改计划展示)
阈值(实测校准自「不用教程学AI」录屏,可按片微调):
  死时间: 帧差<0.8 且 |Δocr字数|<8 → 8x    打字中: 其余 → 3x
  新内容: Δocr字数>+30 → 1.5x(给观众读)
"""
import json
import os
import subprocess
import sys

from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))


def _ocr_cmd():
    """选 OCR 引擎:macOS Vision 编译产物优先,否则 RapidOCR 备胎(ocr.py)。"""
    import sys
    binp = os.path.join(_HERE, "ocr")
    if os.path.exists(binp):
        return [binp]
    return [sys.executable, os.path.join(_HERE, "ocr.py")]


OCR = None  # 兼容旧引用;实际统一走 _ocr_cmd()
BLACKLIST = ["sign in", "sign up", "登录", "登陆", "密码", "password", "verification",
             "验证码", "update available", "通知"]
SPEED_DEAD, SPEED_TYPE, SPEED_REVEAL = 8.0, 3.0, 1.5


def _grab(video, t, path, full=False):
    vf = [] if full else ["-vf", "scale=400:-2"]
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", video,
                    "-frames:v", "1", *vf, path], check=True)


def _luma(path):
    im = Image.open(path).convert("L")
    return list(im.getdata())


def _ocr(path, boxes=False):
    args = _ocr_cmd() + [path] + (["--boxes"] if boxes else [])
    r = subprocess.run(args, capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l.strip()]


def analyze(video, lo, hi, step=2.0, tmpdir="pace_tmp"):
    os.makedirs(tmpdir, exist_ok=True)
    frames = []
    t = lo
    while t < hi:
        p = f"{tmpdir}/f{t:07.1f}.jpg"
        _grab(video, t, p)
        chars = sum(len(l) for l in _ocr(p))
        frames.append((t, _luma(p), chars))
        t += step
    plan = []
    for i in range(1, len(frames)):
        t0, px0, c0 = frames[i - 1]
        t1, px1, c1 = frames[i]
        n = min(len(px0), len(px1))
        d = sum(abs(a - b) for a, b in zip(px0[:n], px1[:n])) / n
        dc = c1 - c0
        if d < 0.8 and abs(dc) < 8:
            sp = SPEED_DEAD
        elif dc > 30:
            sp = SPEED_REVEAL
        else:
            sp = SPEED_TYPE
        plan.append([t0, t1, sp])
    merged = []
    for s, e, sp in plan:
        if merged and merged[-1][2] == sp:
            merged[-1][1] = e
        else:
            merged.append([s, e, sp])
    return merged


def blacklist_masks(video, lo, hi, tmpdir="pace_tmp"):
    """中点全分辨率帧扫黑名单,命中的返回像素遮罩框(交给 drawbox)。"""
    os.makedirs(tmpdir, exist_ok=True)
    p = f"{tmpdir}/bl_mid.png"
    _grab(video, (lo + hi) / 2, p, full=True)
    im = Image.open(p)
    W, H = im.size
    masks, hits = [], []
    for line in _ocr(p, boxes=True):
        try:
            geo, txt = line.split("\t", 1)
        except ValueError:
            continue
        if any(k in txt.lower() for k in BLACKLIST):
            x, y, w, h = [float(v) for v in geo.split(",")]
            pad = 0.012
            masks.append([int((x - pad) * W), int((y - pad * 1.5) * H),
                          int((w + 2 * pad) * W), int((h + 3.2 * pad) * H)])
            hits.append(txt)
    return masks, hits, (W, H)


def render(video, plan, masks, out, canvas="1080x1920"):
    cw, ch = canvas.split("x")
    mask_f = "".join(f",drawbox=x={x}:y={y}:w={w}:h={h}:color=0xF7F5F2@1:t=fill"
                     for x, y, w, h in masks)
    v, lab = [], []
    for i, (s, e, sp) in enumerate(plan):
        v.append(f"[0:v]trim={s}:{e},setpts=(PTS-STARTPTS)/{sp}{mask_f}[v{i}]")
        lab.append(f"[v{i}]")
    fc = (";".join(v) + ";" + "".join(lab) + f"concat=n={len(plan)}:v=1:a=0,"
          f"scale={cw}:{ch}:force_original_aspect_ratio=decrease,"
          f"pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2:color=0x1a1613,setsar=1,fps=30[vo]")
    fcf = out + ".fc.txt"
    open(fcf, "w").write(fc)
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video,
                        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                        "-filter_complex_script", fcf, "-map", "[vo]", "-map", "1:a", "-shortest",
                        "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-c:a", "aac", out],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-400:])
        sys.exit(1)


def main(video, lo, hi, out, step=2.0, canvas="1080x1920"):
    plan = analyze(video, lo, hi, step)
    masks, hits, size = blacklist_masks(video, lo, hi)
    render(video, plan, masks, out, canvas)
    src_dur = hi - lo
    out_dur = sum((e - s) / sp for s, e, sp in plan)
    meta = {"plan": plan, "blacklist_hits": hits, "masks": masks,
            "src_dur": src_dur, "out_dur": round(out_dur, 1)}
    json.dump(meta, open(out + ".plan.json", "w"), ensure_ascii=False, indent=1)
    print(f"配速: {src_dur:.0f}s → {out_dur:.1f}s ({len(plan)}段) 黑名单命中 {len(hits)}: {hits[:2]}")


if __name__ == "__main__":
    a = sys.argv
    main(a[1], float(a[2]), float(a[3]), a[4],
         step=float(a[a.index("--step") + 1]) if "--step" in a else 2.0,
         canvas=a[a.index("--canvas") + 1] if "--canvas" in a else "1080x1920")
