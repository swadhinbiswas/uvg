"""Workspace discovery and manifest parsing.

Discovers projects in a monorepo by scanning for pyproject.toml files
and parsing workspace configuration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


@dataclass
class WorkspaceProject:
    """A single project within a workspace."""

    name: str
    path: Path
    dependencies: list[str] = field(default_factory=list)
    python_version: str = ""
    has_runtime: bool = False
    runtime_fingerprint: str = ""

    @property
    def runtime_dir(self) -> Path:
        """Get the runtime directory for this project.

        Returns:
            Path to .uvg/runtime directory.
        """
        return self.path / ".uvg" / "runtime"


@dataclass
class WorkspaceManifest:
    """Workspace-level manifest defining project relationships."""

    root: Path
    projects: list[WorkspaceProject] = field(default_factory=list)
    members: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)

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


class WorkspaceDiscovery:
    """Discovers and manages workspace projects.

    Scans directory trees for pyproject.toml files and
    builds a workspace manifest.
    """

    DEFAULT_EXCLUDE: ClassVar[list[str]] = [
        ".venv",
        "__pycache__",
        ".git",
        "node_modules",
        ".tox",
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

        all_exclude = set(self.DEFAULT_EXCLUDE) | set(exclude)
        projects = self._scan_directory(self.root, all_exclude, max_depth, current_depth=0)

        return WorkspaceManifest(
            root=self.root,
            projects=projects,
        )

    def _scan_directory(
        self,
        directory: Path,
        exclude: set[str],
        max_depth: int,
        current_depth: int,
    ) -> list[WorkspaceProject]:
        """Recursively scan a directory for projects.

        Args:
            directory: Directory to scan.
            exclude: Patterns to exclude.
            max_depth: Maximum depth to scan.
            current_depth: Current recursion depth.

        Returns:
            List of discovered WorkspaceProject instances.
        """
        if current_depth > max_depth:
            return []

        projects: list[WorkspaceProject] = []
        pyproject = directory / "pyproject.toml"

        if pyproject.exists() and directory != self.root:
            project = self._parse_project(directory, pyproject)
            if project:
                projects.append(project)

        try:
            for entry in sorted(directory.iterdir()):
                if entry.is_dir() and entry.name not in exclude:
                    projects.extend(
                        self._scan_directory(
                            entry,
                            exclude,
                            max_depth,
                            current_depth + 1,
                        )
                    )
        except PermissionError:
            pass

        return projects

    def _parse_project(
        self,
        directory: Path,
        pyproject_path: Path,
    ) -> WorkspaceProject | None:
        """Parse a project's pyproject.toml.

        Args:
            directory: Project directory.
            pyproject_path: Path to pyproject.toml.

        Returns:
            WorkspaceProject or None if parsing fails.
        """
        try:
            content = pyproject_path.read_text(encoding="utf-8")
        except OSError:
            return None

        name = directory.name
        dependencies: list[str] = []
        python_version = ""

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

        has_runtime = (directory / ".uvg" / "runtime" / "manifest.json").exists()
        runtime_fp = ""
        if has_runtime:
            fp_path = directory / ".uvg" / "runtime" / "fingerprint"
            if fp_path.exists():
                runtime_fp = fp_path.read_text(encoding="utf-8").strip()

        return WorkspaceProject(
            name=name,
            path=directory,
            dependencies=dependencies,
            python_version=python_version,
            has_runtime=has_runtime,
            runtime_fingerprint=runtime_fp,
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
