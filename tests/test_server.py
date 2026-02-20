"""Tests for atlas.server (build_description, build_input_help, _serialise, routing)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from atlas.server import (
    _serialise,
    build_description,
    build_input_help,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_atlas(initialized: bool = True, modules: list[str] | None = None) -> MagicMock:
    """Return a mock Atlas with controllable state."""
    atlas = MagicMock()
    atlas.is_initialized = initialized
    atlas.installed_modules = modules or []
    atlas.router = MagicMock()
    atlas.router.find_all_with_command.return_value = []
    atlas.router.has_category_installed.return_value = False
    return atlas


# ---------------------------------------------------------------------------
# build_description — not initialised
# ---------------------------------------------------------------------------


class TestBuildDescriptionNotInitialized:
    def test_returns_short_prompt_when_not_initialized(self):
        atlas = _make_atlas(initialized=False)
        desc = build_description(atlas)
        assert "atlas init" in desc

    def test_returns_string(self):
        atlas = _make_atlas(initialized=False)
        assert isinstance(build_description(atlas), str)

    def test_mentions_atlas_list(self):
        atlas = _make_atlas(initialized=False)
        assert "atlas list" in build_description(atlas)


# ---------------------------------------------------------------------------
# build_description — initialised, base verbs
# ---------------------------------------------------------------------------


class TestBuildDescriptionInitialized:
    def test_includes_modules_line(self):
        atlas = _make_atlas(modules=["python", "ruff"])
        desc = build_description(atlas)
        assert "python" in desc
        assert "ruff" in desc

    def test_includes_base_verbs(self):
        atlas = _make_atlas(modules=["python"])
        desc = build_description(atlas)
        for verb in ("add", "create", "edit", "remove", "list", "sync"):
            assert verb in desc

    def test_no_just_when_no_check_or_test_commands(self):
        atlas = _make_atlas(modules=["python"])
        atlas.router.find_all_with_command.return_value = []
        desc = build_description(atlas)
        assert "just" not in desc

    def test_just_appears_when_check_command_found(self):
        atlas = _make_atlas(modules=["python", "ruff"])

        def find_cmd(cmd: str) -> list:
            return ["ruff"] if cmd == "check" else []

        atlas.router.find_all_with_command.side_effect = find_cmd
        desc = build_description(atlas)
        assert "just" in desc

    def test_just_appears_when_test_command_found(self):
        atlas = _make_atlas(modules=["python", "pytest"])

        def find_cmd(cmd: str) -> list:
            return ["pytest"] if cmd == "test" else []

        atlas.router.find_all_with_command.side_effect = find_cmd
        desc = build_description(atlas)
        assert "just" in desc

    def test_vcs_appears_when_vcs_category_installed(self):
        atlas = _make_atlas(modules=["python", "git"])
        atlas.router.has_category_installed.side_effect = lambda cat: cat == "vcs"
        desc = build_description(atlas)
        assert "vcs" in desc

    def test_crud_appears_when_platform_category_installed(self):
        atlas = _make_atlas(modules=["python", "github"])
        atlas.router.has_category_installed.side_effect = lambda cat: cat == "platform"
        desc = build_description(atlas)
        assert "crud" in desc

    def test_vcs_absent_when_no_vcs_category(self):
        atlas = _make_atlas(modules=["python"])
        atlas.router.has_category_installed.return_value = False
        desc = build_description(atlas)
        assert "vcs" not in desc

    def test_crud_absent_when_no_platform_category(self):
        atlas = _make_atlas(modules=["python"])
        atlas.router.has_category_installed.return_value = False
        desc = build_description(atlas)
        assert "crud" not in desc

    def test_mentions_retrieve_syntax(self):
        atlas = _make_atlas(modules=["python"])
        desc = build_description(atlas)
        assert "Retrieve" in desc or "retrieve" in desc

    def test_mentions_help(self):
        atlas = _make_atlas(modules=["python"])
        desc = build_description(atlas)
        assert "list" in desc


# ---------------------------------------------------------------------------
# build_input_help — not initialised
# ---------------------------------------------------------------------------


class TestBuildInputHelpNotInitialized:
    def test_returns_string(self):
        atlas = _make_atlas(initialized=False)
        assert isinstance(build_input_help(atlas), str)

    def test_mentions_init(self):
        atlas = _make_atlas(initialized=False)
        assert "init" in build_input_help(atlas)

    def test_mentions_list(self):
        atlas = _make_atlas(initialized=False)
        assert "list" in build_input_help(atlas)


# ---------------------------------------------------------------------------
# build_input_help — initialised
# ---------------------------------------------------------------------------


class TestBuildInputHelpInitialized:
    def test_returns_string(self):
        atlas = _make_atlas(modules=["python"])
        assert isinstance(build_input_help(atlas), str)

    def test_includes_first_module(self):
        atlas = _make_atlas(modules=["python", "ruff"])
        result = build_input_help(atlas)
        assert "python" in result

    def test_mentions_passthrough_syntax(self):
        atlas = _make_atlas(modules=["python"])
        result = build_input_help(atlas)
        assert "--" in result

    def test_works_with_empty_module_list(self):
        atlas = _make_atlas(modules=[])
        result = build_input_help(atlas)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# _serialise
# ---------------------------------------------------------------------------


class TestSerialise:
    def test_string_passthrough(self):
        assert _serialise("hello") == "hello"

    def test_empty_string(self):
        assert _serialise("") == ""

    def test_dict_to_json(self):
        result = _serialise({"ok": True, "data": "x"})
        parsed = json.loads(result)
        assert parsed["ok"] is True

    def test_dict_with_nested(self):
        d = {"modules": ["a", "b"], "count": 2}
        result = _serialise(d)
        parsed = json.loads(result)
        assert parsed["modules"] == ["a", "b"]

    def test_other_type_to_str(self):
        assert _serialise(42) == "42"

    def test_none_to_str(self):
        assert _serialise(None) == "None"

    def test_list_to_str(self):
        # Lists are not str or dict — falls through to str()
        result = _serialise([1, 2, 3])
        assert "1" in result
