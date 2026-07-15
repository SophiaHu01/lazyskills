#!/usr/bin/env python3
"""edit —— 一键编排器:一条命令把口播视频从素材跑到定稿,挂了能从任意 stage 续跑。

用法:
    python3 edit.py <config.json>                # 从头跑到定稿(用户批注完终稿后的一键出片)
    python3 edit.py <config.json> --from cut      # 从某 stage 续跑(改了配置后只重跑尾巴)
    python3 edit.py <config.json> --to cut        # 跑到某 stage 停(比如先看剪辑方案再往下)
    python3 edit.py <config.json> --only subtitle # 只跑某一步
    python3 edit.py <config.json> --resume        # 从 .state.json 里第一个没完成的 stage 接着跑
    python3 edit.py <config.json> --list          # 只列本配置的 stage 计划,不跑

stage(按模式):
    拼接模式: assemble → transcribe → cut → cutlock → subtitle → audio → deliver
    单片模式:            transcribe → cut → cutlock → subtitle → audio → deliver

设计:开跑前 vconfig 先校验素材齐全(缺则一次性全列出);.state.json 记已完成 stage;
--from 时前置产物必须已存在,否则明确报「要从 X 续跑得先有 Y」。
"""
import sys, os, json, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vconfig import load, check_inputs

PY = sys.executable


def _p(WD, name):
    return WD + name


# stage 表。needs=开跑前必须存在的输入产物;makes=产出物(用于 --resume 判完成)。
# cmd 用配置路径调各 stage 脚本(每个脚本自己 vconfig.load,保持可单独跑)。
STAGES = [
    {"key": "assemble", "title": "拼接源片", "modes": {"assemble"},
     "cmd": lambda c, WD, CP: [PY, f"{HERE}/assemble.py", CP],
     "needs": lambda c, WD: [],  # clips/script 由 check_inputs 统一校验
     "makes": lambda c, WD: [c["video"]]},
    {"key": "transcribe", "title": "转录源", "modes": {"assemble", "single"},
     "cmd": lambda c, WD, CP: [PY, f"{HERE}/transcribe.py", c["video"], _p(WD, "src")],
     "needs": lambda c, WD: [("源片", c["video"])],
     "makes": lambda c, WD: [_p(WD, "src_words.json"), _p(WD, "src_sents.json")]},
    {"key": "cut", "title": "剪辑方案", "modes": {"assemble", "single"},
     "cmd": lambda c, WD, CP: [PY, f"{HERE}/cut.py", CP],
     "needs": lambda c, WD: [("源片", c["video"]), ("转录", _p(WD, "src_words.json")), ("转录", _p(WD, "src_sents.json"))],
     "makes": lambda c, WD: [_p(WD, "cutplan.json")]},
    {"key": "cutlock", "title": "定剪+转录成片", "modes": {"assemble", "single"},
     "cmd": lambda c, WD, CP: [PY, f"{HERE}/build.py", CP, "--cut-only"],
     "needs": lambda c, WD: [("源片", c["video"]), ("剪辑方案", _p(WD, "cutplan.json"))],
     "makes": lambda c, WD: [_p(WD, "cut_locked.mp4"), _p(WD, "cap_words.json"), _p(WD, "cap_segs.json")]},
    {"key": "subtitle", "title": "字幕+overlay", "modes": {"assemble", "single"},
     "cmd": lambda c, WD, CP: [PY, f"{HERE}/build.py", CP],
     "needs": lambda c, WD: [("定剪成片", _p(WD, "cut_locked.mp4")), ("剪辑方案", _p(WD, "cutplan.json")),
                             ("成片转录", _p(WD, "cap_words.json")), ("成片转录", _p(WD, "cap_segs.json"))],
     "makes": lambda c, WD: [_p(WD, "final.mp4")]},
    {"key": "audio", "title": "AI 音频", "modes": {"assemble", "single"},
     "cmd": lambda c, WD, CP: [PY, f"{HERE}/enhance_audio.py", CP],
     "needs": lambda c, WD: [("字幕成片", _p(WD, "final.mp4"))],
     "makes": lambda c, WD: [_p(WD, c["title"] + "_定稿.mp4")]},
    {"key": "deliver", "title": "交付", "modes": {"assemble", "single"},
     "cmd": lambda c, WD, CP: [PY, f"{HERE}/deliver.py", CP],
     "needs": lambda c, WD: [("定稿", _p(WD, c["title"] + "_定稿.mp4"))],
     "makes": lambda c, WD: [_p(WD, c["title"] + "_压缩.mp4")]},
]


