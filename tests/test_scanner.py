"""Tests for atlas.core.scanner — all parsers and public API."""

import pytest

from atlas.core.scanner import (
    MODULE_CONFIG_KEYS,
    MODULE_CONFIG_MAP,
    _brackets_balanced,
    _map_extracted_values,
    _navigate_json_path,
    _parse_toml_array,
    _parse_toml_value,
    _parse_toml_values,
    _parse_yaml_value,
    _read_file_safe,
    _read_gomod,
    _read_ini_section,
    _read_json_safe,
    _read_toml_section,
    _read_yaml_simple,
    _set_nested,
    enrich_module_rules,
    get_config_locations,
    scan_all_modules,
    scan_module_config,
)


# ---------------------------------------------------------------------------
# _read_file_safe
# ---------------------------------------------------------------------------


class TestReadFileSafe:
    def test_reads_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        assert _read_file_safe(str(f)) == "hello"

    def test_returns_empty_for_nonexistent(self, tmp_path):
        assert _read_file_safe(str(tmp_path / "missing.txt")) == ""

    def test_returns_empty_for_directory(self, tmp_path):
        assert _read_file_safe(str(tmp_path)) == ""

    def test_reads_multiline_file(self, tmp_path):
        f = tmp_path / "multi.txt"
        f.write_text("line1\nline2\n", encoding="utf-8")
        assert _read_file_safe(str(f)) == "line1\nline2\n"


# ---------------------------------------------------------------------------
# _brackets_balanced
# ---------------------------------------------------------------------------


class TestBracketsBalanced:
    def test_empty_string_is_balanced(self):
        assert _brackets_balanced("") is True

    def test_balanced_simple(self):
        assert _brackets_balanced("[a, b, c]") is True

    def test_unbalanced_open(self):
        assert _brackets_balanced("[a, b") is False

    def test_unbalanced_close(self):
        assert _brackets_balanced("a, b]") is False

    def test_nested_balanced(self):
        assert _brackets_balanced('["E", ["W", "F"]]') is True

    def test_nested_unbalanced(self):
        assert _brackets_balanced('["E", ["W"') is False

    def test_no_brackets(self):
        assert _brackets_balanced("hello world") is True


# ---------------------------------------------------------------------------
# _parse_toml_value
# ---------------------------------------------------------------------------


class TestParseTomlValue:
    def test_double_quoted_string(self):
        assert _parse_toml_value('"py310"') == "py310"

    def test_single_quoted_string(self):
        assert _parse_toml_value("'hello'") == "hello"

    def test_integer(self):
        assert _parse_toml_value("120") == 120

    def test_true(self):
        assert _parse_toml_value("true") is True

    def test_false(self):
        assert _parse_toml_value("false") is False

    def test_inline_array(self):
        result = _parse_toml_value('["E", "W", "F"]')
        assert result == ["E", "W", "F"]

    def test_unquoted_string_returned_as_is(self):
        assert _parse_toml_value("py310") == "py310"

    def test_strips_whitespace(self):
        assert _parse_toml_value('  "hello"  ') == "hello"


# ---------------------------------------------------------------------------
# _parse_toml_array
# ---------------------------------------------------------------------------


class TestParseTomlArray:
    def test_empty_array(self):
        assert _parse_toml_array("[]") == []

    def test_string_elements(self):
        assert _parse_toml_array('["E", "W", "F"]') == ["E", "W", "F"]

    def test_integer_elements(self):
        assert _parse_toml_array("[1, 2, 3]") == [1, 2, 3]

    def test_mixed_elements(self):
        result = _parse_toml_array('["src", 2, true]')
        assert result == ["src", 2, True]

    def test_not_an_array_returns_empty(self):
        assert _parse_toml_array("hello") == []

    def test_single_element(self):
        assert _parse_toml_array('["tests"]') == ["tests"]

    def test_whitespace_inside(self):
        assert _parse_toml_array('[ "a" , "b" ]') == ["a", "b"]


