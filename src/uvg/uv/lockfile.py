"""UVG lockfile handling.

Parses and generates uvg.lock files that extend UV's lock file
with runtime fingerprints and additional metadata.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
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
    wheel_url: str = ""
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
            "wheel_url": self.wheel_url,
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
            wheel_url=data.get("wheel_url", ""),
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

    Converts UV's TOML lock file into UVG's internal representation,
    extracting wheel hashes and platform tags for the current system.
    """

    _PYTHON_VERSION_RE = re.compile(r"(?:cp(\d{2,3})|py(\d))")

    @staticmethod
    def parse_uv_lock(lockfile_path: Path) -> UVGLockfile:
        """Parse a UV lock file.

        Extracts wheel hashes and platform tags for the current system.

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
        in_wheels = False
        wheels_content = ""

        current_python = f"{platform.python_version_tuple()[0]}.{platform.python_version_tuple()[1]}"
        current_platform = UVLockfileParser._get_current_platform()

        for line in content.splitlines():
            stripped = line.strip()

            if stripped.startswith("requires-python"):
                match = re.search(r'"([^"]+)"', stripped)
                if match:
                    lockfile.python_version = match.group(1)

            if stripped.startswith("[[package]]"):
                if current_pkg and "name" in current_pkg:
                    pkg = UVLockfileParser._finalize_package(
                        current_pkg, wheels_content, current_python, current_platform
                    )
                    if pkg:
                        packages.append(pkg)
                current_pkg = {}
                in_package = True
                in_wheels = False
                wheels_content = ""
            elif in_package:
                if stripped.startswith("name ="):
                    current_pkg["name"] = stripped.split("=", 1)[1].strip().strip('"')
                elif stripped.startswith("version ="):
                    current_pkg["version"] = stripped.split("=", 1)[1].strip().strip('"')
                elif stripped.startswith("wheels = ["):
                    in_wheels = True
                    wheels_content = stripped
                elif in_wheels:
                    wheels_content += " " + stripped
                    if stripped.endswith("]"):
                        in_wheels = False
                elif stripped.startswith("dependencies ="):
                    deps_str = stripped.split("=", 1)[1].strip()
                    current_pkg["dependencies"] = UVLockfileParser._parse_dependencies(deps_str)

        if current_pkg and "name" in current_pkg:
            pkg = UVLockfileParser._finalize_package(current_pkg, wheels_content, current_python, current_platform)
            if pkg:
                packages.append(pkg)

        lockfile.packages = packages
        lockfile.platform = current_platform
        lockfile.architecture = platform.machine()

        return lockfile

    @staticmethod
    def _get_current_platform() -> str:
        """Get the current platform tag."""
        import sysconfig

        plat = sysconfig.get_platform()
        return plat.replace("-", "_")

    @staticmethod
    def _platform_matches(wheel_platform: str, current_platform: str) -> bool:
        """Check if a wheel platform is compatible with the current platform.

        Args:
            wheel_platform: Platform tag from wheel filename.
            current_platform: Current system platform.

        Returns:
            True if the wheel is compatible.
        """
        if wheel_platform == "any":
            return True

        wheel_lower = wheel_platform.lower()
        current_lower = current_platform.lower()

        if wheel_lower == current_lower:
            return True

        if "manylinux" in wheel_lower and current_lower.startswith("linux"):
            return True

        if "musllinux" in wheel_lower and current_lower.startswith("linux"):
            return True

        if "macosx" in wheel_lower and current_lower.startswith("macosx"):
            return True

        return wheel_lower.startswith("win") and current_lower.startswith("win")

    @staticmethod
    def _finalize_package(
        pkg_data: dict[str, Any],
        wheels_str: str,
        python_version: str,
        current_platform: str,
    ) -> LockfilePackage | None:
        """Extract wheel info for current platform from wheels string.

        Args:
            pkg_data: Package data from lockfile.
            wheels_str: Wheels section as a string.
            python_version: Current Python version.
            current_platform: Current platform tag.

        Returns:
            LockfilePackage with wheel hash and platform info, or None.
        """
        name = pkg_data.get("name", "")
        version = pkg_data.get("version", "")
        deps = pkg_data.get("dependencies", [])

        python_major_minor = python_version.replace(".", "")

        hash_val = ""
        abi = ""
        plat = ""
        wheel_name = ""
        wheel_url = ""

        # Extract all wheel entries from the wheels string
        wheel_entries = re.findall(r"\{[^}]+\}", wheels_str)

        for wheel_entry in wheel_entries:
            url_match = re.search(r'url = "([^"]+)"', wheel_entry)
            hash_match = re.search(r'hash = "([^"]+)"', wheel_entry)

            if not url_match or not hash_match:
                continue

            url = url_match.group(1)
            whl_hash = hash_match.group(1)

            filename = url.split("/")[-1]
            if not filename.endswith(".whl"):
                continue

            parts = filename.replace(".whl", "").split("-")
            if len(parts) < 5:
                continue

            pkg_name = parts[0]
            python_tag = parts[2]
            abi_tag = parts[3]
            platform_tag = "-".join(parts[4:])

            if pkg_name.lower() != name.lower():
                continue

            python_match = UVLockfileParser._PYTHON_VERSION_RE.search(python_tag)
            if not python_match:
                continue

            cp_version = python_match.group(1)
            py_version = python_match.group(2)

            if cp_version:
                wheel_python = cp_version
            elif py_version:
                wheel_python = python_major_minor
            else:
                continue

            if wheel_python != python_major_minor:
                continue

            if UVLockfileParser._platform_matches(platform_tag, current_platform):
                hash_val = whl_hash
                abi = abi_tag
                plat = platform_tag
                wheel_name = filename
                wheel_url = url
                break

        if not hash_val:
            return None

        return LockfilePackage(
            name=name,
            version=version,
            wheel=wheel_name,
            wheel_url=wheel_url,
            hash=hash_val,
            abi=abi,
            platform=plat,
            dependencies=deps,
        )

    @staticmethod
    def _parse_dependencies(deps_str: str) -> list[str]:
        """Parse dependencies string.

        Args:
            deps_str: Dependencies string from lockfile.

        Returns:
            List of dependency names.
        """
        deps_str = deps_str.strip("[]").strip()
        if not deps_str:
            return []

        deps = []
        for item in deps_str.split(","):
            item = item.strip().strip('"')
            if item:
                dep_name = item.split(">=")[0].split("==")[0].split("<")[0].split(">")[0].strip()
                if dep_name:
                    deps.append(dep_name)

        return deps
