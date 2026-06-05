"""Tests for workspace CLI commands."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from gvx.cli.main import main


class TestWorkspaceCLI:
    """Test workspace CLI commands."""

    def test_workspace_list_empty(self, tmp_path: Path) -> None:
        """Test workspace list with no projects."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["workspace", "list"])
            assert result.exit_code == 0
            assert "No projects found" in result.output

    def test_workspace_list_with_projects(self, tmp_path: Path) -> None:
        """Test workspace list with projects."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create two projects with gvx.lock files
            project_a = tmp_path / "project-a"
            project_b = tmp_path / "project-b"
            project_a.mkdir()
            project_b.mkdir()

            # Create gvx.lock files manually
            import json

            lockfile_a = {
                "version": "1.0",
                "python_version": "3.13",
                "packages": [{"name": "requests", "version": "2.34.2"}],
            }
            lockfile_b = {
                "version": "1.0",
                "python_version": "3.13",
                "packages": [{"name": "flask", "version": "3.1.3"}],
            }

            with open(project_a / "gvx.lock", "w") as f:
                json.dump(lockfile_a, f)
            with open(project_b / "gvx.lock", "w") as f:
                json.dump(lockfile_b, f)

            result = runner.invoke(main, ["workspace", "list", "--root", str(tmp_path)])
            assert result.exit_code == 0
            assert "project-a" in result.output
            assert "project-b" in result.output

    def test_workspace_sync_empty(self, tmp_path: Path) -> None:
        """Test workspace sync with no projects."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["workspace", "sync"])
            assert result.exit_code == 0
            assert "Synced 0/0 projects" in result.output

    def test_workspace_stats_empty(self, tmp_path: Path) -> None:
        """Test workspace stats with no projects."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["workspace", "stats"])
            assert result.exit_code == 0
            assert "Total projects: 0" in result.output

    def test_workspace_graph_empty(self, tmp_path: Path) -> None:
        """Test workspace graph with no projects."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["workspace", "graph"])
            assert result.exit_code == 0
            assert "No projects found" in result.output

    def test_workspace_shared_empty(self, tmp_path: Path) -> None:
        """Test workspace shared with no projects."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["workspace", "shared"])
            assert result.exit_code == 0
            assert "No shared dependencies found" in result.output

    def test_workspace_doctor_empty(self, tmp_path: Path) -> None:
        """Test workspace doctor with no projects."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["workspace", "doctor"])
            assert result.exit_code == 0
            assert "Total projects: 0" in result.output
