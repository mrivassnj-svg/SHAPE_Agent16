# FN_Proposal_MichaelRivas_Group_ITAI2376_14562.md

---

# SHAPE Agent 16
## Interactive Learning Companion
### Project Proposal

---

**Course:** ITAI2376 — Artificial Intelligence  
**Section:** 14562  
**Institution:** Houston Community College  
**Submission Date:** November 13, 2026  
**Final Project Due:** December 7, 2026  

---

## Group Members & Functional Roles

| Name | Design Contribution | Coding Role | Reflection Responsibility |
|---|---|---|---|
| **Michael Rivas** | System Architecture, Integration Planning | Orchestrator loop, DB layer, entry point | Architecture decisions and integration challenges |
| **Cherluk** | Learning Design, Instructional Experience | Gradio Lesson Builder UI | Curriculum design insights and UX learnings |
| **Olu** | Agent Behavior, Interaction Engineering | Tool integration, safety layer | Tool reliability, boundary enforcement observations |
| **Taki** | Evaluation Strategy, Learning Analytics | RL policy module, assessment tracking | Metric design, testing outcomes, policy improvements |

---

## 1. Problem Statement

Programming and AI education at the community college level faces three persistent challenges:

1. **Heterogeneous learner backgrounds** — students arrive with vastly different prior experience, and a single lecture pace leaves both ends of the spectrum behind.
2. **Delayed feedback** — students often receive graded feedback days after submission, losing the moment when correction is most effective.
3. **Curriculum rigidity** — instructors cannot easily inject timely, personalised lesson supplements mid-semester without a technical deployment pipeline.

SHAPE Agent 16 addresses all three: it delivers immediate, adaptive, one-on-one tutoring by dynamically selecting among five pedagogical strategies based on a persisted reinforcement learning policy; it gives instant code execution feedback through a sandboxed Python runner; and it provides a no-code web form (the Lesson Builder) through which any team member — coding-proficient or not — can publish new curriculum content that the agent uses in real time.

The target domain is **introductory to intermediate programming (Python) and AI concepts**, aligning directly with ITAI2376 course material.

---

## 2. Project Option

**Option 4 — Interactive Learning Companion**

SHAPE Agent 16 satisfies all four key features specified for this option:

| Required Feature | Implementation |
|---|---|
| Learner profile building and adaptation | `learners` table tracks level, topics seen; level promotion triggers after 3 consecutive perfect-score turns |
| Personalised content generation | Strategy selected per-turn by ε-greedy policy; LLM prompt tailored to level and strategy |
| Progress assessment and feedback | Pre/post assessments stored in DB; hint count and correctness tracked per turn |
| Learning path adjustment based on performance | Evaluator and Learning Strategist sub-agents recommend path changes; level updates persisted |

---

## 3. Agent Design & Architecture

### 3.1 Overall Architecture

SHAPE Agent 16 is built as a **multi-agent system** implemented via specialised LLM system-prompt personas managed by a single Python orchestrator.  All agents share one context window per turn, but each adopts a distinct instructional role.

```
┌────────────────────────────────────────────────────────────┐
│                     Gradio Web Interface                    │
│          (Chat Tab)              (Lesson Builder Tab)       │
└──────────────────────┬────────────────────┬────────────────┘
                       │ user turn           │ lesson submit
                       ▼                     ▼
┌──────────────────────────────────────────────────────────────┐
│                  shape_agent_core.py                         │
│                  8-Step Orchestrator                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │Instructor│  │Debugger  │  │Evaluator │  │Strategist  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└───────┬──────────────────┬──────────────────────────────────┘
        │                  │
        ▼                  ▼
┌──────────────┐   ┌───────────────────────┐
│ shape_tools  │   │  shape_rl_policy.py   │
│ Tool 1: Code │   │  ε-greedy Q-table     │
│ Tool 2: Retr │   └───────────┬───────────┘
└──────┬───────┘               │
       │                       ▼
       └──────────► shape_db_handler.py (SQLite: shape.db)
```

### 3.2 Four Sub-Agent Personas

