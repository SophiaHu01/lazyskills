#!/usr/bin/env python3
"""观众流水稿(2026-07-13 立法「成片多模态过审」的工具):把字幕(语音)与卡片按时间轴
合流,输出观众实际接收的文本流。渲染后交付前,对这份稿重跑表意八项(重点:新名词有头吗、
条件分支有着落吗、卡片先行词合法吗)。

用法: audience_read.py <workdir> [remotion_props.json]
读: workdir/cap_segs.json + 卡片 props(可选) → 打印时间轴合流稿
"""
import json
import os
import sys


def _from_srt(path):
    import re
    segs, blk = [], []
    def _t(x):
        h, m, rest = x.split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    for line in open(path, encoding="utf-8").read().split("\n\n"):
        m = re.search(r"([\d:,]+) --> ([\d:,]+)\n(.+)", line, re.S)
        if m:
            segs.append([_t(m.group(1)), _t(m.group(2)), m.group(3).replace("\n", " ").strip()])
    return segs


def main(wd, props_path=None):
    wd = wd.rstrip("/") + "/"
    if os.path.exists(wd + "cap_segs.json"):
        segs = json.load(open(wd + "cap_segs.json"))
    else:
        import glob as _g
        srts = _g.glob(wd + "*.srt")
        if not srts:
            raise SystemExit("没找到 cap_segs.json 或 .srt——先出字幕再跑观众流水稿")
        segs = _from_srt(srts[0])
    events = [(s, "说", t) for s, e, t in segs if t.strip()]
    if props_path:
        for c in json.load(open(props_path)).get("cards", []):
            body = " / ".join(c.get("sub", []))
            events.append((c["start"], "卡", f"【{c['title']}】{body}"))
    for t, kind, txt in sorted(events):
        print(f"{t:6.1f} [{kind}] {txt}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
