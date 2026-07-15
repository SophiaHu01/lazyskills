#!/usr/bin/env python3
"""所有 ffmpeg 调用:剪辑成片(render_cut) + 最终合成(compose)。

写 .txt(filter 脚本) 与 subprocess 调用放在同一函数,方便金标准 monkeypatch subprocess
后 .txt 照样落盘。ffmpeg 命令/滤镜串一律照搬自原 build.py,一个字不许改。
"""
import sys, os, subprocess, json


def render_cut(cfg):
    WD = cfg["workdir"].rstrip("/")+"/"; SRC = cfg["video"]
    d=json.load(open(WD+"cutplan.json")); kept=d["kept"]; sp=d["speed"]
    speeds=d.get("seg_speeds") or [sp]*len(kept)   # 分段变速(介绍段可单独提速);缺省=全局 speed
    v=[];a=[];lab=[]
    for i,((s,e),spi) in enumerate(zip(kept,speeds)):
        if abs(spi-1.0)<0.01:
            v.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS[v{i}]")
            a.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS[a{i}]")
        else:
            v.append(f"[0:v]trim={s}:{e},setpts=(PTS-STARTPTS)/{spi}[v{i}]")
            a.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,atempo={spi}[a{i}]")
        lab.append(f"[v{i}][a{i}]")
    open(WD+"fc.txt","w").write(";".join(v+a)+";"+"".join(lab)+f"concat=n={len(kept)}:v=1:a=1[vout][aout]")
    r=subprocess.run(["ffmpeg","-y","-i",SRC,"-filter_complex_script",WD+"fc.txt","-map","[vout]","-map","[aout]",
        "-c:v","libx264","-crf","20","-preset","veryfast","-c:a","aac","-b:a","160k",WD+"cut_locked.mp4"],
        capture_output=True,text=True)
    print("render_cut", r.returncode)
    if r.returncode: print(r.stderr[-800:]); sys.exit(1)
    # 成片字幕数据:有转录锁(S1,2026-07-12)→ 按 cutplan 映射推算,不重转(防 whisper 每轮变体);
    # 无锁 → 老路径重新转录(向后兼容旧项目)。
    if os.path.exists(WD+"transcript.lock.json"):
        from transcript_lock import remap_cutplan
        remap_cutplan(WD)
    else:
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__),"transcribe.py"),
                        WD+"cut_locked.mp4", WD+"cap"], check=True)


def compose(cfg, WD, items):
    inp=["-i",WD+"cut_locked.mp4"]
    for it in items: inp+=["-i",it[0]]
    fc=[]; last="0:v"
    for i,(p,s,e,x,y) in enumerate(items):
        o=f"o{i}"; fc.append(f"[{last}][{i+1}:v]overlay={x}:{y}:enable='between(t,{s},{e})'[{o}]"); last=o
    open(WD+"fcf.txt","w").write(";".join(fc))
    r=subprocess.run(["ffmpeg","-y"]+inp+["-filter_complex_script",WD+"fcf.txt","-map",f"[{last}]","-map","0:a",
        "-c:v","libx264","-crf","20","-preset","veryfast","-c:a","copy",WD+"final.mp4"],capture_output=True,text=True)
    return r
