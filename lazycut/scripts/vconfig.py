#!/usr/bin/env python3
"""vconfig —— 配置的唯一真相源:加载 + 校验 + 模式自动判断 + 默认填充。

所有 stage 脚本都从这里拿 config(别再各自 json.load + 各填各的默认)。

用法(库):
    from vconfig import load, check_inputs
    cfg = load("config.json")          # 归一后的 dict,含 _mode/_configpath
用法(CLI 自检,不跑任何 stage,只校验并打印归一后的配置):
    python3 vconfig.py config.json

设计约定:
- 默认值和老脚本里内联的 .get(...,默认) 逐一对齐(见 DEFAULTS),保证成片效果不变。
- silence_mode 按模式给默认:拼接=off、单片=aggressive;显式写了就用显式的。
- 只校验"必须先存在的输入素材"(源片/脚本/overlay 图),不校验流水线产出物(assembled/final/定稿)——那些由 edit.py 按 stage 检查。
"""
import sys, json, os

# 与老脚本内联默认逐一对齐(cut.py / build.py / enhance_audio.py)——别改数,改了成片就变
DEFAULTS = {
    "speed": 1.0,          # cut.py/build.py: 不提速(用户嫌快)
    "silence_db": -30,     # cut.py: 静音检测阈值
    "keep_sent": 0.26,     # cut.py: 句子/话题前留的话口
    "keep_mid": 0.11,      # cut.py: 句内小停顿收紧到
    "filler_words": ["然后"],
    "audio": "ai",         # enhance_audio.py: ClearVoice 播客级
    "end_keep": None,      # cut.py: 结尾停在哪句(None=自动到最后一个词后)
}


def _expand(p):
    return os.path.expanduser(p) if isinstance(p, str) and p else p


def _detect_mode(raw):
    """有非空 assemble.clips → 拼接模式;否则单片模式。"""
    asm = raw.get("assemble")
    if isinstance(asm, dict) and asm.get("clips"):
        return "assemble"
    return "single"


def load(path):
    """读 config → 归一(展开 ~ / 判模式 / 填默认) → 返回 dict。不产生任何副作用(不建目录、不写文件)。"""
    path = os.path.abspath(os.path.expanduser(path))
    with open(path) as f:
        cfg = json.load(f)

    mode = _detect_mode(cfg)
    cfg["_mode"] = mode
    cfg["_configpath"] = path

    # 路径展开 ~
    for k in ("video", "workdir"):
        if cfg.get(k):
            cfg[k] = _expand(cfg[k])
    if cfg.get("workdir"):
        cfg["workdir"] = cfg["workdir"].rstrip("/") + "/"

    asm = cfg.get("assemble") or {}
    for c in asm.get("clips", []):
        c["file"] = _expand(c.get("file"))
    if asm.get("script_xml"):
        asm["script_xml"] = _expand(asm["script_xml"])

    ov = cfg.get("overlay") or {}
    for lg in ov.get("logos", []):
        lg["files"] = [_expand(f) for f in lg.get("files", [])]
    if ov.get("card"):
        ov["card"] = _expand(ov["card"])
    dv = cfg.get("deliver") or {}
    for k in ("desktop_dir", "snapshot_dir"):
        if dv.get(k):
            dv[k] = _expand(dv[k])

    # 拼接模式:video 默认 = assemble 产出的 <workdir>/assembled.mp4
    if mode == "assemble" and not cfg.get("video") and cfg.get("workdir"):
        cfg["video"] = cfg["workdir"] + "assembled.mp4"

    # 填默认(不覆盖显式值)
    for k, v in DEFAULTS.items():
        cfg.setdefault(k, v)
    # silence_mode 按模式给默认
    if "silence_mode" not in cfg:
        cfg["silence_mode"] = "off" if mode == "assemble" else "aggressive"

    return cfg


def check_inputs(cfg):
    """返回一份人话的问题清单(空 = 通过)。只查'开跑前必须存在的输入',不查产出物。"""
    problems = []
    mode = cfg["_mode"]

    if not cfg.get("workdir"):
        problems.append("缺 workdir(工作目录)")
    if not cfg.get("title"):
        problems.append("缺 title(视频名)")

    if mode == "assemble":
        asm = cfg.get("assemble") or {}
        clips = asm.get("clips", [])
        if not clips:
            problems.append("拼接模式但 assemble.clips 为空")
        for c in clips:
            f = c.get("file")
            if not f or not os.path.exists(f):
                problems.append(f"源片不存在: {c.get('name','?')} → {f}")
        sx = asm.get("script_xml")
        if sx and not os.path.exists(sx):
            problems.append(f"终稿 xml 不存在: {sx}")
        if not sx and not asm.get("script_lines"):
            problems.append("拼接模式缺终稿来源(script_xml 或 script_lines 至少给一个)")
    else:
        v = cfg.get("video")
        if not v or not os.path.exists(v):
            problems.append(f"源片(video)不存在: {v}")

    # overlay 图片素材必须存在
    ov = cfg.get("overlay") or {}
    for i, lg in enumerate(ov.get("logos", [])):
        for f in lg.get("files", []):
            if not os.path.exists(f):
                problems.append(f"overlay.logos[{i}] 图片不存在: {f}")
    if ov.get("card") and not os.path.exists(ov["card"]):
        problems.append(f"overlay.card 品牌卡不存在: {ov['card']}")

    return problems


def _summary(cfg):
    ov = cfg.get("overlay") or {}
    lines = [
        f"模式: {cfg['_mode']}",
        f"title: {cfg.get('title')}",
        f"workdir: {cfg.get('workdir')}",
        f"video: {cfg.get('video')}",
        f"silence_mode: {cfg.get('silence_mode')}  speed: {cfg.get('speed')}"
        + (f"  intro_speed: {cfg['intro_speed']}" if cfg.get("intro_speed") else ""),
        f"audio: {cfg.get('audio')}  editorial_cuts: {len(cfg.get('editorial_cuts', []))} 条"
        f"  corrections: {len(cfg.get('corrections', []))} 条",
        f"overlay: logos {len(ov.get('logos', []))} / texts {len(ov.get('texts', []))}"
        + ("  (含老 card 模式)" if ov.get("card") else ""),
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 vconfig.py <config.json>")
        sys.exit(2)
    cfg = load(sys.argv[1])
    print(_summary(cfg))
    probs = check_inputs(cfg)
    if probs:
        print("\n❌ 校验不通过:")
        for p in probs:
            print("  -", p)
        sys.exit(1)
    print("\n✅ 配置校验通过,输入素材齐全")