| Agent | System Prompt Focus | Activated When |
|---|---|---|
| **Instructor** | Explains new material using the selected strategy and level | Default for all question turns |
| **Debugger** | Analyses code errors, points to the exact line, suggests minimal fix | Code fenced block detected in input OR code execution returns an error |
| **Evaluator** | Structured ✅/⚠️/💡 feedback on a submitted answer | User writes "check my answer", "is this correct", or "grade" |
| **Learning Strategist** | Recommends level advancement, topic revisit, or continuation | Invoked internally by the orchestrator after every 5 turns |

### 3.3 Agent Patterns Implemented

- **ReAct (Reasoning and Acting):** The orchestrator reasons in a Chain-of-Thought scratchpad (Step 4) before deciding whether to invoke a tool (Step 5), then generates the final response (Step 6).
- **Chain-of-Thought:** Each turn produces an internal scratchpad noting the learner level, chosen strategy, curriculum hit status, and code detection before any LLM call is made.
- **Reflection-based Improvement:** The Learning Strategist sub-agent reviews accumulated turn outcomes and proposes path adjustments; level promotion is automatic on repeated high-reward turns.

---

## 4. Step-by-Step Execution Sequence

The following is the exact chronological sequence for every learner turn:

```
Step 1 │ RECEIVE
       User submits text via Gradio or CLI.
       shape_safety.validate_user_prompt() checks for:
         • Empty / oversized input
         • Prompt injection patterns (regex: "ignore previous instructions", etc.)
       → If unsafe: return immediate refusal; log violation; skip remaining steps.

Step 2 │ PROFILE
       shape_db_handler.get_learner() loads the learner record.
       If first visit: upsert_learner() creates the record with level='beginner'.
       Session created/continued via create_session() + log_interaction(role='user').

Step 3 │ RETRIEVE  [Tool 2]
       shape_tools.retrieve_curriculum() tokenises the query into keywords
       and calls shape_db_handler.search_lessons().
       Matching lesson excerpts (top 3) are stored in curriculum_ctx string.
       On failure (no DB match): curriculum_ctx = '' → orchestrator continues
       without retrieval context.

Step 4 │ REASON  (CoT scratchpad + strategy selection)
       Orchestrator writes internal scratchpad:
         "Learner level: beginner | Strategy: SCAFFOLD | Curriculum hit: YES | Code: NO"
       shape_rl_policy.select_strategy() applies ε-greedy:
         • With probability ε=0.15 → explore (random strategy, level-biased)
         • Otherwise → exploit argmax Q-value from policy_stats table
       Active sub-agent role determined:
         code fence in input → 'debugger'
         "check my answer" keyword → 'evaluator'
         else → 'instructor'

Step 5 │ ACT  [Tool 1]
       If code block detected:
         shape_tools.run_python_exercise() pipeline:
           a. AST safety scan → reject banned imports / builtins
           b. Execute in restricted namespace with 5-second thread timeout
           c. Capture stdout/stderr; truncate at 2000 chars
         tool_output injected into user message for Step 6.
       If no code: skip Tool 1.

Step 6 │ RESPOND  (LLM call)
       Assemble messages list:
         [system: role prompt with {level} + {strategy} substituted]
         [user:   curriculum_ctx + original query + tool_output]
       Call openai.chat.completions.create(model=gpt-3.5-turbo, max_tokens=600)
       On APIError → shape_safety.fallback_response() returned.

Step 7 │ EVALUATE  (reward computation)
       Heuristic proxies:
         answer_correct = '✅' in reply
         hints_given    = count('hint') in reply
       shape_rl_policy.compute_reward(correct, hints_given, violation)
         correct+0 hints → +1.0 | +1 hint → +0.5 | +2 hints → +0.2
         incorrect → 0.0 | violation → −0.5
       shape_rl_policy.record_outcome() writes reward to policy_stats:
         Q(strategy) ← (cumulative_reward + r) / (n + 1)   [incremental mean]

Step 8 │ ADAPT  (profile update)
       shape_db_handler.add_topic_seen() records matched lesson topic.
       If last 3 agent turns all have reward = 1.0:
         update_learner_level() promotes beginner→intermediate or intermediate→advanced.
       shape_db_handler.log_interaction(role='agent', reward=r) persists the turn.
       Final reply string returned to Gradio / CLI.
```

---

## 5. Tool Selection

### Tool 1 — Python Classroom Exercise Runner (`shape_tools.run_python_exercise`)

**Purpose:** Let students submit code answers and receive immediate execution feedback.

