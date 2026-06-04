"""UVG CLI entry point.

Provides the command-line interface for UVG operations.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from uvg import __version__
from uvg.intelligence.scanner import ProjectScanner
from uvg.runtime.builder import RuntimeBuilder
from uvg.runtime.manifest import RuntimeManifest
from uvg.security.verifier import SecurityVerifier, VerificationStatus
from uvg.store.store import Store
from uvg.uv.lockfile import UVGLockfile
from uvg.uv.resolver import UVResolver
from uvg.workspace.manager import WorkspaceManager

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="uvg")
@click.option(
    "--store-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the UVG store directory.",
)
@click.pass_context
def main(ctx: click.Context, store_path: Path | None) -> None:
    """UVG - One Package Store. Zero Duplicate Environments.

    UVG is a runtime, storage, caching, diagnostics, and dependency
    intelligence layer built on top of UV.
    """
    ctx.ensure_object(dict)
    ctx.obj["store"] = Store(store_path=store_path)


@main.command()
def info() -> None:
    """Show UVG store information."""
    store: Store = click.get_current_context().obj["store"]
    info_data = store.get_info()

    console.print()
    console.print("[bold]UVG Store[/bold]")
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Store Path", info_data["store_path"])
    table.add_row("Objects", str(info_data["object_count"]))
    table.add_row("Total Size", f"{info_data['total_size_mb']} MB")

    console.print(table)
    console.print()


@main.group()
def store() -> None:
    """Manage the UVG content-addressable store."""


@store.command("info")
@click.pass_context
def store_info(ctx: click.Context) -> None:
    """Show store information."""
    store: Store = ctx.obj["store"]
    info_data = store.get_info()

    console.print()
    console.print("[bold]UVG Store[/bold]")
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Store Path", info_data["store_path"])
    table.add_row("Objects", str(info_data["object_count"]))
    table.add_row("Total Size", f"{info_data['total_size_mb']} MB")

    console.print(table)
    console.print()


@store.command("list")
@click.option("--limit", default=50, help="Maximum number of objects to show.")
@click.option("--offset", default=0, help="Number of objects to skip.")
@click.pass_context
def store_list(ctx: click.Context, limit: int, offset: int) -> None:
    """List objects in the store."""
    store: Store = ctx.obj["store"]
    objects = store.list_objects(limit=limit, offset=offset)

    if not objects:
        console.print("[yellow]No objects in store.[/yellow]")
        return

    table = Table(title="Store Objects")
    table.add_column("Package", style="cyan")
    table.add_column("Version", style="white")
    table.add_column("Python", style="white")
    table.add_column("ABI", style="white")
    table.add_column("Platform", style="white")
    table.add_column("Size", style="white")
    table.add_column("Native", style="white")

    for obj in objects:
        size_mb = round(obj["size_bytes"] / (1024 * 1024), 2)
        table.add_row(
            obj["package_name"],
            obj["package_version"],
            obj["python_version"],
            obj["abi_tag"],
            f"{obj['platform_tag']}-{obj['architecture']}",
            f"{size_mb} MB",
            "Yes" if obj["is_native"] else "No",
        )

    console.print()
    console.print(table)
    console.print()


@main.command()
@click.option(
    "--project",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the project directory.",
)
@click.option(
    "--runtime-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the runtime directory.",
)
@click.pass_context
def sync(
    ctx: click.Context,
    project: Path | None,
    runtime_dir: Path | None,
) -> None:
    """Sync dependencies to runtime."""
    store: Store = ctx.obj["store"]

    if project is None:
        project = Path.cwd()

    if runtime_dir is None:
        runtime_dir = project / ".uvg" / "runtime"

    manifest_path = project / "uvg.lock"
    if not manifest_path.exists():
        console.print("[yellow]No uvg.lock found. Run 'uvg init' first.[/yellow]")
        raise SystemExit(1)

    manifest = RuntimeManifest.load(manifest_path)

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

    builder = RuntimeBuilder(
        runtime_dir=runtime_dir,
        store_path=store.store_path,
    )

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    plat = platform.system().lower()
    arch = platform.machine()

    console.print(f"[cyan]Syncing runtime to {runtime_dir}[/cyan]")
    console.print(f"[cyan]Fingerprint: {manifest.fingerprint}[/cyan]")

    builder.build(
        packages=packages,
        python_version=python_version,
        platform=plat,
        architecture=arch,
        abi=manifest.abi,
        entry_points=entry_points if entry_points else None,
    )

    console.print("[green]Runtime synced successfully.[/green]")


@main.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.pass_context
def run(ctx: click.Context) -> None:
    """Run a command with the correct runtime."""
    project = Path.cwd()
    runtime_dir = project / ".uvg" / "runtime"
    manifest_path = runtime_dir / "manifest.json"

    if not manifest_path.exists():
        console.print("[yellow]No runtime found. Run 'uvg sync' first.[/yellow]")
        raise SystemExit(1)

    manifest = RuntimeManifest.load(manifest_path)
    paths = manifest.get_site_packages_paths()

    env = os.environ.copy()
    existing_path = env.get("PYTHONPATH", "")
    new_python_path = ":".join(paths)
    if existing_path:
        new_python_path = f"{new_python_path}:{existing_path}"
    env["PYTHONPATH"] = new_python_path

    result = subprocess.run(ctx.args, env=env)
    raise SystemExit(result.returncode)


@main.command()
@click.option(
    "--project",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the project directory.",
)
@click.pass_context
def doctor(ctx: click.Context, project: Path | None) -> None:
    """Diagnose dependency issues."""
    store: Store = ctx.obj["store"]

    if project is None:
        project = Path.cwd()

    runtime_dir = project / ".uvg" / "runtime"
    scanner = ProjectScanner(store=store)
    result = scanner.scan_project(project, runtime_dir=runtime_dir)

    console.print()
    console.print("[bold]UVG Doctor[/bold]")
    console.print()

    if result.runtime_stats:
        stats = result.runtime_stats
        console.print(f"[cyan]Project:[/cyan] {stats.project_path}")
        console.print(f"[cyan]Fingerprint:[/cyan] {stats.fingerprint}")
        console.print(f"[cyan]Packages:[/cyan] {stats.package_count}")
        console.print(f"[cyan]Python:[/cyan] {stats.python_version}")
        console.print(f"[cyan]Runtime valid:[/cyan] {'Yes' if stats.is_valid else 'No'}")
        console.print()

    if result.dependency_report:
        report = result.dependency_report
        console.print(f"[cyan]Files scanned:[/cyan] {report.files_scanned}")
        console.print(f"[cyan]Total imports:[/cyan] {report.total_imports}")
        console.print()

        if report.unused_dependencies:
            console.print("[yellow]Unused dependencies:[/yellow]")
            for dep in report.unused_dependencies:
                console.print(f"  - {dep}")
            console.print()

        if report.missing_dependencies:
            console.print("[red]Missing dependencies:[/yellow]")
            for dep in report.missing_dependencies:
                console.print(f"  - {dep}")
            console.print()

        if not report.unused_dependencies and not report.missing_dependencies:
            console.print("[green]No dependency issues found.[/green]")

    if result.scan_errors:
        console.print("[red]Errors:[/red]")
        for error in result.scan_errors:
            console.print(f"  - {error}")

    console.print()


@main.command()
@click.option(
    "--project",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the project directory.",
)
@click.pass_context
def scan(ctx: click.Context, project: Path | None) -> None:
    """Scan for unused and missing dependencies."""
    store: Store = ctx.obj["store"]

    if project is None:
        project = Path.cwd()

    runtime_dir = project / ".uvg" / "runtime"
    scanner = ProjectScanner(store=store)
    result = scanner.scan_project(project, runtime_dir=runtime_dir)

    console.print()
    console.print("[bold]UVG Scan[/bold]")
    console.print()

    if result.dependency_report:
        report = result.dependency_report
        table = Table(title="Dependency Analysis")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="white")
        table.add_column("Details", style="white")

        table.add_row(
            "Files scanned",
            str(report.files_scanned),
            "",
        )
        table.add_row(
            "Total imports",
            str(report.total_imports),
            "",
        )
        table.add_row(
            "Manifest packages",
            str(len(report.manifest_packages)),
            ", ".join(sorted(report.manifest_packages))[:60],
        )
        table.add_row(
            "Unused dependencies",
            str(len(report.unused_dependencies)),
            ", ".join(report.unused_dependencies)[:60] if report.unused_dependencies else "None",
        )
        table.add_row(
            "Missing dependencies",
            str(len(report.missing_dependencies)),
            ", ".join(report.missing_dependencies)[:60] if report.missing_dependencies else "None",
        )

        console.print(table)
    else:
        console.print("[yellow]No dependency report available.[/yellow]")

    console.print()


@main.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show storage and dependency statistics."""
    store: Store = ctx.obj["store"]
    scanner = ProjectScanner(store=store)
    storage_stats = scanner.get_storage_stats()

    console.print()
    console.print("[bold]UVG Stats[/bold]")
    console.print()

    table = Table(title="Storage Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total objects", str(storage_stats.total_objects))
    table.add_row("Total size", f"{storage_stats.total_size_mb} MB")
    table.add_row("Unique packages", str(storage_stats.unique_packages))
    table.add_row("Native packages", str(storage_stats.native_packages))
    table.add_row("Pure Python", str(storage_stats.pure_python_packages))
    table.add_row("Python versions", ", ".join(storage_stats.python_versions))

    console.print(table)
    console.print()


