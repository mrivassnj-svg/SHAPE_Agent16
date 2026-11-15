"""
shape_db_handler.py
-------------------
SQLite persistence layer for SHAPE Agent 16 — Interactive Learning Companion.

Tables:
  learners          – one row per learner (profile + current level)
  sessions          – one row per conversation session
  interactions      – every turn (prompt → response) within a session
  assessments       – pre/post test scores per learner
  curriculum        – instructor-authored lessons (editable at runtime)
  policy_stats      – per-strategy cumulative reward for the RL policy

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "shape.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # timeout=10 prevents indefinite hangs when another thread holds a write lock.
    # check_same_thread=False is required for Gradio's thread-pool model.
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    # WAL set once at DB creation — not on every connection (avoids lock contention)
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Create all tables if they do not already exist."""
    conn = _connect()
    # Set WAL mode once here; subsequent connections inherit it from the DB file
    conn.execute("PRAGMA journal_mode=WAL;")
    # executescript commits automatically — don't wrap in `with conn`
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS learners (
        learner_id   TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        level        TEXT NOT NULL DEFAULT 'beginner',
        topics_seen  TEXT NOT NULL DEFAULT '[]',
        created_at   TEXT NOT NULL,
        updated_at   TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sessions (
        session_id  TEXT PRIMARY KEY,
        learner_id  TEXT NOT NULL REFERENCES learners(learner_id),
        started_at  TEXT NOT NULL,
        ended_at    TEXT,
        turn_count  INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS interactions (
        interaction_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id      TEXT NOT NULL REFERENCES sessions(session_id),
        turn_number     INTEGER NOT NULL,
        role            TEXT NOT NULL CHECK(role IN ('user','agent')),
        content         TEXT NOT NULL,
        strategy_used   TEXT,
        reward          REAL,
        timestamp       TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS assessments (
        assessment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id     TEXT NOT NULL REFERENCES learners(learner_id),
        phase          TEXT NOT NULL CHECK(phase IN ('pre','post')),
        score          REAL NOT NULL,
        answers        TEXT NOT NULL DEFAULT '{}',
        taken_at       TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS curriculum (
        lesson_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        topic        TEXT NOT NULL,
        level        TEXT NOT NULL CHECK(level IN ('beginner','intermediate','advanced')),
        title        TEXT NOT NULL,
        content      TEXT NOT NULL,
        keywords     TEXT NOT NULL DEFAULT '[]',
        author       TEXT NOT NULL DEFAULT 'instructor',
        created_at   TEXT NOT NULL,
        updated_at   TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS policy_stats (
        strategy     TEXT PRIMARY KEY,
        total_reward REAL NOT NULL DEFAULT 0.0,
        n_selected   INTEGER NOT NULL DEFAULT 0,
        q_value      REAL NOT NULL DEFAULT 0.0
    );
    """)
    conn.close()


# ── Learner helpers ────────────────────────────────────────────────────────────

def upsert_learner(learner_id: str, display_name: str, level: str = "beginner") -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        conn.execute("""
            INSERT INTO learners (learner_id, display_name, level, topics_seen, created_at, updated_at)
            VALUES (?, ?, ?, '[]', ?, ?)
            ON CONFLICT(learner_id) DO UPDATE SET
                display_name = excluded.display_name,
                level        = excluded.level,
                updated_at   = excluded.updated_at
        """, (learner_id, display_name, level, now, now))
    conn.close()


def get_learner(learner_id: str) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT * FROM learners WHERE learner_id = ?", (learner_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_learner_level(learner_id: str, level: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        conn.execute("UPDATE learners SET level=?, updated_at=? WHERE learner_id=?",
                     (level, now, learner_id))
    conn.close()


def add_topic_seen(learner_id: str, topic: str) -> None:
    learner = get_learner(learner_id)
    if learner is None:
        return
    topics = json.loads(learner["topics_seen"])
    if topic not in topics:
        topics.append(topic)
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        conn.execute("UPDATE learners SET topics_seen=?, updated_at=? WHERE learner_id=?",
                     (json.dumps(topics), now, learner_id))
    conn.close()


# ── Session helpers ────────────────────────────────────────────────────────────

def create_session(session_id: str, learner_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        conn.execute("INSERT OR IGNORE INTO sessions VALUES (?,?,?,NULL,0)",
                     (session_id, learner_id, now))
    conn.close()


def close_session(session_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        conn.execute("UPDATE sessions SET ended_at=? WHERE session_id=?", (now, session_id))
    conn.close()


def log_interaction(session_id: str, turn: int, role: str,
                    content: str, strategy: str | None = None,
                    reward: float | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        conn.execute("""
            INSERT INTO interactions
              (session_id, turn_number, role, content, strategy_used, reward, timestamp)
            VALUES (?,?,?,?,?,?,?)
        """, (session_id, turn, role, content, strategy, reward, now))
        conn.execute("UPDATE sessions SET turn_count = turn_count + 1 WHERE session_id=?",
                     (session_id,))
    conn.close()


# ── Assessment helpers ─────────────────────────────────────────────────────────

def record_assessment(learner_id: str, phase: str, score: float, answers: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        conn.execute("INSERT INTO assessments (learner_id,phase,score,answers,taken_at) VALUES (?,?,?,?,?)",
                     (learner_id, phase, score, json.dumps(answers), now))
    conn.close()


def get_assessments(learner_id: str) -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM assessments WHERE learner_id=? ORDER BY taken_at",
                        (learner_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Curriculum helpers ─────────────────────────────────────────────────────────

def add_lesson(topic: str, level: str, title: str, content: str,
               keywords: list[str], author: str = "instructor") -> int:
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    with conn:
        cur = conn.execute("""
            INSERT INTO curriculum (topic,level,title,content,keywords,author,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (topic, level, title, content, json.dumps(keywords), author, now, now))
        lesson_id = cur.lastrowid
    conn.close()
    return lesson_id


def search_lessons(query_keywords: list[str], level: str | None = None) -> list[dict]:
    """Return lessons whose keyword list overlaps with query_keywords."""
    conn = _connect()
    rows = conn.execute("SELECT * FROM curriculum ORDER BY created_at DESC").fetchall()
    conn.close()
    results = []
    for row in rows:
        if level and row["level"] != level:
            continue
        stored = set(json.loads(row["keywords"]))
        if stored & set(query_keywords):
            results.append(dict(row))
    return results


# ── Policy stats helpers ───────────────────────────────────────────────────────

def update_policy_stat(strategy: str, reward: float) -> None:
    conn = _connect()
    with conn:
        conn.execute("""
            INSERT INTO policy_stats (strategy, total_reward, n_selected, q_value)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(strategy) DO UPDATE SET
                total_reward = total_reward + excluded.total_reward,
                n_selected   = n_selected + 1,
                q_value      = (total_reward + excluded.total_reward) / (n_selected + 1)
        """, (strategy, reward, reward))
    conn.close()


def get_policy_stats() -> dict[str, dict]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM policy_stats").fetchall()
    conn.close()
    return {r["strategy"]: dict(r) for r in rows}


def get_recent_agent_rewards(session_id: str, limit: int = 5) -> list[float]:
    """Return the last `limit` non-null agent-turn rewards for a session."""
    conn = _connect()
    rows = conn.execute(
        "SELECT reward FROM interactions "
        "WHERE session_id=? AND role='agent' AND reward IS NOT NULL "
        "ORDER BY turn_number DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [r["reward"] for r in rows]
