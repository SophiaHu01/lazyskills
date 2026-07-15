#!/usr/bin/env python3
"""跨段内容重复检测(2026-07-13,用户抓出 Playwright 被介绍两次而流程没拦):
对(锁定)转录的所有句段做两两相似度扫描,报「不同位置讲了同一件事」的候选。
用法: redundancy_check.py <transcript.lock.json 或 cap_segs.json> [--min 0.6] [--gap 8]
只报间隔 > gap 秒的相似对(相邻句相似是正常表达,隔很远还相似才是重复介绍)。
这是诊断步的工具:报出来的进修改计划让用户拍,不自动删。
"""
import difflib
import json
import sys


def main(path, min_ratio=0.6, min_gap=8.0):
    data = json.load(open(path))
    segs = data["segs"] if isinstance(data, dict) else data
    segs = [(s, e, t.strip()) for s, e, t in segs if t.strip() and len(t.strip()) >= 6]
    pairs = []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            s1, _, t1 = segs[i]
            s2, _, t2 = segs[j]
            if s2 - s1 < min_gap:
                continue
            r = difflib.SequenceMatcher(None, t1, t2).ratio()
            if r >= min_ratio:
                pairs.append((r, s1, t1, s2, t2))
    pairs.sort(reverse=True)
    if not pairs:
        print("无跨段重复(阈值", min_ratio, ")")
    for r, s1, t1, s2, t2 in pairs[:15]:
        print(f"相似 {r:.2f}  [{s1:.0f}s] {t1[:22]}  ↔  [{s2:.0f}s] {t2[:22]}")
    return 1 if pairs else 0


if __name__ == "__main__":
    a = sys.argv
    sys.exit(main(a[1],
                  float(a[a.index("--min") + 1]) if "--min" in a else 0.6,
                  float(a[a.index("--gap") + 1]) if "--gap" in a else 8.0))
