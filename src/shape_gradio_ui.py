"""
shape_gradio_ui.py
------------------
Gradio web interface for SHAPE Agent 16 — Interactive Learning Companion.

Two tabs:
  1. Chat           – Learner interaction tab
  2. Lesson Builder – Instructor-only tab for live lesson authoring
                      (designed for non-coding teammates: Cherluk, Olu, Taki)

Run:
    python shape_gradio_ui.py
    # or:
    python shape_main.py --ui

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

import uuid

import gradio as gr  # pip install gradio

import shape_db_handler as db
from shape_agent_core import run_turn
from shape_safety import validate_lesson_content
from shape_rl_policy import policy_summary

db.init_db()

# ── Session state (per Gradio session) ───────────────────────────────────────

def _new_session_state() -> dict:
    return {
        "session_id":  str(uuid.uuid4()),
        "learner_id":  None,
        "turn_number": 0,
    }


# ── Chat tab callbacks ────────────────────────────────────────────────────────

def start_session(display_name: str, state: dict) -> tuple[str, dict]:
    """Register or load the learner and create a session."""
    if not display_name.strip():
        return "⚠️ Please enter your name to begin.", state
    learner_id = display_name.strip().lower().replace(" ", "_")
    db.upsert_learner(learner_id, display_name.strip())
    state["learner_id"]  = learner_id
    state["session_id"]  = str(uuid.uuid4())
    state["turn_number"] = 0
    learner = db.get_learner(learner_id)
    return (
        f"👋 Welcome back, **{display_name}**!  Current level: **{learner['level']}**.\n"
        "Ask me anything about programming or AI concepts — or paste some code to debug!",
        state,
    )


def _msg(user: str, bot: str) -> list:
    """Return one exchange as dicts (required by all current Gradio builds)."""
    return [
        {"role": "user",      "content": user},
        {"role": "assistant", "content": bot},
    ]


def chat_turn(user_message: str, history: list, state: dict) -> tuple[list, dict]:
    """Process one learner turn through the 8-step orchestrator."""
    if not state.get("learner_id"):
        return history + _msg(user_message, "⚠️ Please enter your name and click **Start Session** first."), state

    state["turn_number"] += 1
    reply = run_turn(
        learner_id  = state["learner_id"],
        user_input  = user_message,
        session_id  = state["session_id"],
        turn_number = state["turn_number"],
    )
    return history + _msg(user_message, reply), state


def get_learner_profile(state: dict) -> str:
    if not state.get("learner_id"):
        return "No active session."
    learner = db.get_learner(state["learner_id"])
    if not learner:
        return "Learner not found."
    import json
    topics = json.loads(learner["topics_seen"])
    lines = [
        f"**Name:** {learner['display_name']}",
        f"**Level:** {learner['level']}",
        f"**Topics seen:** {', '.join(topics) if topics else 'none yet'}",
    ]

    assessments = db.get_assessments(state["learner_id"])
    if assessments:
        lines.append("\n**Assessments:**")
        for a in assessments:
            lines.append(f"  - {a['phase'].upper()}: {a['score']:.0%} on {a['taken_at'][:10]}")
    return "\n".join(lines)


# ── Lesson Builder tab callbacks ──────────────────────────────────────────────

def submit_lesson(topic: str, level: str, title: str,
                  content: str, keywords_raw: str, author: str) -> str:
    """Validate and save a new instructor-authored lesson to the curriculum DB."""
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    validation = validate_lesson_content(title, content, keywords)
    if not validation.safe:
        return f"⚠️ Validation failed: {validation.reason}"
    lesson_id = db.add_lesson(
        topic    = topic.strip(),
        level    = level,
        title    = title.strip(),
        content  = content.strip(),
        keywords = keywords,
        author   = author.strip() or "instructor",
    )
    return (
        f"✅ Lesson saved successfully (ID: {lesson_id}).\n"
        "The agent will include this content in responses immediately."
    )


def show_policy() -> str:
    return policy_summary()


# ── Build Gradio app ──────────────────────────────────────────────────────────

def build_app() -> gr.Blocks:
    with gr.Blocks(title="SHAPE Agent 16 — Interactive Learning Companion") as app:
        gr.Markdown("# 🎓 SHAPE Agent 16 — Interactive Learning Companion\n"
                    "*ITAI2376_14562 | Michael Rivas · Cherluk · Olu · Taki*")

        state = gr.State(_new_session_state())

        # ── Tab 1: Chat ───────────────────────────────────────────────────────
        with gr.Tab("💬 Chat"):
            with gr.Row():
                name_input = gr.Textbox(label="Your name", placeholder="e.g. Alex")
                start_btn  = gr.Button("Start Session", variant="primary")
            status_box = gr.Markdown("Enter your name and click **Start Session**.")
            chatbot    = gr.Chatbot(label="SHAPE Conversation", height=420)
            with gr.Row():
                msg_input = gr.Textbox(
                    label="Your message or code",
                    placeholder="Ask a question or paste Python code in ```python ... ``` fences",
                    lines=3,
                    scale=5,
                )
                send_btn = gr.Button("Send ➤", variant="primary", scale=1)
            profile_btn    = gr.Button("📊 Show My Profile")
            profile_output = gr.Markdown()

            start_btn.click(start_session,  [name_input, state], [status_box, state])
            send_btn.click(chat_turn,        [msg_input, chatbot, state], [chatbot, state])
            msg_input.submit(chat_turn,      [msg_input, chatbot, state], [chatbot, state])
            profile_btn.click(get_learner_profile, [state], [profile_output])

        # ── Tab 2: Lesson Builder ────────────────────────────────────────────
        with gr.Tab("📝 Lesson Builder (Instructors)"):
            gr.Markdown("### Add a new lesson to the live curriculum\n"
                        "No coding required — fill in the form and click **Save Lesson**.")
            with gr.Row():
                lb_topic   = gr.Textbox(label="Topic",  placeholder="e.g. Python Loops")
                lb_level   = gr.Dropdown(["beginner","intermediate","advanced"],
                                         label="Level", value="beginner")
            lb_title   = gr.Textbox(label="Lesson Title", placeholder="e.g. Understanding for loops")
            lb_content = gr.Textbox(label="Lesson Content", lines=8,
                                    placeholder="Write the lesson explanation here...")
            lb_keywords = gr.Textbox(label="Keywords (comma-separated)",
                                     placeholder="loops, iteration, for, range")
            lb_author   = gr.Textbox(label="Author name", placeholder="Cherluk")
            lb_save_btn = gr.Button("💾 Save Lesson", variant="primary")
            lb_status   = gr.Markdown()
            lb_save_btn.click(
                submit_lesson,
                [lb_topic, lb_level, lb_title, lb_content, lb_keywords, lb_author],
                [lb_status],
            )

        # ── Tab 3: Policy Monitor ────────────────────────────────────────────
        with gr.Tab("📈 RL Policy Monitor"):
            gr.Markdown("### Current Q-values for Teaching Strategies")
            policy_btn    = gr.Button("Refresh")
            policy_output = gr.Textbox(label="Policy Table", lines=10)
            policy_btn.click(show_policy, [], [policy_output])

    return app


if __name__ == "__main__":
    app = build_app()
    app.launch(share=False, server_name="0.0.0.0", server_port=7860)
