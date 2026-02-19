"""Tests for atlas.core.detection — parametrized over every data table."""

import pytest

from atlas.core.detection import (
    _FRAMEWORK_PATTERNS,
    _FULLSTACK_DIRS,
    _LANGUAGE_MARKERS,
    _LOCK_FILE_MANAGERS,
    _TOOL_MARKERS,
    _WORKSPACE_MANAGERS,
    _detect_languages,
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
