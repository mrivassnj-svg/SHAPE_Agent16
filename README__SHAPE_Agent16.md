# SHAPE — Student-centered Handheld Architecture for Programming Education

**Agent 16 — "Learning through interaction. Improving through feedback."**

- **Course:** ITAI2376, Houston Community College
- **Group:** ITAI2376_14562
- **Project deadline:** December 7, 2026
- **Proposal deadline:** November 13, 2026
- **Classification:** Option 3 — Multi-Agent Collaborative System, implemented as an Interactive Learning Companion

## What SHAPE is

SHAPE teaches programming and AI concepts through guided interaction, adaptive instruction, practical exercises, and measurable learner feedback. A learner works through Python-first lessons in a Learning Lab, submits code, gets graduated hints from a Debugger Agent, and is assessed by an Evaluator Agent. A Learning Strategist Agent selects the next teaching strategy from the learner's own results, and the system shows *why* it chose that strategy.

SHAPE is a classroom prototype, not a production tutoring platform. It does not claim to replace an instructor, and it does not present synthetic demonstration results as real student results.

## Team

| Member | Role | Full name |
|---|---|---|
| Michael Rivas | Integration and Project Coordination | Michael Rivas |
| Cherluk | Learning Design and Instructional Experience | [Full name: ____] |
| Olu | Agent Behavior and Interaction Engineering | [Full name: ____] |
| Taki | Evaluation, Testing, and Learning Analytics | [Full name: ____] |

Full names for Cherluk, Olu, and Taki are intentionally left editable — do not invent them. Every member has design, coding, testing, and reflection work; no one is assigned administration only. Michael is the final integration point: he collects contributions, implementation evidence, test results, and individual reflections, and assembles the four individual report drafts. Individual contributions are recorded separately from shared team accomplishments in the Team Workspace, and no contribution evidence or reflection is fabricated — blank fields stay blank until the member fills them.

## How to run in Google Colab (fresh session)

1. Open Google Colab and upload `Notebook__SHAPE_ITAI2376_14562.ipynb` (or open it from the team repository).
2. Run the first cell. It installs dependencies from `requirements.txt` (`gradio>=6.0`, `pandas`, `matplotlib`, `numpy`).
3. Run the setup cell. It creates the SQLite database (`shape.db`, tables: `learners`, `attempts`, `lessons_done`, `contributions`, `policy_state`) if it does not already exist.
4. Run the launch cell. A Gradio interface opens in the notebook (desktop and mobile layouts are supported).
5. Use the **Learning Lab** first: pick a lesson, read the explanation and worked example, try the exercise, submit, and read the feedback. Then check **Learner Progress** and **Adaptive Learning** to see what changed.

No hardware is required for the Colab demonstration. The hardware integration (Raspberry Pi Zero 2 W, Pico W, CYD boards) runs in mock mode by default — see `SHAPE_Agent16_Hardware_Integration_Plan.md`.

### Local demo mode (no API key)

SHAPE works fully without an API key. In local demo mode, a rules-based local fallback generates explanations, hints, and feedback from the curated lesson index. **The local fallback is not an LLM.** The interface labels every response as "LLM" or "Local fallback" in the Agent Workspace, so the distinction is always visible.

### LLM integration (optional, with an API key)

To use a real LLM:

1. In Colab, open the Secrets panel (key icon, left sidebar) and add a secret named `OPENAI_API_KEY` with your key as the value.
2. In the notebook, the key is read only through `google.colab.userdata.get('OPENAI_API_KEY')`. It is never printed, logged, or written to a file.
3. Restart the runtime after adding the secret if the notebook was already running.

**Never paste an API key into notebook source code, a cell, a comment, or a shared file.** Do not commit `.env` files — see `.gitignore`.

What needs a key, and what does not:

| Feature | Needs API key? |
|---|---|
| Lesson explanations, worked examples, exercises | No — curated lesson index |
| Code execution/checking tool, lesson retrieval tool | No |
| Learner progress, adaptive policy, evaluation charts | No |
| LLM-generated explanations, hints, and feedback | Yes |
| Local fallback explanations, hints, and feedback | No — clearly labelled as fallback |

If the key is missing, invalid, or the API call fails, SHAPE falls back to the local mode and says so, rather than failing or pretending the LLM responded.

