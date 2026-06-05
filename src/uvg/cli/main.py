"""UVG CLI - Global package manager using UV's cache.

UVG provides:
- Global package sharing (no duplicate storage)
- Multi-Python version support
- Portable lockfiles
- Instant runtime creation via symlinks
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from uvg import __version__
from uvg.cli.export_import import export, import_runtime
from uvg.cli.workspace import workspace
from uvg.python.manager import find_available_python_versions
from uvg.runtime.builder import RuntimeBuilder
from uvg.uv.cache import UVCache
from uvg.uv.downloader import UVDownloader


@click.group()
@click.version_option(version=__version__, prog_name="uvg")
def main() -> None:
    """UVG - Global package manager with UV's speed."""
    pass


main.add_command(export)
main.add_command(import_runtime, name="import")
main.add_command(workspace)


@main.command()
@click.option("--python", "python_version", help="Python version (e.g., 3.12)")
def init(python_version: str | None) -> None:
    """Initialize UVG in current directory."""
    project_dir = Path.cwd()
    python_version = python_version or f"{sys.version_info.major}.{sys.version_info.minor}"

    # Create uvg.lock
    lockfile = {
        "version": "1.0",
        "python_version": python_version,
        "packages": [],
    }

    lockfile_path = project_dir / "uvg.lock"
    if lockfile_path.exists():
        click.echo(f"uvg.lock already exists in {project_dir}")
        return

    with open(lockfile_path, "w") as f:
        json.dump(lockfile, f, indent=2)

    click.echo(f"Initialized UVG in {project_dir}")
    click.echo(f"Python version: {python_version}")


@main.command()
@click.argument("requirements", nargs=-1, required=True)
@click.option("--python", "python_version", help="Python version (e.g., 3.12)")
def add(requirements: tuple[str, ...], python_version: str | None) -> None:
    """Add package(s) to the project.

    Examples:
        uvg add requests
        uvg add flask django
        uvg add "numpy>=1.24"
    """
    project_dir = Path.cwd()
    lockfile_path = project_dir / "uvg.lock"

    if not lockfile_path.exists():
        click.echo("Error: uvg.lock not found. Run 'uvg init' first.")
        sys.exit(1)

    # Load lockfile
    with open(lockfile_path) as f:
        lockfile = json.load(f)

    python_version = (
        python_version or lockfile.get("python_version") or f"{sys.version_info.major}.{sys.version_info.minor}"
    )

    # Download packages using UV
    downloader = UVDownloader()
    req_list = list(requirements)

    if len(req_list) == 1:
        click.echo(f"Downloading {req_list[0]}...")
    else:
        click.echo(f"Downloading {len(req_list)} package(s)...")

    try:
        if len(req_list) == 1:
            packages = downloader.download(req_list[0], python_version)
        else:
            packages = downloader.download_multiple(req_list, python_version)
    except RuntimeError as e:
        click.echo(f"Error: {e}")
        sys.exit(1)

    # Add to lockfile
    for name, version in packages:
        # Check if already in lockfile
        existing = [p for p in lockfile["packages"] if p["name"] == name]
        if existing:
            click.echo(f"  {name} already in lockfile (version {existing[0]['version']})")
        else:
            lockfile["packages"].append({"name": name, "version": version})
            click.echo(f"  Added {name}=={version}")

    # Save lockfile
    with open(lockfile_path, "w") as f:
        json.dump(lockfile, f, indent=2)

    click.echo(f"Updated uvg.lock with {len(packages)} package(s)")


@main.command()
@click.option("--python", "python_version", help="Python version (e.g., 3.12)")
def sync(python_version: str | None) -> None:
    """Sync runtime from lockfile."""
    project_dir = Path.cwd()
    lockfile_path = project_dir / "uvg.lock"

    if not lockfile_path.exists():
        click.echo("Error: uvg.lock not found. Run 'uvg init' first.")
        sys.exit(1)

    # Load lockfile
    with open(lockfile_path) as f:
        lockfile = json.load(f)

    python_version = (
        python_version or lockfile.get("python_version") or f"{sys.version_info.major}.{sys.version_info.minor}"
    )

    # Extract packages
    packages = [(p["name"], p["version"]) for p in lockfile["packages"]]

    if not packages:
        click.echo("No packages in lockfile")
        return

    # Check if packages are in cache
    uv_cache = UVCache()
    missing_packages = []
    for name, version in packages:
        if uv_cache.find_package(name, version, python_version) is None:
            missing_packages.append(f"{name}=={version}")

    if missing_packages:
        click.echo(f"Warning: {len(missing_packages)} package(s) not found in UV cache:")
        for pkg in missing_packages[:5]:  # Show first 5
            click.echo(f"  - {pkg}")
        if len(missing_packages) > 5:
            click.echo(f"  ... and {len(missing_packages) - 5} more")
        click.echo("\nThese packages may need to be re-downloaded.")
        click.echo("Try running: uvg add <package> to re-download")

    # Build runtime
    click.echo(f"Building runtime for Python {python_version}...")
    builder = RuntimeBuilder(project_dir, python_version)
    success = builder.build(packages)

    if success:
        click.echo(f"Runtime created at {builder.runtime_dir}")
        click.echo(f"  Packages: {len(packages)}")
        click.echo(f"  Python: {python_version}")
    else:
        click.echo("Error: Failed to build runtime")
        sys.exit(1)


