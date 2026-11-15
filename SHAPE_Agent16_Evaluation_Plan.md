# SHAPE Agent 16 — Evaluation Plan

**Project:** SHAPE, Agent 16 — ITAI2376, Houston Community College, Group ITAI2376_14562
**Final deadline:** December 7, 2026. **Proposal deadline:** November 13, 2026.
**Owner:** Taki (Evaluation, Testing, and Learning Analytics). All members contribute test records and review the results; Taki consolidates them.

## 1. Evaluation question

Does adaptive Agent 16 instruction improve learner outcomes compared with fixed instruction, for the same lessons, exercises, and assessments?

This plan does not assume the answer. It is designed so a null or negative result is reportable, not hidden.

## 2. Comparison design

Two conditions, same content:

- **Condition F — Fixed instruction:** lessons and exercises in a fixed order, the same explanation and hints for every learner, no strategy selection.
- **Condition A — Adaptive Agent 16 instruction:** the same lessons and exercises, with the Learning Strategist Agent selecting the next strategy from the learner's results, using the reward function and Q-update in the Architecture document.

Learners are assigned to a condition before the pre-assessment. Assignment method (for example, alternating anonymized IDs) must be recorded in the evaluation log; if assignment was not random, say so in the report — do not claim random assignment that did not happen.

## 3. Instruments and timeline

| Stage | What happens | When |
|---|---|---|
| Pre-assessment | Short concept check + one Python exercise, same for both conditions. Establishes a baseline. | Before Lesson 1 |
| Lesson activities | Lessons 1–N in the Learning Lab. Every attempt, hint, and completion is recorded in `attempts` / `lessons_done`. | During the study |
| Post-assessment | Same format as the pre-assessment, different items of matched difficulty. | Immediately after the last lesson |
| Delayed retention check | Short concept check + one exercise, same format, administered later. | At least 7 days after the post-assessment (record the actual interval) |

If the delayed check cannot be run before December 7, 2026, the report must say so and must not present post-assessment results as retention results.

## 4. Metrics (all computed from `attempts`, never hand-entered)

- **Correctness:** proportion of exercises correct on the first attempt; proportion correct eventually.
- **Completion rate:** lessons completed divided by lessons started, per learner and per condition.
- **Hint dependency:** mean hints used per correct exercise; proportion of correct exercises completed with zero hints.
- **Attempts per exercise:** mean attempts to first correct answer, per exercise and per condition.
- **Improvement between assessments:** post-assessment score minus pre-assessment score, per learner; same for the delayed check.
- **Time / interaction count where practical:** number of interactions per lesson, recorded by the app where available. Do not invent time data the app did not record.

## 5. Learner identifiers and privacy

- Learners are identified only by an anonymized ID (for example, `L001`, `L002`) generated in the app. No real names, emails, or student IDs are stored in `shape.db` or in any evaluation export.
- The mapping from anonymized ID to a real person, if one is ever needed for a classroom, is kept outside this repository and is never included in a report, export, or demo.
- Participation is voluntary for any classroom test; a learner who declines is not recorded as a zero.

## 6. Synthetic demonstration data — labelling rule

The notebook ships with a clearly labelled synthetic dataset so charts and the comparison can be demonstrated without real learners. The rules are:

- Every synthetic record, chart, table, and export is labelled **"SYNTHETIC DEMONSTRATION DATA — NOT REAL STUDENT RESULTS"** in the app, in the export file, and in any screenshot or slide that uses it.
- Synthetic data is stored separately from real records (a `synthetic` flag / separate table) and is never mixed into a real-condition calculation.
- **Never present synthetic results as real student results**, in the demo video, the final report, or a presentation. If a chart in the report uses synthetic data because real data was not yet collected, the caption must say so.
- A reward increase in synthetic or real data does **not** prove learning improved. Reward is a policy signal, not a learning outcome. Learning is judged by the pre/post and retention assessments in Section 4.

## 7. Charts (populated from actual records)

Charts are generated from the `attempts` table (or from the labelled synthetic dataset for demonstration). Required charts:

1. Correctness by condition (pre vs post, grouped bars).
2. Completion rate by condition.
3. Hint dependency: mean hints per correct exercise, by condition.
4. Attempts per exercise, by condition.
5. Improvement (post minus pre) per learner, as a distribution, by condition.
6. Policy values before/after (from `policy_state`) — shown as a policy record, not as a learning outcome.

Each chart carries its data source, the number of learners included, and the date range. A chart with fewer than 3 learners per condition is labelled "too few learners to compare — descriptive only".

## 8. Analysis — what counts as a finding

- Report means and counts per condition, with the number of learners behind each number.
- Report the difference between conditions for each metric in Section 4, and state whether the sample is large enough to support a comparison. With a small classroom sample, describe the difference and its uncertainty honestly; do not claim statistical significance that was not tested.
- Report hint dependency and attempts alongside correctness: an adaptive condition that raises correctness only by using many more hints has not necessarily improved independent learning, and the report must say that.
- Report any condition difference that favours fixed instruction, and any lesson where the adaptive policy selected a strategy that learners then failed with. Negative results are findings.

## 9. Threats and limits (to state in the final report)

- Small sample size; short study duration; delayed retention may not be measurable before the deadline.
- The local fallback is not an LLM, so results in fallback mode are not results for LLM instruction — record which mode each session used.
- The code runner is a classroom tool, not a sandbox; exercise results reflect the exercises, not general programming ability.
- Novelty: learners may engage more with a new system at first; that effect fades and is not learning.

## 10. Evaluation records and responsibilities

| Record | Where it lives | Who records it |
|---|---|---|
| Pre/post/retention scores | `attempts` + assessment exports | Taki (consolidated); all members run their own lesson tests |
| Attempt, hint, completion data | `attempts`, `lessons_done` (automatic) | App (automatic); Taki verifies |
| Condition assignment log | Evaluation log (CSV, Export Center) | Taki |
| Charts | Export Center / final report | Taki, reviewed by Michael |
| Synthetic vs real separation check | Validation report | Taki, reviewed by Michael |

## 11. Milestones

- **Milestone 4 (Evaluation):** pre/post assessment works in the app; test records are collected; charts and comparisons are generated from real records where available; synthetic data is clearly separated.
- **Final submission:** evaluation section of the team report is written from the records above, with the labelling rule in Section 6 applied to every figure.
