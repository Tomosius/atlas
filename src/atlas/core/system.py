"""System tool detection and command execution utilities."""

import shutil
import subprocess


def run_command(
    cmd: list[str],
    cwd: str | None = None,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """Run a subprocess command and return (returncode, stdout, stderr).

    Returns (127, "", "") if the executable is not found.
    Returns (124, "", "") on timeout.
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, "", ""
    except subprocess.TimeoutExpired:
        return 124, "", ""


def check_tool(name: str) -> bool:
    """Return True if the named tool is available on PATH."""
    return shutil.which(name) is not None


def get_version(name: str, args: list[str] | None = None) -> str:
    """Return the version string for a CLI tool, or 'not found'."""
    if not check_tool(name):
        return "not found"
    cmd = [name] + (args if args is not None else ["--version"])
    code, stdout, stderr = run_command(cmd, timeout=5)
    if code != 0:
        return "not found"
    output = (stdout or stderr).strip()
    return _parse_version(output) if output else "not found"


def _parse_version(output: str) -> str:
    """Extract a version number from a tool's --version output."""
    import re

    match = re.search(r"(\d+\.\d+[\.\d]*)", output)
    return match.group(1) if match else output.split("\n")[0].strip()


def detect_system_tools() -> "SystemTools":
    """Detect versions of common CLI tools on the host system."""
    from atlas.core.models import SystemTools

    return SystemTools(
        python3=get_version("python3"),
        node=get_version("node"),
        uv=get_version("uv"),
        git=get_version("git"),
        docker=get_version("docker"),
        gh=get_version("gh"),
        cargo=get_version("cargo"),
        go=get_version("go", ["version"]),
    )
