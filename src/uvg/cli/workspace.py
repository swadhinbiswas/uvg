"""Workspace CLI commands.

Commands for managing monorepo workspaces with multiple projects.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from uvg.workspace.manager import WorkspaceManager


@click.group()
def workspace() -> None:
    """Manage workspace with multiple projects."""
    pass


@workspace.command()
@click.option("--root", "root_dir", type=click.Path(exists=True), help="Workspace root directory")
def sync(root_dir: str | None) -> None:
    """Synchronize all projects in the workspace."""
    root = Path(root_dir) if root_dir else Path.cwd()
    manager = WorkspaceManager(root)

    click.echo(f"Discovering projects in {root}...")
    result = manager.sync()

    click.echo(f"\nSynced {result.synced_projects}/{result.total_projects} projects")

    if result.failed_projects > 0:
        click.echo(f"Failed: {result.failed_projects} projects")
        for error in result.errors:
            click.echo(f"  - {error}")
        sys.exit(1)

    if result.synced_projects == 0:
        click.echo("No projects found or no lockfiles present")
    else:
        click.echo("✓ All projects synchronized successfully")


@workspace.command()
@click.option("--root", "root_dir", type=click.Path(exists=True), help="Workspace root directory")
def doctor(root_dir: str | None) -> None:
    """Run health checks on all projects in the workspace."""
    root = Path(root_dir) if root_dir else Path.cwd()
    manager = WorkspaceManager(root)

    click.echo(f"Running health checks in {root}...")
    result = manager.doctor()

    click.echo("\nHealth check results:")
    click.echo(f"  Total projects: {result.total_projects}")
    click.echo(f"  Healthy: {result.healthy_projects}")
    click.echo(f"  Unhealthy: {result.unhealthy_projects}")

    if result.unhealthy_projects > 0:
        click.echo("\nUnhealthy projects:")
        for name, report in result.project_reports.items():
            if report.runtime_stats and not report.runtime_stats.is_valid:
                click.echo(f"  - {name}")
                if report.runtime_stats.verification_errors:
                    click.echo(f"    Errors: {len(report.runtime_stats.verification_errors)}")

    if result.shared_dependency_issues:
        click.echo("\nShared dependency issues:")
        for issue in result.shared_dependency_issues:
            click.echo(f"  - {issue}")

    if result.unhealthy_projects == 0:
        click.echo("\n✓ All projects are healthy")
    else:
        sys.exit(1)


@workspace.command()
@click.option("--root", "root_dir", type=click.Path(exists=True), help="Workspace root directory")
def stats(root_dir: str | None) -> None:
    """Show workspace statistics."""
    root = Path(root_dir) if root_dir else Path.cwd()
    manager = WorkspaceManager(root)

    click.echo(f"Gathering statistics for {root}...")
    stats = manager.get_stats()

    click.echo("\nWorkspace Statistics:")
    click.echo(f"  Total projects: {stats.total_projects}")
    click.echo(f"  Projects with runtime: {stats.projects_with_runtime}")
    click.echo(f"  Projects without runtime: {stats.projects_without_runtime}")
    click.echo("\nDependencies:")
    click.echo(f"  Total dependency instances: {stats.total_dependencies}")
    click.echo(f"  Unique dependencies: {stats.unique_dependencies}")
    click.echo(f"  Shared dependencies: {stats.shared_dependencies}")

    if stats.python_versions:
        click.echo("\nPython versions:")
        for version in sorted(stats.python_versions):
            click.echo(f"  - {version}")

    if stats.dependency_distribution:
        click.echo("\nMost used dependencies:")
        sorted_deps = sorted(stats.dependency_distribution.items(), key=lambda x: x[1], reverse=True)
        for dep, count in sorted_deps[:10]:
            click.echo(f"  {dep}: {count} project(s)")


@workspace.command(name="list")
@click.option("--root", "root_dir", type=click.Path(exists=True), help="Workspace root directory")
def list_projects(root_dir: str | None) -> None:
    """List all projects in the workspace."""
    root = Path(root_dir) if root_dir else Path.cwd()

    from uvg.workspace.discovery import WorkspaceDiscovery

    discovery = WorkspaceDiscovery(root)
    manifest = discovery.discover()

    if not manifest.projects:
        click.echo("No projects found in workspace")
        return

    click.echo(f"Projects in {root}:\n")

    for project in manifest.projects:
        status = "✓" if project.has_runtime else "✗"
        runtime_status = "has runtime" if project.has_runtime else "no runtime"

        click.echo(f"  {status} {project.name}")
        click.echo(f"    Path: {project.path.relative_to(root)}")
        click.echo(f"    Status: {runtime_status}")

        if project.python_version:
            click.echo(f"    Python: {project.python_version}")

        if project.dependencies:
            click.echo(f"    Dependencies: {len(project.dependencies)}")

        click.echo()


@workspace.command()
@click.option("--root", "root_dir", type=click.Path(exists=True), help="Workspace root directory")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def graph(root_dir: str | None, output_json: bool) -> None:
    """Show workspace dependency graph."""
    root = Path(root_dir) if root_dir else Path.cwd()
    manager = WorkspaceManager(root)

    graph_data = manager.get_graph()

    if output_json:
        click.echo(json.dumps(graph_data, indent=2))
        return

    if not graph_data:
        click.echo("No projects found in workspace")
        return

    click.echo("Workspace Dependency Graph:\n")

    for project, deps in sorted(graph_data.items()):
        click.echo(f"{project}")
        if deps:
            for dep in sorted(deps):
                click.echo(f"  └─ {dep}")
        else:
            click.echo("  └─ (no dependencies)")
        click.echo()


@workspace.command()
@click.option("--root", "root_dir", type=click.Path(exists=True), help="Workspace root directory")
def shared(root_dir: str | None) -> None:
    """Show dependencies shared across projects."""
    root = Path(root_dir) if root_dir else Path.cwd()

    from uvg.workspace.discovery import WorkspaceDiscovery

    discovery = WorkspaceDiscovery(root)
    shared_deps = discovery.get_shared_dependencies()

    if not shared_deps:
        click.echo("No shared dependencies found")
        return

    click.echo("Shared Dependencies:\n")

    sorted_deps = sorted(shared_deps.items(), key=lambda x: len(x[1]), reverse=True)

    for dep, projects in sorted_deps:
        click.echo(f"{dep} ({len(projects)} projects)")
        for project in sorted(projects):
            click.echo(f"  - {project}")
        click.echo()