# ---------------------------------------------------------------------------
# _read_toml_section
# ---------------------------------------------------------------------------


class TestReadTomlSection:
    def test_extracts_simple_section(self):
        content = "[tool.ruff]\nline-length = 120\ntarget-version = \"py310\"\n"
        section = _read_toml_section(content, "[tool.ruff]")
        assert "line-length = 120" in section
        assert 'target-version = "py310"' in section

    def test_stops_at_next_section(self):
        content = "[tool.ruff]\nline-length = 120\n[tool.black]\nline-length = 88\n"
        section = _read_toml_section(content, "[tool.ruff]")
        assert "line-length = 120" in section
        assert "88" not in section

    def test_missing_section_returns_empty(self):
        content = "[tool.ruff]\nline-length = 120\n"
        assert _read_toml_section(content, "[tool.black]") == ""

    def test_empty_content_returns_empty(self):
        assert _read_toml_section("", "[tool.ruff]") == ""

    def test_does_not_stop_at_array_of_tables(self):
        content = "[tool.ruff]\nline-length = 120\n[[servers]]\nname = \"test\"\n"
        section = _read_toml_section(content, "[tool.ruff]")
        assert "line-length = 120" in section


# ---------------------------------------------------------------------------
# _parse_toml_values
# ---------------------------------------------------------------------------


class TestParseTomlValues:
    def test_simple_key_value(self):
        result = _parse_toml_values("line-length = 120\n")
        assert result["line-length"] == 120

    def test_quoted_string_value(self):
        result = _parse_toml_values('target-version = "py310"\n')
        assert result["target-version"] == "py310"

    def test_boolean_value(self):
        result = _parse_toml_values("strict = true\n")
        assert result["strict"] is True

    def test_inline_array_value(self):
        result = _parse_toml_values('select = ["E", "W", "F"]\n')
        assert result["select"] == ["E", "W", "F"]

    def test_multiline_array(self):
        content = 'select = [\n    "E",\n    "W",\n]\n'
        result = _parse_toml_values(content)
        assert result["select"] == ["E", "W"]

    def test_skips_blank_lines_and_comments(self):
        content = "# comment\n\nline-length = 88\n"
        result = _parse_toml_values(content)
        assert result["line-length"] == 88
        assert len(result) == 1

    def test_skips_subsection_headers(self):
        content = "line-length = 88\n[tool.ruff.lint]\nselect = [\"E\"]\n"
        result = _parse_toml_values(content)
        assert "line-length" in result

    def test_inline_comment_stripped(self):
        result = _parse_toml_values("line-length = 88  # default\n")
        assert result["line-length"] == 88

    def test_empty_content_returns_empty_dict(self):
        assert _parse_toml_values("") == {}


# ---------------------------------------------------------------------------
# _read_json_safe
# ---------------------------------------------------------------------------