## Architecture summary

One orchestrator coordinates four specialized agent roles, all served by a single LLM (or the local fallback). Four independent LLM services are not created.

- **Instructor Agent** — explains concepts, breaks lessons into steps, gives examples and guided exercises, adjusts complexity.
- **Debugger Agent** — examines submitted code and errors, explains why an error occurs, gives graduated hints, encourages the learner to fix it.
- **Evaluator Agent** — checks exercise results, records attempts, correctness, hint usage, and completion, and provides measurable feedback.
- **Learning Strategist Agent** — maintains learner progress, selects the next teaching strategy from previous results, and recommends review, practice, or challenge.

**Eight-step reasoning cycle:** (1) receive and validate learner input; (2) retrieve learner and lesson context; (3) plan the next instructional action; (4) select an agent role and tool; (5) execute the action; (6) evaluate the result; (7) update learner memory and feedback policy; (8) explain the outcome to the learner.

Full detail: `SHAPE_Agent16_Architecture.md`.

## Tools

1. **Python exercise execution/checking tool** — runs a learner's exercise code in a restricted namespace after an AST check, with a time limit, and interprets the result (pass, fail, error type). Input is validated before execution; errors are caught and explained rather than crashing the app.
2. **Lesson knowledge retrieval tool** — searches the project's curated lesson/resource index (lessons and the 12 HCC resources below) and returns the matching lesson, resource, and source attribution.

**Safety limit, stated plainly:** the exercise runner is *not* a hardened security sandbox. An AST check plus a restricted namespace reduces accidental harm in a classroom exercise, but it does not make arbitrary code execution safe. Do not run untrusted public code through it, and do not describe it as a sandbox in any report or demo.

## Adaptive learning and reinforcement-learning concept

Teaching strategies: worked example, concept explanation, small hint, simpler practice, challenge exercise.

**Reward function (documented, applied per exercise attempt):**

| Outcome | Reward |
|---|---|
| Correct without hints | +10 |
| Correct with one hint | +7 |
| Correct after multiple hints | +4 |
| Failed attempt | −3 |
| Attempt completed but concept check failed | −1 |

**Policy update (Q-value-inspired, per strategy):** `Q += 0.2 * (r - Q)`, where `Q` is the current value of the selected strategy for the current lesson context, `r` is the reward above, and `0.2` is the learning rate. The Adaptive Learning tab shows the policy (strategy values) before and after each interaction, so the update is transparent and checkable.

A rising reward does **not** by itself prove learning improved. Learning is evaluated independently by pre/post assessment, completion, and retention — see `SHAPE_Agent16_Evaluation_Plan.md`.

## Interface — Gradio tabs

- **A. Learning Lab** — select a lesson, view explanation and worked example, complete and submit an exercise, receive feedback and hints.
- **B. Agent Workspace** — which agent role is responding, the instructional decision, tool activity and results, and whether the LLM or local fallback was used.
- **C. Learner Progress** — attempts, completed lessons, correctness, hints used, progress charts, areas needing review, performance over time.
- **D. Adaptive Learning** — selected strategy and why, reward and policy update, before/after policy comparison.
- **E. Team Workspace** — contribution submission for all four members (design, coding, testing, reflection), evidence descriptions/links/filenames, CSV import and export, consolidation by Michael.
- **F. Export Center** — export contribution logs, evaluation data, and learner progress; generate the four individual report drafts and a team evidence summary (Markdown and CSV).

## Curriculum and HCC resource library

The learning pathway is: (1) deep learning foundations; (2) neural networks and CNNs; (3) sequence modeling and NLP; (4) transformers and attention; (5) autoencoders and generative models; (6) diffusion models; (7) reinforcement learning; (8) advanced agents, reasoning, planning, and orchestration. Initial lessons cover Python fundamentals first, because learners need that foundation before advanced AI-agent concepts.

The 12 HCC resources below are links only. They may require an authenticated HCC account. Their content was **not** accessed or extracted for this package, and restricted course material is not reproduced here. Each resource has an editable notes field and an optional field for a member to add downloaded material, a summary, or an instructor-provided reference, plus a source-attribution field where course concepts are incorporated.

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

## Evaluation summary

