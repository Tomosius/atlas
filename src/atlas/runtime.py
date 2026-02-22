"""Atlas runtime — the stateful core used by both the MCP server and CLI.

One instance per server session (or per CLI invocation).  Lazy-loaded
properties mean nothing is read from disk until actually needed.
"""

from __future__ import annotations

import json
import os
import time

from atlas.core.categories import CategoryRouter
from atlas.core.config import AtlasConfig, load_config
from atlas.core.errors import error_result, ok_result
from atlas.core.modules import install_module, remove_module, update_modules
from atlas.core.registry import load_registry
from atlas.core.retrieve import (
    build_retrieve_file,
    filter_sections,
)
from atlas.core.runner import run_task


def _relative_time(ts: float, now: float) -> str:
    """Return a human-readable relative time string (e.g. '2h ago')."""
    delta = int(now - ts)
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{delta // 60}m ago"
    if delta < 86400:
        return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"


class Atlas:
    """Runtime state for Atlas.

    Created once per server session (MCP) or once per CLI invocation.
    Holds lazy-loaded references to manifest, registry, config, and router.
    All heavy I/O is deferred until the first access.
    """

    def __init__(self, project_dir: str | None = None) -> None:
        self.project_dir: str = os.path.abspath(project_dir or os.getcwd())
        self.atlas_dir: str = os.path.join(self.project_dir, ".atlas")
        self.warehouse_dir: str = self._find_warehouse()

        # Lazy backing fields
        self._manifest: dict | None = None
        self._config: AtlasConfig | None = None
        self._registry: dict | None = None
        self._router: CategoryRouter | None = None
        self._notes: dict | None = None
        self._context: dict | None = None

    # ------------------------------------------------------------------
    # Core lazy properties
    # ------------------------------------------------------------------

    @property
    def is_initialized(self) -> bool:
        """True when the .atlas/ directory exists."""
        return os.path.isdir(self.atlas_dir)

    @property
    def manifest(self) -> dict:
        if self._manifest is None:
            self._manifest = self._load_json(
                os.path.join(self.atlas_dir, "manifest.json"), {}
            )
        return self._manifest

    @property
    def config(self) -> AtlasConfig:
        if self._config is None:
            self._config = load_config(self.project_dir)
        return self._config

    @property
    def registry(self) -> dict:
        if self._registry is None:
            self._registry = load_registry(
                os.path.join(self.warehouse_dir, "registry.json")
            )
        return self._registry

    @property
    def installed_modules(self) -> list[str]:
        return list(self.manifest.get("installed_modules", {}).keys())

    @property
    def router(self) -> CategoryRouter:
        if self._router is None:
            self._router = CategoryRouter(self.manifest, self.registry)
        return self._router

    @property
    def notes(self) -> dict:
        if self._notes is None:
            self._notes = self._load_json(
                os.path.join(self.atlas_dir, "notes.json"), {}
            )
        return self._notes

    @property
    def context(self) -> dict:
        if self._context is None:
            self._context = self._load_json(
                os.path.join(self.atlas_dir, "context.json"), {}
            )
        return self._context

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def invalidate(self) -> None:
        """Clear all cached state.

        Call after any operation that modifies .atlas/ so the next access
        reloads fresh data from disk.
        """
        self._manifest = None
        self._config = None
        self._registry = None
        self._router = None
        self._notes = None
        self._context = None

    def save_manifest(self) -> None:
        """Persist the in-memory manifest to .atlas/manifest.json."""
        if self._manifest is not None:
            self._write_json(
                os.path.join(self.atlas_dir, "manifest.json"), self._manifest
            )

    def save_notes(self) -> None:
        """Persist the in-memory notes to .atlas/notes.json."""
        if self._notes is not None:
            self._write_json(
                os.path.join(self.atlas_dir, "notes.json"), self._notes
            )

    def save_config(self, data: dict) -> None:
        """Persist *data* to .atlas/config.json."""
        self._write_json(os.path.join(self.atlas_dir, "config.json"), data)

    # ------------------------------------------------------------------
    # Verb: query (no-verb context retrieval)
    # ------------------------------------------------------------------

    def query(
        self,
        contexts: list[list[str]],
        message: str | None = None,
    ) -> str:
        """Retrieve pre-built markdown for one or more context groups.

        Each group is ``[module_name, *filter_words]``.  Results are
        concatenated with a blank line separator.
        """
        parts: list[str] = []
        retrieve_dir = os.path.join(self.atlas_dir, "retrieve")
        installed = self.manifest.get("installed_modules", {})

        for group in contexts:
            if not group:
                continue
            module_name = group[0]
            filters = group[1:]

            # Read the pre-built file
            md_path = os.path.join(retrieve_dir, f"{module_name}.md")
            if os.path.isfile(md_path):
                try:
                    with open(md_path) as f:
                        content = f.read()
                except OSError:
                    content = ""
            else:
                # Fall back to building on-the-fly if not pre-built
                content = build_retrieve_file(
                    module_name,
                    self.atlas_dir,
                    self.registry,
                    self.warehouse_dir,
                    installed,
                )

            if filters:
                content = filter_sections(content, filters)

            # Append module notes
            module_notes = self.notes.get(module_name, [])
            if module_notes:
                note_lines = "\n".join(
                    f"  • {n['text']}" for n in module_notes
                )
                content += f"\n\n⚠️ Project Notes:\n{note_lines}"

            if content:
                parts.append(content)

        result = "\n\n".join(parts)
        if message:
            result = f"{result}\n\n---\n{message}" if result else message
        return result

    # ------------------------------------------------------------------
    # Verb: add
    # ------------------------------------------------------------------

    def add_modules(self, names: list[str]) -> dict:
        """Install one or more modules from the warehouse."""
        if not self.is_initialized:
            return error_result("NOT_INITIALIZED", "run atlas init first")

        installed: list[str] = []
        failed: list[dict] = []
        pkg_mgr = self.manifest.get("detected", {}).get("package_manager", "")

        for name in names:
            result = install_module(
                name,
                self.registry,
                self.warehouse_dir,
                self.atlas_dir,
                self.manifest,
                package_manager=pkg_mgr,
            )
            if result["ok"]:
                installed.append(name)
            else:
                failed.append({"name": name, "error": result.get("error", "")})

        if installed:
            self.save_manifest()
            retrieve_dir = os.path.join(self.atlas_dir, "retrieve")
            os.makedirs(retrieve_dir, exist_ok=True)
            for name in installed:
                content = build_retrieve_file(
                    name,
                    self.atlas_dir,
                    self.registry,
                    self.warehouse_dir,
                    self.manifest.get("installed_modules", {}),
                )
                if content:
                    with open(os.path.join(retrieve_dir, f"{name}.md"), "w") as f:
                        f.write(content)
            self.invalidate()

        return ok_result(installed=installed, failed=failed)

    # ------------------------------------------------------------------
    # Verb: remove (module)
    # ------------------------------------------------------------------

    def remove_module(self, name: str) -> dict:
        """Uninstall a module from the project."""
        if not self.is_initialized:
            return error_result("NOT_INITIALIZED", "run atlas init first")

        result = remove_module(name, self.registry, self.atlas_dir, self.manifest)
        if result["ok"]:
            self.save_manifest()
            self.invalidate()
        return result

    # ------------------------------------------------------------------
    # Verb: just (task execution)
    # ------------------------------------------------------------------

    def just(self, task_name: str, extra_args: list[str] | None = None) -> dict:
        """Execute a named task from installed module commands."""
        if not self.is_initialized:
            return error_result("NOT_INITIALIZED", "run atlas init first")

        if not task_name:
            return error_result("INVALID_ARGUMENT", "task name required")

        installed_mods = self.manifest.get("installed_modules", {})
        command: str | None = None

        for mod_name in installed_mods:
            mod_json = self._load_json(
                os.path.join(self.atlas_dir, "modules", f"{mod_name}.json"), {}
            )
            cmds = mod_json.get("commands", {})
            if task_name in cmds:
                command = cmds[task_name]
                break

        if command is None:
            return error_result(
                "INVALID_ARGUMENT",
                f"Task '{task_name}' not found in any installed module",
            )

        return run_task(task_name, command, self.project_dir)

    # ------------------------------------------------------------------
    # Notes management
    # ------------------------------------------------------------------

    def add_note(self, module_name: str, text: str) -> dict:
        """Append a note to *module_name*."""
        if not self.is_initialized:
            return error_result("NOT_INITIALIZED", "run atlas init first")

        notes_list = self.notes.setdefault(module_name, [])
        notes_list.append({"text": text})
        self.save_notes()
        return ok_result(module=module_name, note=text, index=len(notes_list) - 1)

    def remove_note(self, module_name: str, index: int | str) -> dict:
        """Remove a note by index (or all notes) from *module_name*."""
        if not self.is_initialized:
            return error_result("NOT_INITIALIZED", "run atlas init first")

        notes_list = self.notes.get(module_name, [])
        if not notes_list:
            return error_result("INVALID_ARGUMENT", f"No notes for module '{module_name}'")

        if index == "all":
            self.notes[module_name] = []
        else:
            try:
                idx = int(index)
                notes_list.pop(idx)
            except (ValueError, IndexError):
                return error_result(
                    "INVALID_ARGUMENT",
                    f"Invalid note index '{index}' for module '{module_name}'",
                )

        self.save_notes()
        return ok_result(module=module_name, removed=index)

    # ------------------------------------------------------------------
    # Session brief (for MCP auto-brief)
    # ------------------------------------------------------------------

    def build_session_brief(self) -> str:
        """Build the auto-brief text for MCP prompt injection."""
        parts: list[str] = []

        detected = self.manifest.get("detected", {})
        parts.append(f"# Atlas — {detected.get('project_name', 'project')}")
        parts.append(f"Installed: {', '.join(self.installed_modules)}")

        if self.context.get("active"):
            task = self.context["active"]
            parts.append(
                f"\n## Active Task\n→ {task['type']} #{task['id']}: {task['title']}"
            )

        # Recent activity (from history.jsonl — last 3-5 entries)
        history = self._read_recent_history(limit=5)
        if history:
            parts.append("\n## Recent Activity")
            for entry in history:
                parts.append(f"  {entry.get('ago', '?')}: {entry.get('summary', '')}")

        # Git status (quick subprocess if git installed)
        if self.router.has_category_installed("vcs"):
            git_status = self._quick_git_status()
            if git_status:
                parts.append(f"\n## Git Status\n{git_status}")

        all_notes: list[str] = []
        for mod, note_list in self.notes.items():
            for note in note_list:
                all_notes.append(f"  ⚠️ {mod}: {note['text']}")
        if all_notes:
            parts.append("\n## Notes\n" + "\n".join(all_notes))

        parts.append("\n## Atlas Tool")
        parts.append("  One tool: atlas. Spaces filter, commas combine, -- separates.")
        parts.append(f"  Retrieve: {', '.join(self.installed_modules[:5])}")
        parts.append("  Help: atlas list")

        return "\n".join(parts)

    def _read_recent_history(self, limit: int = 5) -> list[dict]:
        """Return the last *limit* entries from history.jsonl with relative timestamps."""
        path = os.path.join(self.atlas_dir, "history.jsonl")
        if not os.path.isfile(path):
            return []
        try:
            with open(path) as f:
                lines = [ln.strip() for ln in f if ln.strip()]
        except OSError:
            return []
        now = time.time()
        entries = []
        for line in lines[-limit:]:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            summary = record.get("summary", "")
            if not summary:
                continue
            ts = record.get("ts")
            ago = _relative_time(ts, now) if ts is not None else "?"
            entries.append({"ago": ago, "summary": summary})
        return entries

    def _quick_git_status(self) -> str:
        """Return a quick git status string. Implemented in #97."""
        return ""

    # ------------------------------------------------------------------
    # Warehouse path resolution
    # ------------------------------------------------------------------

    def _find_warehouse(self) -> str:
        """Locate the modules/ warehouse directory.

        Resolution cascade:
        1. Package-relative: ``<atlas package>/_modules/``
        2. Development repo: sibling ``modules/`` next to ``src/``
        3. Environment variable: ``ATLAS_WAREHOUSE_DIR``
        4. Fallback: ``~/.atlas/modules``
        """
        # 1. Package-relative (_modules/ ships with the wheel)
        package_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(package_dir, "_modules")
        if os.path.isdir(candidate):
            return candidate

        # 2. Development layout: repo_root/modules/ (sibling of src/)
        src_dir = os.path.dirname(package_dir)
        repo_root = os.path.dirname(src_dir)
        candidate = os.path.join(repo_root, "modules")
        if os.path.isdir(candidate):
            return candidate

        # 3. Environment variable override
        env = os.environ.get("ATLAS_WAREHOUSE_DIR", "")
        if env and os.path.isdir(env):
            return env

        # 4. Fallback
        return os.path.expanduser("~/.atlas/modules")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_json(path: str, default: dict) -> dict:
        if not os.path.isfile(path):
            return dict(default)
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return dict(default)

    def _write_json(self, path: str, data: dict) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
