"""SHAPE Agent 16 — Gradio interface (Gradio 6 compatible).

Uses gr.Blocks() with no constructor theme/CSS args (Gradio 6 moved
theme to launch(): the notebook's last cell calls
demo.launch(share=False, theme=gr.themes.Soft())).
All buttons have working callbacks. The UI is built by build_demo();
the notebook's last cell launches it.
"""
import csv
import io
import json
import os
import random

import gradio as gr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .agents import (agent_reply, generate_report_draft, handle_device_message,
                     llm_mode, orchestrate, team_evidence_summary)
from .policy import (STRATEGIES, new_q_table, q_table_rows, reward_for,
                     select_strategy, update_q)
from .store import (ASSESSMENT, CATEGORIES, CONTRIBUTION_FIELDS, LESSONS,
                    MEMBER_NAMES, PATHWAY, RESOURCES, get_attempts,
                    get_contributions, get_lesson, init_db, load_policy,
                    progress_summary, record_attempt, save_contribution,
                    save_policy)
from .tools import retrieve_lesson_tool, run_code_tool

DB = "shape.db"


def _lesson_choices():
    return [(f"{l['id']} — {l['title']}", l["id"]) for l in LESSONS]


def _progress_figure(learner_id):
    attempts = get_attempts(DB, learner_id)
    fig, ax = plt.subplots(figsize=(6, 3))
    if not attempts:
        ax.text(0.5, 0.5, "No attempts yet — submit code in the Learning Lab.",
                ha="center", va="center")
        ax.set_title("Learner progress")
    else:
        xs = list(range(1, len(attempts) + 1))
        ax.plot(xs, [a["passed"] for a in attempts], marker="o", label="Correct (1=yes, 0=no)")
        ax.plot(xs, [a["hints_used"] for a in attempts], marker="s", label="Hints used")
        ax.set_xlabel("Attempt number")
        ax.set_ylabel("Count")
        ax.set_title(f"Progress for {learner_id} ({len(attempts)} attempts)")
        ax.set_ylim(-0.2, max(2, max(a["hints_used"] for a in attempts) + 1))
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def _synthetic_figure():
    """SYNTHETIC DEMO ONLY — never real student results."""
    fig, ax = plt.subplots(figsize=(6, 3))
    groups = ["Fixed instruction", "Adaptive Agent 16"]
    pre = [52, 53]
    post = [61, 74]
    x = range(len(groups))
    ax.bar([i - 0.2 for i in x], pre, 0.4, label="Pre-test (synthetic)")
    ax.bar([i + 0.2 for i in x], post, 0.4, label="Post-test (synthetic)")
    ax.set_xticks(list(x)); ax.set_xticklabels(groups)
    ax.set_ylabel("Mean score (%)")
    ax.set_title("SYNTHETIC DEMO ONLY — fixed vs adaptive (made-up data)")
    ax.set_ylim(0, 100)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def _attempts_df(learner_id):
    rows = get_attempts(DB, learner_id)
    if not rows:
        return pd.DataFrame(columns=["lesson", "passed", "hints", "reward", "strategy"])
    return pd.DataFrame([{"lesson": r["lesson_id"], "passed": r["passed"],
                          "hints": r["hints_used"], "reward": r["reward"],
                          "strategy": r["strategy"]} for r in rows])


def _contrib_df():
    rows = get_contributions(DB)
    if not rows:
        return pd.DataFrame(columns=CONTRIBUTION_FIELDS)
    return pd.DataFrame([{k: r.get(k, "") for k in CONTRIBUTION_FIELDS} for r in rows])


