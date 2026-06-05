"""Tool execution module.

Provides functionality for running tools in temporary environments,
similar to uvx. Tools are installed in isolated environments and
cached for reuse.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolSpec:
    """A tool specification."""

    name: str
    version: str | None = None
    extras: list[str] = field(default_factory=list)

    def to_requirement(self) -> str:
        """Convert to requirement string."""
        req = self.name
        if self.extras:
            req += f"[{','.join(self.extras)}]"
        if self.version:
            req += f"=={self.version}"
        return req

    def cache_key(self) -> str:
        """Generate a cache key for this tool."""
        return hashlib.sha256(self.to_requirement().encode()).hexdigest()[:12]


@dataclass
class ToolEnvironment:
    """A cached tool environment."""

    tools: list[ToolSpec]
    path: Path
    python_version: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tools": [{"name": t.name, "version": t.version, "extras": t.extras} for t in self.tools],
            "path": str(self.path),
            "python_version": self.python_version,
            "created_at": self.created_at,
        }


class ToolCache:
    """Manages cached tool environments."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize tool cache.

        Args:
            cache_dir: Cache directory. Defaults to ~/.uvg/tools.
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".uvg" / "tools"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.cache_dir / "index.json"
        self._index: dict[str, ToolEnvironment] = self._load_index()

    def _load_index(self) -> dict[str, ToolEnvironment]:
        """Load the tool cache index."""
        if self.index_path.exists():
            data = json.loads(self.index_path.read_text())
            return {
                key: ToolEnvironment(
                    tools=[ToolSpec(**t) for t in env_data["tools"]],
                    path=Path(env_data["path"]),
                    python_version=env_data["python_version"],
                    created_at=env_data["created_at"],
                )
                for key, env_data in data.items()
            }
        return {}

    def _save_index(self) -> None:
        """Save the tool cache index."""
        data = {key: env.to_dict() for key, env in self._index.items()}
        self.index_path.write_text(json.dumps(data, indent=2))

    def get_environment(self, tools: list[ToolSpec]) -> Path | None:
        """Get a cached environment for the given tools.

        Args:
            tools: List of tool specifications.

        Returns:
            Path to cached environment or None.
        """
        cache_key = self._compute_cache_key(tools)
        if cache_key in self._index:
            env = self._index[cache_key]
            if env.path.exists():
                return env.path
        return None

    def register_environment(
        self,
        tools: list[ToolSpec],
        path: Path,
        python_version: str,
    ) -> None:
        """Register a new tool environment in the cache.

        Args:
            tools: List of tool specifications.
            path: Path to the environment.
            python_version: Python version used.
        """
        from datetime import datetime, timezone

        cache_key = self._compute_cache_key(tools)
        self._index[cache_key] = ToolEnvironment(
            tools=tools,
            path=path,
            python_version=python_version,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._save_index()

    def _compute_cache_key(self, tools: list[ToolSpec]) -> str:
        """Compute a cache key for a set of tools."""
        tool_strs = sorted(t.to_requirement() for t in tools)
        return hashlib.sha256("|".join(tool_strs).encode()).hexdigest()[:12]

    def clear(self) -> None:
        """Clear all cached tool environments."""
        for env in self._index.values():
            if env.path.exists():
                import shutil

                shutil.rmtree(env.path)
        self._index.clear()
        self._save_index()


class ToolExecutor:
    """Executes tools in temporary or cached environments."""

    def __init__(self, cache: ToolCache | None = None) -> None:
        """Initialize tool executor.

        Args:
            cache: Tool cache instance.
        """
        self.cache = cache or ToolCache()

    def run(
        self,
        tools: list[ToolSpec],
        command: list[str],
        python_version: str | None = None,
        from_packages: list[str] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        """Run a command with tools installed in an isolated environment.

        Args:
            tools: List of tool specifications to install.
            command: Command to execute.
            python_version: Optional Python version constraint.
            from_packages: Additional packages to install from.

        Returns:
            Subprocess result.
        """
        env_path = self.cache.get_environment(tools)

        if env_path is None:
            env_path = self._create_environment(tools, python_version)

        return self._run_in_environment(env_path, command, tools)

    def _create_environment(
        self,
        tools: list[ToolSpec],
        python_version: str | None = None,
    ) -> Path:
        """Create a new tool environment.

        Args:
            tools: List of tool specifications.
            python_version: Optional Python version.

        Returns:
            Path to the created environment.
        """
        import tempfile

        env_dir = Path(tempfile.mkdtemp(prefix="uvg-tool-"))
        venv_path = env_dir / ".venv"

        cmd = ["uv", "venv", str(venv_path)]
        if python_version:
            cmd.extend(["--python", python_version])

        subprocess.run(cmd, capture_output=True, check=True)

        requirements = [t.to_requirement() for t in tools]
        pip_cmd = [
            str(venv_path / "bin" / "uv"),
            "pip",
            "install",
            *requirements,
        ]
        subprocess.run(pip_cmd, capture_output=True, check=True)

        py_version = python_version or self._get_python_version(venv_path)
        self.cache.register_environment(tools, env_dir, py_version)

        return env_dir

    def _run_in_environment(
        self,
        env_path: Path,
        command: list[str],
        tools: list[ToolSpec],
    ) -> subprocess.CompletedProcess[bytes]:
        """Run a command in a tool environment.

        Args:
            env_path: Path to the environment.
            command: Command to execute.
            tools: List of tool specifications.

        Returns:
            Subprocess result.
        """
        venv_bin = env_path / ".venv" / "bin"
        env = {
            "PATH": f"{venv_bin}:{os.environ.get('PATH', '')}",
            "VIRTUAL_ENV": str(venv_bin.parent),
        }

        return subprocess.run(
            command,
            env={**dict(os.environ), **env},
            cwd=Path.cwd(),
        )

    def _get_python_version(self, venv_path: Path) -> str:
        """Get the Python version from a virtual environment.

        Args:
            venv_path: Path to the virtual environment.

        Returns:
            Python version string.
        """
        result = subprocess.run(
            [str(venv_path / "bin" / "python"), "--version"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip().split()[1]
