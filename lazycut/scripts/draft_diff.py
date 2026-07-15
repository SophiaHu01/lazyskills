#!/usr/bin/env python3
"""读回用户在 CapCut 里的手改(2026-07-13,双向协作闭环):比对草稿的「生成快照」与「当前状态」,
用人话报告用户动了什么——重生成之前必须跑,否则会把用户的手改无声抹掉。

比对维度(语义比对,不看键序):
  视频段: 删了哪段/挪了哪段/改速/改音量/裁剪(source 变化)——段落用其源区间对应的锚句描述
  文本:   改了哪条字幕/卡片的文字、时间、删增
  新增:   用户自己加的轨道/素材(BGM、贴纸等)只报数量,不深究

用法: draft_diff.py <草稿文件夹> [workdir]   # workdir 提供 transcript.lock 时,视频段用锚句描述
退出码: 0=无手改 1=有手改(重生成前先合并或换新草稿名)
"""
import json
import os
import sys


def _vsegs(d):
    vids = {m["id"]: os.path.basename(m.get("path", "?")) for m in d["materials"].get("videos", [])}
    out = []
    for tr in d["tracks"]:
        if tr["type"] != "video":
            continue
        for s in tr["segments"]:
            out.append({"file": vids.get(s["material_id"], "?"),
                        "src": (s["source_timerange"]["start"], s["source_timerange"]["duration"]),
                        "tgt": (s["target_timerange"]["start"], s["target_timerange"]["duration"]),
                        "speed": round(s.get("speed", 1.0), 3), "vol": s.get("volume", 1.0),
                        "visible": s.get("visible", True)})
    return out


def _texts(d):
    txt = {}
    for m in d["materials"].get("texts", []):
        try:
            txt[m["id"]] = json.loads(m["content"]).get("text", "")
        except Exception:
            txt[m["id"]] = m.get("base_content", "?")
    out = []
    for tr in d["tracks"]:
        if tr["type"] != "text":
            continue
        for s in tr["segments"]:
            out.append({"text": txt.get(s["material_id"], "?"),
                        "tgt": (s["target_timerange"]["start"], s["target_timerange"]["duration"])})
    return out


def _anchor(seg, lock):
    """视频段源区间 → 锚句(锁文本),用户/我都能看懂在说哪段。"""
    if not lock:
        return f"{seg['file']} {seg['src'][0]/1e6:.1f}s起"
    s0, d0 = seg["src"][0] / 1e6, seg["src"][1] / 1e6
    hits = [t for s, e, t in lock["segs"] if s < s0 + d0 and e > s0]
    return f"「{hits[0][:12]}…{hits[-1][-8:]}」" if hits else f"{seg['file']} {s0:.1f}s起"


def main(draft_dir, workdir=None):
    gen = json.load(open(os.path.join(draft_dir, "draft_info.gen.json")))
    cur = json.load(open(os.path.join(draft_dir, "draft_info.json")))
    lock = None
    if workdir and os.path.exists(os.path.join(workdir, "transcript.lock.json")):
        # 注意:锁须是「成片底源时间轴」那版(montage 用的),不是被 remap 过的
        lock = json.load(open(os.path.join(workdir, "transcript.lock.json")))
    changes = []
    gv, cv = _vsegs(gen), _vsegs(cur)
    gkeys = {(v["file"], v["src"]): v for v in gv}
    ckeys = {(v["file"], v["src"]): v for v in cv}
    for k, v in gkeys.items():
        if k not in ckeys:
            changes.append(f"删/裁了视频段 {_anchor(v, lock)}")
        else:
            c = ckeys[k]
            if abs(c["tgt"][0] - v["tgt"][0]) > 1000:
                changes.append(f"挪动了 {_anchor(v, lock)}: {v['tgt'][0]/1e6:.1f}s → {c['tgt'][0]/1e6:.1f}s")
            if c["speed"] != v["speed"]:
                changes.append(f"改速 {_anchor(v, lock)}: {v['speed']} → {c['speed']}")
            if c["vol"] != v["vol"] or c["visible"] != v["visible"]:
                changes.append(f"改音量/可见性 {_anchor(v, lock)}")
    for k, c in ckeys.items():
        if k not in gkeys:
            changes.append(f"新增/重裁了视频段 {_anchor(c, lock)}")
    gt, ct = _texts(gen), _texts(cur)
    gset = {t["text"] for t in gt}
    cset = {t["text"] for t in ct}
    for t in gset - cset:
        changes.append(f"删/改了文本:「{t[:20]}」")
    for t in cset - gset:
        changes.append(f"新文本:「{t[:20]}」")
    g_aud = len(gen["materials"].get("audios", []))
    c_aud = len(cur["materials"].get("audios", []))
    if c_aud > g_aud:
        changes.append(f"用户加了 {c_aud - g_aud} 条音频(BGM/音效)")
    if not changes:
        print("草稿与生成快照一致:用户没手改,可安全重生成同名草稿")
        return 0
    print(f"检测到 {len(changes)} 处手改(重生成前先合并,或换新草稿名):")
    for c in changes:
        print(" ·", c)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
