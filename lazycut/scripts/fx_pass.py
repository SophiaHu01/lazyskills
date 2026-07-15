#!/usr/bin/env python3
"""热点风格特效后处理:白闪+变焦冲击(punch-in)转场 + 合成音效(whoosh/pop/boom)。

用法: fx_pass.py <in.mp4> <out.mp4> <fx.json>
fx.json: {"transitions":[t,...]     # 章节切换:白闪0.08s+0.25s变焦+whoosh
          ,"pops":[t,...]           # 字卡弹出:pop 音
          ,"booms":[t,...]          # 金句强调:低音 boom
          ,"sfx_gain_db":-16}       # 音效相对音量

机制:变焦用 crop 表达式(w='iw/z(t)',z=1+0.09*高斯脉冲之和,crop 吃 t);白闪用白图
overlay enable;音效用 ffmpeg 合成(噪声/正弦+包络)再 adelay+amix 进原音轨。
2026-07-11 首用于「不用教程学AI」创新版。验法:切换点抽帧看白闪,听感抽查音效点位。
"""
import json, os, subprocess, sys
from PIL import Image

def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: print(r.stderr[-500:]); sys.exit(1)

def main(inp, outp, fxp):
    FX = json.load(open(fxp))
    trans = FX.get("transitions", []); pops = FX.get("pops", []); booms = FX.get("booms", [])
    gain = FX.get("sfx_gain_db", -16)
    wd = os.path.dirname(os.path.abspath(outp)) or "."
    fxd = os.path.join(wd, "fxov"); os.makedirs(fxd, exist_ok=True)

    # 素材:白图 + 三种合成音效
    Image.new("RGB", (1080, 1920), (255, 255, 255)).save(f"{fxd}/white.png")
    sh(["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=c=pink:d=0.4:a=0.8",
        "-af", "highpass=f=400,lowpass=f=6000,afade=t=in:d=0.12,afade=t=out:st=0.15:d=0.25,volume=2.2",
        f"{fxd}/whoosh.wav"])
    sh(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=640:d=0.09",
        "-af", "afade=t=out:st=0.02:d=0.07,volume=2.0", f"{fxd}/pop.wav"])
    # 爆炸:低频轰(55Hz 衰减) + 棕噪爆(低通+快衰) 混合,比纯正弦有质感(2026-07-11 用户嫌之前太弱)
    sh(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=55:d=0.7", "-f", "lavfi",
        "-i", "anoisesrc=c=brown:d=0.7:a=0.75",
        "-filter_complex",
        "[0:a]afade=t=out:st=0.08:d=0.6,volume=3.2[s];"
        "[1:a]lowpass=f=900,afade=t=out:st=0.03:d=0.55,volume=2.4[n];"
        "[s][n]amix=inputs=2:normalize=0,alimiter=limit=0.9",
        f"{fxd}/boom.wav"])

    # 视频链:变焦脉冲(zoompan 的 it 支持逐帧求值;crop/scale 的 w,h 不吃 t,别回去踩)
    # video_fx=false 时只做音效混音(whoosh 仍按 transitions 时间),画面原样——
    # 给创作者自己在剪映里二次叠加的片子用,免得变焦白闪和用户的叠层打架。
    if not FX.get("video_fx", True): trans_v = []
    else: trans_v = trans
    if trans_v:
        pulses = "+".join(f"exp(-pow((it-{t})/0.12,2))" for t in trans_v)
        z = f"1+0.09*({pulses})"
        vf = [f"[0:v]zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d=1:s=1080x1920:fps=30,setsar=1[zv]"]
        prev = "zv"
    else:
        vf = ["[0:v]null[zv]"]; prev = "zv"
    fi = 1
    inputs = ["-i", inp, "-loop", "1", "-i", f"{fxd}/white.png"]
    for i, t in enumerate(trans_v):
        vf.append(f"[{prev}][1:v]overlay=0:0:enable='between(t,{t},{t+0.08})'[f{i}]")
        prev = f"f{i}"

    # 音频链:每个音效点一个 adelay 输入,amix 汇总
    a_ins, a_labels = [], []
    idx = 2
    for kind, arr in (("whoosh", trans), ("pop", pops), ("boom", booms)):
        for t in arr:
            inputs += ["-i", f"{fxd}/{kind}.wav"]
            ms = max(0, int((t - (0.15 if kind == 'whoosh' else 0)) * 1000))
            a_ins.append(f"[{idx}:a]adelay={ms}|{ms},volume={gain}dB[a{idx}]")
            a_labels.append(f"[a{idx}]"); idx += 1
    n = len(a_labels)
    # 响度归一化必须是最后一步(chatcut correctness rule #5,S4/2026-07-12):混完音效统一拉到目标
    ln = "" if FX.get("loudnorm") is False else f",loudnorm=I={FX.get('lufs_target',-14)}:TP=-1.5:LRA=11"
    af = a_ins + [f"[0:a]{''.join(a_labels)}amix=inputs={n+1}:duration=first:normalize=0{ln}[ao]"]

    fcf = os.path.join(wd, "fx_fc.txt"); open(fcf, "w").write(";".join(vf + af))
    r = subprocess.run(["ffmpeg", "-y"] + inputs + ["-filter_complex_script", fcf,
        "-map", f"[{prev}]", "-map", "[ao]", "-c:v", "libx264", "-crf", "20",
        "-preset", "veryfast", "-c:a", "aac", "-b:a", "192k", "-shortest", outp],
        capture_output=True, text=True)
    print("fx_pass ffmpeg", r.returncode)
    if r.returncode: print(r.stderr[-800:]); sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
