"""
shape_agent_core.py
-------------------
8-Step Orchestrator Loop for SHAPE Agent 16 — Interactive Learning Companion.

The orchestrator implements the ReAct (Reasoning + Acting) pattern layered
over a Chain-of-Thought scratchpad.  Each call to `run_turn()` executes
the full 8-step cycle and returns the agent's final reply.

8-Step Reasoning Cycle
──────────────────────
  Step 1 │ RECEIVE    – Ingest and validate user input (safety gate)
  Step 2 │ PROFILE    – Load learner profile; determine level & context
  Step 3 │ RETRIEVE   – Tool 2: keyword search against local curriculum
  Step 4 │ REASON     – Chain-of-Thought scratchpad + strategy selection (RL)
  Step 5 │ ACT        – Invoke tools (Tool 1: code runner) if needed
  Step 6 │ RESPOND    – Compose final reply using LLM with injected context
  Step 7 │ EVALUATE   – Infer reward signal; update RL policy and DB
  Step 8 │ ADAPT      – Update learner profile (level, topics seen)

Agent Roles (sub-agents via prompt personas)
─────────────────────────────────────────────
  Instructor        – primary teacher persona
  Debugger          – code error analysis persona
  Evaluator         – answer grading and feedback persona
  Learning Strategist – chooses teaching strategy and adjusts path

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

from __future__ import annotations

import os
import textwrap
import uuid
from dataclasses import dataclass, field

from groq import Groq  # pip install groq  (free tier, no credit card)
from groq import APIError

import shape_db_handler as db
from shape_safety import validate_user_prompt, fallback_response, agent_scope_reminder
from shape_tools import run_python_exercise, retrieve_curriculum
from shape_rl_policy import Strategy, select_strategy, compute_reward, record_outcome

# Current free models on Groq (Nov 2026). See https://console.groq.com/docs/models
# Override with: export SHAPE_MODEL=<any-model-id>
_DEFAULT_MODEL = "qwen/qwen3.8-27b"


# ── LLM client ───────────────────────────────────────────────────────────────

def _get_client() -> Groq:
    """
    Return a Groq client.
    Get a FREE API key at https://console.groq.com  (no credit card required).
    Set it with:  export GROQ_API_KEY="gsk_..."
    """
    api_key = (
        os.environ.get("GROQ_API_KEY")
        or os.environ.get("SHAPE_API_KEY")
    )
    if not api_key:
        raise EnvironmentError(
            "No Groq API key found.\n"
            "  1. Go to https://console.groq.com and sign up (free).\n"
            "  2. Create an API key (starts with gsk_...).\n"
            "  3. Run:  export GROQ_API_KEY=\"gsk_...\"\n"
            "  4. Then restart the app."
        )
    return Groq(api_key=api_key)


# ── System prompts per agent role ─────────────────────────────────────────────

_ROLE_PROMPTS: dict[str, str] = {
    "instructor": textwrap.dedent("""\
        You are the Instructor agent of SHAPE Agent 16, an interactive learning companion
        for programming and AI concepts.  Adapt your language strictly to the learner's
        current level: {level}.  Use the teaching strategy: {strategy}.
        If curriculum context is provided below, prioritise it over your general knowledge.
        Never answer questions outside the programming / AI domain.
        Always end your response with exactly ONE follow-up question to check understanding.
    """),

    "debugger": textwrap.dedent("""\
        You are the Debugger agent of SHAPE Agent 16.  The learner submitted code that
        produced an error.  Explain what went wrong in plain language appropriate for a
        {level} learner.  Point to the exact line if possible, and suggest ONE minimal fix.
        Do NOT rewrite the entire solution — guide, do not give.
    """),

    "evaluator": textwrap.dedent("""\
        You are the Evaluator agent of SHAPE Agent 16.  Assess the learner's answer or
        code solution and provide structured feedback:
          ✅ What was correct
          ⚠️  What needs improvement
          💡 One targeted hint (do not reveal the full answer)
        Keep feedback concise and encouraging for a {level} learner.
    """),

    "strategist": textwrap.dedent("""\
        You are the Learning Strategist agent of SHAPE Agent 16.  Based on the learner's
        history and current performance, recommend whether to:
          - advance the learner's level
          - revisit a prerequisite topic
          - continue on the current path
        Provide a one-sentence rationale.
    """),
}


# ── Context dataclass ─────────────────────────────────────────────────────────

@dataclass
class TurnContext:
    session_id:      str
    learner_id:      str
    turn_number:     int
    user_input:      str
    learner_level:   str        = "beginner"
    strategy:        Strategy   = Strategy.EXPLAIN
    curriculum_ctx:  str        = ""
    code_in_input:   str        = ""
    tool_output:     str        = ""
    cot_scratchpad:  str        = ""
    final_reply:     str        = ""
    reward:          float      = 0.0
    hints_given:     int        = 0
    answer_correct:  bool       = False
    violation:       bool       = False
    active_role:     str        = "instructor"
    messages:        list       = field(default_factory=list)


# ── Helper: extract Python fenced code blocks ─────────────────────────────────

import re as _re

_CODE_FENCE_RE = _re.compile(r"```(?:python)?\s*(.*?)```", _re.DOTALL | _re.IGNORECASE)

def _extract_code(text: str) -> str:
    """Return the first fenced Python block in text, or empty string."""
    m = _CODE_FENCE_RE.search(text)
    return m.group(1).strip() if m else ""


def _mock_reply(ctx: "TurnContext") -> str:
    """
    Return a canned but realistic reply when SHAPE_MOCK_MODE=1.
    Used when no API key is available so teammates can run all demos.
    """
    role = ctx.active_role
    level = ctx.learner_level
    strategy = ctx.strategy.value

    if ctx.tool_output.startswith("[Code Error]"):
        return (
            f"[MOCK — Debugger | {level}]\n\n"
            "I can see an issue with your code. "
            "Check the line where the error occurred — look for a missing colon "
            "or incorrect indentation. Try fixing that one line first.\n\n"
            "What do you think the problem might be on that line?"
        )
    if role == "evaluator":
        return (
            f"[MOCK — Evaluator | {level}]\n\n"
            "✅ Your understanding of the concept is on the right track.\n"
            "⚠️  Make sure to be more specific about the syntax.\n"
            "💡 Hint: re-read the definition and focus on the keyword used.\n\n"
            "Can you try rephrasing that in your own words?"
        )
    if ctx.tool_output.startswith("[Code Output]"):
        return (
            f"[MOCK — Instructor | {level} | {strategy}]\n\n"
            f"Your code ran successfully! Here's what it produced:\n\n"
            f"{ctx.tool_output}\n\n"
            "Great work. Now try modifying it — what happens if you change the range?\n\n"
            "What do you predict the output will be if you use `range(1, 10, 3)`?"
        )
    return (
        f"[MOCK — Instructor | {level} | {strategy}]\n\n"
        "Great question! In Python, this concept is fundamental to writing clean code. "
        "The key idea is to break the problem into smaller steps and handle each one carefully.\n\n"
        "Here's a simple example:\n"
        "```python\n# Example code here\nfor i in range(5):\n    print(i)\n```\n\n"
        "This is running in **MOCK MODE** (no API key). "
        "Ask Michael Rivas to push `config/groq_key.txt` to the repo for live AI responses.\n\n"
        "What part of this would you like to explore further?"
    )


# ── 8-Step Orchestrator ───────────────────────────────────────────────────────

def run_turn(
    learner_id:  str,
    user_input:  str,
    session_id:  str | None = None,
    turn_number: int        = 1,
) -> str:
    """
    Execute one full 8-step reasoning cycle and return the agent's reply string.

    Parameters
    ----------
    learner_id  : stable user identifier
    user_input  : raw text from the learner
    session_id  : pass an existing ID to continue a session; None creates a new one
    turn_number : monotonically increasing turn counter within the session
    """
    ctx = TurnContext(
        session_id  = session_id or str(uuid.uuid4()),
        learner_id  = learner_id,
        turn_number = turn_number,
        user_input  = user_input,
    )

    # ── Step 1 │ RECEIVE ──────────────────────────────────────────────────────
    safety_result = validate_user_prompt(user_input)
    if not safety_result.safe:
        ctx.violation = True
        ctx.final_reply = (
            f"⚠️ {safety_result.reason}\n\n{agent_scope_reminder()}"
        )
        _finalise(ctx)
        return ctx.final_reply

    # ── Step 2 │ PROFILE ──────────────────────────────────────────────────────
    learner = db.get_learner(learner_id)
    if learner is None:
        db.upsert_learner(learner_id, learner_id)
        learner = db.get_learner(learner_id)
    ctx.learner_level = learner["level"]  # type: ignore[index]

    # Ensure session exists
    db.create_session(ctx.session_id, learner_id)
    db.log_interaction(ctx.session_id, turn_number, "user", user_input)

    # ── Step 3 │ RETRIEVE ─────────────────────────────────────────────────────
    retrieval = retrieve_curriculum(user_input, learner_level=ctx.learner_level)
    if retrieval.success and retrieval.output and "No matching" not in retrieval.output:
        ctx.curriculum_ctx = retrieval.output

    # ── Step 4 │ REASON (CoT + strategy selection) ───────────────────────────
    ctx.strategy = select_strategy(ctx.learner_level)

    ctx.cot_scratchpad = (
        f"Learner level    : {ctx.learner_level}\n"
        f"Strategy chosen  : {ctx.strategy.value}\n"
        f"Curriculum hit   : {'YES' if ctx.curriculum_ctx else 'NO'}\n"
        f"Code in input    : {'YES' if _extract_code(user_input) else 'NO'}\n"
    )

    # Determine active sub-agent role
    ctx.code_in_input = _extract_code(user_input)
    if ctx.code_in_input:
        ctx.active_role = "debugger"
    elif any(kw in user_input.lower() for kw in ("check my answer", "is this correct", "grade")):
        ctx.active_role = "evaluator"
    else:
        ctx.active_role = "instructor"

    # ── Step 5 │ ACT (run code if present) ───────────────────────────────────
    if ctx.code_in_input:
        tool_result = run_python_exercise(ctx.code_in_input)
        if tool_result.success:
            ctx.tool_output = f"[Code Output]\n{tool_result.output}"
        else:
            ctx.tool_output = f"[Code Error]\n{tool_result.error}"
            ctx.active_role = "debugger"  # force debugger when code fails

    # ── Step 6 │ RESPOND (LLM call) ──────────────────────────────────────────
    system_prompt = _ROLE_PROMPTS[ctx.active_role].format(
        level    = ctx.learner_level,
        strategy = ctx.strategy.value,
    )

    user_block_parts = [user_input]
    if ctx.curriculum_ctx:
        user_block_parts.insert(0, f"[Curriculum Context]\n{ctx.curriculum_ctx}\n")
    if ctx.tool_output:
        user_block_parts.append(f"\n{ctx.tool_output}")

    ctx.messages = [
        {"role": "system",    "content": system_prompt},
        {"role": "user",      "content": "\n\n".join(user_block_parts)},
    ]

    # ── Mock mode — no API key required ──────────────────────────────────────
    if os.environ.get("SHAPE_MOCK_MODE") == "1":
        ctx.final_reply = _mock_reply(ctx)
    else:
        try:
            client = _get_client()
            response = client.chat.completions.create(
                model       = os.environ.get("SHAPE_MODEL", _DEFAULT_MODEL),
                messages    = ctx.messages,
                max_tokens  = 600,
                temperature = 0.7,
            )
            ctx.final_reply = response.choices[0].message.content.strip()
        except APIError as exc:
            ctx.final_reply = fallback_response(f"Groq API error: {exc}")
        except EnvironmentError as exc:
            ctx.final_reply = fallback_response(str(exc))

    # ── Step 7 │ EVALUATE (reward computation) ───────────────────────────────
    # Heuristic: if the reply contains a ✅ we treat the attempt as correct.
    ctx.answer_correct = "✅" in ctx.final_reply
    ctx.hints_given    = ctx.final_reply.lower().count("hint")
    ctx.reward         = compute_reward(ctx.answer_correct, ctx.hints_given, ctx.violation)
    record_outcome(ctx.strategy, ctx.reward)

    # ── Step 8 │ ADAPT (profile update) ──────────────────────────────────────
    _adapt_learner(ctx)
    _finalise(ctx)
    return ctx.final_reply


# ── Private helpers ───────────────────────────────────────────────────────────

def _adapt_learner(ctx: TurnContext) -> None:
    """
    Decide whether to promote the learner to the next level.
    Simple heuristic: 3 consecutive correct-first-attempt rewards → promote.
    """
    recent_rewards = db.get_recent_agent_rewards(ctx.session_id, limit=5)

    # Update topics seen
    if ctx.curriculum_ctx:
        m = _re.search(r"\[Lesson: (.+?) \|", ctx.curriculum_ctx)
        if m:
            db.add_topic_seen(ctx.learner_id, m.group(1))

    # Promote on 3+ consecutive perfect-score turns
    if len(recent_rewards) >= 3 and all(r == 1.0 for r in recent_rewards[-3:]):
        level_map = {"beginner": "intermediate", "intermediate": "advanced"}
        current = db.get_learner(ctx.learner_id)["level"]  # type: ignore[index]
        if current in level_map:
            db.update_learner_level(ctx.learner_id, level_map[current])


def _finalise(ctx: TurnContext) -> None:
    """Persist the agent turn to the DB."""
    db.log_interaction(
        ctx.session_id,
        ctx.turn_number,
        "agent",
        ctx.final_reply,
        strategy = ctx.strategy.value if not ctx.violation else None,
        reward   = ctx.reward,
    )
