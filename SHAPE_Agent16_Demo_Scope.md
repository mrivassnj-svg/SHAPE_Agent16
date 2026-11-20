# SHAPE Agent 16 — Tightened Demo Scope

**Purpose of this document:** Define exactly what the team ships for the demo by
December 7, 2026 — no more, no less. Anything not listed here is explicitly
out of scope for the demo. It may be documented as future work, but it will
not appear in the demo video or the final submission.

**Course:** ITAI2376, Houston Community College, Group ITAI2376_14562
**Demo deadline:** December 7, 2026

---

## 1. The Problem That Was Discovered

The repo currently has **two parallel implementations** that share documentation
but diverge in code:

| Path | LLM | UI tabs | Status |
|---|---|---|---|
| `shape/` (Python package) | OpenAI (`gpt-4o-mini`, via Colab Secrets) | 6 tabs (A–F, matches all docs) | Canonical for demo |
| `src/` | Groq (`qwen3.8-27b`, env var) | 3 tabs (Chat, Lesson Builder, RL Monitor) | To be kept as local dev option only |

**Decision:** The demo runs the `shape/` package loaded from `Notebook__SHAPE_ITAI2376_14562.ipynb`
in Google Colab. The `src/` modules are retained for local development and
testing but are **not demoed**. No time is spent merging the two.

---

## 2. What IS in scope for the demo

These are the only things the team builds and demos. Each item has a clear owner
and can be completed by December 7.

### 2.1 The Colab notebook — `Notebook__SHAPE_ITAI2376_14562.ipynb`

The single runnable deliverable. It must:

- Install `gradio>=6.0,<7.0 openai pandas matplotlib numpy` in one cell.
- Build and launch the 6-tab Gradio UI defined in `shape/ui.py` via `build_demo()`.
- Run completely without an API key (local fallback, labelled).
- Run with an OpenAI key stored in Colab Secrets as `OPENAI_API_KEY` (LLM mode, labelled).
- Seed 5 lessons on first run from `shape/store.py`.

**Owner:** Michael Rivas (integration). Every team member confirms the notebook
runs in a fresh Colab session before the demo recording.

### 2.2 The 6-tab Gradio UI — already in `shape/ui.py`

All six tabs are already coded. The only remaining work is functional testing
and bug fixes. No new tabs, no new features.

| Tab | What to verify before demo |
|---|---|
| **A. Learning Lab** | Select a lesson → concept/example/exercise populate; submit code → feedback shows; hint counter increments; concept-check button works; pre-test scores; post-test shows Δ |
| **B. Agent Workspace** | Ask a question → all 6 output fields populate; submit code → tool activity shows; mode label says LLM or Local fallback |
| **C. Learner Progress** | After attempts → Refresh shows counts; chart renders without crashing |
| **D. Adaptive Learning** | Refresh → Q-table shows before/after values; strategy selection shows reason; synthetic-data label is on the chart |
| **E. Team Workspace** | Save a contribution → appears in log; CSV import works with the template |
| **F. Export Center** | Export contributions CSV → file downloads; Export evaluation CSV → file downloads; Generate report drafts → text output includes member name and flags missing evidence; Hardware mock test → JSON validates correctly |

### 2.3 The lesson set — `shape/store.py` `LESSONS` list

Five lessons are already seeded. Each lesson needs:
- A `concept` (3–5 sentences)
- A `example` (5–10 lines of Python, runnable)
- An `exercise` (1–2 sentence problem statement with an `expected_output`)
- Three `hints` (vague → specific → near-solution)
- A `concept_check_q` and `concept_check_a`

**Current lessons:** Variables, For Loops, Functions, Conditionals, Lists.
No new lessons are added for the demo — fix any incomplete fields in the
existing five.

**Owner:** Cherluk (Learning Design). Fill any missing `hints` or
`concept_check_a` fields before November 28.

### 2.4 The two tools — already in `shape/tools.py`

- **`run_code_tool`** — AST-validated Python exercise runner; returns
  `passed`, `stdout`, `expected`, `hint`, `error`. Already works.
  Verify it handles the five seed exercises correctly.