@main.group()
def workspace() -> None:
    """Manage workspace (monorepo) operations."""


@workspace.command("sync")
@click.option(
    "--root",
    type=click.Path(path_type=Path),
    default=None,
    help="Workspace root directory.",
)
@click.pass_context
def workspace_sync(ctx: click.Context, root: Path | None) -> None:
    """Synchronize all workspace projects."""
    store: Store = ctx.obj["store"]

    if root is None:
        root = Path.cwd()

    manager = WorkspaceManager(root=root, store=store)
    result = manager.sync()

    console.print()
    console.print("[bold]UVG Workspace Sync[/bold]")
    console.print()

    table = Table(title="Sync Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total projects", str(result.total_projects))
    table.add_row("Synced", str(result.synced_projects))
    table.add_row("Failed", str(result.failed_projects))

    console.print(table)

    if result.errors:
        console.print()
        console.print("[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  - {error}")

    console.print()


@workspace.command("doctor")
@click.option(
    "--root",
    type=click.Path(path_type=Path),
    default=None,
    help="Workspace root directory.",
)
@click.pass_context
def workspace_doctor(ctx: click.Context, root: Path | None) -> None:
    """Diagnose workspace issues."""
    store: Store = ctx.obj["store"]

    if root is None:
        root = Path.cwd()

    manager = WorkspaceManager(root=root, store=store)
    result = manager.doctor()

    console.print()
    console.print("[bold]UVG Workspace Doctor[/bold]")
    console.print()

    table = Table(title="Workspace Health")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total projects", str(result.total_projects))
    table.add_row("Healthy", str(result.healthy_projects))
    table.add_row("Unhealthy", str(result.unhealthy_projects))

    console.print(table)

    if result.shared_dependency_issues:
        console.print()
        console.print("[cyan]Shared dependencies:[/cyan]")
        for issue in result.shared_dependency_issues:
            console.print(f"  - {issue}")

    console.print()


