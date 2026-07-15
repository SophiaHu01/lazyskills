#!/usr/bin/env python3
"""文本锚点蒙太奇构建(2026-07-12):按「锚句」而非秒数拼片段——结构上杜绝手写坐标的错。

教训背景:开头试剪曾凭记忆手写旧时间轴秒数,落点接错句还切了尾音。本工具强制坐标来自
transcript.lock 的文本查询;渲染后自动 remap 字幕并做「插段区窜词=0 / 尾段文本=预期」校验。

用法: montage_build.py <config.json> <montage.json> <out.mp4>
montage.json 示例:
  {"base": "成品底片.mp4",
   "pieces": [
     {"from_text": "我不信这个世界上", "to_text": "像这样子问它"},   ← base 段:锚句起止(含整段)
     {"insert": "智能配速演示v2.mp4", "from": 0, "dur": 9.5},        ← 插段(静音)
     {"from_text": "发给它", "to_text": "非常完整的回答"}
   ],
   "expect_tail": "非常完整的回答"}                                  ← 交付校验:末段字幕须含此文本
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def seg_span(lk, kw_from, kw_to):
    s0 = e0 = None
    for s, e, t in lk["segs"]:
        if kw_from in t and s0 is None:
            s0 = s
        if s0 is not None and kw_to in t:
            e0 = e
            break
    if s0 is None or e0 is None:
        raise SystemExit(f"❌ 锚句未找到: {kw_from} → {kw_to}(检查 transcript.lock 文本)")
    return s0, e0


def main(cfg_path, spec_path, out):
    cfg = json.load(open(cfg_path))
    wd = cfg["workdir"].rstrip("/") + "/"
    lk = json.load(open(wd + "transcript.lock.json"))
    spec = json.load(open(spec_path))
    base = spec["base"] if os.path.isabs(spec["base"]) else wd + spec["base"]
    # 防呆闸(验收员发现的隐患):锁若已被 remap 到别的时间轴,锚句坐标会剪错画面而文字校验仍自洽。
    # 锁时长必须与底片时长一致(±0.5s),否则要求先从源 cap_* 重新 lock 或恢复 transcript.lock.prev.json。
    bdur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", base], capture_output=True, text=True).stdout.strip())
    if abs(lk.get("duration", 0) - bdur) > 0.5:
        raise SystemExit(f"❌ 锁时长 {lk.get('duration')}s ≠ 底片时长 {bdur:.1f}s——锁描述的不是这条底片。"
                         f"先重新 lock(源 cap_*)或恢复 transcript.lock.prev.json 再跑。")

    fc, labs, pmap, t_new = [], [], [], 0.0
    inputs = ["-i", base]
    fidx = {base: 0}
    quiet = []
    for i, p in enumerate(spec["pieces"]):
        if "insert" in p:
            f = p["insert"] if os.path.isabs(p["insert"]) else wd + p["insert"]
            if f not in fidx:
                fidx[f] = len(fidx)
                inputs += ["-i", f]
            s, d = p.get("from", 0.0), p["dur"]
            fc.append(f"[{fidx[f]}:v]trim={s}:{s + d},setpts=PTS-STARTPTS,fps=30,setsar=1[v{i}]")
            fc.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{d}[a{i}]")
            pmap.append({"new_s": round(t_new, 3), "new_e": round(t_new + d, 3), "kind": "screen"})
            quiet.append((round(t_new, 1), round(t_new + d, 1)))
        else:
            s, e = seg_span(lk, p["from_text"], p["to_text"])
            d = e - s
            fc.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,fps=30,setsar=1[v{i}]")
            fc.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,aresample=48000[a{i}]")
            pmap.append({"new_s": round(t_new, 3), "new_e": round(t_new + d, 3),
                         "kind": "base", "old_s": s, "old_e": e})
            print(f"  base「{p['from_text'][:8]}…{p['to_text'][-6:]}」= {s:.2f}-{e:.2f}")
        labs.append(f"[v{i}][a{i}]")
        t_new += d
    fc.append("".join(labs) + f"concat=n={len(spec['pieces'])}:v=1:a=1[vo][ao]")
    fcf = wd + "montage_fc.txt"
    open(fcf, "w").write(";".join(fc))
    json.dump(pmap, open(wd + "piece_map.json", "w"))
    r = subprocess.run(["ffmpeg", "-y", "-v", "error"] + inputs +
                       ["-filter_complex_script", fcf, "-map", "[vo]", "-map", "[ao]",
                        "-c:v", "libx264", "-crf", "19", "-preset", "veryfast",
                        "-c:a", "aac", out], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-400:])
        sys.exit(1)
    # 字幕跟随:锁 remap 到新时间轴
    from transcript_lock import _mapper_from_pieces, _remap
    m, end = _mapper_from_pieces(wd + "piece_map.json")
    _remap(wd, m, end, write_lock=True)
    # 交付校验:插段区窜词 / 尾段文本
    words = json.load(open(wd + "cap_words.json"))
    stray = [w for w, s, e in words if any(a + 0.1 < s < b - 0.1 for a, b in quiet)]
    tail = "".join(w for w, s, e in words if s >= (pmap[-1]["new_s"] if pmap else 0))
    ok_tail = spec.get("expect_tail", "") in tail if spec.get("expect_tail") else True
    print(f"蒙太奇 {t_new:.1f}s | 插段区窜词 {len(stray)} | 尾段校验 {'✅' if ok_tail else '❌ ' + tail[:30]}")
    print(f"静默区(给 selfcheck --quiet-zones): {','.join(f'{a}-{b}' for a, b in quiet)}")
    if stray or not ok_tail:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
