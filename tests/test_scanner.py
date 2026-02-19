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