- **`retrieve_lesson_tool`** — Keyword search over `LESSONS`; returns the
  matching lesson object. Already works. No changes needed.

**Owner:** Olu (Agent Behavior and Interaction Engineering). Write one test
per tool that covers a passing case, a failing case, and an error case by
November 28. Use `tests/test_shape.py` (already has the fixture pattern).

### 2.5 The RL policy — already in `shape/policy.py`

The ε-greedy contextual bandit is already coded. The demo must show:
1. The Q-table **before** the learner's first attempt (all equal).
2. After a correct-with-one-hint attempt: `+7` reward and the Q-update applied.
3. The strategy selected next and its reason.

No changes to the policy code. The only work is making sure Tab D populates
correctly after a code submission in Tab A.

**Owner:** Taki (Evaluation, Testing, and Learning Analytics).

### 2.6 Pre/post assessment — already in `shape/store.py` `ASSESSMENT` list

Five MC questions already defined. Verify that:
- Pre-test scores and stores the score in `pre_state`.
- Post-test reads `pre_state` and prints the Δ.
- Neither test fabricates data: if `pre_state` is None when post is scored,
  it says so.

**Owner:** Taki. No new questions. Fix any broken callbacks if found.

### 2.7 The tests — `tests/test_shape.py`

50 tests pass today (all in `src/`). Add **one test class** for the
`shape/` package that runs the same core paths without an API key:
- `shape.tools.run_code_tool` — pass, fail, error
- `shape.tools.retrieve_lesson_tool` — match, no match
- `shape.policy.reward_for` — 4 reward values
- `shape.policy.update_q` — Q-value moves in the right direction

**Owner:** Olu and Taki jointly. Target: all tests green by November 28.

---

## 3. What is explicitly OUT of scope for the demo

These items are **not done, not attempted, not mentioned in the demo video.**
They are documented as future work in the Architecture document.

| Item | Why it's cut |
|---|---|
| **Hardware** (Pi Zero 2 W, Pico W, CYD boards) | Zero code, zero devices in hand. Mock mode in Tab F is sufficient. The hardware mock JSON test covers the contract. |
| **Blender sprite generation** (`blender/`) | Unrelated to the AI learning companion. |
| **RPG layer** (`src/shape_rpg_*.py`, `rpg_run.sh`) | A parallel concept, not connected to the Colab demo. |
| **DEBIAN packaging** (`DEBIAN/`) | Not a course deliverable. |
| **`puromo/` directory** | Empty; nothing to do. |
| **Merging `src/` and `shape/`** | No time. `src/` stays as-is for local dev. |
| **Delayed retention check** | Cannot be completed before December 7; the report will say so. |
| **Web search / external APIs** | Not in scope per Architecture document. |
| **Multi-learner comparison study** | Sample size is too small; use synthetic-labelled charts as the demo shows. |

---

## 4. The demo video — tightened to 4 minutes

Follow `SHAPE_Agent16_Demo_Video_Script.md` exactly. The only change:
**cut the hardware segment from 30 s to 15 s** — show the JSON test button
in Tab F, nothing more. Use the saved time to show the policy before/after
comparison more clearly (Tab D).

Revised timeline:

| Segment | Time | Tab |
|---|---|---|
| Introduction | 0:00–0:30 | — |
| Learning Lab — lesson + code submission + hint | 0:30–1:15 | A |
| Agent Workspace — Debugger role + tool log + fallback label | 1:15–2:00 | B |
| Learner Progress — chart + attempt table | 2:00–2:30 | C |
| Adaptive Learning — Q before/after + strategy reason | 2:30–3:15 | D |
| Export Center — CSV export + report draft generation | 3:15–3:45 | F |
| Hardware mock — JSON test button, 1 event | 3:45–4:00 | F |

**Rule:** If a tab crashes during recording, say "I'll come back to that" and
move on. Do not re-record the entire video for one broken tab — fix the tab,
then re-record only that segment.

---

## 5. Member task list — what everyone builds before November 28

### Michael Rivas (Integration and Project Coordination)

