"""SHAPE Agent 16 — adaptive teaching policy (contextual bandit / Q-value).

Five teaching strategies. The policy learns from learner feedback, but a
reward increase is NOT proof of learning — learning is evaluated
independently with the pre/post assessment (see Evaluation Plan).
"""
import random

STRATEGIES = ["Worked example", "Concept explanation", "Small hint",
              "Simpler practice", "Challenge exercise"]
ALPHA = 0.2          # learning rate: Q[s] += ALPHA * (reward - Q[s])
EPSILON = 0.1        # epsilon-greedy exploration


def new_q_table():
    return {s: 0.0 for s in STRATEGIES}


def reward_for(passed, hints_used, concept_check_failed=False):
    """Documented reward function (from the project brief)."""
    if concept_check_failed:
        return -1.0
    if not passed:
        return -3.0
    if hints_used == 0:
        return 10.0
    if hints_used == 1:
        return 7.0
    return 4.0


def update_q(q_table, strategy, reward, alpha=ALPHA):
    """Q[s] += alpha * (reward - Q[s]). Returns (new_q, old_q)."""
    old = float(q_table.get(strategy, 0.0))
    new = old + alpha * (reward - old)
    q_table[strategy] = round(new, 3)
    return q_table[strategy], old


def select_strategy(q_table, rng=None, epsilon=EPSILON):
    """Epsilon-greedy: mostly the best-known strategy, sometimes explore.
    Ties are broken by the fixed STRATEGIES order, so results are stable."""
    rng = rng or random
    if rng.random() < epsilon:
        choice = rng.choice(STRATEGIES)
        return choice, f"Exploration (epsilon={epsilon}): tried '{choice}' to learn how it works for this learner."
    best = max(STRATEGIES, key=lambda s: q_table.get(s, 0.0))
    return best, (f"Exploitation: '{best}' has the highest Q-value "
                  f"({q_table.get(best, 0.0):.2f}) from past rewards.")


def strategy_for_lesson(lesson_id, q_table, rng=None):
    """Pick a strategy, with a sensible starting point per lesson."""
    choice, reason = select_strategy(q_table, rng=rng)
    return choice, reason


def q_table_rows(q_table):
    return [[s, round(float(q_table.get(s, 0.0)), 3)] for s in STRATEGIES]
