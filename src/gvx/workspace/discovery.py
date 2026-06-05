"""Workspace discovery and manifest parsing.

Discovers projects in a monorepo by scanning for pyproject.toml files
and parsing UV workspace configuration (tool.uv.workspace).
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from gvx.uv.config import UVProjectConfig, load_project_config


@dataclass
class WorkspaceProject:
    """A single project within a workspace."""

    name: str
    path: Path
    dependencies: list[str] = field(default_factory=list)
    python_version: str = ""
    has_runtime: bool = False
    runtime_fingerprint: str = ""
    is_workspace_root: bool = False
    uv_config: UVProjectConfig | None = None

    @property
    def runtime_dir(self) -> Path:
        """Get the runtime directory for this project.

        Returns:
            Path to .gvx/runtime directory.
        """
        return self.path / ".gvx" / "runtime"


@dataclass
class WorkspaceManifest:
    """Workspace-level manifest defining project relationships."""

    root: Path
    projects: list[WorkspaceProject] = field(default_factory=list)
    members: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    uv_config: UVProjectConfig | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "root": str(self.root),
            "members": self.members,
            "exclude": self.exclude,
            "projects": [
                {
                    "name": p.name,
                    "path": str(p.path),
                    "dependencies": p.dependencies,
                    "python_version": p.python_version,
                    "is_workspace_root": p.is_workspace_root,
                }
                for p in self.projects
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], root: Path) -> WorkspaceManifest:
        """Create from dictionary.

        Args:
            data: Dictionary representation.
            root: Workspace root path.

        Returns:
            WorkspaceManifest instance.
        """
        projects = [
            WorkspaceProject(
                name=p["name"],
                path=Path(p["path"]),
                dependencies=p.get("dependencies", []),
                python_version=p.get("python_version", ""),
                is_workspace_root=p.get("is_workspace_root", False),
            )
            for p in data.get("projects", [])
        ]
        return cls(
            root=root,
            projects=projects,
            members=data.get("members", []),
            exclude=data.get("exclude", []),
        )

    def save(self, path: Path) -> None:
        """Save manifest to file.

        Args:
            path: Path to save the manifest.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> WorkspaceManifest:
        """Load manifest from file.

        Args:
            path: Path to the manifest file.

        Returns:
            WorkspaceManifest instance.
        """
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        root = Path(data.get("root", str(path.parent)))
        return cls.from_dict(data, root)

    def get_project(self, name: str) -> WorkspaceProject | None:
        """Get a project by name.

        Args:
            name: Project name.

        Returns:
            WorkspaceProject or None.
        """
        for project in self.projects:
            if project.name == name:
                return project
        return None

    def get_shared_dependencies(self) -> dict[str, list[str]]:
        """Get dependencies shared across multiple projects.

        Returns:
            Dict mapping dependency name to list of project names using it.
        """
        dep_map: dict[str, list[str]] = {}
        for project in self.projects:
            for dep in project.dependencies:
                dep_map.setdefault(dep, []).append(project.name)
        return {dep: projects for dep, projects in dep_map.items() if len(projects) > 1}

    @property
    def workspace_members(self) -> list[WorkspaceProject]:
        """Get projects that are workspace members.

        Returns:
            List of workspace member projects.
        """
        if not self.uv_config or not self.uv_config.workspace:
            return self.projects
        return [p for p in self.projects if p.is_workspace_root or p.uv_config]


