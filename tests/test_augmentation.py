"""Tests for augment_errors and find_rule_hint (issue #98)."""

from __future__ import annotations

from atlas.core.runner import augment_errors, find_rule_hint


class TestFindRuleHint:
    def test_known_code_returns_hint(self):
        rules = {"E501": "Line too long — break at logical point"}
        assert find_rule_hint("E501", rules) == "Line too long — break at logical point"

    def test_unknown_code_returns_empty_string(self):
        rules = {"E501": "Line too long"}
        assert find_rule_hint("F401", rules) == ""

    def test_empty_rules_returns_empty_string(self):
        assert find_rule_hint("E501", {}) == ""


class TestAugmentErrors:
    def test_matching_code_gets_hint_appended(self):
        rules = {"E501": "Line too long"}
        output = "file.py:1:80 E501 Line too long (100 > 88)"
        result = augment_errors(output, rules)
        assert "Line too long" in result
        assert result.count("\n") == 1  # original line + hint line

    def test_hint_indented_with_emoji(self):
        rules = {"E501": "Line too long"}
        output = "file.py:1:80 E501 Line too long"
        result = augment_errors(output, rules)
        lines = result.split("\n")
        assert lines[1].startswith("    📎")

    def test_unknown_code_not_augmented(self):
        rules = {"E501": "Line too long"}
        output = "file.py:1:1 F401 'os' imported but unused"
        result = augment_errors(output, rules)
        assert result == output  # no change

    def test_empty_module_rules_returns_output_unchanged(self):
        output = "file.py:1:80 E501 Line too long"
        assert augment_errors(output, {}) == output

    def test_multiple_codes_all_augmented(self):
        rules = {"E501": "Line too long", "F401": "Remove unused import"}
        output = "file.py:1:80 E501 Line too long\nfile.py:2:1 F401 'os' unused"
        result = augment_errors(output, rules)
        assert "Line too long" in result
        assert "Remove unused import" in result
        assert result.count("📎") == 2

    def test_clean_output_no_codes_unchanged(self):
        rules = {"E501": "Line too long"}
        output = "All checks passed!"
        assert augment_errors(output, rules) == output
