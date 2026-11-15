"""SHAPE Agent 16 — data store, lessons and HCC resource index.

SQLite database: shape.db (one name, used consistently everywhere).
Tables: learners, attempts, lessons_done, contributions, policy_state.
"""
import json
import sqlite3
from datetime import date

DB_PATH = "shape.db"

# ---------------------------------------------------------------------------
# HCC resource library — exact URLs/titles from the project brief.
# These pages may require an authenticated HCC account. SHAPE does NOT claim
# to have accessed or extracted content from any restricted page.
# ---------------------------------------------------------------------------
RESOURCES = [
    {"title": "DL Intro", "topic": "Deep Learning Introduction",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/24356286", "notes": "", "source": ""},
    {"title": "DL Toolkit", "topic": "Deep Learning Toolkit",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/24356292", "notes": "", "source": ""},
    {"title": "NN Basics", "topic": "Neural Network Basics",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/24356301", "notes": "", "source": ""},
    {"title": "CNN", "topic": "Convolutional Neural Networks",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/25011377", "notes": "", "source": ""},
    {"title": "Sequence Modeling and NLP", "topic": "Sequence Modeling and Natural Language Processing",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/24356319", "notes": "", "source": ""},
    {"title": "Applications of Transformers and Attention Mechanics", "topic": "Transformers and Attention",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/24356329", "notes": "", "source": ""},
    {"title": "Autoencoders and Applied Variational (VAEs)", "topic": "Autoencoders and VAEs",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/25301433", "notes": "", "source": ""},
    {"title": "Generative Adversarial Networks GANs", "topic": "GANs",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/24356349", "notes": "", "source": ""},
    {"title": "Gen AI with Diffusion Models", "topic": "Diffusion Models",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/24356356", "notes": "", "source": ""},
    {"title": "Reinforcement Learning in AI Agents", "topic": "Reinforcement Learning",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/24356369", "notes": "", "source": ""},
    {"title": "Advanced Agents and Reasoning Models", "topic": "Advanced Agents",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/24356381", "notes": "", "source": ""},
    {"title": "Agent Planning and Orchestration", "topic": "Agent Planning",
     "url": "https://eagleonline.hccs.edu/courses/340456/modules/items/24356400", "notes": "", "source": ""},
]

# Learning pathway (resources -> Agent 16 progression).
PATHWAY = [
    ("1. Deep learning foundations", ["DL Intro", "DL Toolkit"]),
    ("2. Neural networks and CNNs", ["NN Basics", "CNN"]),
    ("3. Sequence modeling and NLP", ["Sequence Modeling and NLP"]),
    ("4. Transformers and attention", ["Applications of Transformers and Attention Mechanics"]),
    ("5. Autoencoders and generative models", ["Autoencoders and Applied Variational (VAEs)", "Generative Adversarial Networks GANs"]),
    ("6. Diffusion models", ["Gen AI with Diffusion Models"]),
    ("7. Reinforcement learning", ["Reinforcement Learning in AI Agents"]),
    ("8. Advanced agents, reasoning, planning, and orchestration", ["Advanced Agents and Reasoning Models", "Agent Planning and Orchestration"]),
]

# ---------------------------------------------------------------------------
# Lessons — Python fundamentals first, before advanced AI-agent concepts.
# ---------------------------------------------------------------------------
LESSONS = [
    {"id": "L1", "title": "Print and Variables",
     "concept": "print() shows text or a value on the screen. A variable is a named box that stores a value, e.g. name = 'Ada'. Use print(name) to see what is inside.",
     "example": "name = 'Ada'\nprint('Hello,', name)",
     "example_output": "Hello, Ada",
     "exercise": "Write code that prints exactly this line:\nHello, SHAPE",
     "expected_output": "Hello, SHAPE",
     "hints": ["Use print() with the text in quotes.",
               "Try: print('Hello, SHAPE') — the comma and spelling must match exactly.",
               "The whole answer is one line: print(\"Hello, SHAPE\")"],
     "concept_check_q": "What does print('Hi') do?",
     "concept_check_a": "shows Hi on the screen"},
    {"id": "L2", "title": "Input and Types",
     "concept": "Every value has a type: int (whole number), float (decimal), str (text), bool (True/False). type() tells you the type. input() always returns a str, so convert it with int() or float() before doing maths.",
     "example": "print(type(42))\nprint(type(3.5))\nprint(type('hi'))",
     "example_output": "<class 'int'>\n<class 'float'>\n<class 'str'>",
     "exercise": "Write code that prints the type of 42.\nExpected output is exactly:\n<class 'int'>",
     "expected_output": "<class 'int'>",
     "hints": ["Use the type() function, then print the result.",
               "Try: print(type(42))",
               "The whole answer is one line: print(type(42))"],
     "concept_check_q": "What type does input() return, even if the user types a number?",
     "concept_check_a": "str"},
    {"id": "L3", "title": "Conditionals",
     "concept": "if / elif / else lets code choose. The condition is True or False. Indentation (4 spaces) shows which lines belong to each branch.",
     "example": "score = 85\nif score >= 80:\n    print('pass')\nelse:\n    print('retry')",
     "example_output": "pass",
     "exercise": "Set x = 7. If x is greater than 5, print 'big', otherwise print 'small'.\nExpected output: big",
     "expected_output": "big",
     "hints": ["Start with x = 7, then an if statement: if x > 5:",
               "Indent the print('big') line by 4 spaces under the if, and add else: with print('small').",
               "x = 7\nif x > 5:\n    print('big')\nelse:\n    print('small')"],
     "concept_check_q": "What does an if statement need after its condition?",
     "concept_check_a": "a colon and an indented block"},
    {"id": "L4", "title": "Loops",
     "concept": "A for loop repeats code for each item. range(3) gives 0, 1, 2. A while loop repeats while a condition is True — make sure it can become False, or it never stops.",
     "example": "for i in range(3):\n    print(i)",
     "example_output": "0\n1\n2",
     "exercise": "Write a loop that prints the numbers 0, 1, 2, each on its own line.",
     "expected_output": "0\n1\n2",
     "hints": ["range(3) gives 0, 1, 2.",
               "Try: for i in range(3): then print(i) on the next, indented line.",
               "for i in range(3):\n    print(i)"],
     "concept_check_q": "What values does range(3) produce?",
     "concept_check_a": "0, 1, 2"},
    {"id": "L5", "title": "Functions",
     "concept": "A function is a named, reusable block: def name(inputs): ... return value. Calling it runs the block. return sends a value back; print only shows it.",
     "example": "def double(n):\n    return n * 2\n\nprint(double(4))",
     "example_output": "8",
     "exercise": "Define a function double(n) that returns n * 2, then print double(4).\nExpected output: 8",
     "expected_output": "8",
     "hints": ["Start with def double(n): and return n * 2 on the indented line.",
               "After the function, add print(double(4)).",
               "def double(n):\n    return n * 2\n\nprint(double(4))"],
     "concept_check_q": "What is the difference between return and print in a function?",
     "concept_check_a": "return sends a value back to the caller; print only shows it"},
    {"id": "L6", "title": "Lists",
     "concept": "A list holds several values in order: nums = [1, 2, 3]. len() counts them, nums[0] is the first item, and sum() adds numbers. Lists can be changed after they are made.",
     "example": "nums = [1, 2, 3]\nprint(len(nums))\nprint(sum(nums))",
     "example_output": "3\n6",
     "exercise": "Make a list nums = [1, 2, 3], then print the sum of its items.\nExpected output: 6",
     "expected_output": "6",
     "hints": ["First make the list: nums = [1, 2, 3]",
               "Then print the sum: print(sum(nums))",
               "nums = [1, 2, 3]\nprint(sum(nums))"],
     "concept_check_q": "What is the first item of [10, 20, 30], and how do you get it?",
     "concept_check_a": "10, with [0]"},
]

# 5-question pre/post assessment (same questions both times, so change is measurable).
ASSESSMENT = [
    {"q": "What does print('Hi') output?", "options": ["Hi", "print", "'Hi'", "Nothing"], "answer": "Hi"},
    {"q": "What is the type of 42 in Python?", "options": ["str", "float", "int", "bool"], "answer": "int"},
    {"q": "x = 7. What does this print? if x > 5: print('big') else: print('small')", "options": ["small", "big", "7", "Error"], "answer": "big"},
    {"q": "How many times does for i in range(3): print(i) print?", "options": ["2", "3", "4", "0"], "answer": "3"},
    {"q": "def double(n): return n * 2 — what is double(4)?", "options": ["4", "6", "8", "n * 2"], "answer": "8"},
]

TEAM = [
    {"first": "Michael Rivas", "full_name": "Michael Rivas", "role": "Integration and Project Coordination"},
    {"first": "Cherluk", "full_name": "", "role": "Learning Design and Instructional Experience"},
    {"first": "Olu", "full_name": "", "role": "Agent Behavior and Interaction Engineering"},
    {"first": "Taki", "full_name": "", "role": "Evaluation, Testing, and Learning Analytics"},
]
MEMBER_NAMES = [m["first"] for m in TEAM]

CONTRIBUTION_FIELDS = ["member", "full_name", "date", "workstream", "category",
                       "task", "contribution", "evidence", "evidence_link",
                       "decisions", "challenges", "outcome", "reflection"]
CATEGORIES = ["Design", "Coding", "Testing", "Reflection"]


def get_lesson(lesson_id):
    for lesson in LESSONS:
        if lesson["id"] == lesson_id:
            return lesson
    return LESSONS[0]


def get_resource(title):
    for r in RESOURCES:
        if r["title"] == title:
            return r
    return None


def init_db(db_path=DB_PATH):
    """Create shape.db and all tables if they do not exist. Safe to re-run."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS learners
        (learner_id TEXT PRIMARY KEY, created TEXT, last_lesson TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS attempts
        (id INTEGER PRIMARY KEY AUTOINCREMENT, learner_id TEXT, lesson_id TEXT,
         code TEXT, passed INTEGER, hints_used INTEGER, reward REAL,
         strategy TEXT, created TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS lessons_done
        (learner_id TEXT, lesson_id TEXT, completed TEXT,
         PRIMARY KEY (learner_id, lesson_id))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS contributions
        (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, full_name TEXT,
         date TEXT, workstream TEXT, category TEXT, task TEXT, contribution TEXT,
         evidence TEXT, evidence_link TEXT, decisions TEXT, challenges TEXT,
         outcome TEXT, reflection TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS policy_state
        (strategy TEXT PRIMARY KEY, q REAL, updated TEXT)""")
    con.commit()
    con.close()
    return db_path


def record_attempt(db_path, learner_id, lesson_id, code, passed, hints_used, reward, strategy):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO learners VALUES (?,?,?)",
                (learner_id, date.today().isoformat(), lesson_id))
    cur.execute("""INSERT INTO attempts
        (learner_id, lesson_id, code, passed, hints_used, reward, strategy, created)
        VALUES (?,?,?,?,?,?,?,?)""",
                (learner_id, lesson_id, code, 1 if passed else 0, hints_used,
                 reward, strategy, date.today().isoformat()))
    if passed:
        cur.execute("INSERT OR IGNORE INTO lessons_done VALUES (?,?,?)",
                    (learner_id, lesson_id, date.today().isoformat()))
    con.commit()
    con.close()


def get_attempts(db_path, learner_id=None):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    if learner_id:
        cur.execute("SELECT * FROM attempts WHERE learner_id=? ORDER BY id", (learner_id,))
    else:
        cur.execute("SELECT * FROM attempts ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows


def progress_summary(db_path, learner_id):
    attempts = get_attempts(db_path, learner_id)
    if not attempts:
        return {"attempts": 0, "correct": 0, "accuracy": 0.0, "hints": 0,
                "lessons_done": 0, "total_reward": 0.0}
    correct = sum(a["passed"] for a in attempts)
    return {"attempts": len(attempts), "correct": correct,
            "accuracy": round(100.0 * correct / len(attempts), 1),
            "hints": sum(a["hints_used"] for a in attempts),
            "lessons_done": len({a["lesson_id"] for a in attempts if a["passed"]}),
            "total_reward": round(sum(a["reward"] for a in attempts), 1)}


def save_contribution(db_path, record):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cols = [c for c in CONTRIBUTION_FIELDS if c in record]
    vals = [record.get(c, "") for c in cols]
    cur.execute(f"INSERT INTO contributions ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)
    con.commit()
    row_id = cur.lastrowid
    con.close()
    return row_id


def get_contributions(db_path, member=None):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    if member:
        cur.execute("SELECT * FROM contributions WHERE member=? ORDER BY id", (member,))
    else:
        cur.execute("SELECT * FROM contributions ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows


def save_policy(db_path, q_table):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    for strategy, q in q_table.items():
        cur.execute("INSERT OR REPLACE INTO policy_state VALUES (?,?,?)",
                    (strategy, float(q), date.today().isoformat()))
    con.commit()
    con.close()


def load_policy(db_path, defaults):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT strategy, q FROM policy_state")
    loaded = dict(cur.fetchall())
    con.close()
    out = dict(defaults)
    out.update({k: float(v) for k, v in loaded.items() if k in out})
    return out


def to_json(obj):
    return json.dumps(obj, indent=2)