def build_demo():
    init_db(DB)
    q_table = load_policy(DB, new_q_table())
    policy_before = dict(q_table)
    mode_text, _ = llm_mode()

    with gr.Blocks(title="SHAPE Agent 16") as demo:
        gr.Markdown("# SHAPE Agent 16 — Learning through interaction. Improving through feedback.")
        gr.Markdown(f"**Course:** ITAI2376, Houston Community College, Group ITAI2376_14562 · "
                    f"**Final deadline:** Dec 7, 2026 · **Proposal:** Nov 13, 2026\n\n"
                    f"**Mode:** {mode_text}  \n"
                    "If no API key is set, the app uses local fallback templates and says so — "
                    "the fallback is never presented as an LLM.")
        hint_state = gr.State(0)
        pre_state = gr.State(None)

        with gr.Tabs():
            # ---- A. Learning Lab ------------------------------------------------
            with gr.Tab("A. Learning Lab"):
                learner_id = gr.Textbox(label="Learner ID (anonymised — use a code like learner-01, no real names)",
                                        value="learner-01")
                lesson_dd = gr.Dropdown(choices=_lesson_choices(), value="L1", label="Lesson")
                concept_box = gr.Textbox(label="Concept", lines=4)
                example_box = gr.Code(label="Worked example", language="python", lines=5)
                exercise_box = gr.Textbox(label="Exercise", lines=3)
                code_box = gr.Code(label="Your code", language="python", lines=6)
                with gr.Row():
                    submit_btn = gr.Button("Submit code", variant="primary")
                    hint_btn = gr.Button("Get a hint")
                feedback_box = gr.Textbox(label="Feedback", lines=5)
                hint_box = gr.Textbox(label="Hint", lines=3)
                check_q = gr.Textbox(label="Concept check", lines=2)
                check_a = gr.Textbox(label="Your concept-check answer")
                with gr.Row():
                    check_btn = gr.Button("Check concept answer")
                check_out = gr.Textbox(label="Concept-check result", lines=2)
                gr.Markdown("### Pre / post assessment (same 5 questions — change is measurable)")
                assess_inputs = []
                for i, item in enumerate(ASSESSMENT):
                    assess_inputs.append(gr.Radio(choices=item["options"], label=f"Q{i+1}. {item['q']}"))
                with gr.Row():
                    pre_btn = gr.Button("Score pre-test")
                    post_btn = gr.Button("Score post-test")
                assess_out = gr.Textbox(label="Assessment result", lines=3)

                def on_lesson(lesson_id):
                    lesson = get_lesson(lesson_id)
                    return (lesson["concept"], lesson["example"], lesson["exercise"],
                            lesson["concept_check_q"], "", "", 0)

                lesson_dd.change(on_lesson, inputs=[lesson_dd],
                                 outputs=[concept_box, example_box, exercise_box, check_q,
                                          feedback_box, hint_box, hint_state])

                def on_submit(learner, lesson_id, code, hints):
                    lesson = get_lesson(lesson_id)
                    result = orchestrate(learner, "check my code", lesson_id=lesson_id,
                                         code=code, hints_used=int(hints or 0), q_table=q_table)
                    reward = reward_for(result["tool_result"]["passed"], int(hints or 0)) if result.get("tool_result") else 0.0
                    record_attempt(DB, learner, lesson_id, code,
                                   result["tool_result"]["passed"] if result.get("tool_result") else False,
                                   int(hints or 0), reward, result["agent"])
                    save_policy(DB, q_table)
                    passed = result["tool_result"]["passed"] if result.get("tool_result") else False
                    text = (f"{'Correct!' if passed else 'Not yet correct.'} "
                            f"Output: {result['tool_result']['stdout'].strip()!r} "
                            f"Expected: {result['tool_result']['expected']!r} "
                            f"Reward: {reward:+.0f}. {result['response']}")
                    return text, 0

                submit_btn.click(on_submit, inputs=[learner_id, lesson_dd, code_box, hint_state],
                                 outputs=[feedback_box, hint_state])

                def on_hint(lesson_id, hints):
                    lesson = get_lesson(lesson_id)
                    n = int(hints or 0)
                    if n >= len(lesson["hints"]):
                        return "No more hints for this exercise — try the worked example again.", n
                    return f"Hint {n+1} of {len(lesson['hints'])}: {lesson['hints'][n]}", n + 1

                hint_btn.click(on_hint, inputs=[lesson_dd, hint_state],
                               outputs=[hint_box, hint_state])

                def on_check(lesson_id, answer):
                    lesson = get_lesson(lesson_id)
                    ok = lesson["concept_check_a"].lower() in (answer or "").lower() or (answer or "").lower() in lesson["concept_check_a"].lower()
                    if ok:
                        return "Concept check: correct."
                    return f"Concept check: not quite. Expected idea: {lesson['concept_check_a']}. Reward -1 if this were scored."

                check_btn.click(on_check, inputs=[lesson_dd, check_a], outputs=[check_out])

                def on_pre(*answers):
                    score = sum(1 for a, item in zip(answers, ASSESSMENT) if a == item["answer"])
                    return (f"Pre-test: {score}/5 correct. Keep this score — "
                            "take the post-test after the lessons."), score

                def on_post(*args):
                    *answers, pre = args
                    score = sum(1 for a, item in zip(answers, ASSESSMENT) if a == item["answer"])
                    if pre is None:
                        return (f"Post-test: {score}/5 correct. No pre-test score was recorded "
                                "in this session, so improvement cannot be measured yet."), None
                    change = score - int(pre)
                    return (f"Post-test: {score}/5 correct. Pre-test was {pre}/5. "
                            f"Change: {change:+d} question(s). This measures test change, "
                            "not proof of learning on its own."), pre

                pre_btn.click(on_pre, inputs=assess_inputs, outputs=[assess_out, pre_state])
                post_btn.click(on_post, inputs=assess_inputs + [pre_state],
                               outputs=[assess_out, pre_state])

            # ---- B. Agent Workspace ----------------------------------------------
            with gr.Tab("B. Agent Workspace"):
                gr.Markdown("See which agent is responding, what tool it used, and whether the reply came from the LLM or the local fallback.")
                ws_learner = gr.Textbox(label="Learner ID", value="learner-01")
                ws_lesson = gr.Dropdown(choices=_lesson_choices(), value="L1", label="Lesson context")
                ws_msg = gr.Textbox(label="Ask SHAPE anything (try: 'explain loops', 'debug my code', 'what should I do next?')", lines=3)
                ws_code = gr.Code(label="Optional code to check (leave blank for a question)", language="python", lines=4)
                ask_btn = gr.Button("Ask the orchestrator", variant="primary")
                ws_agent = gr.Textbox(label="Agent role responding")
                ws_decision = gr.Textbox(label="Instructional decision", lines=2)
                ws_mode = gr.Textbox(label="LLM or local fallback?")
                ws_tools = gr.Textbox(label="Tool activity", lines=3)
                ws_log = gr.Textbox(label="Reasoning-cycle log (8 steps)", lines=8)
                ws_resp = gr.Textbox(label="Response", lines=5)

                def on_ask(learner, lesson_id, message, code):
                    code_arg = code if code and code.strip() else None
                    out = orchestrate(learner, message, lesson_id=lesson_id, code=code_arg, q_table=q_table)
                    tools = "\n".join(f"{t['tool']}: {t['input']}" for t in out["tool_calls"]) or "No tool used."
                    return (out["agent"], out["decision"], out["mode"], tools,
                            "\n".join(out["log"]), out["response"])

                ask_btn.click(on_ask, inputs=[ws_learner, ws_lesson, ws_msg, ws_code],
                              outputs=[ws_agent, ws_decision, ws_mode, ws_tools, ws_log, ws_resp])

            # ---- C. Learner Progress ----------------------------------------------
            with gr.Tab("C. Learner Progress"):
                prog_learner = gr.Textbox(label="Learner ID", value="learner-01")
                refresh_btn = gr.Button("Refresh progress")
                prog_summary = gr.Markdown()
                prog_df = gr.Dataframe(label="Attempts", interactive=False)
                prog_plot = gr.Plot(label="Progress chart")

                def on_refresh(learner):
                    s = progress_summary(DB, learner)
                    md = (f"**Attempts:** {s['attempts']} · **Correct:** {s['correct']} · "
                          f"**Accuracy:** {s['accuracy']}% · **Hints used:** {s['hints']} · "
                          f"**Lessons completed:** {s['lessons_done']} / {len(LESSONS)} · "
                          f"**Total reward:** {s['total_reward']}")
                    return md, _attempts_df(learner), _progress_figure(learner)

                refresh_btn.click(on_refresh, inputs=[prog_learner],
                                  outputs=[prog_summary, prog_df, prog_plot])

            # ---- D. Adaptive Learning ---------------------------------------------
            with gr.Tab("D. Adaptive Learning"):
                gr.Markdown("A reward increase is **not** proof of learning. Learning is measured "
                            "independently with the pre/post assessment in the Learning Lab.")
                adapt_refresh = gr.Button("Refresh policy")
                adapt_table = gr.Dataframe(label="Q-table: strategy vs Q-value (before -> now)",
                                           headers=["Strategy", "Q before", "Q now"], interactive=False)
                adapt_strategy = gr.Textbox(label="Strategy the policy would select next, and why", lines=3)
                adapt_plot = gr.Plot(label="Synthetic evaluation (demo data only)")

                def on_adapt():
                    rows = [[s, round(float(policy_before.get(s, 0.0)), 3),
                             round(float(q_table.get(s, 0.0)), 3)] for s in STRATEGIES]
                    choice, reason = select_strategy(q_table, rng=random.Random(0))
                    return (pd.DataFrame(rows, columns=["Strategy", "Q before", "Q now"]),
                            f"Selected: {choice}. {reason}", _synthetic_figure())

                adapt_refresh.click(on_adapt, inputs=[], outputs=[adapt_table, adapt_strategy, adapt_plot])

            # ---- E. Team Workspace --------------------------------------------------
            with gr.Tab("E. Team Workspace"):
                gr.Markdown("Every member records Design, Coding, Testing and Reflection work here. "
                            "Full names for Cherluk, Olu and Taki are editable fields — they are not invented here.")
                tw_member = gr.Dropdown(choices=MEMBER_NAMES, label="Member (first name as listed)")
                tw_full = gr.Textbox(label="Full name (editable — leave blank if not yet confirmed)")
                tw_date = gr.Textbox(label="Date (YYYY-MM-DD)", value="2026-11-06")
                tw_stream = gr.Textbox(label="Workstream", value="SHAPE Agent 16")
                tw_cat = gr.Dropdown(choices=CATEGORIES, label="Category")
                tw_task = gr.Textbox(label="Task completed")
                tw_contrib = gr.Textbox(label="Specific contribution", lines=3)
                tw_evidence = gr.Textbox(label="Evidence description", lines=2)
                tw_link = gr.Textbox(label="Evidence link or filename")
                tw_decisions = gr.Textbox(label="Technical decisions", lines=2)
                tw_challenges = gr.Textbox(label="Challenges encountered", lines=2)
                tw_outcome = gr.Textbox(label="Outcome", lines=2)
                tw_reflection = gr.Textbox(label="Individual reflection", lines=3)
                with gr.Row():
                    tw_save = gr.Button("Save contribution", variant="primary")
                    tw_refresh = gr.Button("Refresh list")
                tw_status = gr.Textbox(label="Status", lines=2)
                tw_df = gr.Dataframe(label="Contribution log", interactive=False)
                tw_file = gr.File(label="Import contributions CSV (columns: member, full_name, date, workstream, category, task, contribution, evidence, evidence_link, decisions, challenges, outcome, reflection)")
                tw_import = gr.Button("Import CSV")

                def on_save(member, full, date_, stream, cat, task, contrib, ev, link,
                            decisions, challenges, outcome, reflection):
                    if not member or not task.strip():
                        return "Member and task are required.", _contrib_df()
                    rec = {"member": member, "full_name": full, "date": date_, "workstream": stream,
                           "category": cat, "task": task, "contribution": contrib, "evidence": ev,
                           "evidence_link": link, "decisions": decisions, "challenges": challenges,
                           "outcome": outcome, "reflection": reflection}
                    save_contribution(DB, rec)
                    return f"Saved contribution for {member}: {task}", _contrib_df()

                tw_save.click(on_save, inputs=[tw_member, tw_full, tw_date, tw_stream, tw_cat, tw_task,
                                               tw_contrib, tw_evidence, tw_link, tw_decisions,
                                               tw_challenges, tw_outcome, tw_reflection],
                              outputs=[tw_status, tw_df])
                tw_refresh.click(lambda: _contrib_df(), inputs=[], outputs=[tw_df])

                def on_import(file):
                    if file is None:
                        return "Choose a CSV file first.", _contrib_df()
                    path = file.name if hasattr(file, "name") else str(file)
                    n = 0
                    with open(path, newline="", encoding="utf-8") as fh:
                        for row in csv.DictReader(fh):
                            rec = {k: (row.get(k, "") or "") for k in CONTRIBUTION_FIELDS}
                            if rec.get("member") and rec.get("task"):
                                save_contribution(DB, rec)
                                n += 1
                    return f"Imported {n} contribution record(s).", _contrib_df()

                tw_import.click(on_import, inputs=[tw_file], outputs=[tw_status, tw_df])

            # ---- F. Export Center ---------------------------------------------------
            with gr.Tab("F. Export Center"):
                gr.Markdown("Exports are generated from the actual records in shape.db. "
                            "Report drafts flag missing evidence and reflections — they never invent work.")
                with gr.Row():
                    exp_contrib = gr.Button("Export contributions CSV")
                    exp_eval = gr.Button("Export evaluation CSV")
                    exp_prog = gr.Button("Export progress CSV")
                exp_file = gr.File(label="Download the exported file")
                gen_btn = gr.Button("Generate 4 individual report drafts + team summary", variant="primary")
                gen_out = gr.Textbox(label="Generated drafts (also written as .md files)", lines=20)
                hw_msg = gr.Textbox(label="Hardware mock — test message (JSON)",
                                    value='{"device_id": "pi-zero-01", "event": "lesson_start", "lesson_id": "L1", "action": "next", "timestamp": "2026-11-06T09:00:00"}',
                                    lines=3)
                hw_btn = gr.Button("Test hardware message")
                hw_out = gr.Textbox(label="Hardware mock result", lines=3)

                def export_csv(kind):
                    import json as _json
                    if kind == "contributions":
                        rows = get_contributions(DB)
                        path = "SHAPE_contributions.csv"
                        fields = CONTRIBUTION_FIELDS
                    elif kind == "evaluation":
                        rows = get_attempts(DB)
                        path = "SHAPE_evaluation.csv"
                        fields = ["learner_id", "lesson_id", "passed", "hints_used", "reward", "strategy"]
                    else:
                        rows = get_attempts(DB)
                        path = "SHAPE_progress.csv"
                        fields = ["learner_id", "lesson_id", "passed", "hints_used", "reward", "strategy"]
                    with open(path, "w", newline="", encoding="utf-8") as fh:
                        w = csv.DictWriter(fh, fieldnames=fields)
                        w.writeheader()
                        for r in rows:
                            w.writerow({k: r.get(k, "") for k in fields})
                    return path

                exp_contrib.click(lambda: export_csv("contributions"), inputs=[], outputs=[exp_file])
                exp_eval.click(lambda: export_csv("evaluation"), inputs=[], outputs=[exp_file])
                exp_prog.click(lambda: export_csv("progress"), inputs=[], outputs=[exp_file])

                def on_generate():
                    rows = get_contributions(DB)
                    parts = []
                    for member in MEMBER_NAMES:
                        draft = generate_report_draft(member, rows)
                        fname = f"SHAPE_Report_Draft_{member.replace(' ', '_')}.md"
                        with open(fname, "w", encoding="utf-8") as fh:
                            fh.write(draft)
                        parts.append(draft)
                    summary = team_evidence_summary(rows)
                    with open("SHAPE_Team_Evidence_Summary.md", "w", encoding="utf-8") as fh:
                        fh.write(summary)
                    parts.append(summary)
                    return "\n\n---\n\n".join(parts)

                gen_btn.click(on_generate, inputs=[], outputs=[gen_out])

                def on_hw(msg):
                    try:
                        data = json.loads(msg)
                    except Exception as e:
                        return f"Invalid JSON: {e}"
                    return str(handle_device_message(data))

                hw_btn.click(on_hw, inputs=[hw_msg], outputs=[hw_out])

        # Pre-fill the Learning Lab with Lesson 1 on first load.
        demo.load(lambda: (LESSONS[0]["concept"], LESSONS[0]["example"], LESSONS[0]["exercise"],
                           LESSONS[0]["concept_check_q"]),
                  inputs=[], outputs=[concept_box, example_box, exercise_box, check_q])
    return demo
