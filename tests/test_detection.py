"""Tests for atlas.core.detection — parametrized over every data table."""

import pytest

from atlas.core.detection import (
    _FRAMEWORK_PATTERNS,
    _FULLSTACK_DIRS,
    _LANGUAGE_MARKERS,
    _LOCK_FILE_MANAGERS,
    _TOOL_MARKERS,
    _WORKSPACE_MANAGERS,
    _detect_existing_tools,
    _detect_languages,
    _detect_package_manager,
)


# ---------------------------------------------------------------------------
# _detect_languages
# ---------------------------------------------------------------------------


class TestDetectLanguages:
    """Parametrized tests covering every entry in _LANGUAGE_MARKERS."""

    @pytest.mark.parametrize("lang,markers", _LANGUAGE_MARKERS.items())
    def test_exact_filename_marker_detected(self, lang: str, markers: list[str], tmp_path):
        """Creating any non-glob marker file must detect that language."""
        exact_markers = [m for m in markers if not m.startswith("*")]
        if not exact_markers:
            pytest.skip(f"{lang} has no exact filename markers")

        marker = exact_markers[0]
        (tmp_path / marker).write_text("", encoding="utf-8")
        languages, primary = _detect_languages(str(tmp_path))

        assert lang in languages

    @pytest.mark.parametrize("lang,markers", _LANGUAGE_MARKERS.items())
    def test_glob_extension_marker_detected(self, lang: str, markers: list[str], tmp_path):
        """Creating a file with a glob-matched extension must detect that language."""
        glob_markers = [m for m in markers if m.startswith("*")]
        if not glob_markers:
            pytest.skip(f"{lang} has no glob extension markers")

        ext = glob_markers[0][1:]  # strip leading '*'
        (tmp_path / f"example{ext}").write_text("", encoding="utf-8")
        languages, primary = _detect_languages(str(tmp_path))

        assert lang in languages

    def test_empty_dir_detects_no_languages(self, tmp_path):
        languages, primary = _detect_languages(str(tmp_path))
        assert languages == []
        assert primary == ""

    def test_typescript_removes_javascript_when_both_present(self, tmp_path):
        """When tsconfig.json and package.json coexist, JS should be dropped."""
        (tmp_path / "tsconfig.json").write_text("", encoding="utf-8")
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        languages, _ = _detect_languages(str(tmp_path))

        assert "typescript" in languages
        assert "javascript" not in languages

    def test_primary_language_priority_python_over_javascript(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        _, primary = _detect_languages(str(tmp_path))

        assert primary == "python"

    def test_primary_language_priority_python_over_rust(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        (tmp_path / "Cargo.toml").write_text("", encoding="utf-8")
        _, primary = _detect_languages(str(tmp_path))

        assert primary == "python"

    def test_primary_language_fallback_to_first(self, tmp_path):
        """A language not in the priority list gets primary set to itself."""
        (tmp_path / "mix.exs").write_text("", encoding="utf-8")
        languages, primary = _detect_languages(str(tmp_path))

        assert "elixir" in languages
        assert primary == "elixir"


# ---------------------------------------------------------------------------
# _detect_package_manager
# ---------------------------------------------------------------------------


class TestDetectPackageManager:
    """Parametrized tests covering every entry in _LOCK_FILE_MANAGERS."""

    @pytest.mark.parametrize("lock_file,expected_manager", _LOCK_FILE_MANAGERS.items())
    def test_lock_file_returns_correct_manager(
        self, lock_file: str, expected_manager: str, tmp_path
    ):
        (tmp_path / lock_file).write_text("", encoding="utf-8")
        result = _detect_package_manager(str(tmp_path), languages=[])
        assert result == expected_manager

    def test_no_lock_file_returns_none(self, tmp_path):
        result = _detect_package_manager(str(tmp_path), languages=[])
        assert result == "none"

    def test_empty_dir_returns_none(self, tmp_path):
        result = _detect_package_manager(str(tmp_path), languages=[])
        assert result == "none"


# ---------------------------------------------------------------------------
# _detect_existing_tools
# ---------------------------------------------------------------------------


def _tool_markers_by_kind(tool: str) -> tuple[list[str], list[str]]:
    """Split a tool's markers into TOML-section markers and file markers."""
    markers = _TOOL_MARKERS[tool]
    toml = [m for m in markers if m.startswith("[")]
    files = [m for m in markers if not m.startswith("[")]
    return toml, files


class TestDetectExistingTools:
    """Parametrized tests covering every entry in _TOOL_MARKERS."""

    @pytest.mark.parametrize("tool", [t for t in _TOOL_MARKERS if _tool_markers_by_kind(t)[0]])
    def test_toml_section_marker_detected(self, tool: str, tmp_path):
        toml_markers, _ = _tool_markers_by_kind(tool)
        content = "\n".join(toml_markers)
        (tmp_path / "pyproject.toml").write_text(content, encoding="utf-8")
        found = _detect_existing_tools(str(tmp_path))
        assert tool in found

    @pytest.mark.parametrize("tool", [t for t in _TOOL_MARKERS if _tool_markers_by_kind(t)[1]])
    def test_standalone_file_marker_detected(self, tool: str, tmp_path):
        _, file_markers = _tool_markers_by_kind(tool)
        (tmp_path / file_markers[0]).write_text("", encoding="utf-8")
        found = _detect_existing_tools(str(tmp_path))
        assert tool in found

    def test_empty_dir_detects_no_tools(self, tmp_path):
        found = _detect_existing_tools(str(tmp_path))
        assert found == []

    def test_jest_detected_via_package_json_marker(self, tmp_path):
        """jest.config.js in package.json content also triggers detection."""
        (tmp_path / "package.json").write_text('{"scripts": {"test": "jest.config.js"}}')
        found = _detect_existing_tools(str(tmp_path))
        assert "jest" in found
