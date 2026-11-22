"""
shape_consolidate.py
--------------------
Step 2 — Offline Consolidation / Replay Pass  ("sleep job")

This module implements the memory consolidation pipeline for SHAPE Agent 16.
It is designed to be run as a scheduled background job *between* sessions —
analogous to the sleep-phase memory consolidation observed in biological memory.

Consolidation pipeline
─────────────────────
  Phase A │ SCORE     – Re-score all un-replayed episodes by salience
  Phase B │ FILTER    – Separate high-salience, non-contradicted items
                        from ephemeral session chatter
  Phase C │ REPLAY    – Walk high-salience items; write / update distilled
                        memory entries (the "low-rank adapter" proxy)
  Phase D │ PRUNE     – Mark distractor / superseded / low-salience episodes
                        as replayed=1 so they are skipped in future passes

Key design decisions
────────────────────
  - Base weights are NEVER mutated.  Distilled memory is a separate table
    (distilled_memory) that acts as a soft key-value store retrieved at
    session start — equivalent to a LoRA adapter that augments but does not
    overwrite the base model's weights.
  - Contradictions win: if an episode supersedes an older one, the new
    value is what gets written to distilled_memory.
  - Confidence propagation: an episode that was itself produced from a
    high-confidence correction is promoted to 'high' confidence in the
    distilled store.

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

import shape_db_handler as db
from shape_memory import (
    init_memory_tables,
    get_active_episodes,
    upsert_distilled_memory,
)

# ── Thresholds ────────────────────────────────────────────────────────────────

#: Minimum salience to include in replay (Phase C)
REPLAY_SALIENCE_THRESHOLD: float = 0.4

#: Maximum salience that qualifies a turn as "ephemeral chatter" to prune
PRUNE_SALIENCE_CEILING: float = 0.2


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ConsolidationReport:
    learner_id:        str
    total_episodes:    int              = 0
    replayed_count:    int              = 0
    pruned_count:      int              = 0
    distilled_count:   int              = 0
    skipped_count:     int              = 0
    subject_log:       list[str]        = field(default_factory=list)
    run_at:            str              = ""

    def summary(self) -> str:
        return (
            f"Consolidation report for learner '{self.learner_id}' "
            f"[{self.run_at}]\n"
            f"  Total episodes examined : {self.total_episodes}\n"
            f"  Distilled (upserted)    : {self.distilled_count}\n"
            f"  Replayed (marked done)  : {self.replayed_count}\n"
            f"  Pruned (ephemeral)      : {self.pruned_count}\n"
            f"  Skipped (already done)  : {self.skipped_count}\n"
            f"  Subjects consolidated   : {', '.join(self.subject_log) or 'none'}"
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mark_replayed(episode_ids: Iterable[int]) -> None:
    """Set replayed=1 for all given episode IDs in one transaction."""
    ids = list(episode_ids)
    if not ids:
        return
    placeholders = ",".join("?" * len(ids))
    conn = db._connect()
    with conn:
        conn.execute(
            f"UPDATE episodes SET replayed=1 WHERE episode_id IN ({placeholders})",
            ids,
        )
    conn.close()


def _get_unreplayed_episodes_for_learner(learner_id: str) -> list[dict]:
    """
    Fetch all episodes (including superseded ones) that have not yet
    been processed by the consolidation job.
    """
    init_memory_tables()
    conn = db._connect()
    rows = conn.execute(
        "SELECT * FROM episodes WHERE learner_id=? AND replayed=0 "
        "ORDER BY salience DESC, timestamp ASC",
        (learner_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _infer_confidence(episode: dict) -> str:
    """
    Derive a confidence level for the distilled store from the episode.
    Corrections and explicitly high-confidence episodes → 'high'.
    Low-salience or low-confidence → 'low'.  Everything else → 'medium'.
    """
    if episode["episode_type"] == "correction" or episode["confidence"] == "high":
        return "high"
    if episode["salience"] < 0.35 or episode["confidence"] == "low":
        return "low"
    return "medium"


# ── Main consolidation entry-point ────────────────────────────────────────────

def run_consolidation(learner_id: str) -> ConsolidationReport:
    """
    Execute the full 4-phase consolidation pipeline for one learner and
    return a ConsolidationReport.

    This is the function to call from a scheduler (e.g. APScheduler, cron,
    or a background thread) after a session closes.

    Parameters
    ----------
    learner_id : stable learner identifier matching learners.learner_id
    """
    report = ConsolidationReport(
        learner_id=learner_id,
        run_at=datetime.now(timezone.utc).isoformat(),
    )

    # ── Phase A │ SCORE ───────────────────────────────────────────────────────
    all_eps = _get_unreplayed_episodes_for_learner(learner_id)
    report.total_episodes = len(all_eps)

    if not all_eps:
        return report  # nothing to consolidate

    # ── Phase B │ FILTER ──────────────────────────────────────────────────────
    # Split into high-value (replay) vs ephemeral (prune).
    # Superseded episodes are always pruned regardless of salience.
    high_value: list[dict] = []
    ephemeral_ids: list[int] = []

    for ep in all_eps:
        if ep["superseded"] == 1:
            ephemeral_ids.append(ep["episode_id"])
        elif ep["salience"] < PRUNE_SALIENCE_CEILING:
            ephemeral_ids.append(ep["episode_id"])
        elif ep["salience"] >= REPLAY_SALIENCE_THRESHOLD:
            high_value.append(ep)
        else:
            # mid-range salience: skip for now (not pruned, not replayed)
            report.skipped_count += 1

    # ── Phase C │ REPLAY ──────────────────────────────────────────────────────
    # Group by subject: last-write (highest timestamp) wins within a subject.
    subject_map: dict[str, dict] = {}
    for ep in high_value:
        subj = ep["subject"]
        if subj not in subject_map:
            subject_map[subj] = ep
        else:
            # Keep the more-recent one (correction > earlier fact)
            if ep["timestamp"] > subject_map[subj]["timestamp"]:
                subject_map[subj] = ep

    replayed_ids: list[int] = []
    for subj, ep in subject_map.items():
        confidence = _infer_confidence(ep)
        upsert_distilled_memory(
            learner_id  = learner_id,
            subject     = subj,
            content     = ep["content"],
            source_ids  = [ep["episode_id"]],
            confidence  = confidence,
        )
        replayed_ids.append(ep["episode_id"])
        report.distilled_count += 1
        report.subject_log.append(subj)

    # Mark all high-value episodes for this batch as replayed
    # (even ones that lost the subject-map race — they were considered)
    all_high_ids = [ep["episode_id"] for ep in high_value]
    _mark_replayed(all_high_ids)
    report.replayed_count = len(all_high_ids)

    # ── Phase D │ PRUNE ───────────────────────────────────────────────────────
    _mark_replayed(ephemeral_ids)
    report.pruned_count = len(ephemeral_ids)

    return report


# ── Convenience: consolidate all learners with pending episodes ───────────────

def consolidate_all() -> list[ConsolidationReport]:
    """
    Run consolidation for every learner that has un-replayed episodes.
    Returns one ConsolidationReport per affected learner.

    Intended for use by a nightly cron job or an end-of-session hook:

        from shape_consolidate import consolidate_all
        reports = consolidate_all()
        for r in reports:
            print(r.summary())
    """
    init_memory_tables()
    conn = db._connect()
    rows = conn.execute(
        "SELECT DISTINCT learner_id FROM episodes WHERE replayed=0"
    ).fetchall()
    conn.close()

    reports: list[ConsolidationReport] = []
    for row in rows:
        report = run_consolidation(row["learner_id"])
        reports.append(report)
    return reports
