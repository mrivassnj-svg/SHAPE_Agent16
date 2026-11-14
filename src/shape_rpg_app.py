"""
shape_rpg_app.py
----------------
Streamlit RPG UI for SHAPE Agent 16 — Interactive Learning Companion.

Place your Blender-rendered sprite PNGs in:
  assets/sprites/<name>.png

Expected sprite filenames (from ZONE_ENEMIES sprite keys + player):
  player.png   agent16.png (fallback)
  slime.png    crab.png    imp.png    wyrm.png
  wraith.png   lich.png    ogre.png   specter.png
  knight.png   hydra.png   drake.png  boss.png

All sprites are optional — emoji fallbacks are used if file not found.

Launch:
  streamlit run src/shape_rpg_app.py

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

from __future__ import annotations

import base64
import json
import sys
import os
from pathlib import Path

import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ── Path setup ────────────────────────────────────────────────────────────────
_SRC = Path(__file__).parent
sys.path.insert(0, str(_SRC))

from shape_rpg_db import (
    init_rpg_tables, upsert_player, get_player,
    save_player, apply_xp, xp_for_next_level,
    get_player_stats_summary,
)
from shape_rpg_engine import (
    new_battle, answer_question, flee_battle, available_zones, BattleState,
)
from shape_rpg_questions import ZONES_IN_ORDER, ZONE_ENEMIES

# ── Init DB ───────────────────────────────────────────────────────────────────
init_rpg_tables()

# ── Assets ────────────────────────────────────────────────────────────────────
ASSETS = Path(__file__).parent.parent / "assets" / "sprites"

SPRITE_EMOJI: dict[str, str] = {
    "player":  "🧑‍💻",
    "slime":   "🟢",
    "crab":    "🦀",
    "imp":     "😈",
    "wyrm":    "🐛",
    "wraith":  "👻",
    "lich":    "💀",
    "ogre":    "👹",
    "specter": "🌫️",
    "knight":  "⚔️",
    "hydra":   "🐉",
    "drake":   "🔥",
    "boss":    "☠️",
}

ZONE_EMOJI: dict[str, str] = {
    "Syntax Swamp":      "🌿",
    "Loop Lagoon":       "🌊",
    "Function Fortress": "🏰",
    "List Labyrinth":    "🗺️",
    "Dict Dungeon":      "🏚️",
    "Error Cavern":      "🕳️",
}

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SHAPE Agent 16 RPG",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS — base styles + ALL battle animations
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
/* ── Base ──────────────────────────────────────────────── */
body { background-color: #1a1a2e; color: #eee; }
.stButton>button {
    background: #16213e; color: #eee; border: 1px solid #0f3460;
    border-radius: 6px; padding: 8px 20px; font-size: 15px;
    transition: background 0.2s, border-color 0.2s;
}
.stButton>button:hover { background: #0f3460; border-color: #e94560; }
.battle-box {
    background: #16213e; border: 1px solid #0f3460;
    border-radius: 12px; padding: 20px; margin-bottom: 12px;
}
.question-box {
    background: #0f3460; border-radius: 10px;
    padding: 18px; font-size: 16px; margin: 10px 0;
    border-left: 4px solid #e94560;
}
.result-correct { color: #2ecc71; font-size: 18px; font-weight: bold; }
.result-wrong   { color: #e74c3c; font-size: 18px; font-weight: bold; }
.zone-card {
    background: #16213e; border: 1px solid #0f3460; border-radius: 8px;
    padding: 12px; text-align: center; margin: 4px;
}

/* ── Sprite containers ─────────────────────────────────── */
.sprite-wrap {
    display: flex; flex-direction: column;
    align-items: center; justify-content: flex-end;
    min-height: 200px; position: relative;
}
.sprite-wrap img, .sprite-wrap .emoji-sprite {
    display: block; margin: 0 auto;
    image-rendering: pixelated;
}
.emoji-sprite {
    font-size: 90px; line-height: 1; text-align: center;
}

/* ── Idle float ────────────────────────────────────────── */
@keyframes idle-float {
    0%   { transform: translateY(0px); }
    50%  { transform: translateY(-8px); }
    100% { transform: translateY(0px); }
}
.anim-idle {
    animation: idle-float 2.6s ease-in-out infinite;
}

/* ── Player attacks enemy — lunges right then snaps back ── */
@keyframes player-attack {
    0%   { transform: translateX(0px)   translateY(0px) rotate(0deg); }
    20%  { transform: translateX(12px)  translateY(-6px) rotate(-8deg); }
    45%  { transform: translateX(80px)  translateY(-18px) rotate(-15deg); }
    65%  { transform: translateX(80px)  translateY(-18px) rotate(-15deg); }
    80%  { transform: translateX(-8px)  translateY(4px)  rotate(5deg); }
    100% { transform: translateX(0px)   translateY(0px) rotate(0deg); }
}
.anim-player-attack {
    animation: player-attack 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
}

/* ── Enemy takes hit — recoils right + red flash ───────── */
@keyframes enemy-hit {
    0%   { transform: translateX(0px);  filter: brightness(1); }
    15%  { transform: translateX(22px); filter: brightness(3) saturate(0) sepia(1) hue-rotate(-30deg); }
    30%  { transform: translateX(-18px); filter: brightness(2.5) saturate(0) sepia(1) hue-rotate(-30deg); }
    50%  { transform: translateX(12px); filter: brightness(1.8); }
    70%  { transform: translateX(-8px); filter: brightness(1.3); }
    100% { transform: translateX(0px);  filter: brightness(1); }
}
.anim-enemy-hit {
    animation: enemy-hit 0.65s ease-out forwards;
}

/* ── Enemy attacks player — lunges left then snaps back ── */
@keyframes enemy-attack {
    0%   { transform: translateX(0px)   translateY(0px) rotate(0deg); }
    20%  { transform: translateX(-12px) translateY(-6px) rotate(8deg); }
    45%  { transform: translateX(-80px) translateY(-18px) rotate(15deg); }
    65%  { transform: translateX(-80px) translateY(-18px) rotate(15deg); }
    80%  { transform: translateX(8px)   translateY(4px)  rotate(-5deg); }
    100% { transform: translateX(0px)   translateY(0px) rotate(0deg); }
}
.anim-enemy-attack {
    animation: enemy-attack 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
}

/* ── Player takes damage — shakes + red tint ──────────── */
@keyframes player-hurt {
    0%   { transform: translateX(0px)  rotate(0deg);  filter: brightness(1); }
    10%  { transform: translateX(-16px) rotate(-6deg); filter: brightness(3) saturate(0) sepia(1) hue-rotate(-30deg); }
    25%  { transform: translateX(16px)  rotate(6deg);  filter: brightness(2.5) sepia(1) hue-rotate(-30deg); }
    40%  { transform: translateX(-12px) rotate(-4deg); filter: brightness(2); }
    55%  { transform: translateX(10px)  rotate(3deg);  filter: brightness(1.5); }
    70%  { transform: translateX(-6px)  rotate(-2deg); filter: brightness(1.2); }
    100% { transform: translateX(0px)   rotate(0deg);  filter: brightness(1); }
}
.anim-player-hurt {
    animation: player-hurt 0.75s ease-out forwards;
}

/* ── Enemy death — shrinks, spins, fades out ──────────── */
@keyframes enemy-death {
    0%   { transform: scale(1) rotate(0deg);   opacity: 1; filter: brightness(1); }
    20%  { transform: scale(1.2) rotate(-15deg); opacity: 1; filter: brightness(4) saturate(2); }
    50%  { transform: scale(0.7) rotate(30deg);  opacity: 0.7; filter: brightness(2); }
    80%  { transform: scale(0.3) rotate(70deg);  opacity: 0.3; filter: brightness(1); }
    100% { transform: scale(0) rotate(90deg);    opacity: 0; }
}
.anim-enemy-death {
    animation: enemy-death 1.1s ease-in forwards;
}

/* ── Player defeat — slumps down and fades ────────────── */
@keyframes player-defeat {
    0%   { transform: translateY(0px)  rotate(0deg); opacity: 1; }
    30%  { transform: translateY(-12px) rotate(-15deg); opacity: 1; filter: brightness(2) sepia(1) hue-rotate(-30deg); }
    60%  { transform: translateY(20px)  rotate(80deg); opacity: 0.7; }
    100% { transform: translateY(40px)  rotate(90deg); opacity: 0.2; }
}
.anim-player-defeat {
    animation: player-defeat 1.0s ease-in forwards;
}

/* ── Level-up glow pulse ──────────────────────────────── */
@keyframes levelup-pulse {
    0%   { filter: brightness(1) drop-shadow(0 0 0px #fff); }
    25%  { filter: brightness(2.5) drop-shadow(0 0 24px #ffe066); }
    50%  { filter: brightness(1.5) drop-shadow(0 0 12px #9b59b6); }
    75%  { filter: brightness(2.2) drop-shadow(0 0 20px #00eeff); }
    100% { filter: brightness(1) drop-shadow(0 0 0px #fff); }
}
.anim-levelup {
    animation: levelup-pulse 1.0s ease-in-out 3;
}

/* ── Slash VFX overlay ────────────────────────────────── */
@keyframes slash-appear {
    0%   { opacity: 0; transform: scale(0.4) rotate(-40deg); }
    30%  { opacity: 1; transform: scale(1.3) rotate(5deg); }
    60%  { opacity: 0.8; transform: scale(1.1) rotate(0deg); }
    100% { opacity: 0; transform: scale(1.4) rotate(10deg); }
}
.slash-vfx {
    position: absolute; top: 20%; left: 50%;
    transform: translateX(-50%);
    font-size: 72px; line-height: 1;
    pointer-events: none;
    animation: slash-appear 0.6s ease-out forwards;
    z-index: 10;
}

/* ── Hit number float-up ──────────────────────────────── */
@keyframes dmg-float {
    0%   { opacity: 1; transform: translateY(0px) scale(1); }
    40%  { opacity: 1; transform: translateY(-28px) scale(1.3); }
    100% { opacity: 0; transform: translateY(-55px) scale(0.9); }
}
.dmg-number {
    position: absolute; top: 10%; left: 50%;
    transform: translateX(-50%);
    font-size: 28px; font-weight: 900;
    pointer-events: none;
    animation: dmg-float 1.0s ease-out forwards;
    z-index: 20; text-shadow: 2px 2px 6px #000;
}
.dmg-number.hit  { color: #ff4444; }
.dmg-number.deal { color: #ffe066; }

/* ── Idle sparkles ────────────────────────────────────── */
@keyframes sparkle {
    0%   { opacity: 0; transform: scale(0) translateY(0); }
    40%  { opacity: 1; transform: scale(1) translateY(-10px); }
    100% { opacity: 0; transform: scale(0.5) translateY(-22px); }
}
.sparkle {
    position: absolute; font-size: 14px; pointer-events: none;
    animation: sparkle 1.4s ease-out infinite;
}
.sparkle:nth-child(1) { left: 10%; animation-delay: 0s; }
.sparkle:nth-child(2) { left: 80%; animation-delay: 0.5s; }
.sparkle:nth-child(3) { left: 45%; animation-delay: 1.0s; }

/* ── Battle arena ground line ─────────────────────────── */
.arena-ground {
    width: 100%; height: 4px;
    background: linear-gradient(90deg, transparent, #0f3460 20%, #e94560 50%, #0f3460 80%, transparent);
    border-radius: 2px; margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────

# How long (ms) to show the hit/attack animation before resetting to idle.
# The longest animation is enemy-death at 1.1s — 1400ms gives it breathing room.
_ANIM_HOLD_MS  = 1400
# How often (ms) the idle battle scene cycles to keep the float animation live.
_IDLE_CYCLE_MS = 2000

def _init_state() -> None:
    defaults = {
        "screen":        "title",   # title | world | zone_select | battle
        "player_id":     None,
        "battle":        None,      # BattleState
        "last_result":   None,      # result dict from answer_question
        "selected_zone": None,
        "message_log":   [],
        # animation state — set for one render cycle then cleared
        "anim":          "idle",    # idle | attack | hurt | death | defeat | levelup
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()
S = st.session_state


# ══════════════════════════════════════════════════════════════════════════════
# SPRITE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _img_b64(name: str) -> str | None:
    """Return base64 data-URI for a sprite PNG, or None if missing."""
    path = ASSETS / f"{name}.png"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def _animated_sprite(
    name: str,
    *,
    width: int = 150,
    anim_class: str = "anim-idle",
    extra_css: str = "",
    show_slash: bool = False,
    dmg_number: int | None = None,
    dmg_type: str = "hit",        # "hit" (red) or "deal" (yellow)
    sparkles: bool = False,
    flip: bool = False,
) -> str:
    """
    Return raw HTML for an animated sprite container.
    Caller passes to st.markdown(..., unsafe_allow_html=True).
    """
    b64 = _img_b64(name)
    emoji = SPRITE_EMOJI.get(name, "❓")
    transform_base = "scaleX(-1)" if flip else "scaleX(1)"

    if b64:
        inner = (
            f"<img src='{b64}' width='{width}' "
            f"style='display:block;margin:0 auto;transform:{transform_base}' "
            f"class='{anim_class}' />"
        )
    else:
        inner = (
            f"<div class='emoji-sprite {anim_class}' "
            f"style='font-size:{width//2}px;transform:{transform_base}'>"
            f"{emoji}</div>"
        )

    slash_html  = "<div class='slash-vfx'>⚡</div>" if show_slash else ""
    dmg_html    = ""
    if dmg_number is not None and dmg_number > 0:
        dmg_html = f"<div class='dmg-number {dmg_type}'>-{dmg_number}</div>"
    spark_html  = ""
    if sparkles:
        spark_html = "<span class='sparkle'>✦</span><span class='sparkle'>✦</span><span class='sparkle'>✦</span>"

    return (
        f"<div class='sprite-wrap' style='{extra_css}'>"
        f"{spark_html}{slash_html}{dmg_html}{inner}"
        f"<div class='arena-ground'></div>"
        f"</div>"
    )


def _hp_bar(current: int, maximum: int, color: str = "#e74c3c") -> None:
    pct = max(0, min(100, int(current / maximum * 100)))
    bar_color = "#2ecc71" if pct > 50 else "#f39c12" if pct > 25 else color
    st.markdown(
        f"""
        <div style="background:#333;border-radius:8px;height:18px;width:100%;margin-bottom:4px">
          <div style="background:{bar_color};width:{pct}%;height:100%;
                      border-radius:8px;transition:width 0.5s ease"></div>
        </div>
        <div style="font-size:12px;color:#aaa;margin-bottom:8px">
          {current} / {maximum} HP
        </div>
        """,
        unsafe_allow_html=True,
    )


def _xp_bar(xp: int, level: int) -> None:
    needed = xp_for_next_level(level)
    pct    = min(100, int(xp / needed * 100)) if needed > 0 else 100
    st.markdown(
        f"""
        <div style="background:#333;border-radius:8px;height:12px;width:100%;margin-bottom:2px">
          <div style="background:#9b59b6;width:{pct}%;height:100%;border-radius:8px;transition:width 0.5s ease"></div>
        </div>
        <div style="font-size:11px;color:#aaa;margin-bottom:8px">
          XP {xp} / {needed}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _sprite(name: str, width: int = 140) -> None:
    """Simple static sprite for non-battle screens."""
    b64 = _img_b64(name)
    if b64:
        st.image(str(ASSETS / f"{name}.png"), width=width)
    else:
        st.markdown(
            f"<div style='font-size:{width//2}px;text-align:center;line-height:1'>"
            f"{SPRITE_EMOJI.get(name, '❓')}</div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN: TITLE
# ══════════════════════════════════════════════════════════════════════════════

def screen_title() -> None:
    st.markdown("""
    <div style='text-align:center;padding:40px 0 10px'>
      <div style='font-size:64px'>⚔️</div>
      <h1 style='font-size:42px;color:#e94560;margin:0'>SHAPE Agent 16</h1>
      <h2 style='font-size:22px;color:#aaa;font-weight:normal'>Python RPG — The Learning Quest</h2>
      <p style='color:#777;font-size:13px'>ITAI2376_14562 | Michael Rivas · Cherluk · Olu · Taki</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("#### Enter your name to begin")
        name = st.text_input("Player name", placeholder="Agent 16", key="name_input",
                             label_visibility="collapsed")
        if st.button("▶  START QUEST", use_container_width=True):
            if name.strip():
                pid = name.strip().lower().replace(" ", "_")
                upsert_player(pid, name.strip())
                S["player_id"] = pid
                S["screen"]    = "world"
                S["anim"]      = "idle"
                st.rerun()
            else:
                st.warning("Enter a name to begin.")

        st.markdown("---")
        st.markdown("""
        <div style='font-size:13px;color:#777;text-align:center'>
        ⚔️ Answer Python questions correctly to deal damage<br>
        ❤️ Wrong answers — the enemy strikes YOU back<br>
        🏆 Defeat enemies to earn XP and level up<br>
        🗺️ Explore 6 zones — defeat the final BOSS: NullByte
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — always visible during play
# ══════════════════════════════════════════════════════════════════════════════

def sidebar_player_card() -> None:
    if not S["player_id"]:
        return
    player = get_player(S["player_id"])
    if not player:
        return

    with st.sidebar:
        st.markdown("## 🧑‍💻 Agent 16")
        _sprite("player", width=120)
        st.markdown(f"**{player['display_name']}**  ·  Level {player['level']}")
        st.markdown("**❤️ HP**")
        _hp_bar(player["hp"], player["max_hp"])
        st.markdown("**✨ XP**")
        _xp_bar(player["xp"], player["level"])
        st.markdown(f"🪙 **Gold:** {player['gold']}")

        stats = get_player_stats_summary(S["player_id"])
        st.markdown(f"⚔️ Wins: **{stats['wins']}**  💀 Losses: **{stats['losses']}**")

        cleared = json.loads(player["zones_cleared"])
        st.markdown("**🗺️ Zones Cleared:**")
        for z in ZONES_IN_ORDER:
            mark = "✅" if z in cleared else ("📍" if z == player["current_zone"] else "🔒")
            st.markdown(f"{mark} {ZONE_EMOJI.get(z,'')} {z}")

        st.markdown("---")
        if st.button("🏠 World Map"):
            S["screen"]      = "world"
            S["battle"]      = None
            S["last_result"] = None
            S["anim"]        = "idle"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN: WORLD MAP
# ══════════════════════════════════════════════════════════════════════════════

def screen_world() -> None:
    player  = get_player(S["player_id"])
    cleared = json.loads(player["zones_cleared"])

    st.markdown("## 🗺️ World Map — Choose Your Zone")
    st.markdown(f"Current zone: **{player['current_zone']}**")
    st.markdown("---")

    cols = st.columns(3)
    for i, zone in enumerate(ZONES_IN_ORDER):
        unlocked   = zone in available_zones(S["player_id"])
        is_cleared = zone in cleared
        emoji      = ZONE_EMOJI.get(zone, "🌐")

        with cols[i % 3]:
            st.markdown(
                f"<div class='zone-card'>"
                f"<div style='font-size:36px'>{emoji}</div>"
                f"<b>{zone}</b><br>"
                f"<span style='font-size:12px;color:#aaa'>"
                f"{'✅ Cleared' if is_cleared else ('🔓 Available' if unlocked else '🔒 Locked')}"
                f"</span></div>",
                unsafe_allow_html=True,
            )
            if unlocked:
                enemies = ZONE_ENEMIES.get(zone, [])
                enemy_names = " · ".join(e["name"] for e in enemies)
                st.caption(f"Enemies: {enemy_names}")
                if st.button(f"Enter {zone}", key=f"zone_{zone}"):
                    S["selected_zone"] = zone
                    S["screen"]        = "zone_select"
                    st.rerun()
            else:
                st.caption("Clear previous zones to unlock")


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN: ZONE SELECT
# ══════════════════════════════════════════════════════════════════════════════

def screen_zone_select() -> None:
    zone    = S["selected_zone"]
    enemies = ZONE_ENEMIES.get(zone, [])
    emoji   = ZONE_EMOJI.get(zone, "🌐")

    st.markdown(f"## {emoji} {zone}")
    st.markdown("Choose your opponent:")
    st.markdown("---")

    cols = st.columns(len(enemies))
    for i, enemy in enumerate(enemies):
        with cols[i]:
            _sprite(enemy["sprite"], width=160)
            st.markdown(f"**{enemy['name']}**")
            st.markdown(f"❤️ HP: {enemy['hp']}  ⚔️ ATK: {enemy['attack']}")
            st.markdown(f"🏆 XP Reward: {enemy['xp_reward']}")
            if st.button(f"⚔️ Fight {enemy['name']}", key=f"fight_{i}"):
                battle = new_battle(S["player_id"], zone)
                battle.enemy        = dict(enemy)
                battle.enemy_hp     = enemy["hp"]
                battle.enemy_max_hp = enemy["hp"]
                S["battle"]      = battle
                S["last_result"] = None
                S["screen"]      = "battle"
                S["anim"]        = "idle"
                st.rerun()

    if st.button("← Back to World Map"):
        S["screen"] = "world"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN: BATTLE  (with animations)
# ══════════════════════════════════════════════════════════════════════════════

def _battle_autorefresh(anim: str) -> None:
    """
    Non-blocking auto-refresh using streamlit-autorefresh.

    - After an action animation fires: refresh every _ANIM_HOLD_MS once,
      which lets the CSS animation play out, then we reset anim→idle on
      the next rerun.
    - During idle: refresh every _IDLE_CYCLE_MS so the floating animation
      keeps cycling and the battle stays live.

    Uses st_autorefresh which fires an async rerun without blocking the
    server thread — clicks remain responsive during the interval.
    """
    if anim in ("win", "loss", "fled"):
        return   # battle over — no more refreshes

    interval = _ANIM_HOLD_MS if anim != "idle" else _IDLE_CYCLE_MS
    # limit=1 on action animations so they don't loop; limit=0 (unlimited) on idle
    limit = 1 if anim != "idle" else 0
    count = st_autorefresh(interval=interval, limit=limit if limit > 0 else None,
                            key=f"ar_{anim}")

    # When the action animation refresh fires (count becomes 1), reset to idle
    if anim != "idle" and count and count >= 1:
        S["anim"] = "idle"


def screen_battle() -> None:
    battle: BattleState = S["battle"]
    player = get_player(S["player_id"])
    anim   = S.get("anim", "idle")
    r      = S.get("last_result")

    # ── Derive per-sprite animation classes from last result ──────────────────
    player_anim  = "anim-idle"
    enemy_anim   = "anim-idle"
    show_slash   = False
    enemy_dmg    = None
    player_dmg   = None
    player_spark = False
    enemy_spark  = False

    if r:
        if battle.outcome == "win":
            # Final blow — enemy dies, player stays
            player_anim  = "anim-player-attack"
            enemy_anim   = "anim-enemy-death"
            show_slash   = True
            enemy_dmg    = r["damage_dealt"]
            player_spark = True          # celebrate
        elif battle.outcome == "loss":
            enemy_anim  = "anim-enemy-attack"
            player_anim = "anim-player-defeat"
            player_dmg  = r["damage_taken"]
        elif r["correct"]:
            player_anim = "anim-player-attack"
            enemy_anim  = "anim-enemy-hit"
            show_slash  = True
            enemy_dmg   = r["damage_dealt"]
            if r.get("level_up"):
                player_anim  = "anim-levelup"
                player_spark = True
        else:
            # Wrong answer — enemy counter-attacks player
            enemy_anim  = "anim-enemy-attack"
            player_anim = "anim-player-hurt"
            player_dmg  = r["damage_taken"]

    # ── Layout: player left | arena centre | enemy right ─────────────────────
    left, mid, right = st.columns([2, 3, 2])

    # ── Player column ─────────────────────────────────────────────────────────
    with left:
        st.markdown(
            f"<div style='text-align:center;font-size:14px;color:#aaa;margin-bottom:4px'>"
            f"🧑‍💻 <b>{player['display_name']}</b>  Lv.{player['level']}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            _animated_sprite(
                "player",
                width=150,
                anim_class=player_anim,
                dmg_number=player_dmg,
                dmg_type="hit",
                sparkles=player_spark,
            ),
            unsafe_allow_html=True,
        )
        _hp_bar(player["hp"], player["max_hp"])

    # ── Centre arena ──────────────────────────────────────────────────────────
    with mid:
        # Zone banner
        zone_em = ZONE_EMOJI.get(battle.zone, "⚔️")
        st.markdown(
            f"<div style='text-align:center;font-size:13px;color:#777;margin-bottom:4px'>"
            f"{zone_em} {battle.zone}  ·  Turn {battle.turn + 1}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='text-align:center;font-size:30px;color:#e94560;"
            "font-weight:900;letter-spacing:4px;margin-bottom:8px'>⚔️ VS ⚔️</div>",
            unsafe_allow_html=True,
        )

        # ── Last result feedback ───────────────────────────────────────────
        if r:
            css   = "result-correct" if r["correct"] else "result-wrong"
            icon  = "✅" if r["correct"] else "❌"
            st.markdown(
                f"<div class='{css}' style='text-align:center;margin-bottom:6px'>"
                f"{icon} {r['message']}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='font-size:13px;color:#aaa;text-align:center;"
                f"background:#0f3460;padding:8px;border-radius:6px;margin-bottom:8px'>"
                f"💡 {r['explanation']}</div>",
                unsafe_allow_html=True,
            )
            if r.get("level_up"):
                st.markdown(
                    f"<div style='text-align:center;font-size:20px;color:#ffe066;"
                    f"font-weight:900;animation:levelup-pulse 1s ease-in-out 3'>"
                    f"✨ LEVEL UP! → Level {r['new_level']} ✨</div>",
                    unsafe_allow_html=True,
                )

        # ── Battle over screens ────────────────────────────────────────────
        if battle.outcome == "win":
            st.success(f"🏆 Victory! {battle.enemy['name']} defeated! +{r['xp_this_turn'] if r else 0} XP")
            if st.button("🗺️ Return to World Map", key="btn_win"):
                S["screen"] = "world"; S["battle"] = None
                S["last_result"] = None; S["anim"] = "idle"
                st.rerun()
            return
        elif battle.outcome == "loss":
            st.error("💀 You were defeated... You recover with partial HP.")
            if st.button("🗺️ Return to World Map", key="btn_loss"):
                S["screen"] = "world"; S["battle"] = None
                S["last_result"] = None; S["anim"] = "idle"
                st.rerun()
            return
        elif battle.outcome == "fled":
            st.warning("🏃 You fled the battle!")
            if st.button("🗺️ Return to World Map", key="btn_fled"):
                S["screen"] = "world"; S["battle"] = None
                S["last_result"] = None; S["anim"] = "idle"
                st.rerun()
            return

        # ── Question ──────────────────────────────────────────────────────
        q = battle.current_q
        if q:
            st.markdown(
                f"<div class='question-box'>"
                f"{q['prompt'].replace(chr(10), '<br>')}"
                f"</div>",
                unsafe_allow_html=True,
            )
            labels = ["A", "B", "C", "D"]
            for idx, choice in enumerate(q["choices"]):
                btn_label = f"{labels[idx]}.  {choice}"
                if st.button(btn_label, key=f"choice_{idx}_{battle.turn}",
                             use_container_width=True):
                    result = answer_question(battle, idx)
                    S["last_result"] = result
                    # Set animation state based on outcome
                    if result["correct"]:
                        S["anim"] = "levelup" if result.get("level_up") else "attack"
                    else:
                        S["anim"] = "hurt"
                    st.rerun()

            st.markdown("---")
            if st.button("🏃 Flee (take half damage)", use_container_width=False,
                         key=f"flee_{battle.turn}"):
                flee_battle(battle)
                S["last_result"] = None
                S["anim"] = "idle"
                st.rerun()

    # ── Enemy column ──────────────────────────────────────────────────────────
    with right:
        st.markdown(
            f"<div style='text-align:center;font-size:14px;color:#e94560;margin-bottom:4px'>"
            f"<b>{battle.enemy['name']}</b>  ⚔️ ATK {battle.enemy['attack']}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            _animated_sprite(
                battle.enemy["sprite"],
                width=150,
                anim_class=enemy_anim,
                flip=True,              # face the player
                show_slash=show_slash,
                dmg_number=enemy_dmg,
                dmg_type="deal",
                sparkles=enemy_spark,
            ),
            unsafe_allow_html=True,
        )
        _hp_bar(battle.enemy_hp, battle.enemy_max_hp, color="#e74c3c")

    # ── Auto-refresh loop — keeps animations cycling ──────────────────────────
    # Called after all UI is rendered so the page draws first, then sleeps.
    # Skipped when battle is already over.
    if battle.outcome == "ongoing":
        _battle_autorefresh(anim)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════

sidebar_player_card()

screen = S["screen"]

if screen == "title":
    screen_title()
elif screen == "world":
    screen_world()
elif screen == "zone_select":
    screen_zone_select()
elif screen == "battle":
    screen_battle()
else:
    screen_title()
