# SHAPE Agent 16 — System Architecture

**Project:** SHAPE — Student-centered Handheld Architecture for Programming Education
**Course:** ITAI2376, Houston Community College, Group ITAI2376_14562
**Version:** Agent 16. Final deadline December 7, 2026; proposal November 13, 2026.

## 1. Overview

SHAPE is a multi-agent collaborative system (Option 3) implemented as an Interactive Learning Companion. One orchestrator coordinates four specialized agent roles, all served by a single LLM (or a labelled local fallback). The learner interacts through a Gradio application in Google Colab. Learner state persists in SQLite. A handheld hardware layer (Raspberry Pi Zero 2 W, Pico W, CYD boards) is a later, optional milestone and is not required for the Colab demonstration.

```
Learner ──► Gradio UI (Tabs A–F) ──► Orchestrator ──► Instructor / Debugger /
                                     Evaluator / Learning Strategist
                                          │                 │
                                     Tool 1: code runner    │ Tool 2: lesson retrieval
                                          │                 │
                                     SQLite (learners, attempts, lessons_done,
                                             contributions, policy_state)
                                          │
                                     LLM (via Colab Secrets) OR local fallback
```

## 2. Orchestrator

The orchestrator is the single decision point. It does not teach directly; it receives learner input, retrieves context, plans, selects an agent role and a tool, executes, evaluates the result, updates memory and policy, and explains the outcome. There is one orchestrator instance per session. It keeps no LLM state of its own beyond the learner record and the policy state it reads from SQLite.

The orchestrator's routing logic, in plain language:

- Code submitted → Debugger Agent + code-runner tool.
- "Explain this" or a new lesson requested → Instructor Agent + lesson-retrieval tool.
- Exercise finished → Evaluator Agent; record the attempt, compute the reward, update the policy.
- Learner asks "what next?" or finishes a lesson → Learning Strategist Agent; select the next strategy from policy values.
- Anything the orchestrator cannot classify → Instructor Agent with a clarification question, and the event is logged as an unclassified input (not silently dropped).

## 3. Agent roles

### 3.1 Instructor Agent
Explains concepts, breaks lessons into manageable steps, provides worked examples and guided exercises, and adjusts explanation complexity up or down based on the learner's recent correctness and hint use. Its responses are grounded in the curated lesson index: every explanation cites the lesson and, where a course concept is used, the HCC resource it came from (source attribution field, not a copy of restricted material).

### 3.2 Debugger Agent
Examines submitted code and the error returned by the code-runner tool. It explains *why* the error occurs in plain language, then gives graduated hints — first a vague hint (what kind of problem it is), then a specific hint (where to look), then, only if asked, the corrected line. It never simply hands over a full solution on the first attempt, and it encourages the learner to correct the problem themselves.

### 3.3 Evaluator Agent
Checks exercise results against the exercise's test cases, records the attempt (correctness, attempts, hints used, completion), and gives feedback. It does not decide the next lesson — that is the Strategist's job — but its recorded reward is the input the Strategist's policy learns from.

### 3.4 Learning Strategist Agent
Maintains learner progress, selects the next teaching strategy, and recommends review, practice, or challenge activities. Its selection is explained in the Adaptive Learning tab ("selected X because strategy Y had the highest Q-value for this lesson context after N attempts").

## 4. Eight-step reasoning cycle

This is the documented reasoning pattern (planning-then-execution with evaluation and reflection). Every learner interaction runs through it, and the Agent Workspace shows the current step.

1. **Receive and validate learner input.** Empty submissions, oversized input, and input that fails the code runner's AST check are rejected with an explanation, not executed.
2. **Retrieve relevant learner and lesson context.** The learner's recent attempts, current lesson, and the matching lesson/resource from the retrieval tool.
3. **Plan the next instructional action.** The orchestrator states the intended action before acting (shown in the Agent Workspace).
4. **Select an agent role and tool.** One role and, where relevant, one tool. Tool choice is logged with its reason.
5. **Execute the action.** Run the tool and/or generate the response.
6. **Evaluate the result.** The Evaluator Agent checks the outcome against the exercise's expectations.
7. **Update learner memory and feedback policy.** Write the attempt to SQLite; apply the reward and the Q-update (Section 7).
8. **Explain the outcome to the learner.** What happened, why, and what happens next — in plain language.

## 5. Tools

At least two tools are implemented, each with input validation, selection logic, error handling, output interpretation, and a fallback path. The LLM decides when to use them and interprets their results; the orchestrator logs each call.

