#!/usr/bin/env python3
"""金标准:证明拆分后的 build.py 流水线与旧生产版逐字节一致(成片效果不变)。

做法:把生产 fixture work2 拷到 scratchpad 副本上跑(别碰原 work2 的旧标准),
monkeypatch subprocess(不真跑 ffmpeg/transcribe,只记 argv,让 .txt/PNG 照常落盘),
逐项 diff:fc.txt / fcf.txt / compose 的 ffmpeg argv / ov 下每个 PNG 字节。

跑法:  python3 _golden_test.py
"""
import sys, os, json, shutil, subprocess, filecmp

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

GOLDEN_WORK_SRC = "examples/golden/work"  # TODO: 随样例素材包提供
CONFIG_SRC = "examples/golden/config.json"
SCRATCH = "/tmp/videoedit_golden"

CALLS = []


class FakeCompleted:
    def __init__(self, args):
        self.args = args
        self.returncode = 0
        self.stdout = ""
        self.stderr = ""


def fake_run(args, **kwargs):
    CALLS.append(list(args))
    return FakeCompleted(args)


def expected_compose_argv(WD, items):
    """按旧 build.py(lines 196-203)的公式独立重建 compose 的 ffmpeg argv。"""
    inp = ["-i", WD + "cut_locked.mp4"]
    for it in items:
        inp += ["-i", it[0]]
    last = f"o{len(items)-1}"
    return (["ffmpeg", "-y"] + inp
            + ["-filter_complex_script", WD + "fcf.txt", "-map", f"[{last}]", "-map", "0:a",
               "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-c:a", "copy", WD + "final.mp4"])


