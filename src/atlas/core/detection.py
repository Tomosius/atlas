"""Language, framework, and database detection engine."""

import os

from atlas.core.models import Infrastructure, ProjectDetection, SystemTools


# --- Data tables ---

_LANGUAGE_MARKERS: dict[str, list[str]] = {
    "python": [
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "Pipfile",
        "*.py",
    ],
    "typescript": ["tsconfig.json", "*.ts", "*.tsx"],
    "javascript": ["package.json", "*.js", "*.jsx", "*.mjs"],
    "rust": ["Cargo.toml"],
    "go": ["go.mod"],
    "ruby": ["Gemfile", "*.rb"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "kotlin": ["build.gradle.kts", "*.kt"],
    "swift": ["Package.swift", "*.swift"],
    "csharp": ["*.csproj", "*.sln", "*.cs"],
    "php": ["composer.json", "*.php"],
    "elixir": ["mix.exs"],
    "haskell": ["stack.yaml", "*.cabal"],
    "lua": ["*.lua"],
}

_LOCK_FILE_MANAGERS: dict[str, str] = {
    "uv.lock": "uv",
    "poetry.lock": "poetry",
    "Pipfile.lock": "pipenv",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "package-lock.json": "npm",
    "bun.lockb": "bun",
    "Cargo.lock": "cargo",
    "Gemfile.lock": "bundler",
    "go.sum": "go",
    "composer.lock": "composer",
    "mix.lock": "mix",
}

_WORKSPACE_MANAGERS: dict[str, str] = {
    "pnpm-workspace.yaml": "pnpm",
    "lerna.json": "lerna",
    "nx.json": "nx",
    "turbo.json": "turborepo",
    "rush.json": "rush",
}

_FULLSTACK_DIRS: list[str] = [
    "frontend",
    "backend",
    "client",
    "server",
    "web",
    "api",
    "apps",
    "packages",
]

_FRAMEWORK_PATTERNS: dict[str, tuple[str, str]] = {
    # python backends
    "fastapi": ("python", "python-backend"),
    "flask": ("python", "python-backend"),
    "django": ("python", "python-backend"),
    "starlette": ("python", "python-backend"),
    "litestar": ("python", "python-backend"),
    # python data / ml
    "numpy": ("python", "python-data"),
    "pandas": ("python", "python-data"),
    "torch": ("python", "python-ml"),
    "tensorflow": ("python", "python-ml"),
    "scikit-learn": ("python", "python-ml"),
    # js/ts frontends
    "react": ("typescript", "ts-frontend"),
    "vue": ("typescript", "ts-frontend"),
    "svelte": ("typescript", "ts-frontend"),
    "angular": ("typescript", "ts-frontend"),
    "solid": ("typescript", "ts-frontend"),
    # js/ts backends
    "express": ("javascript", "js-backend"),
    "fastify": ("javascript", "js-backend"),
    "hono": ("javascript", "js-backend"),
    "nestjs": ("typescript", "ts-backend"),
    # mobile
    "react-native": ("typescript", "ts-mobile"),
}

_DATABASE_PATTERNS: list[str] = [
    "sqlalchemy",
    "alembic",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "pymongo",
    "motor",
    "redis",
    "aioredis",
    "prisma",
    "typeorm",
    "sequelize",
    "mongoose",
    "pg",
    "mysql2",
    "sqlite3",
]

_TOOL_MARKERS: dict[str, list[str]] = {
    "ruff": ["[tool.ruff]"],
    "pytest": ["[tool.pytest.ini_options]", "pytest.ini", "conftest.py"],
    "mypy": ["[tool.mypy]", "mypy.ini", ".mypy.ini"],
    "black": ["[tool.black]"],
    "isort": ["[tool.isort]"],
    "eslint": [
        "eslint.config.js",
        "eslint.config.mjs",
        ".eslintrc.json",
        ".eslintrc.js",
    ],
    "prettier": [".prettierrc", ".prettierrc.json", "prettier.config.js"],
    "vitest": ["vitest.config.ts", "vitest.config.js"],
    "jest": ["jest.config.js", "jest.config.ts"],
    "docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
}


# --- Internal helpers ---


def _read_file_safe(path: str) -> str:
    """Read a file and return its contents, or empty string on any error."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def _detect_languages(project_dir: str) -> tuple[list[str], str]:
    """Detect languages present in the project. Returns (languages, primary)."""
    entries = set(os.listdir(project_dir))
    languages: list[str] = []

    for lang, markers in _LANGUAGE_MARKERS.items():
        for marker in markers:
            if marker.startswith("*"):
                ext = marker[1:]
                if any(f.endswith(ext) for f in entries):
                    languages.append(lang)
                    break
            elif marker in entries:
                languages.append(lang)
                break

    # Determine primary language
    # TypeScript takes priority over JavaScript when both present
    if "typescript" in languages and "javascript" in languages:
        languages.remove("javascript")

    primary = ""
    priority = [
        "python",
        "typescript",
        "javascript",
        "rust",
        "go",
        "ruby",
        "java",
        "kotlin",
    ]
    for lang in priority:
        if lang in languages:
            primary = lang
            break
    if not primary and languages:
        primary = languages[0]

    return languages, primary


def _detect_package_manager(project_dir: str, languages: list[str]) -> str:
    """Detect package manager from lock files."""
    entries = set(os.listdir(project_dir))
    for lock_file, manager in _LOCK_FILE_MANAGERS.items():
        if lock_file in entries:
            return manager
    return "none"


def _detect_existing_tools(project_dir: str) -> list[str]:
    """Detect tools already configured in the project."""
    entries = set(os.listdir(project_dir))
    found: list[str] = []

    pyproject_content = ""
    if "pyproject.toml" in entries:
        pyproject_content = _read_file_safe(os.path.join(project_dir, "pyproject.toml"))

    package_content = ""
    if "package.json" in entries:
        package_content = _read_file_safe(os.path.join(project_dir, "package.json"))

    for tool, markers in _TOOL_MARKERS.items():
        for marker in markers:
            if marker.startswith("["):
                # TOML section marker
                if marker in pyproject_content:
                    found.append(tool)
                    break
            elif marker in entries:
                found.append(tool)
                break
            elif marker in package_content:
                found.append(tool)
                break

    return found


def _detect_frameworks_and_stack(
    project_dir: str, languages: list[str]
) -> tuple[list[str], str]:
    """Detect frameworks and infer the project stack."""
    entries = set(os.listdir(project_dir))
    frameworks: list[str] = []
    stack = ""

    # Read dependency files
    content = ""
    for fname in ("pyproject.toml", "requirements.txt", "package.json"):
        if fname in entries:
            content += _read_file_safe(os.path.join(project_dir, fname))

    for framework, (lang, candidate_stack) in _FRAMEWORK_PATTERNS.items():
        if lang in languages and framework in content:
            frameworks.append(framework)
            if not stack:
                stack = candidate_stack

    # Fallback stack inference
    if not stack:
        if "python" in languages:
            stack = "python-library"
        elif "typescript" in languages:
            stack = "ts-library"
        elif "javascript" in languages:
            stack = "js-library"
        elif "rust" in languages:
            stack = "rust-library"
        elif "go" in languages:
            stack = "go-service"

    return frameworks, stack


def _detect_databases(project_dir: str, languages: list[str]) -> list[str]:
    """Detect databases from dependency files."""
    entries = set(os.listdir(project_dir))
    content = ""
    for fname in ("pyproject.toml", "requirements.txt", "package.json"):
        if fname in entries:
            content += _read_file_safe(os.path.join(project_dir, fname))

    return [db for db in _DATABASE_PATTERNS if db in content]


def _detect_infrastructure(project_dir: str) -> Infrastructure:
    """Detect presence of infrastructure files."""
    entries = set(os.listdir(project_dir))
    github_dir = os.path.join(project_dir, ".github")
    workflows_dir = os.path.join(github_dir, "workflows")

    return Infrastructure(
        git=".git" in entries,
        gitignore=".gitignore" in entries,
        dockerfile="Dockerfile" in entries,
        docker_compose="docker-compose.yml" in entries
        or "docker-compose.yaml" in entries,
        github_actions=os.path.isdir(workflows_dir),
        github_dir=os.path.isdir(github_dir),
        gitlab_ci=".gitlab-ci.yml" in entries,
    )


def _detect_structure(project_dir: str) -> tuple[str, str]:
    """Detect project structure type and workspace manager.

    Returns (structure_type, workspace_manager).
    structure_type: 'single' | 'monorepo' | 'fullstack'
    """
    entries = set(os.listdir(project_dir))

    # Check for workspace managers
    for marker, manager in _WORKSPACE_MANAGERS.items():
        if marker in entries:
            return "monorepo", manager

    # Check for fullstack layout (both frontend+backend dirs present)
    found_dirs = [
        d for d in _FULLSTACK_DIRS if os.path.isdir(os.path.join(project_dir, d))
    ]
    if len(found_dirs) >= 2:
        return "fullstack", "none"

    return "single", "none"


# --- Public API ---


def detect_project(project_dir: str) -> ProjectDetection:
    """Run full project detection and return a ProjectDetection result.

    Args:
        project_dir: Absolute or relative path to the project root.

    Returns:
        Populated ProjectDetection dataclass.
    """
    project_dir = os.path.abspath(project_dir)

    if not os.path.isdir(project_dir):
        return ProjectDetection()

    languages, primary = _detect_languages(project_dir)
    package_manager = _detect_package_manager(project_dir, languages)
    existing_tools = _detect_existing_tools(project_dir)
    frameworks, stack = _detect_frameworks_and_stack(project_dir, languages)
    databases = _detect_databases(project_dir, languages)
    infrastructure = _detect_infrastructure(project_dir)
    structure_type, workspace_manager = _detect_structure(project_dir)

    from atlas.core.system import detect_system_tools

    return ProjectDetection(
        languages=languages,
        primary_language=primary,
        package_manager=package_manager,
        existing_tools=existing_tools,
        frameworks=frameworks,
        stack=stack,
        databases=databases,
        infrastructure=infrastructure,
        structure_type=structure_type,
        workspace_manager=workspace_manager,
        system_tools=detect_system_tools(),
    )
