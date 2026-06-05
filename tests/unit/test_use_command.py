"""Tests for use command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from uvg.cli.main import main


class TestUseCommand:
    """Test use command."""

    def test_use_switches_python_version(self, tmp_path: Path) -> None:
        """Test switching Python version."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize project
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            # Get current Python version
            with open("uvg.lock") as f:
                lockfile = json.load(f)
            original_version = lockfile["python_version"]

            # Find another available version
            from uvg.python.manager import find_available_python_versions

            versions = find_available_python_versions()
            other_version = None
            for v in versions:
                if v != original_version:
                    other_version = v
                    break

            if other_version:
                # Switch to other version
                result = runner.invoke(main, ["use", other_version])
                assert result.exit_code == 0
                assert f"Switched from Python {original_version} to {other_version}" in result.output

                # Verify lockfile was updated
                with open("uvg.lock") as f:
                    lockfile = json.load(f)
                assert lockfile["python_version"] == other_version

    def test_use_with_packages(self, tmp_path: Path) -> None:
        """Test switching Python version with packages."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize and add a package
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            result = runner.invoke(main, ["add", "requests"])
            assert result.exit_code == 0

            # Sync to build runtime
            result = runner.invoke(main, ["sync"])
            assert result.exit_code == 0

            # Find another available version
            from uvg.python.manager import find_available_python_versions

            versions = find_available_python_versions()
            if len(versions) > 1:
                other_version = versions[1] if versions[0] == "3.13" else versions[0]

                # Switch version (should rebuild)
                result = runner.invoke(main, ["use", other_version])
                assert result.exit_code == 0
                assert "Rebuilding runtime" in result.output

    def test_use_invalid_version(self, tmp_path: Path) -> None:
        """Test switching to invalid Python version."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize project
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            # Try to switch to non-existent version
            result = runner.invoke(main, ["use", "99.99"])
            assert result.exit_code != 0
            assert "not found on system" in result.output

    def test_use_without_lockfile(self, tmp_path: Path) -> None:
        """Test use command without lockfile."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["use", "3.12"])
            assert result.exit_code != 0
            assert "uvg.lock not found" in result.output

    def test_use_no_rebuild(self, tmp_path: Path) -> None:
        """Test use command with --no-rebuild."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize and add a package
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            result = runner.invoke(main, ["add", "requests"])
            assert result.exit_code == 0

            # Find another available version
            from uvg.python.manager import find_available_python_versions

            versions = find_available_python_versions()
            if len(versions) > 1:
                other_version = versions[1] if versions[0] == "3.13" else versions[0]

                # Switch version without rebuild
                result = runner.invoke(main, ["use", other_version, "--no-rebuild"])
                assert result.exit_code == 0
                assert "Rebuilding runtime" not in result.output
