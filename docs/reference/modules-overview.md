# Module Catalogue

All 61 modules shipped with Atlas, organised by category.

## Languages

| Module | Detects | Conflicts |
|---|---|---|
| `python` | `pyproject.toml`, `setup.py`, `requirements.txt` | — |
| `typescript` | `tsconfig.json` | — |
| `rust` | `Cargo.toml` | — |
| `go` | `go.mod` | — |
| `java` | `pom.xml`, `build.gradle` | — |
| `ruby` | `Gemfile` | — |
| `cpp` | `CMakeLists.txt`, `*.cpp` | — |
| `csharp` | `*.csproj`, `*.sln` | — |
| `html` | `*.html` | — |
| `css` | `*.css` | — |

## Linters

| Module | Detects | Conflicts |
|---|---|---|
| `ruff` | `pyproject.toml [tool.ruff]`, `.ruff.toml` | `flake8`, `pylint` |
| `eslint` | `.eslintrc*`, `eslint.config.*` | `biome` |
| `biome` | `biome.json` | `eslint`, `prettier` |
| `clippy` | `Cargo.toml` | — |
| `flake8` | `.flake8`, `setup.cfg [flake8]` | `ruff` |
| `golangci-lint` | `.golangci.yml` | — |

## Formatters

| Module | Detects | Conflicts |
|---|---|---|
| `prettier` | `.prettierrc*`, `prettier.config.*` | `biome` |
| `rustfmt` | `rustfmt.toml` | — |
| `gofmt` | `go.mod` | — |

## Testing

| Module | Detects | Conflicts |
|---|---|---|
| `pytest` | `pyproject.toml [tool.pytest*]`, `pytest.ini` | — |
| `vitest` | `vitest.config.*` | `jest` |
| `jest` | `jest.config.*` | `vitest` |
| `playwright` | `playwright.config.*` | — |
| `cargo-test` | `Cargo.toml` | — |
| `go-test` | `go.mod` | — |

## Frameworks

| Module | Detects | Combines well with |
|---|---|---|
| `django` | `manage.py`, `django.core` in deps | `python`, `postgresql` |
| `fastapi` | `fastapi` in deps | `python`, `postgresql` |
| `flask` | `flask` in deps | `python` |
| `react` | `react` in `package.json` | `typescript` |
| `next-js` | `next.config.*` | `typescript`, `react` |
| `svelte` | `svelte.config.*` | `typescript` |
| `vue` | `vue.config.*` | `typescript` |
| `express` | `express` in `package.json` | `typescript` |
| `angular` | `angular.json` | `typescript` |
| `nestjs` | `nest-cli.json` | `typescript` |

## Databases

| Module | Detects |
|---|---|
| `postgresql` | `psycopg*` or `asyncpg` in deps |
| `sqlite` | `sqlite3` usage |
| `redis` | `redis` in deps |
| `mongodb` | `pymongo` or `motor` in deps |

## VCS

| Module | Detects |
|---|---|
| `git` | `.git/` directory |
| `svn` | `.svn/` directory |
| `mercurial` | `.hg/` directory |

## Platforms

| Module | Detects |
|---|---|
| `github` | `.github/` directory |
| `gitlab` | `.gitlab-ci.yml` |
| `bitbucket` | `bitbucket-pipelines.yml` |

## Package Managers

| Module | Detects |
|---|---|
| `uv` | `uv.lock` |
| `pnpm` | `pnpm-lock.yaml` |
| `npm` | `package-lock.json` |
| `yarn` | `yarn.lock` |
| `bun` | `bun.lockb` |
| `cargo` | `Cargo.lock` |
| `poetry` | `poetry.lock` |
| `pip` | `requirements.txt` |

## Environments

| Module | Detects |
|---|---|
| `docker` | `Dockerfile` |
| `docker-compose` | `docker-compose.yml` |
| `venv` | `.venv/` |
| `node` | `.nvmrc`, `.node-version` |

## CI/CD

| Module | Detects |
|---|---|
| `github-actions` | `.github/workflows/*.yml` |
| `gitlab-ci` | `.gitlab-ci.yml` |
| `circleci` | `.circleci/config.yml` |

## Stacks

Pre-bundled combinations for common project types:

| Stack | Includes |
|---|---|
| `python-backend` | python + uv + ruff + pytest + git |
| `python-cli` | python + uv + ruff + pytest + git |
| `python-library` | python + uv + ruff + pytest + git |
| `ts-frontend` | typescript + pnpm + eslint + vitest |
| `ts-backend` | typescript + pnpm + eslint + jest |
| `fullstack` | python + typescript + uv + pnpm |

## Tools

| Module | Purpose |
|---|---|
| `commit-rules` | Semantic commit message conventions |

## Prompts

| Module | Purpose |
|---|---|
| `design` | Senior engineer design review prompt |
| `review` | Code review prompt with language + linter fragments |
| `debug` | Debugging prompt with language + testing context |
| `king-mode` | High-discipline senior engineer mode |
