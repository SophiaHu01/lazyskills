#!/usr/bin/env python3
"""装前体检:检查这台电脑能不能跑本 skill、缺什么、哪些功能会降级。

用法: python3 scripts/doctor.py
输出: 逐项 ✅/⚠️/❌ + 一句人话结论。❌=硬缺失(装完再来),⚠️=功能降级但能用。
把输出原样贴给你的 AI 助手,它就知道该帮你装什么。
"""
import importlib
import os
import platform
import shutil
import subprocess
import sys

OK, WARN, FAIL = "✅", "⚠️", "❌"
issues = {"fail": 0, "warn": 0}


def check(label, status, note=""):
    print(f"  {status} {label}" + (f" — {note}" if note else ""))
    if status == FAIL:
        issues["fail"] += 1
    elif status == WARN:
        issues["warn"] += 1


def main():
    print("== lazycut skill 体检 ==\n")
    sysname = platform.system()
    mach = platform.machine()
    check(f"系统 {sysname} / {mach}", OK if sysname in ("Darwin", "Windows") else WARN,
          "" if sysname in ("Darwin", "Windows") else "Linux 未充分测试")

    v = sys.version_info
    check(f"Python {v.major}.{v.minor}", OK if (v.major, v.minor) >= (3, 10) else FAIL,
          "" if (v.major, v.minor) >= (3, 10) else "需要 3.10+")

    for tool in ("ffmpeg", "ffprobe"):
        check(tool, OK if shutil.which(tool) else FAIL,
              "" if shutil.which(tool) else "视频引擎,必装(macOS: brew install ffmpeg / Windows: winget install ffmpeg)")

    try:
        importlib.import_module("PIL")
        check("Pillow(字幕绘制)", OK)
    except ImportError:
        check("Pillow(字幕绘制)", FAIL, "pip install pillow")

    # 转录引擎:Apple 芯片首选 mlx-whisper,其余 faster-whisper
    eng = None
    for m, name in (("mlx_whisper", "mlx-whisper(Apple 芯片)"), ("faster_whisper", "faster-whisper")):
        try:
            importlib.import_module(m)
            eng = name
            break
        except ImportError:
            pass
    if eng:
        check(f"转录引擎: {eng}", OK, "首次运行会自动下载模型(约 1-2GB,只下一次)")
    else:
        tip = "pip install mlx-whisper" if (sysname == "Darwin" and mach == "arm64") else "pip install faster-whisper"
        check("转录引擎", FAIL, f"没装。{tip}")

    # OCR:macOS 用系统 Vision(零依赖),其他平台 RapidOCR
    if sysname == "Darwin":
        here = os.path.dirname(os.path.abspath(__file__))
        check("OCR(macOS Vision)", OK if os.path.exists(os.path.join(here, "ocr")) else WARN,
              "" if os.path.exists(os.path.join(here, "ocr")) else
              f"首次编译: swiftc -O {here}/ocr.swift -o {here}/ocr")
    else:
        try:
            importlib.import_module("rapidocr_onnxruntime")
            check("OCR(RapidOCR)", OK)
        except ImportError:
            check("OCR(RapidOCR)", WARN, "录屏台账功能降级。pip install rapidocr-onnxruntime")

    # 剪辑器草稿目录(草稿直出的落点)
    roots = [os.path.expanduser(p) for p in (
        "~/Movies/CapCut/User Data/Projects/com.lveditor.draft",
        "~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft")]
    if sysname == "Windows":
        la = os.environ.get("LOCALAPPDATA", "")
        roots = [os.path.join(la, r"CapCut\User Data\Projects\com.lveditor.draft"),
                 os.path.join(la, r"JianyingPro\User Data\Projects\com.lveditor.draft")]
    hit = next((r for r in roots if os.path.isdir(r)), None)
    check("剪映/CapCut 桌面版", OK if hit else WARN,
          hit or "没找到草稿目录:装桌面版并新建过至少一个草稿(模板克隆法需要它)。没有也能出 mp4,只是少了草稿直出")

    # 可选增强
    try:
        importlib.import_module("clearvoice")
        check("人声增强(ClearVoice,可选)", OK)
    except ImportError:
        check("人声增强(ClearVoice,可选)", WARN, "跳过此步不影响出片")
    check("卡片动效(Remotion,可选)", OK if shutil.which("npx") else WARN,
          "" if shutil.which("npx") else "没有 node 就用剪辑器文本轨做卡,不影响主流程")

    free_gb = shutil.disk_usage(os.path.expanduser("~")).free / 1e9
    check(f"磁盘剩余 {free_gb:.0f}GB", OK if free_gb > 10 else WARN, "" if free_gb > 10 else "建议留 10GB+")

    print()
    if issues["fail"]:
        print(f"结论: 有 {issues['fail']} 项必须先装(❌)。把上面的输出整段贴给你的 AI 助手,让它帮你装好再来。")
        sys.exit(1)
    if issues["warn"]:
        print(f"结论: 能跑!有 {issues['warn']} 项功能会降级(⚠️),不影响出片。")
    else:
        print("结论: 满配,直接开工。")


if __name__ == "__main__":
    main()