class WorkspaceDiscovery:
    """Discovers and manages workspace projects.

    Scans directory trees for pyproject.toml files and
    builds a workspace manifest using UV workspace configuration.
    """

    DEFAULT_EXCLUDE: ClassVar[list[str]] = [
        ".venv",
        "__pycache__",
        ".git",
        "node_modules",
        ".tox",
        ".gvx",
    ]

    def __init__(self, root: Path) -> None:
        """Initialize workspace discovery.

        Args:
            root: Workspace root directory.
        """
        self.root = root

    def discover(
        self,
        exclude: list[str] | None = None,
        max_depth: int = 5,
    ) -> WorkspaceManifest:
        """Discover all projects in the workspace.

        Args:
            exclude: Additional patterns to exclude.
            max_depth: Maximum directory depth to scan.

        Returns:
            WorkspaceManifest with all discovered projects.
        """
        if exclude is None:
            exclude = []

        root_pyproject = self.root / "pyproject.toml"
        root_config: UVProjectConfig | None = None
        workspace_members: list[str] = []
        workspace_exclude: list[str] = []

        if root_pyproject.exists():
            root_config = load_project_config(root_pyproject)
            if root_config.workspace:
                workspace_members = root_config.workspace.members
                workspace_exclude = root_config.workspace.exclude

        all_exclude = set(self.DEFAULT_EXCLUDE) | set(exclude) | set(workspace_exclude)

        projects = self._scan_directory(
            self.root,
            all_exclude,
            workspace_members,
            max_depth,
            current_depth=0,
        )

        return WorkspaceManifest(
            root=self.root,
            projects=projects,
            members=workspace_members,
            exclude=workspace_exclude,
            uv_config=root_config,
        )

    def _scan_directory(
        self,
        directory: Path,
        exclude: set[str],
        workspace_members: list[str],
        max_depth: int,
        current_depth: int,
    ) -> list[WorkspaceProject]:
        """Recursively scan a directory for projects.

        Args:
            directory: Directory to scan.
            exclude: Patterns to exclude.
            workspace_members: UV workspace member globs.
            max_depth: Maximum depth to scan.
            current_depth: Current recursion depth.

        Returns:
            List of discovered WorkspaceProject instances.
        """
        if current_depth > max_depth:
            return []

        projects: list[WorkspaceProject] = []
        pyproject = directory / "pyproject.toml"
        gvx_lock = directory / "gvx.lock"

        # Detect project if it has pyproject.toml or gvx.lock
        if pyproject.exists():
            project = self._parse_project(directory, pyproject, workspace_members)
            if project:
                projects.append(project)
        elif gvx_lock.exists():
            # Parse project from gvx.lock only
            project = self._parse_gvx_lock_project(directory, gvx_lock, workspace_members)
            if project:
                projects.append(project)

        try:
            for entry in sorted(directory.iterdir()):
                if entry.is_dir() and entry.name not in exclude:
                    if workspace_members and not self._matches_workspace_glob(entry, workspace_members):
                        continue
                    projects.extend(
                        self._scan_directory(
                            entry,
                            exclude,
                            workspace_members,
                            max_depth,
                            current_depth + 1,
                        )
                    )
        except PermissionError:
            pass

        return projects

    def _matches_workspace_glob(self, directory: Path, workspace_members: list[str]) -> bool:
        """Check if a directory matches workspace member globs.

        Args:
            directory: Directory to check.
            workspace_members: List of workspace member globs.

        Returns:
            True if directory matches any glob.
        """
        rel_path = str(directory.relative_to(self.root))
        for pattern in workspace_members:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            if fnmatch.fnmatch(directory.name, pattern):
                return True
        return False

    def _parse_project(
        self,
        directory: Path,
        pyproject_path: Path,
        workspace_members: list[str],
    ) -> WorkspaceProject | None:
        """Parse a project's pyproject.toml.

        Args:
            directory: Project directory.
            pyproject_path: Path to pyproject.toml.
            workspace_members: UV workspace member globs.

        Returns:
            WorkspaceProject or None if parsing fails.
        """
        try:
            uv_config = load_project_config(pyproject_path)
        except Exception:
            return None

        name = directory.name
        dependencies: list[str] = []
        python_version = ""

        try:
            content = pyproject_path.read_text(encoding="utf-8")
        except OSError:
            return None

        for line in content.splitlines():
            line = line.strip()
            if ("dependencies" in line or "requires" in line) and "=" in line:
                deps_str = line.split("=", 1)[1].strip()
                if deps_str.startswith("["):
                    deps_str = deps_str.strip("[]")
                    for dep in deps_str.split(","):
                        dep = dep.strip().strip('"').strip("'")
                        if dep:
                            dependencies.append(dep)
            if line.startswith("requires-python") and "=" in line:
                python_version = line.split("=", 1)[1].strip().strip('"').strip("'")

        has_runtime = (directory / ".gvx" / "runtime" / "manifest.json").exists()
        runtime_fp = ""
        if has_runtime:
            fp_path = directory / ".gvx" / "runtime" / "fingerprint"
            if fp_path.exists():
                runtime_fp = fp_path.read_text(encoding="utf-8").strip()

        is_workspace_root = uv_config.has_workspace
        if not is_workspace_root and workspace_members:
            is_workspace_root = self._matches_workspace_glob(directory, workspace_members)

        return WorkspaceProject(
            name=name,
            path=directory,
            dependencies=dependencies,
            python_version=python_version,
            has_runtime=has_runtime,
            runtime_fingerprint=runtime_fp,
            is_workspace_root=is_workspace_root,
            uv_config=uv_config,
        )

    def _parse_gvx_lock_project(
        self,
        directory: Path,
        gvx_lock_path: Path,
        workspace_members: list[str],
    ) -> WorkspaceProject | None:
        """Parse a project's gvx.lock file.

        Args:
            directory: Project directory.
            gvx_lock_path: Path to gvx.lock.
            workspace_members: UV workspace member globs.

        Returns:
            WorkspaceProject or None if parsing fails.
        """
        try:
            with open(gvx_lock_path, encoding="utf-8") as f:
                lockfile = json.load(f)
        except Exception:
            return None

        name = directory.name
        dependencies: list[str] = []
        python_version = lockfile.get("python_version", "")

        # Extract dependencies from lockfile
        for pkg in lockfile.get("packages", []):
            dep_name = pkg.get("name", "")
            if dep_name:
                dependencies.append(dep_name)

        has_runtime = (directory / ".gvx" / "runtime" / "manifest.json").exists()
        runtime_fp = ""
        if has_runtime:
            fp_path = directory / ".gvx" / "runtime" / "fingerprint"
            if fp_path.exists():
                runtime_fp = fp_path.read_text(encoding="utf-8").strip()

        is_workspace_root = False
        if workspace_members:
            is_workspace_root = self._matches_workspace_glob(directory, workspace_members)

        return WorkspaceProject(
            name=name,
            path=directory,
            dependencies=dependencies,
            python_version=python_version,
            has_runtime=has_runtime,
            runtime_fingerprint=runtime_fp,
            is_workspace_root=is_workspace_root,
            uv_config=None,
        )

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """Get the dependency graph for the workspace.

        Returns:
            Dict mapping project name to list of dependencies.
        """
        manifest = self.discover()
        graph: dict[str, list[str]] = {}
        for project in manifest.projects:
            graph[project.name] = project.dependencies
        return graph

    def get_shared_dependencies(self) -> dict[str, list[str]]:
        """Get dependencies shared across projects.

        Returns:
            Dict mapping dependency to list of projects using it.
        """
        manifest = self.discover()
        return manifest.get_shared_dependencies()
