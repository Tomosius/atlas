"""Tests for atlas.parser (ParsedInput + parse_input)."""

from __future__ import annotations

import pytest

from atlas.parser import RESOURCE_TYPES, VERBS, ParsedInput, parse_input


# ---------------------------------------------------------------------------
# ParsedInput dataclass
# ---------------------------------------------------------------------------


class TestParsedInput:
    def test_default_verb_is_none(self):
        assert ParsedInput().verb is None

    def test_default_resource_type_is_none(self):
        assert ParsedInput().resource_type is None

    def test_default_contexts_is_empty_list(self):
        assert ParsedInput().contexts == []

    def test_default_args_is_empty_list(self):
        assert ParsedInput().args == []

    def test_default_message_is_none(self):
        assert ParsedInput().message is None

    def test_instances_have_independent_mutable_defaults(self):
        a = ParsedInput()
        b = ParsedInput()
        a.contexts.append(["python"])
        assert b.contexts == []

    def test_can_construct_with_all_fields(self):
        p = ParsedInput(
            verb="add",
            resource_type="note",
            contexts=[["python"]],
            args=["django"],
            message="hello",
        )
        assert p.verb == "add"
        assert p.resource_type == "note"
        assert p.contexts == [["python"]]
        assert p.args == ["django"]
        assert p.message == "hello"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_verbs_contains_all_10(self):
        expected = {"init", "add", "create", "edit", "remove", "list", "just", "vcs", "crud", "sync"}
        assert expected == set(VERBS)

    def test_resource_types_contains_four(self):
        expected = {"note", "prompt", "task", "scope"}
        assert expected == set(RESOURCE_TYPES)


# ---------------------------------------------------------------------------
# parse_input — empty / whitespace
# ---------------------------------------------------------------------------


class TestParseEmpty:
    def test_empty_string_returns_empty_parsed(self):
        result = parse_input("")
        assert result.verb is None
        assert result.contexts == []
        assert result.args == []
        assert result.message is None

    def test_whitespace_only_returns_empty_parsed(self):
        result = parse_input("   ")
        assert result.verb is None
        assert result.contexts == []


# ---------------------------------------------------------------------------
# parse_input — context queries (no verb)
# ---------------------------------------------------------------------------


class TestParseContextQueries:
    def test_single_module(self):
        result = parse_input("python")
        assert result.verb is None
        assert result.contexts == [["python"]]

    def test_module_with_filter(self):
        result = parse_input("python linter")
        assert result.contexts == [["python", "linter"]]

    def test_module_with_two_filters(self):
        result = parse_input("python linter rules")
        assert result.contexts == [["python", "linter", "rules"]]

    def test_comma_produces_two_context_groups(self):
        result = parse_input("python, svelte")
        assert result.contexts == [["python"], ["svelte"]]

    def test_comma_with_filters(self):
        result = parse_input("python linter, svelte style")
        assert result.contexts == [["python", "linter"], ["svelte", "style"]]

    def test_three_comma_groups(self):
        result = parse_input("python, svelte, rust")
        assert result.contexts == [["python"], ["svelte"], ["rust"]]

    def test_status_as_context(self):
        result = parse_input("status")
        assert result.verb is None
        assert result.contexts == [["status"]]

    def test_prompt_design_as_context(self):
        result = parse_input("prompt design")
        assert result.contexts == [["prompt", "design"]]

    def test_extra_spaces_around_comma(self):
        result = parse_input("python ,  svelte")
        assert result.contexts == [["python"], ["svelte"]]

    def test_leading_trailing_whitespace_trimmed(self):
        result = parse_input("  python linter  ")
        assert result.contexts == [["python", "linter"]]


# ---------------------------------------------------------------------------
# parse_input — double dash passthrough
# ---------------------------------------------------------------------------


class TestParseDoubleDash:
    def test_double_dash_splits_message(self):
        result = parse_input("python -- refactor auth")
        assert result.contexts == [["python"]]
        assert result.message == "refactor auth"

    def test_double_dash_with_verb(self):
        result = parse_input("init -- some note")
        assert result.verb == "init"
        assert result.message == "some note"

    def test_double_dash_message_preserved_exactly(self):
        result = parse_input("python -- the message with   spaces")
        assert result.message == "the message with   spaces"

    def test_double_dash_with_context_and_filter(self):
        result = parse_input("prompt design -- src/auth.py")
        assert result.contexts == [["prompt", "design"]]
        assert result.message == "src/auth.py"

    def test_no_double_dash_message_is_none(self):
        result = parse_input("python linter")
        assert result.message is None

    def test_single_dash_not_treated_as_separator(self):
        result = parse_input("python - linter")
        assert result.contexts == [["python", "-", "linter"]]
        assert result.message is None


# ---------------------------------------------------------------------------
# parse_input — verb detection
# ---------------------------------------------------------------------------


