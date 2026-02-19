"""Config scanner: reads tool configuration from project files."""

from __future__ import annotations

import configparser
import fnmatch
import json
import os


# --- Data tables ---

# Maps module name → ordered list of config file locations.
# Each entry: {file, format, section, priority}
# format values: toml | json | ini | yaml | gomod | exists | dir | glob_exists
# priority: lower = checked first; first found wins.
MODULE_CONFIG_MAP: dict[str, list[dict]] = {
    # --- Languages ---
    "python": [
        {"file": "pyproject.toml", "format": "toml", "section": "[project]", "priority": 1},
        {"file": "setup.cfg", "format": "ini", "section": "metadata", "priority": 2},
        {"file": "setup.py", "format": "exists", "section": None, "priority": 3},
        {"file": "requirements.txt", "format": "exists", "section": None, "priority": 4},
    ],
    "typescript": [
        {"file": "tsconfig.json", "format": "json", "section": None, "priority": 1},
        {"file": "tsconfig.base.json", "format": "json", "section": None, "priority": 2},
    ],
    "rust": [
        {"file": "Cargo.toml", "format": "toml", "section": "[package]", "priority": 1},
    ],
    "go": [
        {"file": "go.mod", "format": "gomod", "section": None, "priority": 1},
    ],
    "java": [
        {"file": "pom.xml", "format": "exists", "section": None, "priority": 1},
        {"file": "build.gradle", "format": "exists", "section": None, "priority": 2},
        {"file": "build.gradle.kts", "format": "exists", "section": None, "priority": 3},
    ],
    "ruby": [
        {"file": "Gemfile", "format": "exists", "section": None, "priority": 1},
        {"file": ".ruby-version", "format": "exists", "section": None, "priority": 2},
    ],
    "cpp": [
        {"file": "CMakeLists.txt", "format": "exists", "section": None, "priority": 1},
        {"file": "Makefile", "format": "exists", "section": None, "priority": 2},
    ],
    "csharp": [
        {"file": "*.csproj", "format": "glob_exists", "section": None, "priority": 1},
        {"file": "*.sln", "format": "glob_exists", "section": None, "priority": 2},
    ],
    "html": [
        {"file": "index.html", "format": "exists", "section": None, "priority": 1},
    ],
    "css": [
        {"file": "*.css", "format": "glob_exists", "section": None, "priority": 1},
        {"file": "*.scss", "format": "glob_exists", "section": None, "priority": 2},
    ],
    # --- Linters ---
    "ruff": [
        {"file": "pyproject.toml", "format": "toml", "section": "[tool.ruff]", "priority": 1},
        {"file": "ruff.toml", "format": "toml", "section": None, "priority": 2},
        {"file": ".ruff.toml", "format": "toml", "section": None, "priority": 3},
    ],
    "eslint": [
        {"file": "eslint.config.js", "format": "exists", "section": None, "priority": 1},
        {"file": "eslint.config.mjs", "format": "exists", "section": None, "priority": 2},
        {"file": ".eslintrc.json", "format": "json", "section": None, "priority": 3},
        {"file": ".eslintrc.js", "format": "exists", "section": None, "priority": 4},
        {"file": "package.json", "format": "json", "section": "eslintConfig", "priority": 5},
    ],
    "biome": [
        {"file": "biome.json", "format": "json", "section": None, "priority": 1},
        {"file": "biome.jsonc", "format": "json", "section": None, "priority": 2},
    ],
    "clippy": [
        {"file": "Cargo.toml", "format": "toml", "section": "[lints.clippy]", "priority": 1},
        {"file": ".clippy.toml", "format": "toml", "section": None, "priority": 2},
    ],
    "flake8": [
        {"file": "setup.cfg", "format": "ini", "section": "flake8", "priority": 1},
        {"file": ".flake8", "format": "ini", "section": "flake8", "priority": 2},
        {"file": "tox.ini", "format": "ini", "section": "flake8", "priority": 3},
    ],
    "golangci-lint": [
        {"file": ".golangci.yml", "format": "yaml", "section": None, "priority": 1},
        {"file": ".golangci.yaml", "format": "yaml", "section": None, "priority": 2},
        {"file": ".golangci.toml", "format": "toml", "section": None, "priority": 3},
        {"file": ".golangci.json", "format": "json", "section": None, "priority": 4},
    ],
    # --- Formatters ---
    "prettier": [
        {"file": ".prettierrc", "format": "json", "section": None, "priority": 1},
        {"file": ".prettierrc.json", "format": "json", "section": None, "priority": 2},
        {"file": ".prettierrc.yml", "format": "yaml", "section": None, "priority": 3},
        {"file": ".prettierrc.yaml", "format": "yaml", "section": None, "priority": 4},
        {"file": "prettier.config.js", "format": "exists", "section": None, "priority": 5},
        {"file": "package.json", "format": "json", "section": "prettier", "priority": 6},
    ],
    "rustfmt": [
        {"file": "rustfmt.toml", "format": "toml", "section": None, "priority": 1},
        {"file": ".rustfmt.toml", "format": "toml", "section": None, "priority": 2},
    ],
    "gofmt": [
        {"file": "go.mod", "format": "gomod", "section": None, "priority": 1},
    ],
    # --- Testing ---
    "pytest": [
        {
            "file": "pyproject.toml",
            "format": "toml",
            "section": "[tool.pytest.ini_options]",
            "priority": 1,
        },
        {"file": "pytest.ini", "format": "ini", "section": "pytest", "priority": 2},
        {"file": "setup.cfg", "format": "ini", "section": "tool:pytest", "priority": 3},
        {"file": "tox.ini", "format": "ini", "section": "pytest", "priority": 4},
    ],
    "vitest": [
        {"file": "vitest.config.ts", "format": "exists", "section": None, "priority": 1},
        {"file": "vitest.config.js", "format": "exists", "section": None, "priority": 2},
        {"file": "vite.config.ts", "format": "exists", "section": None, "priority": 3},
    ],
    "jest": [
        {"file": "jest.config.ts", "format": "exists", "section": None, "priority": 1},
        {"file": "jest.config.js", "format": "exists", "section": None, "priority": 2},
        {"file": "package.json", "format": "json", "section": "jest", "priority": 3},
    ],
    "playwright": [
        {"file": "playwright.config.ts", "format": "exists", "section": None, "priority": 1},
        {"file": "playwright.config.js", "format": "exists", "section": None, "priority": 2},
    ],
    "cargo-test": [
        {"file": "Cargo.toml", "format": "toml", "section": "[profile.test]", "priority": 1},
    ],
    "go-test": [
        {"file": "go.mod", "format": "gomod", "section": None, "priority": 1},
    ],
    # --- Frameworks ---
    "react": [
        {"file": "package.json", "format": "json", "section": None, "priority": 1},
    ],
    "next-js": [
        {"file": "next.config.js", "format": "exists", "section": None, "priority": 1},
        {"file": "next.config.ts", "format": "exists", "section": None, "priority": 2},
        {"file": "next.config.mjs", "format": "exists", "section": None, "priority": 3},
    ],
    "django": [
        {"file": "manage.py", "format": "exists", "section": None, "priority": 1},
        {"file": "settings.py", "format": "exists", "section": None, "priority": 2},
    ],
    "fastapi": [
        {"file": "pyproject.toml", "format": "toml", "section": "[project]", "priority": 1},
    ],
    "flask": [
        {"file": "pyproject.toml", "format": "toml", "section": "[project]", "priority": 1},
        {"file": ".env", "format": "exists", "section": None, "priority": 2},
    ],
    "svelte": [
        {"file": "svelte.config.js", "format": "exists", "section": None, "priority": 1},
        {"file": "svelte.config.ts", "format": "exists", "section": None, "priority": 2},
    ],
    "vue": [
        {"file": "vue.config.js", "format": "exists", "section": None, "priority": 1},
        {"file": "package.json", "format": "json", "section": None, "priority": 2},
    ],
    "angular": [
        {"file": "angular.json", "format": "json", "section": None, "priority": 1},
    ],
    "express": [
        {"file": "package.json", "format": "json", "section": None, "priority": 1},
    ],
    "nestjs": [
        {"file": "nest-cli.json", "format": "json", "section": None, "priority": 1},
        {"file": "package.json", "format": "json", "section": None, "priority": 2},
    ],
    # --- Databases ---
    "postgresql": [
        {"file": "docker-compose.yml", "format": "yaml", "section": None, "priority": 1},
        {"file": "docker-compose.yaml", "format": "yaml", "section": None, "priority": 2},
        {"file": ".env", "format": "exists", "section": None, "priority": 3},
    ],
    "sqlite": [
        {"file": "*.db", "format": "glob_exists", "section": None, "priority": 1},
        {"file": "*.sqlite3", "format": "glob_exists", "section": None, "priority": 2},
    ],
    "redis": [
        {"file": "redis.conf", "format": "exists", "section": None, "priority": 1},
        {"file": "docker-compose.yml", "format": "yaml", "section": None, "priority": 2},
    ],
    "mongodb": [
        {"file": "docker-compose.yml", "format": "yaml", "section": None, "priority": 1},
        {"file": ".env", "format": "exists", "section": None, "priority": 2},
    ],
    # --- VCS ---
    "git": [
        {"file": ".git", "format": "dir", "section": None, "priority": 1},
        {"file": ".gitignore", "format": "exists", "section": None, "priority": 2},
        {"file": ".gitattributes", "format": "exists", "section": None, "priority": 3},
    ],
    "svn": [
        {"file": ".svn", "format": "dir", "section": None, "priority": 1},
    ],
    "mercurial": [
        {"file": ".hg", "format": "dir", "section": None, "priority": 1},
        {"file": ".hgrc", "format": "ini", "section": None, "priority": 2},
    ],
    "fossil": [
        {"file": ".fslckout", "format": "exists", "section": None, "priority": 1},
        {"file": "_FOSSIL_", "format": "exists", "section": None, "priority": 2},
    ],
    "perforce": [
        {"file": ".p4config", "format": "exists", "section": None, "priority": 1},
    ],
    "plastic-scm": [
        {"file": ".plastic", "format": "dir", "section": None, "priority": 1},
    ],
    # --- Platforms ---
    "github": [
        {"file": ".github", "format": "dir", "section": None, "priority": 1},
    ],
    "gitlab": [
        {"file": ".gitlab-ci.yml", "format": "yaml", "section": None, "priority": 1},
    ],
    "bitbucket": [
        {"file": "bitbucket-pipelines.yml", "format": "yaml", "section": None, "priority": 1},
    ],
    # --- Package Managers ---
    "uv": [
        {"file": "uv.toml", "format": "toml", "section": None, "priority": 1},
        {"file": "pyproject.toml", "format": "toml", "section": "[tool.uv]", "priority": 2},
        {"file": "uv.lock", "format": "exists", "section": None, "priority": 3},
    ],
    "pip": [
        {"file": "requirements.txt", "format": "exists", "section": None, "priority": 1},
        {"file": "pip.conf", "format": "ini", "section": "global", "priority": 2},
    ],
    "pnpm": [
        {"file": "pnpm-lock.yaml", "format": "exists", "section": None, "priority": 1},
        {"file": ".npmrc", "format": "ini", "section": None, "priority": 2},
        {"file": "package.json", "format": "json", "section": None, "priority": 3},
    ],
    "npm": [
        {"file": "package-lock.json", "format": "exists", "section": None, "priority": 1},
        {"file": ".npmrc", "format": "ini", "section": None, "priority": 2},
        {"file": "package.json", "format": "json", "section": None, "priority": 3},
    ],
    "yarn": [
        {"file": "yarn.lock", "format": "exists", "section": None, "priority": 1},
        {"file": ".yarnrc.yml", "format": "yaml", "section": None, "priority": 2},
        {"file": "package.json", "format": "json", "section": None, "priority": 3},
    ],
    "bun": [
        {"file": "bun.lockb", "format": "exists", "section": None, "priority": 1},
        {"file": "bunfig.toml", "format": "toml", "section": None, "priority": 2},
    ],
    "cargo": [
        {"file": "Cargo.lock", "format": "exists", "section": None, "priority": 1},
        {"file": "Cargo.toml", "format": "toml", "section": "[workspace]", "priority": 2},
    ],
    # --- Environments ---
    "docker": [
        {"file": "Dockerfile", "format": "exists", "section": None, "priority": 1},
        {"file": ".dockerignore", "format": "exists", "section": None, "priority": 2},
    ],
    "docker-compose": [
        {"file": "docker-compose.yml", "format": "yaml", "section": None, "priority": 1},
        {"file": "docker-compose.yaml", "format": "yaml", "section": None, "priority": 2},
        {"file": "compose.yml", "format": "yaml", "section": None, "priority": 3},
    ],
    "venv": [
        {"file": ".venv", "format": "dir", "section": None, "priority": 1},
        {"file": "venv", "format": "dir", "section": None, "priority": 2},
    ],
    "node": [
        {"file": ".nvmrc", "format": "exists", "section": None, "priority": 1},
        {"file": ".node-version", "format": "exists", "section": None, "priority": 2},
    ],
    # --- CI/CD ---
    "github-actions": [
        {"file": ".github/workflows", "format": "dir", "section": None, "priority": 1},
    ],
    "gitlab-ci": [
        {"file": ".gitlab-ci.yml", "format": "yaml", "section": None, "priority": 1},
    ],
    "circleci": [
        {"file": ".circleci/config.yml", "format": "yaml", "section": None, "priority": 1},
    ],
    # --- Stacks ---
    "python-backend": [
        {"file": "pyproject.toml", "format": "toml", "section": "[project]", "priority": 1},
    ],
    "python-cli": [
        {
            "file": "pyproject.toml",
            "format": "toml",
            "section": "[project.scripts]",
            "priority": 1,
        },
    ],
    "python-library": [
        {"file": "pyproject.toml", "format": "toml", "section": "[project]", "priority": 1},
    ],
    "ts-frontend": [
        {"file": "package.json", "format": "json", "section": None, "priority": 1},
    ],
    "ts-backend": [
        {"file": "package.json", "format": "json", "section": None, "priority": 1},
        {"file": "tsconfig.json", "format": "json", "section": None, "priority": 2},
    ],
    "fullstack": [
        {"file": "package.json", "format": "json", "section": None, "priority": 1},
    ],
    # --- Tools ---
    "commit-rules": [
        {"file": ".git", "format": "dir", "section": None, "priority": 1},
        {"file": "COMMIT_RULES.md", "format": "exists", "section": None, "priority": 2},
    ],
    # --- Standalone tools (not yet full module bundles, used by detection engine) ---
    "mypy": [
        {"file": "pyproject.toml", "format": "toml", "section": "[tool.mypy]", "priority": 1},
        {"file": "mypy.ini", "format": "ini", "section": "mypy", "priority": 2},
        {"file": ".mypy.ini", "format": "ini", "section": "mypy", "priority": 3},
        {"file": "setup.cfg", "format": "ini", "section": "mypy", "priority": 4},
    ],
    "black": [
        {"file": "pyproject.toml", "format": "toml", "section": "[tool.black]", "priority": 1},
    ],
    "isort": [
        {"file": "pyproject.toml", "format": "toml", "section": "[tool.isort]", "priority": 1},
        {"file": ".isort.cfg", "format": "ini", "section": "settings", "priority": 2},
        {"file": "setup.cfg", "format": "ini", "section": "isort", "priority": 3},
    ],
}

