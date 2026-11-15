# SHAPE Agent 16 — Validation Report

Date: 2026-11-06
Package: `SHAPE_Agent16_Team_Package.zip` (folder `SHAPE_Agent16/`)
Course: ITAI2376, Group ITAI2376_14562, Houston Community College
Final deadline: December 7, 2026. Proposal deadline: November 13, 2026.

## Deliverables — 21 items, all present

Core (7): Notebook, README, requirements.txt, .env.example, .gitignore, LICENSE, source modules (`shape/` — 6 files).
Team (5): Onboarding PDF (5 pp), Roles and Milestones PDF (4 pp), Contribution Template CSV (4 example rows, 13 columns), Evidence Guidelines, HCC Resource Library CSV (12 resources).
Individual (4): Report templates for Cherluk, Olu, Taki, Michael Rivas.
Documentation (5): Architecture, Evaluation Plan, Hardware Integration Plan, Proposal Outline, Demo Video Script.

Note on field count: the contribution log has **13 fields** (member name, full name, date, workstream, category, task, specific contribution, evidence description, evidence link/filename, technical decisions, challenges, outcome, individual reflection). That matches the master prompt's field list and the CSV header exactly. An earlier internal brief said "14 fields" in error; no 14th field was invented.

## PASS

- Notebook JSON valid (`python3 -m json.tool`); 16 cells (7 code, 9 markdown).
- Notebook code cells executed in order in a clean temp dir (Gradio 6.31.0, pandas, matplotlib; launch skipped via `SHAPE_LAUNCH=0`): 43 functional checks, 43 PASS, 0 FAIL (builder run, 2026-11-06).
- Independent spot check by the integrator (2026-11-06): `shape.policy` imports; `run_code_tool("print('Hello, SHAPE')", ...)` passes; `import os` blocked with a clear error; `retrieve_lesson_tool("loops")` returns L4.
- Rewards +10/+7/+4/−3/−1 and Q-update `Q += 0.2*(reward − Q)` verified; Q for Worked example 0.0 → 2.0 on reward +10.
- Orchestrator logs 8 reasoning steps; mode labelled "Local fallback" with no key.
- SQLite: 5 tables (learners, attempts, lessons_done, contributions, policy_state); attempts/progress recorded.
- Contributions: save + CSV logic works; report drafts use real records only and flag missing evidence/reflections (e.g. Olu draft: "Records with no reflection: 1"; Taki draft: "No contribution records were found").
- Hardware mock: valid JSON message accepted, missing-fields message rejected.
- All 12 HCC resource URLs present verbatim in README and Architecture; notes say HCC login may be required, content not claimed as accessed.
- No full names invented for Cherluk, Olu, or Taki; editable `[Full name: ____]` fields present.
- No API secrets in source (scanned .md/.py/.ipynb/.txt for keys; `.env.example` contains only an empty `OPENAI_API_KEY=` placeholder).
- PDFs verified: Onboarding 5 pages, Roles and Milestones 4 pages (`pdfinfo`).
- CSVs validated with Python `csv` module.

## PARTIAL

- UI callbacks: verified as 18 wired Gradio dependencies with inputs/outputs, not by clicking in a live browser.
- CSV export / report file writing through the live UI: verified by the same code paths in the test harness, not through the live UI.
- Gradio theme: Gradio 6 moved `theme` from `Blocks()` to `launch()` — fixed during testing; launch is `demo.launch(share=False, theme=gr.themes.Soft())`.

## NOT TESTED

- Live `demo.launch()` serving (guarded out in tests; launching would block).
- A real OpenAI call (no API key in this environment; only the no-key fallback path was exercised).
- A real Google Colab run (tested locally in a venv; a local httpx/NO_PROXY quirk required clearing proxy env vars for Gradio import — a local environment quirk, not a notebook bug, and Colab does not have that env).
- No real student evaluation data exists yet. All evaluation figures in the notebook are labelled **SYNTHETIC DEMO ONLY** and must not be presented as real results.
- Hardware integration with physical Pi Zero 2 W / Pico W / CYD devices (mock mode only; Milestone 5).

## Bugs found and fixed during testing

1. Gradio 6 theme argument location (see PARTIAL above).
2. `import math` failed in the restricted runner because `__import__` was missing from allowed builtins — added; direct `__import__` use in learner code is still AST-banned, only `math`/`random` imports pass.
3. Orchestrator log merged steps 5–6 into one entry — split into 8 log lines.
4. Earlier notebook build: `set_visibility`-style single-object error — not applicable here; this notebook was built fresh.

## How to re-run the checks

1. `python3 -m json.tool Notebook__SHAPE_ITAI2376_14562.ipynb > /dev/null`
2. Extract the 7 code cells, run them in order with `SHAPE_LAUNCH=0` (see notebook cell 1 for setup).
3. In the app: submit a correct and an incorrect exercise, use a hint, check Learner Progress and Adaptive Learning (Q-table changes), save a contribution, export CSVs, generate the 4 report drafts.
4. Confirm the mode label reads "Local fallback" with no API key, and "LLM" only after a Colab Secret `OPENAI_API_KEY` is set.
