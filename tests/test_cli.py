"""Tests for atlas.cli (run, _print_result, main)."""

from __future__ import annotations

import json
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from atlas.cli import _print_result, run


# ---------------------------------------------------------------------------
# _print_result
# ---------------------------------------------------------------------------


class TestPrintResult:
    def test_string_printed_to_stdout(self, capsys):
        _print_result("hello world")
        out, _ = capsys.readouterr()
        assert "hello world" in out

    def test_success_dict_printed_as_json(self, capsys):
        _print_result({"ok": True, "data": "x"})
        out, _ = capsys.readouterr()
        parsed = json.loads(out)
        assert parsed["ok"] is True

    def test_error_dict_printed_to_stderr(self, capsys):
        _print_result({"ok": False, "error": "NOT_INITIALIZED", "detail": "run init first"})
        _, err = capsys.readouterr()
        assert "run init first" in err

    def test_error_dict_nothing_on_stdout(self, capsys):
        _print_result({"ok": False, "error": "X", "detail": "msg"})
        out, _ = capsys.readouterr()
        assert out == ""

    def test_other_type_printed_as_str(self, capsys):
        _print_result(42)
        out, _ = capsys.readouterr()
        assert "42" in out

    def test_none_printed_as_str(self, capsys):
        _print_result(None)
        out, _ = capsys.readouterr()
        assert "None" in out


# ---------------------------------------------------------------------------
# run() — routing and return codes
# ---------------------------------------------------------------------------


def _patched_atlas(method_name: str, return_value: object):
    """Return a context manager that patches Atlas.<method_name>."""
    return patch(f"atlas.cli.Atlas.{method_name}", return_value=return_value)


class TestRunReturnCodes:
    def test_success_dict_returns_zero(self, capsys):
        with patch("atlas.cli.Atlas.query", return_value="# Python\nsome rules"):
            code = run("python")
        assert code == 0

    def test_error_dict_returns_one(self, capsys):
        with patch("atlas.cli.Atlas.add_modules", return_value={"ok": False, "error": "X", "detail": "d"}):
            code = run("add nonexistent")
        assert code == 1

    def test_string_result_returns_zero(self, capsys):
        with patch("atlas.cli.Atlas.query", return_value="some content"):
            code = run("python")
        assert code == 0


class TestRunRouting:
    def test_no_verb_calls_query(self):
        with patch("atlas.cli.Atlas.query", return_value="ok") as mock:
            run("python linter")
        mock.assert_called_once()
        args, _ = mock.call_args
        assert args[0] == [["python", "linter"]]

    def test_add_verb_calls_add_modules(self):
        with patch("atlas.cli.Atlas.add_modules", return_value={"ok": True}) as mock:
            run("add ruff pytest")
        mock.assert_called_once_with(["ruff", "pytest"])

    def test_remove_verb_no_resource_calls_remove_module(self):
        with patch("atlas.cli.Atlas.remove_module", return_value={"ok": True}) as mock:
            run("remove ruff")
        mock.assert_called_once_with("ruff")

    def test_just_verb_calls_just(self):
        with patch("atlas.cli.Atlas.just", return_value={"ok": True, "output": ""}) as mock:
            run("just check")
        mock.assert_called_once_with("check", [])

    def test_just_verb_with_extra_args(self):
        with patch("atlas.cli.Atlas.just", return_value={"ok": True, "output": ""}) as mock:
            run("just check --fix")
        mock.assert_called_once_with("check", ["--fix"])

    def test_empty_input_calls_query_with_empty_contexts(self, capsys):
        with patch("atlas.cli.Atlas.query", return_value="") as mock:
            run("")
        mock.assert_called_once_with([], None)

    def test_double_dash_passes_message(self):
        with patch("atlas.cli.Atlas.query", return_value="ok") as mock:
            run("python -- refactor auth")
        _, kwargs = mock.call_args if mock.call_args.kwargs else (mock.call_args.args, {})
        args = mock.call_args.args
        assert args[1] == "refactor auth"

    def test_unknown_verb_not_possible_via_parse(self, capsys):
        # All 10 verbs are handled; unknown first word becomes a context query
        with patch("atlas.cli.Atlas.query", return_value="ok") as mock:
            run("unknownverb")
        mock.assert_called_once()


class TestRunOutput:
    def test_string_query_result_printed(self, capsys):
        with patch("atlas.cli.Atlas.query", return_value="# Python rules"):
            run("python")
        out, _ = capsys.readouterr()
        assert "# Python rules" in out

    def test_success_dict_printed_as_json(self, capsys):
        with patch("atlas.cli.Atlas.add_modules", return_value={"ok": True, "installed": ["ruff"]}):
            run("add ruff")
        out, _ = capsys.readouterr()
        parsed = json.loads(out)
        assert parsed["ok"] is True

    def test_error_goes_to_stderr(self, capsys):
        with patch("atlas.cli.Atlas.remove_module", return_value={"ok": False, "error": "E", "detail": "bad"}):
            run("remove ruff")
        _, err = capsys.readouterr()
        assert "bad" in err


# ---------------------------------------------------------------------------
# main() — sys.argv integration
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_exits_zero_on_success(self):
        with patch("sys.argv", ["atlas", "python"]):
            with patch("atlas.cli.Atlas.query", return_value="content"):
                with pytest.raises(SystemExit) as exc_info:
                    from atlas.cli import main
                    main()
        assert exc_info.value.code == 0

    def test_main_exits_one_on_error(self):
        with patch("sys.argv", ["atlas", "add", "nonexistent"]):
            with patch("atlas.cli.Atlas.add_modules", return_value={"ok": False, "error": "X", "detail": "d"}):
                with pytest.raises(SystemExit) as exc_info:
                    from atlas.cli import main
                    main()
        assert exc_info.value.code == 1

    def test_main_joins_argv_as_single_string(self):
        with patch("sys.argv", ["atlas", "add", "ruff", "pytest"]):
            with patch("atlas.cli.Atlas.add_modules", return_value={"ok": True}) as mock:
                with pytest.raises(SystemExit):
                    from atlas.cli import main
                    main()
        mock.assert_called_once_with(["ruff", "pytest"])

    def test_main_no_args_runs_query(self):
        with patch("sys.argv", ["atlas"]):
            with patch("atlas.cli.Atlas.query", return_value="") as mock:
                with pytest.raises(SystemExit):
                    from atlas.cli import main
                    main()
        mock.assert_called_once()
