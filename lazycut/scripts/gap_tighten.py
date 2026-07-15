#!/usr/bin/env python3
"""气口收紧(2026-07-13 60秒版返工 E4):片内 >阈值 的停顿压到 ~0.24s,语速本身不动。

原理:silencedetect 找语音区里的长停顿 → 每个停顿只保留首尾各 0.12s → 写 cutplan.json
(kept 区间) → 复用 render.render_cut 渲染并自动 remap 字幕锁(字幕零漂移)。
静音插段(演示/尾卡)在 voice_end 之后,整段原样保留,绝不检测。

用法: gap_tighten.py <config.json> <voice_end秒> [--noise -30] [--min-gap 0.45]
前提: cfg["video"] 指向待收紧的底片;workdir 的 transcript.lock 与该底片同时间轴。
产出: cut_locked.mp4 + 更新后的 cap_*/lock;打印映射后的静默区新坐标。
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

KEEP_EDGE = 0.12  # 停顿两侧各留的呼吸量


def detect_silences(video, noise_db, min_gap):
    r = subprocess.run(["ffmpeg", "-i", video, "-af",
                        f"silencedetect=noise={noise_db}dB:d={min_gap}", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(m) for m in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(starts, ends[:len(starts)]))


def main(cfg_path, voice_end, noise_db=-30, min_gap=0.45):
    cfg = json.load(open(cfg_path))
    wd = cfg["workdir"].rstrip("/") + "/"
    video = cfg["video"] if os.path.isabs(cfg["video"]) else wd + cfg["video"]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip())
    sil = [(a, b) for a, b in detect_silences(video, noise_db, min_gap)
           if b <= voice_end + 0.01 and (b - a) > min_gap]
    cuts = [(a + KEEP_EDGE, b - KEEP_EDGE) for a, b in sil if (b - a) > 2 * KEEP_EDGE + 0.05]
    kept, t = [], 0.0
    for a, b in cuts:
        if a > t:
            kept.append([round(t, 3), round(a, 3)])
        t = b
    kept.append([round(t, 3), round(dur, 3)])
    saved = sum(b - a for a, b in cuts)
    json.dump({"kept": kept, "speed": 1.0}, open(wd + "cutplan.json", "w"))
    import render
    render.render_cut(cfg)
    # 映射旧坐标(如静默插段边界)到新时间轴,给调用方对时用
    from transcript_lock import _mapper_from_cutplan
    m, end = _mapper_from_cutplan(wd)
    print(f"气口: 压掉 {len(cuts)} 个停顿共 {saved:.1f}s | {dur:.1f}s → {end:.1f}s")
    return m, end


if __name__ == "__main__":
    a = sys.argv
    noise = float(a[a.index("--noise") + 1]) if "--noise" in a else -30
    mg = float(a[a.index("--min-gap") + 1]) if "--min-gap" in a else 0.45
    main(a[1], float(a[2]), noise, mg)
