"""Runtime manifest.

Defines the structure of a runtime manifest that maps packages
to store objects and configures the runtime environment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ManifestPackage:
    """A package entry in the runtime manifest."""

    name: str
    version: str
    wheel_hash: str
    store_path: str
    abi: str
    platform: str
    dependencies: list[str] = field(default_factory=list)
    is_native: bool = False
    editable: bool = False
    source_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        result: dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "wheel_hash": self.wheel_hash,
            "store_path": self.store_path,
            "abi": self.abi,
            "platform": self.platform,
            "dependencies": self.dependencies,
            "is_native": self.is_native,
            "editable": self.editable,
        }
        if self.source_path:
            result["source_path"] = self.source_path
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManifestPackage:
        """Create from dictionary.

        Args:
            data: Dictionary representation.

        Returns:
            ManifestPackage instance.
        """
        return cls(
            name=data["name"],
            version=data["version"],
            wheel_hash=data["wheel_hash"],
            store_path=data["store_path"],
            abi=data["abi"],
            platform=data["platform"],
            dependencies=data.get("dependencies", []),
            is_native=data.get("is_native", False),
            editable=data.get("editable", False),
            source_path=data.get("source_path", ""),
        )


@dataclass
class ManifestEntryPoint:
    """An entry point script definition."""

    name: str
    module: str
    function: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "name": self.name,
            "module": self.module,
            "function": self.function,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManifestEntryPoint:
        """Create from dictionary.

        Args:
            data: Dictionary representation.

        Returns:
            ManifestEntryPoint instance.
        """
        return cls(
            name=data["name"],
            module=data["module"],
            function=data["function"],
        )


@dataclass
class RuntimeManifest:
    """Runtime manifest defining the execution environment.

    The manifest is the authoritative source for what packages
    are available in a runtime and how to construct the import path.
    """

    MANIFEST_VERSION = 1

    version: int = MANIFEST_VERSION
    fingerprint: str = ""
    python_version: str = ""
    platform: str = ""
    architecture: str = ""
    abi: str = ""
    packages: dict[str, ManifestPackage] = field(default_factory=dict)
    entry_points: dict[str, ManifestEntryPoint] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "version": self.version,
            "fingerprint": self.fingerprint,
            "python_version": self.python_version,
            "platform": self.platform,
            "architecture": self.architecture,
            "abi": self.abi,
            "created_at": self.created_at,
            "packages": {name: pkg.to_dict() for name, pkg in self.packages.items()},
            "entry_points": {name: ep.to_dict() for name, ep in self.entry_points.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeManifest:
        """Create from dictionary.

        Args:
            data: Dictionary representation.

        Returns:
            RuntimeManifest instance.
        """
        packages = {name: ManifestPackage.from_dict(pkg_data) for name, pkg_data in data.get("packages", {}).items()}
        entry_points = {
            name: ManifestEntryPoint.from_dict(ep_data) for name, ep_data in data.get("entry_points", {}).items()
        }
        return cls(
            version=data.get("version", cls.MANIFEST_VERSION),
            fingerprint=data.get("fingerprint", ""),
            python_version=data.get("python_version", ""),
            platform=data.get("platform", ""),
            architecture=data.get("architecture", ""),
            abi=data.get("abi", ""),
            created_at=data.get("created_at", ""),
            packages=packages,
            entry_points=entry_points,
        )

    def to_json(self) -> str:
        """Serialize to JSON string.

        Returns:
            JSON string representation.
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> RuntimeManifest:
        """Deserialize from JSON string.

        Args:
            json_str: JSON string representation.

        Returns:
            RuntimeManifest instance.
        """
        return cls.from_dict(json.loads(json_str))

    def save(self, path: Path) -> None:
        """Save manifest to file.

        Args:
            path: Path to save the manifest.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> RuntimeManifest:
        """Load manifest from file.

        Args:
            path: Path to the manifest file.

        Returns:
            RuntimeManifest instance.
        """
        content = path.read_text(encoding="utf-8")
        return cls.from_json(content)

    def get_site_packages_paths(self) -> list[str]:
        """Get all site-packages paths for import path construction.

        Returns:
            List of site-packages directory paths.
        """
        paths = []
        for pkg in self.packages.values():
            if pkg.editable and pkg.source_path:
                paths.append(pkg.source_path)
            else:
                paths.append(pkg.store_path)
        return paths

    def has_package(self, name: str) -> bool:
        """Check if a package is in the manifest.

        Args:
            name: Package name.

        Returns:
            True if the package is in the manifest.
        """
        return name in self.packages
