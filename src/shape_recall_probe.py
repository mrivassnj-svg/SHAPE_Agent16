"""
shape_recall_probe.py
---------------------
Step 3 — Cross-Session Recall & Transfer Probe

Tests that distilled memory persists and behaves correctly across
completely fresh sessions (zero prompt preamble).

Three probe types
─────────────────
  DIRECT       — Ask directly about a persistent attribute the agent
                 should remember (e.g. "What is my preferred language?").

  IMPLICIT     — Ask a technical/creative question where applying the
                 remembered context is natural, without naming the attribute
                 explicitly (e.g. code response in the learner's language).

  CONTRADICTION — Re-ask about an attribute that was corrected mid-session;
                  the stale / superseded value must NOT appear.

Usage (CLI / scripted)
──────────────────────
    python src/shape_recall_probe.py --learner alice
    python src/shape_recall_probe.py --learner alice --probe-type direct
    python src/shape_recall_probe.py --learner alice --probe-type contradiction

Usage (programmatic)
────────────────────
    from shape_recall_probe import run_all_probes
    results = run_all_probes("alice")
    for r in results:
        print(r.summary())

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

import shape_db_handler as db
from shape_memory import get_distilled_memory, get_active_episodes, init_memory_tables

ProbeType = Literal["direct", "implicit", "contradiction"]


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ProbeResult:
    probe_type:       ProbeType
    subject:          str
    expected_value:   str
    forbidden_value:  str | None   = None   # for contradiction probes
    matched:          bool         = False
    forbidden_found:  bool         = False
    retrieved_content: str         = ""
    notes:            str          = ""
    run_at:           str          = ""

    def passed(self) -> bool:
        """A probe passes when the expected value is found and no forbidden value leaks."""
        if self.probe_type == "contradiction":
            return self.matched and not self.forbidden_found
        return self.matched

    def summary(self) -> str:
        status = "✅ PASS" if self.passed() else "❌ FAIL"
        lines = [
            f"{status} [{self.probe_type.upper()}] subject='{self.subject}'",
            f"  expected   : {self.expected_value!r}",
            f"  retrieved  : {self.retrieved_content!r}",
        ]
        if self.forbidden_value:
            leak_flag = "⚠️  LEAKED" if self.forbidden_found else "✅ clean"
            lines.append(f"  forbidden  : {self.forbidden_value!r}  → {leak_flag}")
        if self.notes:
            lines.append(f"  notes      : {self.notes}")
        return "\n".join(lines)


# ── Probe runner ──────────────────────────────────────────────────────────────

def probe_direct(learner_id: str, subject: str, expected_value: str) -> ProbeResult:
    """
    Direct recall probe.

    Looks up the distilled_memory table for learner_id / subject and
    checks whether the stored content matches (case-insensitive substring).
    No LLM call — this tests the retrieval layer directly.
    """
    result = ProbeResult(
        probe_type     = "direct",
        subject        = subject,
        expected_value = expected_value,
        run_at         = datetime.now(timezone.utc).isoformat(),
    )
    memories = get_distilled_memory(learner_id)
    for mem in memories:
        if mem["subject"] == subject:
            result.retrieved_content = mem["content"]
            result.matched = expected_value.lower() in mem["content"].lower()
            if not result.matched:
                result.notes = "Subject found in distilled memory but value mismatch."
            return result

    result.notes = f"Subject '{subject}' not found in distilled_memory."
    return result


def probe_implicit(
    learner_id:    str,
    subject:       str,
    expected_value: str,
) -> ProbeResult:
    """
    Implicit transfer probe.

    Checks that the distilled_memory entry for `subject` could supply
    the right context if injected into a prompt without being named.
    The probe verifies the value exists in distilled memory *and* is
    marked high-enough confidence to be injected.

    In a live session, shape_agent_core would pull this via
    `load_memory_context()` before building the system prompt.
    """
    result = ProbeResult(
        probe_type     = "implicit",
        subject        = subject,
        expected_value = expected_value,
        run_at         = datetime.now(timezone.utc).isoformat(),
    )
    memories = get_distilled_memory(learner_id)
    for mem in memories:
        if mem["subject"] == subject and mem["confidence"] in ("high", "medium"):
            result.retrieved_content = mem["content"]
            result.matched = expected_value.lower() in mem["content"].lower()
            if not result.matched:
                result.notes = "Memory entry exists but expected value not present."
            else:
                result.notes = f"Memory confidence: {mem['confidence']}"
            return result

    result.notes = (
        f"No high/medium-confidence distilled memory for '{subject}'."
    )
    return result


def probe_contradiction(
    learner_id:    str,
    subject:       str,
    correct_value: str,
    stale_value:   str,
) -> ProbeResult:
    """
    Contradiction probe.

    Verifies that:
      1. The distilled memory holds the *corrected* value (correct_value).
      2. The *stale* (superseded) value does NOT appear anywhere in the
         active distilled memory for this subject.

    Also scans active (non-superseded) episodes to confirm the stale
    value is not still live there.
    """
    result = ProbeResult(
        probe_type     = "contradiction",
        subject        = subject,
        expected_value = correct_value,
        forbidden_value= stale_value,
        run_at         = datetime.now(timezone.utc).isoformat(),
    )

    # 1. Check distilled_memory
    memories = get_distilled_memory(learner_id)
    for mem in memories:
        if mem["subject"] == subject:
            result.retrieved_content = mem["content"]
            result.matched       = correct_value.lower() in mem["content"].lower()
            result.forbidden_found = stale_value.lower() in mem["content"].lower()
            if result.forbidden_found:
                result.notes = "Stale value leaked into distilled_memory!"
            return result

    # 2. If nothing distilled yet, fall back to active episode check
    active_eps = get_active_episodes(learner_id)
    for ep in active_eps:
        if ep["subject"] == subject:
            result.retrieved_content = ep["content"]
            result.matched       = correct_value.lower() in ep["content"].lower()
            result.forbidden_found = stale_value.lower() in ep["content"].lower()
            result.notes = "Checked live episodes (consolidation not yet run)."
            return result

    result.notes = (
        f"No distilled memory or active episode found for '{subject}'. "
        "Run consolidation first."
    )
    return result


# ── Build a standard probe suite for a learner ───────────────────────────────

def run_all_probes(learner_id: str) -> list[ProbeResult]:
    """
    Run the standard 3-category probe battery for a learner using
    whatever distilled memory exists in the DB.

    Returns a list of ProbeResult objects ready for inspection or
    further processing by the stability checker.
    """
    init_memory_tables()
    memories = get_distilled_memory(learner_id)
    if not memories:
        return [ProbeResult(
            probe_type     = "direct",
            subject        = "(none)",
            expected_value = "",
            notes          = "No distilled memory found — run consolidation first.",
            run_at         = datetime.now(timezone.utc).isoformat(),
        )]

    results: list[ProbeResult] = []

    for mem in memories:
        subject = mem["subject"]
        content = mem["content"]

        # Direct probe: exact subject lookup
        results.append(probe_direct(learner_id, subject, content))

        # Implicit probe: confidence-gated retrieval check
        results.append(probe_implicit(learner_id, subject, content))

    # Contradiction probes: scan for any episode that was superseded and
    # check the stale value doesn't appear in distilled memory.
    conn = db._connect()
    stale_rows = conn.execute(
        "SELECT e_old.subject, e_old.content AS stale_content, "
        "       e_new.content AS correct_content "
        "FROM episodes e_old "
        "JOIN episodes e_new "
        "  ON e_new.contradiction_of = e_old.episode_id "
        "WHERE e_old.learner_id=? AND e_old.superseded=1",
        (learner_id,),
    ).fetchall()
    conn.close()

    for row in stale_rows:
        results.append(probe_contradiction(
            learner_id    = learner_id,
            subject       = row["subject"],
            correct_value = row["correct_content"],
            stale_value   = row["stale_content"],
        ))

    return results


# ── Summary printer ───────────────────────────────────────────────────────────

def print_probe_report(results: list[ProbeResult]) -> None:
    passed = sum(1 for r in results if r.passed())
    print(f"\n{'='*60}")
    print(f"Cross-Session Recall & Transfer Probe — {len(results)} checks")
    print(f"{'='*60}")
    for r in results:
        print(r.summary())
    print(f"\n{'='*60}")
    print(f"Result: {passed}/{len(results)} passed")
    print(f"{'='*60}\n")


# ── CLI entry-point ───────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="SHAPE Agent 16 — Cross-Session Recall Probe"
    )
    parser.add_argument("--learner",     required=True,
                        help="Learner ID to probe")
    parser.add_argument("--probe-type",  choices=["direct","implicit","contradiction","all"],
                        default="all", help="Which probe type to run (default: all)")
    parser.add_argument("--subject",     default=None,
                        help="Subject to probe (optional; runs all if omitted)")
    args = parser.parse_args()

    import sys
    sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")

    if args.probe_type == "all" or args.subject is None:
        results = run_all_probes(args.learner)
    else:
        # Single-subject targeted probe
        memories = get_distilled_memory(args.learner)
        mem = next((m for m in memories if m["subject"] == args.subject), None)
        if mem is None:
            print(f"No distilled memory for subject '{args.subject}'.")
            return
        ptype: ProbeType = args.probe_type  # type: ignore[assignment]
        if ptype == "direct":
            results = [probe_direct(args.learner, args.subject, mem["content"])]
        elif ptype == "implicit":
            results = [probe_implicit(args.learner, args.subject, mem["content"])]
        else:
            results = [probe_contradiction(args.learner, args.subject, mem["content"], "")]

    print_probe_report(results)


if __name__ == "__main__":
    _cli()
