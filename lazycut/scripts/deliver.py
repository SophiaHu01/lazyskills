#!/usr/bin/env python3
"""交付: python3 deliver.py <config.json>
产出两件:压缩预览版(方便传给任何人过目) + 全画质定稿。**本脚本不发送到任何地方**——
产完打印路径,由 AI 在对话里问用户想怎么收(存哪/发谁/要不要传网盘),用户说了才动。
"""
import json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vconfig import load

cfg = load(sys.argv[1]); WD = cfg["workdir"].rstrip("/")+"/"; title = cfg["title"]
final = WD + title + "_定稿.mp4"
comp = WD + title + "_压缩.mp4"
subprocess.run(["ffmpeg","-y","-v","error","-i",final,"-vf","scale=720:-2","-c:v","libx264",
                "-crf","28","-preset","veryfast","-c:a","aac","-b:a","128k",comp],check=True)
sz = os.path.getsize(comp)/1e6
print(f"交付就绪:\n  预览版(720p,{sz:.0f}MB): {comp}\n  全画质: {final}")
print("→ 问用户:想存到哪/发给谁?未经确认不发送到任何地方。")
