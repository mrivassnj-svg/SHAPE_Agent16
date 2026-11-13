"""
shape_rpg_questions.py
----------------------
Python question bank for SHAPE Agent 16 RPG.

Every question is a dict with:
  id          – unique string
  zone        – which world zone this question belongs to
  tier        – 1 (easy) / 2 (medium) / 3 (hard)
  xp          – XP awarded on correct answer
  damage      – damage dealt to enemy on correct answer
  prompt      – question text shown to player
  choices     – list of 4 option strings  (A/B/C/D)
  answer      – correct choice index 0-3
  explanation – shown after answer is revealed

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

from __future__ import annotations
import random

QUESTIONS: list[dict] = [

    # ── ZONE 1: SYNTAX SWAMP (tier 1) ────────────────────────────────────────
    {
        "id": "q001", "zone": "Syntax Swamp", "tier": 1, "xp": 20, "damage": 25,
        "prompt": "Which symbol starts a comment in Python?",
        "choices": ["//", "/*", "#", "--"],
        "answer": 2,
        "explanation": "Python uses # for single-line comments.",
    },
    {
        "id": "q002", "zone": "Syntax Swamp", "tier": 1, "xp": 20, "damage": 25,
        "prompt": "What does print('Hello') do?",
        "choices": [
            "Stores 'Hello' in a variable",
            "Outputs Hello to the screen",
            "Creates a file called Hello",
            "Raises a SyntaxError",
        ],
        "answer": 1,
        "explanation": "print() writes its argument to standard output.",
    },
    {
        "id": "q003", "zone": "Syntax Swamp", "tier": 1, "xp": 20, "damage": 25,
        "prompt": "Which of these is a valid variable name in Python?",
        "choices": ["2name", "my-var", "_score", "class"],
        "answer": 2,
        "explanation": "Variable names can start with _ or a letter, not a digit or hyphen, and 'class' is a reserved keyword.",
    },
    {
        "id": "q004", "zone": "Syntax Swamp", "tier": 1, "xp": 20, "damage": 25,
        "prompt": "What value does bool('') return?",
        "choices": ["True", "False", "None", "Error"],
        "answer": 1,
        "explanation": "An empty string is falsy in Python.",
    },
    {
        "id": "q005", "zone": "Syntax Swamp", "tier": 1, "xp": 25, "damage": 30,
        "prompt": "What is the output of: print(type(3.14))?",
        "choices": ["<class 'int'>", "<class 'str'>", "<class 'float'>", "<class 'number'>"],
        "answer": 2,
        "explanation": "3.14 is a float literal.",
    },

    # ── ZONE 2: LOOP LAGOON (tier 1-2) ───────────────────────────────────────
    {
        "id": "q010", "zone": "Loop Lagoon", "tier": 1, "xp": 25, "damage": 30,
        "prompt": "How many times does this print?\n\nfor i in range(3):\n    print(i)",
        "choices": ["2", "3", "4", "0"],
        "answer": 1,
        "explanation": "range(3) produces 0, 1, 2 — three iterations.",
    },
    {
        "id": "q011", "zone": "Loop Lagoon", "tier": 1, "xp": 25, "damage": 30,
        "prompt": "Which keyword immediately exits a loop?",
        "choices": ["exit", "stop", "break", "end"],
        "answer": 2,
        "explanation": "break terminates the innermost loop immediately.",
    },
    {
        "id": "q012", "zone": "Loop Lagoon", "tier": 2, "xp": 35, "damage": 40,
        "prompt": "What does continue do inside a loop?",
        "choices": [
            "Exits the loop",
            "Skips the rest of the current iteration and goes to the next",
            "Restarts the loop from the beginning",
            "Pauses execution",
        ],
        "answer": 1,
        "explanation": "continue skips remaining code in the current iteration.",
    },
    {
        "id": "q013", "zone": "Loop Lagoon", "tier": 2, "xp": 35, "damage": 40,
        "prompt": "What is the output?\n\nx = 0\nwhile x < 3:\n    x += 1\nprint(x)",
        "choices": ["0", "2", "3", "4"],
        "answer": 2,
        "explanation": "Loop runs while x<3, incrementing each time. When x=3 condition is False, loop ends.",
    },
    {
        "id": "q014", "zone": "Loop Lagoon", "tier": 2, "xp": 35, "damage": 40,
        "prompt": "What does range(2, 8, 2) produce?",
        "choices": ["[2, 4, 6, 8]", "[2, 4, 6]", "[2, 3, 4, 5, 6, 7]", "[0, 2, 4, 6]"],
        "answer": 1,
        "explanation": "range(start=2, stop=8, step=2) → 2, 4, 6 (stop is exclusive).",
    },

    # ── ZONE 3: FUNCTION FORTRESS (tier 2) ───────────────────────────────────
    {
        "id": "q020", "zone": "Function Fortress", "tier": 2, "xp": 40, "damage": 45,
        "prompt": "What keyword defines a function?",
        "choices": ["func", "define", "def", "function"],
        "answer": 2,
        "explanation": "Python uses def to define a function.",
    },
    {
        "id": "q021", "zone": "Function Fortress", "tier": 2, "xp": 40, "damage": 45,
        "prompt": "What does this return?\n\ndef add(a, b=10):\n    return a + b\n\nadd(5)",
        "choices": ["5", "10", "15", "Error"],
        "answer": 2,
        "explanation": "b defaults to 10, so add(5) returns 5 + 10 = 15.",
    },
    {
        "id": "q022", "zone": "Function Fortress", "tier": 2, "xp": 40, "damage": 45,
        "prompt": "What is a function that calls itself called?",
        "choices": ["A loop", "A lambda", "A recursive function", "A generator"],
        "answer": 2,
        "explanation": "A function that calls itself is recursive.",
    },
    {
        "id": "q023", "zone": "Function Fortress", "tier": 2, "xp": 45, "damage": 50,
        "prompt": "What does *args allow in a function?",
        "choices": [
            "Only keyword arguments",
            "A variable number of positional arguments",
            "Arguments with default values",
            "Type-annotated arguments",
        ],
        "answer": 1,
        "explanation": "*args collects any number of positional arguments into a tuple.",
    },

    # ── ZONE 4: LIST LABYRINTH (tier 2) ──────────────────────────────────────
    {
        "id": "q030", "zone": "List Labyrinth", "tier": 2, "xp": 35, "damage": 40,
        "prompt": "What index is the LAST element of a list?",
        "choices": ["0", "len(list)", "-1", "last"],
        "answer": 2,
        "explanation": "Python supports negative indexing; -1 is always the last element.",
    },
    {
        "id": "q031", "zone": "List Labyrinth", "tier": 2, "xp": 35, "damage": 40,
        "prompt": "What does .append() do to a list?",
        "choices": [
            "Removes the last element",
            "Adds an element to the end",
            "Sorts the list",
            "Reverses the list",
        ],
        "answer": 1,
        "explanation": "list.append(x) adds x to the end of the list.",
    },
    {
        "id": "q032", "zone": "List Labyrinth", "tier": 2, "xp": 40, "damage": 45,
        "prompt": "What is the output?\n\nmy_list = [1, 2, 3]\nprint(my_list[1:3])",
        "choices": ["[1, 2]", "[2, 3]", "[1, 2, 3]", "[3]"],
        "answer": 1,
        "explanation": "Slicing [1:3] returns indices 1 and 2 (stop is exclusive).",
    },
    {
        "id": "q033", "zone": "List Labyrinth", "tier": 2, "xp": 40, "damage": 45,
        "prompt": "What does [x*2 for x in range(4)] produce?",
        "choices": ["[0, 2, 4, 6]", "[2, 4, 6, 8]", "[1, 2, 3, 4]", "[0, 1, 2, 3]"],
        "answer": 0,
        "explanation": "List comprehension: 0*2=0, 1*2=2, 2*2=4, 3*2=6.",
    },

    # ── ZONE 5: DICT DUNGEON (tier 2-3) ──────────────────────────────────────
    {
        "id": "q040", "zone": "Dict Dungeon", "tier": 2, "xp": 40, "damage": 45,
        "prompt": "How do you access value for key 'name' in dict d?",
        "choices": ["d.name", "d[name]", "d['name']", "d->name"],
        "answer": 2,
        "explanation": "Dictionary keys are accessed with square brackets and quotes for string keys.",
    },
    {
        "id": "q041", "zone": "Dict Dungeon", "tier": 3, "xp": 55, "damage": 60,
        "prompt": "What does .get('key', 'default') return if key is missing?",
        "choices": ["None", "KeyError", "'default'", "False"],
        "answer": 2,
        "explanation": ".get() returns the second argument if the key doesn't exist.",
    },
    {
        "id": "q042", "zone": "Dict Dungeon", "tier": 3, "xp": 55, "damage": 60,
        "prompt": "What is the output?\n\nd = {'a': 1, 'b': 2}\nprint(len(d))",
        "choices": ["1", "2", "3", "Error"],
        "answer": 1,
        "explanation": "len() on a dict returns the number of key-value pairs.",
    },

    # ── ZONE 6: ERROR CAVERN — BOSS ZONE (tier 3) ────────────────────────────
    {
        "id": "q050", "zone": "Error Cavern", "tier": 3, "xp": 70, "damage": 75,
        "prompt": "Which error is raised when you access a list index that doesn't exist?",
        "choices": ["KeyError", "ValueError", "IndexError", "TypeError"],
        "answer": 2,
        "explanation": "IndexError is raised for out-of-range list/tuple indices.",
    },
    {
        "id": "q051", "zone": "Error Cavern", "tier": 3, "xp": 70, "damage": 75,
        "prompt": "What does try/except do?",
        "choices": [
            "Runs code faster",
            "Catches and handles exceptions without crashing",
            "Prevents the program from running",
            "Deletes error messages",
        ],
        "answer": 1,
        "explanation": "try/except lets you handle exceptions gracefully.",
    },
    {
        "id": "q052", "zone": "Error Cavern", "tier": 3, "xp": 80, "damage": 80,
        "prompt": "What error does 1 + '1' raise?",
        "choices": ["ValueError", "SyntaxError", "TypeError", "NameError"],
        "answer": 2,
        "explanation": "You cannot add int and str — Python raises TypeError.",
    },
    {
        "id": "q053", "zone": "Error Cavern", "tier": 3, "xp": 80, "damage": 80,
        "prompt": "What does finally: do in a try block?",
        "choices": [
            "Runs only if no exception occurred",
            "Runs only if an exception occurred",
            "Always runs, exception or not",
            "Raises a new exception",
        ],
        "answer": 2,
        "explanation": "finally always executes regardless of whether an exception was raised.",
    },
]


def get_zone_questions(zone: str) -> list[dict]:
    """Return all questions for a specific zone, shuffled."""
    qs = [q for q in QUESTIONS if q["zone"] == zone]
    random.shuffle(qs)
    return qs


def get_random_question(zone: str | None = None, tier: int | None = None) -> dict:
    """Return a random question, optionally filtered by zone and/or tier."""
    pool = QUESTIONS
    if zone:
        pool = [q for q in pool if q["zone"] == zone]
    if tier:
        pool = [q for q in pool if q["tier"] == tier]
    return random.choice(pool) if pool else random.choice(QUESTIONS)


ZONES_IN_ORDER = [
    "Syntax Swamp",
    "Loop Lagoon",
    "Function Fortress",
    "List Labyrinth",
    "Dict Dungeon",
    "Error Cavern",
]

ZONE_ENEMIES: dict[str, list[dict]] = {
    "Syntax Swamp": [
        {"name": "Syntax Slime",   "hp": 60,  "attack": 10, "sprite": "slime",   "xp_reward": 30},
        {"name": "Comment Crab",   "hp": 80,  "attack": 12, "sprite": "crab",    "xp_reward": 40},
    ],
    "Loop Lagoon": [
        {"name": "Infinite Imp",   "hp": 100, "attack": 15, "sprite": "imp",     "xp_reward": 55},
        {"name": "While Wyrm",     "hp": 120, "attack": 18, "sprite": "wyrm",    "xp_reward": 65},
    ],
    "Function Fortress": [
        {"name": "Recursion Wraith","hp": 140, "attack": 20, "sprite": "wraith",  "xp_reward": 80},
        {"name": "Lambda Lich",    "hp": 160, "attack": 22, "sprite": "lich",    "xp_reward": 90},
    ],
    "List Labyrinth": [
        {"name": "Index Error Ogre","hp": 180, "attack": 25, "sprite": "ogre",    "xp_reward": 100},
        {"name": "Slice Specter",  "hp": 200, "attack": 28, "sprite": "specter", "xp_reward": 110},
    ],
    "Dict Dungeon": [
        {"name": "KeyError Knight","hp": 220, "attack": 30, "sprite": "knight",  "xp_reward": 120},
        {"name": "Hash Hydra",     "hp": 250, "attack": 33, "sprite": "hydra",   "xp_reward": 135},
    ],
    "Error Cavern": [
        {"name": "Exception Drake","hp": 300, "attack": 38, "sprite": "drake",   "xp_reward": 160},
        {"name": "BOSS: NullByte", "hp": 500, "attack": 45, "sprite": "boss",    "xp_reward": 300},
    ],
}