- [ ] Confirm `Notebook__SHAPE_ITAI2376_14562.ipynb` runs clean in a fresh Colab session.
- [ ] Wire `shape/` package import path in the notebook (single `sys.path.insert` or `%cd` cell).
- [ ] Verify all 6 tabs launch without errors in both local-fallback and LLM mode.
- [ ] Confirm `shape.db` is auto-created on first run and excluded from git (`.gitignore` check).
- [ ] Run the full test suite (50 existing + new `shape/` package tests) green before the final submission.
- [ ] Record or coordinate the final 4-minute demo video.
- [ ] Consolidate the four individual report drafts from Tab F.

### Cherluk (Learning Design and Instructional Experience)

- [ ] Review each of the five seed lessons in `shape/store.py`; fill any missing `hints[2]` or `concept_check_a` fields.
- [ ] Confirm the `expected_output` for each exercise matches what `run_code_tool` returns for the worked example code.
- [ ] Record individual contributions in Tab E (Design category: lesson design decisions; Reflection: what you learned).
- [ ] Contribute the Learning Design section to the final report.

### Olu (Agent Behavior and Interaction Engineering)

- [ ] Test all four agent routes in Tab B: Instructor (plain question), Debugger (error code), Evaluator (concept check answer), Learning Strategist ("what next?").
- [ ] Add the `shape/` package test class to `tests/test_shape.py` (run_code_tool, retrieve_lesson_tool, reward_for, update_q).
- [ ] Confirm the tool log in Tab B shows the tool name, input snippet, and result for a code submission.
- [ ] Record individual contributions in Tab E (Coding and Testing categories).
- [ ] Contribute the Agent Behavior section to the final report.

### Taki (Evaluation, Testing, and Learning Analytics)

- [ ] Verify Tab C charts render after at least 3 attempts; confirm the synthetic-data label is visible on the Tab D chart.
- [ ] Confirm Tab A pre-test → lesson attempts → Tab A post-test shows the correct Δ.
- [ ] Record synthetic vs real flag in any chart that uses synthetic data (already in `_synthetic_figure()`; just confirm the label is visible at demo resolution).
- [ ] Record individual contributions in Tab E (Testing and Reflection categories).
- [ ] Contribute the Evaluation section to the final report.

---

## 6. The only files the team touches before the deadline

**Edit these:**

| File | Who | What |
|---|---|---|
| `Notebook__SHAPE_ITAI2376_14562.ipynb` | Michael | Setup cells, launch cell, Colab compatibility |
| `shape/store.py` | Cherluk | Lesson `hints` and `concept_check_a` fields; `expected_output` fixes |
| `tests/test_shape.py` | Olu + Taki | Add `shape/` package test class |
| `SHAPE_Report_Template_*.md` | Each member | Individual report content |

**Do not touch these:**

- `shape/agents.py`, `shape/policy.py`, `shape/tools.py`, `shape/ui.py` —
  these are functionally complete; only fix confirmed bugs, do not add features.
- `src/` — do not merge, do not modify; leave as local dev option.
- `SHAPE_Agent16_Architecture.md`, `SHAPE_Agent16_Evaluation_Plan.md`,
  `SHAPE_Agent16_Hardware_Integration_Plan.md` — these are correct and final.
- `README.md`, `README__SHAPE_Agent16.md` — correct; do not rewrite.

---

## 7. Definition of done

The demo is ready when all of the following are true:

- [ ] `Notebook__SHAPE_ITAI2376_14562.ipynb` runs from top to bottom in a fresh
      Colab session with no uncaught exceptions.
- [ ] All six tabs are reachable and their primary action (submit, refresh, ask,
      export, etc.) works in local-fallback mode.
- [ ] The test suite passes (`python -m pytest tests/ -v`), including the new
      `shape/` package tests.
- [ ] All five lessons have three hints and a concept-check answer.
- [ ] The demo video is 3–5 minutes, labelled correctly (synthetic data, local
      fallback or LLM, mock hardware), and shows real app behavior.
- [ ] All four individual report drafts have been generated from Tab F, reviewed
      by each member, and reflect actual recorded contributions.
- [ ] No API key, password, real learner name, or personal data appears in any
      submitted file or in the demo video.
