#!/usr/bin/env python3
"""CapCut 草稿直出(2026-07-13,省 token 改造 A 方案):流水线不吐成品 mp4,直接往用户的
CapCut 草稿夹写可编辑工程——视频轨(分段+变速)、字幕文本轨、卡片文本轨,用户打开就能自己剪。

原理:不信任第三方库的过期 schema,**深拷贝用户本机真实草稿(模板)里的 segment/material
当骨架**,只替换 id/路径/时间/文本,版本号天然匹配用户装的 CapCut(实测 8.7.0,draft_info.json
明文 JSON,时间单位微秒)。

用法(作为库):
    from capcut_draft import build_draft
    build_draft(template_dir, out_name, clips, captions, cards, cover_src)
clips    = [{"path":..,"s":源起秒,"e":源止秒,"speed":1.12}]   # 按时间线顺序
captions = [(start秒,end秒,文本)]                              # 成片时间轴
cards    = [{"title":..,"sub":[..],"start":秒,"hold":秒}]
"""
import copy
import json
import os
import shutil
import subprocess
import time
import uuid

INFO_NAMES = ("draft_info.json", "draft_content.json")  # 国际版 / 国内版剪映的草稿主文件名


def _info_name(draft_dir):
    for n in INFO_NAMES:
        if os.path.exists(os.path.join(draft_dir, n)):
            return n
    return None


def find_template(root=None):
    """认领模板草稿:扫草稿根目录,取最近修改的「合格」草稿(能解析+有视频段+有文本材料)。
    找不到就用人话教用户造一个。装机问卷答完剪辑软件后调这个,把结果记进配置。"""
    root = root or DRAFT_ROOT
    cands = sorted((os.path.join(root, d) for d in os.listdir(root)
                    if os.path.isdir(os.path.join(root, d))),
                   key=os.path.getmtime, reverse=True)
    for c in cands:
        n = _info_name(c)
        if not n:
            continue
        try:
            d = json.load(open(os.path.join(c, n)))
        except Exception:
            continue  # 解析不了(可能加密/损坏),看下一个
        has_v = any(t.get("type") == "video" and t.get("segments") for t in d.get("tracks", []))
        has_t = bool(d.get("materials", {}).get("texts"))
        if has_v and has_t:
            return c
    raise SystemExit("❌ 还没有可当模板的草稿——做一次40秒的「教AI认识你的剪映」:打开剪映→新建草稿→"
                     "拖 examples/ 里的样例视频(或任意视频)进时间线→随手打一行字幕→保存关闭→再来。"
                     "一台电脑只做一次。为什么:本工具靠读你的真实草稿学格式,所以剪映怎么升级都不怕。")


def verify_draft(out_dir):
    """生成后自检:身份链闭环+引用完整+时间合法。把人肉排障三轮的检查固化成机器动作。"""
    n = _info_name(out_dir)
    d = json.load(open(os.path.join(out_dir, n)))
    ids = {it["id"] for v in d["materials"].values() if isinstance(v, list)
           for it in v if isinstance(it, dict) and "id" in it}
    problems = []
    for tr in d["tracks"]:
        for s in tr["segments"]:
            if s["material_id"] not in ids:
                problems.append(f"段 {s['id'][:8]} 的素材引用悬空")
            problems += [f"段 {s['id'][:8]} 的附属引用悬空" for r in s["extra_material_refs"] if r not in ids]
            t = s["target_timerange"]
            if t["start"] < 0 or t["duration"] <= 0:
                problems.append(f"段 {s['id'][:8]} 时间非法")
    lm = {v.get("local_material_id") for v in d["materials"].get("videos", [])}
    vs_p = os.path.join(out_dir, "draft_virtual_store.json")
    if os.path.exists(vs_p):
        store = {c["child_id"] for g in json.load(open(vs_p)).get("draft_virtual_store", [])
                 if g.get("type") == 1 for c in g.get("value", [])}
        if not lm <= store:
            problems.append("素材身份链未闭环(local_material_id 未在 virtual_store 登记)")
    if problems:
        raise SystemExit("❌ 草稿自检不过:\n  " + "\n  ".join(problems[:8]))
    print("草稿自检 ✅ 身份链闭环/引用完整/时间合法")


def _find_draft_root():
    """自动探测剪映/CapCut 草稿根目录(mac/Windows,国际版/国内版)。找不到=没装或没建过草稿。"""
    cands = [os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft"),
             os.path.expanduser("~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft")]
    la = os.environ.get("LOCALAPPDATA")
    if la:
        cands += [os.path.join(la, r"CapCut\User Data\Projects\com.lveditor.draft"),
                  os.path.join(la, r"JianyingPro\User Data\Projects\com.lveditor.draft")]
    for c in cands:
        if os.path.isdir(c):
            return c
    raise SystemExit("❌ 没找到剪映/CapCut 桌面版的草稿目录。装桌面版并新建过至少一个草稿再来(模板克隆法需要拿你的真实草稿当格式模板)。")