def plan_stages(cfg):
    return [s for s in STAGES if cfg["_mode"] in s["modes"]]


def load_state(WD):
    p = _p(WD, ".state.json")
    if os.path.exists(p):
        try:
            return json.load(open(p))
        except Exception:
            pass
    return {"done": [], "stages": {}}


def save_state(WD, st):
    json.dump(st, open(_p(WD, ".state.json"), "w"), ensure_ascii=False, indent=2)


def die(msg):
    print("❌ " + msg)
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cfgpath = os.path.abspath(os.path.expanduser(sys.argv[1]))
    args = sys.argv[2:]

    def flagval(name):
        return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else None

    frm = flagval("--from")
    to = flagval("--to")
    only = flagval("--only")
    do_resume = "--resume" in args
    do_list = "--list" in args

    cfg = load(cfgpath)
    WD = cfg["workdir"]
    stages = plan_stages(cfg)
    keys = [s["key"] for s in stages]

    print(f"配置: {cfgpath}")
    print(f"模式: {cfg['_mode']}  ·  title: {cfg.get('title')}  ·  workdir: {WD}")
    print("stage 计划: " + " → ".join(f"{s['title']}({s['key']})" for s in stages))

    if do_list:
        return

    for name in (only, frm, to):
        if name and name not in keys:
            die(f"未知 stage: {name}。本模式可用: {', '.join(keys)}")

    # 选定要跑的子区间 [lo, hi]
    st = load_state(WD)
    if only:
        lo = hi = keys.index(only)
    else:
        if frm:
            lo = keys.index(frm)
        elif do_resume:
            lo = next((i for i, k in enumerate(keys) if k not in st.get("done", [])), len(keys))
            if lo == len(keys):
                print("✅ .state 显示全部 stage 已完成,无需续跑(要重跑用 --from)")
                return
            print(f"续跑: 从第一个未完成 stage「{stages[lo]['title']}」开始")
        else:
            lo = 0
        hi = keys.index(to) if to else len(keys) - 1
    if lo > hi:
        die(f"--from({frm}) 在 --to({to}) 之后,空区间")

    os.makedirs(WD, exist_ok=True)

    # 素材校验(始终):缺输入素材一次性全列出
    probs = check_inputs(cfg)
    if probs:
        print("\n开跑前校验不通过,先补齐再跑:")
        for p in probs:
            print("  -", p)
        # 拼接模式下 video(assembled.mp4)是产物不是素材,check_inputs 已跳过,这里的 probs 都是真缺的素材
        sys.exit(1)

    # 续跑前置产物校验:起点 stage 的 needs 必须已存在
    start = stages[lo]
    miss = [(lbl, pth) for lbl, pth in start["needs"](cfg, WD) if not os.path.exists(pth)]
    if lo > 0 and miss:
        print(f"\n要从「{start['title']}」续跑,但缺前置产物(得先从更早的 stage 跑):")
        for lbl, pth in miss:
            print(f"  - {lbl}: {pth}")
        sys.exit(1)

    # 逐 stage 跑
    print()
    for i in range(lo, hi + 1):
        s = stages[i]
        print(f"━━━ [{i - lo + 1}/{hi - lo + 1}] {s['title']} ({s['key']}) ━━━")
        cmd = s["cmd"](cfg, WD, cfgpath)
        r = subprocess.run(cmd)
        if r.returncode != 0:
            print(f"\n❌ stage「{s['title']}」失败(退出码 {r.returncode})。已跑到这里,修好后 --from {s['key']} 续跑。")
            save_state(WD, st)
            sys.exit(r.returncode)
        # 产物校验:声称成功但产物没出来 = 也算失败(wired≠working)
        made = s["makes"](cfg, WD)
        gone = [p for p in made if not os.path.exists(p)]
        if gone:
            print(f"\n❌ stage「{s['title']}」返回 0 但产物缺失:")
            for p in gone:
                print("  -", p)
            print(f"修好后 --from {s['key']} 续跑。")
            save_state(WD, st)
            sys.exit(1)
        if s["key"] not in st["done"]:
            st["done"].append(s["key"])
        st["stages"][s["key"]] = {"at": time.strftime("%Y-%m-%d %H:%M:%S")}
        save_state(WD, st)

    last = stages[hi]
    print(f"\n✅ 跑完到「{last['title']}」。")
    if last["key"] == "deliver":
        print(f"   定稿: {_p(WD, cfg['title'] + '_定稿.mp4')}")
        print(f"   压缩预览: {_p(WD, cfg['title'] + '_压缩.mp4')}")


if __name__ == "__main__":
    main()
