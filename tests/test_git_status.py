"""Tests for Atlas._quick_git_status (issue #97)."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from atlas.runtime import Atlas


def _make_atlas(tmp_path) -> Atlas:
    (tmp_path / ".atlas").mkdir()
    return Atlas(project_dir=str(tmp_path))


def _mock_git(responses: dict[str, str]):
    """Return a mock for subprocess.check_output that maps git subcommands to outputs."""
    def _check_output(cmd, **kwargs):
        # Use the second git subcommand as the key (e.g. "rev-parse", "diff")
        key = cmd[1] if len(cmd) > 1 else ""
        # For rev-list use a more specific key
        if cmd[1:3] == ["rev-list", "--left-right"]:
            key = "rev-list"
        val = responses.get(key, "")
        if val is None:
            raise subprocess.CalledProcessError(128, cmd)
        return val.encode()
    return _check_output


class TestQuickGitStatus:
    def test_returns_empty_when_not_in_git_repo(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        with patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(128, "git")):
            result = atlas._quick_git_status()
        assert result == ""

    def test_returns_empty_when_branch_is_HEAD(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        with patch("subprocess.check_output", side_effect=_mock_git({"rev-parse": "HEAD"})):
            result = atlas._quick_git_status()
        assert result == ""

    def test_branch_name_in_output(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        with patch("subprocess.check_output", side_effect=_mock_git({
            "rev-parse": "main",
            "rev-list": "",
            "diff": "",
        })):
            result = atlas._quick_git_status()
        assert "main" in result

    def test_ahead_count_shown(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        with patch("subprocess.check_output", side_effect=_mock_git({
            "rev-parse": "feat/auth",
            "rev-list": "2\t0",
            "diff": "",
        })):
            result = atlas._quick_git_status()
        assert "2 ahead" in result

    def test_behind_count_shown(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        with patch("subprocess.check_output", side_effect=_mock_git({
            "rev-parse": "feat/auth",
            "rev-list": "0\t3",
            "diff": "",
        })):
            result = atlas._quick_git_status()
        assert "3 behind" in result

    def test_ahead_and_behind_shown(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        with patch("subprocess.check_output", side_effect=_mock_git({
            "rev-parse": "feat/auth",
            "rev-list": "1\t2",
            "diff": "",
        })):
            result = atlas._quick_git_status()
        assert "1 ahead" in result
        assert "2 behind" in result

    def test_unstaged_files_shown(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        with patch("subprocess.check_output", side_effect=_mock_git({
            "rev-parse": "main",
            "rev-list": "0\t0",
            "diff": "src/auth.py\nsrc/utils.py",
        })):
            result = atlas._quick_git_status()
        assert "Modified (unstaged)" in result
        assert "src/auth.py" in result

    def test_staged_files_shown(self, tmp_path):
        atlas = _make_atlas(tmp_path)

        call_count = [0]
        def _staged_mock(cmd, **kwargs):
            if cmd[1] == "rev-parse":
                return b"main"
            if cmd[1:3] == ["rev-list", "--left-right"]:
                return b"0\t0"
            if cmd[1] == "diff":
                if "--cached" in cmd:
                    return b"src/auth.py"
                return b""
            return b""

        with patch("subprocess.check_output", side_effect=_staged_mock):
            result = atlas._quick_git_status()
        assert "Staged" in result
        assert "src/auth.py" in result

    def test_clean_branch_no_suffix(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        with patch("subprocess.check_output", side_effect=_mock_git({
            "rev-parse": "main",
            "rev-list": "0\t0",
            "diff": "",
        })):
            result = atlas._quick_git_status()
        assert "ahead" not in result
        assert "behind" not in result
        assert "main" in result

    def test_no_upstream_still_shows_branch(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        with patch("subprocess.check_output", side_effect=_mock_git({
            "rev-parse": "feature/new",
            "rev-list": "",  # no upstream
            "diff": "",
        })):
            result = atlas._quick_git_status()
        assert "feature/new" in result
        assert result != ""
