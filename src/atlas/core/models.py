"""All Atlas data models as pure-Python dataclasses."""

from dataclasses import dataclass, field


@dataclass
class SystemTools:
    """Detected CLI tool versions on the host system."""

    python3: str = "not found"
    node: str = "not found"
    uv: str = "not found"
    git: str = "not found"
    docker: str = "not found"
    gh: str = "not found"
    cargo: str = "not found"
    go: str = "not found"


@dataclass
class Infrastructure:
    """Presence flags for common infrastructure files."""

    git: bool = False
    gitignore: bool = False
    dockerfile: bool = False
    docker_compose: bool = False
    github_actions: bool = False
    github_dir: bool = False
    gitlab_ci: bool = False


@dataclass
class ProjectDetection:
    """Full project detection result."""

    languages: list[str] = field(default_factory=list)
    primary_language: str = ""
    package_manager: str = "none"
    existing_tools: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    stack: str = ""
    databases: list[str] = field(default_factory=list)
    infrastructure: Infrastructure = field(default_factory=Infrastructure)
    structure_type: str = "single"
    workspace_manager: str = "none"
    system_tools: SystemTools = field(default_factory=SystemTools)