# Maps module name → {raw_config_key: atlas_dotted_path}.
# The scanner extracts these values from the config file and stores them
# under the Atlas internal namespace so rules templates can reference them
# as {{style.line_length}}, {{project.name}}, etc.
MODULE_CONFIG_KEYS: dict[str, dict[str, str]] = {
    # --- Languages ---
    "python": {
        "requires-python": "style.python_version",
        "name": "project.name",
        "version": "project.version",
    },
    "typescript": {
        "strict": "style.strict_mode",
        "target": "style.target",
        "module": "style.module_system",
    },
    "rust": {
        "edition": "style.edition",
        "name": "project.name",
        "version": "project.version",
    },
    "go": {
        "go": "style.go_version",
        "module": "project.module",
    },
    # --- Linters ---
    "ruff": {
        "line-length": "style.line_length",
        "target-version": "style.python_version",
        "select": "style.lint_rules",
        "ignore": "style.lint_ignore",
        "indent-width": "style.indent_width",
    },
    "eslint": {
        "rules": "style.lint_rules",
        "env": "style.environments",
        "extends": "style.extends",
    },
    "biome": {
        "indentStyle": "style.indent_style",
        "indentWidth": "style.indent_width",
        "lineWidth": "style.line_length",
    },
    "flake8": {
        "max-line-length": "style.line_length",
        "max-complexity": "style.max_complexity",
        "extend-ignore": "style.lint_ignore",
        "per-file-ignores": "style.per_file_ignores",
    },
    "golangci-lint": {
        "timeout": "testing.timeout",
        "issues-exit-code": "style.exit_code",
    },
    # --- Formatters ---
    "prettier": {
        "printWidth": "style.line_length",
        "tabWidth": "style.indent_width",
        "useTabs": "style.use_tabs",
        "singleQuote": "style.single_quote",
        "trailingComma": "style.trailing_comma",
        "semi": "style.semicolons",
    },
    "rustfmt": {
        "max_width": "style.line_length",
        "tab_spaces": "style.indent_width",
        "edition": "style.edition",
    },
    # --- Testing ---
    "pytest": {
        "testpaths": "testing.test_dirs",
        "pythonpath": "testing.python_path",
        "addopts": "testing.extra_args",
        "minversion": "testing.min_version",
    },
    "vitest": {
        "testTimeout": "testing.timeout",
        "coverage": "testing.coverage",
    },
    "jest": {
        "testTimeout": "testing.timeout",
        "coverageDirectory": "testing.coverage_dir",
        "testEnvironment": "testing.environment",
    },
    # --- Package Managers ---
    "uv": {
        "dev-dependencies": "project.dev_dependencies",
        "python": "style.python_version",
    },
    "cargo": {
        "edition": "style.edition",
        "resolver": "project.resolver",
    },
    # --- Standalone tools ---
    "mypy": {
        "python_version": "style.python_version",
        "strict": "style.strict_mode",
        "ignore_missing_imports": "style.ignore_missing_imports",
    },
    "black": {
        "line-length": "style.line_length",
        "target-version": "style.python_version",
        "skip-string-normalization": "style.skip_string_normalization",
    },
    "isort": {
        "line_length": "style.line_length",
        "profile": "style.profile",
        "known_first_party": "style.first_party_imports",
    },
}


