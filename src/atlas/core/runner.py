"""Task execution via subprocess with local-first tool resolution."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess

from atlas.core.errors import error_result, ok_result


def resolve_tool(tool_name: str, project_dir: str) -> str | None:
    """Return the path to *tool_name*, preferring project-local installations.

    Resolution cascade:
    1. ``<project_dir>/.venv/bin/<tool>`` (Python virtual environment)
    2. ``<project_dir>/node_modules/.bin/<tool>`` (Node.js local packages)
    3. ``shutil.which(<tool>)`` (system PATH)
    4. None — tool not found

    Atlas NEVER installs packages; it only informs when a tool is missing.
    """
    candidates = [
        os.path.join(project_dir, ".venv", "bin", tool_name),
        os.path.join(project_dir, "node_modules", ".bin", tool_name),
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    return shutil.which(tool_name)


def run_task(
    task_name: str,
    command: str,
    project_dir: str,
    timeout: int = 60,
) -> dict:
    """Execute *command* as a shell command in *project_dir*.

    Returns ``ok_result(task=task_name, output=..., returncode=...)`` on
    completion (even when the command exits non-zero, so the caller can
    decide how to handle failures).

    Returns ``error_result`` when:
    - *command* is empty
    - The executable is not found (exit code 127)
    - The command times out (exit code 124)
    """
    if not command or not command.strip():
        return error_result("INVALID_ARGUMENT", f"No command for task '{task_name}'")

    try:
        args = shlex.split(command)
    except ValueError as exc:
        return error_result("INVALID_ARGUMENT", f"Cannot parse command: {exc}")

    try:
        proc = subprocess.run(
            args,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = (proc.stdout + proc.stderr).strip()
        return ok_result(task=task_name, output=output, returncode=proc.returncode)
    except FileNotFoundError:
        return error_result(
            "INVALID_ARGUMENT",
            f"Executable not found for task '{task_name}': {args[0]}",
        )
    except subprocess.TimeoutExpired:
        return error_result(
            "INVALID_ARGUMENT",
            f"Task '{task_name}' timed out after {timeout}s",
        )


def find_rule_hint(code: str, module_rules: dict) -> str:
    """Return the rule hint for *code* from *module_rules*, or empty string."""
    return module_rules.get(code, "")


def augment_errors(output: str, module_rules: dict) -> str:
    """Scan tool output for error codes and append relevant rule hints inline.

    Looks for patterns like E501, F401, W291 (letter + 3-4 digits).
    If a matching rule hint exists in *module_rules*, appends it on the
    next line with a 📎 prefix.
    """
    if not module_rules:
        return output
    lines = output.split("\n")
    augmented: list[str] = []
    for line in lines:
        augmented.append(line)
        code_match = re.search(r'\b([A-Z]\d{3,4})\b', line)
        if code_match:
            hint = find_rule_hint(code_match.group(1), module_rules)
            if hint:
                augmented.append(f"    \U0001f4ce {hint}")
    return "\n".join(augmented)
