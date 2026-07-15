English | [简体中文](README.zh-CN.md)

# lazyskills · Replicating 30 AI Products as Open-Source Skills

I'm replicating the core features of commercial AI products, one by one, as open-source
**skills** — install them into an **AI coding assistant** (Claude Code, Cursor, Windsurf,
Codex, etc.) and get roughly **80% of the original product's capability**. Free, fully
local, private (nothing is ever uploaded). When a replication succeeds, you get it
open-source; when it fails, you get a teardown of the product's moat.

| Episode | Target product | Skill | Status |
|---|---|---|---|
| EP01 | ChatCut (AI video editing) | [lazycut](lazycut/) | Beta |

---

## EP01 · lazycut in detail

### What it does

Transcribes your talking-head footage → auto-picks the best take from your retakes →
text-based editing (strike a sentence to cut it) → captions with natural line breaks and
keyword highlights → smart-paced silent screen recordings → motion-graphics planning →
machine QA → **exports an editable project for the editor you already use** — it asks
which one during onboarding. Deepest support today: CapCut/JianYing native drafts
(separate tracks, not a baked mp4); DaVinci Resolve / Premiere / Final Cut via EDL/OTIO;
a universal asset pack (clean base + SRT + card PNGs) for anything else.
Full capability table and how-it-works: [lazycut/README.md](lazycut/README.md).

### Architecture

Three layers, rules separated from tools:

- **SKILL.md (instruction layer)** — the mainline the AI reads: an 8-step pipeline,
  3 hard stops that require your explicit confirmation (before cutting / before rendering /
  before sending anything anywhere), and a channel ban.
- **scripts/ (tool layer)** — 30 deterministic single-file tools. Judgment belongs to the
  AI; execution belongs to code — same input, same output, every time.
- **assets/style.json (style layer) + reference/lessons.local.md (mistake journal)** —
  your taste is data; rules grow from your corrections.

Two core mechanisms: the **transcript lock** (transcribe once, lock it as the single
source of truth, derive every subsequent edit via time mapping — kills the
"every re-transcription produces different typos" problem at the root) and **template
cloning** (learn the draft format from a real draft on *your* machine instead of
hardcoding a reverse-engineered schema — upgrade-proof by construction).

Note: the skill's instruction layer is currently written in Chinese (AI assistants read it
natively); an English mirror is planned.

### Open-source components

| Component | Role | Required? |
|---|---|---|
| [ffmpeg](https://ffmpeg.org) | video engine | ✅ |
| [Whisper](https://github.com/openai/whisper) (via mlx-whisper / faster-whisper) | speech-to-text | ✅ auto-selected |
| [Pillow](https://python-pillow.org) | caption rendering | ✅ |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | on-screen OCR on non-macOS | per-platform |
| [ClearVoice](https://github.com/modelscope/ClearerVoice-Studio) | voice enhancement | optional |
| [Remotion](https://remotion.dev) | motion graphics | optional |
| [OpenTimelineIO](https://opentimelineio.readthedocs.io) | timeline interchange | optional |

Models download to your machine on first run (~1–2 GB, once); everything runs offline after.

### What you may need to install

Python 3.10+, ffmpeg, a few pip packages (the transcription engine is auto-selected for
your chip), and optionally Node.js for motion graphics. No need to memorize any of this:
run `python3 lazycut/scripts/doctor.py` and paste the output to your AI coding assistant —
it installs whatever is missing.

### Machine requirements

Works on macOS (smoothest on Apple silicon) and Windows: dual transcription engines,
dual OCR engines, automatic CJK font detection. Windows hasn't had a full end-to-end
real-machine test yet — Windows users, please open an issue whether it works or breaks;
first testers get credited here.

---

## How to use

**Absolute beginner?** Follow the illustrated [step-by-step tutorial](docs/tutorial.md).

```bash
git clone https://github.com/SophiaHu01/lazyskills.git
cd lazyskills/lazycut && python3 scripts/doctor.py
```

**Claude Code**: copy `lazycut/` into `~/.claude/skills/`, then say
"use lazycut to edit `<footage folder>`".
**Cursor / Windsurf / Codex**: the bundled `AGENTS.md` activates when you open the repo,
or just say "read lazycut/SKILL.md and follow it".
A skill is only markdown rules + python scripts — any AI assistant that can read files
and run commands can drive it.

License: MIT