Fixed instruction is compared with adaptive Agent 16 instruction using a pre-assessment, lesson activities, a post-assessment, and a delayed retention check. Metrics: correctness, completion rate, hint dependency, attempts per exercise, and improvement between assessments. Learner identifiers are anonymized. Sample data in the notebook is **clearly labelled synthetic demonstration data** and is never presented as real student results; charts are populated from actual evaluation records when they exist. Full plan: `SHAPE_Agent16_Evaluation_Plan.md`.

## Hardware (mock mode by default)

Two Raspberry Pi Zero 2 W, two Raspberry Pi Pico W, two CYD display boards, and 3D-printed enclosures are planned for a later milestone. The LLM and orchestration run on the central host (Colab or a computer); handheld devices send and receive small JSON events only — lesson prompts, navigation choices, and feedback — and never run the LLM. Handheld screens are for navigation, short prompts, progress, and challenge selection; longer code entry stays on a browser or computer. Full plan: `SHAPE_Agent16_Hardware_Integration_Plan.md`.

## Package contents

| File | Purpose |
|---|---|
| `Notebook__SHAPE_ITAI2376_14562.ipynb` | Interactive Colab application (built by a separate workstream) |
| `README__SHAPE_Agent16.md` | This file |
| `requirements.txt` | Python dependencies |
| `.env.example` | API-key template (empty, no real key) |
| `.gitignore` | Keeps secrets, databases, and caches out of the repository |
| `LICENSE` | MIT License, 2026 SHAPE Team, ITAI2376 |
| `SHAPE_Agent16_Architecture.md` | System architecture |
| `SHAPE_Agent16_Evaluation_Plan.md` | Evaluation plan |
| `SHAPE_Agent16_Hardware_Integration_Plan.md` | Hardware integration plan |
| `SHAPE_Agent16_Proposal_Outline.md` | 3–4-page proposal outline (due Nov 13, 2026) |
| `SHAPE_Agent16_Demo_Video_Script.md` | Timed 3–5-minute demo script |
| `SHAPE_Agent16_Evidence_Guidelines.md` | What counts as contribution evidence |
| `SHAPE_Agent16_Team_Onboarding.pdf` | Team onboarding (built by a separate workstream) |
| `SHAPE_Agent16_Team_Roles_and_Milestones.pdf` | Roles and milestones (built by a separate workstream) |
| `SHAPE_Agent16_Contribution_Template.csv` | Contribution log template |
| `SHAPE_Agent16_HCC_Resource_Library.csv` | HCC resource library with notes fields |
| `SHAPE_Report_Template_Cherluk.md` | Individual report template — Cherluk |
| `SHAPE_Report_Template_Olu.md` | Individual report template — Olu |
| `SHAPE_Report_Template_Taki.md` | Individual report template — Taki |
| `SHAPE_Report_Template_Michael_Rivas.md` | Individual report template — Michael Rivas |

## Troubleshooting

| Problem | What to do |
|---|---|
| Gradio interface does not appear | Re-run the launch cell; check the install cell completed without errors; restart the Colab runtime and run all cells in order. |
| `OPENAI_API_KEY` not found | Add the secret in Colab Secrets, then restart the runtime. The app will still work in local fallback mode and will say so. |
| LLM call fails (quota, network, invalid key) | The app falls back to local mode and labels the response. Check the key in Secrets; do not paste it into a cell. |
| Database is empty after a restart | Colab runtimes are temporary. Export progress and contributions (Export Center, CSV) before closing, and re-import them next session. |
| Code exercise times out or errors | Read the Debugger Agent's explanation; check the exercise runner limits in the Architecture document. Do not paste arbitrary code from the internet into the runner. |
| A lesson link asks for an HCC login | That is expected — HCC resources may require an authenticated HCC account. Use the resource notes field to record what you used. |

## Safety and limits

- The code runner is a classroom exercise tool, not a hardened sandbox.
- The local fallback is rules-based, not an LLM; it is always labelled as such.
- Synthetic evaluation data is labelled synthetic and is never real student results.
- No API keys, passwords, or personal data are stored in this repository.
- HCC resource content was not extracted; links are provided with attribution and login notes only.

## License

MIT License — see `LICENSE`. Copyright 2026 SHAPE Team, ITAI2376.
