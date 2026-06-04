"""Workspace manager.

Handles synchronization, diagnostics, and analytics across
all projects in a workspace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from uvg.intelligence.scanner import ProjectScanner, ScanResult
from uvg.runtime.builder import RuntimeBuilder
from uvg.store.store import Store
from uvg.workspace.discovery import WorkspaceDiscovery, WorkspaceProject


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
    """Manages workspace-wide operations.

    Provides synchronization, diagnostics, and analytics
    across all projects in a monorepo.
    """

    def __init__(
        self,
        root: Path,
        store: Store | None = None,
    ) -> None:
        """Initialize workspace manager.

        Args:
            root: Workspace root directory.
            store: UVG store instance.
        """
        self.root = root
        self.store = store
        self.discovery = WorkspaceDiscovery(root)
        self.scanner = ProjectScanner(store=store)

    def sync(self) -> WorkspaceSyncResult:
        """Synchronize all projects in the workspace.

        Returns:
            WorkspaceSyncResult with sync status.
        """
        manifest = self.discovery.discover()
        result = WorkspaceSyncResult(total_projects=len(manifest.projects))

        for project in manifest.projects:
            try:
                self._sync_project(project)
                result.synced_projects += 1
                result.project_results[project.name] = "synced"
            except Exception as e:
                result.failed_projects += 1
                result.errors.append(f"{project.name}: {e}")
                result.project_results[project.name] = f"failed: {e}"

        return result

    def _sync_project(self, project: WorkspaceProject) -> None:
        """Synchronize a single project.

        Args:
            project: Workspace project to sync.
        """
        runtime_dir = project.runtime_dir
        manifest_path = runtime_dir / "manifest.json"

        if not manifest_path.exists():
            return

        from uvg.runtime.manifest import RuntimeManifest

        manifest = RuntimeManifest.load(manifest_path)

        if self.store is None:
            return

        builder = RuntimeBuilder(
            runtime_dir=runtime_dir,
            store_path=self.store.store_path,
        )

        packages: dict[str, dict[str, object]] = {}
        for name, pkg in manifest.packages.items():
            packages[name] = {
                "version": pkg.version,
                "wheel_hash": pkg.wheel_hash,
                "abi": pkg.abi,
                "platform": pkg.platform,
                "dependencies": pkg.dependencies,
                "is_native": pkg.is_native,
            }

        entry_points: dict[str, dict[str, str]] = {}
        for ep_name, ep in manifest.entry_points.items():
            entry_points[ep_name] = {
                "module": ep.module,
                "function": ep.function,
            }

        builder.build(
            packages=packages,
            python_version=manifest.python_version,
            platform=manifest.platform,
            architecture=manifest.architecture,
            abi=manifest.abi,
            entry_points=entry_points if entry_points else None,
        )

    def doctor(self) -> WorkspaceDoctorResult:
        """Run health checks on all workspace projects.

        Returns:
            WorkspaceDoctorResult with health status.
        """
        manifest = self.discovery.discover()
        result = WorkspaceDoctorResult(total_projects=len(manifest.projects))

        for project in manifest.projects:
            scan_result = self.scanner.scan_project(
                project_path=project.path,
                runtime_dir=project.runtime_dir,
            )
            result.project_reports[project.name] = scan_result

            if scan_result.has_issues:
                result.unhealthy_projects += 1
            else:
                result.healthy_projects += 1

        shared = manifest.get_shared_dependencies()
        for dep, projects in shared.items():
            result.shared_dependency_issues.append(f"{dep} used by {len(projects)} projects: {', '.join(projects)}")

        return result

    def get_graph(self) -> dict[str, list[str]]:
        """Get the workspace dependency graph.

        Returns:
            Dict mapping project name to its dependencies.
        """
        return self.discovery.get_dependency_graph()

    def get_stats(self) -> WorkspaceStats:
        """Get workspace-wide statistics.

        Returns:
            WorkspaceStats with analytics.
        """
        manifest = self.discovery.discover()
        stats = WorkspaceStats(total_projects=len(manifest.projects))

        all_deps: set[str] = set()
        dep_count: dict[str, int] = {}
        python_versions: set[str] = set()

        for project in manifest.projects:
            if project.has_runtime:
                stats.projects_with_runtime += 1
            else:
                stats.projects_without_runtime += 1

            if project.python_version:
                python_versions.add(project.python_version)

            for dep in project.dependencies:
                all_deps.add(dep)
                dep_count[dep] = dep_count.get(dep, 0) + 1

        stats.total_dependencies = sum(len(p.dependencies) for p in manifest.projects)
        stats.unique_dependencies = len(all_deps)
        stats.shared_dependencies = sum(1 for c in dep_count.values() if c > 1)
        stats.python_versions = sorted(python_versions)
        stats.dependency_distribution = dict(sorted(dep_count.items(), key=lambda x: x[1], reverse=True))

        return stats