# --- TOML parser (stdlib only — no tomllib / tomli) ---


def _read_file_safe(path: str) -> str:
    """Read a file and return its contents, or empty string on any error."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def _brackets_balanced(text: str) -> bool:
    """Return True if all square brackets in text are balanced."""
    depth = 0
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _read_toml_section(content: str, section: str) -> str:
    """Extract the text of a TOML section (between its header and the next header).

    Args:
        content: Full TOML file content as a string.
        section: Section header to find, e.g. ``"[tool.ruff]"``.

    Returns:
        The text between the section header and the next ``[`` header,
        or an empty string if the section is not found.
    """
    lines = content.splitlines()
    section_stripped = section.strip()
    inside = False
    result: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped == section_stripped:
            inside = True
            continue
        if inside:
            # Stop at the next section header (but not array-of-tables like [[x]])
            if stripped.startswith("[") and not stripped.startswith("[["):
                break
            result.append(line)

    return "\n".join(result)


def _parse_toml_array(raw: str) -> list:
    """Parse a TOML inline array string like ``'["a", "b"]'`` into a list.

    Handles:
    - String elements (single or double quoted)
    - Integer and boolean elements
    - Nested brackets balanced check for multiline continuation
    """
    raw = raw.strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        return []
    inner = raw[1:-1].strip()
    if not inner:
        return []

    items: list = []
    current = ""
    in_string = False
    string_char = ""
    depth = 0

    for ch in inner:
        if in_string:
            current += ch
            if ch == string_char:
                in_string = False
        elif ch in ('"', "'"):
            in_string = True
            string_char = ch
            current += ch
        elif ch == "[":
            depth += 1
            current += ch
        elif ch == "]":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            items.append(_parse_toml_value(current.strip()))
            current = ""
        else:
            current += ch

    if current.strip():
        items.append(_parse_toml_value(current.strip()))

    return items


def _parse_toml_value(raw: str) -> str | int | list | bool:
    """Convert a raw TOML value string to a Python type.

    Handles: quoted strings, integers, booleans (true/false), and arrays.
    Falls back to returning the raw string for anything else.
    """
    raw = raw.strip()

    # Quoted string (single or double)
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]

    # Inline array
    if raw.startswith("["):
        return _parse_toml_array(raw)

    # Boolean
    if raw == "true":
        return True
    if raw == "false":
        return False

    # Integer
    try:
        return int(raw)
    except ValueError:
        pass

    # Return as-is (e.g. unquoted identifiers)
    return raw


def _parse_toml_values(section_content: str) -> dict:
    """Parse key=value pairs from TOML section content.

    Handles:
    - Simple ``key = value`` lines
    - Multiline arrays (continuation until brackets are balanced)
    - Inline comments (``# ...``) stripped from values
    - Subsection headers (``[tool.ruff.lint]``) treated as nested key separators

    Returns a flat dict of {key: typed_value}.
    """
    result: dict = {}
    lines = section_content.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip blank lines and comments
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Skip subsection headers inside this section
        if stripped.startswith("["):
            i += 1
            continue

        if "=" in stripped:
            key, _, value_raw = stripped.partition("=")
            key = key.strip()
            value_raw = value_raw.strip()

            # Strip inline comment (outside of strings/arrays)
            if "#" in value_raw and not value_raw.startswith(("[", '"', "'")):
                value_raw = value_raw.partition("#")[0].strip()

            # Multiline array: accumulate lines until brackets are balanced
            if value_raw.startswith("[") and not _brackets_balanced(value_raw):
                while i + 1 < len(lines) and not _brackets_balanced(value_raw):
                    i += 1
                    value_raw += " " + lines[i].strip()

            result[key] = _parse_toml_value(value_raw)

        i += 1

    return result


# --- JSON parser ---


def _read_json_safe(path: str) -> dict:
    """Load a JSON file and return its contents as a dict, or {} on any error."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _navigate_json_path(data: dict, path: str) -> dict | None:
    """Resolve a dotted path into a nested dict.

    Args:
        data: The root JSON dict.
        path: Dotted key path, e.g. ``"compilerOptions"`` or ``"tool.jest"``.

    Returns:
        The nested dict at the path, or None if any key is missing or the
        value at the path is not a dict.
    """
    current: object = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current if isinstance(current, dict) else None


# --- INI parser ---


def _read_ini_section(path: str, section: str) -> dict:
    """Read a section from an INI-style config file via configparser.

    Args:
        path: Absolute path to the INI file.
        section: Section name (without brackets), e.g. ``"flake8"``.

    Returns:
        A flat dict of {key: value} strings for the section, or {} if the
        file cannot be read or the section does not exist.
    """
    parser = configparser.ConfigParser(strict=False)
    try:
        parser.read(path, encoding="utf-8")
    except (OSError, configparser.Error):
        return {}

    if not parser.has_section(section):
        return {}

    return dict(parser.items(section))


# --- YAML parser (simple key: value only — no PyYAML) ---


def _parse_yaml_value(raw: str) -> str | int | list | bool:
    """Convert a raw YAML scalar string to a Python type.

    Handles: booleans (true/false/yes/no), integers, and plain strings.
    List values (``[a, b]`` inline or block ``- item``) are not supported
    here — use the full YAML library for complex structures.
    """
    raw = raw.strip()

    if raw.lower() in ("true", "yes"):
        return True
    if raw.lower() in ("false", "no"):
        return False

    # Quoted string
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]

    try:
        return int(raw)
    except ValueError:
        pass

    return raw


def _read_yaml_simple(path: str) -> dict:
    """Parse a simple ``key: value`` YAML file using only the stdlib.

    Limitations:
    - Only top-level ``key: value`` pairs are extracted.
    - Block sequences (``- item``) and nested mappings are skipped.
    - Inline arrays (``[a, b]``) are returned as raw strings.

    Returns:
        A flat dict of {key: typed_value}, or {} on any error.
    """
    content = _read_file_safe(path)
    if not content:
        return {}

    result: dict = {}
    for line in content.splitlines():
        stripped = line.strip()
        # Skip blank lines, comments, and list items
        if not stripped or stripped.startswith(("#", "-")):
            continue
        # Skip lines that are indented (nested mappings)
        if line != stripped and line.startswith(" ") is not False:
            pass
        if ":" in stripped and not stripped.startswith(":"):
            key, _, value_raw = stripped.partition(":")
            key = key.strip()
            value_raw = value_raw.strip()
            if key and not key.startswith("-"):
                result[key] = _parse_yaml_value(value_raw) if value_raw else ""

    return result


# --- go.mod parser ---


def _read_gomod(path: str) -> dict:
    """Parse a go.mod file and extract the module path and Go version.

    Returns:
        A dict with keys ``"module"`` and ``"go"`` (both strings), or {}
        on any read error.
    """
    content = _read_file_safe(path)
    if not content:
        return {}

    result: dict = {}
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("module "):
            result["module"] = stripped[len("module "):].strip()
        elif stripped.startswith("go "):
            result["go"] = stripped[len("go "):].strip()

    return result


# --- Public API and helpers ---


def get_config_locations(module_name: str) -> list[dict]:
    """Return the ordered config file locations for a module.

    Args:
        module_name: The module identifier, e.g. ``"ruff"``.

    Returns:
        A list of location dicts (file, format, section, priority),
        sorted by priority ascending. Empty list if module is unknown.
    """
    locations = MODULE_CONFIG_MAP.get(module_name, [])
    return sorted(locations, key=lambda x: x.get("priority", 99))


def _set_nested(d: dict, dotted_key: str, value: object) -> None:
    """Set a value at a dotted path inside a nested dict, creating dicts as needed.

    Example::

        d = {}
        _set_nested(d, "style.line_length", 120)
        # d == {"style": {"line_length": 120}}
    """
    parts = dotted_key.split(".")
    current = d
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _map_extracted_values(raw_values: dict, key_mapping: dict) -> dict:
    """Map raw config key/value pairs to Atlas internal dotted paths.

    Args:
        raw_values: Flat dict of {raw_key: value} extracted from a config file.
        key_mapping: Dict of {raw_key: atlas_dotted_path} from MODULE_CONFIG_KEYS.

    Returns:
        Nested dict with Atlas internal structure, e.g.
        ``{"style": {"line_length": 120}}``.
    """
    result: dict = {}
    for raw_key, value in raw_values.items():
        atlas_path = key_mapping.get(raw_key)
        if atlas_path:
            _set_nested(result, atlas_path, value)
    return result


def scan_module_config(  # noqa: PLR0912
    module_name: str,
    project_dir: str,
    config_locations: list[dict] | None = None,
) -> dict:
    """Scan a project directory for a module's configuration file.

    Tries each config location in priority order. Returns on first match.

    Args:
        module_name: The module identifier, e.g. ``"ruff"``.
        project_dir: Absolute or relative path to the project root.
        config_locations: Override config locations (e.g. from module.json).
                          Falls back to MODULE_CONFIG_MAP if None.

    Returns:
        A result dict::

            {
                "found": True,
                "config_file": "pyproject.toml",
                "extracted": {"style": {"line_length": 120}},
            }

        or ``{"found": False}`` if no config file was found or the module
        is unknown.
    """
    locations = config_locations if config_locations is not None else get_config_locations(module_name)
    if not locations:
        return {"found": False}

    key_mapping = MODULE_CONFIG_KEYS.get(module_name, {})

    for loc in locations:
        file_pattern = loc.get("file", "")
        fmt = loc.get("format", "exists")
        section = loc.get("section")

        # Resolve glob patterns
        if "*" in file_pattern:
            try:
                entries = os.listdir(project_dir)
            except OSError:
                continue
            matches = [e for e in entries if fnmatch.fnmatch(e, file_pattern)]
            if not matches:
                continue
            file_path = os.path.join(project_dir, matches[0])
        else:
            file_path = os.path.join(project_dir, file_pattern)

        # Check existence based on format
        if fmt == "dir":
            if not os.path.isdir(file_path):
                continue
            return {"found": True, "config_file": file_pattern, "extracted": {}}

        if fmt in ("exists", "glob_exists"):
            if not os.path.isfile(file_path):
                continue
            return {"found": True, "config_file": file_pattern, "extracted": {}}

        if not os.path.isfile(file_path):
            continue

        # Parse the file and extract values
        raw_values: dict = {}

        if fmt == "toml":
            content = _read_file_safe(file_path)
            if section:
                section_text = _read_toml_section(content, section)
                raw_values = _parse_toml_values(section_text)
            else:
                raw_values = _parse_toml_values(content)

        elif fmt == "json":
            data = _read_json_safe(file_path)
            if section:
                nested = _navigate_json_path(data, section)
                raw_values = nested if nested is not None else {}
            else:
                raw_values = {k: v for k, v in data.items() if isinstance(v, (str, int, bool))}

        elif fmt == "ini":
            raw_values = _read_ini_section(file_path, section or "")

        elif fmt == "yaml":
            raw_values = _read_yaml_simple(file_path)

        elif fmt == "gomod":
            raw_values = _read_gomod(file_path)

        extracted = _map_extracted_values(raw_values, key_mapping) if raw_values else {}
        return {"found": True, "config_file": file_pattern, "extracted": extracted}

    return {"found": False}


def scan_all_modules(module_names: list[str], project_dir: str) -> dict[str, dict]:
    """Scan multiple modules and return results keyed by module name.

    Args:
        module_names: List of module identifiers to scan.
        project_dir: Absolute or relative path to the project root.

    Returns:
        Dict of {module_name: scan_result} where each scan_result is the
        output of :func:`scan_module_config`.
    """
    return {name: scan_module_config(name, project_dir) for name in module_names}


def enrich_module_rules(module_name: str, base_rules: dict, project_dir: str) -> dict:
    """Merge project-specific config values into a base rules dict.

    Scans the project for the module's config and deep-merges the extracted
    values into a copy of ``base_rules``.

    Args:
        module_name: The module identifier, e.g. ``"ruff"``.
        base_rules: The base rules dict (e.g. loaded from rules.md frontmatter).
        project_dir: Absolute or relative path to the project root.

    Returns:
        A new dict that is ``base_rules`` updated with any extracted values.
        The original ``base_rules`` is not modified.
    """
    result = dict(base_rules)
    scan = scan_module_config(module_name, project_dir)
    if scan.get("found") and scan.get("extracted"):
        for top_key, sub in scan["extracted"].items():
            if isinstance(sub, dict) and isinstance(result.get(top_key), dict):
                result[top_key] = {**result[top_key], **sub}
            else:
                result[top_key] = sub
    return result
