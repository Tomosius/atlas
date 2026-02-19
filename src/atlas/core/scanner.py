"""Config scanner: reads tool configuration from project files."""

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
