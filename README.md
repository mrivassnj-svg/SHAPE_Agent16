# SHAPE Agent 16 — Interactive Learning Companion

**Course:** ITAI2376 — Artificial Intelligence  
**Section:** 14562  
**Institution:** Houston Community College  
**Project Option:** Option 4 — Interactive Learning Companion  

---

## Team Members

| Name | Role |
|---|---|
| **Michael Rivas** | Integration, Project Coordination, System Architecture |
| **Cherluk** | Learning Design and Instructional Experience |
| **Olu** | Agent Behavior, Interaction Engineering, Tool Integration |
| **Taki** | Evaluation, Testing, and Learning Analytics |

---

## Project Overview

SHAPE Agent 16 is a multi-agent interactive learning companion that teaches programming
and AI concepts to students at any level.  The system adapts its communication style
and teaching strategy to each individual learner, supports live curriculum authoring by
non-coding team members through a Gradio web interface, and applies reinforcement learning
(contextual bandit with ε-greedy policy) to improve its instructional choices over time.

### Key Features

- **Multi-agent architecture** — four specialised sub-agent personas: Instructor, Debugger,
  Evaluator, Learning Strategist
- **8-Step Reasoning Cycle** — ReAct pattern with Chain-of-Thought scratchpad
- **Tool 1: Python Classroom Exercise Runner** — AST-validated safe code execution
- **Tool 2: Local Keyword Retrieval** — searches instructor-curated curriculum in SQLite
- **RL Policy** — contextual bandit over 5 teaching strategies with Q-value updates
- **Live Lesson Builder** — Gradio UI tab lets non-coders add curriculum entries instantly
- **Safety layer** — prompt injection detection, sandbox enforcement, fallback strategies

---

## Repository Structure

```
SHAPE_Agent16/
├── src/
│   ├── shape_agent_core.py       ← 8-step orchestrator + sub-agent personas
│   ├── shape_db_handler.py       ← SQLite layer (shape.db)
│   ├── shape_tools.py            ← Tool 1 (code runner) + Tool 2 (retrieval)
│   ├── shape_safety.py           ← Input validation + safety filters
│   ├── shape_rl_policy.py        ← ε-greedy contextual bandit policy
│   ├── shape_gradio_ui.py        ← Gradio web interface
│   └── shape_main.py             ← Entry point (UI / CLI / seed / policy)
├── data/
│   └── shape.db                  ← SQLite database (auto-created on first run)
├── tests/
│   └── (test files go here)
├── docs/
│   └── FN_Proposal_MichaelRivas_Group_ITAI2376_14562.md
├── curriculum/
│   └── (export CSVs of curriculum go here)
├── requirements.txt
└── README.md
```

---

## Setup Instructions

### Prerequisites

- Python 3.10 or newer
- A **free** Groq API key — sign up at **https://console.groq.com** (no credit card required, takes ~1 minute)

---

### Option A — One-command setup (Kali / Debian / Ubuntu)

```bash
git clone https://github.com/<your-org>/SHAPE_Agent16.git
cd SHAPE_Agent16
bash setup.sh      # creates .venv, installs deps, asks for your key, seeds DB
bash run.sh        # launches the Gradio UI at http://localhost:7860
```

---

### Option B — Manual setup (any OS)

#### 1. Clone the repository

```bash
git clone https://github.com/<your-org>/SHAPE_Agent16.git
cd SHAPE_Agent16
```

#### 2. Create a virtual environment

> ⚠️ On Kali/Debian you **must** use a venv — system-wide `pip install` is blocked by PEP 668.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Get a free Groq API key

1. Go to **https://console.groq.com**
2. Sign up (Google / GitHub / email — no credit card)
3. Click **API Keys → Create API Key**
4. Copy the key (starts with `gsk_...`)

#### 5. Set the key

```bash
export GROQ_API_KEY="gsk_..."    # Linux / macOS (add to ~/.zshrc to make permanent)
```

Or create a `.env` file in the project root (never commit this file):

```
GROQ_API_KEY=gsk_...
SHAPE_MODEL=llama-3.3-70b-versatile
```

#### 6. Seed the database with starter lessons

```bash
python src/shape_main.py --seed
```

#### 7. Launch the web UI

```bash
python src/shape_main.py
# Open http://localhost:7860 in your browser
```

#### 8. (Alternative) CLI mode — useful for Google Colab terminals

```bash
python src/shape_main.py --cli
```

---

## Google Colab Quick Start

```python
# Cell 1 — install
!pip install groq gradio python-dotenv

# Cell 2 — clone repo
!git clone https://github.com/<your-org>/SHAPE_Agent16.git
%cd SHAPE_Agent16

# Cell 3 — set key and run
import os
os.environ["GROQ_API_KEY"] = "gsk_..."   # paste your free Groq key here

!python src/shape_main.py --seed          # seed lessons
!python src/shape_main.py                 # launches UI — follow the public URL printed
```

---

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | **Required.** Free key from https://console.groq.com |
| `SHAPE_API_KEY` | — | Alias for `GROQ_API_KEY` |
| `SHAPE_MODEL` | `llama-3.3-70b-versatile` | Groq model to use. `llama-3.1-8b-instant` is faster/lighter. |

---

## Naming Convention Compliance

All deliverables follow the required convention `TypeOfDeliverable__Group_ITAI2376_14562.FileExtension`:

| File | Deliverable type |
|---|---|
| `FN_Proposal_MichaelRivas_Group_ITAI2376_14562.pdf` | Project Proposal |
| `FN_Report_MichaelRivas_Group_ITAI2376_14562.pdf` | Final Report |
| `FN_Demo_MichaelRivas_Group_ITAI2376_14562.mp4` | Demo Video |

---

## License

For educational use only — Houston Community College ITAI2376.
