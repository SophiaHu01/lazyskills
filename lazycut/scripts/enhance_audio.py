#!/usr/bin/env python3
"""音频增强: python3 enhance_audio.py <config.json>  → workdir/<title>_定稿.mp4
audio: ai=ClearVoice播客级 / loud=只提响度 / bright=提响度+提亮。别用重降噪(发闷)。"""
import sys, json, subprocess, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vconfig import load
cfg=load(sys.argv[1]); WD=cfg["workdir"].rstrip("/")+"/"; mode=cfg.get("audio","ai")
inp=WD+"final.mp4"; out=WD+cfg.get("title","成片")+"_定稿.mp4"
CHAINS={
 "loud":"loudnorm=I=-14:TP=-1.5:LRA=11",
 "bright":"highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:makeup=2,equalizer=f=3000:t=q:w=1.4:g=3,treble=g=4:f=4500,loudnorm=I=-14:TP=-1.5:LRA=11",
}
VENV=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv_cv", "bin", "python")  # skill目录内,随仓库走
if mode=="ai" and os.path.exists(VENV):
    subprocess.run(["ffmpeg","-y","-i",inp,"-vn","-ar","48000","-ac","1",WD+"aud48.wav"],check=True,capture_output=True)
    open(WD+"_cv.py","w").write(
        'from clearvoice import ClearVoice\nimport warnings; warnings.filterwarnings("ignore")\n'
        'cv=ClearVoice(task="speech_enhancement",model_names=["MossFormer2_SE_48K"])\n'
        f'o=cv(input_path="{WD}aud48.wav",online_write=False); cv.write(o,output_path="{WD}aud_ai.wav")\nprint("AI_DONE")\n')
    r=subprocess.run([VENV,WD+"_cv.py"],capture_output=True,text=True); print(r.stdout.strip()[-100:] or r.stderr[-300:])
    subprocess.run(["ffmpeg","-y","-i",inp,"-i",WD+"aud_ai.wav","-map","0:v","-map","1:a",
        "-af","loudnorm=I=-14:TP=-1.5:LRA=11","-c:v","copy","-c:a","aac","-b:a","192k",out],check=True,capture_output=True)
    print("AI 音频定稿:",out)
else:
    if mode=="ai": print("!! ClearVoice venv 未装,降级 bright。首次装见 SKILL.md 环境依赖")
    chain=CHAINS.get(mode, CHAINS["bright"])
    subprocess.run(["ffmpeg","-y","-i",inp,"-af",chain,"-c:v","copy","-c:a","aac","-b:a","192k",out],check=True,capture_output=True)
    print(f"{mode} 音频定稿:",out)
