"""SHAPE Agent 16 — LLM client, four agent roles, orchestrator, reports, hardware mock.

One LLM, four roles. Each role is a prompt + a tool-routing decision, not
a separate LLM service. If no API key is available, every role falls back
to local template logic and the UI says so — the fallback is NEVER
presented as an LLM.
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime

from .policy import reward_for, select_strategy, update_q
from .store import (CONTRIBUTION_FIELDS, LESSONS, MEMBER_NAMES, get_lesson)
from .tools import retrieve_lesson_tool, run_code_tool

LLM_MODEL = "gpt-4o-mini"
LLM_TIMEOUT = 20


def get_api_key():
    """API key from Colab secrets first, then the environment. Never from
    notebook source code, and never printed or logged."""
    try:
        from google.colab import userdata  # type: ignore
        key = userdata.get("OPENAI_API_KEY")
        if key:
            return key, "Colab secret OPENAI_API_KEY"
    except Exception:
        pass
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        return key, "environment variable OPENAI_API_KEY"
    return "", ""


def llm_mode():
    key, source = get_api_key()
    if key:
        return f"LLM active (OpenAI {LLM_MODEL}, key from {source})", True
    return "Local fallback — no API key found. Responses are local templates, NOT an LLM.", False


def call_llm(system_prompt, user_prompt, api_key=None):
    """Plain urllib call to OpenAI chat completions. Any failure -> None
    (caller must use the local fallback). Returns the reply text or None."""
    key = api_key or get_api_key()[0]
    if not key:
        return None
    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": user_prompt}],
        "temperature": 0.3, "max_tokens": 400,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


# --- Agent roles (prompts; one LLM serves all four) -------------------------
ROLE_SYSTEM = {
    "Instructor": "You are SHAPE's Instructor Agent. Explain simply, in short steps, with one small example. Never do the exercise for the learner.",
    "Debugger": "You are SHAPE's Debugger Agent. Explain why an error happened in plain language, then give one small hint at a time. Never just give the corrected code.",
    "Evaluator": "You are SHAPE's Evaluator Agent. Check work against the expected output, state clearly pass or fail, and say exactly what differed.",
    "Learning Strategist": "You are SHAPE's Learning Strategist Agent. Recommend the next step (review, practice, or challenge) and give one reason based on the learner's recent results.",
}

FALLBACK = {
    "Instructor": "Here is the idea in small steps: {detail} Try the worked example first, then the exercise.",
    "Debugger": "The error was: {detail} Read the line it names, check spelling and indentation, and try again — one fix at a time.",
    "Evaluator": "{detail}",
    "Learning Strategist": "Next step: {detail} This is based on your recent attempts, not a guess.",
}


def agent_reply(role, detail, context=""):
    """Ask the LLM for this role; on any failure use the local template.
    Returns (text, mode) where mode is 'LLM' or 'Local fallback'."""
    mode_text, has_key = llm_mode()
    if has_key:
        text = call_llm(ROLE_SYSTEM[role], f"Context: {context}\nDetail: {detail}")
        if text:
            return text, "LLM"
    return FALLBACK[role].format(detail=detail), "Local fallback"


def route_intent(text):
    """Orchestrator routing by intent (keyword rules, documented)."""
    t = (text or "").lower()
    if any(w in t for w in ("error", "debug", "bug", "traceback", "wrong", "fail")):
        return "Debugger"
    if any(w in t for w in ("check", "evaluate", "grade", "correct?", "did i", "is this right")):
        return "Evaluator"
    if any(w in t for w in ("next", "plan", "strategy", "what should i", "review", "challenge")):
        return "Learning Strategist"
    return "Instructor"


def orchestrate(learner_id, message, lesson_id="L1", code=None, hints_used=0,
                q_table=None, rng=None):
    """The 8-step reasoning cycle, in code:
    1 receive/validate, 2 retrieve context, 3 plan, 4 select agent+tool,
    5 execute, 6 evaluate, 7 update memory/policy, 8 explain.
    Returns a dict the UI displays in the Agent Workspace tab."""
    log = []
    # 1. Receive and validate.
    if not isinstance(message, str) or not message.strip():
        return {"agent": "Instructor", "decision": "Input was empty.",
                "tool_calls": [], "response": "Please type a question, or submit some code.",
                "mode": "Local fallback", "log": ["1. Input empty — asked learner to try again."]}
    log.append("1. Received and validated learner input.")
    # 2. Retrieve context.
    lesson = get_lesson(lesson_id)
    log.append(f"2. Retrieved context: lesson {lesson['id']} ({lesson['title']}), learner {learner_id}.")
    # 3. Plan.
    role = route_intent(message)
    log.append(f"3. Planned: route to {role} Agent (intent from learner's words).")
    # 4. Select agent + tool.
    tool_calls = []
    tool_result = None
    if code is not None:
        tool_calls.append({"tool": "run_code_tool", "input": code[:80]})
        tool_result = run_code_tool(code, lesson["expected_output"])
        log.append(f"4. Selected tool run_code_tool for submitted code (passed={tool_result['passed']}).")
    elif any(w in message.lower() for w in ("lesson", "learn", "what is", "resource", "topic")):
        tool_calls.append({"tool": "retrieve_lesson_tool", "input": message})
        tool_result = retrieve_lesson_tool(message)
        log.append(f"4. Selected tool retrieve_lesson_tool for a topic question (found={tool_result['found']}).")
    else:
        log.append("4. No tool needed for this message.")
    # 5. Execute + 6. Evaluate.
    if tool_result is not None and code is not None:
        detail = (f"Your code {'passed' if tool_result['passed'] else 'did not pass'}. "
                  f"Output: {tool_result['stdout'].strip()!r}. "
                  f"Expected: {tool_result['expected']!r}. {tool_result.get('hint', '')}")
        if tool_result.get("error"):
            role = "Debugger"
            detail = tool_result["error"] + " " + tool_result.get("hint", "")
    elif tool_result is not None:
        detail = tool_result["message"]
        if tool_result.get("lesson"):
            detail += f" Lesson: {tool_result['lesson']['title']} — {tool_result['lesson']['concept']}"
    else:
        detail = lesson["concept"]
    log.append("5. Executed the action.")
    log.append("6. Evaluated the result.")
    # 7. Update memory/policy (only when a code result exists and a policy was given).
    policy_note = "No policy update for this message."
    if q_table is not None and code is not None and tool_result is not None:
        reward = reward_for(tool_result["passed"], hints_used)
        strategy, reason = select_strategy(q_table, rng=rng)
        before = q_table.get(strategy, 0.0)
        update_q(q_table, strategy, reward)
        policy_note = (f"Reward {reward:+.0f} for this attempt. Strategy '{strategy}' "
                       f"Q {before:.2f} -> {q_table[strategy]:.2f}. {reason}")
        log.append(f"7. Updated policy: {policy_note}")
    else:
        log.append("7. No policy update (no code result in this message).")
    # 8. Explain.
    response, mode = agent_reply(role, detail, context=f"Lesson {lesson['id']}: {lesson['title']}")
    log.append(f"8. Explained the outcome to the learner (via {role} Agent, {mode}).")
    return {"agent": role, "decision": f"Routed to {role} Agent. {policy_note}",
            "tool_calls": tool_calls, "response": response,
            "mode": mode, "log": log, "tool_result": tool_result}


# --- Individual report drafts (from actual records only) --------------------
def generate_report_draft(member, contributions):
    """Draft a member's individual report from THEIR contribution records.
    Never fabricates. Flags missing evidence and unanswered reflections."""
    mine = [c for c in contributions if c.get("member") == member]
    lines = [f"# SHAPE Agent 16 — Individual Report Draft: {member}",
             "",
             "DRAFT — generated from contribution records in shape.db. "
             "The member must review and correct this draft before submission. "
             "Nothing in this draft was invented.",
             "",
             f"Contributions recorded: {len(mine)}",
             ""]
    if not mine:
        lines += ["## Missing evidence",
                  "",
                  f"No contribution records were found for {member}. "
                  "Add records in the Team Workspace tab before this report can be completed.",
                  ""]
        return "\n".join(lines)
    by_cat = {}
    for c in mine:
        by_cat.setdefault(c.get("category", "Uncategorised"), []).append(c)
    lines.append("## Contributions by category")
    lines.append("")
    for cat in ["Design", "Coding", "Testing", "Reflection"]:
        items = by_cat.get(cat, [])
        lines.append(f"- {cat}: {len(items)} record(s)")
    lines.append("")
    for c in mine:
        lines.append(f"### {c.get('date', '')} — {c.get('task', '')} ({c.get('category', '')})")
        lines.append("")
        lines.append(f"- Workstream: {c.get('workstream', '')}")
        lines.append(f"- Contribution: {c.get('contribution', '')}")
        lines.append(f"- Evidence: {c.get('evidence', '')} {c.get('evidence_link', '')}")
        lines.append(f"- Technical decisions: {c.get('decisions', '')}")
        lines.append(f"- Challenges: {c.get('challenges', '')}")
        lines.append(f"- Outcome: {c.get('outcome', '')}")
        lines.append(f"- Reflection: {c.get('reflection', '')}")
        lines.append("")
    missing_ev = [c for c in mine if not (c.get("evidence") or "").strip()]
    missing_refl = [c for c in mine if not (c.get("reflection") or "").strip()]
    lines.append("## Missing evidence / unanswered sections")
    lines.append("")
    lines.append(f"- Records with no evidence description: {len(missing_ev)}")
    lines.append(f"- Records with no reflection: {len(missing_refl)}")
    if missing_ev:
        lines.append("- Add an evidence description / link for: " +
                     "; ".join(c.get("task", "?") for c in missing_ev))
    if missing_refl:
        lines.append("- Add a reflection for: " +
                     "; ".join(c.get("task", "?") for c in missing_refl))
    lines.append("")
    lines.append("## Shared team work vs individual work")
    lines.append("")
    lines.append("This draft lists only this member's recorded contributions. "
                 "Shared accomplishments (the Colab app, the lesson set, the "
                 "evaluation plan) belong to the whole team and are described "
                 "in the team report, not claimed here as individual work.")
    return "\n".join(lines)


def team_evidence_summary(contributions):
    lines = ["# SHAPE Agent 16 — Team Evidence Summary", "",
             f"Total contribution records: {len(contributions)}", ""]
    for member in MEMBER_NAMES:
        mine = [c for c in contributions if c.get("member") == member]
        cats = {}
        for c in mine:
            cats[c.get("category", "?")] = cats.get(c.get("category", "?"), 0) + 1
        lines.append(f"- {member}: {len(mine)} record(s) — " +
                     (", ".join(f"{k}: {v}" for k, v in sorted(cats.items())) or "no records"))
    lines.append("")
    lines.append("Missing evidence overall: " +
                 str(sum(1 for c in contributions if not (c.get("evidence") or "").strip())))
    return "\n".join(lines)


# --- Hardware mock ------------------------------------------------------------
def handle_device_message(msg):
    """Validate a handheld-device JSON message. Contract:
    {"device_id","event","lesson_id","action","timestamp"}.
    The host runs the LLM; devices only send small events. No hardware needed."""
    required = ["device_id", "event", "lesson_id", "action", "timestamp"]
    if not isinstance(msg, dict):
        return {"ok": False, "error": "Message must be a JSON object."}
    missing = [k for k in required if k not in msg or msg[k] in ("", None)]
    if missing:
        return {"ok": False, "error": f"Missing fields: {', '.join(missing)}."}
    return {"ok": True, "ack": f"Received '{msg['event']}' from {msg['device_id']} "
                               f"for lesson {msg['lesson_id']}: action={msg['action']}. "
                               "Host will respond with the next prompt (no LLM runs on the device).",
            "received_at": datetime.now().isoformat(timespec="seconds")}
