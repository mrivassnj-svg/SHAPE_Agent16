"""
render_demo.py
--------------
SHAPE Agent 16 — Fast Python video renderer.
No Blender render loop. No GPU required. Runs on any machine.

Uses Pillow to draw each frame and pipes directly into ffmpeg.
Expected throughput: 100–300 frames/second → full 2400-frame video in ~15 seconds.

USAGE
-----
    python render_demo.py                      # renders SHAPE_Agent16_Demo.mp4
    python render_demo.py --preview            # renders first 10 s only (240 frames)
    python render_demo.py --out my_video.mp4   # custom output filename

REQUIREMENTS
------------
    pip install Pillow
    ffmpeg must be on PATH (already installed on Kali)

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

from __future__ import annotations

import argparse
import io
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

FPS    = 24
W, H   = 1920, 1080
TOTAL  = 2400          # 100 s

# Colour palette  (R, G, B)
BG         = (13,  13,  26)
ACCENT     = (0,   212, 255)
SECONDARY  = (124, 92,  216)
POSITIVE   = (34,  197, 94)
WARNING    = (245, 158, 11)
WHITE      = (240, 240, 245)
GREY       = (100, 100, 115)
RED        = (220, 38,  38)
PANEL      = (22,  22,  48)
DIM        = (40,  40,  70)

# ─────────────────────────────────────────────────────────────────────────────
# FONT LOADER  (falls back to built-in if no system font found)
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

# Pre-load font sizes used throughout
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
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t


def ease_out(t: float) -> float:
    """Quadratic ease-out: fast start, smooth stop."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 2


def alpha_t(frame: int, start: int, duration: int = 12) -> float:
    """0→1 fade-in alpha over `duration` frames starting at `start`."""
    return ease_out((frame - start) / max(duration, 1))


def slide_x(frame: int, start: int, duration: int = 14) -> float:
    """Slide-in offset: returns 0 when complete, negative (off-screen) at start."""
    t = ease_out((frame - start) / max(duration, 1))
    return lerp(-W * 0.6, 0, t)


def centered_text(draw: ImageDraw.Draw, text: str, y: int, f: ImageFont.FreeTypeFont,
                  color: tuple, alpha: float = 1.0, x_offset: int = 0) -> None:
    bbox  = draw.textbbox((0, 0), text, font=f)
    tw    = bbox[2] - bbox[0]
    x     = (W - tw) // 2 + x_offset
    r, g, b = color
    a = int(255 * max(0.0, min(1.0, alpha)))
    draw.text((x, y), text, font=f, fill=(r, g, b, a))


def left_text(draw: ImageDraw.Draw, text: str, x: int, y: int,
              f: ImageFont.FreeTypeFont, color: tuple, alpha: float = 1.0) -> None:
    r, g, b = color
    a = int(255 * max(0.0, min(1.0, alpha)))
    draw.text((x, y), text, font=f, fill=(r, g, b, a))


