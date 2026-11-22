"""
shape_memory.py
---------------
Step 1 — Wake Phase (Episodic Encoding)

Implements the episodic memory layer for SHAPE Agent 16's 4-Step Demo Protocol.
Each conversational turn can be logged as an *episode* with:
  - a UTC timestamp
  - a salience score  (0.0 – 1.0)
  - a confidence tag  ('high' | 'medium' | 'low')
  - an episode_type   ('fact' | 'preference' | 'correction' | 'distractor' | 'skill')
  - an optional contradiction_of reference to a prior episode_id

The module handles:
  - Episode insertion (log_episode)
  - Contradiction detection: if a new 'correction' episode is logged,
    any prior episode with the same subject is superseded automatically.
  - Retrieval helpers used by the consolidation job and recall probe.

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import shape_db_handler as db  # re-use the existing DB connection pattern

# ── Schema bootstrap (called at import or explicitly) ────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS episodes (
    episode_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT    NOT NULL,
    learner_id      TEXT    NOT NULL,
    turn_number     INTEGER NOT NULL,
    episode_type    TEXT    NOT NULL
        CHECK(episode_type IN ('fact','preference','correction','distractor','skill')),
    subject         TEXT    NOT NULL,
    content         TEXT    NOT NULL,
    salience        REAL    NOT NULL DEFAULT 0.5,
    confidence      TEXT    NOT NULL DEFAULT 'medium'
        CHECK(confidence IN ('high','medium','low')),
    contradiction_of INTEGER REFERENCES episodes(episode_id),
    superseded      INTEGER NOT NULL DEFAULT 0,
    replayed        INTEGER NOT NULL DEFAULT 0,
    timestamp       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS distilled_memory (
    memory_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id  TEXT    NOT NULL,
    subject     TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    source_ids  TEXT    NOT NULL DEFAULT '[]',
    confidence  TEXT    NOT NULL DEFAULT 'high',
    consolidated_at TEXT NOT NULL,
    updated_at  TEXT    NOT NULL,
    UNIQUE(learner_id, subject)
);
"""


def init_memory_tables() -> None:
    """Create episodes and distilled_memory tables if they don't exist."""
    conn = db._connect()
    conn.executescript(_DDL)
    conn.close()


# ── Salience scoring heuristic ────────────────────────────────────────────────

_TYPE_SALIENCE: dict[str, float] = {
    "correction":  1.0,   # corrections are maximally salient
    "fact":        0.7,
    "preference":  0.8,
    "skill":       0.75,
    "distractor":  0.1,   # small-talk / off-topic chatter
}


def _score_salience(episode_type: str, explicit_salience: float | None) -> float:
    if explicit_salience is not None:
        return max(0.0, min(1.0, explicit_salience))
    return _TYPE_SALIENCE.get(episode_type, 0.5)


# ── Core API ──────────────────────────────────────────────────────────────────

def log_episode(
    session_id:   str,
    learner_id:   str,
    turn_number:  int,
    episode_type: str,
    subject:      str,
    content:      str,
    salience:     float | None = None,
    confidence:   str          = "medium",
) -> int:
    """
    Persist one episode and return its episode_id.

    If episode_type == 'correction', any prior episode for the same
    (learner_id, subject) is marked superseded=1 and linked back via
    contradiction_of.

    Parameters
    ----------
    session_id   : active session UUID
    learner_id   : stable learner identifier
    turn_number  : turn within the session
    episode_type : one of fact | preference | correction | distractor | skill
    subject      : short label for the topic/attribute being encoded
                   (e.g. "preferred_language", "project_name")
    content      : the actual value or statement to remember
    salience     : explicit 0-1 override; computed from type when omitted
    confidence   : 'high' | 'medium' | 'low'
    """
    init_memory_tables()
    computed_salience = _score_salience(episode_type, salience)
    now = datetime.now(timezone.utc).isoformat()

    conn = db._connect()
    contradiction_of: int | None = None

    if episode_type == "correction":
        # Supersede all prior non-distractor episodes on this subject
        prior = conn.execute(
            "SELECT episode_id FROM episodes "
            "WHERE learner_id=? AND subject=? AND superseded=0 "
            "ORDER BY episode_id DESC LIMIT 1",
            (learner_id, subject),
        ).fetchone()
        if prior:
            contradiction_of = prior["episode_id"]
            conn.execute(
                "UPDATE episodes SET superseded=1 WHERE learner_id=? AND subject=?",
                (learner_id, subject),
            )

    with conn:
        cur = conn.execute(
            """
            INSERT INTO episodes
              (session_id, learner_id, turn_number, episode_type,
               subject, content, salience, confidence,
               contradiction_of, superseded, replayed, timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,0,0,?)
            """,
            (session_id, learner_id, turn_number, episode_type,
             subject, content, computed_salience, confidence,
             contradiction_of, now),
        )
        episode_id = cur.lastrowid
    conn.close()
    return episode_id  # type: ignore[return-value]


def get_active_episodes(
    learner_id:  str,
    min_salience: float = 0.0,
) -> list[dict]:
    """
    Return all non-superseded episodes for a learner, ordered by
    salience descending.  Optionally filter by minimum salience.
    """
    init_memory_tables()
    conn = db._connect()
    rows = conn.execute(
        "SELECT * FROM episodes "
        "WHERE learner_id=? AND superseded=0 AND salience>=? "
        "ORDER BY salience DESC, timestamp DESC",
        (learner_id, min_salience),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_episodes_for_session(session_id: str) -> list[dict]:
    """Return all episodes logged within a specific session."""
    init_memory_tables()
    conn = db._connect()
    rows = conn.execute(
        "SELECT * FROM episodes WHERE session_id=? ORDER BY turn_number",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_distilled_memory(learner_id: str) -> list[dict]:
    """Return consolidated (distilled) memory entries for a learner."""
    init_memory_tables()
    conn = db._connect()
    rows = conn.execute(
        "SELECT * FROM distilled_memory WHERE learner_id=? ORDER BY updated_at DESC",
        (learner_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_distilled_memory(
    learner_id:  str,
    subject:     str,
    content:     str,
    source_ids:  list[int],
    confidence:  str = "high",
) -> None:
    """
    Write or update a distilled memory entry — the output of offline
    consolidation.  Existing entries for the same (learner_id, subject)
    are updated in place so only the most-recent consolidated value persists.
    """
    init_memory_tables()
    now = datetime.now(timezone.utc).isoformat()
    conn = db._connect()
    with conn:
        conn.execute(
            """
            INSERT INTO distilled_memory
              (learner_id, subject, content, source_ids, confidence,
               consolidated_at, updated_at)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(learner_id, subject) DO UPDATE SET
                content          = excluded.content,
                source_ids       = excluded.source_ids,
                confidence       = excluded.confidence,
                updated_at       = excluded.updated_at
            """,
            (learner_id, subject, content,
             json.dumps(source_ids), confidence, now, now),
        )
    conn.close()
