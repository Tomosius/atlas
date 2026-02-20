"""Tests for atlas.core.config."""

from __future__ import annotations

import json
import os

import pytest

from atlas.core.config import (
    AtlasConfig,
    _load_json,
    _merge_config,
    load_config,
    save_config,
)


# ---------------------------------------------------------------------------
# AtlasConfig
# ---------------------------------------------------------------------------


class TestAtlasConfig:
    def test_default_retrieve_links_is_empty_dict(self):
        assert AtlasConfig().retrieve_links == {}

    def test_default_ignore_patterns_is_empty_list(self):
        assert AtlasConfig().ignore_patterns == []

    def test_default_detection_overrides_is_empty_dict(self):
        assert AtlasConfig().detection_overrides == {}

    def test_default_package_manager_override_is_empty_string(self):
        assert AtlasConfig().package_manager_override == ""

    def test_default_auto_add_recommendations_is_false(self):
        assert AtlasConfig().auto_add_recommendations is False

    def test_instances_have_independent_mutable_defaults(self):
        a = AtlasConfig()
        b = AtlasConfig()
        a.retrieve_links["python"] = ["ruff"]
        assert b.retrieve_links == {}

    def test_can_set_fields(self):
        cfg = AtlasConfig(package_manager_override="uv", auto_add_recommendations=True)
        assert cfg.package_manager_override == "uv"
        assert cfg.auto_add_recommendations is True


# ---------------------------------------------------------------------------
# _load_json
# ---------------------------------------------------------------------------


class TestLoadJson:
    def test_valid_file_returns_dict(self, tmp_path):
        f = tmp_path / "cfg.json"
        f.write_text(json.dumps({"key": "value"}))
        assert _load_json(str(f)) == {"key": "value"}

    def test_missing_file_returns_empty_dict(self, tmp_path):
        assert _load_json(str(tmp_path / "nonexistent.json")) == {}

    def test_invalid_json_returns_empty_dict(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{ not valid }")
        assert _load_json(str(f)) == {}

    def test_empty_file_returns_empty_dict(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("")
        assert _load_json(str(f)) == {}


# ---------------------------------------------------------------------------
# _merge_config
# ---------------------------------------------------------------------------


class TestMergeConfig:
    def test_scalar_field_replaced(self):
        cfg = AtlasConfig()
        _merge_config(cfg, {"package_manager_override": "uv"})
        assert cfg.package_manager_override == "uv"

    def test_bool_field_replaced(self):
        cfg = AtlasConfig()
        _merge_config(cfg, {"auto_add_recommendations": True})
        assert cfg.auto_add_recommendations is True

    def test_list_field_replaced(self):
        cfg = AtlasConfig()
        _merge_config(cfg, {"ignore_patterns": ["*.pyc", ".venv"]})
        assert cfg.ignore_patterns == ["*.pyc", ".venv"]

    def test_dict_field_merged_not_replaced(self):
        cfg = AtlasConfig(retrieve_links={"python": ["ruff"]})
        _merge_config(cfg, {"retrieve_links": {"typescript": ["eslint"]}})
        assert cfg.retrieve_links == {"python": ["ruff"], "typescript": ["eslint"]}

    def test_dict_field_update_overwrites_existing_key(self):
        cfg = AtlasConfig(retrieve_links={"python": ["ruff"]})
        _merge_config(cfg, {"retrieve_links": {"python": ["black"]}})
        assert cfg.retrieve_links["python"] == ["black"]

    def test_unknown_key_is_silently_skipped(self):
        cfg = AtlasConfig()
        _merge_config(cfg, {"no_such_field": "ignored"})
        assert not hasattr(cfg, "no_such_field")

    def test_empty_data_changes_nothing(self):
        cfg = AtlasConfig(package_manager_override="pip")
        _merge_config(cfg, {})
        assert cfg.package_manager_override == "pip"

    def test_detection_overrides_merged(self):
        cfg = AtlasConfig(detection_overrides={"language": "python"})
        _merge_config(cfg, {"detection_overrides": {"framework": "django"}})
        assert cfg.detection_overrides == {"language": "python", "framework": "django"}


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------


class TestSaveConfig:
    def test_writes_json_file(self, tmp_path):
        path = str(tmp_path / "out" / "config.json")
        save_config({"key": "value"}, path)
        with open(path) as f:
            assert json.load(f) == {"key": "value"}

    def test_creates_parent_directories(self, tmp_path):
        path = str(tmp_path / "deep" / "nested" / "config.json")
        save_config({}, path)
        assert os.path.isfile(path)

    def test_file_ends_with_newline(self, tmp_path):
        path = str(tmp_path / "config.json")
        save_config({"a": 1}, path)
        with open(path) as f:
            content = f.read()
        assert content.endswith("\n")

    def test_json_is_indented(self, tmp_path):
        path = str(tmp_path / "config.json")
        save_config({"key": "value"}, path)
        with open(path) as f:
            content = f.read()
        assert "\n" in content  # indented JSON has newlines


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_returns_atlas_config_instance(self, tmp_path):
        result = load_config(str(tmp_path))
        assert isinstance(result, AtlasConfig)

    def test_defaults_when_no_config_files(self, tmp_path):
        result = load_config(str(tmp_path))
        assert result.retrieve_links == {}
        assert result.ignore_patterns == []
        assert result.package_manager_override == ""
        assert result.auto_add_recommendations is False

    def test_project_config_applied(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        (atlas_dir / "config.json").write_text(
            json.dumps({"package_manager_override": "uv"})
        )
        result = load_config(str(tmp_path))
        assert result.package_manager_override == "uv"

    def test_project_config_with_list(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        (atlas_dir / "config.json").write_text(
            json.dumps({"ignore_patterns": [".venv", "*.pyc"]})
        )
        result = load_config(str(tmp_path))
        assert ".venv" in result.ignore_patterns

    def test_project_config_with_dict_merged(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        (atlas_dir / "config.json").write_text(
            json.dumps({"retrieve_links": {"python": ["ruff"]}})
        )
        result = load_config(str(tmp_path))
        assert result.retrieve_links == {"python": ["ruff"]}

    def test_invalid_project_config_uses_defaults(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        (atlas_dir / "config.json").write_text("{ invalid json }")
        result = load_config(str(tmp_path))
        assert result.package_manager_override == ""

    def test_missing_atlas_dir_uses_defaults(self, tmp_path):
        result = load_config(str(tmp_path))
        assert result.retrieve_links == {}

    def test_unknown_keys_in_project_config_ignored(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        (atlas_dir / "config.json").write_text(
            json.dumps({"unknown_field": "value", "package_manager_override": "pip"})
        )
        result = load_config(str(tmp_path))
        assert result.package_manager_override == "pip"
        assert not hasattr(result, "unknown_field")