@workspace.command("graph")
@click.option(
    "--root",
    type=click.Path(path_type=Path),
    default=None,
    help="Workspace root directory.",
)
@click.pass_context
def workspace_graph(ctx: click.Context, root: Path | None) -> None:
    """Visualize workspace dependency graph."""
    store: Store = ctx.obj["store"]

    if root is None:
        root = Path.cwd()

    manager = WorkspaceManager(root=root, store=store)
    graph = manager.get_graph()

    console.print()
    console.print("[bold]UVG Workspace Graph[/bold]")
    console.print()

    for project, deps in sorted(graph.items()):
        if deps:
            console.print(f"[cyan]{project}[/cyan]")
            for dep in sorted(deps):
                console.print(f"  -> {dep}")
        else:
            console.print(f"[cyan]{project}[/cyan] [dim](no dependencies)[/dim]")
        console.print()


@workspace.command("stats")
@click.option(
    "--root",
    type=click.Path(path_type=Path),
    default=None,
    help="Workspace root directory.",
)
@click.pass_context
def workspace_stats(ctx: click.Context, root: Path | None) -> None:
    """Show workspace statistics."""
    store: Store = ctx.obj["store"]

    if root is None:
        root = Path.cwd()

    manager = WorkspaceManager(root=root, store=store)
    stats = manager.get_stats()

    console.print()
    console.print("[bold]UVG Workspace Stats[/bold]")
    console.print()

    table = Table(title="Workspace Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total projects", str(stats.total_projects))
    table.add_row("Total dependencies", str(stats.total_dependencies))
    table.add_row("Unique dependencies", str(stats.unique_dependencies))
    table.add_row("Shared dependencies", str(stats.shared_dependencies))
    table.add_row("Projects with runtime", str(stats.projects_with_runtime))
    table.add_row("Projects without runtime", str(stats.projects_without_runtime))
    table.add_row("Python versions", ", ".join(stats.python_versions))

    console.print(table)

    if stats.dependency_distribution:
        console.print()
        console.print("[cyan]Top dependencies:[/cyan]")
        for dep, count in list(stats.dependency_distribution.items())[:10]:
            console.print(f"  {dep}: {count} projects")

    console.print()