DRAFT_ROOT = _find_draft_root()
AUX_ORDER = ["speeds", "placeholder_infos", "canvases", "sound_channel_mappings",
             "material_colors", "vocal_separations"]


def _uid():
    return str(uuid.uuid4()).upper()


def _us(sec):
    return int(round(sec * 1_000_000))


def _probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height", "-show_entries", "format=duration",
                        "-of", "json", path], capture_output=True, text=True)
    j = json.loads(r.stdout)
    st = j["streams"][0]
    return int(st["width"]), int(st["height"]), float(j["format"]["duration"])


def _balance_wrap(t, maxlen=13):
    """字幕平衡断行(2026-07-13 用户要求:不出画面框+给右侧点赞栏留位)。按行数均分,
    避开英文词中间,标点后优先。≤maxlen 原样返回。"""
    if len(t) <= maxlen or "\n" in t:
        return t
    import math
    nlines = math.ceil(len(t) / maxlen)
    lines, rest = [], t
    for k in range(nlines - 1, 0, -1):
        target = len(rest) / (k + 1)
        local = [i for i in range(1, len(rest))
                 if not (rest[i-1].isascii() and rest[i-1].isalnum()
                         and rest[i].isascii() and rest[i].isalnum())]
        if not local:
            break
        best = min(local, key=lambda i: abs(i - target) - (1.5 if rest[i-1] in ",。?!、:" else 0))
        lines.append(rest[:best]); rest = rest[best:]
    lines.append(rest)
    return "\n".join(lines)


def _reset_clip(seg):
    seg["clip"] = {"scale": {"x": 1.0, "y": 1.0}, "rotation": 0.0,
                   "transform": {"x": 0.0, "y": 0.0},
                   "flip": {"vertical": False, "horizontal": False}, "alpha": 1.0}