### Tool 1 — Python exercise execution / checking tool
- **Purpose:** Run a learner's exercise code and check it against the exercise's test cases.
- **Input validation:** The submission must be non-empty, under a size limit, and pass an AST check that rejects imports of disallowed modules, file/network access, and other operations outside the exercise's allowed set. Anything rejected is reported to the learner with the reason.
- **Execution:** The code runs in a restricted namespace with a short time limit. Output, return values, and exceptions are captured.
- **Output interpretation:** The tool returns pass/fail per test case, the error type and line when it fails, and a short machine-readable summary the Debugger Agent turns into an explanation.
- **Error handling:** Timeouts, syntax errors, and runtime errors are caught and returned as results, never as application crashes.
- **Fallback:** If execution cannot run at all (for example, the runner is unavailable), the exercise is marked "not checked — try again" and the learner is given the worked example instead of a false pass/fail.
- **Limitation, stated plainly:** This is a classroom exercise runner. An AST check plus a restricted namespace is **not** a hardened security sandbox. Do not run untrusted public code through it, and do not describe it as a sandbox in any report, demo, or README.

### Tool 2 — Lesson knowledge retrieval tool
- **Purpose:** Find the right lesson and HCC resource for the learner's current question or lesson.
- **Input validation:** The query must be non-empty text; lesson IDs must exist in the index.
- **Execution:** Searches the curated lesson/resource index (lesson titles, concept keywords, and the 12 HCC resources listed in Section 8) and returns the best-matching lesson, its worked example, and the source attribution.
- **Output interpretation:** The Instructor Agent uses the returned lesson as the grounding for its explanation and cites it.
- **Error handling:** If no lesson matches, the tool returns "no match" and the Instructor Agent says so and offers the nearest lessons, rather than inventing a lesson.
- **Fallback:** If the index is unavailable, the tool returns the current lesson's stored explanation.

Optional web search or other external APIs are **not** included in the initial build. If added later, they must be optional, documented, and configured through the same secrets mechanism as the LLM key.

## 6. LLM integration and local fallback

- **With a key:** The LLM is called through a single integration point. The API key is read only from Colab Secrets (`google.colab.userdata.get('OPENAI_API_KEY')`). It is never printed, logged, written to disk, or pasted into notebook code.
- **Without a key, or on API failure:** The system uses a rules-based local fallback that generates explanations, hints, and feedback from the curated lesson index and the error type. **The local fallback is not an LLM.** Every response in the Agent Workspace is labelled "LLM" or "Local fallback", with the reason a fallback was used when applicable.
- **What the LLM does and does not do:** It generates explanations, hints, and feedback, and it decides tool use. It does not write grades, invent evaluation results, or change the reward function. Rewards and policy updates are computed by deterministic code, not by the LLM.

## 7. Adaptive learning policy

Strategies: worked example, concept explanation, small hint, simpler practice, challenge exercise.

**Reward function:**

| Outcome | Reward |
|---|---|
| Correct without hints | +10 |
| Correct with one hint | +7 |
| Correct after multiple hints | +4 |
| Failed attempt | −3 |
| Attempt completed but concept check failed | −1 |

**Update rule (Q-value-inspired):** for the strategy just used, in the current lesson context,

```
Q += 0.2 * (r - Q)
```

where `Q` is the strategy's current value, `r` is the reward above, and `0.2` is the learning rate. The Adaptive Learning tab shows the full policy (all strategy values) before and after each update, the reward applied, and the reason the next strategy was selected. The policy starts with equal values for all strategies, so the first selections are documented as exploratory, not as learned preferences.

A rising reward does not prove learning improved. Learning is evaluated independently (see `SHAPE_Agent16_Evaluation_Plan.md`).

## 8. Curriculum and HCC resource library

Learning pathway: (1) deep learning foundations; (2) neural networks and CNNs; (3) sequence modeling and NLP; (4) transformers and attention; (5) autoencoders and generative models; (6) diffusion models; (7) reinforcement learning; (8) advanced agents, reasoning, planning, and orchestration. Initial lessons cover Python fundamentals first.

The 12 HCC resources are links only. They may require an authenticated HCC account. Their content was not accessed or extracted for this package, and restricted course material is not reproduced. Each resource has an editable notes field, an optional field for downloaded material / summary / instructor-provided reference, and a source-attribution field.

