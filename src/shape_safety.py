"""
shape_safety.py
---------------
Input validation, boundary enforcement, and fallback strategies for
SHAPE Agent 16 — Interactive Learning Companion.

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

import ast
import re
from dataclasses import dataclass

# ── Banned patterns (code execution safety) ───────────────────────────────────
_BANNED_IMPORTS = {
    "os", "sys", "subprocess", "shutil", "socket", "ctypes", "multiprocessing",
    "signal", "resource", "pty", "fcntl", "termios", "importlib",
}
_BANNED_BUILTINS = {"exec", "eval", "compile", "__import__", "open", "input"}

# ── Prompt injection keywords ──────────────────────────────────────────────────
_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"disregard (your )?system prompt",
    r"you are now",
    r"pretend (you are|to be)",
    r"jailbreak",
    r"DAN mode",
    r"bypass",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


@dataclass
class SafetyResult:
    safe: bool
    reason: str = ""


def validate_user_prompt(text: str) -> SafetyResult:
    """Screen free-text user input for prompt injection attempts."""
    if not text or not text.strip():
        return SafetyResult(False, "Empty input.")
    if len(text) > 8_000:
        return SafetyResult(False, "Input exceeds maximum length (8000 chars).")
    if _INJECTION_RE.search(text):
        return SafetyResult(False, "Input resembles a prompt-injection attempt and was blocked.")
    return SafetyResult(True)


def validate_python_code(code: str) -> SafetyResult:
    """
    Statically analyse student-submitted Python with AST before running it.
    Rejects dangerous imports, banned built-ins, and syntax errors.
    """
    # 1. Parse
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return SafetyResult(False, f"Syntax error: {exc}")

    # 2. Walk AST for banned patterns
    for node in ast.walk(tree):
        # banned imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else ([node.module] if node.module else [])
            )
            for name in names:
                root = name.split(".")[0]
                if root in _BANNED_IMPORTS:
                    return SafetyResult(False, f"Import of '{root}' is not permitted in the classroom sandbox.")

        # banned built-ins called as functions
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _BANNED_BUILTINS:
                return SafetyResult(False, f"Built-in '{func.id}()' is not permitted in the classroom sandbox.")
            if isinstance(func, ast.Attribute) and func.attr in _BANNED_BUILTINS:
                return SafetyResult(False, f"Built-in '{func.attr}()' is not permitted in the classroom sandbox.")

    return SafetyResult(True)


def validate_lesson_content(title: str, content: str, keywords: list[str]) -> SafetyResult:
    """Basic validation for instructor-authored lesson submissions."""
    if not title or not title.strip():
        return SafetyResult(False, "Lesson title is required.")
    if not content or len(content.strip()) < 50:
        return SafetyResult(False, "Lesson content must be at least 50 characters.")
    if not keywords:
        return SafetyResult(False, "At least one keyword is required.")
    return SafetyResult(True)


def fallback_response(context: str = "") -> str:
    """
    Return a graceful fallback message when the LLM or a tool is unavailable.
    """
    base = (
        "I'm sorry — I ran into an issue and couldn't complete that step. "
        "Here's what I can tell you about what happened: "
    )
    if context:
        return base + context
    return (
        base + "an external service (the language model or a tool) did not respond as expected. "
        "Please try again in a moment. If the problem continues, notify your instructor."
    )


def agent_scope_reminder() -> str:
    """Return the standard out-of-scope notice to the user."""
    return (
        "That request is outside my current scope. I'm a programming and AI learning companion "
        "designed to help you understand course concepts, run practice exercises, and track "
        "your progress. I cannot browse the internet, access external files, or answer questions "
        "unrelated to the curriculum."
    )
