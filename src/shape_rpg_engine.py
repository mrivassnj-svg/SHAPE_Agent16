"""
shape_rpg_engine.py
-------------------
Pure-logic battle engine for SHAPE Agent 16 RPG.
No UI dependencies — Streamlit calls this.

Battle flow per turn:
  1. Engine presents a question from the current zone
  2. Player selects A/B/C/D
  3. Engine resolves:
       Correct  → player deals damage to enemy, gains partial XP
       Wrong    → enemy deals damage to player
  4. Check win/loss conditions
  5. On win: full XP + gold awarded, zone progression checked

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

from shape_rpg_questions import (
    get_zone_questions, get_random_question,
    ZONES_IN_ORDER, ZONE_ENEMIES,
)
from shape_rpg_db import (
    get_player, save_player, apply_xp,
    start_battle, end_battle, log_battle_turn,
    max_hp_for_level,
)


# ── Battle state dataclass ────────────────────────────────────────────────────

@dataclass
class BattleState:
    player_id:      str
    battle_id:      int
    zone:           str
    enemy:          dict                   # from ZONE_ENEMIES
    enemy_hp:       int
    enemy_max_hp:   int
    question_pool:  list                   # remaining questions for this battle
    current_q:      dict | None = None
    turn:           int          = 0
    xp_earned:      int          = 0
    gold_earned:    int          = 0
    outcome:        str          = "ongoing"  # ongoing / win / loss / fled
    log:            list         = field(default_factory=list)


# ── Engine API ────────────────────────────────────────────────────────────────

def new_battle(player_id: str, zone: str) -> BattleState:
    """
    Initialise a new battle for the given player in the given zone.
    Randomly pick an enemy from the zone's roster.
    """
    enemies = ZONE_ENEMIES.get(zone, ZONE_ENEMIES["Syntax Swamp"])
    enemy   = dict(random.choice(enemies))        # copy so we can mutate hp

    battle_id = start_battle(player_id, zone, enemy["name"], enemy["hp"])

    q_pool = get_zone_questions(zone)
    if not q_pool:
        q_pool = get_zone_questions("Syntax Swamp")

    state = BattleState(
        player_id    = player_id,
        battle_id    = battle_id,
        zone         = zone,
        enemy        = enemy,
        enemy_hp     = enemy["hp"],
        enemy_max_hp = enemy["hp"],
        question_pool= q_pool,
    )
    state.current_q = _next_question(state)
    return state


def answer_question(state: BattleState, choice_index: int) -> dict:
    """
    Process the player's answer.
    Returns a result dict:
      correct       bool
      damage_dealt  int   (to enemy, 0 if wrong)
      damage_taken  int   (to player, 0 if correct)
      explanation   str
      enemy_hp      int   (remaining)
      player_hp     int   (remaining)
      outcome       str   (ongoing/win/loss)
      xp_this_turn  int
      level_up      bool
      new_level     int
      message       str   (narrative text)
    """
    q       = state.current_q
    correct = (choice_index == q["answer"])
    player  = get_player(state.player_id)

    damage_dealt = 0
    damage_taken = 0
    xp_this_turn = 0
    level_up     = False
    new_level    = player["level"]

    if correct:
        damage_dealt  = q["damage"]
        state.enemy_hp = max(0, state.enemy_hp - damage_dealt)
        xp_this_turn  = q["xp"] // 2          # partial XP mid-battle
        state.xp_earned += xp_this_turn
        message = f"⚔️ Correct! You dealt **{damage_dealt}** damage to {state.enemy['name']}!"
    else:
        damage_taken = player["attack"] if "attack" in player else state.enemy["attack"]
        new_hp = max(0, player["hp"] - damage_taken)
        save_player(state.player_id, hp=new_hp)
        player = get_player(state.player_id)        # refresh
        message = f"❌ Wrong! {state.enemy['name']} struck back for **{damage_taken}** damage!"

    # Log the turn
    log_battle_turn(
        state.battle_id, q["id"], choice_index,
        correct, damage_dealt, damage_taken,
    )
    state.log.append({
        "turn": state.turn,
        "q": q["prompt"][:60],
        "correct": correct,
        "dmg_dealt": damage_dealt,
        "dmg_taken": damage_taken,
    })
    state.turn += 1

    # ── Check win ──────────────────────────────────────────────────────────
    if state.enemy_hp <= 0:
        state.outcome   = "win"
        full_xp         = state.enemy["xp_reward"]
        gold            = random.randint(5, 20) * state.enemy.get("tier_gold", 1)
        state.xp_earned += full_xp
        state.gold_earned = gold

        lv_result = apply_xp(state.player_id, state.xp_earned)
        save_player(state.player_id, gold=player["gold"] + gold)
        end_battle(state.battle_id, "win", state.xp_earned, gold)

        level_up  = lv_result["leveled_up"]
        new_level = lv_result["new_level"]
        message  += f"\n\n🏆 **{state.enemy['name']} defeated!** +{state.xp_earned} XP, +{gold} 🪙"
        if level_up:
            message += f"\n\n✨ **LEVEL UP! You are now Level {new_level}! HP fully restored!**"

        # Check zone cleared
        _check_zone_clear(state.player_id, state.zone)

    # ── Check loss ─────────────────────────────────────────────────────────
    elif player["hp"] <= 0:
        state.outcome = "loss"
        end_battle(state.battle_id, "loss", state.xp_earned, 0)
        # Partial XP even on loss
        apply_xp(state.player_id, state.xp_earned // 2)
        # Restore a small amount of HP so player isn't stuck at 0
        save_player(state.player_id, hp=max_hp_for_level(player["level"]) // 4)
        message += f"\n\n💀 **You were defeated...** You recover with partial HP. Try again!"

    # ── Still ongoing — load next question ────────────────────────────────
    else:
        state.current_q = _next_question(state)

    return {
        "correct":      correct,
        "damage_dealt": damage_dealt,
        "damage_taken": damage_taken,
        "explanation":  q["explanation"],
        "enemy_hp":     state.enemy_hp,
        "enemy_max_hp": state.enemy_max_hp,
        "player_hp":    player["hp"],
        "player_max_hp":player["max_hp"],
        "outcome":      state.outcome,
        "xp_this_turn": xp_this_turn,
        "level_up":     level_up,
        "new_level":    new_level,
        "message":      message,
    }


def flee_battle(state: BattleState) -> None:
    """Player flees — lose a small amount of HP, no XP."""
    player = get_player(state.player_id)
    flee_damage = state.enemy["attack"] // 2
    save_player(state.player_id, hp=max(1, player["hp"] - flee_damage))
    end_battle(state.battle_id, "fled", 0, 0)
    state.outcome = "fled"


# ── Zone helpers ──────────────────────────────────────────────────────────────

def available_zones(player_id: str) -> list[str]:
    """Return zones the player can currently enter (all cleared zones + next)."""
    import json
    player  = get_player(player_id)
    cleared = json.loads(player["zones_cleared"]) if player else []
    result  = []
    for z in ZONES_IN_ORDER:
        result.append(z)
        if z not in cleared:
            break                   # can only access up to first uncleared zone
    return result


def _check_zone_clear(player_id: str, zone: str) -> None:
    """Mark zone as cleared if the player just beat the boss (last enemy listing)."""
    import json
    player  = get_player(player_id)
    cleared = json.loads(player["zones_cleared"])
    if zone not in cleared:
        cleared.append(zone)
        # Advance to next zone
        next_idx = ZONES_IN_ORDER.index(zone) + 1
        next_zone = ZONES_IN_ORDER[next_idx] if next_idx < len(ZONES_IN_ORDER) else zone
        save_player(player_id, zones_cleared=json.dumps(cleared), current_zone=next_zone)


def _next_question(state: BattleState) -> dict:
    """Pop the next question from the pool; refill if exhausted."""
    if not state.question_pool:
        state.question_pool = get_zone_questions(state.zone)
        if not state.question_pool:
            state.question_pool = [get_random_question()]
    return state.question_pool.pop(0)
