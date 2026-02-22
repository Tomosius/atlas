# Design: Error Augmentation in `just` Verb (Issue #98)

## What We're Building

When `atlas just check` (or any task) fails, Atlas enriches the output with
relevant rule hints — the rule appears RIGHT NEXT to the violation.

```
src/auth/oauth.py:42:5 E501 Line too long (145 > 120)
    📎 Rule: Line length limit is 120 (from ruff.toml).
```

## Reference

- `plan/05-ATLAS-API.md §13` — error augmentation spec + `augment_errors` pseudocode
- `src/atlas/core/runner.py` — `run_task` returns `{ok, task, output, returncode}`
- `src/atlas/runtime.py:277` — `just` verb (currently calls `run_task` and returns)
- Issue #99 will add the actual error code → hint mappings per linter

## What Changes

### `src/atlas/core/runner.py`

Two new module-level functions:

```python
import re

def find_rule_hint(code: str, module_rules: dict) -> str:
    """Return the rule hint for *code* from module_rules, or ''."""
    return module_rules.get(code, "")


def augment_errors(output: str, module_rules: dict) -> str:
    """Scan tool output for error codes, append relevant rule hints inline."""
    if not module_rules:
        return output
    lines = output.split("\n")
    augmented = []
    for line in lines:
        augmented.append(line)
        code_match = re.search(r'\b([A-Z]\d{3,4})\b', line)
        if code_match:
            hint = find_rule_hint(code_match.group(1), module_rules)
            if hint:
                augmented.append(f"    \U0001f4ce {hint}")
    return "\n".join(augmented)
```

### `src/atlas/runtime.py`

Update the `just` verb to:
1. Collect merged error code → hint mappings from all installed modules
   (each module's `.atlas/modules/<name>.json` may have an `"error_codes"` key — a `{code: hint}` dict; issue #99 populates this)
2. After `run_task`, if `returncode != 0` and we have mappings, augment the output

```python
# In runtime.py just():
result = run_task(task_name, command, self.project_dir)

# Augment output on failure
if result.get("ok") and result.get("returncode", 0) != 0:
    merged_codes: dict[str, str] = {}
    for mod_name in installed_mods:
        mod_json = self._load_json(
            os.path.join(self.atlas_dir, "modules", f"{mod_name}.json"), {}
        )
        merged_codes.update(mod_json.get("error_codes", {}))
    if merged_codes:
        result["output"] = augment_errors(result["output"], merged_codes)

return result
```

### `tests/test_augmentation.py` (new file)

**`TestFindRuleHint`** (3 tests):
- `test_known_code_returns_hint`
- `test_unknown_code_returns_empty_string`
- `test_empty_rules_returns_empty_string`

**`TestAugmentErrors`** (6 tests):
- `test_matching_code_gets_hint_appended`
- `test_hint_indented_with_emoji`
- `test_unknown_code_not_augmented`
- `test_empty_module_rules_returns_output_unchanged`
- `test_multiple_codes_all_augmented`
- `test_clean_output_no_codes_unchanged`

**`TestJustWithAugmentation`** (3 tests in existing `tests/test_runtime.py`):
- `test_just_augments_output_on_failure_with_error_codes`
- `test_just_does_not_augment_on_success`
- `test_just_does_not_augment_when_no_error_codes_in_modules`

## Acceptance Criteria

- `augment_errors` and `find_rule_hint` in `runner.py`, exported
- `just` verb augments output when task fails and error_codes present
- `just` verb leaves output unchanged on success or empty mappings
- 9 new tests in `tests/test_augmentation.py` + 3 in `tests/test_runtime.py`
- All existing tests pass
