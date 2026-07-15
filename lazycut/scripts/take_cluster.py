#!/usr/bin/env python3
"""重录聚类(2026-07-14,素材理解层①):原始转录里自动找「同一句录了好几遍」,默认取最后一遍。

开源空白地带,方法论来源(调研已核):TimeBolt=重复检测+默认留最后+可调往后看窗口;
videocut-skills=口误三分类(整句重复/说错替换/卡顿)。创作者拍板:默认取最后一遍(=用户习惯)。

规则:
  相似度 ≥ HIGH(0.72)      → 整句重复,同簇,取最后一遍
  GRAY(0.45) ≤ 相似度 < HIGH → 疑似改稿(说法变了):不自动删,标出来交创作者拍板
  簇内早期 take 很短且是后一句前缀 → 卡顿(起头失败),直接删
用法: take_cluster.py <segs.json> [--lookahead 6] [--report out.json]
输出: 人话对照表(stdout) + 机器结果(--report):kept/dropped/ask 三份清单
"""
import difflib
import json
import sys


def sim(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def cluster(segs, lookahead=6, high=0.72, gray=0.45):
    n = len(segs)
    drop, ask, reasons = set(), [], {}
    i = 0
    while i < n:
        s0, e0, t0 = segs[i]
        if not t0.strip():
            i += 1
            continue
        # 在窗口里找本句的重录(后面出现高相似句)
        takes = [i]
        j = i + 1
        while j < min(i + 1 + lookahead, n):
            r = sim(t0, segs[j][2])
            # 卡顿:后句以本句为前缀延展,本句很短(起头失败)
            if len(t0) <= 8 and segs[j][2].startswith(t0[: max(2, len(t0) - 1)]) and len(segs[j][2]) > len(t0):
                takes.append(j)
            elif r >= high:
                takes.append(j)
            elif (r >= gray
                  and abs(len(t0) - len(segs[j][2])) < max(len(t0), len(segs[j][2])) * 0.6
                  # 防排比误报(2026-07-14 真实素材实测):改稿=紧挨着重来且开头相同;
                  # 排比句(这里/那里,能/不能)开头就不同,或隔了好几句——不问创作者,别当改稿
                  and segs[j][0] - e0 <= 3.5
                  and t0[:2] == segs[j][2][:2]):
                ask.append({"a": {"t": s0, "text": t0}, "b": {"t": segs[j][0], "text": segs[j][2]},
                            "sim": round(r, 2), "note": "疑似改稿(说法变了),交创作者拍板"})
            j += 1
        if len(takes) > 1:
            keep = takes[-1]   # 默认取最后一遍
            for k in takes[:-1]:
                drop.add(k)
                kind = "卡顿起头" if len(segs[k][2]) <= 8 else "整句重复"
                reasons[k] = f"{kind}→取最后一遍({segs[keep][0]:.1f}s)"
            i = takes[-1] + 1
        else:
            i += 1
    kept = [dict(s=s, e=e, text=t) for k, (s, e, t) in enumerate(segs) if k not in drop]
    dropped = [dict(s=segs[k][0], e=segs[k][1], text=segs[k][2], reason=reasons[k]) for k in sorted(drop)]
    return kept, dropped, ask


def main(path, lookahead=6, report=None):
    segs = [tuple(x) for x in json.load(open(path))]
    kept, dropped, ask = cluster(segs, lookahead)
    print(f"重录聚类: 共{len(segs)}段 → 保留{len(kept)} 删{len(dropped)} 待创作者拍板{len(ask)}")
    if dropped:
        print("── 建议删除(默认取最后一遍) ──")
        for d in dropped:
            print(f"  {d['s']:7.1f}s 「{d['text'][:24]}」 {d['reason']}")
    if ask:
        print("── 疑似改稿,别自动删,问创作者 ──")
        for a in ask:
            print(f"  {a['a']['t']:7.1f}s「{a['a']['text'][:20]}」vs {a['b']['t']:.1f}s「{a['b']['text'][:20]}」sim={a['sim']}")
    if report:
        json.dump({"kept": kept, "dropped": dropped, "ask": ask},
                  open(report, "w"), ensure_ascii=False, indent=1)
        print("报告 →", report)


if __name__ == "__main__":
    a = sys.argv
    main(a[1],
         int(a[a.index("--lookahead") + 1]) if "--lookahead" in a else 6,
         a[a.index("--report") + 1] if "--report" in a else None)
