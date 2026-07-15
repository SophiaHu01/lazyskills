#!/usr/bin/env python3
"""S5 字幕断句唯一实现(用户强调过无数次:按自然断句,不机械切/不跨句合并)。

规则(全流水线共用,PIL 烧录与 Remotion 两条路径都从这取页):
  1. 主边界 = whisper 分段(自然停顿),一段一页,绝不跨段合并
  2. 单段 > maxc 字才段内二次切:切点不落在英文词/词组中间
  3. 英文相邻词合并成不可分 token(pre-requisite / office hour / Playwright MCP)
输入 words=[{w,s,e,..}](已纠错,词序即时序) + segs=[[s,e,txt]..];输出每词 br 标记。
"""


def _wc(ch: str) -> bool:
    return ch.isascii() and (ch.isalnum() or ch in "-'")


def merge_latin(words: list, segs: list) -> list:
    """同段内相邻 latin 词合并成一个 token(带空格语义),防英文被拦腰截断。"""
    def seg_idx(t):
        for i, (s, e, _) in enumerate(segs):
            if t < e - 1e-6:
                return i
        return len(segs) - 1
    out = []
    for o in words:
        si = seg_idx(o["s"])
        last = out[-1] if out else None
        lw = last["w"] if last else ""
        cw = o["w"]
        if (last and lw.strip() and cw.strip() and _wc(lw.rstrip()[-1]) and _wc(cw.lstrip()[0])
                and last["_si"] == si):
            sep = " " if (cw[:1].isspace() or lw[-1:].isspace()) else ""
            last["w"] = lw.rstrip() + sep + cw.lstrip()
            last["e"] = o["e"]
            last["emph"] = last.get("emph", False) or o.get("emph", False)
        else:
            oo = dict(o)
            oo["_si"] = si
            out.append(oo)
    return out


def mark_breaks(words: list, maxc: int = 30) -> list:
    """就地给每词打 br(该词起新页)。words 必须已带 _si(merge_latin 的输出)。"""
    prev, chars = None, 0
    for i, o in enumerate(words):
        si, w = o["_si"], o["w"]
        if prev is None or si != prev:
            o["br"] = True
            chars = 0
        elif chars + len(w) > maxc:
            pw = words[i - 1]["w"]
            if pw and w and _wc(pw[-1]) and _wc(w[0]):
                o["br"] = False   # 会切断英文 → 推迟到干净处
            else:
                o["br"] = True
                chars = 0
        else:
            o["br"] = False
        chars += len(w)
        prev = si
    for o in words:
        o.pop("_si", None)
    return words


def paginate(words: list, segs: list, maxc: int = 30) -> list:
    """完整管线:合并 latin → 打 br → 返回页列表 [[word,..],..](烧录路径用)。"""
    ws = mark_breaks(merge_latin(words, segs), maxc)
    pages, cur = [], []
    for w in ws:
        if w.get("br") and cur:
            pages.append(cur)
            cur = []
        cur.append(w)
    if cur:
        pages.append(cur)
    return pages
