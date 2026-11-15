# SHAPE Agent 16 — Project Proposal Outline

**Proposal due:** November 13, 2026
**Final deadline:** December 7, 2026
**Course:** ITAI2376, Houston Community College, Group ITAI2376_14562
**Target length:** 3–4 pages (about 1,500–2,000 words). Page guidance below is a target, not a rule — stay within 3–4 pages total.

**How to use this outline:** Write each section in your own words, fill the bracketed fields, and delete the guidance notes before submitting. Do not invent results, test data, or contributions that have not happened yet; where something is planned rather than done, say "planned" and give the milestone date.

## 1. Title and team (¼ page)

- Title: SHAPE — Student-centered Handheld Architecture for Programming Education, Agent 16.
- Tagline: "Learning through interaction. Improving through feedback."
- Course, institution, group number, proposal date.
- Team table: Michael Rivas (Integration and Project Coordination); Cherluk (Learning Design and Instructional Experience) [Full name: ____]; Olu (Agent Behavior and Interaction Engineering) [Full name: ____]; Taki (Evaluation, Testing, and Learning Analytics) [Full name: ____].
- One sentence: what the team will deliver by December 7, 2026 (working Colab application, evaluation, demo video, final report, source repository).

## 2. Problem and motivation (½–¾ page)

- The problem: programming and AI concepts are hard to learn from static material alone; learners need guided interaction, immediate feedback on code, and instruction that adapts when they struggle.
- Who the learners are (HCC ITAI2376 students, Python fundamentals first, then AI-agent concepts) and what they struggle with, in the team's own words, based on the course resources and the team's experience — do not invent survey data.
- Why a multi-agent companion fits: different teaching jobs (explain, debug, evaluate, plan next steps) are different enough to deserve separate agent roles, coordinated by one orchestrator, rather than one undifferentiated chatbot.
- What SHAPE will not do: replace an instructor, run a hardened code sandbox, or present synthetic results as real student results.

## 3. Objectives (¼ page, bulleted)

List 4–6 measurable objectives, for example:

1. A working Colab application with Learning Lab, Agent Workspace, Learner Progress, Adaptive Learning, Team Workspace, and Export Center tabs.
2. An orchestrator coordinating four agent roles through the eight-step reasoning cycle, with at least two working tools.
3. A functioning LLM integration (Colab Secrets) with a labelled local fallback when no key is available.
4. A transparent adaptive policy (documented reward function and Q-update) whose values are shown before and after learning interactions.
5. An evaluation comparing fixed and adaptive instruction (pre/post, plus delayed retention if time permits), with anonymized IDs and synthetic data clearly labelled.
6. A hardware mock mode, with physical integration attempted only if it does not jeopardize the core application.

## 4. System architecture (¾–1 page)

- Diagram in words: learner → Gradio UI → orchestrator → four agent roles (Instructor, Debugger, Evaluator, Learning Strategist) → tools → SQLite → LLM or local fallback.
- The four roles, one or two sentences each, and what each one does not do.
- The eight-step reasoning cycle, listed in order.
- The two tools: (1) Python exercise execution/checking, with validation, error handling, and the stated limit that it is not a hardened sandbox; (2) lesson knowledge retrieval from the curated lesson/resource index.
- Data: SQLite tables `learners`, `attempts`, `lessons_done`, `contributions`, `policy_state`.
- Adaptive policy: reward table (+10 / +7 / +4 / −3 / −1) and the update `Q += 0.2 * (r - Q)`, with the note that a reward increase does not by itself prove learning improved.

## 5. Curriculum and learning pathway (½ page)

- Python fundamentals first, then the eight-stage pathway: deep learning foundations; neural networks and CNNs; sequence modeling and NLP; transformers and attention; autoencoders and generative models; diffusion models; reinforcement learning; advanced agents, reasoning, planning, and orchestration.
- The 12 HCC resources (list the titles; the full URLs are in the README and Architecture document). Note that HCC resources may require an authenticated HCC account and that their content was not extracted.
- How lessons, worked examples, and exercises map to the pathway, and who is designing them (Cherluk, Learning Design).

## 6. Evaluation plan (½ page)

- Fixed vs adaptive comparison, same lessons and assessments.
- Pre-assessment, lesson activities, post-assessment, delayed retention check (with the honest note if the delayed check cannot be completed before December 7).
- Metrics: correctness, completion rate, hint dependency, attempts per exercise, improvement between assessments.
- Anonymized learner IDs; synthetic demonstration data clearly labelled and never presented as real results.
- Owner: Taki (Evaluation, Testing, and Learning Analytics).

## 7. Team, roles, and milestones (½ page)

- Role table (Section 1) plus one sentence per member on their design, coding, testing, and reflection work — every member has all four kinds of work.
- Milestones 1–6 with dates (fill in actual dates as a team; the proposal deadline is November 13, 2026 and the final deadline is December 7, 2026):
  - M1 Team launch — package distributed, names and responsibilities confirmed, contribution log started.
  - M2 Working software prototype — Colab runs, Learning Lab works, orchestration works, progress persists.
  - M3 Agent and tool integration — LLM works, two tools work, errors and fallbacks demonstrated, policy updates recorded.
  - M4 Evaluation — pre/post works, records collected, charts generated, synthetic data separated.
  - M5 Hardware demonstration — mock mode works; physical device integrated only if time and compatibility permit.
  - M6 Final submission — contributions consolidated, four individual report drafts generated, team report completed, demo video recorded, repository validated.

## 8. Risks and mitigations (¼ page)

- LLM key / API availability → local fallback, labelled; demo does not depend on a key.
- Small evaluation sample / delayed retention not measurable in time → report descriptively, do not claim significance that was not tested.
- Hardware compatibility / Wi-Fi → mock mode is the fallback; hardware never blocks Milestones 2–4.
- Code runner safety → state the limit plainly; do not run untrusted code; do not call it a sandbox.
- Team coordination → contribution log, weekly consolidation by Michael, individual report drafts generated from actual records only.

## 9. Deliverables (¼ page, list)

Colab notebook, README, requirements, source modules, Architecture / Evaluation / Hardware documents, this proposal, demo video script and 3–5-minute video, 5–7-page final report, four individual report drafts, contribution template and evidence guidelines, HCC resource library, complete source repository.

---

**Pre-submission check:** 3–4 pages? Every bracketed field filled or honestly marked TODO? No invented results, names, or reflections? Full names for Cherluk, Olu, Taki left as editable fields, not invented? HCC links and login note included? Risks stated, not hidden?
