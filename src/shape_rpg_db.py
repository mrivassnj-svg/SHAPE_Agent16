"""
shape_rpg_db.py
---------------
SQLite schema additions for SHAPE Agent 16 RPG mode.
Extends shape.db with RPG-specific tables without touching the existing schema.

Tables added:
  rpg_players     – one row per player (HP, XP, level, zone, gold)
  rpg_battles     – one battle record per enemy encounter
  rpg_battle_turns– one row per question asked in a battle

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import sqlite3

DB_PATH = Path(__file__).parent.parent / "data" / "shape.db"

# XP required to reach each level: level_thresholds[i] = XP needed for level i+2
XP_THRESHOLDS = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200]

MAX_HP_PER_LEVEL = [100, 120, 145, 175, 210, 250, 295, 345, 400, 460]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_rpg_tables() -> None:
    conn = _connect()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS rpg_players (
            player_id    TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            hp           INTEGER NOT NULL DEFAULT 100,
            max_hp       INTEGER NOT NULL DEFAULT 100,
            xp           INTEGER NOT NULL DEFAULT 0,
            level        INTEGER NOT NULL DEFAULT 1,
            gold         INTEGER NOT NULL DEFAULT 0,
            current_zone TEXT NOT NULL DEFAULT 'Syntax Swamp',
            zones_cleared TEXT NOT NULL DEFAULT '[]',
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rpg_battles (
            battle_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id    TEXT NOT NULL,
            zone         TEXT NOT NULL,
            enemy_name   TEXT NOT NULL,
            enemy_hp_start INTEGER NOT NULL,
            outcome      TEXT CHECK(outcome IN ('win','loss','fled','ongoing')) DEFAULT 'ongoing',
            xp_earned    INTEGER NOT NULL DEFAULT 0,
            gold_earned  INTEGER NOT NULL DEFAULT 0,
            started_at   TEXT NOT NULL,
            ended_at     TEXT
        );

        CREATE TABLE IF NOT EXISTS rpg_battle_turns (
            turn_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            battle_id    INTEGER NOT NULL REFERENCES rpg_battles(battle_id),
            question_id  TEXT NOT NULL,
            player_answer INTEGER NOT NULL,
            correct      INTEGER NOT NULL,
            damage_dealt INTEGER NOT NULL DEFAULT 0,
            damage_taken INTEGER NOT NULL DEFAULT 0,
            timestamp    TEXT NOT NULL
        );
        """)
    conn.close()


# ── Player helpers ────────────────────────────────────────────────────────────

def upsert_player(player_id: str, display_name: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        conn.execute("""
            INSERT INTO rpg_players
              (player_id, display_name, hp, max_hp, xp, level, gold,
               current_zone, zones_cleared, created_at, updated_at)
            VALUES (?,?,100,100,0,1,0,'Syntax Swamp','[]',?,?)
            ON CONFLICT(player_id) DO UPDATE SET
                display_name = excluded.display_name,
                updated_at   = excluded.updated_at
        """, (player_id, display_name, now, now))
    conn.close()


def get_player(player_id: str) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM rpg_players WHERE player_id=?", (player_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_player(player_id: str, **fields) -> None:
    """Update arbitrary player fields."""
    now = datetime.now(timezone.utc).isoformat()
    fields["updated_at"] = now
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [player_id]
    conn = _connect()
    with conn:
        conn.execute(f"UPDATE rpg_players SET {set_clause} WHERE player_id=?", values)
    conn.close()


def xp_for_next_level(level: int) -> int:
    """Total XP required to reach (level+1). Returns 99999 if max level."""
    if level - 1 < len(XP_THRESHOLDS):
        return XP_THRESHOLDS[level - 1]
    return 99999


def max_hp_for_level(level: int) -> int:
    idx = min(level - 1, len(MAX_HP_PER_LEVEL) - 1)
    return MAX_HP_PER_LEVEL[idx]


def apply_xp(player_id: str, xp_gained: int) -> dict:
    """
    Add XP to player; handle level-up.
    Returns dict with keys: leveled_up (bool), new_level (int), new_xp (int).
    """
    player = get_player(player_id)
    if not player:
        return {"leveled_up": False, "new_level": 1, "new_xp": 0}

    new_xp    = player["xp"] + xp_gained
    new_level = player["level"]
    leveled_up = False

    # Check for level up
    while new_level < len(XP_THRESHOLDS) and new_xp >= XP_THRESHOLDS[new_level - 1]:
        new_level  += 1
        leveled_up  = True

    new_max_hp = max_hp_for_level(new_level)
    # Restore HP on level up
    new_hp = new_max_hp if leveled_up else player["hp"]

    save_player(player_id, xp=new_xp, level=new_level, max_hp=new_max_hp, hp=new_hp)
    return {"leveled_up": leveled_up, "new_level": new_level, "new_xp": new_xp}


# ── Battle helpers ────────────────────────────────────────────────────────────

def start_battle(player_id: str, zone: str, enemy_name: str, enemy_hp: int) -> int:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        cur = conn.execute("""
            INSERT INTO rpg_battles (player_id,zone,enemy_name,enemy_hp_start,started_at)
            VALUES (?,?,?,?,?)
        """, (player_id, zone, enemy_name, enemy_hp, now))
        battle_id = cur.lastrowid
    conn.close()
    return battle_id


def end_battle(battle_id: int, outcome: str, xp_earned: int, gold_earned: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        conn.execute("""
            UPDATE rpg_battles SET outcome=?, xp_earned=?, gold_earned=?, ended_at=?
            WHERE battle_id=?
        """, (outcome, xp_earned, gold_earned, now, battle_id))
    conn.close()


def log_battle_turn(battle_id: int, question_id: str, player_answer: int,
                    correct: bool, damage_dealt: int, damage_taken: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        conn.execute("""
            INSERT INTO rpg_battle_turns
              (battle_id,question_id,player_answer,correct,damage_dealt,damage_taken,timestamp)
            VALUES (?,?,?,?,?,?,?)
        """, (battle_id, question_id, player_answer, int(correct),
              damage_dealt, damage_taken, now))
    conn.close()


def get_player_stats_summary(player_id: str) -> dict:
    """Return aggregated battle stats for the player."""
    conn = _connect()
    wins   = conn.execute("SELECT COUNT(*) FROM rpg_battles WHERE player_id=? AND outcome='win'",   (player_id,)).fetchone()[0]
    losses = conn.execute("SELECT COUNT(*) FROM rpg_battles WHERE player_id=? AND outcome='loss'",  (player_id,)).fetchone()[0]
    total_xp = conn.execute("SELECT SUM(xp_earned) FROM rpg_battles WHERE player_id=?", (player_id,)).fetchone()[0] or 0
    conn.close()
    return {"wins": wins, "losses": losses, "total_xp_from_battles": total_xp}