class TestReadJsonSafe:
    def test_reads_valid_json(self, tmp_path):
        f = tmp_path / "tsconfig.json"
        f.write_text('{"compilerOptions": {"strict": true}}', encoding="utf-8")
        result = _read_json_safe(str(f))
        assert result["compilerOptions"]["strict"] is True

    def test_returns_empty_for_nonexistent(self, tmp_path):
        assert _read_json_safe(str(tmp_path / "missing.json")) == {}

    def test_returns_empty_for_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{not valid json", encoding="utf-8")
        assert _read_json_safe(str(f)) == {}

    def test_returns_empty_when_root_is_list(self, tmp_path):
        f = tmp_path / "list.json"
        f.write_text("[1, 2, 3]", encoding="utf-8")
        assert _read_json_safe(str(f)) == {}

    def test_reads_nested_dict(self, tmp_path):
        f = tmp_path / "pkg.json"
        f.write_text('{"name": "myapp", "version": "1.0.0"}', encoding="utf-8")
        result = _read_json_safe(str(f))
        assert result["name"] == "myapp"


# ---------------------------------------------------------------------------
# _navigate_json_path
# ---------------------------------------------------------------------------


class TestNavigateJsonPath:
    def test_single_key(self):
        data = {"compilerOptions": {"strict": True}}
        result = _navigate_json_path(data, "compilerOptions")
        assert result == {"strict": True}

    def test_dotted_path(self):
        data = {"a": {"b": {"c": "value"}}}
        result = _navigate_json_path(data, "a.b")
        assert result == {"c": "value"}

    def test_missing_key_returns_none(self):
        data = {"compilerOptions": {}}
        assert _navigate_json_path(data, "missing") is None

    def test_non_dict_value_returns_none(self):
        data = {"name": "myapp"}
        assert _navigate_json_path(data, "name") is None

    def test_empty_path_segment(self):
        data = {}
        assert _navigate_json_path(data, "a.b.c") is None

    def test_deeply_nested(self):
        data = {"tool": {"jest": {"timeout": 5000}}}
        result = _navigate_json_path(data, "tool.jest")
        assert result == {"timeout": 5000}


# ---------------------------------------------------------------------------
# _read_ini_section
# ---------------------------------------------------------------------------


class TestReadIniSection:
    def test_reads_existing_section(self, tmp_path):
        f = tmp_path / "setup.cfg"
        f.write_text("[flake8]\nmax-line-length = 88\nextend-ignore = E501\n", encoding="utf-8")
        result = _read_ini_section(str(f), "flake8")
        assert result["max-line-length"] == "88"
        assert result["extend-ignore"] == "E501"

    def test_returns_empty_for_missing_section(self, tmp_path):
        f = tmp_path / "setup.cfg"
        f.write_text("[flake8]\nmax-line-length = 88\n", encoding="utf-8")
        assert _read_ini_section(str(f), "mypy") == {}

    def test_returns_empty_for_nonexistent_file(self, tmp_path):
        assert _read_ini_section(str(tmp_path / "missing.cfg"), "flake8") == {}

    def test_reads_pytest_section(self, tmp_path):
        f = tmp_path / "pytest.ini"
        f.write_text("[pytest]\ntestpaths = tests\naddopts = -v\n", encoding="utf-8")
        result = _read_ini_section(str(f), "pytest")
        assert result["testpaths"] == "tests"
        assert result["addopts"] == "-v"

    def test_returns_empty_for_empty_section(self, tmp_path):
        f = tmp_path / "setup.cfg"
        f.write_text("[flake8]\n", encoding="utf-8")
        result = _read_ini_section(str(f), "flake8")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# _parse_yaml_value / _read_yaml_simple
# ---------------------------------------------------------------------------


class TestParseYamlValue:
    def test_true_string(self):
        assert _parse_yaml_value("true") is True

    def test_false_string(self):
        assert _parse_yaml_value("false") is False

    def test_yes_string(self):
        assert _parse_yaml_value("yes") is True

    def test_no_string(self):
        assert _parse_yaml_value("no") is False

    def test_integer(self):
        assert _parse_yaml_value("30") == 30

    def test_plain_string(self):
        assert _parse_yaml_value("myproject") == "myproject"

    def test_double_quoted_string(self):
        assert _parse_yaml_value('"hello"') == "hello"

    def test_strips_whitespace(self):
        assert _parse_yaml_value("  42  ") == 42


class TestReadYamlSimple:
    def test_reads_simple_key_value(self, tmp_path):
        f = tmp_path / "config.yml"
        f.write_text("timeout: 30\nstrictMode: true\nname: myproject\n", encoding="utf-8")
        result = _read_yaml_simple(str(f))
        assert result["timeout"] == 30
        assert result["strictMode"] is True
        assert result["name"] == "myproject"

    def test_returns_empty_for_nonexistent(self, tmp_path):
        assert _read_yaml_simple(str(tmp_path / "missing.yml")) == {}

    def test_skips_comments(self, tmp_path):
        f = tmp_path / "config.yml"
        f.write_text("# comment\ntimeout: 30\n", encoding="utf-8")
        result = _read_yaml_simple(str(f))
        assert result["timeout"] == 30
        assert len(result) == 1

    def test_skips_list_items(self, tmp_path):
        f = tmp_path / "config.yml"
        f.write_text("timeout: 30\n- item\n", encoding="utf-8")
        result = _read_yaml_simple(str(f))
        assert "timeout" in result


# ---------------------------------------------------------------------------
# _read_gomod
# ---------------------------------------------------------------------------


class TestReadGomod:
    def test_extracts_module_and_go_version(self, tmp_path):
        f = tmp_path / "go.mod"
        f.write_text("module github.com/myorg/myapp\n\ngo 1.21\n", encoding="utf-8")
        result = _read_gomod(str(f))
        assert result["module"] == "github.com/myorg/myapp"
        assert result["go"] == "1.21"

    def test_returns_empty_for_nonexistent(self, tmp_path):
        assert _read_gomod(str(tmp_path / "missing.mod")) == {}

    def test_module_only(self, tmp_path):
        f = tmp_path / "go.mod"
        f.write_text("module example.com/app\n", encoding="utf-8")
        result = _read_gomod(str(f))
        assert result["module"] == "example.com/app"
        assert "go" not in result

    def test_ignores_require_block(self, tmp_path):
        f = tmp_path / "go.mod"
        f.write_text(
            "module example.com/app\ngo 1.20\nrequire (\n    github.com/pkg v1.0.0\n)\n",
            encoding="utf-8",
        )
        result = _read_gomod(str(f))
        assert result["module"] == "example.com/app"
        assert result["go"] == "1.20"


# ---------------------------------------------------------------------------
# _set_nested
# ---------------------------------------------------------------------------


class TestSetNested:
    def test_single_key(self):
        d: dict = {}
        _set_nested(d, "key", "value")
        assert d == {"key": "value"}

    def test_dotted_two_levels(self):
        d: dict = {}
        _set_nested(d, "style.line_length", 120)
        assert d == {"style": {"line_length": 120}}

    def test_dotted_three_levels(self):
        d: dict = {}
        _set_nested(d, "a.b.c", 42)
        assert d == {"a": {"b": {"c": 42}}}

    def test_overwrites_existing_leaf(self):
        d = {"style": {"line_length": 88}}
        _set_nested(d, "style.line_length", 120)
        assert d["style"]["line_length"] == 120

    def test_creates_intermediate_dicts(self):
        d: dict = {}
        _set_nested(d, "x.y.z", True)
        assert d["x"]["y"]["z"] is True

    def test_replaces_non_dict_intermediate(self):
        d: dict = {"a": "not_a_dict"}
        _set_nested(d, "a.b", 1)
        assert d["a"]["b"] == 1

    def test_multiple_keys_same_top(self):
        d: dict = {}
        _set_nested(d, "style.line_length", 100)
        _set_nested(d, "style.indent_width", 4)
        assert d == {"style": {"line_length": 100, "indent_width": 4}}


# ---------------------------------------------------------------------------
# _map_extracted_values
# ---------------------------------------------------------------------------


class TestMapExtractedValues:
    def test_maps_known_key(self):
        raw = {"line-length": 120}
        mapping = {"line-length": "style.line_length"}
        result = _map_extracted_values(raw, mapping)
        assert result == {"style": {"line_length": 120}}

    def test_skips_unknown_keys(self):
        raw = {"unknown-key": "value"}
        mapping = {"line-length": "style.line_length"}
        result = _map_extracted_values(raw, mapping)
        assert result == {}

    def test_maps_multiple_keys(self):
        raw = {"line-length": 120, "target-version": "py310"}
        mapping = {
            "line-length": "style.line_length",
            "target-version": "style.python_version",
        }
        result = _map_extracted_values(raw, mapping)
        assert result["style"]["line_length"] == 120
        assert result["style"]["python_version"] == "py310"

    def test_empty_raw_returns_empty(self):
        mapping = {"line-length": "style.line_length"}
        assert _map_extracted_values({}, mapping) == {}

    def test_empty_mapping_returns_empty(self):
        raw = {"line-length": 120}
        assert _map_extracted_values(raw, {}) == {}

    def test_boolean_value_preserved(self):
        raw = {"strict": True}
        mapping = {"strict": "style.strict_mode"}
        result = _map_extracted_values(raw, mapping)
        assert result["style"]["strict_mode"] is True


# ---------------------------------------------------------------------------
# get_config_locations
# ---------------------------------------------------------------------------


class TestGetConfigLocations:
    def test_known_module_returns_list(self):
        locs = get_config_locations("ruff")
        assert isinstance(locs, list)
        assert len(locs) > 0

    def test_unknown_module_returns_empty(self):
        assert get_config_locations("nonexistent-module-xyz") == []

    def test_sorted_by_priority(self):
        locs = get_config_locations("ruff")
        priorities = [loc["priority"] for loc in locs]
        assert priorities == sorted(priorities)

    def test_each_location_has_required_keys(self):
        for module in ("ruff", "pytest", "eslint", "mypy"):
            for loc in get_config_locations(module):
                assert "file" in loc
                assert "format" in loc
                assert "section" in loc
                assert "priority" in loc

    def test_all_modules_in_map_return_locations(self):
        from atlas.core.scanner import MODULE_CONFIG_MAP
        for module in MODULE_CONFIG_MAP:
            locs = get_config_locations(module)
            assert len(locs) > 0, f"{module} returned empty locations"


# ---------------------------------------------------------------------------
# scan_module_config
# ---------------------------------------------------------------------------


class TestScanModuleConfig:
    # --- unknown / empty ---

    def test_unknown_module_returns_not_found(self, tmp_path):
        result = scan_module_config("nonexistent-xyz", str(tmp_path))
        assert result == {"found": False}

    def test_empty_dir_returns_not_found(self, tmp_path):
        result = scan_module_config("ruff", str(tmp_path))
        assert result == {"found": False}

    # --- format: exists ---

    def test_exists_format_found(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")
        result = scan_module_config("pip", str(tmp_path))
        assert result["found"] is True
        assert result["config_file"] == "requirements.txt"
        assert result["extracted"] == {}

    def test_exists_format_not_found(self, tmp_path):
        result = scan_module_config("pip", str(tmp_path))
        assert result["found"] is False

    # --- format: dir ---

    def test_dir_format_found(self, tmp_path):
        (tmp_path / ".git").mkdir()
        result = scan_module_config("git", str(tmp_path))
        assert result["found"] is True
        assert result["config_file"] == ".git"
        assert result["extracted"] == {}

    def test_dir_format_not_found(self, tmp_path):
        result = scan_module_config("git", str(tmp_path))
        assert result["found"] is False

    # --- format: glob_exists ---

    def test_glob_exists_found(self, tmp_path):
        (tmp_path / "mydb.db").write_text("", encoding="utf-8")
        result = scan_module_config("sqlite", str(tmp_path))
        assert result["found"] is True
        assert result["config_file"] == "*.db"

    def test_glob_exists_not_found(self, tmp_path):
        result = scan_module_config("sqlite", str(tmp_path))
        assert result["found"] is False

    # --- format: toml ---

    def test_toml_format_extracts_values(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 120\ntarget-version = \"py310\"\n",
            encoding="utf-8",
        )
        result = scan_module_config("ruff", str(tmp_path))
        assert result["found"] is True
        assert result["config_file"] == "pyproject.toml"
        assert result["extracted"]["style"]["line_length"] == 120
        assert result["extracted"]["style"]["python_version"] == "py310"

    def test_toml_priority_first_file_wins(self, tmp_path):
        # pyproject.toml (priority 1) and ruff.toml (priority 2) both present
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 100\n", encoding="utf-8"
        )
        (tmp_path / "ruff.toml").write_text("line-length = 80\n", encoding="utf-8")
        result = scan_module_config("ruff", str(tmp_path))
        assert result["config_file"] == "pyproject.toml"
        assert result["extracted"]["style"]["line_length"] == 100

    def test_toml_no_section_match_returns_empty_extracted(self, tmp_path):
        # pyproject.toml exists but has no [tool.ruff] section
        (tmp_path / "pyproject.toml").write_text("[project]\nname = \"app\"\n", encoding="utf-8")
        result = scan_module_config("ruff", str(tmp_path))
        # File is found but section is absent → extracted is empty
        assert result["found"] is True
        assert result["extracted"] == {}

    # --- format: json ---

    def test_json_format_extracts_values(self, tmp_path):
        (tmp_path / "tsconfig.json").write_text(
            '{"strict": true, "target": "ES2020"}', encoding="utf-8"
        )
        result = scan_module_config("typescript", str(tmp_path))
        assert result["found"] is True
        assert result["config_file"] == "tsconfig.json"
        assert result["extracted"]["style"]["strict_mode"] is True
        assert result["extracted"]["style"]["target"] == "ES2020"

    def test_json_with_section_extracts_nested(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"jest": {"testTimeout": 5000, "testEnvironment": "node"}}',
            encoding="utf-8",
        )
        result = scan_module_config("jest", str(tmp_path))
        assert result["found"] is True
        assert result["extracted"]["testing"]["timeout"] == 5000
        assert result["extracted"]["testing"]["environment"] == "node"

    # --- format: ini ---

    def test_ini_format_extracts_values(self, tmp_path):
        (tmp_path / "setup.cfg").write_text(
            "[flake8]\nmax-line-length = 88\nextend-ignore = E501\n", encoding="utf-8"
        )
        result = scan_module_config("flake8", str(tmp_path))
        assert result["found"] is True
        assert result["config_file"] == "setup.cfg"
        assert result["extracted"]["style"]["line_length"] == "88"

    # --- format: yaml ---

    def test_yaml_format_extracts_values(self, tmp_path):
        (tmp_path / ".golangci.yml").write_text(
            "timeout: 5m\nissues-exit-code: 1\n", encoding="utf-8"
        )
        result = scan_module_config("golangci-lint", str(tmp_path))
        assert result["found"] is True
        assert result["config_file"] == ".golangci.yml"

    # --- format: gomod ---

    def test_gomod_format_extracts_values(self, tmp_path):
        (tmp_path / "go.mod").write_text(
            "module github.com/org/app\ngo 1.21\n", encoding="utf-8"
        )
        result = scan_module_config("go", str(tmp_path))
        assert result["found"] is True
        assert result["config_file"] == "go.mod"
        assert result["extracted"]["project"]["module"] == "github.com/org/app"
        assert result["extracted"]["style"]["go_version"] == "1.21"

    # --- custom config_locations override ---

    def test_custom_config_locations_override(self, tmp_path):
        (tmp_path / "custom.toml").write_text("line-length = 99\n", encoding="utf-8")
        custom_locs = [{"file": "custom.toml", "format": "toml", "section": None, "priority": 1}]
        result = scan_module_config("ruff", str(tmp_path), config_locations=custom_locs)
        assert result["found"] is True
        assert result["config_file"] == "custom.toml"

    def test_empty_custom_locations_returns_not_found(self, tmp_path):
        result = scan_module_config("ruff", str(tmp_path), config_locations=[])
        assert result == {"found": False}

    # --- plan §5.2 examples ---

    def test_plan_ruff_from_pyproject(self, tmp_path):
        """Plan §5.2 example: ruff config in pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.ruff]\nline-length = 120\nselect = ["E", "W", "F"]\n',
            encoding="utf-8",
        )
        result = scan_module_config("ruff", str(tmp_path))
        assert result["found"] is True
        assert result["extracted"]["style"]["line_length"] == 120

    def test_plan_pytest_from_pyproject(self, tmp_path):
        """Plan §5.2 example: pytest config in pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\naddopts = \"-v\"\n",
            encoding="utf-8",
        )
        result = scan_module_config("pytest", str(tmp_path))
        assert result["found"] is True
        assert result["extracted"]["testing"]["test_dirs"] == ["tests"]

    def test_plan_typescript_from_tsconfig(self, tmp_path):
        """Plan §5.2 example: TypeScript config from tsconfig.json."""
        (tmp_path / "tsconfig.json").write_text(
            '{"compilerOptions": {"strict": true, "target": "ESNext"}}',
            encoding="utf-8",
        )
        result = scan_module_config("typescript", str(tmp_path))
        assert result["found"] is True
        # compilerOptions is not a direct key — strict/target are at root level
        # tsconfig uses section=None so root keys are extracted directly
        assert result["config_file"] == "tsconfig.json"


