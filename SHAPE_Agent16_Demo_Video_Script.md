# SHAPE Agent 16 — Demo Video Script

**Target length:** 3–5 minutes. Total timed below: about 4 minutes 30 seconds.
**Format:** Screen recording of the Colab application, with narration. No face camera is required.
**Rule:** Show the real application doing real things. If a feature is in local fallback mode, say so on screen and in narration. Do not present synthetic data as real student results; the synthetic chart segment is labelled on screen.

## 0:00–0:30 — Introduction (30 s)

**On screen:** Title screen / Gradio app open on the Learning Lab tab.
**Narration:** "SHAPE is a Student-centered Handheld Architecture for Programming Education — Agent 16. Learning through interaction. Improving through feedback. I'm [name], from ITAI2376, Group 14562 at Houston Community College. In the next four minutes I'll show you a learner working through a Python lesson, the four agents behind the feedback, and how the system changes its teaching based on what the learner does."

## 0:30–1:15 — Learning Lab (45 s)

**On screen:** Select a Python fundamentals lesson (e.g. "Variables and types"). Show the concept explanation and the worked example. Click into the exercise, type a short answer, submit it.
**Narration:** "First, the Learning Lab. The learner picks a lesson — we start with Python fundamentals, before any AI-agent concepts. There's a short explanation, a worked example, and then an exercise. I'll submit an answer with a small mistake in it, so you can see what happens next."

## 1:15–2:00 — Agent Workspace and Debugger (45 s)

**On screen:** Switch to the Agent Workspace. Show the Debugger Agent role, the tool activity (code-runner tool: test result and error type), and the graduated hint. Point to the "LLM" or "Local fallback" label.
**Narration:** "This is the Agent Workspace, and this is the point of SHAPE: the process is visible. The Debugger Agent ran the code with the exercise-checking tool, found the error, and explained why it happened — it didn't just hand over the answer. It gives a graduated hint first. And here you can see whether this response came from the LLM or from the local fallback. If there's no API key, the fallback is used and it's labelled as not an LLM."

**Action:** Submit the corrected answer. Show the Evaluator Agent recording a correct attempt.

## 2:00–2:45 — Learner Progress (45 s)

**On screen:** Learner Progress tab. Show attempts, correctness, hints used, completed lessons, and the progress chart. Point to an area needing review.
**Narration:** "Every attempt is recorded — correctness, hints used, and completion. The progress view shows what the learner has finished, where they're struggling, and how their performance is changing over time. Learners are identified only by an anonymized ID."

## 2:45–3:30 — Adaptive Learning: before and after (45 s)

**On screen:** Adaptive Learning tab. Show the policy table before the learner's attempts, then after: the reward applied (for example, +7 for correct with one hint), the update `Q += 0.2 * (r - Q)`, and the next strategy selected, with its reason.
**Narration:** "Here's the reinforcement-learning idea. A correct answer with one hint earns plus seven. The policy updates with Q plus zero point two times reward minus Q, and you can see the values before and after — the strategy that helped gets stronger. The next strategy is selected from those values, and the system tells you why. A higher reward is a policy signal, not proof on its own that learning improved — we check that separately with the pre- and post-assessments."

## 3:30–4:00 — Fallback and hardware mock mode (30 s)

**On screen:** Briefly show local fallback mode (or state that the key was removed for this segment), then the mock hardware panel sending a JSON event (e.g. `lesson_select` from `mock-cyd-01`) and the app responding.
**Narration:** "If the LLM is unavailable, SHAPE falls back to local logic and says so. And the handheld hardware — Raspberry Pi and CYD boards — works in mock mode: a small JSON event, like a lesson selection, goes through the same orchestrator. No hardware is needed for this demo, and the mock is labelled as a mock."

## 4:00–4:30 — Export Center and close (30 s)

**On screen:** Export Center. Export learner progress as CSV, then generate one individual report draft and show that its sections are filled from recorded evidence, with missing-evidence items flagged rather than invented.
**Narration:** "Finally, everything exports — progress, evaluation data, and contribution logs — and the report drafts are generated from the evidence members actually recorded. Anything missing is flagged, not made up. That's SHAPE Agent 16: learning through interaction, improving through feedback. Thank you."

---

## Recording checklist

- [ ] Record in a fresh Colab session; show the setup cell running.
- [ ] Keep the cursor visible; move slowly; pause on each tab for at least 3 seconds.
- [ ] The "LLM" / "Local fallback" label is visible in at least one shot.
- [ ] The synthetic-data label is visible on any chart that uses synthetic data, and the narration says "synthetic demonstration data".
- [ ] The policy before/after comparison is shown, not just described.
- [ ] The mock hardware event is labelled "mock" on screen.
- [ ] Total length is 3–5 minutes; check the final cut with a timer before submitting.
- [ ] No API key, password, or personal data appears on screen at any point.