**How the agent decides to use it:** The orchestrator scans the user's message for a fenced Python code block (`` ```python ... ``` ``). If found, Tool 1 is invoked before the LLM call.

**Error handling:** 
- AST scan rejects dangerous imports (`os`, `subprocess`, `socket`, etc.) and banned builtins (`exec`, `eval`, `open`)  
- Execution runs on a daemon thread with a 5-second hard timeout to prevent infinite loops  
- Any runtime exception is caught, formatted (traceback limited to 5 frames), and passed to the Debugger persona  

**How the agent uses the output:** The captured stdout or error message is appended to the user message block sent to the LLM, so the Debugger persona can see exactly what the code produced.

---

### Tool 2 — Local Keyword Retrieval (`shape_tools.retrieve_curriculum`)

**Purpose:** Surface instructor-curated lesson content before falling back to general LLM knowledge, ensuring the agent teaches what the course syllabus prescribes.

**How the agent decides to use it:** Tool 2 is invoked on every non-violation turn (Step 3), regardless of whether code is present. Stopwords are filtered; remaining tokens are matched against the `keywords` JSON column in the `curriculum` table.

**Error handling:**
- Empty query → immediate `ToolResult(success=False)`  
- DB exception → `fallback_response()` with exception message  
- No matching lessons → `ToolResult(success=True, data=[])` — orchestrator continues without curriculum injection  

**How the agent uses the output:** Top-3 matching lesson excerpts (truncated to 600 chars each) are prepended to the user's message as `[Curriculum Context]` so the LLM treats them as authoritative reference material.

---

## 6. Reinforcement Learning Elements

SHAPE Agent 16 implements a **contextual bandit** framework — a simplified form of reinforcement learning appropriate for a tutoring system where each turn is effectively stateless with respect to future turns.

### 6.1 Teaching Strategies (Actions)

| ID | Strategy | Description |
|---|---|---|
| EXPLAIN | Direct Explanation | State the concept clearly with a worked example |
| SOCRATIC | Guided Questioning | Lead the learner to the answer with questions |
| ANALOGY | Analogy-First | Anchor the concept in a familiar real-world scenario before formalising |
| SCAFFOLD | Incremental Build-up | Decompose the concept into the smallest learnable steps |
| CHALLENGE | Extension Challenge | Present a harder problem first; debrief after attempt |

### 6.2 Reward Function

```
reward(correct, hints, violation) =
    −0.5   if violation
     0.0   if not correct
    +1.0   if correct AND hints == 0
    +0.5   if correct AND hints == 1
    +0.2   if correct AND hints >= 2
```

### 6.3 Policy Update (Incremental Sample Mean)

```
Q(strategy) ← (Σ rewards for strategy) / (n selections of strategy)
```

This is the incremental mean update equivalent to Q-learning with α = 1/n, appropriate for a stationary bandit.

### 6.4 Action Selection (ε-Greedy)

```
ε = 0.15   (15% exploration)

if random() < ε:
    pick random strategy
    (beginners: exclude CHALLENGE; advanced: exclude EXPLAIN)
else:
    pick argmax Q(strategy)
```

Q-values are initialised at 0.5 (optimistic) to encourage early exploration of all strategies.

### 6.5 Policy Improvement Evidence

The policy_stats table persists Q-values across sessions.  The `/RL Policy Monitor` tab in the Gradio UI displays the current Q-table, allowing the team to observe which strategy the agent has learned to prefer for the current learner population.

---

## 7. Safety and Security Measures

| Measure | Implementation | Location |
|---|---|---|
| **Input validation** | `validate_user_prompt()` — max length 8000 chars, regex for 8 injection patterns | `shape_safety.py` |
| **Code sandbox** | AST scan blocks 10 dangerous stdlib modules + 5 banned builtins; execution in stripped namespace; 5s timeout | `shape_tools.py` + `shape_safety.py` |
| **Boundary enforcement** | `agent_scope_reminder()` returned for out-of-scope requests; LLM system prompt explicitly states domain limits | `shape_safety.py` |
| **Fallback strategies** | `fallback_response(context)` on APIError or tool failure; lesson submission validation before DB write | `shape_safety.py` |
| **Transparency** | Every system prompt ends with: "I cannot browse the internet, access external files, or answer questions unrelated to the curriculum." | `shape_agent_core.py` |

---

## 8. Evaluation Strategy & Metrics