# ---------------------------------------------------------------------------
# scan_all_modules
# ---------------------------------------------------------------------------


class TestScanAllModules:
    def test_empty_module_list_returns_empty_dict(self, tmp_path):
        result = scan_all_modules([], str(tmp_path))
        assert result == {}

    def test_single_module_not_found(self, tmp_path):
        result = scan_all_modules(["ruff"], str(tmp_path))
        assert result == {"ruff": {"found": False}}

    def test_single_module_found(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        result = scan_all_modules(["ruff"], str(tmp_path))
        assert result["ruff"]["found"] is True

    def test_multiple_modules_mixed_results(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        result = scan_all_modules(["ruff", "eslint"], str(tmp_path))
        assert result["ruff"]["found"] is True
        assert result["eslint"]["found"] is False

    def test_returns_dict_keyed_by_module_name(self, tmp_path):
        modules = ["ruff", "mypy"]
        result = scan_all_modules(modules, str(tmp_path))
        assert set(result.keys()) == {"ruff", "mypy"}

    def test_unknown_module_gets_not_found(self, tmp_path):
        result = scan_all_modules(["unknown-xyz"], str(tmp_path))
        assert result["unknown-xyz"] == {"found": False}


# ---------------------------------------------------------------------------
# enrich_module_rules
# ---------------------------------------------------------------------------


class TestEnrichModuleRules:
    def test_no_config_returns_base_rules_unchanged(self, tmp_path):
        base = {"style": {"line_length": 88}}
        result = enrich_module_rules("ruff", base, str(tmp_path))
        assert result == {"style": {"line_length": 88}}

    def test_does_not_mutate_base_rules(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 120\n", encoding="utf-8"
        )
        base = {"style": {"line_length": 88}}
        enrich_module_rules("ruff", base, str(tmp_path))
        assert base["style"]["line_length"] == 88  # original untouched

    def test_merges_extracted_into_base_dict(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 120\n", encoding="utf-8"
        )
        base = {"style": {"line_length": 88, "indent_width": 4}}
        result = enrich_module_rules("ruff", base, str(tmp_path))
        assert result["style"]["line_length"] == 120
        assert result["style"]["indent_width"] == 4  # preserved from base

    def test_adds_new_top_level_keys(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 100\n", encoding="utf-8"
        )
        base: dict = {}
        result = enrich_module_rules("ruff", base, str(tmp_path))
        assert result["style"]["line_length"] == 100

    def test_overwrites_non_dict_top_level(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 100\n", encoding="utf-8"
        )
        base = {"style": "old-string-value"}
        result = enrich_module_rules("ruff", base, str(tmp_path))
        # extracted style is a dict, replaces the string
        assert isinstance(result["style"], dict)
        assert result["style"]["line_length"] == 100

    def test_returns_new_dict_not_same_object(self, tmp_path):
        base = {"style": {"line_length": 88}}
        result = enrich_module_rules("ruff", base, str(tmp_path))
        assert result is not base

    def test_unknown_module_returns_base_unchanged(self, tmp_path):
        base = {"style": {"line_length": 88}}
        result = enrich_module_rules("nonexistent-xyz", base, str(tmp_path))
        assert result == base
