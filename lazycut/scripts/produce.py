#!/usr/bin/env python3
"""一键流水线(2026-07-14,省token改造B):project.json 收拢全部决定,一条命令跑全链,
每个 stage 按输入内容哈希缓存——改哪只重跑哪,别的直接跳过。

    produce.py <project.json> [--dry-run] [--assume-current] [--until STAGE]

stages(顺序): montage → speed → captions → cards → mix → check → draft → sheet
  --dry-run        只报告哪些 stage 会跑(哈希比对),不执行
  --assume-current 把当前输入哈希直接记为已完成(接管手工跑过的项目,避免无谓全量重跑)
  --until          跑到某 stage 为止

project.json 形状(参照 workdir60 实例):
  {"workdir":..., "config":"config60.json", "montage":"montage60.json",
   "voice_speed":1.12, "props":"remotion_props.json", "fx":"fx.json",
   "bgm":{"type":"synth_pad","voice_vol":0.11,"lift_vol":0.30},
   "remotion_dir":"<你的remotion工程路径>",
   "template_draft":"<用户的真实草稿目录>", "draft_name":"xxx", "out":"成片名.mp4",
   "gates":{"plan_approved":false}}    ← 计划没批,montage 之后的 stage 一律拒跑

铁则:draft stage 前自动跑 draft_diff,同名草稿有用户的手改→自动换新版本名,绝不覆写。
"""
import hashlib
import json
import os
import subprocess
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)

STAGES = ["montage", "speed", "captions", "cards", "mix", "check", "draft", "sheet"]


def _h(x):
    return hashlib.md5(x if isinstance(x, bytes) else str(x).encode()).hexdigest()[:12]


def _hfile(p):
    if not os.path.exists(p):
        return "missing"
    st = os.stat(p)
    if st.st_size < 512_000:
        return _h(open(p, "rb").read())
    return _h(f"{p}:{st.st_size}:{st.st_mtime_ns}")


def _run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        print(r.stdout[-400:] if r.stdout else "", r.stderr[-600:] if r.stderr else "")
        raise SystemExit(f"❌ stage 命令失败: {' '.join(map(str, cmd[:3]))}…")
    return r


class P:
    def __init__(self, path):
        self.j = json.load(open(path))
        self.wd = self.j["workdir"].rstrip("/") + "/"
        self.state_p = self.wd + ".produce_state.json"
        self.state = json.load(open(self.state_p)) if os.path.exists(self.state_p) else {}

    def cfgp(self, k):
        v = self.j[k]
        return v if os.path.isabs(v) else self.wd + v

    def save(self):
        json.dump(self.state, open(self.state_p, "w"))


def stage_inputs(p, s):
    """每个 stage 的输入指纹:变了才重跑。"""
    j, wd = p.j, p.wd
    if s == "montage":
        spec = json.load(open(p.cfgp("montage")))
        files = [spec["base"]] + [wd + x["insert"] for x in spec["pieces"] if "insert" in x]
        return _h(json.dumps(spec, sort_keys=True) + "".join(_hfile(f) for f in files))
    if s == "speed":
        return _h(str(j.get("voice_speed", 1.0)) + p.state.get("montage", ""))
    if s == "captions":
        c = json.load(open(p.cfgp("config")))
        keys = json.dumps([c.get(k) for k in ("corrections", "emphasis", "ta", "ta_keep",
                                              "subtitle_size", "subtitle_line_chars")], sort_keys=True)
        return _h(keys + p.state.get("speed", ""))
    if s == "cards":
        return _hfile(p.cfgp("props"))
    if s == "mix":
        return _h(json.dumps(j.get("bgm", {}), sort_keys=True) + _hfile(p.cfgp("fx"))
                  + p.state.get("captions", "") + p.state.get("cards", ""))
    if s == "check":
        return p.state.get("mix", "")
    if s == "draft":
        return _h(p.state.get("speed", "") + _hfile(p.cfgp("props")) + j.get("draft_name", ""))
    if s == "sheet":
        return p.state.get("mix", "")
    return ""


def _timeline(p):
    pm = json.load(open(p.wd + "piece_map.json"))
    sp = p.j.get("voice_speed", 1.0)
    voice_end = min((x["new_s"] for x in pm if x["kind"] == "screen"), default=max(x["new_e"] for x in pm))
    end = max(x["new_e"] for x in pm)
    ve, e = voice_end / sp, voice_end / sp + (end - voice_end)
    joints = sorted({round(x["new_s"] / sp if x["new_s"] <= voice_end else ve + x["new_s"] - voice_end, 2)
                     for x in pm} - {0.0})
    return ve, e, joints


