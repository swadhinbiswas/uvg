"""Package identity model.

A package is identified by a 7-tuple:
(package_name, package_version, python_version, abi_tag, platform_tag, architecture, wheel_hash)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple


class Version(NamedTuple):
    """Semantic version representation."""

    major: int
    minor: int
    patch: int
    prerelease: str = ""

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            return f"{base}-{self.prerelease}"
        return base

    @classmethod
    def parse(cls, version_str: str) -> Version:
        """Parse a version string into a Version object.

        Args:
            version_str: Version string (e.g., "2.3.0", "1.0.0-alpha.1").

        Returns:
            Parsed Version object.

        Raises:
            ValueError: If the version string is invalid.
        """
        prerelease = ""
        if "-" in version_str:
            version_str, prerelease = version_str.split("-", 1)

        parts = version_str.split(".")
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(f"Invalid version string: {version_str}")

        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) == 3 else 0

        return cls(major=major, minor=minor, patch=patch, prerelease=prerelease)


@dataclass(frozen=True)
class PackageIdentity:
    """Unique identity of a package in the GVX store.

    A package is not identified by (name, version) alone.
    It is identified by the full 7-tuple including Python version,
    ABI, platform, architecture, and content hash.
    """

    name: str
    version: Version
    python_version: str
    abi_tag: str
    platform_tag: str
    architecture: str
    wheel_hash: str

    @property
    def object_name(self) -> str:
        """Generate the store object name.

        Returns:
            Object name in format: <hash>-<abi>-<platform>-<arch>
        """
        hash_short = self.wheel_hash.removeprefix("sha256:")[:16]
        return f"{hash_short}-{self.abi_tag}-{self.platform_tag}-{self.architecture}"

    @property
    def object_path(self) -> str:
        """Generate the store object path.

        Returns:
            Relative path within the store.
        """
        return f"objects/sha256/{self.object_name}"

    def __str__(self) -> str:
        return (
            f"{self.name}=={self.version} ({self.python_version}, {self.abi_tag}, "
            f"{self.platform_tag}, {self.architecture})"
        )


@dataclass(frozen=True)
class WheelInfo:
    """Parsed wheel filename information.

    Follows PEP 427 wheel naming convention:
    {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    """

    distribution: str
    version: Version
    build_tag: str = ""
    python_tag: str = ""
    abi_tag: str = ""
    platform_tag: str = ""
    filename: str = ""

    @classmethod
    def parse(cls, filename: str) -> WheelInfo:
        """Parse a wheel filename into its components.

        Args:
            filename: Wheel filename (e.g., "numpy-2.3.0-cp312-cp312-manylinux_2_17_x86_64.whl").

        Returns:
            Parsed WheelInfo object.

        Raises:
            ValueError: If the filename is not a valid wheel name.
        """
        if not filename.endswith(".whl"):
            raise ValueError(f"Not a wheel filename: {filename}")

        base = filename[:-4]
        parts = base.split("-")

        if len(parts) < 5:
            raise ValueError(f"Invalid wheel filename (too few parts): {filename}")

        distribution = parts[0]
        version = Version.parse(parts[1])

        build_tag = ""
        platform_start = -3

        if len(parts) > 5:
            build_tag = parts[2]
            platform_start = -3
        else:
            platform_start = -3

        python_tag = parts[platform_start]
        abi_tag = parts[platform_start + 1]
        platform_tag = "-".join(parts[platform_start + 2 :])

        return cls(
            distribution=distribution,
            version=version,
            build_tag=build_tag,
            python_tag=python_tag,
            abi_tag=abi_tag,
            platform_tag=platform_tag,
            filename=filename,
        )


@dataclass
class PackageMetadata:
    """Metadata extracted from package dist-info."""

    summary: str = ""
    description: str = ""
    author: str = ""
    author_email: str = ""
    license: str = ""
    home_page: str = ""
    classifiers: list[str] = field(default_factory=list)
    requires_python: str = ""
    provides_extra: list[str] = field(default_factory=list)


@dataclass
class EntryPoint:
    """Entry point definition from a package."""

    group: str
    name: str
    module: str
    function: str

    def __str__(self) -> str:
        return f"{self.name} = {self.module}:{self.function}"
