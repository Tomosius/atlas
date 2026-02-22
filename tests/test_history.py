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
