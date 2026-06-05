"""Tests for workspace discovery and management."""

from __future__ import annotations

from pathlib import Path

from gvx.workspace.discovery import WorkspaceDiscovery, WorkspaceManifest, WorkspaceProject
from gvx.workspace.manager import WorkspaceManager


class TestWorkspaceProject:
    def test_runtime_dir(self, tmp_path: Path) -> None:
        project = WorkspaceProject(
            name="my-app",
            path=tmp_path / "my-app",
        )
        expected = tmp_path / "my-app" / ".gvx" / "runtime"
        assert project.runtime_dir == expected


class TestWorkspaceManifest:
    def test_to_dict(self, tmp_path: Path) -> None:
        manifest = WorkspaceManifest(
            root=tmp_path,
            projects=[
                WorkspaceProject(
                    name="api",
                    path=tmp_path / "api",
                    dependencies=["requests", "fastapi"],
                ),
                WorkspaceProject(
                    name="core",
                    path=tmp_path / "core",
                    dependencies=["pydantic"],
                ),
            ],
        )
        d = manifest.to_dict()
        assert d["root"] == str(tmp_path)
        assert len(d["projects"]) == 2

    def test_from_dict(self, tmp_path: Path) -> None:
        d = {
            "root": str(tmp_path),
            "members": ["api", "core"],
            "exclude": ["node_modules"],
            "projects": [
                {
                    "name": "api",
                    "path": str(tmp_path / "api"),
                    "dependencies": ["requests"],
                    "python_version": "3.12",
                },
            ],
        }
        manifest = WorkspaceManifest.from_dict(d, tmp_path)
        assert len(manifest.projects) == 1
        assert manifest.projects[0].name == "api"

    def test_save_load(self, tmp_path: Path) -> None:
        manifest = WorkspaceManifest(
            root=tmp_path,
            projects=[
                WorkspaceProject(
                    name="api",
                    path=tmp_path / "api",
                    dependencies=["requests"],
                ),
            ],
        )

        path = tmp_path / "workspace.json"
        manifest.save(path)
        loaded = WorkspaceManifest.load(path)
        assert len(loaded.projects) == 1
        assert loaded.projects[0].name == "api"

    def test_get_project(self, tmp_path: Path) -> None:
        manifest = WorkspaceManifest(
            root=tmp_path,
            projects=[
                WorkspaceProject(name="api", path=tmp_path / "api"),
                WorkspaceProject(name="core", path=tmp_path / "core"),
            ],
        )
        project = manifest.get_project("api")
        assert project is not None
        assert project.name == "api"
        assert manifest.get_project("missing") is None

    def test_get_shared_dependencies(self, tmp_path: Path) -> None:
        manifest = WorkspaceManifest(
            root=tmp_path,
            projects=[
                WorkspaceProject(
                    name="api",
                    path=tmp_path / "api",
                    dependencies=["requests", "pydantic"],
                ),
                WorkspaceProject(
                    name="core",
                    path=tmp_path / "core",
                    dependencies=["pydantic", "numpy"],
                ),
                WorkspaceProject(
                    name="worker",
                    path=tmp_path / "worker",
                    dependencies=["pydantic", "celery"],
                ),
            ],
        )
        shared = manifest.get_shared_dependencies()
        assert "pydantic" in shared
        assert len(shared["pydantic"]) == 3
        assert "requests" not in shared


