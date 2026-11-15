"""SHAPE Agent 16 — tools.

Tool 1: run_code_tool — controlled Python exercise runner.
Tool 2: retrieve_lesson_tool — lesson / HCC resource retrieval.

LIMITATION, stated plainly: the AST check + restricted namespace below is
a CLASSROOM exercise runner, not a hardened security sandbox. It blocks
the obvious escapes (imports other than math/random, open/eval/exec,
os/sys/subprocess, file access, dunder access), but it must NOT be used
to run arbitrary untrusted public code. Never describe it as secure.
"""
import ast
import io
import sys
from contextlib import redirect_stdout

from .store import LESSONS, RESOURCES, get_lesson

ALLOWED_IMPORTS = {"math", "random"}
BANNED_NAMES = {"open", "eval", "exec", "compile", "__import__", "input",
                "os", "sys", "subprocess", "socket", "pathlib", "globals",
                "locals", "vars", "getattr", "setattr", "delattr", "breakpoint"}
ALLOWED_BUILTINS = {"print": print, "len": len, "range": range, "str": str,
                    "int": int, "float": float, "bool": bool, "list": list,
                    "dict": dict, "set": set, "tuple": tuple, "sum": sum,
                    "min": min, "max": max, "abs": abs, "round": round,
                    "enumerate": enumerate, "zip": zip, "sorted": sorted,
                    "reversed": reversed, "type": type,
                    # __import__ is needed so `import math` / `import random`
                    # (the only imports the AST check allows) can run at all.
                    # Learner code may NOT call __import__ directly: the AST
                    # check bans the name '__import__', and only math/random
                    # pass the import check, so this cannot be used to reach
                    # os/sys/subprocess.
                    "__import__": __import__}


def _check_code(code):
    """Return an error string, or None if the code passes the checks."""
    if not isinstance(code, str) or not code.strip():
        return "No code submitted. Write some Python code first."
    if len(code) > 5000:
        return "Code is too long (over 5000 characters)."
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"SyntaxError: {e.msg} (line {e.lineno})"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    return f"Import not allowed: '{alias.name}'. Only math and random are allowed."
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                return f"Import not allowed: '{node.module}'. Only math and random are allowed."
        if isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            return f"Not allowed in exercises: '{node.id}'."
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return "Dunder (double-underscore) access is not allowed."
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            return "global / nonlocal are not allowed in exercises."
    return None


def run_code_tool(code, expected_output=None):
    """Run learner code in a restricted namespace and compare stdout.

    Returns dict: passed, stdout, expected, error, hint.
    The runner is a classroom aid, NOT a hardened sandbox.
    """
    error = _check_code(code)
    if error:
        return {"passed": False, "stdout": "", "expected": expected_output or "",
                "error": error, "hint": "Fix the problem above, then submit again."}
    buf = io.StringIO()
    safe_globals = {"__builtins__": dict(ALLOWED_BUILTINS)}
    try:
        with redirect_stdout(buf):
            exec(compile(code, "<exercise>", "exec"), safe_globals)
    except Exception as e:  # noqa: BLE001 — learner errors are the point
        return {"passed": False, "stdout": buf.getvalue(),
                "expected": expected_output or "",
                "error": f"{type(e).__name__}: {e}",
                "hint": "Read the error message: it usually names the line and the problem."}
    stdout = buf.getvalue()
    if expected_output is None:
        return {"passed": True, "stdout": stdout, "expected": "",
                "error": "", "hint": "It ran without an error."}
    passed = stdout.strip() == str(expected_output).strip()
    hint = ""
    if not passed:
        hint = (f"Your output was {stdout.strip()!r}, expected {str(expected_output).strip()!r}. "
                "Check spelling, spacing and line breaks — they must match exactly.")
    return {"passed": passed, "stdout": stdout, "expected": str(expected_output),
            "error": "", "hint": hint}


def retrieve_lesson_tool(query):
    """Search the curated lesson + HCC resource index by keyword.

    Returns dict: found, lesson (or None), resources (list), message.
    No web access is used; this searches only the project's own index.
    """
    if not isinstance(query, str) or not query.strip():
        return {"found": False, "lesson": None, "resources": [],
                "message": "Give me a topic to look up, e.g. 'loops' or 'functions'."}
    q = query.strip().lower()
    lesson = None
    for item in LESSONS:
        hay = (item["id"] + " " + item["title"] + " " + item["concept"]).lower()
        if q in hay or any(word in hay for word in q.split() if len(word) > 3):
            lesson = {"id": item["id"], "title": item["title"],
                      "concept": item["concept"], "example": item["example"]}
            break
    resources = [r for r in RESOURCES if q in (r["title"] + " " + r["topic"]).lower()
                 or any(word in (r["title"] + " " + r["topic"]).lower()
                        for word in q.split() if len(word) > 3)]
    if lesson is None and not resources:
        return {"found": False, "lesson": None, "resources": [],
                "message": f"No lesson or HCC resource matched '{query}'. Try: print, variables, loops, functions, lists, CNN, transformers, reinforcement learning."}
    return {"found": True, "lesson": lesson, "resources": resources,
            "message": "Found in the SHAPE lesson / HCC resource index (HCC pages may need an HCC login)."}