def main():
    results = []  # (name, ok, detail)

    # 1. 拷 fixture 到 scratchpad 副本(别在原 work2 上跑)
    dst_work = os.path.join(SCRATCH, "golden_work")
    if os.path.exists(dst_work):
        shutil.rmtree(dst_work)
    shutil.copytree(GOLDEN_WORK_SRC, dst_work)
    WD = dst_work.rstrip("/") + "/"

    # 拷 config,把 workdir 指到副本
    with open(CONFIG_SRC) as f:
        cfg_raw = json.load(f)
    cfg_raw["workdir"] = WD
    dst_config = os.path.join(SCRATCH, "config_golden.json")
    with open(dst_config, "w") as f:
        json.dump(cfg_raw, f, ensure_ascii=False)

    # 2. monkeypatch subprocess.run(render 里通过 subprocess.run 调用)
    import render, build
    subprocess.run = fake_run  # render 用的是 subprocess.run(模块属性),这里换掉

    # 3a. cut-only: 跑 render_cut → 副本生成 fc.txt
    cfg = build.load(dst_config)
    CALLS.clear()
    render.render_cut(cfg)

    # 3b. 全流程: caption + overlay + compose → 副本生成 fcf.txt + ov/*.png,并捕获 items
    CALLS.clear()
    out = build.main([sys.argv[0], dst_config])
    compose_argv = CALLS[-1] if CALLS else None  # compose 是最后一个 subprocess 调用

    # 4. 逐项 diff
    # --- fc.txt ---
    with open(WD + "fc.txt") as f:
        new_fc = f.read()
    with open(GOLDEN_WORK_SRC + "/fc.txt") as f:
        old_fc = f.read()
    ok = new_fc == old_fc
    results.append(("fc.txt", ok, "一致" if ok else f"差异!\n新:{new_fc!r}\n旧:{old_fc!r}"))

    # --- fcf.txt ---
    with open(WD + "fcf.txt") as f:
        new_fcf = f.read()
    with open(GOLDEN_WORK_SRC + "/fcf.txt") as f:
        old_fcf = f.read()
    ok = new_fcf == old_fcf
    if ok:
        detail = "一致"
    else:
        # 定位首个不同字符
        n = min(len(new_fcf), len(old_fcf))
        pos = next((i for i in range(n) if new_fcf[i] != old_fcf[i]), n)
        detail = (f"差异! len 新{len(new_fcf)} 旧{len(old_fcf)} 首异@{pos}\n"
                  f"新…{new_fcf[max(0,pos-40):pos+40]!r}\n旧…{old_fcf[max(0,pos-40):pos+40]!r}")
    results.append(("fcf.txt", ok, detail))

    # --- compose 的 ffmpeg argv ---
    exp_argv = expected_compose_argv(WD, out["items"])
    ok = compose_argv == exp_argv
    if ok:
        detail = f"一致(共 {len(compose_argv)} 段, {out['items'].__len__()} 个 PNG 输入按序)"
    else:
        # 找第一个不同
        m = min(len(compose_argv or []), len(exp_argv))
        pos = next((i for i in range(m) if compose_argv[i] != exp_argv[i]), m)
        detail = (f"差异! @{pos}\n新:{(compose_argv or [])[max(0,pos-2):pos+3]}\n"
                  f"期望:{exp_argv[max(0,pos-2):pos+3]}")
    results.append(("compose ffmpeg argv", ok, detail))

    # 额外自检:compose argv 里的 -i 输入顺序 == cut_locked + items 路径
    got_inputs = [compose_argv[i+1] for i, a in enumerate(compose_argv or []) if a == "-i"]
    exp_inputs = [WD + "cut_locked.mp4"] + [it[0] for it in out["items"]]
    ok2 = got_inputs == exp_inputs
    results.append(("compose -i 输入顺序(PNG 叠放顺序)", ok2,
                    "一致" if ok2 else f"差异! 新{got_inputs[:4]}… 期望{exp_inputs[:4]}…"))

    # --- ov/*.png 逐字节 ---
    old_ov = GOLDEN_WORK_SRC + "/ov"
    new_ov = WD + "ov"
    old_files = sorted(os.listdir(old_ov))
    new_files = sorted(os.listdir(new_ov))
    set_ok = old_files == new_files
    if not set_ok:
        only_old = sorted(set(old_files) - set(new_files))
        only_new = sorted(set(new_files) - set(old_files))
        results.append(("ov 文件集合", False, f"不一致! 仅旧有:{only_old} 仅新有:{only_new}"))
    else:
        results.append(("ov 文件集合", True, f"一致(共 {len(old_files)} 个)"))

    byte_mismatch = []
    size_mismatch = []
    from PIL import Image
    for name in sorted(set(old_files) & set(new_files)):
        op = os.path.join(old_ov, name)
        np = os.path.join(new_ov, name)
        if filecmp.cmp(op, np, shallow=False):
            continue
        byte_mismatch.append(name)
        try:
            so = Image.open(op).size
            sn = Image.open(np).size
            if so != sn:
                size_mismatch.append((name, so, sn))
        except Exception as ex:
            size_mismatch.append((name, "err", str(ex)))
    common_n = len(set(old_files) & set(new_files))
    if not byte_mismatch:
        results.append(("ov PNG 逐字节", True, f"全部 {common_n} 个 PNG 字节一致"))
    else:
        # 降级:字节不同但 size 相同 → 报告降级为 size 比对
        size_all_ok = all(name not in [m[0] for m in size_mismatch] for name in byte_mismatch)
        detail = f"{len(byte_mismatch)}/{common_n} 字节不同: {byte_mismatch[:20]}"
        if size_mismatch:
            detail += f"\n  其中 size 也不同(真差异): {size_mismatch}"
        else:
            detail += "\n  但所有 size 相同 → 疑似 Pillow 版本像素微差(降级为 size 比对通过)"
        results.append(("ov PNG 逐字节", False, detail))

    # 5. 汇总
    print("\n" + "=" * 70)
    print("金标准 diff 结果")
    print("=" * 70)
    all_pass = True
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"[{mark}] {name}: {detail}")
    print("=" * 70)
    print(f"字幕数 capev={len(out['capev'])}  overlay plan={len(out['plan'])}  items={len(out['items'])}")
    print("全部通过 ✅ 字节一致,效果不变已证" if all_pass else "有项未通过 ❌ 见上")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