class TestWorkspaceDiscovery:
    def test_discover_empty(self, tmp_path: Path) -> None:
        discovery = WorkspaceDiscovery(tmp_path)
        manifest = discovery.discover()
        assert len(manifest.projects) == 0

    def test_discover_single_project(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "my-app"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text('[project]\nname = "my-app"\ndependencies = ["requests"]\n')

        discovery = WorkspaceDiscovery(tmp_path)
        manifest = discovery.discover()
        assert len(manifest.projects) == 1
        assert manifest.projects[0].name == "my-app"

    def test_discover_multiple_projects(self, tmp_path: Path) -> None:
        for name in ["api", "core", "worker"]:
            project_dir = tmp_path / name
            project_dir.mkdir()
            (project_dir / "pyproject.toml").write_text(f'[project]\nname = "{name}"\ndependencies = ["requests"]\n')

        discovery = WorkspaceDiscovery(tmp_path)
        manifest = discovery.discover()
        assert len(manifest.projects) == 3

    def test_discover_excludes_venv(self, tmp_path: Path) -> None:
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        (venv_dir / "pyproject.toml").write_text('[project]\nname = "hidden"\n')

        discovery = WorkspaceDiscovery(tmp_path)
        manifest = discovery.discover()
        assert len(manifest.projects) == 0

    def test_discover_respects_max_depth(self, tmp_path: Path) -> None:
        deep_dir = tmp_path / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)
        (deep_dir / "pyproject.toml").write_text('[project]\nname = "deep"\n')

        discovery = WorkspaceDiscovery(tmp_path)
        manifest = discovery.discover(max_depth=1)
        assert len(manifest.projects) == 0

        manifest = discovery.discover(max_depth=5)
        assert len(manifest.projects) == 1

    def test_get_dependency_graph(self, tmp_path: Path) -> None:
        for name, deps in [("api", "requests, fastapi"), ("core", "pydantic")]:
            project_dir = tmp_path / name
            project_dir.mkdir()
            (project_dir / "pyproject.toml").write_text(f'[project]\nname = "{name}"\ndependencies = ["{deps}"]\n')

        discovery = WorkspaceDiscovery(tmp_path)
        graph = discovery.get_dependency_graph()
        assert "api" in graph
        assert "core" in graph

    def test_get_shared_dependencies(self, tmp_path: Path) -> None:
        for name in ["api", "core", "worker"]:
            project_dir = tmp_path / name
            project_dir.mkdir()
            (project_dir / "pyproject.toml").write_text('[project]\nname = "test"\ndependencies = ["requests"]\n')

        discovery = WorkspaceDiscovery(tmp_path)
        shared = discovery.get_shared_dependencies()
        assert "requests" in shared
        assert len(shared["requests"]) == 3


class TestWorkspaceManager:
    def test_sync_empty(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(root=tmp_path)
        result = manager.sync()
        assert result.total_projects == 0
        assert result.synced_projects == 0

    def test_sync_with_projects(self, tmp_path: Path) -> None:
        for name in ["api", "core"]:
            project_dir = tmp_path / name
            project_dir.mkdir()
            (project_dir / "pyproject.toml").write_text(f'[project]\nname = "{name}"\n')

        manager = WorkspaceManager(root=tmp_path)
        result = manager.sync()
        assert result.total_projects == 2

    def test_doctor_empty(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(root=tmp_path)
        result = manager.doctor()
        assert result.total_projects == 0

    def test_doctor_with_projects(self, tmp_path: Path) -> None:
        for name in ["api", "core"]:
            project_dir = tmp_path / name
            project_dir.mkdir()
            (project_dir / "pyproject.toml").write_text(f'[project]\nname = "{name}"\n')

        manager = WorkspaceManager(root=tmp_path)
        result = manager.doctor()
        assert result.total_projects == 2

    def test_get_graph(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "api"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text('[project]\nname = "api"\ndependencies = ["requests"]\n')

        manager = WorkspaceManager(root=tmp_path)
        graph = manager.get_graph()
        assert "api" in graph

    def test_get_stats(self, tmp_path: Path) -> None:
        for name in ["api", "core", "worker"]:
            project_dir = tmp_path / name
            project_dir.mkdir()
            (project_dir / "pyproject.toml").write_text(f'[project]\nname = "{name}"\ndependencies = ["requests"]\n')

        manager = WorkspaceManager(root=tmp_path)
        stats = manager.get_stats()
        assert stats.total_projects == 3
        assert stats.unique_dependencies >= 1