def build_draft(template_dir, out_name, clips, captions, cards, cover_src=None):
    if not template_dir:
        template_dir = find_template()
        print(f"模板草稿(自动认领): {os.path.basename(template_dir)}")
    info_name = _info_name(template_dir)
    tpl = json.load(open(os.path.join(template_dir, info_name)))
    tpl_vseg = copy.deepcopy(tpl["tracks"][0]["segments"][0])
    ttrack = next(t for t in tpl["tracks"] if t["type"] == "text")
    tpl_tseg = copy.deepcopy(ttrack["segments"][0])
    mats_t = tpl["materials"]
    tpl_video = copy.deepcopy(mats_t["videos"][0])
    tid = tpl_tseg["material_id"]
    tpl_text = copy.deepcopy(next(x for x in mats_t["texts"] if x["id"] == tid)
                             if any(x["id"] == tid for x in mats_t["texts"])
                             else mats_t["texts"][0])
    tpl_aux = {c: copy.deepcopy(mats_t[c][0]) for c in AUX_ORDER}
    tpl_anim = copy.deepcopy(mats_t["material_animations"][0]) if mats_t.get("material_animations") \
        else {"id": _uid(), "type": "sticker_animation", "animations": [], "multi_language_current": "none"}

    info = copy.deepcopy(tpl)
    mats = info["materials"]
    for k, v in mats.items():
        if isinstance(v, list):
            mats[k] = []

    # 素材以 APFS 克隆(cp -c,写时复制)进草稿文件夹。三层原因(2026-07-13 定案):
    # ① 沙盒:CapCut 只免弹窗读两处——自家目录 + ~/Movies(assets.movies entitlement 实测);
    #   任意其他路径都会弹 Link media。放草稿夹内=零弹窗。
    # ② 为什么不用硬链接:硬链接共享 inode,流水线 `ffmpeg -y` 原地重写源文件会隔空篡改
    #   用户正在编辑的草稿素材;克隆有独立 inode,是当时的快照,零空间、瞬间完成。
    # ③ 生命周期:用户在 CapCut 删草稿,素材随文件夹走,不留孤儿。跨卷时克隆失败退回真复制。
    out_dir = os.path.join(DRAFT_ROOT, out_name)
    res_dir = os.path.join(out_dir, "Resources", "local")
    os.makedirs(res_dir, exist_ok=True)

    def _localize(p):
        dst = os.path.join(res_dir, os.path.basename(p))
        if not os.path.exists(dst):
            r = subprocess.run(["cp", "-c", p, dst], capture_output=True)
            if r.returncode:
                shutil.copy(p, dst)
        return dst

    # ── 视频轨 ──
    # 身份链(2026-07-13 排障结论,「File not accessible」的真凶):CapCut 按素材池身份解析媒体,
    # 不是按路径。videos 材料的 local_material_id 必须指向本草稿 meta 素材池条目的 id,
    # 且该 id 要在 draft_virtual_store.json 登记——整块克隆模板会把用户旧素材的身份证抄进来,必炸。
    vids = {}       # 本地化后 path -> {mat: material id, entry: 素材池条目 id}
    seg_kv = []     # (segment id, 文件名) → key_value.json 逐段登记
    vsegs, acc = [], 0.0
    for c in clips:
        p = _localize(c["path"])
        c = dict(c, path=p)
        if p not in vids:
            w, h, dur = _probe(p)
            has_a = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                                         "-show_entries", "stream=index", "-of", "csv=p=0", p],
                                        capture_output=True, text=True).stdout.strip())
            entry_id = str(uuid.uuid4())
            m = copy.deepcopy(tpl_video)
            m.update({"id": _uid(), "path": p, "duration": _us(dur), "width": w, "height": h,
                      "material_name": os.path.basename(p), "has_audio": has_a,
                      "local_material_id": entry_id})
            mats["videos"].append(m)
            vids[p] = {"mat": m["id"], "entry": entry_id}
        sp = c.get("speed", 1.0)
        seg = copy.deepcopy(tpl_vseg)
        refs = []
        for cat in AUX_ORDER:
            a = copy.deepcopy(tpl_aux[cat])
            a["id"] = _uid()
            if cat == "speeds":
                a["speed"] = sp
            mats[cat].append(a)
            refs.append(a["id"])
        dur_t = (c["e"] - c["s"]) / sp
        seg.update({"id": _uid(), "material_id": vids[p]["mat"], "extra_material_refs": refs,
                    "speed": sp, "volume": 1.0, "last_nonzero_volume": 1.0, "visible": True,
                    "source_timerange": {"start": _us(c["s"]), "duration": _us(c["e"] - c["s"])},
                    "target_timerange": {"start": _us(acc), "duration": _us(dur_t)}})
        _reset_clip(seg)
        seg_kv.append((seg["id"], os.path.basename(p)))
        vsegs.append(seg)
        acc += dur_t
    total = acc

    def _text_seg(txt, s, dur, y, ridx):
        m = copy.deepcopy(tpl_text)
        m["id"] = _uid()
        content = json.loads(m["content"])
        content["text"] = txt
        if content.get("styles"):
            content["styles"] = [content["styles"][0]]
            content["styles"][0]["range"] = [0, len(txt)]
        m["content"] = json.dumps(content, ensure_ascii=False)
        if "base_content" in m:
            m["base_content"] = txt
        mats["texts"].append(m)
        anim = copy.deepcopy(tpl_anim)
        anim["id"] = _uid()
        mats["material_animations"].append(anim)
        seg = copy.deepcopy(tpl_tseg)
        seg.update({"id": _uid(), "material_id": m["id"], "extra_material_refs": [anim["id"]],
                    "render_index": ridx, "visible": True,
                    "target_timerange": {"start": _us(s), "duration": _us(dur)}})
        _reset_clip(seg)
        seg["clip"]["transform"]["y"] = y
        return seg

    # 画布跟素材走(bug修复:此前照抄模板画布,横屏素材进竖屏模板画布必错)
    if vids:
        first = next(iter(vids))
        cw, ch, _ = _probe(first)
        info["canvas_config"] = {"ratio": "original", "width": cw, "height": ch,
                                 "background": info.get("canvas_config", {}).get("background")}
    else:
        cw, ch = 1080, 1920
    # 断行上限按横竖屏自适应(竖屏13/横屏22),可被 style.json caption.line_chars 覆盖
    maxlen = 13 if ch >= cw else 22
    try:
        style = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                            "assets", "style.json")))
        maxlen = int(style.get("caption", {}).get("line_chars", maxlen))
    except Exception:
        pass
    cap_scale = 0.6
    try:
        cap_scale = float(style.get("caption", {}).get("draft_scale", 0.6))
    except Exception:
        pass
    csegs = []
    for i, (cs, ce, t) in enumerate(captions):
        seg = _text_seg(_balance_wrap(t, maxlen), cs, ce - cs, -0.73, 14000 + i)
        seg["clip"]["scale"] = {"x": cap_scale, "y": cap_scale}  # 治「模板克隆继承大标题字号」:默认缩到0.6
        csegs.append(seg)
    ksegs = [_text_seg(c["title"] + "\n" + "\n".join(c["sub"]), c["start"], c["hold"], 0.62, 15000 + i)
             for i, c in enumerate(cards)]

    def _track(tpl_track, segs):
        tr = copy.deepcopy(tpl_track)
        tr["id"] = _uid()
        tr["segments"] = segs
        return tr

    info["tracks"] = [_track(tpl["tracks"][0], vsegs), _track(ttrack, csegs), _track(ttrack, ksegs)]
    info["id"] = _uid()
    info["name"] = out_name
    info["duration"] = _us(total)

    # ── 落盘 ──
    json.dump(info, open(os.path.join(out_dir, info_name), "w"), ensure_ascii=False)
    shutil.copy(os.path.join(out_dir, info_name), os.path.join(out_dir, info_name + ".bak"))
    # 生成快照:用户在 CapCut 里手改后,draft_diff.py 拿它和现状比对,读回用户的改动(双向协作的锚)
    shutil.copy(os.path.join(out_dir, info_name), os.path.join(out_dir, "draft_info.gen.json"))

    meta = json.load(open(os.path.join(template_dir, "draft_meta_info.json")))
    now = int(time.time())
    ent_tpl = meta["draft_materials"][0]["value"][0] if meta["draft_materials"][0].get("value") else {}
    for g in meta.get("draft_materials", []):
        g["value"] = []
    vals = []
    for p, ids in vids.items():
        w, h, dur = _probe(p)
        e = copy.deepcopy(ent_tpl)
        e.update({"id": ids["entry"], "file_Path": p, "duration": _us(dur), "width": w,
                  "height": h, "metetype": "video", "create_time": now, "import_time": now,
                  "import_time_ms": now * 1_000_000, "roughcut_time_range": {"start": -1, "duration": -1}})
        vals.append(e)
    if meta.get("draft_materials"):
        meta["draft_materials"][0]["value"] = vals
    meta.update({"draft_id": _uid(), "draft_name": out_name,
                 "draft_fold_path": out_dir, "draft_root_path": DRAFT_ROOT,
                 "tm_draft_create": now * 1_000_000, "tm_draft_modified": now * 1_000_000,
                 "tm_duration": _us(total), "draft_removable_storage_device": ""})
    json.dump(meta, open(os.path.join(out_dir, "draft_meta_info.json"), "w"), ensure_ascii=False)

    # 素材池登记表:virtual_store 的 type-1 child_id 必须列出素材池条目 id(身份链闭环)
    vstore = {"draft_materials": [], "draft_virtual_store": [
        {"type": 0, "value": [{"creation_time": 0, "display_name": "", "filter_type": 0, "id": "",
                               "import_time": 0, "import_time_us": 0, "sort_sub_type": 0, "sort_type": 0,
                               "subdraft_filter_type": 0}]},
        {"type": 1, "value": [{"child_id": ids["entry"], "parent_id": ""} for ids in vids.values()]},
        {"type": 2, "value": []}]}
    json.dump(vstore, open(os.path.join(out_dir, "draft_virtual_store.json"), "w"), ensure_ascii=False)
    # 逐段媒体登记(照用户真实草稿 key_value.json 的条目形状)
    import hashlib
    kv = {}
    for sid, name in seg_kv:
        kv[sid] = {"filter_category": "", "filter_detail": "", "is_brand": 0, "is_from_artist_shop": 0,
                   "is_vip": "0", "keywordSource": "", "materialCategory": "media",
                   "materialId": hashlib.md5(name.encode()).hexdigest(), "materialName": name,
                   "materialSubcategory": "local", "materialSubcategoryId": "",
                   "materialThirdcategory": "Import", "materialThirdcategoryId": "",
                   "material_copyright": "", "material_is_purchased": "", "rank": "0", "rec_id": "",
                   "requestId": "", "role": "", "searchId": "", "searchKeyword": "", "segmentId": sid}
    json.dump(kv, open(os.path.join(out_dir, "key_value.json"), "w"), ensure_ascii=False)
    open(os.path.join(out_dir, "draft_settings"), "w").write(
        f"[General]\ndraft_create_time={now}\ndraft_last_edit_time={now}\nreal_edit_keys=0\nreal_edit_seconds=0\n")
    for sub in ["Resources/audioAlg", "Resources/videoAlg"]:
        os.makedirs(os.path.join(out_dir, sub), exist_ok=True)
    for f in ["attachment_pc_common.json", "draft_biz_config.json", "draft_agency_config.json",
              "performance_opt_info.json"]:
        src = os.path.join(template_dir, f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(out_dir, f))
    if cover_src:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "3", "-i", cover_src,
                        "-frames:v", "1", os.path.join(out_dir, "draft_cover.jpg")], check=True)
    verify_draft(out_dir)
    print(f"草稿已写入: {out_dir}\n  视频段 {len(vsegs)} | 字幕 {len(csegs)} | 卡片 {len(ksegs)} | 总长 {total:.1f}s")
    return out_dir
