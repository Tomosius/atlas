"""Smoke tests — verify the package imports without errors."""

from atlas.core import detection, errors, models, system


def test_models_importable() -> None:
    assert hasattr(models, "ProjectDetection")
    assert hasattr(models, "Infrastructure")
    assert hasattr(models, "SystemTools")


def test_errors_importable() -> None:
    assert hasattr(errors, "ok_result")
    assert hasattr(errors, "error_result")
    assert hasattr(errors, "AtlasError")


def test_system_importable() -> None:
    assert hasattr(system, "run_command")
    assert hasattr(system, "check_tool")
    assert hasattr(system, "detect_system_tools")


def test_detection_importable() -> None:
    assert hasattr(detection, "detect_project")


def test_ok_result() -> None:
    result = errors.ok_result(data="hello")
    assert result["ok"] is True
    assert result["data"] == "hello"


def test_error_result() -> None:
    result = errors.error_result("MODULE_NOT_FOUND", "ruff")
    assert result["ok"] is False
    assert result["error"] == "MODULE_NOT_FOUND"


def test_project_detection_defaults() -> None:
    d = models.ProjectDetection()
    assert d.languages == []
    assert d.primary_language == ""
    assert d.package_manager == "none"


def test_detect_project_empty(tmp_path) -> None:
    result = detection.detect_project(str(tmp_path))
    assert result.languages == []
    assert result.package_manager == "none"
