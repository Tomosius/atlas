"""Tests for atlas.core.runner."""

from __future__ import annotations

import os
import stat
import sys

import pytest

from atlas.core.runner import resolve_tool, run_task


# ---------------------------------------------------------------------------
# resolve_tool
# ---------------------------------------------------------------------------


def _make_executable(path: str) -> None:
    """Write a dummy executable script at *path*."""
    with open(path, "w") as f:
        f.write(f"#!{sys.executable}\nprint('hi')\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class TestResolveTool:
    def test_returns_venv_path_when_present(self, tmp_path):
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        tool_path = venv_bin / "ruff"
        _make_executable(str(tool_path))
        result = resolve_tool("ruff", str(tmp_path))
        assert result == str(tool_path)

    def test_returns_node_modules_path_when_present(self, tmp_path):
        node_bin = tmp_path / "node_modules" / ".bin"
        node_bin.mkdir(parents=True)
        tool_path = node_bin / "eslint"
        _make_executable(str(tool_path))
        result = resolve_tool("eslint", str(tmp_path))
        assert result == str(tool_path)

    def test_venv_takes_priority_over_node_modules(self, tmp_path):
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        node_bin = tmp_path / "node_modules" / ".bin"
        node_bin.mkdir(parents=True)
        venv_tool = venv_bin / "mytool"
        node_tool = node_bin / "mytool"
        _make_executable(str(venv_tool))
        _make_executable(str(node_tool))
        result = resolve_tool("mytool", str(tmp_path))
        assert result == str(venv_tool)

    def test_falls_back_to_system_path_when_no_local(self, tmp_path):
        # "python3" or "python" should always be on PATH in a test environment
        result = resolve_tool("python3", str(tmp_path))
        assert result is not None
        assert "python" in result

    def test_returns_none_when_tool_not_found_anywhere(self, tmp_path):
        result = resolve_tool("__nonexistent_tool_xyz__", str(tmp_path))
        assert result is None

    def test_non_executable_venv_file_not_returned(self, tmp_path):
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        # Write a file but don't make it executable
        non_exec = venv_bin / "notexec"
        non_exec.write_text("not a script")
        result = resolve_tool("notexec", str(tmp_path))
        assert result is None

    def test_returns_string_or_none(self, tmp_path):
        result = resolve_tool("python3", str(tmp_path))
        assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# run_task
# ---------------------------------------------------------------------------


class TestRunTask:
    def test_successful_command_returns_ok(self, tmp_path):
        result = run_task("echo_test", f"{sys.executable} -c \"print('hello')\"", str(tmp_path))
        assert result["ok"] is True

    def test_successful_command_has_task_name(self, tmp_path):
        result = run_task("mytask", f"{sys.executable} -c \"print('hello')\"", str(tmp_path))
        assert result["task"] == "mytask"

    def test_successful_command_captures_stdout(self, tmp_path):
        result = run_task("echo_test", f"{sys.executable} -c \"print('hello world')\"", str(tmp_path))
        assert "hello world" in result["output"]

    def test_successful_command_has_returncode_zero(self, tmp_path):
        result = run_task("zero", f"{sys.executable} -c \"import sys; sys.exit(0)\"", str(tmp_path))
        assert result["returncode"] == 0

    def test_failing_command_still_returns_ok_result(self, tmp_path):
        # A command that exits non-zero is still "ok" from runner's perspective
        result = run_task("fail", f"{sys.executable} -c \"import sys; sys.exit(1)\"", str(tmp_path))
        assert result["ok"] is True
        assert result["returncode"] == 1

    def test_stderr_captured_in_output(self, tmp_path):
        result = run_task(
            "stderr_test",
            f"{sys.executable} -c \"import sys; sys.stderr.write('err output')\"",
            str(tmp_path),
        )
        assert "err output" in result["output"]

    def test_empty_command_returns_error(self, tmp_path):
        result = run_task("empty", "", str(tmp_path))
        assert result["ok"] is False
        assert result["error"] == "INVALID_ARGUMENT"

    def test_whitespace_only_command_returns_error(self, tmp_path):
        result = run_task("blank", "   ", str(tmp_path))
        assert result["ok"] is False
        assert result["error"] == "INVALID_ARGUMENT"

    def test_nonexistent_executable_returns_error(self, tmp_path):
        result = run_task("bad", "__totally_nonexistent_binary__", str(tmp_path))
        assert result["ok"] is False
        assert result["error"] == "INVALID_ARGUMENT"

    def test_timeout_returns_error(self, tmp_path):
        result = run_task(
            "slow",
            f"{sys.executable} -c \"import time; time.sleep(60)\"",
            str(tmp_path),
            timeout=1,
        )
        assert result["ok"] is False
        assert result["error"] == "INVALID_ARGUMENT"
        assert "timed out" in result["detail"]

    def test_runs_in_project_dir(self, tmp_path):
        # Command lists cwd; should be tmp_path
        result = run_task(
            "cwd_test",
            f"{sys.executable} -c \"import os; print(os.getcwd())\"",
            str(tmp_path),
        )
        assert result["ok"] is True
        assert str(tmp_path) in result["output"]

    def test_result_has_ok_key(self, tmp_path):
        result = run_task("check", f"{sys.executable} -c \"pass\"", str(tmp_path))
        assert "ok" in result

    def test_result_has_output_key_on_success(self, tmp_path):
        result = run_task("check", f"{sys.executable} -c \"pass\"", str(tmp_path))
        assert "output" in result

    def test_result_has_returncode_key_on_success(self, tmp_path):
        result = run_task("check", f"{sys.executable} -c \"pass\"", str(tmp_path))
        assert "returncode" in result