@main.command()
@click.argument("python_version")
@click.option("--rebuild/--no-rebuild", default=True, help="Rebuild runtime after switching")
def use(python_version: str, rebuild: bool) -> None:
    """Switch Python version for the project.

    Example: uvg use 3.12
    """
    project_dir = Path.cwd()
    lockfile_path = project_dir / "uvg.lock"

    if not lockfile_path.exists():
        click.echo("Error: uvg.lock not found. Run 'uvg init' first.")
        sys.exit(1)

    # Check if Python version is available
    available_versions = find_available_python_versions()
    if python_version not in available_versions:
        click.echo(f"Error: Python {python_version} not found on system.")
        click.echo(f"Available versions: {', '.join(available_versions)}")
        sys.exit(1)

    # Update lockfile
    with open(lockfile_path) as f:
        lockfile = json.load(f)

    old_version = lockfile.get("python_version", "unknown")
    lockfile["python_version"] = python_version

    with open(lockfile_path, "w") as f:
        json.dump(lockfile, f, indent=2)

    click.echo(f"Switched from Python {old_version} to {python_version}")

    # Rebuild runtime if requested and packages exist
    if rebuild and lockfile.get("packages"):
        packages = [(p["name"], p["version"]) for p in lockfile["packages"]]
        click.echo(f"Rebuilding runtime for Python {python_version}...")
        builder = RuntimeBuilder(project_dir, python_version)
        success = builder.build(packages)

        if success:
            click.echo(f"Runtime rebuilt with {len(packages)} package(s)")
        else:
            click.echo("Warning: Failed to rebuild runtime", err=True)


@main.command(context_settings={"ignore_unknown_options": True})
@click.argument("command", nargs=-1, type=click.UNPROCESSED)
@click.option("--python", "python_version", help="Python version (e.g., 3.12)")
def run(command: tuple[str, ...], python_version: str | None) -> None:
    """Run a command with the project runtime."""
    project_dir = Path.cwd()
    runtime_dir = project_dir / ".uvg" / "runtime"

    if not runtime_dir.exists():
        click.echo("Error: Runtime not found. Run 'uvg sync' first.")
        sys.exit(1)

    if not command:
        click.echo("Error: No command specified")
        sys.exit(1)

    # Load manifest
    manifest_path = runtime_dir / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    python_version = python_version or manifest.get("python_version")

    # Build runtime
    builder = RuntimeBuilder(project_dir, python_version)
    packages = [(p["name"], p["version"]) for p in manifest["packages"]]
    builder.build(packages)

    # Run command
    exit_code = builder.run(list(command))
    sys.exit(exit_code)


@main.command()
def clean() -> None:
    """Clean runtime directory."""
    project_dir = Path.cwd()
    runtime_dir = project_dir / ".uvg" / "runtime"

    if runtime_dir.exists():
        import shutil

        shutil.rmtree(runtime_dir)
        click.echo(f"Cleaned {runtime_dir}")
    else:
        click.echo("No runtime to clean")


@main.command()
def info() -> None:
    """Show UVG information."""
    uv_cache = UVCache()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    project_dir = Path.cwd()
    lockfile_path = project_dir / "uvg.lock"

    click.echo(f"UVG version: {__version__}")
    click.echo(f"Python version: {python_version}")
    click.echo(f"UV cache: {uv_cache.cache_path}")
    click.echo(f"UV wheels: {uv_cache.wheels_path}")

    # Count cached packages
    packages = uv_cache.find_all_packages(python_version)
    click.echo(f"Cached packages: {len(packages)}")

    # Show project info if in a UVG project
    if lockfile_path.exists():
        with open(lockfile_path) as f:
            lockfile = json.load(f)
        project_python = lockfile.get("python_version", "unknown")
        project_packages = len(lockfile.get("packages", []))
        click.echo("\nProject:")
        click.echo(f"  Python version: {project_python}")
        click.echo(f"  Packages: {project_packages}")


@main.command(name="list")
def list_python() -> None:
    """List available Python versions."""
    available_versions = find_available_python_versions()

    if not available_versions:
        click.echo("No Python versions found in PATH")
        return

    click.echo("Available Python versions:")
    for version in available_versions:
        click.echo(f"  {version}")

    # Show current project version if in a UVG project
    project_dir = Path.cwd()
    lockfile_path = project_dir / "uvg.lock"
    if lockfile_path.exists():
        with open(lockfile_path) as f:
            lockfile = json.load(f)
        project_python = lockfile.get("python_version")
        if project_python:
            click.echo(f"\nProject using: Python {project_python}")


if __name__ == "__main__":
    main()
