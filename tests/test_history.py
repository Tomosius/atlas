"""Tests for history reading and relative timestamps (issue #96)."""

from __future__ import annotations

import json
import os
import time

import pytest

from atlas.runtime import _relative_time, Atlas


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_history(atlas_dir, lines: list[dict]) -> None:
    path = os.path.join(str(atlas_dir), "history.jsonl")
    with open(path, "w") as f:
        for record in lines:
            f.write(json.dumps(record) + "\n")


def _make_atlas(tmp_path) -> Atlas:
    atlas_dir = tmp_path / ".atlas"
    atlas_dir.mkdir()
    return Atlas(project_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# _relative_time
# ---------------------------------------------------------------------------


class TestRelativeTime:
    def test_just_now(self):
        assert _relative_time(1000.0, 1050.0) == "just now"

    def test_minutes_ago(self):
        assert _relative_time(1000.0, 1090.0) == "1m ago"

    def test_hours_ago(self):
        assert _relative_time(1000.0, 1000.0 + 7200) == "2h ago"

    def test_days_ago(self):
        assert _relative_time(1000.0, 1000.0 + 172800) == "2d ago"

    def test_boundary_one_hour(self):
        assert _relative_time(1000.0, 1000.0 + 3600) == "1h ago"


# ---------------------------------------------------------------------------
# _read_recent_history
# ---------------------------------------------------------------------------


class TestReadRecentHistory:
    def test_returns_empty_when_no_file(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        assert atlas._read_recent_history() == []

    def test_returns_entries_in_order(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        now = time.time()
        records = [
            {"ts": now - 7200, "summary": "first op"},
            {"ts": now - 3600, "summary": "second op"},
            {"ts": now - 60, "summary": "third op"},
        ]
        _write_history(tmp_path / ".atlas", records)
        result = atlas._read_recent_history()
        assert len(result) == 3
        assert result[0]["summary"] == "first op"
        assert result[2]["summary"] == "third op"

    def test_respects_limit(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        now = time.time()
        records = [{"ts": now - i * 60, "summary": f"op {i}"} for i in range(10, 0, -1)]
        _write_history(tmp_path / ".atlas", records)
        result = atlas._read_recent_history(limit=3)
        assert len(result) == 3
        # Last 3 entries in the file
        assert result[-1]["summary"] == "op 1"

    def test_skips_malformed_lines(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        now = time.time()
        path = os.path.join(str(tmp_path / ".atlas"), "history.jsonl")
        # _write_history only produces valid JSON, so we write directly here
        with open(path, "w") as f:
            f.write('{"ts": ' + str(now - 60) + ', "summary": "good op"}\n')
            f.write("not valid json\n")
        result = atlas._read_recent_history()
        assert len(result) == 1
        assert result[0]["summary"] == "good op"

    def test_skips_entries_without_summary(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        now = time.time()
        records = [
            {"ts": now - 120, "summary": ""},
            {"ts": now - 60, "summary": "has summary"},
        ]
        _write_history(tmp_path / ".atlas", records)
        result = atlas._read_recent_history()
        assert len(result) == 1
        assert result[0]["summary"] == "has summary"

    def test_ago_field_is_relative_string(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        now = time.time()
        _write_history(tmp_path / ".atlas", [{"ts": now - 7200, "summary": "ran tests"}])
        result = atlas._read_recent_history()
        assert len(result) == 1
        assert result[0]["ago"] == "2h ago"
        assert result[0]["summary"] == "ran tests"

    def test_missing_ts_field_uses_question_mark(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _write_history(tmp_path / ".atlas", [{"summary": "op with no timestamp"}])
        result = atlas._read_recent_history()
        assert len(result) == 1
        assert result[0]["ago"] == "?"
        assert result[0]["summary"] == "op with no timestamp"

    def test_returns_empty_when_file_unreadable(self, tmp_path, monkeypatch):
        atlas = _make_atlas(tmp_path)
        import builtins
        real_open = builtins.open
        def mock_open(path, *args, **kwargs):
            if "history.jsonl" in str(path):
                raise OSError("permission denied")
            return real_open(path, *args, **kwargs)
        # Create the file so the isfile() check passes
        (tmp_path / ".atlas" / "history.jsonl").write_text('{"ts": 1.0, "summary": "x"}\n')
        monkeypatch.setattr(builtins, "open", mock_open)
        result = atlas._read_recent_history()
        assert result == []


# ---------------------------------------------------------------------------
# _append_history
# ---------------------------------------------------------------------------


class TestAppendHistory:
    def test_creates_history_file_when_absent(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._append_history("test operation")
        path = tmp_path / ".atlas" / "history.jsonl"
        assert path.is_file()

    def test_writes_valid_json_line(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._append_history("did something")
        path = tmp_path / ".atlas" / "history.jsonl"
        line = path.read_text().strip()
        record = json.loads(line)
        assert record["summary"] == "did something"
        assert isinstance(record["ts"], float)

    def test_ts_is_approximately_now(self, tmp_path):
        before = time.time()
        atlas = _make_atlas(tmp_path)
        atlas._append_history("timed op")
        after = time.time()
        path = tmp_path / ".atlas" / "history.jsonl"
        record = json.loads(path.read_text().strip())
        assert before <= record["ts"] <= after

    def test_appends_multiple_entries(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._append_history("first")
        atlas._append_history("second")
        atlas._append_history("third")
        path = tmp_path / ".atlas" / "history.jsonl"
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) == 3
        summaries = [json.loads(l)["summary"] for l in lines]
        assert summaries == ["first", "second", "third"]

    def test_does_not_rewrite_existing_entries(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        path = tmp_path / ".atlas" / "history.jsonl"
        path.write_text(json.dumps({"ts": 1000.0, "summary": "existing"}) + "\n")
        atlas._append_history("new entry")
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) == 2
        assert json.loads(lines[0])["summary"] == "existing"
        assert json.loads(lines[1])["summary"] == "new entry"

    def test_skips_when_not_initialized(self, tmp_path):
        """No .atlas/ dir — should not crash and not create file."""
        atlas = Atlas(project_dir=str(tmp_path))
        atlas._append_history("should not write")
        assert not (tmp_path / ".atlas" / "history.jsonl").exists()


# ---------------------------------------------------------------------------
# add_modules writes history
# ---------------------------------------------------------------------------


class TestAddModulesHistory:
    def test_history_written_when_module_installed(self, tmp_path):
        from unittest.mock import patch
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}, "detected": {}}
        atlas._registry = {"modules": {}}

        fake_ok = {"ok": True, "module": "ruff"}
        with patch("atlas.runtime.install_module", return_value=fake_ok):
            atlas.add_modules(["ruff"])

        path = tmp_path / ".atlas" / "history.jsonl"
        assert path.is_file()
        record = json.loads(path.read_text().strip())
        assert "ruff" in record["summary"]

    def test_no_history_when_all_installs_fail(self, tmp_path):
        from unittest.mock import patch
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}, "detected": {}}
        atlas._registry = {"modules": {}}

        fake_fail = {"ok": False, "error": "NOT_FOUND"}
        with patch("atlas.runtime.install_module", return_value=fake_fail):
            atlas.add_modules(["nonexistent"])

        path = tmp_path / ".atlas" / "history.jsonl"
        assert not path.is_file()
