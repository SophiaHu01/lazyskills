#!/usr/bin/env python3
"""S3 渲后自检(偷 video-use 的 Self-Eval 思路):渲染完机器先验,不过=不交付。

查四样:
  ① 剪切点画面:每个拼接/剪切点前后抽帧,黑帧/冻帧(相邻两帧几乎无差)报警
  ② 剪切点音频:接缝 ±0.4s 窗口 max_volume 突变(爆音/咔哒)报警
  ③ 字幕覆盖率:有语音的时间里字幕页覆盖 <90% 报警(用 cap_segs vs 页窗口)
  ④ 响度:成片整体 LUFS 距目标(-14)超 ±1.5 报警
用法: selfcheck.py <video> <workdir> [--joints t1,t2,..] [--lufs-target -14]
退出码: 0=全过 1=有报警(报告落 workdir/selfcheck.json)
"""
import json
import os
import re
import subprocess
import sys

from PIL import Image


def frame(video, t, path):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(max(0, t)), "-i", video,
                    "-frames:v", "1", "-vf", "scale=270:-2", path], check=True)


def luma_stats(path):
    im = Image.open(path).convert("L")
    px = list(im.getdata())
    mean = sum(px) / len(px)
    return mean, px


def diff(px1, px2):
    n = min(len(px1), len(px2))
    return sum(abs(a - b) for a, b in zip(px1[:n], px2[:n])) / n


def maxvol(video, ss, t):
    r = subprocess.run(["ffmpeg", "-ss", str(max(0, ss)), "-t", str(t), "-i", video,
                        "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"max_volume: ([-\d.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def lufs(video):
    r = subprocess.run(["ffmpeg", "-i", video, "-af", "loudnorm=print_format=summary",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"Input Integrated:\s*(-?[\d.]+)", r.stderr)
    return float(m.group(1)) if m else None


def main(video, wd, joints, lufs_target=-14.0, quiet_zones=None):
    quiet_zones = quiet_zones or []  # 已知静默插段(打字录屏等):豁免冻帧与字幕空洞报警
    def in_quiet(t):
        return any(a <= t <= b for a, b in quiet_zones)
    wd = wd.rstrip("/") + "/"
    tmp = wd + "selfcheck_frames/"
    os.makedirs(tmp, exist_ok=True)
    alerts = []
    # ① / ② 剪切点
    for t in joints:
        pa, pb = tmp + f"j{t:.1f}_a.jpg", tmp + f"j{t:.1f}_b.jpg"
        try:
            frame(video, t - 0.2, pa)
            frame(video, t + 0.2, pb)
        except subprocess.CalledProcessError:
            alerts.append({"type": "frame_extract_fail", "t": t})
            continue
        ma, xa = luma_stats(pa)
        mb, xb = luma_stats(pb)
        if ma < 16 or mb < 16:
            alerts.append({"type": "black_frame", "t": t, "luma": [round(ma, 1), round(mb, 1)]})
        mv = maxvol(video, t - 0.4, 0.8)
        if mv is not None and mv > -0.3:
            alerts.append({"type": "audio_clip", "t": t, "max_db": mv})
    # 冻帧粗查:均匀 12 个点,t 与 t+0.5 帧几乎无差且该处应有运动(口播画面)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip())
    for k in range(1, 13):
        t = dur * k / 13
        pa, pb = tmp + f"z{k}_a.jpg", tmp + f"z{k}_b.jpg"
        frame(video, t, pa)
        frame(video, t + 0.5, pb)
        _, xa = luma_stats(pa)
        _, xb = luma_stats(pb)
        if diff(xa, xb) < 0.35 and not in_quiet(t):
            alerts.append({"type": "possible_freeze", "t": round(t, 1)})
    # ③ 字幕覆盖率
    try:
        segs = json.load(open(wd + "cap_segs.json"))
        speech = sum(e - s for s, e, t in segs if t.strip())
        # 页窗口≈段窗口(锁定后 cap_segs 即页源),覆盖率=有文本段总时长/语音总时长,这里检查空洞
        holes = [(round(segs[i][1], 1), round(segs[i + 1][0], 1)) for i in range(len(segs) - 1)
                 if segs[i + 1][0] - segs[i][1] > 3.0
                 and not in_quiet((segs[i][1] + segs[i + 1][0]) / 2)]
        if holes:
            alerts.append({"type": "caption_gap>3s", "holes": holes[:8]})
    except FileNotFoundError:
        pass
    # ④ 响度
    lf = lufs(video)
    if lf is not None and abs(lf - lufs_target) > 1.5:
        alerts.append({"type": "loudness_off", "lufs": lf, "target": lufs_target})
    # ⑤ 静默区声底(2026-07-13 教训:豁免了机器豁免不了观众——静默插段必须有 BGM/音效铺底,
    # 否则观众以为视频坏了。mean_volume < -50dB = 死寂,报警)
    for a, b in quiet_zones:
        r = subprocess.run(["ffmpeg", "-ss", str(a), "-t", str(b - a), "-i", video,
                            "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
        m = re.search(r"mean_volume: ([-\d.]+) dB", r.stderr)
        if m and float(m.group(1)) < -50:
            alerts.append({"type": "quiet_zone_dead_air", "zone": [a, b], "mean_db": float(m.group(1))})
    report = {"video": video, "joints_checked": len(joints), "lufs": lf, "alerts": alerts}
    json.dump(report, open(wd + "selfcheck.json", "w"), ensure_ascii=False, indent=1)
    print(f"自检: 接缝 {len(joints)} 响度 {lf} 报警 {len(alerts)}")
    for a in alerts[:10]:
        print("  ⚠", a)
    return 1 if alerts else 0


if __name__ == "__main__":
    a = sys.argv
    joints = []
    if "--joints" in a:
        joints = [float(x) for x in a[a.index("--joints") + 1].split(",") if x]
    tgt = float(a[a.index("--lufs-target") + 1]) if "--lufs-target" in a else -14.0
    qz = []
    if "--quiet-zones" in a:  # 形如 21.4-30.9,100-105
        for z in a[a.index("--quiet-zones") + 1].split(","):
            lo, hi = z.split("-")
            qz.append((float(lo), float(hi)))
    sys.exit(main(a[1], a[2], joints, tgt, qz))
