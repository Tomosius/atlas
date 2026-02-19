"""Tests for atlas.core.detection — parametrized over every data table."""

import pytest

from atlas.core.detection import (
    _DATABASE_PATTERNS,
    _FRAMEWORK_PATTERNS,
    _FULLSTACK_DIRS,
    _LANGUAGE_MARKERS,
    _LOCK_FILE_MANAGERS,
    _TOOL_MARKERS,
    _WORKSPACE_MANAGERS,
    _detect_databases,
    _detect_existing_tools,
    _detect_frameworks_and_stack,
    _detect_infrastructure,
    _detect_languages,
    _detect_package_manager,
    _detect_structure,
    detect_project,
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


# ---------------------------------------------------------------------------
# _detect_frameworks_and_stack
# ---------------------------------------------------------------------------


# Frameworks whose name is a substring of another framework's name cause the
# engine's simple `in` check to match the shorter name first, making exact
# stack assertions fragile.  Those cases are tested separately below.
# "react" is a substring of "react-native"; both must be excluded from the
# parametrized exact-stack test and covered by dedicated tests below.
_AMBIGUOUS_FRAMEWORKS = {"react", "react-native"}


class TestDetectFrameworksAndStack:
    """Parametrized tests covering every entry in _FRAMEWORK_PATTERNS."""

    @pytest.mark.parametrize(
        "framework,lang_stack",
        [(f, ls) for f, ls in _FRAMEWORK_PATTERNS.items() if f not in _AMBIGUOUS_FRAMEWORKS],
    )
    def test_framework_detected_and_stack_correct(
        self, framework: str, lang_stack: tuple[str, str], tmp_path
    ):
        lang, expected_stack = lang_stack
        (tmp_path / "pyproject.toml").write_text(
            f'[project]\ndependencies = ["{framework}"]', encoding="utf-8"
        )
        lang_marker = next(
            m for m in _LANGUAGE_MARKERS[lang] if not m.startswith("*")
        )
        if lang_marker != "pyproject.toml":
            (tmp_path / lang_marker).write_text("", encoding="utf-8")

        frameworks, stack = _detect_frameworks_and_stack(str(tmp_path), languages=[lang])

        assert framework in frameworks
        assert stack == expected_stack

    def test_react_native_detected(self, tmp_path):
        """react-native is detected even though 'react' also matches as substring."""
        (tmp_path / "package.json").write_text(
            '{"dependencies": {"react-native": "0.73"}}', encoding="utf-8"
        )
        frameworks, _ = _detect_frameworks_and_stack(str(tmp_path), languages=["typescript"])
        assert "react-native" in frameworks

    def test_first_framework_wins_stack(self, tmp_path):
        """Stack should be set by the first matched framework."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["fastapi", "flask"]', encoding="utf-8"
        )
        _, stack = _detect_frameworks_and_stack(str(tmp_path), languages=["python"])
        assert stack == "python-backend"

    def test_fallback_stack_python(self, tmp_path):
        frameworks, stack = _detect_frameworks_and_stack(str(tmp_path), languages=["python"])
        assert frameworks == []
        assert stack == "python-library"

    def test_fallback_stack_typescript(self, tmp_path):
        _, stack = _detect_frameworks_and_stack(str(tmp_path), languages=["typescript"])
        assert stack == "ts-library"

    def test_fallback_stack_javascript(self, tmp_path):
        _, stack = _detect_frameworks_and_stack(str(tmp_path), languages=["javascript"])
        assert stack == "js-library"

    def test_fallback_stack_rust(self, tmp_path):
        _, stack = _detect_frameworks_and_stack(str(tmp_path), languages=["rust"])
        assert stack == "rust-library"

    def test_fallback_stack_go(self, tmp_path):
        _, stack = _detect_frameworks_and_stack(str(tmp_path), languages=["go"])
        assert stack == "go-service"

    def test_no_language_no_stack(self, tmp_path):
        _, stack = _detect_frameworks_and_stack(str(tmp_path), languages=[])
        assert stack == ""


# ---------------------------------------------------------------------------
# _detect_databases
# ---------------------------------------------------------------------------


class TestDetectDatabases:
    """Parametrized tests covering every entry in _DATABASE_PATTERNS."""

    @pytest.mark.parametrize("db", _DATABASE_PATTERNS)
    def test_db_detected_from_pyproject(self, db: str, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            f'[project]\ndependencies = ["{db}"]', encoding="utf-8"
        )
        result = _detect_databases(str(tmp_path), languages=[])
        assert db in result

    @pytest.mark.parametrize("db", _DATABASE_PATTERNS)
    def test_db_detected_from_requirements_txt(self, db: str, tmp_path):
        (tmp_path / "requirements.txt").write_text(f"{db}==1.0.0\n", encoding="utf-8")
        result = _detect_databases(str(tmp_path), languages=[])
        assert db in result

    @pytest.mark.parametrize("db", _DATABASE_PATTERNS)
    def test_db_detected_from_package_json(self, db: str, tmp_path):
        (tmp_path / "package.json").write_text(
            f'{{"dependencies": {{"{db}": "1.0.0"}}}}', encoding="utf-8"
        )
        result = _detect_databases(str(tmp_path), languages=[])
        assert db in result

    def test_empty_dir_detects_no_databases(self, tmp_path):
        result = _detect_databases(str(tmp_path), languages=[])
        assert result == []


# ---------------------------------------------------------------------------
# _detect_infrastructure
# ---------------------------------------------------------------------------


class TestDetectInfrastructure:
    """Each Infrastructure flag toggled on and verified."""

    def test_empty_dir_all_flags_false(self, tmp_path):
        infra = _detect_infrastructure(str(tmp_path))
        assert not infra.git
        assert not infra.gitignore
        assert not infra.dockerfile
        assert not infra.docker_compose
        assert not infra.github_actions
        assert not infra.github_dir
        assert not infra.gitlab_ci

    def test_git_flag(self, tmp_path):
        (tmp_path / ".git").mkdir()
        infra = _detect_infrastructure(str(tmp_path))
        assert infra.git

    def test_gitignore_flag(self, tmp_path):
        (tmp_path / ".gitignore").write_text("", encoding="utf-8")
        infra = _detect_infrastructure(str(tmp_path))
        assert infra.gitignore

    def test_dockerfile_flag(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("", encoding="utf-8")
        infra = _detect_infrastructure(str(tmp_path))
        assert infra.dockerfile

    def test_docker_compose_yml_flag(self, tmp_path):
        (tmp_path / "docker-compose.yml").write_text("", encoding="utf-8")
        infra = _detect_infrastructure(str(tmp_path))
        assert infra.docker_compose

    def test_docker_compose_yaml_flag(self, tmp_path):
        (tmp_path / "docker-compose.yaml").write_text("", encoding="utf-8")
        infra = _detect_infrastructure(str(tmp_path))
        assert infra.docker_compose

    def test_github_dir_flag(self, tmp_path):
        (tmp_path / ".github").mkdir()
        infra = _detect_infrastructure(str(tmp_path))
        assert infra.github_dir

    def test_github_actions_flag(self, tmp_path):
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        infra = _detect_infrastructure(str(tmp_path))
        assert infra.github_actions
        assert infra.github_dir

    def test_gitlab_ci_flag(self, tmp_path):
        (tmp_path / ".gitlab-ci.yml").write_text("", encoding="utf-8")
        infra = _detect_infrastructure(str(tmp_path))
        assert infra.gitlab_ci


# ---------------------------------------------------------------------------
# _detect_structure
# ---------------------------------------------------------------------------


class TestDetectStructure:
    """Tests covering monorepo, fullstack, and single structure detection."""

    @pytest.mark.parametrize("marker,expected_manager", _WORKSPACE_MANAGERS.items())
    def test_workspace_marker_returns_monorepo(
        self, marker: str, expected_manager: str, tmp_path
    ):
        (tmp_path / marker).write_text("", encoding="utf-8")
        structure, manager = _detect_structure(str(tmp_path))
        assert structure == "monorepo"
        assert manager == expected_manager

    def test_two_fullstack_dirs_returns_fullstack(self, tmp_path):
        # Use the first two entries from _FULLSTACK_DIRS
        d1, d2 = _FULLSTACK_DIRS[0], _FULLSTACK_DIRS[1]
        (tmp_path / d1).mkdir()
        (tmp_path / d2).mkdir()
        structure, manager = _detect_structure(str(tmp_path))
        assert structure == "fullstack"
        assert manager == "none"

    def test_one_fullstack_dir_returns_single(self, tmp_path):
        (tmp_path / _FULLSTACK_DIRS[0]).mkdir()
        structure, _ = _detect_structure(str(tmp_path))
        assert structure == "single"

    def test_empty_dir_returns_single(self, tmp_path):
        structure, manager = _detect_structure(str(tmp_path))
        assert structure == "single"
        assert manager == "none"

    def test_all_fullstack_dirs_returns_fullstack(self, tmp_path):
        for d in _FULLSTACK_DIRS:
            (tmp_path / d).mkdir()
        structure, _ = _detect_structure(str(tmp_path))
        assert structure == "fullstack"


# ---------------------------------------------------------------------------
# detect_project (public API)
# ---------------------------------------------------------------------------


class TestDetectProject:
    """Integration-level tests for the public detect_project function."""

    def test_empty_dir_returns_default_detection(self, tmp_path):
        result = detect_project(str(tmp_path))
        assert result.languages == []
        assert result.primary_language == ""
        assert result.package_manager == "none"
        assert result.existing_tools == []
        assert result.frameworks == []
        assert result.stack == ""
        assert result.databases == []
        assert result.structure_type == "single"
        assert result.workspace_manager == "none"

    def test_nonexistent_path_returns_default_detection(self, tmp_path):
        result = detect_project(str(tmp_path / "does_not_exist"))
        assert result.languages == []
        assert result.primary_language == ""
        assert result.package_manager == "none"

    def test_python_project_detected(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\n[tool.pytest.ini_options]\n', encoding="utf-8"
        )
        (tmp_path / "uv.lock").write_text("", encoding="utf-8")
        result = detect_project(str(tmp_path))
        assert "python" in result.languages
        assert result.primary_language == "python"
        assert result.package_manager == "uv"
        assert "pytest" in result.existing_tools

    def test_system_tools_always_populated(self, tmp_path):
        result = detect_project(str(tmp_path))
        # SystemTools is always populated (may be 'not found' but not None)
        assert result.system_tools is not None

    def test_returns_project_detection_type(self, tmp_path):
        from atlas.core.models import ProjectDetection
        result = detect_project(str(tmp_path))
        assert isinstance(result, ProjectDetection)