### 8.1 Pre/Post Assessment

Each learner completes a 5-question multiple-choice assessment at the start and end of the course interaction.  Both scores are stored in the `assessments` table.

**Score formula:**

```
Score(learner) = (Correct answers) / 5  × 100%
Learning Gain  = Post_Score − Pre_Score
```

### 8.2 Hint Dependency Index (HDI)

```
HDI = (Turns with ≥1 hint) / (Total turns)
```
Lower HDI over time indicates reduced dependency on hints → stronger understanding.

### 8.3 Strategy Effectiveness Score (SES)

```
SES(strategy) = Q-value for that strategy (from policy_stats)
```
Strategies with SES > 0.7 are considered high-effectiveness for the current learner population.

### 8.4 Success Criteria

| Metric | Target |
|---|---|
| Average Learning Gain | ≥ 20 percentage points post−pre |
| Hint Dependency Index (final 10 turns) | ≤ 0.30 |
| User session length (turns) | ≥ 5 per session |
| Policy convergence | Dominant strategy Q-value ≥ 0.65 after 50 turns |

---

## 9. Resource Requirements

| Resource | Specification |
|---|---|
| **Compute** | Local laptop or Google Colab (CPU runtime) |
| **LLM API** | OpenAI `gpt-3.5-turbo` (~$0.002 / 1K tokens; target < $5 total for development) |
| **Storage** | SQLite file — < 10 MB for 1000 turns |
| **Dependencies** | openai ≥ 1.30, gradio ≥ 4.36, python-dotenv ≥ 1.0 |
| **Python** | 3.10+ (uses `match`-compatible type hints) |

**Token optimisation strategies:**
- Curriculum context capped at 3 excerpts × 600 chars
- Tool output capped at 2000 chars
- `max_tokens=600` on all LLM calls
- Caching: repeated identical queries within a session reuse the last retrieval result (future enhancement)

---

## 10. Development Timeline

| Milestone | Owner | Target Date |
|---|---|---|
| Project Proposal submitted | Michael Rivas | Nov 13, 2026 |
| DB schema + safety layer complete | Michael Rivas / Olu | Nov 17, 2026 |
| Tool 1 (code runner) + Tool 2 (retrieval) functional | Olu | Nov 20, 2026 |
| RL policy module + DB persistence | Taki | Nov 22, 2026 |
| Orchestrator 8-step loop integrated | Michael Rivas | Nov 26, 2026 |
| Gradio UI with Lesson Builder live | Cherluk | Nov 28, 2026 |
| Curriculum seeded (≥ 10 lessons) | Cherluk / Olu | Nov 30, 2026 |
| Pre/post assessment module | Taki | Dec 2, 2026 |
| End-to-end testing + bug fixes | All | Dec 3–4, 2026 |
| Demo video recorded | All | Dec 5, 2026 |
| Final report written | All | Dec 6, 2026 |
| **Final submission** | Michael Rivas | **Dec 7, 2026** |

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OpenAI API key cost overrun | Medium | High | Use `gpt-3.5-turbo`; set OpenAI billing hard cap at $10; implement token count logging |
| Student code crashes the runner | High | Low | 5-second thread timeout; restricted namespace; AST pre-scan catches most malicious patterns |
| Gradio session state loss | Medium | Medium | All state persisted to SQLite; Gradio state dict is a thin pointer — session survives page refresh if learner re-enters name |
| LLM hallucination of incorrect code answers | Medium | Medium | Tool 2 injects authoritative curriculum before LLM generates; Evaluator persona checks work |
| Team member unavailability | Low | High | Each module is independent; any member can run `shape_main.py --cli` to test without the UI |
| RL policy slow to converge | Low | Low | Optimistic initialisation (Q₀ = 0.5) ensures exploration of all strategies in early sessions |

---

## Appendix — File Naming Compliance

All deliverables follow the required format `TypeOfDeliverable__Group_ITAI2376_14562.FileExtension`:

- `FN_Proposal_MichaelRivas_Group_ITAI2376_14562.pdf` ← this document
- `FN_Report_MichaelRivas_Group_ITAI2376_14562.pdf` ← due Dec 7
- `FN_Demo_MichaelRivas_Group_ITAI2376_14562.mp4` ← due Dec 7

Git repository link to be submitted on Canvas per project instructions.
