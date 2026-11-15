"""
shape_tools.py
--------------
Tool integrations for SHAPE Agent 16:

  Tool 1 – Python Classroom Exercise Runner
      Validates student code with the AST safety filter, then executes it
      inside a restricted namespace with a hard wall-clock timeout.

  Tool 2 – Local Keyword Retrieval Tool
      Searches the curriculum table in shape.db for lesson content matching
      keywords extracted from the learner's question.

Both tools return a ToolResult dataclass so the orchestrator can branch on
success/failure without fragile string parsing.

Group: ITAI2376_14562
Members: Michael Rivas, Cherluk, Olu, Taki
"""

import io
import textwrap
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field
from typing import Any

from shape_safety import validate_python_code, fallback_response
from shape_db_handler import search_lessons

EXEC_TIMEOUT_SECONDS = 5       # maximum wall-clock seconds for student code
MAX_OUTPUT_CHARS     = 2_000   # truncate stdout beyond this


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    error:  str = ""
    data:   Any = field(default=None)


# ── Tool 1: Python Classroom Exercise Runner ──────────────────────────────────

def run_python_exercise(code: str) -> ToolResult:
    """
    Safely execute student-submitted Python code.

    Pipeline:
      1. AST safety scan  (shape_safety.validate_python_code)
      2. Compile
      3. Execute inside a restricted namespace with stdout/stderr capture
      4. Return captured output or error message

    The agent uses this tool to:
      - Run solution code and show the learner the output
      - Verify exercise answers against expected output
      - Provide line-level error feedback for debugging tasks
    """
    # Step 1 — safety
    safety = validate_python_code(code)
    if not safety.safe:
        return ToolResult(success=False, error=f"[Safety Block] {safety.reason}")

    # Step 2 — restricted namespace (no builtins beyond a safe whitelist)
    safe_globals: dict = {
        "__builtins__": {
            "print": print, "range": range, "len": len, "int": int,
            "float": float, "str": str, "bool": bool, "list": list,
            "dict": dict, "tuple": tuple, "set": set, "type": type,
            "isinstance": isinstance, "enumerate": enumerate, "zip": zip,
            "map": map, "filter": filter, "sorted": sorted, "abs": abs,
            "min": min, "max": max, "sum": sum, "round": round,
            "True": True, "False": False, "None": None,
        }
    }

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    # Step 3 — timed execution using a thread-based timeout wrapper
    import threading
    result_holder: dict = {"output": None, "error": None}

    def _run() -> None:
        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(compile(code, "<student_code>", "exec"), safe_globals)  # noqa: S102
            result_holder["output"] = stdout_buf.getvalue()
        except Exception:
            result_holder["error"] = traceback.format_exc(limit=5)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=EXEC_TIMEOUT_SECONDS)

    if thread.is_alive():
        return ToolResult(success=False, error="Execution timed out (infinite loop or slow code).")

    if result_holder["error"]:
        return ToolResult(success=False, error=result_holder["error"])

    output = (result_holder["output"] or "").strip()
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n... [output truncated]"
    return ToolResult(success=True, output=output or "(no output)")


# ── Tool 2: Local Keyword Retrieval ──────────────────────────────────────────

def retrieve_curriculum(query: str, learner_level: str | None = None) -> ToolResult:
    """
    Tokenise the free-text query into keywords and search the curriculum DB.

    The agent uses this tool to:
      - Locate instructor-authored lesson content relevant to the learner's question
      - Surface curated examples and explanations before falling back to the LLM
      - Ensure new lessons added through the Gradio UI are immediately discoverable

    How the agent determines when to use this tool:
      - Any user question containing a recognised programming / AI term triggers retrieval
      - The orchestrator checks retrieval first and injects matching lessons into the LLM context

    When the tool fails (empty results):
      - The orchestrator proceeds with LLM-only generation and logs a cache miss
    """
    if not query or not query.strip():
        return ToolResult(success=False, error="Empty query.")

    # Naive keyword extraction — split on non-alphanumeric, lowercase, de-dup
    raw_tokens = set(query.lower().split())
    stopwords  = {"a","an","the","is","are","what","how","why","does","do","i","my","can","to","of"}
    keywords   = [t for t in raw_tokens if t not in stopwords and len(t) > 2]

    if not keywords:
        return ToolResult(success=False, error="No usable keywords extracted from query.")

    try:
        lessons = search_lessons(keywords, level=learner_level)
    except Exception as exc:
        return ToolResult(success=False, error=fallback_response(str(exc)))

    if not lessons:
        return ToolResult(
            success=True,
            output="No matching lessons found in the local curriculum.",
            data=[],
        )

    # Format top-3 results for injection into the LLM context
    snippets = []
    for lesson in lessons[:3]:
        snippets.append(
            f"[Lesson: {lesson['title']} | Level: {lesson['level']}]\n"
            f"{textwrap.shorten(lesson['content'], width=600, placeholder='...')}"
        )

    return ToolResult(
        success=True,
        output="\n\n".join(snippets),
        data=lessons[:3],
    )
