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

import json
import sys
import os
from pathlib import Path

import streamlit as st

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
    "Syntax Swamp":     "🌿",
    "Loop Lagoon":      "🌊",
    "Function Fortress":"🏰",
    "List Labyrinth":   "🗺️",
    "Dict Dungeon":     "🏚️",
    "Error Cavern":     "🕳️",
}


def _sprite(name: str, width: int = 140) -> None:
    """Display sprite image if file exists, else show large emoji."""
    path = ASSETS / f"{name}.png"
    if path.exists():
        st.image(str(path), width=width)
    else:
        st.markdown(
            f"<div style='font-size:{width//2}px;text-align:center;line-height:1'>"
            f"{SPRITE_EMOJI.get(name, '❓')}</div>",
            unsafe_allow_html=True,
        )


def _hp_bar(current: int, maximum: int, color: str = "#e74c3c") -> None:
    pct = max(0, min(100, int(current / maximum * 100)))
    bar_color = "#2ecc71" if pct > 50 else "#f39c12" if pct > 25 else color
    st.markdown(
        f"""
        <div style="background:#333;border-radius:8px;height:18px;width:100%;margin-bottom:4px">
          <div style="background:{bar_color};width:{pct}%;height:100%;
                      border-radius:8px;transition:width 0.3s"></div>
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
          <div style="background:#9b59b6;width:{pct}%;height:100%;border-radius:8px"></div>
        </div>
        <div style="font-size:11px;color:#aaa;margin-bottom:8px">
          XP {xp} / {needed}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SHAPE Agent 16 RPG",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
body { background-color: #1a1a2e; color: #eee; }
.stButton>button {
    background: #16213e; color: #eee; border: 1px solid #0f3460;
    border-radius: 6px; padding: 8px 20px; font-size: 15px;
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
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "screen":       "title",      # title | world | battle | gameover | victory
        "player_id":    None,
        "battle":       None,         # BattleState
        "last_result":  None,         # result dict from answer_question
        "selected_zone":None,
        "message_log":  [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()
S = st.session_state


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
                st.rerun()
            else:
                st.warning("Enter a name to begin.")

        st.markdown("---")
        st.markdown("""
        <div style='font-size:13px;color:#777;text-align:center'>
        ⚔️ Answer Python questions to deal damage<br>
        ❤️ Wrong answers hurt YOU<br>
        🏆 Defeat enemies to earn XP and level up<br>
        🗺️ Explore 6 zones — defeat the final BOSS
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
            S["screen"]  = "world"
            S["battle"]  = None
            S["last_result"] = None
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN: WORLD MAP
# ══════════════════════════════════════════════════════════════════════════════

def screen_world() -> None:
    player = get_player(S["player_id"])
    cleared = json.loads(player["zones_cleared"])

    st.markdown(f"## 🗺️ World Map — Choose Your Zone")
    st.markdown(f"Current zone: **{player['current_zone']}**")
    st.markdown("---")

    cols = st.columns(3)
    for i, zone in enumerate(ZONES_IN_ORDER):
        unlocked = zone in available_zones(S["player_id"])
        is_cleared = zone in cleared
        emoji = ZONE_EMOJI.get(zone, "🌐")

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
# SCREEN: ZONE SELECT (pick enemy)
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
                # Override to fight specific enemy
                import random as _r
                battle.enemy    = dict(enemy)
                battle.enemy_hp = enemy["hp"]
                battle.enemy_max_hp = enemy["hp"]
                S["battle"]      = battle
                S["last_result"] = None
                S["screen"]      = "battle"
                st.rerun()

    if st.button("← Back to World Map"):
        S["screen"] = "world"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN: BATTLE
# ══════════════════════════════════════════════════════════════════════════════

def screen_battle() -> None:
    battle: BattleState = S["battle"]
    player = get_player(S["player_id"])

    # ── Layout ────────────────────────────────────────────────────────────────
    left, mid, right = st.columns([2, 3, 2])

    # Player side
    with left:
        st.markdown("### 🧑‍💻 Agent 16")
        _sprite("player", width=150)
        st.markdown(f"**{player['display_name']}**  Lv.{player['level']}")
        _hp_bar(player["hp"], player["max_hp"])

    # Battle arena centre
    with mid:
        st.markdown(
            f"<div style='text-align:center;font-size:28px;color:#e94560;"
            f"font-weight:bold;padding:10px'>VS</div>",
            unsafe_allow_html=True,
        )
        # Last result message
        if S["last_result"]:
            r = S["last_result"]
            css = "result-correct" if r["correct"] else "result-wrong"
            st.markdown(
                f"<div class='{css}'>{r['message']}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='font-size:13px;color:#aaa;margin-top:6px'>"
                f"💡 {r['explanation']}</div>",
                unsafe_allow_html=True,
            )

        # Check battle over
        if battle.outcome == "win":
            st.success(f"🏆 Victory! You defeated {battle.enemy['name']}!")
            if st.button("🗺️ Return to World Map"):
                S["screen"] = "world"; S["battle"] = None; S["last_result"] = None
                st.rerun()
            return
        elif battle.outcome == "loss":
            st.error("💀 Defeated! You recover with partial HP...")
            if st.button("🗺️ Return to World Map"):
                S["screen"] = "world"; S["battle"] = None; S["last_result"] = None
                st.rerun()
            return
        elif battle.outcome == "fled":
            st.warning("🏃 You fled the battle!")
            if st.button("🗺️ Return to World Map"):
                S["screen"] = "world"; S["battle"] = None; S["last_result"] = None
                st.rerun()
            return

        # ── Question ──────────────────────────────────────────────────────────
        q = battle.current_q
        if q:
            st.markdown(
                f"<div class='question-box'>"
                f"<b>Turn {battle.turn + 1}</b> · Zone: {battle.zone}<br><br>"
                f"{q['prompt'].replace(chr(10), '<br>')}"
                f"</div>",
                unsafe_allow_html=True,
            )
            labels = ["A", "B", "C", "D"]
            for idx, choice in enumerate(q["choices"]):
                if st.button(f"{labels[idx]}.  {choice}", key=f"choice_{idx}_{battle.turn}",
                             use_container_width=True):
                    result = answer_question(battle, idx)
                    S["last_result"] = result
                    st.rerun()

            st.markdown("---")
            if st.button("🏃 Flee (take half damage)", use_container_width=False):
                flee_battle(battle)
                S["last_result"] = None
                st.rerun()

    # Enemy side
    with right:
        st.markdown(f"### {battle.enemy['name']}")
        _sprite(battle.enemy["sprite"], width=150)
        st.markdown(f"⚔️ ATK: {battle.enemy['attack']}")
        _hp_bar(battle.enemy_hp, battle.enemy_max_hp, color="#e74c3c")


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
