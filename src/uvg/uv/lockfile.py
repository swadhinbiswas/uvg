"""UVG lockfile handling.

Parses and generates uvg.lock files that extend UV's lock file
with runtime fingerprints and additional metadata.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from uvg.runtime.manifest import RuntimeManifest


@dataclass
class LockfilePackage:
    """A package entry in the UVG lockfile."""

    name: str
    version: str
    wheel: str = ""
    hash: str = ""
    abi: str = ""
    platform: str = ""
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "name": self.name,
            "version": self.version,
            "wheel": self.wheel,
            "hash": self.hash,
            "abi": self.abi,
            "platform": self.platform,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LockfilePackage:
        """Create from dictionary.

        Args:
            data: Dictionary representation.

        Returns:
            LockfilePackage instance.
        """
        return cls(
            name=data["name"],
            version=data["version"],
            wheel=data.get("wheel", ""),
            hash=data.get("hash", ""),
            abi=data.get("abi", ""),
            platform=data.get("platform", ""),
            dependencies=data.get("dependencies", []),
        )


@dataclass
class UVGLockfile:
    """UVG lockfile with extended metadata.

    Extends UV's lock file with runtime fingerprints,
    wheel hashes, and platform metadata.
    """

    LOCKFILE_VERSION = 1

    version: int = LOCKFILE_VERSION
    python_version: str = ""
    platform: str = ""
    architecture: str = ""
    fingerprint: str = ""
    packages: list[LockfilePackage] = field(default_factory=list)
    metadata_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "metadata": {
                "version": self.version,
                "python_version": self.python_version,
                "platform": self.platform,
                "architecture": self.architecture,
                "fingerprint": self.fingerprint,
                "metadata_version": self.metadata_version,
            },
            "packages": [pkg.to_dict() for pkg in self.packages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UVGLockfile:
        """Create from dictionary.

        Args:
            data: Dictionary representation.

        Returns:
            UVGLockfile instance.
        """
        metadata = data.get("metadata", {})
        packages = [LockfilePackage.from_dict(pkg) for pkg in data.get("packages", [])]
        return cls(
            version=metadata.get("version", cls.LOCKFILE_VERSION),
            python_version=metadata.get("python_version", ""),
            platform=metadata.get("platform", ""),
            architecture=metadata.get("architecture", ""),
            fingerprint=metadata.get("fingerprint", ""),
            packages=packages,
            metadata_version=metadata.get("metadata_version", 1),
        )

    def to_json(self) -> str:
        """Serialize to JSON string.

        Returns:
            JSON string representation.
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> UVGLockfile:
        """Deserialize from JSON string.

        Args:
            json_str: JSON string representation.

        Returns:
            UVGLockfile instance.
        """
        return cls.from_dict(json.loads(json_str))

    def save(self, path: Path) -> None:
        """Save lockfile to disk.

        Args:
            path: Path to save the lockfile.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> UVGLockfile:
        """Load lockfile from disk.

        Args:
            path: Path to the lockfile.

        Returns:
            UVGLockfile instance.
        """
        content = path.read_text(encoding="utf-8")
        return cls.from_json(content)

    def compute_hash(self) -> str:
        """Compute the lockfile hash for verification.

        Returns:
            SHA-256 hash of the lockfile content.
        """
        content = self.to_json()
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def to_runtime_manifest(self) -> RuntimeManifest:
        """Convert lockfile to runtime manifest.

        Returns:
            RuntimeManifest instance.
        """
        from uvg.runtime.manifest import ManifestPackage

        packages: dict[str, ManifestPackage] = {}
        for pkg in self.packages:
            packages[pkg.name] = ManifestPackage(
                name=pkg.name,
                version=pkg.version,
                wheel_hash=pkg.hash,
                store_path="",
                abi=pkg.abi,
                platform=pkg.platform,
                dependencies=pkg.dependencies,
            )

        return RuntimeManifest(
            version=self.version,
            fingerprint=self.fingerprint,
            python_version=self.python_version,
            platform=self.platform,
            architecture=self.architecture,
            packages=packages,
        )


class UVLockfileParser:
    """Parses UV's uv.lock file format.

    Converts UV's TOML lock file into UVG's internal representation.
    """

    @staticmethod
    def parse_uv_lock(lockfile_path: Path) -> UVGLockfile:
        """Parse a UV lock file.

        Args:
            lockfile_path: Path to uv.lock.

        Returns:
            UVGLockfile instance.

        Raises:
            FileNotFoundError: If lockfile does not exist.
        """
        if not lockfile_path.exists():
            raise FileNotFoundError(f"UV lockfile not found: {lockfile_path}")

        content = lockfile_path.read_text(encoding="utf-8")

        lockfile = UVGLockfile()
        packages: list[LockfilePackage] = []

        current_pkg: dict[str, Any] = {}
        in_package = False

        for line in content.splitlines():
            stripped = line.strip()

            if stripped.startswith("[[package]]"):
                if current_pkg and "name" in current_pkg:
                    packages.append(
                        LockfilePackage(
                            name=current_pkg.get("name", ""),
                            version=current_pkg.get("version", ""),
                            wheel=current_pkg.get("wheel", ""),
                            hash=current_pkg.get("hash", ""),
                        )
                    )
                current_pkg = {}
                in_package = True
            elif in_package and "=" in stripped:
                key, value = stripped.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"')
                if key in ("name", "version", "source"):
                    current_pkg[key] = value

        if current_pkg and "name" in current_pkg:
            packages.append(
                LockfilePackage(
                    name=current_pkg.get("name", ""),
                    version=current_pkg.get("version", ""),
                    wheel=current_pkg.get("wheel", ""),
                    hash=current_pkg.get("hash", ""),
                )
            )

        lockfile.packages = packages
        return lockfile
