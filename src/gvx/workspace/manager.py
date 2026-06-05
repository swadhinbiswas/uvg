"""Workspace manager.

Handles synchronization, diagnostics, and analytics across
all projects in a workspace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gvx.intelligence.scanner import ProjectScanner, ScanResult
from gvx.runtime.builder import RuntimeBuilder
from gvx.workspace.discovery import WorkspaceDiscovery


@dataclass
class WorkspaceSyncResult:
    """Result of a workspace synchronization."""

    total_projects: int = 0
    synced_projects: int = 0
    failed_projects: int = 0
    errors: list[str] = field(default_factory=list)
    project_results: dict[str, str] = field(default_factory=dict)


@dataclass
class WorkspaceDoctorResult:
    """Result of a workspace health check."""

    total_projects: int = 0
    healthy_projects: int = 0
    unhealthy_projects: int = 0
    project_reports: dict[str, ScanResult] = field(default_factory=dict)
    shared_dependency_issues: list[str] = field(default_factory=list)


@dataclass
class WorkspaceStats:
    """Statistics for the entire workspace."""

    total_projects: int = 0
    total_dependencies: int = 0
    unique_dependencies: int = 0
    shared_dependencies: int = 0
    projects_with_runtime: int = 0
    projects_without_runtime: int = 0
    python_versions: list[str] = field(default_factory=list)
    dependency_distribution: dict[str, int] = field(default_factory=dict)


class WorkspaceManager:
    """Manages workspace operations across multiple projects."""

    def __init__(self, root: Path) -> None:
        """Initialize workspace manager.

        Args:
            root: Workspace root directory.
        """
        self.root = root
        self.discovery = WorkspaceDiscovery(root)
        self.scanner = ProjectScanner()

    def sync(self) -> WorkspaceSyncResult:
        """Synchronize all projects in the workspace.

        Returns:
            WorkspaceSyncResult with synchronization results.
        """
        result = WorkspaceSyncResult()

        # Discover projects
        manifest = self.discovery.discover()
        result.total_projects = len(manifest.projects)

        # Sync each project
        for project in manifest.projects:
            try:
                # Build runtime
                builder = RuntimeBuilder(project.path, project.python_version)

                # Get packages from lockfile
                lockfile_path = project.path / "gvx.lock"
                if lockfile_path.exists():
                    import json

                    with open(lockfile_path) as f:
                        lockfile = json.load(f)

                    packages = [(p["name"], p["version"]) for p in lockfile["packages"]]
                    success = builder.build(packages)

                    if success:
                        result.synced_projects += 1
                        result.project_results[project.name] = "synced"
                    else:
                        result.failed_projects += 1
                        result.project_results[project.name] = "failed"
                        result.errors.append(f"Failed to sync {project.name}")
                else:
                    result.project_results[project.name] = "no lockfile"

            except Exception as e:
                result.failed_projects += 1
                result.project_results[project.name] = "error"
                result.errors.append(f"Error syncing {project.name}: {e}")

        return result

    def doctor(self) -> WorkspaceDoctorResult:
        """Run health checks on all projects.

        Returns:
            WorkspaceDoctorResult with health check results.
        """
        result = WorkspaceDoctorResult()

        # Discover projects
        manifest = self.discovery.discover()
        result.total_projects = len(manifest.projects)

        # Check each project
        for project in manifest.projects:
            scan_result = self.scanner.scan_project(project.path)
            result.project_reports[project.name] = scan_result

            if scan_result.runtime_stats and scan_result.runtime_stats.is_valid:
                result.healthy_projects += 1
            else:
                result.unhealthy_projects += 1

        return result

    def get_stats(self) -> WorkspaceStats:
        """Get workspace statistics.

        Returns:
            WorkspaceStats with workspace statistics.
        """
        stats = WorkspaceStats()

        # Discover projects
        manifest = self.discovery.discover()
        stats.total_projects = len(manifest.projects)

        # Collect stats
        all_deps: set[str] = set()
        dep_counts: dict[str, int] = {}

        for project in manifest.projects:
            # Check if runtime exists
            runtime_dir = project.path / ".gvx" / "runtime"
            if runtime_dir.exists():
                stats.projects_with_runtime += 1
            else:
                stats.projects_without_runtime += 1

            # Get dependencies from lockfile or pyproject.toml
            lockfile_path = project.path / "gvx.lock"
            if lockfile_path.exists():
                import json

                with open(lockfile_path) as f:
                    lockfile = json.load(f)

                for pkg in lockfile["packages"]:
                    dep_name = pkg["name"]
                    all_deps.add(dep_name)
                    dep_counts[dep_name] = dep_counts.get(dep_name, 0) + 1

                    # Track Python versions
                    if lockfile.get("python_version"):
                        py_ver = lockfile["python_version"]
                        if py_ver not in stats.python_versions:
                            stats.python_versions.append(py_ver)
            else:
                # Fall back to pyproject.toml
                pyproject_path = project.path / "pyproject.toml"
                if pyproject_path.exists():
                    try:
                        import tomllib  # type: ignore[import-not-found]

                        with open(pyproject_path, "rb") as f:
                            pyproject = tomllib.load(f)
                    except ImportError:
                        # Python < 3.11
                        import tomli as tomllib  # type: ignore[import-not-found]

                        with open(pyproject_path, "rb") as f:
                            pyproject = tomllib.load(f)

                    project_data = pyproject.get("project", {})
                    deps = project_data.get("dependencies", [])
                    for dep in deps:
                        # Parse dependency name (e.g., "requests>=2.0" -> "requests")
                        dep_name = (
                            dep.split(">=")[0]
                            .split("<=")[0]
                            .split("==")[0]
                            .split(">")[0]
                            .split("<")[0]
                            .split("[")[0]
                            .strip()
                        )
                        if dep_name:
                            all_deps.add(dep_name)
                            dep_counts[dep_name] = dep_counts.get(dep_name, 0) + 1

                    # Track Python version
                    requires_python = project_data.get("requires-python", "")
                    if requires_python and requires_python not in stats.python_versions:
                        stats.python_versions.append(requires_python)

        stats.unique_dependencies = len(all_deps)
        stats.total_dependencies = sum(dep_counts.values())
        stats.shared_dependencies = sum(1 for count in dep_counts.values() if count > 1)
        stats.dependency_distribution = dep_counts

        return stats

    def get_graph(self) -> dict[str, list[str]]:
        """Get workspace dependency graph.

        Returns:
            Dictionary mapping project names to their dependencies.
        """
        graph: dict[str, list[str]] = {}

        # Discover projects
        manifest = self.discovery.discover()

        for project in manifest.projects:
            deps: list[str] = []

            # Get dependencies from lockfile
            lockfile_path = project.path / "gvx.lock"
            if lockfile_path.exists():
                import json

                with open(lockfile_path) as f:
                    lockfile = json.load(f)

                deps = [pkg["name"] for pkg in lockfile["packages"]]

            graph[project.name] = deps

        return graph
