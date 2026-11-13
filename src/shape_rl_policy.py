"""
shape_rl_policy.py
------------------
Contextual bandit / Q-value policy over 5 teaching strategies.
Uses epsilon-greedy action selection.  Q-values are persisted to
shape.db via shape_db_handler so the policy improves across sessions.

Teaching Strategies
-------------------
  EXPLAIN    – Direct explanation with worked example
  SOCRATIC   – Guided questioning toward the answer
  ANALOGY    – Real-world analogy-first framing
  SCAFFOLD   – Step-by-step incremental build-up
  CHALLENGE  – Harder extension problem first, then debrief

Reward Signal
-------------
  Correct answer on first attempt  →  +1.0
  Correct with one hint             →  +0.5
  Correct with two+ hints           →  +0.2
  Incorrect / gave up               →   0.0
  Safety/policy violation flagged   →  -0.5

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

import random
from enum import Enum

from shape_db_handler import get_policy_stats, update_policy_stat

EPSILON = 0.15          # exploration rate
DEFAULT_Q = 0.5         # optimistic initialisation for unseen strategies


class Strategy(str, Enum):
    EXPLAIN   = "EXPLAIN"
    SOCRATIC  = "SOCRATIC"
    ANALOGY   = "ANALOGY"
    SCAFFOLD  = "SCAFFOLD"
    CHALLENGE = "CHALLENGE"


ALL_STRATEGIES = list(Strategy)


# ── Reward constants ──────────────────────────────────────────────────────────

REWARD_CORRECT_FIRST   = 1.0
REWARD_CORRECT_HINT1   = 0.5
REWARD_CORRECT_HINT2   = 0.2
REWARD_WRONG           = 0.0
REWARD_VIOLATION       = -0.5


def compute_reward(correct: bool, hint_count: int, violation: bool = False) -> float:
    """
    Map an interaction outcome to a scalar reward.

    Parameters
    ----------
    correct    : learner's final answer was correct
    hint_count : number of hints the agent issued before success
    violation  : a safety / scope violation was triggered
    """
    if violation:
        return REWARD_VIOLATION
    if not correct:
        return REWARD_WRONG
    if hint_count == 0:
        return REWARD_CORRECT_FIRST
    if hint_count == 1:
        return REWARD_CORRECT_HINT1
    return REWARD_CORRECT_HINT2


def _load_q_table() -> dict[str, float]:
    """Pull persisted Q-values from DB; fall back to DEFAULT_Q."""
    stats = get_policy_stats()
    return {
        s.value: stats[s.value]["q_value"] if s.value in stats else DEFAULT_Q
        for s in ALL_STRATEGIES
    }


def select_strategy(learner_level: str = "beginner") -> Strategy:
    """
    Epsilon-greedy strategy selection.

    With probability EPSILON, pick a random strategy (explore).
    Otherwise, pick the strategy with the highest Q-value (exploit).

    Learner level biases random exploration toward appropriate strategies:
      beginner     → avoids CHALLENGE
      advanced     → avoids over-using EXPLAIN
    """
    q_table = _load_q_table()

    if random.random() < EPSILON:
        # Exploration — bias candidate pool by level
        if learner_level == "beginner":
            candidates = [s for s in ALL_STRATEGIES if s != Strategy.CHALLENGE]
        elif learner_level == "advanced":
            candidates = [s for s in ALL_STRATEGIES if s != Strategy.EXPLAIN]
        else:
            candidates = ALL_STRATEGIES
        return random.choice(candidates)

    # Exploitation — argmax Q
    return max(ALL_STRATEGIES, key=lambda s: q_table[s.value])


def record_outcome(strategy: Strategy, reward: float) -> None:
    """Persist the reward and update the running Q-value for the strategy."""
    update_policy_stat(strategy.value, reward)


def policy_summary() -> str:
    """Return a human-readable table of current Q-values."""
    q_table = _load_q_table()
    lines = ["Strategy   | Q-value | Selections", "-" * 38]
    stats = get_policy_stats()
    for s in ALL_STRATEGIES:
        q = q_table[s.value]
        n = stats[s.value]["n_selected"] if s.value in stats else 0
        lines.append(f"{s.value:<10} | {q:7.4f} | {n}")
    return "\n".join(lines)
