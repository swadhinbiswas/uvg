"""Export and import runtime functionality."""

from __future__ import annotations

import json
import tarfile
import tempfile
from pathlib import Path

import click

from gvx.runtime.builder import RuntimeBuilder


@click.command()
@click.option("--output", "-o", type=click.Path(), help="Output tarball path")
def export(output: str | None) -> None:
    """Export runtime to a tarball for CI/CD."""
    project_dir = Path.cwd()
    runtime_dir = project_dir / ".gvx" / "runtime"

    if not runtime_dir.exists():
        click.echo("Error: No runtime found. Run 'gvx sync' first.", err=True)
        raise SystemExit(1)

    lockfile = project_dir / "gvx.lock"
    if not lockfile.exists():
        click.echo("Error: No gvx.lock found.", err=True)
        raise SystemExit(1)

    # Create tarball
    if output is None:
        with open(lockfile) as f:
            data = json.load(f)
        project_name = data.get("project", {}).get("name", "project")
        python_version = data.get("python_version", "unknown")
        output = f"{project_name}-runtime-{python_version}.tar.gz"

    output_path = Path(output)

    click.echo(f"Exporting runtime to {output_path}...")

    with tarfile.open(output_path, "w:gz") as tar:
        # Add runtime directory
        tar.add(runtime_dir, arcname="runtime")
        # Add lockfile
        tar.add(lockfile, arcname="gvx.lock")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    click.echo(f"✓ Exported runtime ({size_mb:.1f} MB)")


@click.command()
@click.argument("tarball", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help="Overwrite existing runtime")
def import_runtime(tarball: str, force: bool) -> None:
    """Import runtime from a tarball."""
    project_dir = Path.cwd()
    runtime_dir = project_dir / ".gvx" / "runtime"

    if runtime_dir.exists() and not force:
        click.echo("Error: Runtime already exists. Use --force to overwrite.", err=True)
        raise SystemExit(1)

    tarball_path = Path(tarball)
    click.echo(f"Importing runtime from {tarball_path}...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Extract tarball
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(tmpdir_path)

        # Move runtime to project
        extracted_runtime = tmpdir_path / "runtime"
        if not extracted_runtime.exists():
            click.echo("Error: Invalid tarball (no runtime directory)", err=True)
            raise SystemExit(1)

        # Remove existing runtime if force
        if runtime_dir.exists():
            import shutil

            shutil.rmtree(runtime_dir)

        # Move runtime
        import shutil

        shutil.move(str(extracted_runtime), str(runtime_dir))

        # Copy lockfile if it exists
        extracted_lockfile = tmpdir_path / "gvx.lock"
        if extracted_lockfile.exists():
            project_lockfile = project_dir / "gvx.lock"
            if project_lockfile.exists() and not force:
                click.echo("Warning: gvx.lock already exists, skipping", err=True)
            else:
                shutil.copy2(extracted_lockfile, project_lockfile)

    # Verify runtime
    builder = RuntimeBuilder(project_dir)
    if builder.verify():
        click.echo("✓ Imported runtime successfully")
    else:
        click.echo("Warning: Runtime verification failed", err=True)
