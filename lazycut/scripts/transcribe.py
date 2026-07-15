#!/usr/bin/env python3
"""转录: python3 transcribe.py <video> <out_prefix>
出 <prefix>_words.json(词级) / _segs.json(句段) / _sents.json(句子起点)

引擎自动选择:Apple 芯片用 mlx-whisper(最快);其他机器用 faster-whisper(通用,CPU/GPU 都行)。
两个都没装时给出对应安装命令。首次运行自动下载模型(约 1-2GB,只下一次)。
"""
import json
import sys

video, prefix = sys.argv[1], sys.argv[2]
words, segs, sents = [], [], []

try:
    import mlx_whisper
    r = mlx_whisper.transcribe(video, path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                               language="zh", word_timestamps=True, verbose=False)
    for s in r["segments"]:
        segs.append([round(s["start"], 2), round(s["end"], 2), s["text"].strip()])
        sents.append(round(s["start"], 2))
        for w in s.get("words", []):
            words.append([w["word"], round(w["start"], 2), round(w["end"], 2)])
except ImportError:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("没有可用转录引擎。Apple 芯片: pip install mlx-whisper;其他机器: pip install faster-whisper")
    model = WhisperModel("large-v3-turbo", compute_type="auto")
    seg_iter, _ = model.transcribe(video, language="zh", word_timestamps=True)
    for s in seg_iter:
        segs.append([round(s.start, 2), round(s.end, 2), s.text.strip()])
        sents.append(round(s.start, 2))
        for w in (s.words or []):
            words.append([w.word, round(w.start, 2), round(w.end, 2)])

json.dump(words, open(prefix + "_words.json", "w"), ensure_ascii=False)
json.dump(segs, open(prefix + "_segs.json", "w"), ensure_ascii=False)
json.dump(sents, open(prefix + "_sents.json", "w"), ensure_ascii=False)
print(f"转录完成: 词 {len(words)} 句段 {len(segs)}")
