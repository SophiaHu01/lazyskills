#!/usr/bin/env python3
"""S1 转录锁定:转录一次→纠错→锁定为唯一真相源,之后剪辑靠映射推算,永不重转。

为什么(2026-07-12 硬化):whisper 每轮转录换着法子出错(同一人名出过 巴扬/巴尤/巴奥),
纠错表被迫涨到 49 条,每渲一轮全文重扫——打地鼠打不完。锁定后地鼠窝直接拆掉。

用法:
  transcript_lock.py lock <config.json> [--from src|cap]     # 纠错并锁定(默认 src_*)
  transcript_lock.py remap-cutplan <config.json>             # 按 cutplan(kept+speeds) 推算 cap_*
  transcript_lock.py remap-pieces <config.json> <piece_map>  # 按重构 piece_map 推算并更新锁
锁文件: workdir/transcript.lock.json  {video, duration, words:[[w,s,e]..], segs:[[s,e,txt]..]}
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from remotion_props import corrected_words  # 词级纠错摊回(全文拼串→顺序replace→按字符对齐摊回)


def _load(cfg_path):
    cfg = json.load(open(cfg_path))
    wd = cfg["workdir"].rstrip("/") + "/"
    return cfg, wd


def _pairs(cfg):
    base = json.load(open(os.path.join(os.path.dirname(__file__), "..", "reference", "corrections.json")))
    return [tuple(x) for x in base] + [tuple(x) for x in cfg.get("corrections", [])]


def lock(cfg_path, src_prefix="src"):
    cfg, wd = _load(cfg_path)
    words = json.load(open(wd + f"{src_prefix}_words.json"))
    segs = json.load(open(wd + f"{src_prefix}_segs.json"))
    cw = corrected_words([tuple(w) for w in words], _pairs(cfg),
                         cfg.get("ta", "ai") != "human", cfg.get("ta_keep", []), [])
    lw = [[o["w"], o["s"], o["e"]] for o in cw]
    # segs 文本同样纠错(用 build_fix,和烧字幕一致)
    from common import build_fix
    fix = build_fix(cfg)
    ls = [[round(s, 3), round(e, 3), fix(t).strip()] for s, e, t in segs]
    out = {"video": cfg.get("video", ""), "duration": ls[-1][1] if ls else 0,
           "words": lw, "segs": ls}
    json.dump(out, open(wd + "transcript.lock.json", "w"), ensure_ascii=False)
    print(f"锁定: 词 {len(lw)} 段 {len(ls)} 时长 {out['duration']}s → transcript.lock.json")


def _make_mapper(table):
    """table=[(old_s,old_e,new_s,scale)];m(t,side):端点落在被剪窗口时吸附到剪口边界——
    side='s' 吸到下一保留段头,side='e' 吸到上一保留段尾(2026-07-13 修:坍缩丢词 bug,
    「这个内容」尾巴压在0.5s静默刀上整段字幕消失,自检抓出)。"""
    def m(t, side=None):
        for s, e, ns, sp in table:
            if s <= t <= e:
                return ns + (t - s) / sp
        if side == "s":
            nxt = [x for x in table if x[0] >= t]
            if nxt:
                s, e, ns, sp = min(nxt, key=lambda x: x[0])
                return ns
        if side == "e":
            prv = [x for x in table if x[1] <= t]
            if prv:
                s, e, ns, sp = max(prv, key=lambda x: x[1])
                return ns + (e - s) / sp
        return None
    return m


def _mapper_from_cutplan(wd):
    cp = json.load(open(wd + "cutplan.json"))
    kept = cp["kept"]
    speeds = cp.get("seg_speeds") or [cp["speed"]] * len(kept)
    table = []
    acc = 0.0
    for (s, e), sp in zip(kept, speeds):
        table.append((s, e, acc, sp))
        acc += (e - s) / sp
    return _make_mapper(table), acc


def _mapper_from_pieces(pmap_path):
    pmap = json.load(open(pmap_path))
    table = [(p["old_s"], p["old_e"], p["new_s"], 1.0) for p in pmap if p["kind"] == "base"]
    end = max(p["new_e"] for p in pmap)
    return _make_mapper(table), end


def remap_cutplan(wd):
    """render_cut 后调:按 cutplan 推算 cap_* 并同步更新锁(锁与 cut_locked 时间轴配套,
    供后续 montage_build 直接使用;旧锁自动存 transcript.lock.prev.json)。"""
    wd = wd.rstrip("/") + "/"
    m, end = _mapper_from_cutplan(wd)
    _remap(wd, m, end, write_lock=True)


def _remap(wd, mapper, end, write_lock):
    wd = wd.rstrip("/") + "/"
    lk = json.load(open(wd + "transcript.lock.json"))
    words, segs = [], []
    for w, s, e in lk["words"]:
        ns, ne = mapper(s, "s"), mapper(e, "e")
        if ns is None or ne is None or ne - ns < 0.02:
            continue
        words.append([w, round(ns, 3), round(ne, 3)])
    for s, e, t in lk["segs"]:
        ns, ne = mapper(s, "s"), mapper(e, "e")
        if ns is None or ne is None or ne - ns < 0.1 or not t:
            continue
        segs.append([round(ns, 3), round(ne, 3), t])
    json.dump(words, open(wd + "cap_words.json", "w"), ensure_ascii=False)
    json.dump(segs, open(wd + "cap_segs.json", "w"), ensure_ascii=False)
    json.dump([s for s, e, _ in segs] + ([segs[-1][1]] if segs else []),
              open(wd + "cap_sents.json", "w"))
    if write_lock:
        # 覆盖前留上一版(重剪迭代要回到源时间轴时用,防丢)
        if os.path.exists(wd + "transcript.lock.json"):
            os.replace(wd + "transcript.lock.json", wd + "transcript.lock.prev.json")
        json.dump({"video": "", "duration": round(end, 3), "words": words, "segs": segs},
                  open(wd + "transcript.lock.json", "w"), ensure_ascii=False)
    print(f"映射推算: 词 {len(words)} 段 {len(segs)} 新时长 {end:.1f}s → cap_*"
          + (" + 锁已更新" if write_lock else ""))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "lock":
        pre = "cap" if "--from" in sys.argv and "cap" in sys.argv else "src"
        lock(sys.argv[2], pre)
    elif cmd == "remap-cutplan":
        cfg, wd = _load(sys.argv[2])
        remap_cutplan(wd)
    elif cmd == "remap-pieces":
        cfg, wd = _load(sys.argv[2])
        m, end = _mapper_from_pieces(sys.argv[3])
        _remap(wd, m, end, write_lock=True)
    else:
        raise SystemExit("用法见文件头")
