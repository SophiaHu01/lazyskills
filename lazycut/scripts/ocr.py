#!/usr/bin/env python3
"""OCR 备胎(非 macOS 机器用):RapidOCR 实现,输出格式与 macOS Vision 版(ocr.swift)完全一致。
  python3 ocr.py <image> [--boxes]
无 --boxes: 每行一条识别文本;--boxes: "x,y,w,h\\t文本"(归一化坐标,y 从顶部起)。
依赖: pip install rapidocr-onnxruntime(首次自动下模型,~15MB)
"""
import sys

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    raise SystemExit("需要 RapidOCR: pip install rapidocr-onnxruntime")
from PIL import Image

img = sys.argv[1]
boxes = "--boxes" in sys.argv
W, H = Image.open(img).size
result, _ = RapidOCR()(img)
for item in (result or []):
    quad, txt = item[0], item[1]
    if not txt.strip():
        continue
    if boxes:
        xs = [p[0] for p in quad]
        ys = [p[1] for p in quad]
        x, y = min(xs) / W, min(ys) / H
        w, h = (max(xs) - min(xs)) / W, (max(ys) - min(ys)) / H
        print(f"{x:.4f},{y:.4f},{w:.4f},{h:.4f}\t{txt}")
    else:
        print(txt)
