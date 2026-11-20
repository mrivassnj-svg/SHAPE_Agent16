"""
render_demo.py
--------------
SHAPE Agent 16— Narrated Demo Video Renderer  (v2 — extended)

Pure Python + Pillow + ffmpeg.  No GPU, no Blender render loop required.
Expected throughput on Intel UHD: ~10 fps → full video in ~20 min.

VIDEO LAYOUT
────────────
  Total runtime  :  ~8 minutes  (11 520 frames at 24 fps)
  Resolution     :  1920 × 1080
  Narration bar  :  Bottom 160 px — spoken text revealed word-by-word
  Progress bar   :  Bottom 4 px

SLIDES  (each ~40–60 s — paced for live narration)
────────────────────────────────────────────────────
  00  Title card                      40 s
  01  What is SHAPE                   50 s
  02  Four agent roles                60 s
  03  8-Step reasoning cycle          70 s
  04  Learning Lab walkthrough        80 s  ← new: step-by-step lesson flow
  05  Live exchange demo              70 s  ← new: mock learner ↔ agent turn
  06  Two tools                       60 s
  07  RL policy + reward table        70 s
  08  Assessment & Learner Progress   60 s
  09  LLM vs Local Fallback           50 s
  10  Hardware mock                   50 s
  11  Export Center                   50 s
  12  Closing                         50 s

USAGE
─────
    python render_demo.py                      # full ~8-minute video
    python render_demo.py --preview            # first 24 s only (preview)
    python render_demo.py --out my_video.mp4   # custom filename

REQUIREMENTS
────────────
    pip install Pillow
    ffmpeg on PATH  (Kali: already installed)

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

FPS   = 24
W, H  = 1920, 1080
NAR_H = 160          # height of narration bar at bottom
VH    = H - NAR_H    # usable visual area above narration bar

# Colour palette  (R, G, B)
BG        = (13,  13,  26)
ACCENT    = (0,   212, 255)
SECONDARY = (124, 92,  216)
POSITIVE  = (34,  197, 94)
WARNING   = (245, 158, 11)
WHITE     = (240, 240, 245)
GREY      = (100, 100, 115)
RED       = (220, 38,  38)
PANEL     = (22,  22,  48)
DIM       = (40,  40,  70)
NAR_BG    = (8,   8,   20)

# ─────────────────────────────────────────────────────────────────────────────
# FONT LOADER
# ─────────────────────────────────────────────────────────────────────────────

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf" if bold else
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

_FONTS: dict[tuple, ImageFont.FreeTypeFont] = {}

def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key not in _FONTS:
        _FONTS[key] = _load_font(size, bold)
    return _FONTS[key]


# ─────────────────────────────────────────────────────────────────────────────
# DRAWING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))

def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 2

def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

def alpha_t(frame: int, start: int, duration: int = 20) -> float:
    return ease_out((frame - start) / max(duration, 1))

def slide_x(frame: int, start: int, duration: int = 20) -> float:
    return lerp(-W * 0.55, 0, ease_out((frame - start) / max(duration, 1)))

def new_frame() -> Image.Image:
    img = Image.new("RGBA", (W, H), (*BG, 255))
    # Narration bar background
    ImageDraw.Draw(img).rectangle((0, VH, W, H), fill=(*NAR_BG, 255))
    ImageDraw.Draw(img).rectangle((0, VH, W, VH + 2), fill=(*ACCENT, 180))
    return img

def centered_text(draw: ImageDraw.Draw, text: str, y: int,
                  f: ImageFont.FreeTypeFont, color: tuple,
                  alpha: float = 1.0, x_offset: int = 0) -> None:
    bbox = draw.textbbox((0, 0), text, font=f)
    tw   = bbox[2] - bbox[0]
    x    = (W - tw) // 2 + x_offset
    r, g, b = color
    draw.text((x, y), text, font=f, fill=(r, g, b, int(255 * max(0.0, min(1.0, alpha)))))

def left_text(draw: ImageDraw.Draw, text: str, x: int, y: int,
              f: ImageFont.FreeTypeFont, color: tuple, alpha: float = 1.0) -> None:
    r, g, b = color
    draw.text((x, y), text, font=f, fill=(r, g, b, int(255 * max(0.0, min(1.0, alpha)))))

def glow_circle(img: Image.Image, cx: int, cy: int, r: int,
                color: tuple, alpha: float = 1.0) -> None:
    if alpha <= 0.01:
        return
    # Operate on a small crop instead of a full 1920×1080 overlay.
    margin = r + 56
    bx1, by1 = max(0, cx - margin), max(0, cy - margin)
    bx2, by2 = min(W, cx + margin), min(H, cy + margin)
    crop = Image.new("RGBA", (bx2 - bx1, by2 - by1), (0, 0, 0, 0))
    d    = ImageDraw.Draw(crop)
    ox, oy = cx - bx1, cy - by1
    for step in range(6, 0, -1):
        rad = r + step * 9
        a   = int(16 * alpha * (7 - step) / 6)
        d.ellipse((ox-rad, oy-rad, ox+rad, oy+rad), fill=(*color, a))
    d.ellipse((ox-r, oy-r, ox+r, oy+r), fill=(*color, int(195 * alpha)))
    img.alpha_composite(crop, dest=(bx1, by1))

def panel_rect(img: Image.Image, x1: int, y1: int, x2: int, y2: int,
               color: tuple = PANEL, alpha: float = 1.0,
               border_color: tuple | None = None, border_w: int = 2) -> None:
    if alpha <= 0.01:
        return
    # Operate on a crop sized exactly to the panel.
    px1, py1 = max(0, x1), max(0, y1)
    px2, py2 = min(W, x2), min(H, y2)
    if px2 <= px1 or py2 <= py1:   # panel is fully off-screen
        return
    crop = Image.new("RGBA", (px2 - px1, py2 - py1), (0, 0, 0, 0))
    d    = ImageDraw.Draw(crop)
    rx1, ry1 = x1 - px1, y1 - py1
    rx2, ry2 = x2 - px1, y2 - py1
    d.rectangle((rx1, ry1, rx2, ry2), fill=(*color, int(230 * alpha)))
    if border_color:
        d.rectangle((rx1, ry1, rx2, ry2),
                    outline=(*border_color, int(200 * alpha)), width=border_w)
    img.alpha_composite(crop, dest=(px1, py1))

def accent_bar_v(draw: ImageDraw.Draw, x: int, y1: int, y2: int,
                 color: tuple = ACCENT, width: int = 5) -> None:
    draw.rectangle((x, y1, x + width, y2), fill=color)

def draw_progress_bar(draw: ImageDraw.Draw, frame_in_slide: int, duration: int) -> None:
    pct    = min(1.0, frame_in_slide / max(duration, 1))
    filled = int(W * pct)
    draw.rectangle((0, H - 4, W, H), fill=DIM)
    draw.rectangle((0, H - 4, filled, H), fill=ACCENT)

def orbit_dot(img: Image.Image, cx: int, cy: int, orbit_r: int,
              angle_deg: float, dot_r: int, color: tuple, alpha: float = 1.0) -> None:
    rad = math.radians(angle_deg)
    glow_circle(img,
                int(cx + orbit_r * math.cos(rad)),
                int(cy + orbit_r * math.sin(rad)),
                dot_r, color, alpha * 0.75)


# ─────────────────────────────────────────────────────────────────────────────
# NARRATION BAR — karaoke-style word-by-word reveal
# ─────────────────────────────────────────────────────────────────────────────

# Pre-computed narration layout cache: narration_text → (all_words, line_breaks)
_NAR_CACHE: dict[str, tuple[list[str], list[int]]] = {}

def _nar_layout(narration: str) -> tuple[list[str], list[int]]:
    """Return (word_list, line_break_indices) — computed once per unique narration."""
    if narration in _NAR_CACHE:
        return _NAR_CACHE[narration]
    nf    = font(32)
    dummy = ImageDraw.Draw(Image.new("RGBA", (W, 40)))
    words = narration.split()
    breaks: list[int] = []   # word index where a new line starts
    cur   = ""
    line_count = 0
    for i, w in enumerate(words):
        test = (cur + " " + w).strip()
        bbox = dummy.textbbox((0, 0), test, font=nf)
        if bbox[2] - bbox[0] > W - 160:
            breaks.append(i)
            cur = w
            line_count += 1
            if line_count >= 2:   # max 2 lines
                break
        else:
            cur = test
    result = (words, breaks)
    _NAR_CACHE[narration] = result
    return result


def draw_narration(img: Image.Image, narration: str, frame_in_slide: int,
                   slide_duration: int) -> None:
    """
    Word-by-word karaoke reveal — no full-frame overlays, no mask images.
    Revealed words drawn in WHITE directly; pending words in dim GREY.
    """
    draw  = ImageDraw.Draw(img)
    words, breaks = _nar_layout(narration)
    if not words:
        return

    nf           = font(32)
    reveal_start = 8
    reveal_dur   = max(slide_duration - reveal_start - 12, 1)
    shown        = int(len(words) * min(1.0,
                        max(0.0, (frame_in_slide - reveal_start) / reveal_dur)))

    # Split words into at most 2 display lines
    line_words: list[list[str]] = []
    prev = 0
    for br in breaks[:1]:       # only one break allowed → 2 lines max
        line_words.append(words[prev:br])
        prev = br
    line_words.append(words[prev:])
    line_words = line_words[:2]

    y_base  = VH + 22
    line_h  = 52
    word_i  = 0   # global word counter across lines

    for li, lwords in enumerate(line_words):
        line_text = " ".join(lwords)
        bbox      = draw.textbbox((0, 0), line_text, font=nf)
        line_w    = bbox[2] - bbox[0]
        x_start   = (W - line_w) // 2
        y         = y_base + li * line_h

        # Draw word by word so we can colour each independently
        x_cursor = x_start
        for w in lwords:
            wb    = draw.textbbox((0, 0), w, font=nf)
            ww    = wb[2] - wb[0]
            color = WHITE if word_i < shown else GREY
            alpha = 255   if word_i < shown else 70
            draw.text((x_cursor, y), w, font=nf, fill=(*color, alpha))
            x_cursor += ww + draw.textbbox((0,0)," ",font=nf)[2]
            word_i += 1

    draw.text((20, VH + 8), "▶ SHAPE Agent 16", font=font(20), fill=(*ACCENT, 110))


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE DRAW FUNCTIONS
# Each receives: img, f (absolute frame), s (slide start frame)
# All content must stay within y < VH (= H - NAR_H = 920)
# ─────────────────────────────────────────────────────────────────────────────

# ── Slide 0: Title (40 s = 960 frames) ───────────────────────────────────────

def draw_title(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    for i in range(14):
        a_deg = (f - s) * 0.9 + i * 25.7
        orbit_dot(img, W//2, VH//2, 340, a_deg, 7,
                  ACCENT if i % 3 == 0 else SECONDARY,
                  alpha_t(f, s + 6, 28))
    glow_circle(img, W//2, VH//2, 100, ACCENT, alpha_t(f, s + 6, 28) * 0.38)

    centered_text(draw, "SHAPE", VH//2 - 160, font(170, bold=True),
                  ACCENT, alpha_t(f, s + 6, 28))
    centered_text(draw, "Agent 16  |  ITAI2376",
                  VH//2 + 30, font(50), WHITE, alpha_t(f, s + 28, 24))
    centered_text(draw,
        "Student-centered Handheld Architecture for Programming Education",
        VH//2 + 108, font(30), GREY, alpha_t(f, s + 50, 24))
    centered_text(draw,
        "Learning through interaction.  Improving through feedback.",
        VH//2 + 172, font(34), ACCENT, alpha_t(f, s + 72, 24))
    draw_progress_bar(draw, f - s, dur)


# ── Slide 1: What is SHAPE (50 s = 1200 frames) ───────────────────────────────

def draw_what(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    accent_bar_v(draw, 100, 100, VH - 60)
    centered_text(draw, "What is SHAPE?", 70, font(80, bold=True), ACCENT,
                  alpha_t(f, s + 6, 20))
    bullets = [
        ("Multi-agent interactive learning companion",    ACCENT),
        ("Teaches Python and AI concepts adaptively",     WHITE),
        ("Google Colab — free, no local install",         WHITE),
        ("Works with or without an LLM API key",          WHITE),
        ("Classroom prototype — not a production product",WARNING),
        ("Built by ITAI2376 students for ITAI2376",       GREY),
    ]
    for i, (line, color) in enumerate(bullets):
        a = alpha_t(f, s + 20 + i * 20, 18)
        y = 210 + i * 108
        glow_circle(img, 148, y + 24, 9, color, a * 0.7)
        left_text(draw, line, 182, y, font(44), color, a)
    draw_progress_bar(draw, f - s, dur)


# ── Slide 2: Four Agent Roles (60 s = 1440 frames) ───────────────────────────

ROLE_DATA = [
    ("Instructor",          POSITIVE,   ["Explains concepts",    "Breaks into steps",     "Adjusts complexity"]),
    ("Debugger",            WARNING,    ["Analyses code errors",  "Plain-language why",    "Graduated hints only"]),
    ("Evaluator",           ACCENT,     ["Checks exercise",       "Records attempts+hints","Computes reward"]),
    ("Learning Strategist", SECONDARY,  ["Tracks progress",       "Selects next strategy", "Shows policy live"]),
]

def draw_agents(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Four Agent Roles — One Orchestrator", 55,
                  font(70, bold=True), ACCENT, alpha_t(f, s + 6, 20))

    xs = [270, 720, 1200, 1660]
    for i, ((name, color, descs), x) in enumerate(zip(ROLE_DATA, xs)):
        a  = alpha_t(f, s + 24 + i * 22, 20)
        cy = 420
        for j in range(3):
            angle = (f - s) * (1.2 if i % 2 == 0 else -1.2) + j * 120
            orbit_dot(img, x, cy, 80, angle, 6, color, a * 0.7)
        glow_circle(img, x, cy, 44, color, a * 0.85)

        # Role name under sphere
        bbox = draw.textbbox((0,0), name, font=font(32, bold=True))
        tw   = bbox[2] - bbox[0]
        draw.text((x - tw//2, cy + 70), name, font=font(32, bold=True),
                  fill=(*color, int(255*a)))

        for j, desc in enumerate(descs):
            da   = alpha_t(f, s + 44 + i * 22, 18)
            bbox2 = draw.textbbox((0,0), desc, font=font(27))
            tw2  = bbox2[2] - bbox2[0]
            draw.text((x - tw2//2, cy + 128 + j * 52), desc, font=font(27),
                      fill=(*GREY, int(255*da)))

    # Bottom note
    centered_text(draw,
        "One LLM serves all four roles — or a labelled local fallback when no key is set",
        VH - 60, font(28), GREY, alpha_t(f, s + 110, 20))
    draw_progress_bar(draw, f - s, dur)


# ── Slide 3: 8-Step Reasoning Cycle (70 s = 1680 frames) ─────────────────────

STEPS = [
    ("1. RECEIVE",   "Validate learner input — empty, oversized, injection → rejected with explanation",  WHITE),
    ("2. PROFILE",   "Load learner level and recent history from SQLite",                                 WHITE),
    ("3. RETRIEVE",  "Tool 2: keyword search over lesson index — inject top-3 into LLM context",          ACCENT),
    ("4. REASON",    "Chain-of-Thought scratchpad + ε-greedy strategy selection",                         SECONDARY),
    ("5. ACT",       "Tool 1: AST-validate → execute code → capture output or error",                     ACCENT),
    ("6. RESPOND",   "LLM (or local fallback) generates explanation, hint, or feedback",                  POSITIVE),
    ("7. EVALUATE",  "Compute reward → Q += 0.2 × (r − Q) → persist to policy_state table",              WARNING),
    ("8. ADAPT",     "Update learner level if 3 consecutive perfect-score turns",                         WHITE),
]

def draw_cycle(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "8-Step Reasoning Cycle", 40, font(72, bold=True), ACCENT,
                  alpha_t(f, s + 6, 20))

    for i, (step, detail, color) in enumerate(STEPS):
        col  = 0 if i < 4 else 1
        row  = i % 4
        x0   = 60 + col * 975
        y0   = 155 + row * 178
        a    = alpha_t(f, s + 14 + i * 16, 18)
        ox   = slide_x(f, s + 12 + i * 16, 18) * (1 if col == 0 else -1)

        panel_rect(img, int(x0+ox), y0, int(x0+ox)+900, y0+152,
                   PANEL, a, border_color=color, border_w=3)
        left_text(draw, step,   int(x0+ox)+18, y0+16,  font(34, bold=True), color, a)
        left_text(draw, detail, int(x0+ox)+18, y0+70,  font(22), GREY, a)

    # Connecting spine down the middle
    spine_a = alpha_t(f, s + 150, 20)
    draw.rectangle((W//2-3, 140, W//2+3, VH-40),
                   fill=(*ACCENT, int(100*spine_a)))
    draw_progress_bar(draw, f - s, dur)


# ── Slide 4: Learning Lab Walkthrough (80 s = 1920 frames) ───────────────────

LAB_STEPS = [
    ("Step 1 — Select a lesson",
     "Learner picks from 6 Python fundamentals: Variables, Types,\n"
     "Conditionals, Loops, Functions, Lists.  SHAPE loads the\n"
     "lesson concept, worked example, and exercise.", ACCENT),
    ("Step 2 — Read the concept & example",
     "Instructor Agent explains the concept at the learner's current level\n"
     "(beginner / intermediate / advanced).  A worked Python example\n"
     "is shown with the expected output.", WHITE),
    ("Step 3 — Submit code",
     "Learner writes code in the editor and clicks Submit.\n"
     "The code-runner tool (Tool 1) validates it with an AST check,\n"
     "runs it in a restricted namespace, and captures output.", POSITIVE),
    ("Step 4 — Get feedback + hints",
     "If correct: Evaluator records a pass, computes reward, updates policy.\n"
     "If wrong: Debugger explains the error in plain language and gives\n"
     "a graduated hint — vague first, specific only if asked.", WARNING),
    ("Step 5 — Pre/post assessment",
     "Same 5 questions before Lesson 1 and after the last lesson.\n"
     "Post − Pre = the measurable change.  Learners use anonymous IDs only.\n"
     "Reward trend ≠ proof of learning — the assessment is the proof.", SECONDARY),
]

def draw_lab(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Learning Lab — Step by Step", 45, font(72, bold=True),
                  ACCENT, alpha_t(f, s + 6, 20))

    step_dur = dur // len(LAB_STEPS)
    active   = min((f - s) // step_dur, len(LAB_STEPS) - 1)

    for i, (title, body, color) in enumerate(LAB_STEPS):
        # Timeline dot on left spine
        dot_y = 180 + i * 148
        a_dot = alpha_t(f, s + i * step_dur, 18)
        is_active = (i == active)

        # Spine line
        if i < len(LAB_STEPS) - 1:
            draw.rectangle((119, dot_y + 20, 123, dot_y + 148), fill=(*DIM, 200))
        glow_circle(img, 121, dot_y, 16 if is_active else 10,
                    color if is_active else GREY,
                    a_dot * (1.0 if is_active else 0.5))

        # Step label + body
        label_a = a_dot * (1.0 if is_active else 0.55)
        left_text(draw, title, 158, dot_y - 18, font(34, bold=True), color, label_a)
        for li, bline in enumerate(body.splitlines()):
            body_a = alpha_t(f, s + i * step_dur + 10, 20) * (0.9 if is_active else 0.4)
            left_text(draw, bline, 162, dot_y + 26 + li * 36, font(26), WHITE, body_a)

    # Active step highlight panel
    ah_y = 162 + active * 148
    panel_rect(img, 140, ah_y - 24, W - 60, ah_y + 118,
               PANEL, alpha_t(f, s + active * step_dur, 14) * 0.6,
               border_color=LAB_STEPS[active][2])
    draw_progress_bar(draw, f - s, dur)


# ── Slide 5: Live Exchange Demo (70 s = 1680 frames) ─────────────────────────

EXCHANGE = [
    ("learner",  "Variables and Types", "Learner selects lesson → Instructor Agent activates"),
    ("agent",    "[Instructor | beginner | worked_example]\n"
                 "A variable is a named container. Try:\n"
                 "  name = 'Ada'\n  print(name)  # → Ada\n"
                 "What type does input() always return?",
                 "Instructor responds with concept + worked example + check question"),
    ("learner",  "```python\nname = input()\nprint(type(name))\n```",
                 "Learner submits code with backtick fences → triggers code-runner tool"),
    ("agent",    "[Tool 1 — code runner]\n"
                 "  Input  : name = input()\\nprint(type(name))\n"
                 "  Output : <class 'str'>\n"
                 "[Evaluator | reward +10]\n"
                 "  Correct. type(name) = <class 'str'>  ✅\n"
                 "  Reward: +10  Q(worked_example) → 0.20",
                 "Evaluator records correct attempt, computes +10 reward, updates Q"),
    ("learner",  "Why does it always return str even if I type a number?",
                 "New question → Instructor Agent, Tool 2 retrieves lesson"),
    ("agent",    "[Tool 2 — lesson retrieval]\n"
                 "  Query: 'type input str number'\n"
                 "  Match: L2 Input and Types (beginner)\n"
                 "[Instructor | beginner | concept_explanation]\n"
                 "  input() reads raw text from the keyboard.\n"
                 "  Python has no way to know if '42' means the number 42\n"
                 "  or the string '42' — that decision is yours.  Use int(input()).",
                 "Instructor grounds explanation in retrieved lesson, cites source"),
]

def draw_exchange(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw  = ImageDraw.Draw(img)
    centered_text(draw, "Live Interaction — Learner ↔ Agent", 42,
                  font(66, bold=True), ACCENT, alpha_t(f, s + 6, 20))

    turn_dur = dur // len(EXCHANGE)
    shown    = min(int((f - s) / turn_dur) + 1, len(EXCHANGE))

    y_cursor = 150
    for i in range(shown):
        role, text, caption = EXCHANGE[i]
        a   = alpha_t(f, s + i * turn_dur, 18)
        is_learner = (role == "learner")
        color  = ACCENT   if is_learner else POSITIVE
        label  = "LEARNER" if is_learner else "SHAPE AGENT"
        x0     = 80  if is_learner else 460
        x_end  = W - 80

        panel_rect(img, x0, y_cursor, x_end, y_cursor + 10, PANEL, 0)
        lines = text.splitlines()
        box_h = 36 + len(lines) * 36 + 10
        panel_rect(img, x0, y_cursor, x_end, y_cursor + box_h,
                   PANEL, a * 0.85, border_color=color, border_w=2)
        left_text(draw, label, x0 + 14, y_cursor + 8, font(22, bold=True), color, a)
        for li, line in enumerate(lines):
            left_text(draw, line, x0 + 14, y_cursor + 36 + li * 34,
                      font(22), WHITE, a * 0.9)
        # Caption underneath
        cap_a = alpha_t(f, s + i * turn_dur + 10, 16)
        left_text(draw, f"↳ {caption}", x0 + 14, y_cursor + box_h + 2,
                  font(20), GREY, cap_a * 0.8)
        y_cursor += box_h + 48

        if y_cursor > VH - 60:
            break

    draw_progress_bar(draw, f - s, dur)


# ── Slide 6: Two Tools (60 s = 1440 frames) ───────────────────────────────────

TOOL1_LINES = [
    "AST-validated before execution",
    "Restricted namespace — no os / subprocess / open",
    "5-second hard timeout (infinite loop guard)",
    "Returns: passed / stdout / error type / line number",
    "⚠  NOT a hardened sandbox — classroom tool only",
]
TOOL2_LINES = [
    "Keyword search over SQLite lesson/resource index",
    "Filters results by learner level",
    "Top-3 matches injected into LLM context window",
    "New lessons added via UI are searchable instantly",
    "Returns 'no match' + nearest lessons — never invents",
]

def draw_tools(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Two Tools", 45, font(84, bold=True), ACCENT,
                  alpha_t(f, s + 6, 20))
    draw.rectangle((W//2 - 2, 155, W//2 + 2, VH - 60), fill=(*SECONDARY, 140))

    for side, (title, color, lines) in enumerate([
        ("Tool 1 — Python Exercise Runner", POSITIVE,  TOOL1_LINES),
        ("Tool 2 — Lesson Knowledge Retrieval", ACCENT, TOOL2_LINES),
    ]):
        x0 = 80 if side == 0 else W//2 + 70
        a0 = alpha_t(f, s + 16, 20)
        left_text(draw, title, x0, 155, font(38, bold=True), color, a0)
        cy = 320
        glow_circle(img, x0 + 55, cy, 40, color, a0 * 0.75)
        for i, line in enumerate(lines):
            a = alpha_t(f, s + 28 + i * 18, 16)
            col = WARNING if "⚠" in line else WHITE
            left_text(draw, f"·  {line}", x0, 420 + i * 94, font(30), col, a)

    # Selection logic label at bottom
    logic_a = alpha_t(f, s + 130, 20)
    centered_text(draw,
        "Agent decides which tool to use and interprets the result — the orchestrator logs every call",
        VH - 55, font(26), GREY, logic_a)
    draw_progress_bar(draw, f - s, dur)


# ── Slide 7: RL Policy (70 s = 1680 frames) ───────────────────────────────────

REWARDS = [
    ("Correct — no hints",        "+10", POSITIVE),
    ("Correct — 1 hint",          " +7", POSITIVE),
    ("Correct — multiple hints",  " +4", WARNING),
    ("Failed attempt",            " −3", RED),
    ("Concept check failed",      " −1", WARNING),
]
STRATEGIES = ["worked example", "concept explanation",
              "small hint", "simpler practice", "challenge exercise"]

def draw_rl(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Adaptive RL Policy — ε-Greedy Contextual Bandit", 42,
                  font(60, bold=True), ACCENT, alpha_t(f, s + 6, 20))

    # Reward table
    left_text(draw, "Reward Function", 100, 148, font(44, bold=True), WHITE,
              alpha_t(f, s + 16, 18))
    for i, (outcome, reward, color) in enumerate(REWARDS):
        a = alpha_t(f, s + 24 + i * 16, 16)
        y = 232 + i * 100
        panel_rect(img, 88, y, 870, y + 82, PANEL, a, border_color=color)
        left_text(draw, outcome, 112, y + 22, font(32), WHITE, a)
        left_text(draw, reward,  780, y + 14, font(44, bold=True), color, a)

    # Q-update equation
    a_eq = alpha_t(f, s + 100, 24)
    panel_rect(img, 920, 160, W - 60, 330, PANEL, a_eq, border_color=ACCENT, border_w=3)
    centered_text(draw, "Q  +=  0.2  ×  ( reward − Q )",
                  188, font(46, bold=True), ACCENT, a_eq, x_offset=200)
    centered_text(draw, "α = 0.2  (learning rate)      ε = 0.15  (exploration rate)",
                  268, font(26), GREY, a_eq, x_offset=200)

    # Strategy orbit
    for i, strat in enumerate(STRATEGIES):
        a    = alpha_t(f, s + 120 + i * 14, 16)
        angle = (2*math.pi*i/len(STRATEGIES)) - math.pi/2
        cx   = 1310 + int(math.cos(angle) * 240)
        cy   = 580  + int(math.sin(angle) * 170)
        panel_rect(img, cx-170, cy-30, cx+170, cy+30, PANEL, a, border_color=SECONDARY)
        bbox = draw.textbbox((0,0), strat, font=font(26))
        tw   = bbox[2]-bbox[0]
        draw.text((cx - tw//2, cy - 14), strat, font=font(26),
                  fill=(*SECONDARY, int(255*a)))

    # Policy-state table header
    ph_a = alpha_t(f, s + 110, 20)
    left_text(draw, "policy_state table (SQLite)", 920, 350, font(32, bold=True),
              WHITE, ph_a)
    for i, strat in enumerate(STRATEGIES):
        q_demo = round(0.0 + i * 0.04, 2)   # illustrative starting values
        left_text(draw,
            f"  {strat:<25}  Q = {q_demo:.2f}",
            930, 400 + i*52, font(26), GREY, ph_a)

    caution_a = alpha_t(f, s + 190, 20)
    centered_text(draw,
        "⚠  Rising reward ≠ proof of learning — verified by pre/post assessment",
        VH - 55, font(26), WARNING, caution_a)
    draw_progress_bar(draw, f - s, dur)


# ── Slide 8: Assessment & Progress (60 s = 1440 frames) ──────────────────────

def draw_assess(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Assessment & Learner Progress", 45, font(66, bold=True),
                  ACCENT, alpha_t(f, s + 6, 20))
    draw.rectangle((W//2 - 2, 148, W//2 + 2, VH - 60), fill=(*SECONDARY, 140))

    left_text(draw, "Pre / Post Assessment", 100, 148, font(42, bold=True), WHITE,
              alpha_t(f, s + 16, 18))
    assess_lines = [
        ("Same 5 questions both times", WHITE),
        ("Score before Lesson 1  →  pre-test", WHITE),
        ("Score after last lesson  →  post-test", WHITE),
        ("post − pre = measurable change", POSITIVE),
        ("Delayed retention check if time allows", GREY),
        ("Anonymised IDs only — no real names", ACCENT),
    ]
    for i, (line, color) in enumerate(assess_lines):
        a = alpha_t(f, s + 24 + i * 16, 16)
        left_text(draw, f"·  {line}", 112, 240 + i * 100, font(32), color, a)

    left_text(draw, "Learner Progress Metrics", W//2 + 80, 148, font(42, bold=True),
              ACCENT, alpha_t(f, s + 22, 18))
    metrics = [
        ("Attempts",         "total code submissions"),
        ("Correctness",      "first-attempt pass rate (%)"),
        ("Hint dependency",  "mean hints used per correct exercise"),
        ("Completion rate",  "lessons done ÷ lessons started"),
        ("Reward total",     "cumulative policy signal (not a grade)"),
    ]
    for i, (metric, detail) in enumerate(metrics):
        am = alpha_t(f, s + 32 + i * 18, 16)
        y  = 240 + i * 125
        left_text(draw, metric, W//2 + 100, y,      font(36, bold=True), ACCENT, am)
        left_text(draw, detail, W//2 + 100, y + 50, font(26), GREY, am)

    syn_a = alpha_t(f, s + 170, 20)
    centered_text(draw,
        "★  SYNTHETIC DEMO DATA  ★  charts in app are labelled as such",
        VH - 55, font(26), WARNING, syn_a)
    draw_progress_bar(draw, f - s, dur)


# ── Slide 9: LLM vs Fallback (50 s = 1200 frames) ────────────────────────────

LLM_LINES = [
    "OpenAI key stored in Colab Secrets",
    "Read via userdata.get('OPENAI_API_KEY')",
    "Never printed, logged, or written to disk",
    "Generates explanations, hints, feedback",
    "Does NOT write grades or change rewards",
    "Labelled 'LLM' in Agent Workspace tab",
]
FB_LINES = [
    "No key — or key fails / quota exhausted",
    "Rules-based templates from lesson index",
    "Every response labelled 'Local fallback'",
    "Label reads: NOT an LLM",
    "Covers all 4 agent roles fully",
    "Demo works completely in fallback mode",
]

def draw_fallback(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "LLM Mode  vs  Local Fallback", 45, font(68, bold=True),
                  ACCENT, alpha_t(f, s + 6, 20))

    for side, (title, color, lines) in enumerate([
        ("LLM Mode",       POSITIVE, LLM_LINES),
        ("Local Fallback", WARNING,  FB_LINES),
    ]):
        x0 = 90 if side == 0 else W//2 + 90
        a0 = alpha_t(f, s + 16, 20)
        left_text(draw, title, x0, 158, font(54, bold=True), color, a0)
        for i, line in enumerate(lines):
            a = alpha_t(f, s + 26 + i * 16, 16)
            left_text(draw, f"·  {line}", x0, 266 + i * 102, font(30), WHITE, a)

    draw.rectangle((W//2 - 2, 148, W//2 + 2, VH - 60), fill=(*DIM, 200))
    a_vs = alpha_t(f, s + 46, 18)
    glow_circle(img, W//2, VH//2, 50, SECONDARY, a_vs * 0.65)
    centered_text(draw, "VS", VH//2 - 34, font(60, bold=True), SECONDARY, a_vs)
    draw_progress_bar(draw, f - s, dur)


# ── Slide 10: Hardware Mock (50 s = 1200 frames) ──────────────────────────────

JSON_REQ  = ('{ "device_id": "cyd-01",\n'
             '  "event":     "lesson_select",\n'
             '  "lesson_id": "L1",\n'
             '  "action":    "next",\n'
             '  "timestamp": "2026-12-01T10:00:00Z" }')
JSON_RESP = ('{ "device_id": "cyd-01",\n'
             '  "event":     "prompt",\n'
             '  "lesson_id": "L1",\n'
             '  "action":    "Variables and Types",\n'
             '  "timestamp": "2026-12-01T10:00:01Z" }')

def draw_hw(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Hardware — Mock Mode", 45, font(76, bold=True), ACCENT,
                  alpha_t(f, s + 6, 20))

    devices = [("Pi Zero 2 W", GREY, 230), ("Pico W", GREY, 580),
               ("CYD Display", SECONDARY, 930)]
    for name, color, cx in devices:
        a = alpha_t(f, s + 14, 20)
        panel_rect(img, cx-110, 170, cx+110, 390, PANEL, a, border_color=color)
        glow_circle(img, cx, 220, 22, ACCENT, a * 0.55)
        bbox = draw.textbbox((0,0), name, font=font(28, bold=True))
        tw   = bbox[2]-bbox[0]
        draw.text((cx - tw//2, 410), name, font=font(28, bold=True),
                  fill=(*color, int(255*a)))

    # Request arrow and card
    a_req = alpha_t(f, s + 44, 20)
    ax    = int(lerp(1060, 1200, ease_out((f - s - 44) / 20)))
    draw.rectangle((1050, 268, ax, 274), fill=(*ACCENT, int(220*a_req)))
    draw.polygon([(ax, 258), (ax+22, 271), (ax, 284)],
                 fill=(*ACCENT, int(220*a_req)))
    left_text(draw, "JSON event →", 1050, 230, font(24), ACCENT, a_req)
    panel_rect(img, 1230, 180, W-50, 450, PANEL, a_req, border_color=POSITIVE)
    for i, line in enumerate(JSON_REQ.splitlines()):
        left_text(draw, line, 1250, 206 + i*52, font(24), POSITIVE, a_req)

    # Response arrow and card
    a_resp = alpha_t(f, s + 100, 20)
    rx     = int(lerp(1230, 1060, ease_out((f - s - 100) / 20)))
    draw.rectangle((rx, 530, 1230, 536), fill=(*SECONDARY, int(220*a_resp)))
    draw.polygon([(rx, 520), (rx-22, 533), (rx, 546)],
                 fill=(*SECONDARY, int(220*a_resp)))
    left_text(draw, "← JSON response", 1050, 560, font(24), SECONDARY, a_resp)
    panel_rect(img, 1230, 490, W-50, 740, PANEL, a_resp, border_color=SECONDARY)
    for i, line in enumerate(JSON_RESP.splitlines()):
        left_text(draw, line, 1250, 514 + i*52, font(24), SECONDARY, a_resp)

    note_a = alpha_t(f, s + 130, 20)
    centered_text(draw,
        "No LLM runs on device  ·  Host runs everything  ·  Mock events labelled as mock",
        VH - 55, font(26), WARNING, note_a)
    draw_progress_bar(draw, f - s, dur)


# ── Slide 11: Export Center (50 s = 1200 frames) ──────────────────────────────

EXPORTS = [
    ("Contributions CSV",   POSITIVE,
     "One row per team contribution.\nAll four members, all categories."),
    ("Evaluation CSV",      ACCENT,
     "Attempt records from shape.db.\nCorrect, hints used, reward, strategy."),
    ("Progress CSV",        SECONDARY,
     "Learner progress per lesson.\nCompletion, accuracy, hint dependency."),
    ("Report Drafts (.md)", WARNING,
     "Four individual report drafts.\nMissing evidence flagged, not invented."),
]

def draw_export(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Export Center", 45, font(84, bold=True), ACCENT,
                  alpha_t(f, s + 6, 20))

    xs = [240, 720, 1200, 1680]
    for i, ((name, color, body), x) in enumerate(zip(EXPORTS, xs)):
        a   = alpha_t(f, s + 16 + i * 20, 18)
        ox  = slide_x(f, s + 14 + i * 20, 18)
        px  = int(x + ox)
        panel_rect(img, px-170, 180, px+170, 540, PANEL, a, border_color=color)
        draw.rectangle((px-170, 180, px+170, 234), fill=(*color, int(200*a)))
        bbox = draw.textbbox((0,0), name, font=font(26, bold=True))
        tw   = bbox[2]-bbox[0]
        draw.text((px - tw//2, 254), name, font=font(26, bold=True),
                  fill=(*color, int(255*a)))
        for li, bline in enumerate(body.splitlines()):
            ba = alpha_t(f, s + 36 + i * 20, 16)
            bb = draw.textbbox((0,0), bline, font=font(23))
            btw = bb[2]-bb[0]
            draw.text((px - btw//2, 318 + li*54), bline, font=font(23),
                      fill=(*GREY, int(255*ba)))

    rule_a = alpha_t(f, s + 110, 20)
    centered_text(draw,
        "Generated from ACTUAL contribution records  ·  Missing evidence flagged, not invented",
        VH - 55, font(26), WARNING, rule_a)
    draw_progress_bar(draw, f - s, dur)


# ── Slide 12: Closing (50 s = 1200 frames) ────────────────────────────────────

def draw_closing(img: Image.Image, f: int, s: int, dur: int) -> None:
    draw = ImageDraw.Draw(img)
    for i in range(18):
        angle = (2*math.pi*i/18)
        r     = 350 + 44*(i%3)
        cx    = W//2 + int(math.cos(angle)*r)
        cy    = VH//2 + int(math.sin(angle)*r*0.52)
        a_st  = alpha_t(f, s+10, 28) * (0.55 + 0.45*math.sin(math.radians((f-s)*3+i*20)))
        glow_circle(img, cx, cy, 5, ACCENT if i%3 else SECONDARY, a_st)

    glow_circle(img, W//2, VH//2, 110, ACCENT, alpha_t(f, s+40, 28)*0.3)

    centered_text(draw, "Learning through interaction.", VH//2-200,
                  font(64), ACCENT, alpha_t(f, s+8, 24))
    centered_text(draw, "Improving through feedback.", VH//2-110,
                  font(64), ACCENT, alpha_t(f, s+28, 24))
    centered_text(draw, "SHAPE Agent 16", VH//2+10,
                  font(100, bold=True), WHITE, alpha_t(f, s+48, 26))
    centered_text(draw, "ITAI2376  ·  Houston Community College  ·  Group 14562",
                  VH//2+140, font(34), GREY, alpha_t(f, s+68, 24))
    centered_text(draw, "Michael Rivas  ·  Cherluk  ·  Olu  ·  Taki",
                  VH//2+200, font(34), SECONDARY, alpha_t(f, s+86, 24))
    draw_progress_bar(draw, f - s, dur)


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE TABLE  — (duration in seconds × FPS = frames)
# ─────────────────────────────────────────────────────────────────────────────

def _build_slides() -> list[dict]:
    specs = [
        # (draw_fn,       dur_s, narration_text)
        (draw_title,   40,
         "SHAPE Agent 16. Student-centered Handheld Architecture for Programming Education. "
         "Learning through interaction. Improving through feedback. "
         "Built by Group 14562 at Houston Community College."),
        (draw_what,    50,
         "SHAPE is a multi-agent interactive learning companion that teaches Python and AI "
         "concepts adaptively. It runs entirely in Google Colab with no local install, "
         "works with or without an LLM API key, and is a classroom prototype — "
         "not a production product."),
        (draw_agents,  60,
         "One orchestrator coordinates four specialised agent roles. "
         "The Instructor explains concepts at the learner's level. "
         "The Debugger analyses code errors and gives graduated hints — never the full answer. "
         "The Evaluator records attempts and computes the reward. "
         "The Learning Strategist selects the next teaching strategy from the policy."),
        (draw_cycle,   70,
         "Every interaction runs the eight-step reasoning cycle. "
         "Receive and validate input. Load the learner profile. "
         "Retrieve relevant lessons with Tool 2. "
         "Plan with Chain-of-Thought and select a strategy. "
         "Execute Tool 1 if code was submitted. "
         "Generate a response with the LLM or the local fallback. "
         "Compute the reward and update the Q-table. "
         "Adapt the learner's level if three consecutive perfect turns."),
        (draw_lab,     80,
         "In the Learning Lab the learner selects one of six Python fundamentals lessons. "
         "The Instructor Agent loads the concept, worked example, and exercise. "
         "The learner submits code. Tool 1 validates and runs it. "
         "If correct, the Evaluator records a pass. "
         "If wrong, the Debugger explains in plain language and gives a hint. "
         "Pre-test before Lesson 1 and post-test after the last lesson measure the change."),
        (draw_exchange, 70,
         "Here is a live interaction. The learner selects a lesson. "
         "The Instructor responds with a concept and a worked example. "
         "The learner submits code inside backtick fences. "
         "Tool 1 runs it. The Evaluator records correct, reward plus ten. "
         "The learner asks a follow-up question. "
         "Tool 2 retrieves the matching lesson. "
         "The Instructor grounds the explanation in the retrieved content and cites it."),
        (draw_tools,   60,
         "Two tools power the agents. "
         "Tool 1 is the Python exercise runner. "
         "It AST-validates the code, runs it in a restricted namespace, "
         "and enforces a five-second timeout. "
         "It is not a hardened sandbox — it is a classroom exercise tool. "
         "Tool 2 is the lesson knowledge retrieval tool. "
         "It keyword-searches the curated lesson index in SQLite "
         "and injects the top three matches into the LLM context."),
        (draw_rl,      70,
         "The Learning Strategist uses a contextual bandit policy. "
         "Correct without hints earns plus ten. Correct with one hint earns plus seven. "
         "Failed attempts earn minus three. "
         "The Q update rule is: Q plus equals zero point two times reward minus Q. "
         "Five strategies are tracked: worked example, concept explanation, small hint, "
         "simpler practice, and challenge exercise. "
         "A rising reward is a policy signal — not proof of learning. "
         "Learning is measured by the pre and post assessments."),
        (draw_assess,  60,
         "Every attempt is recorded automatically — correctness, hints used, and completion. "
         "The pre-test runs before Lesson 1. The post-test runs after the last lesson. "
         "Post minus pre is the measurable change. "
         "Learners are identified only by anonymised IDs. "
         "No real names, emails, or student IDs are stored anywhere."),
        (draw_fallback, 50,
         "SHAPE works completely without an API key. "
         "In LLM mode the key is read from Colab Secrets and never printed or logged. "
         "When no key is available, or when an API call fails, "
         "SHAPE switches to rules-based local fallback. "
         "Every response in the Agent Workspace is labelled LLM or Local fallback. "
         "The fallback is always clearly identified as not an LLM."),
        (draw_hw,      50,
         "Hardware integration runs in mock mode by default. "
         "Raspberry Pi Zero 2 W, Pico W, and CYD display boards send small JSON events "
         "to the central host over Wi-Fi. "
         "The host runs the LLM and orchestration. No LLM runs on a handheld device. "
         "A mock device panel sends the same events as real hardware "
         "so the demo works with no physical devices present."),
        (draw_export,  50,
         "The Export Center generates four files from actual records in shape dot db. "
         "Contributions CSV, Evaluation CSV, Learner Progress CSV, "
         "and four individual report drafts in Markdown. "
         "Report drafts are generated only from contribution records members actually entered. "
         "Missing evidence is flagged explicitly — nothing is invented or filled in."),
        (draw_closing, 50,
         "Learning through interaction. Improving through feedback. "
         "SHAPE Agent 16. ITAI2376, Houston Community College, Group 14562. "
         "Michael Rivas, Cherluk, Olu, Taki. Thank you."),
    ]
    slides = []
    cursor = 0
    for fn, dur_s, narr in specs:
        dur_f = dur_s * FPS
        slides.append({
            "start": cursor,
            "end":   cursor + dur_f,
            "dur":   dur_f,
            "fn":    fn,
            "narr":  narr,
        })
        cursor += dur_f
    return slides

SLIDES = _build_slides()
TOTAL  = SLIDES[-1]["end"]


def active_slide(frame: int) -> dict:
    for slide in reversed(SLIDES):
        if frame >= slide["start"]:
            return slide
    return SLIDES[0]


# ─────────────────────────────────────────────────────────────────────────────
# SRT WRITER
# ─────────────────────────────────────────────────────────────────────────────

def write_srt(out_dir: Path) -> None:
    def tc(frame: int) -> str:
        s   = frame / FPS
        h   = int(s // 3600)
        m   = int((s % 3600) // 60)
        sec = int(s % 60)
        ms  = int((s % 1) * 1000)
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

    lines = []
    for i, slide in enumerate(SLIDES):
        lines += [
            str(i + 1),
            f"{tc(slide['start'] + 1)} --> {tc(slide['end'])}",
            slide["narr"],
            "",
        ]
    path = out_dir / "SHAPE_Agent16_Demo.srt"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  SRT : {path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="SHAPE Agent 16 — video renderer v2")
    parser.add_argument("--preview", action="store_true",
                        help="Render first 24 s only (576 frames)")
    parser.add_argument("--out", default="SHAPE_Agent16_Demo.mp4")
    args = parser.parse_args()

    total_frames = 576 if args.preview else TOTAL
    out_path     = Path(args.out)
    total_s      = total_frames / FPS

    print(f"\n{'='*60}")
    print(f"  SHAPE Agent 16 — Narrated Demo Video Renderer  v2")
    print(f"  Slides  : {len(SLIDES)}")
    print(f"  Frames  : {total_frames}  ({total_s:.0f} s / {total_s/60:.1f} min)")
    print(f"  Output  : {out_path}")
    print(f"{'='*60}\n")

    # Pre-warm fonts
    for sz in [20, 22, 23, 24, 26, 27, 28, 30, 32, 34, 36, 38, 42, 44,
               46, 50, 52, 54, 60, 64, 66, 68, 70, 72, 76, 80, 84, 90, 100, 170]:
        font(sz, False); font(sz, True)

    render_dir = Path(__file__).parent / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    write_srt(render_dir)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgba",
        "-r", str(FPS), "-i", "pipe:0",
        "-vcodec", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "18",
        str(out_path),
    ]
    try:
        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("ERROR: ffmpeg not found.  sudo apt install ffmpeg")
        sys.exit(1)

    t0 = time.perf_counter()
    for frame in range(1, total_frames + 1):
        slide = active_slide(frame)
        img   = new_frame()
        slide["fn"](img, frame, slide["start"], slide["dur"])
        draw_narration(img, slide["narr"], frame - slide["start"], slide["dur"])
        proc.stdin.write(img.tobytes())

        if frame % FPS == 0:
            elapsed = time.perf_counter() - t0
            fps_now = frame / elapsed
            remain  = (elapsed / frame) * (total_frames - frame)
            pct     = 100.0 * frame / total_frames
            print(f"  {frame:5d}/{total_frames}  {pct:5.1f}%  "
                  f"{fps_now:5.0f} fps  ETA {remain/60:4.1f} min")

    proc.stdin.close()
    proc.wait()
    total_time = time.perf_counter() - t0

    print(f"\n✅  Done in {total_time/60:.1f} min  ({total_frames/total_time:.0f} fps avg)")
    print(f"   Video : {out_path.resolve()}")
    print(f"   SRT   : {(render_dir/'SHAPE_Agent16_Demo.srt').resolve()}")
    if args.preview:
        print(f"\n  Preview looks good? Run without --preview for the full {TOTAL/FPS/60:.0f}-minute video.\n")


if __name__ == "__main__":
    main()
