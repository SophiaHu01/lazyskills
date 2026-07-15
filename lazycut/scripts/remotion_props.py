#!/usr/bin/env python3
"""生成 Remotion VidCaption 组件的 props(逐词动画字幕 + 卡片)。

用法: remotion_props.py <config.json> <out_props.json> [--window 起,止]

难点是词级纠错:corrections 按整句写(跨多个 whisper 词),词级直接替换纠不到。
做法:全文拼串(记每字符属于哪个词)→ 顺序 replace(含 ta 替换)→ 按字符区间摊回词,
被替换跨越的词按比例分回文字,时间戳保原词区间。emphasis 词组同样在纠错后文本上匹配。
"""
import json, os, sys


def corrected_words(words, fix_pairs, ta_ai, ta_keep, emphasis):
    # words: [[w,s,e],...] → 拼串并记录 char→词索引
    text = ""
    owner = []
    for i, (w, s, e) in enumerate(words):
        text += w
        owner += [i] * len(w)
    # 顺序替换,owner 同步重建(替换段的 owner = 原段首词…原段尾词 均匀摊)
    def apply(text, owner, a, b):
        out_t, out_o = "", []
        i = 0
        while i < len(text):
            if text.startswith(a, i):
                span = owner[i:i + len(a)]
                if b:
                    for k in range(len(b)):
                        out_t += b[k]
                        out_o.append(span[min(int(k * len(span) / max(1, len(b))), len(span) - 1)])
                i += len(a)
            else:
                out_t += text[i]
                out_o.append(owner[i])
                i += 1
        return out_t, out_o
    for a, b in fix_pairs:
        if a in text:
            text, owner = apply(text, owner, a, b)
    if ta_ai:
        for i, k in enumerate(ta_keep):
            text, owner = apply(text, owner, k, f"\x00{i}\x00")
        text, owner = apply(text, owner, "他", "它")
        text, owner = apply(text, owner, "其它", "其他")
        for i, k in enumerate(ta_keep):
            text, owner = apply(text, owner, f"\x00{i}\x00", k)
    # 摊回词:每个原词收自己 owner 的字符
    buf = {i: "" for i in range(len(words))}
    for ch, o in zip(text, owner):
        buf[o] += ch
    out = []
    for i, (w, s, e) in enumerate(words):
        if buf[i]:
            out.append({"w": buf[i], "s": round(s, 3), "e": round(e, 3), "emph": False})
    # emphasis:纠错后全文匹配,命中区间内的词标 emph
    full = "".join(o["w"] for o in out)
    starts = []
    pos = 0
    for o in out:
        starts.append(pos)
        pos += len(o["w"])
    for kw in emphasis:
        idx = 0
        while True:
            j = full.find(kw, idx)
            if j < 0: break
            for wi, st in enumerate(starts):
                if st < j + len(kw) and st + len(out[wi]["w"]) > j:
                    out[wi]["emph"] = True
            idx = j + len(kw)
    return out


def main(cfg_path, out_path, window=None):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    cfg = json.load(open(cfg_path))
    WD = cfg["workdir"].rstrip("/") + "/"
    base = json.load(open(os.path.join(os.path.dirname(__file__), "..", "reference", "corrections.json")))
    pairs = [tuple(x) for x in base] + [tuple(x) for x in cfg.get("corrections", [])]
    words = json.load(open(WD + "cap_words.json"))
    segs = json.load(open(WD + "cap_segs.json"))
    end = segs[-1][1]
    lo, hi = (0.0, end) if not window else window
    ww = [(w, s, e) for w, s, e in words if lo <= s < hi]
    out_words = corrected_words(ww, pairs, cfg.get("ta", "ai") != "human", cfg.get("ta_keep", []), cfg.get("emphasis", []))
    # 断句分页:唯一实现在 caption_pages.py(S5,烧录与 Remotion 共用,别在这重写规则)
    from caption_pages import merge_latin, mark_breaks
    out_words = mark_breaks(merge_latin(out_words, segs), maxc=30)
    for o in out_words:
        o["s"] = round(o["s"] - lo, 3); o["e"] = round(o["e"] - lo, 3)
    # 卡片:用和 overlays 同逻辑的锚点解析(fix 后 seg 文本)
    from common import build_fix
    fix = build_fix(cfg)
    def anchor_time(anchor, at):
        for s, e, t in segs:
            if anchor and anchor in fix(t): return s
        return at
    cards = []
    for tx in cfg.get("overlay", {}).get("texts", []):
        at = anchor_time(tx.get("anchor"), tx.get("at", 0))
        if not (lo <= at < hi): continue
        cards.append({"title": tx.get("title") or tx.get("header", ""),
                      "sub": tx.get("sub", []) or ([tx.get("body", "")] if tx.get("body") else []),
                      "start": round(at - lo, 2), "hold": tx.get("hold", 4.0)})
    props = {"src": "sample.mp4", "words": out_words, "cards": cards,
             "durationSec": round(hi - lo, 2)}
    json.dump(props, open(out_path, "w"), ensure_ascii=False)
    print(f"props: 词 {len(out_words)} 卡 {len(cards)} 时长 {props['durationSec']}s → {out_path}")


if __name__ == "__main__":
    win = None
    if "--window" in sys.argv:
        i = sys.argv.index("--window")
        lo, hi = sys.argv[i + 1].split(",")
        win = (float(lo), float(hi))
    main(sys.argv[1], sys.argv[2], win)
