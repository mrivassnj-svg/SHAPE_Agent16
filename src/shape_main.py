"""
shape_main.py
-------------
Entry point for SHAPE Agent 16 — Interactive Learning Companion.

Usage:
    # Launch Gradio web UI (default)
    python shape_main.py

    # CLI interactive mode (no browser needed, useful for Colab terminals)
    python shape_main.py --cli

    # Seed the database with starter curriculum lessons
    python shape_main.py --seed

    # Print current RL policy stats
    python shape_main.py --policy

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

import argparse
import uuid
import sys
import os

# Make sure src/ siblings are on the path when running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import shape_db_handler as db
from shape_rl_policy import policy_summary


# ── Starter curriculum seed data ──────────────────────────────────────────────

SEED_LESSONS = [
    {
        "topic": "Python Basics",
        "level": "beginner",
        "title": "Variables and Data Types",
        "content": (
            "In Python, a variable is a name that refers to a value stored in memory. "
            "Python supports several built-in data types: int (whole numbers), float (decimals), "
            "str (text), bool (True/False), list (ordered collection), dict (key-value pairs). "
            "You do not need to declare the type — Python infers it automatically.\n\n"
            "Example:\n"
            "  name = 'Alice'   # str\n"
            "  age  = 21        # int\n"
            "  gpa  = 3.8       # float\n"
            "  enrolled = True  # bool\n\n"
            "Practice: Create a variable for each type and print them."
        ),
        "keywords": ["variable", "variables", "int", "float", "str", "bool", "type", "types", "data"],
        "author": "Michael Rivas",
    },
    {
        "topic": "Python Basics",
        "level": "beginner",
        "title": "For Loops and Iteration",
        "content": (
            "A for loop repeats a block of code for each item in a sequence.\n\n"
            "Syntax:\n"
            "  for item in sequence:\n"
            "      # code block\n\n"
            "The range() function generates a sequence of numbers:\n"
            "  for i in range(5):   # 0,1,2,3,4\n"
            "      print(i)\n\n"
            "You can also iterate over a list:\n"
            "  fruits = ['apple', 'banana', 'cherry']\n"
            "  for fruit in fruits:\n"
            "      print(fruit)\n\n"
            "Practice: Write a loop that prints the squares of numbers 1–10."
        ),
        "keywords": ["loop", "loops", "for", "iteration", "range", "iterate"],
        "author": "Cherluk",
    },
    {
        "topic": "Python Basics",
        "level": "beginner",
        "title": "Functions",
        "content": (
            "A function is a reusable block of code that performs a specific task.\n\n"
            "Define with def:\n"
            "  def greet(name):\n"
            "      return f'Hello, {name}!'\n\n"
            "Call it:\n"
            "  message = greet('Bob')\n"
            "  print(message)  # Hello, Bob!\n\n"
            "Functions can have default parameters:\n"
            "  def power(base, exp=2):\n"
            "      return base ** exp\n\n"
            "Practice: Write a function that takes a list of numbers and returns their average."
        ),
        "keywords": ["function", "functions", "def", "return", "parameter", "argument", "call"],
        "author": "Olu",
    },
    {
        "topic": "AI Concepts",
        "level": "intermediate",
        "title": "Supervised vs Unsupervised Learning",
        "content": (
            "Machine learning is broadly divided into supervised and unsupervised learning.\n\n"
            "Supervised Learning:\n"
            "  - Training data has labelled examples (input → expected output)\n"
            "  - Goal: learn a mapping from inputs to outputs\n"
            "  - Examples: classification, regression\n"
            "  - Algorithms: decision trees, SVM, neural networks\n\n"
            "Unsupervised Learning:\n"
            "  - Training data has NO labels\n"
            "  - Goal: discover hidden structure or patterns\n"
            "  - Examples: clustering, dimensionality reduction\n"
            "  - Algorithms: K-Means, PCA, autoencoders\n\n"
            "Key difference: presence of labelled training data."
        ),
        "keywords": ["supervised", "unsupervised", "learning", "classification", "clustering", "ml", "machine"],
        "author": "Taki",
    },
    {
        "topic": "AI Concepts",
        "level": "intermediate",
        "title": "Reinforcement Learning Fundamentals",
        "content": (
            "Reinforcement Learning (RL) is about an agent learning to make decisions by "
            "interacting with an environment to maximise cumulative reward.\n\n"
            "Key components:\n"
            "  Agent     – the learner / decision maker\n"
            "  Environment – what the agent interacts with\n"
            "  State (s) – current situation\n"
            "  Action (a)– choice made by the agent\n"
            "  Reward (r)– feedback signal from environment\n"
            "  Policy (π)– mapping from states to actions\n\n"
            "Q-Learning update rule:\n"
            "  Q(s,a) ← Q(s,a) + α [r + γ·max Q(s',a') − Q(s,a)]\n\n"
            "SHAPE uses a simplified contextual bandit (no state transitions) "
            "with epsilon-greedy exploration."
        ),
        "keywords": ["reinforcement", "rl", "reward", "policy", "q-learning", "agent", "bandit", "epsilon"],
        "author": "Michael Rivas",
    },
]


def seed_database() -> None:
    db.init_db()
    for lesson in SEED_LESSONS:
        existing = db.search_lessons(lesson["keywords"], level=lesson["level"])
        titles   = [e["title"] for e in existing]
        if lesson["title"] not in titles:
            db.add_lesson(**lesson)
            print(f"  Seeded: {lesson['title']}")
        else:
            print(f"  Skipped (already exists): {lesson['title']}")
    print("Database seeding complete.")


# ── CLI interactive mode ───────────────────────────────────────────────────────

def cli_mode() -> None:
    from shape_agent_core import run_turn

    db.init_db()
    print("\n=== SHAPE Agent 16 — CLI Mode ===")
    print("Type 'quit' to exit.\n")
    display_name = input("Enter your name: ").strip() or "learner"
    learner_id   = display_name.lower().replace(" ", "_")
    session_id   = str(uuid.uuid4())
    db.upsert_learner(learner_id, display_name)

    turn = 0
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue
        turn += 1
        reply = run_turn(learner_id, user_input, session_id, turn)
        print(f"\nSHAPE Agent:\n{reply}\n{'─'*60}")

    db.close_session(session_id)
    print("\nSession ended. Goodbye!")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="SHAPE Agent 16 launcher")
    parser.add_argument("--cli",    action="store_true", help="Run in terminal CLI mode")
    parser.add_argument("--seed",   action="store_true", help="Seed DB with starter lessons")
    parser.add_argument("--policy", action="store_true", help="Print current RL policy stats")
    args = parser.parse_args()

    db.init_db()

    if args.seed:
        seed_database()
        return

    if args.policy:
        print(policy_summary())
        return

    if args.cli:
        cli_mode()
        return

    # Default: Gradio UI
    from shape_gradio_ui import build_app
    app = build_app()
    app.launch(share=False, server_name="0.0.0.0", server_port=7860)


if __name__ == "__main__":
    main()
