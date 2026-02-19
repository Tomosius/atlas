"""Tests for atlas.core.categories — validate functions and contracts."""

from atlas.core.categories import (
    ALL_CATEGORIES,
    AUTO_CATEGORIES,
    CATEGORY_CONTRACTS,
    CategoryRouter,
    get_contract,
    get_expected_commands,
    get_required_fields,
    get_valid_categories,
    is_auto_category,
    is_valid_category,
    validate_module_against_contract,
    validate_registry_integrity,
)


# ---------------------------------------------------------------------------
# Existing contract helpers (smoke tests — already implemented)
# ---------------------------------------------------------------------------


class TestCategoryContracts:
    def test_13_installable_categories(self):
        assert len(CATEGORY_CONTRACTS) == 13

    def test_2_auto_categories(self):
        assert len(AUTO_CATEGORIES) == 2

    def test_all_categories_count(self):
        assert len(ALL_CATEGORIES) == 15

    def test_language_allows_multiple(self):
        assert CATEGORY_CONTRACTS["language"]["allows_multiple"] is True

    def test_linter_does_not_allow_multiple(self):
        assert CATEGORY_CONTRACTS["linter"]["allows_multiple"] is False

    def test_linter_requires_check_command(self):
        assert "check" in CATEGORY_CONTRACTS["linter"]["expected_commands"]

    def test_formatter_requires_fix_command(self):
        assert "fix" in CATEGORY_CONTRACTS["formatter"]["expected_commands"]

    def test_testing_requires_test_command(self):
        assert "test" in CATEGORY_CONTRACTS["testing"]["expected_commands"]

    def test_vcs_requires_commit_status_diff_log(self):
        expected = {"commit", "status", "diff", "log"}
        assert expected.issubset(set(CATEGORY_CONTRACTS["vcs"]["expected_commands"]))


class TestHelperFunctions:
    def test_get_valid_categories_returns_15(self):
        assert len(get_valid_categories()) == 15

    def test_is_valid_category_known(self):
        assert is_valid_category("language") is True
        assert is_valid_category("linter") is True
        assert is_valid_category("prompt") is True

    def test_is_valid_category_unknown(self):
        assert is_valid_category("nonexistent") is False
        assert is_valid_category("") is False

    def test_is_auto_category_true(self):
        assert is_auto_category("prompt") is True
        assert is_auto_category("runtime") is True

    def test_is_auto_category_false_for_installable(self):
        assert is_auto_category("language") is False
        assert is_auto_category("linter") is False

    def test_get_contract_known(self):
        contract = get_contract("linter")
        assert "required_fields" in contract
        assert "expected_commands" in contract

    def test_get_contract_unknown_returns_empty(self):
        assert get_contract("nonexistent") == {}

    def test_get_required_fields_language(self):
        fields = get_required_fields("language")
        assert "id" in fields
        assert "name" in fields
        assert "category" in fields
        assert "brief" in fields

    def test_get_required_fields_unknown_returns_empty(self):
        assert get_required_fields("nonexistent") == []

    def test_get_expected_commands_vcs(self):
        cmds = get_expected_commands("vcs")
        assert "commit" in cmds

    def test_get_expected_commands_language_returns_empty(self):
        assert get_expected_commands("language") == []


# ---------------------------------------------------------------------------
# validate_module_against_contract
# ---------------------------------------------------------------------------


class TestValidateModuleAgainstContract:
    """validate_module_against_contract(module_name, reg_entry) -> list[dict]

    Returns [] if valid, or list of {"module": name, "error": message} dicts.
    """

    def _valid_linter(self):
        return {
            "id": "ruff",
            "name": "Ruff",
            "version": "0.4.0",
            "category": "linter",
            "description": "Fast Python linter.",
            "detect_files": ["pyproject.toml"],
            "brief": "Ruff lints Python.",
            "for_languages": ["python"],
            "commands": {"check": "ruff check ."},
        }

    def _valid_language(self):
        return {
            "id": "python",
            "name": "Python",
            "version": "3.12",
            "category": "language",
            "description": "Python language support.",
            "detect_files": ["*.py"],
            "brief": "Python is a language.",
        }

    def test_valid_module_returns_empty_list(self):
        errors = validate_module_against_contract("ruff", self._valid_linter())
        assert errors == []

    def test_valid_language_module_returns_empty_list(self):
        errors = validate_module_against_contract("python", self._valid_language())
        assert errors == []

    def test_missing_required_field_returns_error(self):
        entry = self._valid_linter()
        del entry["brief"]
        errors = validate_module_against_contract("ruff", entry)
        assert len(errors) == 1
        assert errors[0]["module"] == "ruff"
        assert "brief" in errors[0]["error"]

    def test_multiple_missing_required_fields(self):
        entry = self._valid_linter()
        del entry["name"]
        del entry["description"]
        errors = validate_module_against_contract("ruff", entry)
        assert len(errors) == 2
        error_messages = {e["error"] for e in errors}
        # Both missing fields should be mentioned in errors
        assert any("name" in msg for msg in error_messages)
        assert any("description" in msg for msg in error_messages)

    def test_missing_expected_command_returns_error(self):
        entry = self._valid_linter()
        del entry["commands"]
        errors = validate_module_against_contract("ruff", entry)
        assert len(errors) >= 1
        assert any("check" in e["error"] for e in errors)

    def test_expected_command_present_but_key_missing(self):
        entry = self._valid_linter()
        entry["commands"] = {"fix": "ruff --fix ."}  # has fix, not check
        errors = validate_module_against_contract("ruff", entry)
        assert len(errors) >= 1
        assert any("check" in e["error"] for e in errors)

    def test_unknown_category_returns_error(self):
        entry = self._valid_linter()
        entry["category"] = "totally_unknown"
        errors = validate_module_against_contract("ruff", entry)
        assert len(errors) >= 1
        assert any(
            "category" in e["error"].lower() or "totally_unknown" in e["error"]
            for e in errors
        )

    def test_language_no_expected_commands_so_no_command_error(self):
        # language has no expected_commands — even without a commands field it's fine
        entry = self._valid_language()
        errors = validate_module_against_contract("python", entry)
        assert errors == []

    def test_module_name_in_every_error(self):
        entry = self._valid_linter()
        del entry["brief"]
        del entry["name"]
        errors = validate_module_against_contract("ruff", entry)
        for e in errors:
            assert e["module"] == "ruff"

    def test_empty_reg_entry_returns_errors(self):
        errors = validate_module_against_contract("ruff", {})
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# validate_registry_integrity
# ---------------------------------------------------------------------------