@main.command()
@click.option(
    "--runtime",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to runtime directory.",
)
@click.option(
    "--lockfile",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to lockfile.",
)
@click.pass_context
def verify(
    ctx: click.Context,
    runtime: Path | None,
    lockfile: Path | None,
) -> None:
    """Verify runtime and store integrity."""
    store: Store = ctx.obj["store"]
    verifier = SecurityVerifier(store=store)

    report = verifier.verify_all(
        runtime_dir=runtime,
        lockfile_path=lockfile,
    )

    console.print()
    console.print("[bold]UVG Verify[/bold]")
    console.print()

    for check in report.checks:
        if check.status == VerificationStatus.PASS:
            icon = "[green]PASS[/green]"
        elif check.status == VerificationStatus.FAIL:
            icon = "[red]FAIL[/red]"
        elif check.status == VerificationStatus.WARN:
            icon = "[yellow]WARN[/yellow]"
        else:
            icon = "[dim]SKIP[/dim]"

        console.print(f"  {icon} {check.name}: {check.message}")
        if check.details:
            console.print(f"         {check.details}")

    console.print()

    if report.passed:
        console.print("[green]All checks passed.[/green]")
    else:
        console.print(f"[red]{report.failure_count} check(s) failed, {report.warning_count} warning(s).[/red]")

    console.print()


@main.command()
@click.option(
    "--project",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the project directory.",
)
def init(project: Path | None) -> None:
    """Initialize UVG in a project."""
    if project is None:
        project = Path.cwd()

    pyproject = project / "pyproject.toml"
    if not pyproject.exists():
        console.print("[yellow]No pyproject.toml found. Creating one...[/yellow]")
        pyproject.write_text(
            '[project]\nname = "my-project"\nversion = "0.1.0"\nrequires-python = ">=3.10"\n',
            encoding="utf-8",
        )

    runtime_dir = project / ".uvg" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[green]UVG initialized in {project}[/green]")
    console.print()


@main.command()
@click.argument("package")
@click.option(
    "--dev",
    is_flag=True,
    default=False,
    help="Add as a development dependency.",
)
@click.option(
    "--project",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the project directory.",
)
@click.pass_context
def add(ctx: click.Context, package: str, dev: bool, project: Path | None) -> None:
    """Add a dependency to the project."""
    if project is None:
        project = Path.cwd()

    resolver = UVResolver(project_dir=project)
    result = resolver.add_package(package, dev=dev)

    if result.returncode != 0:
        console.print(f"[red]Failed to add {package}: {result.stderr.decode()}[/red]")
        raise SystemExit(1)

    console.print(f"[green]Added {package}[/green]")

    lockfile_path = project / "uv.lock"
    if lockfile_path.exists():
        from uvg.uv.lockfile import UVLockfileParser

        uv_lockfile = UVLockfileParser.parse_uv_lock(lockfile_path)
        uvg_lockfile = UVGLockfile(
            python_version=uv_lockfile.python_version,
            platform=uv_lockfile.platform,
            architecture=uv_lockfile.architecture,
            packages=uv_lockfile.packages,
        )
        uvg_lockfile.save(project / "uvg.lock")
        console.print("[green]Generated uvg.lock[/green]")

    console.print()


@main.command()
@click.argument("package")
@click.option(
    "--project",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the project directory.",
)
def remove(package: str, project: Path | None) -> None:
    """Remove a dependency from the project."""
    if project is None:
        project = Path.cwd()

    resolver = UVResolver(project_dir=project)
    result = resolver.remove_package(package)

    if result.returncode != 0:
        console.print(f"[red]Failed to remove {package}: {result.stderr.decode()}[/red]")
        raise SystemExit(1)

    console.print(f"[green]Removed {package}[/green]")
    console.print()


def main_entry() -> None:
    """Entry point for the UVG CLI."""
    main()


if __name__ == "__main__":
    main_entry()