| Resource | Topic | URL |
|---|---|---|
| DL Intro | Deep Learning Introduction | https://eagleonline.hccs.edu/courses/340456/modules/items/24356286 |
| DL Toolkit | Deep Learning Toolkit | https://eagleonline.hccs.edu/courses/340456/modules/items/24356292 |
| NN Basics | Neural Network Basics | https://eagleonline.hccs.edu/courses/340456/modules/items/24356301 |
| CNN | Convolutional Neural Networks | https://eagleonline.hccs.edu/courses/340456/modules/items/25011377 |
| Sequence Modeling and NLP | Sequence Modeling and Natural Language Processing | https://eagleonline.hccs.edu/courses/340456/modules/items/24356319 |
| Applications of Transformers and Attention Mechanics | Transformers and Attention | https://eagleonline.hccs.edu/courses/340456/modules/items/24356329 |
| Autoencoders and Applied Variational (VAEs) | Autoencoders and VAEs | https://eagleonline.hccs.edu/courses/340456/modules/items/25301433 |
| Generative Adversarial Networks GANs | GANs | https://eagleonline.hccs.edu/courses/340456/modules/items/24356349 |
| Gen AI with Diffusion Models | Diffusion Models | https://eagleonline.hccs.edu/courses/340456/modules/items/24356356 |
| Reinforcement Learning in AI Agents | Reinforcement Learning | https://eagleonline.hccs.edu/courses/340456/modules/items/24356369 |
| Advanced Agents and Reasoning Models | Advanced Agents | https://eagleonline.hccs.edu/courses/340456/modules/items/24356381 |
| Agent Planning and Orchestration | Agent Planning | https://eagleonline.hccs.edu/courses/340456/modules/items/24356400 |

## 9. Data — SQLite schema

Database file: `shape.db` (created by the notebook setup cell; excluded from the repository by `.gitignore`).

| Table | Key columns | Purpose |
|---|---|---|
| `learners` | `learner_id` (anonymized, primary key), `display_name`, `created_at` | One row per learner. No real names, emails, or student IDs are stored. |
| `attempts` | `attempt_id`, `learner_id`, `lesson_id`, `exercise_id`, `correct` (0/1), `hints_used`, `attempt_number`, `reward`, `created_at` | Every exercise attempt, for progress and evaluation. |
| `lessons_done` | `learner_id`, `lesson_id`, `completed_at` | Lesson completion. |
| `contributions` | `contribution_id`, `member_name`, `date`, `workstream`, `category` (Design/Coding/Testing/Reflection), `task`, `contribution`, `evidence`, `evidence_link`, `outcome`, `reflection` | Team contribution log; feeds the four individual report drafts. |
| `policy_state` | `learner_id`, `lesson_id`, `strategy`, `q_value`, `updated_at` | One row per (learner, lesson, strategy); the adaptive policy. |

Export: all five tables export to CSV from the Export Center. Import: contribution records import from CSV in the Team Workspace, with a validation report for rows that fail (missing member, date, or category).

## 10. Gradio interface (Tabs A–F)

- **A. Learning Lab** — lesson selector, concept explanation, worked example, exercise editor, submit, feedback and hints, next exercise.
- **B. Agent Workspace** — active agent role, instructional decision, tool activity and results, LLM vs local-fallback label, current reasoning-cycle step.
- **C. Learner Progress** — attempts, completed lessons, correctness, hints used, charts (matplotlib), areas needing review, performance over time.
- **D. Adaptive Learning** — selected strategy and why, reward and policy update, policy before/after comparison.
- **E. Team Workspace** — contribution form for all four members, evidence fields, CSV import/export, consolidation view for Michael.
- **F. Export Center** — export contribution logs, evaluation data, learner progress; generate the four individual report drafts and the team evidence summary (Markdown and CSV).

Gradio 6 compatibility: no deprecated constructor arguments for theme or CSS are used. Layout is usable on desktop and mobile; labels do not overlap and components are not cramped.

## 11. Safety, validation, and transparency

- Learner input is validated before any tool runs; rejected input is explained, not silently ignored.
- The code runner is not a hardened sandbox (Section 5).
- The local fallback is labelled as not an LLM (Section 6).
- The adaptive policy, its rewards, and its updates are shown to the learner (Section 7).
- Evaluation data is anonymized and synthetic data is labelled synthetic (see Evaluation Plan).
- No API keys or personal data are stored in the repository (`.env` is git-ignored; Colab Secrets are used instead).
- Every agent response that draws on a course concept carries a source attribution; restricted course material is not reproduced.

## 12. Hardware interface summary

Full detail: `SHAPE_Agent16_Hardware_Integration_Plan.md`. In short: the LLM and orchestration run on the central host (Colab or a computer). Handheld devices (Pi Zero 2 W, Pico W, CYD) send and receive small JSON events only, e.g. `{"device_id": "cyd-01", "event": "lesson_select", "lesson_id": "py-01", "action": "next", "timestamp": "2026-12-01T10:00:00Z"}`. They never run the LLM. Mock mode works without any physical device and is the default for the Colab demonstration.