class TestValidateRegistryIntegrity:
    """validate_registry_integrity(registry) -> list[dict]

    Takes a full registry dict ({"modules": {...}}) and returns all errors
    across all modules. Returns [] if everything is valid.
    """

    def _valid_registry(self):
        return {
            "modules": {
                "python": {
                    "id": "python",
                    "name": "Python",
                    "version": "3.12",
                    "category": "language",
                    "description": "Python language support.",
                    "detect_files": ["*.py"],
                    "brief": "Python is a language.",
                },
                "ruff": {
                    "id": "ruff",
                    "name": "Ruff",
                    "version": "0.4.0",
                    "category": "linter",
                    "description": "Fast Python linter.",
                    "detect_files": ["pyproject.toml"],
                    "brief": "Ruff lints Python.",
                    "for_languages": ["python"],
                    "commands": {"check": "ruff check ."},
                },
            }
        }

    def test_all_valid_returns_empty_list(self):
        errors = validate_registry_integrity(self._valid_registry())
        assert errors == []

    def test_one_invalid_module_returns_its_errors(self):
        registry = self._valid_registry()
        del registry["modules"]["ruff"]["brief"]
        errors = validate_registry_integrity(registry)
        assert len(errors) >= 1
        assert all(e["module"] == "ruff" for e in errors)

    def test_multiple_invalid_modules_returns_all_errors(self):
        registry = self._valid_registry()
        del registry["modules"]["ruff"]["brief"]
        del registry["modules"]["python"]["name"]
        errors = validate_registry_integrity(registry)
        module_names = {e["module"] for e in errors}
        assert "ruff" in module_names
        assert "python" in module_names

    def test_empty_registry_returns_empty_list(self):
        errors = validate_registry_integrity({})
        assert errors == []

    def test_empty_modules_dict_returns_empty_list(self):
        errors = validate_registry_integrity({"modules": {}})
        assert errors == []

    def test_missing_modules_key_returns_empty_list(self):
        errors = validate_registry_integrity({"other_key": "value"})
        assert errors == []

    def test_error_dicts_have_module_and_error_keys(self):
        registry = self._valid_registry()
        del registry["modules"]["ruff"]["brief"]
        errors = validate_registry_integrity(registry)
        for e in errors:
            assert "module" in e
            assert "error" in e


# ---------------------------------------------------------------------------
# CategoryRouter (smoke tests — already implemented)
# ---------------------------------------------------------------------------


class TestCategoryRouter:
    def _manifest(self):
        return {
            "installed_modules": {
                "git": {"category": "vcs"},
                "ruff": {"category": "linter"},
            }
        }

    def _registry(self):
        return {
            "modules": {
                "git": {
                    "category": "vcs",
                    "commands": {"commit": "git commit", "status": "git status"},
                },
                "ruff": {
                    "category": "linter",
                    "commands": {"check": "ruff check ."},
                },
            }
        }

    def test_has_category_installed_true(self):
        router = CategoryRouter(self._manifest(), self._registry())
        assert router.has_category_installed("vcs") is True
        assert router.has_category_installed("linter") is True

    def test_has_category_installed_false(self):
        router = CategoryRouter(self._manifest(), self._registry())
        assert router.has_category_installed("platform") is False

    def test_find_all_with_command_returns_match(self):
        router = CategoryRouter(self._manifest(), self._registry())
        results = router.find_all_with_command("check")
        assert len(results) == 1
        assert results[0]["module"] == "ruff"
        assert results[0]["command"] == "ruff check ."

    def test_find_all_with_command_no_match(self):
        router = CategoryRouter(self._manifest(), self._registry())
        results = router.find_all_with_command("nonexistent")
        assert results == []

    def test_find_all_with_command_multiple_matches(self):
        manifest = {
            "installed_modules": {
                "git": {"category": "vcs"},
                "ruff": {"category": "linter"},
            }
        }
        registry = {
            "modules": {
                "git": {"category": "vcs", "commands": {"check": "git check"}},
                "ruff": {"category": "linter", "commands": {"check": "ruff check ."}},
            }
        }
        router = CategoryRouter(manifest, registry)
        results = router.find_all_with_command("check")
        assert len(results) == 2

    def test_find_module_for_category_found(self):
        router = CategoryRouter(self._manifest(), self._registry())
        assert router.find_module_for_category("vcs") == "git"

    def test_find_module_for_category_not_found(self):
        router = CategoryRouter(self._manifest(), self._registry())
        assert router.find_module_for_category("platform") is None
