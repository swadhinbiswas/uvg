"""Tests for export/import functionality."""

import json
import tarfile
from pathlib import Path

from uvg.cli.export_import import export, import_runtime
from uvg.runtime.builder import RuntimeBuilder


class TestExportImport:
    """Test export and import commands."""

    def test_export_creates_tarball(self, tmp_path: Path) -> None:
        """Test that export creates a tarball."""
        # Create a test project with runtime
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create uvg.lock
        lockfile = project_dir / "uvg.lock"
        lockfile.write_text(json.dumps({"python_version": "3.13", "packages": []}))

        # Create runtime directory
        runtime_dir = project_dir / ".uvg" / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "site-packages").mkdir()
        (runtime_dir / "manifest.json").write_text(json.dumps({"python_version": "3.13", "packages": []}))

        # Change to project directory
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)

            # Create output path
            output = tmp_path / "test.tar.gz"

            # Run export
            from click.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(export, ["-o", str(output)])

            assert result.exit_code == 0
            assert output.exists()
            assert output.stat().st_size > 0

            # Verify tarball contents
            with tarfile.open(output, "r:gz") as tar:
                names = tar.getnames()
                assert "runtime/manifest.json" in names
                assert "uvg.lock" in names
        finally:
            os.chdir(old_cwd)

    def test_import_extracts_runtime(self, tmp_path: Path) -> None:
        """Test that import extracts runtime from tarball."""
        # Create a test tarball
        tarball = tmp_path / "test.tar.gz"

        # Create source project
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create uvg.lock
        lockfile = source_dir / "uvg.lock"
        lockfile.write_text(json.dumps({"python_version": "3.13", "packages": []}))

        # Create runtime directory
        runtime_dir = source_dir / ".uvg" / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "site-packages").mkdir()
        (runtime_dir / "manifest.json").write_text(json.dumps({"python_version": "3.13", "packages": []}))

        # Create tarball
        with tarfile.open(tarball, "w:gz") as tar:
            tar.add(runtime_dir, arcname="runtime")
            tar.add(lockfile, arcname="uvg.lock")

        # Create target project
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create uvg.lock in target
        target_lockfile = target_dir / "uvg.lock"
        target_lockfile.write_text(json.dumps({"python_version": "3.13", "packages": []}))

        # Change to target directory
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(target_dir)

            # Run import
            from click.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(import_runtime, [str(tarball)])

            assert result.exit_code == 0

            # Verify runtime was extracted
            target_runtime = target_dir / ".uvg" / "runtime"
            assert target_runtime.exists()
            assert (target_runtime / "manifest.json").exists()
            assert (target_runtime / "site-packages").exists()
        finally:
            os.chdir(old_cwd)

    def test_verify_runtime(self, tmp_path: Path) -> None:
        """Test runtime verification."""
        # Create a test project
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create runtime directory
        runtime_dir = project_dir / ".uvg" / "runtime"
        runtime_dir.mkdir(parents=True)
        site_packages = runtime_dir / "site-packages"
        site_packages.mkdir()

        # Create manifest
        manifest_path = runtime_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps({"python_version": "3.13", "packages": [{"name": "requests", "version": "2.31.0"}]})
        )

        # Create a symlink to a non-existent target
        fake_link = site_packages / "requests"
        fake_link.symlink_to("/nonexistent/path")

        # Verify should fail
        builder = RuntimeBuilder(project_dir)
        assert not builder.verify()

        # Remove the broken symlink
        fake_link.unlink()

        # Verify should pass now
        assert builder.verify()
