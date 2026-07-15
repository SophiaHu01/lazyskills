#!/usr/bin/env python3
"""通用时间线出口(任意剪辑软件的翻译官,CapCut 草稿之外的那排):

  SRT   — 字幕,任何剪辑软件都认(export_pack.py 已产,这里可重出)
  EDL   — CMX3600 剪辑表,DaVinci Resolve / Premiere 直接导入(变速段带 M2 备注)
  FCPXML— 装了 opentimelineio 才产(可选依赖),Final Cut / Premiere 用

用法: export_timeline.py <workdir> <出口目录> [--fps 30]
输入: workdir 的 piece_map.json(蒙太奇映射) + montage spec(源文件路径) + cap_segs.json
诚实声明: EDL/FCPXML 属 beta——按规范生成、结构自检通过,但尚未在每个 NLE 真机验证;
导入报错请开 issue 附软件版本,这正是我们要收的兼容性样本。
"""
import glob
import json
import os
import sys


def tc(sec, fps):
    f = int(round((sec - int(sec)) * fps))
    s = int(sec)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}:{min(f, fps - 1):02d}"


def load(wd):
    wd = wd.rstrip("/") + "/"
    pm = json.load(open(wd + "piece_map.json"))
    spec = None
    for cand in sorted(glob.glob(wd + "montage*.json")):
        spec = json.load(open(cand))
        break
    inserts = [p["insert"] for p in spec["pieces"] if "insert" in p] if spec else []
    base = spec["base"] if spec else ""
    clips, ii = [], 0
    for p in pm:
        if p["kind"] == "base":
            clips.append({"path": base, "src_s": p["old_s"], "src_e": p["old_e"],
                          "rec_s": p["new_s"], "rec_e": p["new_e"]})
        else:
            f = inserts[ii] if ii < len(inserts) else "insert.mp4"
            ii += 1
            clips.append({"path": wd + f if not os.path.isabs(f) else f,
                          "src_s": 0.0, "src_e": p["new_e"] - p["new_s"],
                          "rec_s": p["new_s"], "rec_e": p["new_e"]})
    return clips


def write_edl(clips, out, fps, title="timeline"):
    lines = [f"TITLE: {title}", "FCM: NON-DROP FRAME", ""]
    for i, c in enumerate(clips, 1):
        reel = os.path.splitext(os.path.basename(c["path"]))[0][:32] or f"clip{i}"
        lines.append(f"{i:03d}  {reel:<8} V     C        "
                     f"{tc(c['src_s'], fps)} {tc(c['src_e'], fps)} "
                     f"{tc(c['rec_s'], fps)} {tc(c['rec_e'], fps)}")
        src_d, rec_d = c["src_e"] - c["src_s"], c["rec_e"] - c["rec_s"]
        if abs(src_d - rec_d) > 0.05 and rec_d > 0:
            speed = src_d / rec_d
            lines.append(f"M2   {reel:<8} {speed * fps:.1f}                {tc(c['src_s'], fps)}")
        lines.append(f"* FROM CLIP NAME: {os.path.basename(c['path'])}")
        lines.append("")
    open(out, "w").write("\n".join(lines))
    print(f"EDL → {out} ({len(clips)} 段)")


def write_fcpxml(clips, out, fps):
    try:
        import opentimelineio as otio
    except ImportError:
        print("FCPXML 跳过(可选:pip install opentimelineio)")
        return
    tl = otio.schema.Timeline(name="videoedit")
    tr = otio.schema.Track(kind=otio.schema.TrackKind.Video)
    tl.tracks.append(tr)
    for c in clips:
        rng = otio.opentime.TimeRange(
            otio.opentime.RationalTime(c["src_s"] * fps, fps),
            otio.opentime.RationalTime((c["src_e"] - c["src_s"]) * fps, fps))
        clip = otio.schema.Clip(
            name=os.path.basename(c["path"]),
            media_reference=otio.schema.ExternalReference(target_url="file://" + c["path"]),
            source_range=rng)
        tr.append(clip)
    otio.adapters.write_to_file(tl, out)
    print(f"FCPXML/OTIO → {out}")


def main(wd, outdir, fps=30):
    os.makedirs(outdir, exist_ok=True)
    clips = load(wd)
    write_edl(clips, os.path.join(outdir, "timeline.edl"), fps)
    write_fcpxml(clips, os.path.join(outdir, "timeline.otio"), fps)
    # SRT 顺手重出(通用兜底)
    segs = json.load(open(wd.rstrip("/") + "/cap_segs.json"))
    def st(t):
        ms = int(round((t - int(t)) * 1000))
        s = int(t)
        return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d},{ms:03d}"
    srt = "".join(f"{i}\n{st(s)} --> {st(e)}\n{txt}\n\n"
                  for i, (s, e, txt) in enumerate(segs, 1) if txt.strip())
    open(os.path.join(outdir, "captions.srt"), "w").write(srt)
    print(f"SRT → {outdir}/captions.srt ({len(segs)} 条)")


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], int(a[a.index("--fps") + 1]) if "--fps" in a else 30)
