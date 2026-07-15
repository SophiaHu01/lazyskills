#!/usr/bin/env python3
"""给已生成的 CapCut 草稿字幕原地平衡断行(2026-07-13 安全区返工用,可重复打)。

只动「流水线生成的字幕」(与 workdir/cap_segs.json 文本匹配的条目),用户手改的卡片/新增文本
零触碰;改完把 gen 快照重定基线。

写前保险:CapCut 进程若在运行则拒绝执行——用户开着草稿时写文件必被其自动保存覆盖
(2026-07-13 实战教训:第一次折行就是这么丢的)。

用法: draft_wrap_captions.py <草稿文件夹> <workdir> [maxlen=13] [--force]
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capcut_draft import _balance_wrap


def main(draft_dir, workdir, maxlen=13, force=False):
    if not force:
        r = subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True)
        if r.returncode == 0:
            raise SystemExit("❌ CapCut 正在运行——用户开着草稿时写文件会被自动保存覆盖。"
                             "让用户完全退出 CapCut 后再跑(确认无风险可加 --force)。")
    draft_dir = draft_dir.rstrip("/") + "/"
    caps = {t for s, e, t in json.load(open(os.path.join(workdir, "cap_segs.json")))}
    cur = json.load(open(draft_dir + "draft_info.json"))
    fixed = []
    for m in cur["materials"]["texts"]:
        c = json.loads(m["content"])
        flat = c.get("text", "").replace("\n", "")
        if flat in caps and len(flat) > maxlen:
            nt = _balance_wrap(flat, maxlen)
            c["text"] = nt
            if c.get("styles"):
                c["styles"][0]["range"] = [0, len(nt)]
            m["content"] = json.dumps(c, ensure_ascii=False)
            if "base_content" in m:
                m["base_content"] = nt
            fixed.append(nt)
    json.dump(cur, open(draft_dir + "draft_info.json", "w"), ensure_ascii=False)
    shutil.copy(draft_dir + "draft_info.json", draft_dir + "draft_info.gen.json")
    print(f"平衡断行 {len(fixed)} 条(用户的手改零触碰),基线已重定:")
    for t in fixed:
        print("  " + t.replace("\n", " ⏎ "))


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2],
         int(a[3]) if len(a) > 3 and a[3].isdigit() else 13,
         "--force" in a)
