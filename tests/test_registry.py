"""Tests for atlas.core.registry."""

import json

import pytest

from atlas.core.registry import (
    check_conflicts,
    find_module,
    get_dependencies,
    get_recommendations,
    load_module_bundle,
    load_module_rules_md,
    load_registry,
)


# ---------------------------------------------------------------------------
# load_registry
# ---------------------------------------------------------------------------


class TestLoadRegistry:
    def test_valid_file_returns_parsed_dict(self, tmp_path):
        data = {"version": "1.0.0", "modules": {"python": {"category": "language"}}}
        f = tmp_path / "registry.json"
        f.write_text(json.dumps(data))
        result = load_registry(str(f))
        assert result["version"] == "1.0.0"
        assert "python" in result["modules"]

    def test_missing_file_returns_empty_dict(self, tmp_path):
        result = load_registry(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_invalid_json_returns_empty_dict(self, tmp_path):
        f = tmp_path / "registry.json"
        f.write_text("{ not valid json }")
        result = load_registry(str(f))
        assert result == {}

    def test_empty_file_returns_empty_dict(self, tmp_path):
        f = tmp_path / "registry.json"
        f.write_text("")
        result = load_registry(str(f))
        assert result == {}

    def test_directory_path_returns_empty_dict(self, tmp_path):
        # tmp_path is a directory, not a file
        result = load_registry(str(tmp_path))
        assert result == {}

    def test_returns_dict_type(self, tmp_path):
        f = tmp_path / "registry.json"
        f.write_text(json.dumps({"modules": {}}))
        result = load_registry(str(f))
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# find_module
# ---------------------------------------------------------------------------


class TestFindModule:
    def _registry(self):
        return {
            "modules": {
                "python": {"category": "language", "path": "languages/python"},
                "ruff": {"category": "linter", "path": "linters/ruff"},
            }
        }

    def test_found_returns_entry(self):
        entry = find_module(self._registry(), "python")
        assert entry["category"] == "language"

    def test_not_found_returns_empty_dict(self):
        assert find_module(self._registry(), "nonexistent") == {}

    def test_empty_registry_returns_empty_dict(self):
        assert find_module({}, "python") == {}

    def test_missing_modules_key_returns_empty_dict(self):
        assert find_module({"version": "1.0"}, "python") == {}

    def test_returns_dict_type(self):
        result = find_module(self._registry(), "ruff")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# check_conflicts
# ---------------------------------------------------------------------------


class TestCheckConflicts:
    def _registry(self):
        return {
            "modules": {
                "ruff": {"category": "linter", "conflicts_with": ["flake8", "pylint"]},
                "black": {"category": "formatter", "conflicts_with": ["ruff"]},
                "pytest": {"category": "testing"},
            }
        }

    def test_conflict_present_returns_it(self):
        result = check_conflicts(self._registry(), "ruff", ["flake8"])
        assert result == ["flake8"]

    def test_multiple_conflicts_all_returned(self):
        result = check_conflicts(self._registry(), "ruff", ["flake8", "pylint"])
        assert set(result) == {"flake8", "pylint"}

    def test_no_installed_conflict_returns_empty(self):
        result = check_conflicts(self._registry(), "ruff", ["pytest"])
        assert result == []

    def test_empty_installed_returns_empty(self):
        result = check_conflicts(self._registry(), "ruff", [])
        assert result == []

    def test_module_not_in_registry_returns_empty(self):
        result = check_conflicts(self._registry(), "unknown", ["flake8"])
        assert result == []

    def test_module_with_no_conflicts_field_returns_empty(self):
        result = check_conflicts(self._registry(), "pytest", ["ruff"])
        assert result == []

    def test_returns_list_type(self):
        result = check_conflicts(self._registry(), "ruff", ["flake8"])
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# get_dependencies
# ---------------------------------------------------------------------------


class TestGetDependencies:
    def _registry(self):
        return {
            "modules": {
                "django": {"category": "framework", "requires": ["python"]},
                "ruff": {"category": "linter"},
                "pytest": {"category": "testing", "requires": []},
            }
        }

    def test_module_with_deps_returns_list(self):
        result = get_dependencies(self._registry(), "django")
        assert result == ["python"]

    def test_module_with_no_requires_returns_empty(self):
        result = get_dependencies(self._registry(), "ruff")
        assert result == []

    def test_module_with_empty_requires_returns_empty(self):
        result = get_dependencies(self._registry(), "pytest")
        assert result == []

    def test_module_not_in_registry_returns_empty(self):
        result = get_dependencies(self._registry(), "unknown")
        assert result == []

    def test_returns_list_copy_not_reference(self):
        # Mutating the returned list should not affect the registry.
        reg = {"modules": {"django": {"requires": ["python"]}}}
        result = get_dependencies(reg, "django")
        result.append("extra")
        assert reg["modules"]["django"]["requires"] == ["python"]


# ---------------------------------------------------------------------------
# load_module_bundle
# ---------------------------------------------------------------------------


class TestLoadModuleBundle:
    def _registry(self, path="linters/ruff"):
        return {"modules": {"ruff": {"category": "linter", "path": path}}}

    def test_valid_bundle_returns_parsed_dict(self, tmp_path):
        bundle_dir = tmp_path / "linters" / "ruff"
        bundle_dir.mkdir(parents=True)
        data = {"id": "ruff", "category": "linter"}
        (bundle_dir / "module.json").write_text(json.dumps(data))
        result = load_module_bundle("ruff", self._registry(), str(tmp_path))
        assert result["id"] == "ruff"

    def test_missing_module_json_returns_empty_dict(self, tmp_path):
        bundle_dir = tmp_path / "linters" / "ruff"
        bundle_dir.mkdir(parents=True)
        # no module.json written
        result = load_module_bundle("ruff", self._registry(), str(tmp_path))
        assert result == {}

    def test_invalid_json_returns_empty_dict(self, tmp_path):
        bundle_dir = tmp_path / "linters" / "ruff"
        bundle_dir.mkdir(parents=True)
        (bundle_dir / "module.json").write_text("{ bad json }")
        result = load_module_bundle("ruff", self._registry(), str(tmp_path))
        assert result == {}

    def test_module_not_in_registry_returns_empty_dict(self, tmp_path):
        result = load_module_bundle("unknown", self._registry(), str(tmp_path))
        assert result == {}

    def test_registry_entry_missing_path_returns_empty_dict(self, tmp_path):
        reg = {"modules": {"ruff": {"category": "linter"}}}  # no "path"
        result = load_module_bundle("ruff", reg, str(tmp_path))
        assert result == {}

    def test_empty_path_in_entry_returns_empty_dict(self, tmp_path):
        result = load_module_bundle("ruff", self._registry(""), str(tmp_path))
        assert result == {}


# ---------------------------------------------------------------------------
# load_module_rules_md
# ---------------------------------------------------------------------------


class TestLoadModuleRulesMd:
    def _registry(self, path="linters/ruff"):
        return {"modules": {"ruff": {"category": "linter", "path": path}}}

    def test_valid_rules_md_returns_content(self, tmp_path):
        bundle_dir = tmp_path / "linters" / "ruff"
        bundle_dir.mkdir(parents=True)
        (bundle_dir / "rules.md").write_text("# Ruff rules\nUse ruff.")
        result = load_module_rules_md("ruff", self._registry(), str(tmp_path))
        assert result == "# Ruff rules\nUse ruff."

    def test_missing_rules_md_returns_empty_string(self, tmp_path):
        bundle_dir = tmp_path / "linters" / "ruff"
        bundle_dir.mkdir(parents=True)
        result = load_module_rules_md("ruff", self._registry(), str(tmp_path))
        assert result == ""

    def test_module_not_in_registry_returns_empty_string(self, tmp_path):
        result = load_module_rules_md("unknown", self._registry(), str(tmp_path))
        assert result == ""

    def test_registry_entry_missing_path_returns_empty_string(self, tmp_path):
        reg = {"modules": {"ruff": {"category": "linter"}}}
        result = load_module_rules_md("ruff", reg, str(tmp_path))
        assert result == ""

    def test_empty_path_returns_empty_string(self, tmp_path):
        result = load_module_rules_md("ruff", self._registry(""), str(tmp_path))
        assert result == ""

    def test_returns_str_type(self, tmp_path):
        result = load_module_rules_md("ruff", self._registry(), str(tmp_path))
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# get_recommendations
# ---------------------------------------------------------------------------


class TestGetRecommendations:
    def _detection(self, **kwargs):
        defaults = {
            "languages": [],
            "frameworks": [],
            "databases": [],
            "package_manager": "none",
            "existing_tools": [],
            "stack": "",
        }
        defaults.update(kwargs)
        return defaults

    def _reg(self, modules: dict) -> dict:
        return {"modules": modules}

    # --- empty / no-match cases ---

    def test_empty_registry_returns_empty(self):
        assert get_recommendations({}, self._detection()) == []

    def test_no_matching_modules_returns_empty(self):
        reg = self._reg({"django": {"category": "framework"}})
        result = get_recommendations(reg, self._detection(frameworks=[]))
        assert result == []

    # --- language matching ---

    def test_language_module_matched_when_detected(self):
        reg = self._reg({"python": {"category": "language"}})
        result = get_recommendations(reg, self._detection(languages=["python"]))
        assert len(result) == 1
        assert result[0]["name"] == "python"

    def test_language_module_skipped_when_not_detected(self):
        reg = self._reg({"python": {"category": "language"}})
        result = get_recommendations(reg, self._detection(languages=["typescript"]))
        assert result == []

    # --- for_languages filter ---

    def test_for_languages_module_included_when_language_matches(self):
        reg = self._reg({
            "ruff": {"category": "linter", "for_languages": ["python"]},
        })
        result = get_recommendations(reg, self._detection(
            languages=["python"], existing_tools=["ruff"]
        ))
        assert any(r["name"] == "ruff" for r in result)

    def test_for_languages_module_skipped_when_language_absent(self):
        reg = self._reg({
            "ruff": {"category": "linter", "for_languages": ["python"]},
        })
        result = get_recommendations(reg, self._detection(
            languages=["typescript"], existing_tools=["ruff"]
        ))
        assert result == []

    # --- framework matching ---

    def test_framework_module_matched_when_detected(self):
        reg = self._reg({"django": {"category": "framework"}})
        result = get_recommendations(reg, self._detection(frameworks=["django"]))
        assert any(r["name"] == "django" for r in result)

    def test_framework_module_skipped_when_not_detected(self):
        reg = self._reg({"django": {"category": "framework"}})
        result = get_recommendations(reg, self._detection(frameworks=["fastapi"]))
        assert result == []

    # --- database matching ---

    def test_database_module_matched_when_detected(self):
        reg = self._reg({"postgres": {"category": "database"}})
        result = get_recommendations(reg, self._detection(databases=["postgres"]))
        assert any(r["name"] == "postgres" for r in result)

    # --- pkg_manager matching ---

    def test_pkg_manager_matched_by_name(self):
        reg = self._reg({"uv": {"category": "pkg_manager"}})
        result = get_recommendations(reg, self._detection(package_manager="uv"))
        assert any(r["name"] == "uv" for r in result)

    def test_pkg_manager_skipped_when_different(self):
        reg = self._reg({"uv": {"category": "pkg_manager"}})
        result = get_recommendations(reg, self._detection(package_manager="pip"))
        assert result == []

    # --- tool matching via existing_tools ---

    def test_vcs_module_matched_when_in_existing_tools(self):
        reg = self._reg({"git": {"category": "vcs"}})
        result = get_recommendations(reg, self._detection(existing_tools=["git"]))
        assert any(r["name"] == "git" for r in result)

    def test_linter_matched_when_in_existing_tools(self):
        reg = self._reg({"ruff": {"category": "linter"}})
        result = get_recommendations(reg, self._detection(existing_tools=["ruff"]))
        assert any(r["name"] == "ruff" for r in result)

    # --- result shape ---

    def test_result_dicts_have_name_category_reason(self):
        reg = self._reg({"python": {"category": "language"}})
        result = get_recommendations(reg, self._detection(languages=["python"]))
        assert len(result) == 1
        assert set(result[0].keys()) >= {"name", "category", "reason"}

    def test_reason_is_non_empty_string(self):
        reg = self._reg({"python": {"category": "language"}})
        result = get_recommendations(reg, self._detection(languages=["python"]))
        assert isinstance(result[0]["reason"], str)
        assert len(result[0]["reason"]) > 0

    # --- ordering ---

    def test_vcs_before_language_in_output(self):
        reg = self._reg({
            "python": {"category": "language"},
            "git": {"category": "vcs"},
        })
        result = get_recommendations(reg, self._detection(
            languages=["python"], existing_tools=["git"]
        ))
        names = [r["name"] for r in result]
        assert names.index("git") < names.index("python")

    def test_language_before_linter_in_output(self):
        reg = self._reg({
            "python": {"category": "language"},
            "ruff": {"category": "linter", "for_languages": ["python"]},
        })
        result = get_recommendations(reg, self._detection(
            languages=["python"], existing_tools=["ruff"]
        ))
        names = [r["name"] for r in result]
        assert names.index("python") < names.index("ruff")

    # --- dict detection input ---

    def test_accepts_plain_dict_as_detection(self):
        reg = self._reg({"python": {"category": "language"}})
        detection = {"languages": ["python"], "frameworks": [], "databases": [],
                     "package_manager": "none", "existing_tools": [], "stack": ""}
        result = get_recommendations(reg, detection)
        assert any(r["name"] == "python" for r in result)