def glow_circle(img: Image.Image, cx: int, cy: int, r: int,
                color: tuple, alpha: float = 1.0) -> None:
    """Draw a soft radial glow by layering translucent circles."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for step in range(6, 0, -1):
        rad  = r + step * 8
        a    = int(18 * alpha * (7 - step) / 6)
        d.ellipse((cx - rad, cy - rad, cx + rad, cy + rad),
                  fill=(*color, a))
    d.ellipse((cx - r, cy - r, cx + r, cy + r),
              fill=(*color, int(200 * alpha)))
    img.alpha_composite(overlay)


def panel_rect(img: Image.Image, x1: int, y1: int, x2: int, y2: int,
               color: tuple = PANEL, alpha: float = 1.0,
               border_color: tuple | None = None) -> None:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    a = int(230 * alpha)
    d.rectangle((x1, y1, x2, y2), fill=(*color, a))
    if border_color:
        d.rectangle((x1, y1, x2, y2), outline=(*border_color, int(200 * alpha)),
                    width=2)
    img.alpha_composite(overlay)


def accent_bar(draw: ImageDraw.Draw, x: int, y1: int, y2: int,
               color: tuple = ACCENT, width: int = 4) -> None:
    draw.rectangle((x, y1, x + width, y2), fill=color)


def draw_progress_bar(draw: ImageDraw.Draw, frame: int, total: int) -> None:
    """Thin progress bar at the very bottom of the frame."""
    filled = int(W * frame / total)
    draw.rectangle((0, H - 4, W, H), fill=DIM)
    draw.rectangle((0, H - 4, filled, H), fill=ACCENT)


def orbit_dot(img: Image.Image, cx: int, cy: int, orbit_r: int,
              angle_deg: float, dot_r: int, color: tuple,
              alpha: float = 1.0) -> None:
    rad = math.radians(angle_deg)
    x   = int(cx + orbit_r * math.cos(rad))
    y   = int(cy + orbit_r * math.sin(rad))
    glow_circle(img, x, y, dot_r, color, alpha * 0.7)


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE DEFINITIONS  (start_frame, end_frame, draw_fn)
# ─────────────────────────────────────────────────────────────────────────────

def new_frame() -> Image.Image:
    return Image.new("RGBA", (W, H), (*BG, 255))


# ── Slide 0: Title ────────────────────────────────────────────────────────────

def draw_title(img: Image.Image, f: int, s: int) -> None:
    draw = ImageDraw.Draw(img)
    # Orbiting ring dots
    for i in range(12):
        a_deg = (f - s) * 1.2 + i * 30
        orbit_dot(img, W // 2, H // 2, 320, a_deg, 6,
                  ACCENT if i % 3 == 0 else SECONDARY, alpha_t(f, s, 20))

    # Central glow
    glow_circle(img, W // 2, H // 2, 80, ACCENT, alpha_t(f, s, 20) * 0.4)

    a0 = alpha_t(f, s + 4, 20)
    centered_text(draw, "SHAPE", H // 2 - 130, font(140, bold=True), ACCENT, a0)

    a1 = alpha_t(f, s + 20, 16)
    centered_text(draw, "Agent 16  |  ITAI2376", H // 2 + 30, font(44), WHITE, a1)

    a2 = alpha_t(f, s + 36, 16)
    centered_text(draw,
        "Student-centered Handheld Architecture for Programming Education",
        H // 2 + 100, font(28), GREY, a2)

    a3 = alpha_t(f, s + 52, 16)
    centered_text(draw,
        "Learning through interaction.  Improving through feedback.",
        H // 2 + 165, font(32), ACCENT, a3)

    draw_progress_bar(draw, f - s, 72)


# ── Slide 1: What is SHAPE ────────────────────────────────────────────────────

def draw_what(img: Image.Image, f: int, s: int) -> None:
    draw = ImageDraw.Draw(img)
    accent_bar(draw, 100, 120, H - 80, ACCENT, 5)

    a0 = alpha_t(f, s + 4, 14)
    left_text(draw, "What is SHAPE?", 130, 110, font(72, bold=True), ACCENT, a0)

    bullets = [
        "Multi-agent interactive learning companion",
        "Teaches Python + AI concepts adaptively",
        "Runs in Google Colab — free, no install",
        "Works with or without an LLM API key",
        "Built by ITAI2376 students for ITAI2376 students",
    ]
    for i, line in enumerate(bullets):
        a = alpha_t(f, s + 20 + i * 14, 12)
        y = 240 + i * 100
        glow_circle(img, 148, y + 20, 8, ACCENT, a * 0.8)
        left_text(draw, line, 180, y, font(42), WHITE, a)

    draw_progress_bar(draw, f - s, 168)


# ── Slide 2: Four Agent Roles ─────────────────────────────────────────────────

ROLE_DATA = [
    ("Instructor",          POSITIVE,   ["Explains concepts", "Breaks into steps", "Adjusts complexity"]),
    ("Debugger",            WARNING,    ["Analyses code errors", "Plain-language why", "Graduated hints only"]),
    ("Evaluator",           ACCENT,     ["Checks exercise results", "Records attempts+hints", "Computes reward signal"]),
    ("Learning Strategist", SECONDARY,  ["Tracks learner progress", "Selects next strategy", "Shows policy before/after"]),
]

def draw_agents(img: Image.Image, f: int, s: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Four Agent Roles", 60, font(72, bold=True), ACCENT,
                  alpha_t(f, s + 4, 14))

    xs = [260, 700, 1220, 1660]
    for i, ((name, color, descs), x) in enumerate(zip(ROLE_DATA, xs)):
        a = alpha_t(f, s + 18 + i * 16, 14)
        cy = 380
        # Orbiting glow
        angle = (f - s) * (1.5 if i % 2 == 0 else -1.5) + i * 90
        orbit_dot(img, x, cy, 70, angle, 7, color, a * 0.9)
        glow_circle(img, x, cy, 38, color, a * 0.85)
        # Role name
        bbox = draw.textbbox((0,0), name, font=font(30, bold=True))
        tw = bbox[2] - bbox[0]
        draw.text((x - tw//2, cy + 65), name, font=font(30, bold=True),
                  fill=(*color, int(255*a)))
        # Description lines
        for j, desc in enumerate(descs):
            da = alpha_t(f, s + 30 + i * 16, 12)
            bbox2 = draw.textbbox((0,0), desc, font=font(24))
            tw2 = bbox2[2] - bbox2[0]
            draw.text((x - tw2//2, cy + 115 + j * 44), desc,
                      font=font(24), fill=(*GREY, int(255*da)))

    note_a = alpha_t(f, s + 90, 14)
    centered_text(draw,
        "One LLM serves all four roles — or a labelled local fallback when no key is set",
        H - 90, font(28), GREY, note_a)
    draw_progress_bar(draw, f - s, 240)


# ── Slide 3: 8-Step Reasoning Cycle ──────────────────────────────────────────

STEPS = [
    ("1. RECEIVE",   "Validate learner input",         WHITE),
    ("2. PROFILE",   "Load learner level & history",   WHITE),
    ("3. RETRIEVE",  "Tool 2: lesson keyword search",  ACCENT),
    ("4. REASON",    "CoT scratchpad + strategy pick",  SECONDARY),
    ("5. ACT",       "Tool 1: code runner",             ACCENT),
    ("6. RESPOND",   "LLM or local fallback reply",     POSITIVE),
    ("7. EVALUATE",  "Reward → Q-update",               WARNING),
    ("8. ADAPT",     "Update learner profile / level",  WHITE),
]

def draw_cycle(img: Image.Image, f: int, s: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "8-Step Reasoning Cycle", 40, font(66, bold=True), ACCENT,
                  alpha_t(f, s + 4, 14))

    for i, (step, detail, color) in enumerate(STEPS):
        col   = 0 if i < 4 else 1
        row   = i % 4
        x0    = 80  + col * 970
        y0    = 160 + row * 200
        a     = alpha_t(f, s + 10 + i * 12, 12)
        ox    = slide_x(f, s + 8 + i * 12, 14) * (1 if col == 0 else -1)

        panel_rect(img, int(x0 + ox), y0, int(x0 + ox) + 860, y0 + 160,
                   PANEL, a, border_color=color)
        left_text(draw, step,   int(x0 + ox) + 20, y0 + 18,  font(34, bold=True), color, a)
        left_text(draw, detail, int(x0 + ox) + 20, y0 + 72,  font(28), GREY, a)

    draw_progress_bar(draw, f - s, 288)


# ── Slide 4: Two Tools ────────────────────────────────────────────────────────

TOOL1_LINES = [
    "AST-validated before execution",
    "No os / subprocess / open allowed",
    "5-second hard timeout guard",
    "Returns pass / fail / error / line",
    "NOT a hardened sandbox — classroom tool",
]
TOOL2_LINES = [
    "Keyword search over SQLite lesson index",
    "Filters by learner level",
    "Top-3 matches injected into LLM context",
    "New lessons added via UI are live instantly",
    "Graceful no-match fallback",
]

def draw_tools(img: Image.Image, f: int, s: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Two Tools", 50, font(80, bold=True), ACCENT,
                  alpha_t(f, s + 4, 14))

    # Divider
    draw.rectangle((W//2 - 2, 160, W//2 + 2, H - 80), fill=SECONDARY)

    for side, (title, color, lines) in enumerate([
        ("Tool 1 — Python Exercise Runner", POSITIVE,  TOOL1_LINES),
        ("Tool 2 — Lesson Retrieval",        ACCENT,    TOOL2_LINES),
    ]):
        x0 = 80 if side == 0 else W // 2 + 60
        a0 = alpha_t(f, s + 14, 14)
        left_text(draw, title, x0, 155, font(36, bold=True), color, a0)
        cy = 310
        glow_circle(img, x0 + 50, cy, 36, color, a0 * 0.8)
        for i, line in enumerate(lines):
            a = alpha_t(f, s + 24 + i * 14, 12)
            left_text(draw, f"·  {line}", x0, 400 + i * 100, font(32), WHITE, a)

    draw_progress_bar(draw, f - s, 288)


# ── Slide 5: RL Policy ────────────────────────────────────────────────────────

REWARDS = [
    ("Correct — no hints",        "+10", POSITIVE),
    ("Correct — 1 hint",          " +7", POSITIVE),
    ("Correct — multiple hints",  " +4", WARNING),
    ("Failed attempt",            " −3", RED),
    ("Concept check failed",      " −1", WARNING),
]

def draw_rl(img: Image.Image, f: int, s: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Adaptive RL Policy", 50, font(72, bold=True), ACCENT,
                  alpha_t(f, s + 4, 14))

    left_text(draw, "Reward Function", 100, 160, font(42, bold=True), WHITE,
              alpha_t(f, s + 14, 12))
    for i, (outcome, reward, color) in enumerate(REWARDS):
        a = alpha_t(f, s + 20 + i * 12, 10)
        y = 240 + i * 90
        panel_rect(img, 90, y, 820, y + 72, PANEL, a, border_color=color)
        left_text(draw, outcome, 115, y + 18, font(30), WHITE, a)
        left_text(draw, reward,  730, y + 12, font(40, bold=True), color, a)

    # Q-update equation
    a_eq = alpha_t(f, s + 80, 16)
    panel_rect(img, 900, 200, W - 80, 340, PANEL, a_eq, border_color=ACCENT)
    centered_text(draw, "Q  +=  0.2 × ( reward − Q )", 230,
                  font(44, bold=True), ACCENT, a_eq, x_offset=200)
    centered_text(draw, "learning rate = 0.2    ε-greedy exploration",
                  310, font(26), GREY, a_eq, x_offset=200)

    # Strategy pills
    strategies = ["worked example", "concept explanation",
                  "small hint", "simpler practice", "challenge exercise"]
    for i, strat in enumerate(strategies):
        a = alpha_t(f, s + 100 + i * 10, 10)
        angle = (2 * math.pi * i / len(strategies)) - math.pi / 2
        cx    = 1300 + int(math.cos(angle) * 220)
        cy    = 680  + int(math.sin(angle) * 150)
        panel_rect(img, cx - 160, cy - 28, cx + 160, cy + 28,
                   PANEL, a, border_color=SECONDARY)
        bbox = draw.textbbox((0,0), strat, font=font(24))
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw//2, cy - 14), strat, font=font(24),
                  fill=(*SECONDARY, int(255*a)))

    caution_a = alpha_t(f, s + 160, 12)
    centered_text(draw,
        "⚠  Rising reward ≠ proof of learning — verified by pre/post assessment",
        H - 80, font(26), WARNING, caution_a)
    draw_progress_bar(draw, f - s, 288)


# ── Slide 6: Assessment & Progress ───────────────────────────────────────────

def draw_assess(img: Image.Image, f: int, s: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Assessment & Learner Progress", 50, font(60, bold=True),
                  ACCENT, alpha_t(f, s + 4, 14))

    draw.rectangle((W//2 - 2, 150, W//2 + 2, H - 80), fill=SECONDARY)

    # Left: assessment
    left_text(draw, "Pre / Post Assessment", 100, 150, font(40, bold=True), WHITE,
              alpha_t(f, s + 14, 12))
    assess_lines = [
        "Same 5 questions both times",
        "Score before Lesson 1  (pre)",
        "Score after last lesson (post)",
        "Post − Pre = measurable change",
        "Delayed check if time permits",
        "Anonymised learner IDs only",
    ]
    for i, line in enumerate(assess_lines):
        a = alpha_t(f, s + 22 + i * 12, 10)
        left_text(draw, f"·  {line}", 110, 240 + i * 100, font(32), WHITE, a)

    # Right: metrics
    left_text(draw, "Learner Progress Metrics", W//2 + 80, 150, font(40, bold=True),
              ACCENT, alpha_t(f, s + 20, 12))
    metrics = [
        ("Attempts",         "all code submissions"),
        ("Correctness",      "first-attempt pass rate"),
        ("Hint dependency",  "mean hints per correct"),
        ("Completion rate",  "lessons done / started"),
        ("Reward total",     "cumulative Q-signal"),
    ]
    for i, (metric, detail) in enumerate(metrics):
        am = alpha_t(f, s + 30 + i * 14, 12)
        y  = 240 + i * 115
        left_text(draw, metric, W//2 + 100, y,      font(34, bold=True), ACCENT, am)
        left_text(draw, detail, W//2 + 100, y + 46, font(26), GREY, am)

    syn_a = alpha_t(f, s + 150, 12)
    centered_text(draw,
        "★  SYNTHETIC DEMO DATA  ★  charts labelled as such in the app",
        H - 80, font(26), WARNING, syn_a)
    draw_progress_bar(draw, f - s, 288)


# ── Slide 7: LLM vs Fallback ──────────────────────────────────────────────────

LLM_LINES = [
    "OpenAI key in Colab Secrets",
    "Never printed or logged",
    "Generates explanations + hints",
    "Does NOT write grades",
    "Labelled 'LLM' in UI",
]
FB_LINES = [
    "No key — or key fails",
    "Rules-based templates",
    "Labelled 'Local fallback — NOT an LLM'",
    "Covers all 4 agent roles",
    "Demo works fully without a key",
]

def draw_fallback(img: Image.Image, f: int, s: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "LLM Mode  vs  Local Fallback", 50, font(64, bold=True),
                  ACCENT, alpha_t(f, s + 4, 14))

    for side, (title, color, lines) in enumerate([
        ("LLM Mode",       POSITIVE, LLM_LINES),
        ("Local Fallback", WARNING,  FB_LINES),
    ]):
        x0 = 100 if side == 0 else W//2 + 80
        a0 = alpha_t(f, s + 14, 14)
        left_text(draw, title, x0, 160, font(52, bold=True), color, a0)
        for i, line in enumerate(lines):
            a = alpha_t(f, s + 24 + i * 14, 12)
            left_text(draw, f"·  {line}", x0, 270 + i * 110, font(32), WHITE, a)

    # VS badge
    a_vs = alpha_t(f, s + 36, 14)
    glow_circle(img, W//2, H//2, 46, SECONDARY, a_vs * 0.7)
    centered_text(draw, "VS", H//2 - 30, font(56, bold=True), SECONDARY, a_vs)
    draw_progress_bar(draw, f - s, 192)


# ── Slide 8: Hardware Mock ────────────────────────────────────────────────────

JSON_TEXT = ('{ "device_id": "cyd-01",\n'
             '  "event":     "lesson_select",\n'
             '  "lesson_id": "L1",\n'
             '  "action":    "next",\n'
             '  "timestamp": "2026-12-01T10:00:00Z" }')

def draw_hw(img: Image.Image, f: int, s: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Hardware — Mock Mode", 50, font(70, bold=True), ACCENT,
                  alpha_t(f, s + 4, 14))

    # Device boxes
    devices = [
        ("Pi Zero 2 W", GREY,      250),
        ("Pico W",      GREY,      620),
        ("CYD Display", SECONDARY, 990),
    ]
    for name, color, cx in devices:
        a = alpha_t(f, s + 12, 14)
        panel_rect(img, cx - 110, 180, cx + 110, 420, PANEL, a, border_color=color)
        glow_circle(img, cx, 220, 20, ACCENT, a * 0.6)
        bbox = draw.textbbox((0,0), name, font=font(28, bold=True))
        tw = bbox[2]-bbox[0]
        draw.text((cx - tw//2, 440), name, font=font(28, bold=True),
                  fill=(*color, int(255*a)))

    # Arrow → Host
    a_arr = alpha_t(f, s + 40, 16)
    ax    = int(lerp(1130, 1300, ease_out((f - s - 40) / 16)))
    draw.rectangle((1120, H//2 - 4, ax, H//2 + 4), fill=(*ACCENT, int(220 * a_arr)))
    draw.polygon([(ax, H//2 - 14), (ax + 24, H//2), (ax, H//2 + 14)],
                 fill=(*ACCENT, int(220 * a_arr)))

    # JSON card
    a_json = alpha_t(f, s + 50, 16)
    panel_rect(img, 1310, 200, W - 60, 620, PANEL, a_json, border_color=POSITIVE)
    for i, line in enumerate(JSON_TEXT.splitlines()):
        left_text(draw, line, 1340, 230 + i * 68, font(28), POSITIVE, a_json)

    left_text(draw,
        "No LLM runs on device  ·  Host runs everything  ·  Mock events labelled",
        90, H - 80, font(26), WARNING, alpha_t(f, s + 90, 12))
    draw_progress_bar(draw, f - s, 192)


# ── Slide 9: Export Center ────────────────────────────────────────────────────

EXPORTS = [
    ("Contributions CSV",   POSITIVE),
    ("Evaluation CSV",      ACCENT),
    ("Progress CSV",        SECONDARY),
    ("Report Drafts (.md)", WARNING),
]

def draw_export(img: Image.Image, f: int, s: int) -> None:
    draw = ImageDraw.Draw(img)
    centered_text(draw, "Export Center", 50, font(80, bold=True), ACCENT,
                  alpha_t(f, s + 4, 14))

    xs = [220, 620, 1020, 1680]
    for i, ((name, color), x) in enumerate(zip(EXPORTS, xs)):
        a   = alpha_t(f, s + 12 + i * 16, 14)
        ox  = slide_x(f, s + 10 + i * 16, 16)
        px  = int(x + ox)
        panel_rect(img, px - 160, 200, px + 160, 530, PANEL, a, border_color=color)
        draw.rectangle((px - 160, 200, px + 160, 250), fill=(*color, int(200*a)))
        bbox = draw.textbbox((0,0), name, font=font(26, bold=True))
        tw = bbox[2] - bbox[0]
        draw.text((px - tw//2, 560), name, font=font(26, bold=True),
                  fill=(*color, int(255*a)))

    rule_a = alpha_t(f, s + 80, 14)
    centered_text(draw,
        "Generated from ACTUAL contribution records only.",
        H - 130, font(34), WHITE, rule_a)
    centered_text(draw,
        "Missing evidence is flagged — nothing is invented.",
        H - 80, font(30), WARNING, rule_a)
    draw_progress_bar(draw, f - s, 192)


# ── Slide 10: Closing ─────────────────────────────────────────────────────────

def draw_closing(img: Image.Image, f: int, s: int) -> None:
    draw = ImageDraw.Draw(img)

    # Star field
    for i in range(16):
        angle = (2 * math.pi * i / 16)
        r     = 340 + 40 * (i % 3)
        cx    = W // 2 + int(math.cos(angle) * r)
        cy    = H // 2 + int(math.sin(angle) * r * 0.55)
        a_st  = alpha_t(f, s + 10, 20) * (0.6 + 0.4 * math.sin(math.radians((f-s)*4 + i*22)))
        glow_circle(img, cx, cy, 5, ACCENT if i % 3 else SECONDARY, a_st)

    # Central aura
    glow_circle(img, W//2, H//2, 90, ACCENT, alpha_t(f, s + 36, 20) * 0.35)

    a0 = alpha_t(f, s + 6, 18)
    centered_text(draw, "Learning through interaction.", H//2 - 160,
                  font(60), ACCENT, a0)
    a1 = alpha_t(f, s + 24, 18)
    centered_text(draw, "Improving through feedback.", H//2 - 70,
                  font(60), ACCENT, a1)
    a2 = alpha_t(f, s + 42, 20)
    centered_text(draw, "SHAPE Agent 16", H//2 + 50, font(90, bold=True), WHITE, a2)
    a3 = alpha_t(f, s + 60, 16)
    centered_text(draw,
        "ITAI2376  ·  Houston Community College  ·  Group 14562",
        H//2 + 170, font(32), GREY, a3)
    a4 = alpha_t(f, s + 76, 16)
    centered_text(draw,
        "Michael Rivas  ·  Cherluk  ·  Olu  ·  Taki",
        H//2 + 230, font(32), SECONDARY, a4)
    draw_progress_bar(draw, f - s, 192)


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE TABLE
# ─────────────────────────────────────────────────────────────────────────────

SLIDES: list[dict] = [
    {"start":    0, "end":   72, "fn": draw_title},
    {"start":   72, "end":  240, "fn": draw_what},
    {"start":  240, "end":  480, "fn": draw_agents},
    {"start":  480, "end":  768, "fn": draw_cycle},
    {"start":  768, "end": 1056, "fn": draw_tools},
    {"start": 1056, "end": 1344, "fn": draw_rl},
    {"start": 1344, "end": 1632, "fn": draw_assess},
    {"start": 1632, "end": 1824, "fn": draw_fallback},
    {"start": 1824, "end": 2016, "fn": draw_hw},
    {"start": 2016, "end": 2208, "fn": draw_export},
    {"start": 2208, "end": 2400, "fn": draw_closing},
]

NARRATION: list[str] = [
    "SHAPE Agent 16 — Student-centered Handheld Architecture for Programming Education",
    "SHAPE teaches Python and AI concepts through guided interaction and adaptive feedback.",
    "Four specialised agents — Instructor, Debugger, Evaluator, Learning Strategist — served by one LLM.",
    "Every interaction runs the 8-step reasoning cycle. The Agent Workspace shows every step in real time.",
    "Two tools: a Python exercise runner and a lesson retrieval tool backed by SQLite.",
    "The Learning Strategist uses a contextual bandit policy with a documented reward function and Q-update.",
    "Every attempt is recorded. Pre-test before Lesson 1, post-test after. Learners identified by anonymised IDs only.",
    "SHAPE works without an API key. Local fallback mode is always labelled as not an LLM.",
    "Hardware runs in mock mode by default. JSON events go through the same orchestrator — no device needed.",
    "The Export Center generates CSVs and report drafts from actual contribution records. Missing evidence is flagged.",
    "Learning through interaction. Improving through feedback. SHAPE Agent 16.",
]


def active_slide(frame: int) -> dict:
    for slide in reversed(SLIDES):
        if frame >= slide["start"]:
            return slide
    return SLIDES[0]


# ─────────────────────────────────────────────────────────────────────────────
# SRT WRITER
# ─────────────────────────────────────────────────────────────────────────────

def write_srt(out_dir: Path, total: int) -> None:
    def tc(frame: int) -> str:
        s   = frame / FPS
        h   = int(s // 3600)
        m   = int((s % 3600) // 60)
        sec = int(s % 60)
        ms  = int((s % 1) * 1000)
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

    lines = []
    for i, (slide, narr) in enumerate(zip(SLIDES, NARRATION)):
        lines += [
            str(i + 1),
            f"{tc(slide['start'] + 1)} --> {tc(min(slide['end'], total))}",
            narr,
            "",
        ]
    srt_path = out_dir / "SHAPE_Agent16_Demo.srt"
    srt_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  SRT written: {srt_path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="SHAPE Agent 16 — video renderer")
    parser.add_argument("--preview", action="store_true",
                        help="Render first 10 seconds only (240 frames)")
    parser.add_argument("--out", default="SHAPE_Agent16_Demo.mp4",
                        help="Output MP4 filename (default: SHAPE_Agent16_Demo.mp4)")
    args = parser.parse_args()

    total_frames = 240 if args.preview else TOTAL
    out_path     = Path(args.out)

    print(f"\n{'='*58}")
    print(f"  SHAPE Agent 16 — Python Video Renderer")
    print(f"  Frames : {total_frames}  ({total_frames/FPS:.0f} s at {FPS} fps)")
    print(f"  Output : {out_path}")
    print(f"{'='*58}\n")

    # Pre-load fonts so the first frame isn't slow
    for sz in [24, 26, 28, 30, 32, 34, 36, 40, 42, 44, 52, 56, 60, 64, 66,
               70, 72, 80, 90, 140]:
        font(sz, bold=False)
        font(sz, bold=True)

    # Build SRT
    render_dir = Path(__file__).parent / "render"
    render_dir.mkdir(parents=True, exist_ok=True)
    write_srt(render_dir, total_frames)

    # Open ffmpeg pipe
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{W}x{H}",
        "-pix_fmt", "rgba",
        "-r", str(FPS),
        "-i", "pipe:0",
        "-vcodec", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        str(out_path),
    ]

    try:
        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("ERROR: ffmpeg not found. Install with:  sudo apt install ffmpeg")
        sys.exit(1)

    t0 = time.perf_counter()

    for frame in range(1, total_frames + 1):
        slide = active_slide(frame)
        img   = new_frame()
        slide["fn"](img, frame, slide["start"])
        proc.stdin.write(img.tobytes())

        if frame % FPS == 0:
            elapsed = time.perf_counter() - t0
            fps_actual = frame / elapsed
            pct    = 100.0 * frame / total_frames
            remain = (elapsed / frame) * (total_frames - frame)
            print(f"  {frame:4d}/{total_frames}  {pct:5.1f}%  "
                  f"{fps_actual:5.0f} fps  ETA {remain:4.0f}s")

    proc.stdin.close()
    proc.wait()

    total_time = time.perf_counter() - t0
    fps_avg    = total_frames / total_time

    print(f"\n✅  Done in {total_time:.1f}s  ({fps_avg:.0f} fps avg)")
    print(f"   Video : {out_path.resolve()}")
    print(f"   SRT   : {(render_dir / 'SHAPE_Agent16_Demo.srt').resolve()}\n")

    if args.preview:
        print("  Run without --preview to render the full 100-second video.\n")


if __name__ == "__main__":
    main()