class TestParseVerbs:
    @pytest.mark.parametrize("verb", ["init", "add", "create", "edit", "remove",
                                       "list", "just", "vcs", "crud", "sync"])
    def test_all_verbs_detected(self, verb):
        result = parse_input(verb)
        assert result.verb == verb
        assert result.contexts == []

    def test_verb_case_insensitive(self):
        result = parse_input("INIT")
        assert result.verb == "init"

    def test_verb_mixed_case(self):
        result = parse_input("Add ruff")
        assert result.verb == "add"
        assert result.args == ["ruff"]

    def test_init_no_args(self):
        result = parse_input("init")
        assert result.verb == "init"
        assert result.args == []

    def test_init_with_force_flag(self):
        result = parse_input("init --force")
        assert result.verb == "init"
        assert result.args == ["--force"]

    def test_add_single_module(self):
        result = parse_input("add django")
        assert result.verb == "add"
        assert result.args == ["django"]

    def test_add_multiple_modules(self):
        result = parse_input("add ruff pytest")
        assert result.verb == "add"
        assert result.args == ["ruff", "pytest"]

    def test_list_no_args(self):
        result = parse_input("list")
        assert result.verb == "list"
        assert result.args == []

    def test_list_with_arg(self):
        result = parse_input("list modules")
        assert result.verb == "list"
        assert result.args == ["modules"]

    def test_just_with_task(self):
        result = parse_input("just check")
        assert result.verb == "just"
        assert result.args == ["check"]

    def test_vcs_commit(self):
        result = parse_input("vcs commit")
        assert result.verb == "vcs"
        assert result.args == ["commit"]

    def test_vcs_smart_commit(self):
        result = parse_input("vcs smart commit")
        assert result.verb == "vcs"
        assert result.args == ["smart", "commit"]

    def test_crud_issues(self):
        result = parse_input("crud issues")
        assert result.verb == "crud"
        assert result.args == ["issues"]

    def test_crud_focus(self):
        result = parse_input("crud focus 42")
        assert result.verb == "crud"
        assert result.args == ["focus", "42"]

    def test_sync_no_args(self):
        result = parse_input("sync")
        assert result.verb == "sync"
        assert result.args == []

    def test_sync_with_arg(self):
        result = parse_input("sync update")
        assert result.verb == "sync"
        assert result.args == ["update"]

    def test_remove_module_no_resource_type(self):
        result = parse_input("remove django")
        assert result.verb == "remove"
        assert result.resource_type is None
        assert result.args == ["django"]


# ---------------------------------------------------------------------------
# parse_input — resource_type detection
# ---------------------------------------------------------------------------


class TestParseResourceType:
    def test_create_note(self):
        result = parse_input("create note python use-async")
        assert result.verb == "create"
        assert result.resource_type == "note"
        assert result.args == ["python", "use-async"]

    def test_create_prompt(self):
        result = parse_input("create prompt security")
        assert result.verb == "create"
        assert result.resource_type == "prompt"
        assert result.args == ["security"]

    def test_create_task(self):
        result = parse_input("create task lint cmd")
        assert result.verb == "create"
        assert result.resource_type == "task"
        assert result.args == ["lint", "cmd"]

    def test_create_scope(self):
        result = parse_input("create scope auth src/auth/")
        assert result.verb == "create"
        assert result.resource_type == "scope"
        assert result.args == ["auth", "src/auth/"]

    def test_edit_note(self):
        result = parse_input("edit note python 1 new text")
        assert result.verb == "edit"
        assert result.resource_type == "note"
        assert result.args == ["python", "1", "new", "text"]

    def test_edit_task(self):
        result = parse_input("edit task lint new_cmd")
        assert result.verb == "edit"
        assert result.resource_type == "task"
        assert result.args == ["lint", "new_cmd"]

    def test_remove_note_with_resource_type(self):
        result = parse_input("remove note python 1")
        assert result.verb == "remove"
        assert result.resource_type == "note"
        assert result.args == ["python", "1"]

    def test_remove_task_with_resource_type(self):
        result = parse_input("remove task lint")
        assert result.verb == "remove"
        assert result.resource_type == "task"
        assert result.args == ["lint"]

    def test_remove_with_only_resource_type_no_extra_args_no_resource_type_set(self):
        # "remove note" has len(rest)==1 which is < 2, so resource_type not set
        result = parse_input("remove note")
        assert result.verb == "remove"
        assert result.resource_type is None
        assert result.args == ["note"]

    def test_create_without_resource_type_puts_rest_in_args(self):
        result = parse_input("create mymodule")
        assert result.verb == "create"
        assert result.resource_type is None
        assert result.args == ["mymodule"]

    def test_resource_type_not_set_for_non_create_edit_remove(self):
        result = parse_input("add note")
        assert result.verb == "add"
        assert result.resource_type is None
        assert result.args == ["note"]


# ---------------------------------------------------------------------------
# parse_input — return type
# ---------------------------------------------------------------------------


class TestParseReturnType:
    def test_returns_parsed_input_instance(self):
        assert isinstance(parse_input("python"), ParsedInput)

    def test_verb_mode_contexts_empty(self):
        result = parse_input("add ruff")
        assert result.contexts == []

    def test_context_mode_verb_none(self):
        result = parse_input("python linter")
        assert result.verb is None

    def test_context_mode_resource_type_none(self):
        result = parse_input("python linter")
        assert result.resource_type is None