def run_stage(p, s):
    j, wd = p.j, p.wd
    if s == "montage":
        _run([sys.executable, f"{SCRIPTS}/montage_build.py", p.cfgp("config"), p.cfgp("montage"),
              wd + "蒙太奇底.mp4"])
    elif s == "speed":
        import render
        pm = json.load(open(wd + "piece_map.json"))
        voice_end = min((x["new_s"] for x in pm if x["kind"] == "screen"),
                        default=max(x["new_e"] for x in pm))
        end = max(x["new_e"] for x in pm)
        json.dump({"kept": [[0, voice_end], [voice_end, end]], "speed": 1.0,
                   "seg_speeds": [j.get("voice_speed", 1.0), 1.0]}, open(wd + "cutplan.json", "w"))
        cfg = json.load(open(p.cfgp("config")))
        cfg["video"] = wd + "蒙太奇底.mp4"
        json.dump(cfg, open(p.cfgp("config"), "w"), ensure_ascii=False, indent=1)
        render.render_cut(cfg)
    elif s == "captions":
        _run([sys.executable, f"{SCRIPTS}/build.py", p.cfgp("config")])
    elif s == "cards":
        # 分段渲染(2026-07-14 立法:动画必须单段独立,用户在剪辑器里才能单独缩放/挪/删;
        # 文件带版本号且旧版不删=秒级回滚)。输入 motion_plan.json {events:[{type,start,hold,props}]}
        plan_p = wd + "motion_plan.json"
        if not os.path.exists(plan_p):
            print("  (无 motion_plan.json,跳过动效)")
            return
        plan = json.load(open(plan_p))
        seg_dir = wd + "动效段/"
        os.makedirs(seg_dir, exist_ok=True)
        LEAD = 0.4   # 每段片头留的进场余量
        canvas = plan.get("canvas", {"width": 1080, "height": 1920})
        manifest = []
        for i, ev in enumerate(plan.get("events", [])):
            k = 1
            while os.path.exists(seg_dir + f"ev{i:02d}_{ev['type']}_v{k}.mov"):
                k += 1
            out = seg_dir + f"ev{i:02d}_{ev['type']}_v{k}.mov"
            dur = LEAD + ev["hold"] + 0.8
            tmp = wd + f".ev{i}.props.json"
            json.dump({"events": [dict(ev, start=LEAD)], "durationSec": round(dur, 2),
                       "width": canvas["width"], "height": canvas["height"]},
                      open(tmp, "w"), ensure_ascii=False)
            _run(["npx", "remotion", "render", "VidMotion", out, f"--props={tmp}",
                  "--codec=prores", "--prores-profile=4444", "--image-format=png",
                  "--pixel-format=yuva444p10le", "--log=error"],
                 cwd=os.path.expanduser(j.get("motion_dir",
                     os.path.join(os.path.dirname(SCRIPTS), "..", "motion"))))
            manifest.append({"file": out, "at": round(ev["start"] - LEAD, 3), "dur": dur,
                             "type": ev["type"]})
            os.remove(tmp)
        json.dump(manifest, open(wd + "动效段manifest.json", "w"), ensure_ascii=False, indent=1)
        print(f"  动效分段渲染 {len(manifest)} 段 → 动效段/(旧版本文件保留,回滚=换回旧文件)")
    elif s == "mix":
        ve, end, _ = _timeline(p)
        b = j.get("bgm", {})
        vv, lv = b.get("voice_vol", 0.11), b.get("lift_vol", 0.30)
        d = end + 0.05
        fc = (f"[1:a][2:a][3:a][4:a]amix=inputs=4:duration=first:normalize=0,"
              f"chorus=0.6:0.9:55:0.35:0.25:2,tremolo=f=0.35:d=0.25,lowpass=f=1600,"
              f"volume='{vv}+{lv - vv}*min(1,max(0,(t-{ve - 0.5})/1.2))':eval=frame,"
              f"afade=t=out:st={end - 1.4}:d=1.4[bed];[0:a][bed]amix=inputs=2:duration=first:normalize=0[a]")
        mani_p = wd + "动效段manifest.json"
        if os.path.exists(mani_p):
            mani = json.load(open(mani_p))
            inputs = ["-i", wd + "final.mp4"]
            for m in mani:
                inputs += ["-i", m["file"]]
            ov = "[0:v]null[v0];"
            for k, m in enumerate(mani):
                at = max(0, m["at"])
                ov += (f"[{k+1}:v]setpts=PTS+{at}/TB[o{k}];"
                       f"[v{k}][o{k}]overlay=0:0:format=auto:enable='between(t,{at},{at+m['dur']})'[v{k+1}];")
            ov = ov.rstrip(";")
            _run(["ffmpeg", "-y", "-v", "error"] + inputs +
                 ["-filter_complex", ov, "-map", f"[v{len(mani)}]", "-map", "0:a",
                  "-c:v", "libx264", "-crf", "19", "-preset", "veryfast", "-c:a", "copy",
                  wd + "带卡.mp4"])
            base_in = wd + "带卡.mp4"
        else:
            base_in = wd + "final.mp4"
        _run(["ffmpeg", "-y", "-v", "error", "-i", base_in,
              "-f", "lavfi", "-i", f"sine=frequency=110:duration={d}",
              "-f", "lavfi", "-i", f"sine=frequency=164.81:duration={d}",
              "-f", "lavfi", "-i", f"sine=frequency=220:duration={d}",
              "-f", "lavfi", "-i", f"sine=frequency=329.63:duration={d}",
              "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
              "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", wd + "带卡带底.mp4"])
        _run([sys.executable, f"{SCRIPTS}/fx_pass.py", wd + "带卡带底.mp4",
              wd + j.get("out", "成片.mp4"), p.cfgp("fx")])
    elif s == "check":
        ve, end, joints = _timeline(p)
        r = subprocess.run([sys.executable, f"{SCRIPTS}/selfcheck.py", wd + j.get("out", "成片.mp4"), wd,
                            "--joints", ",".join(map(str, joints)),
                            "--quiet-zones", f"{ve:.1f}-{end:.1f}"], capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[-1] if r.stdout else "")
        if r.returncode:
            raise SystemExit("❌ 自检未过,停在 check(报告 selfcheck.json)")
    elif s == "draft":
        from capcut_draft import build_draft, DRAFT_ROOT
        import draft_diff
        name = j["draft_name"]
        tgt = os.path.join(DRAFT_ROOT, name)
        if os.path.exists(os.path.join(tgt, "draft_info.gen.json")):
            if draft_diff.main(tgt, p.wd.rstrip("/")) != 0:
                k = 2
                while os.path.exists(os.path.join(DRAFT_ROOT, f"{name}v{k}")):
                    k += 1
                name = f"{name}v{k}"
                print(f"⚠ 同名草稿有用户的手改,换新名: {name}")
        pm = json.load(open(wd + "piece_map.json"))
        spec = json.load(open(p.cfgp("montage")))
        inserts = [x["insert"] for x in spec["pieces"] if "insert" in x]
        clips, ii = [], 0
        for x in pm:
            if x["kind"] == "base":
                clips.append({"path": spec["base"], "s": x["old_s"], "e": x["old_e"],
                              "speed": j.get("voice_speed", 1.0)})
            else:
                clips.append({"path": wd + inserts[ii], "s": 0.0, "e": x["new_e"] - x["new_s"],
                              "speed": 1.0})
                ii += 1
        caps = [(s, e, t) for s, e, t in json.load(open(wd + "cap_segs.json"))]
        cards = json.load(open(p.cfgp("props")))["cards"]
        build_draft(os.path.expanduser(j["template_draft"]), name, clips, caps, cards,
                    cover_src=wd + j.get("out", "成片.mp4"))
    elif s == "sheet":
        from PIL import Image
        out = wd + j.get("out", "成片.mp4")
        ve, end, _ = _timeline(p)
        ts = [end * k / 7 for k in range(1, 7)]
        imgs = []
        for i, t in enumerate(ts):
            f = wd + f".sheet{i}.jpg"
            _run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", out,
                  "-frames:v", "1", "-vf", "scale=270:-2", f])
            imgs.append(Image.open(f))
        w, h = imgs[0].size
        grid = Image.new("RGB", (w * 3, h * 2))
        for i, im in enumerate(imgs):
            grid.paste(im, ((i % 3) * w, (i // 3) * h))
        grid.save(wd + "接触表.jpg")
        for i in range(6):
            os.remove(wd + f".sheet{i}.jpg")
        print("接触表 →", wd + "接触表.jpg (一张图目检全片)")


def main(path, dry=False, assume=False, until=None):
    p = P(path)
    gates = p.j.get("gates", {})
    for s in STAGES:
        if s != "montage" and not gates.get("plan_approved", False):
            print(f"⛔ 闸门:计划未批(gates.plan_approved=false),停在 {s} 之前")
            break
        sig = stage_inputs(p, s)
        if assume:
            p.state[s] = sig
            continue
        if p.state.get(s) == sig:
            print(f"  ⏭ {s}(输入没变,跳过)")
        elif dry:
            print(f"  ▶ {s} 会重跑")
            p.state.pop(s, None)   # dry 下后续 stage 视为脏
            continue
        else:
            print(f"  ▶ {s} …")
            run_stage(p, s)
            p.state[s] = stage_inputs(p, s)
            p.save()
        if s == until:
            break
    if assume:
        p.save()
        print("已接管:当前输入全部记为已完成,下次只跑变化的")
    if dry:
        print("(dry-run,未写状态)")


if __name__ == "__main__":
    a = sys.argv
    main(a[1], "--dry-run" in a, "--assume-current" in a,
         a[a.index("--until") + 1] if "--until" in a else None)
