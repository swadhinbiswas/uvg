"""Runtime builder.

Constructs runtime directories from manifests, including
symlink creation, entry point generation, and verification.
"""

from __future__ import annotations

import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from uvg.core.exceptions import (
    RuntimeNotFoundError,
)
from uvg.runtime.fingerprint import FingerprintInput, compute_fingerprint
from uvg.runtime.manifest import ManifestEntryPoint, ManifestPackage, RuntimeManifest

ENTRY_POINT_SCRIPT = '''#!/usr/bin/env {python_exe}
"""UVG entry point script for {name}."""
import sys
import os

_runtime_dir = os.path.dirname(os.path.abspath(__file__))
_manifest_path = os.path.join(_runtime_dir, "..", "manifest.json")

with open(_manifest_path, encoding="utf-8") as _f:
    import json
    _manifest = json.load(_f)

for _pkg in _manifest["packages"].values():
    _site_pkgs = os.path.expanduser(_pkg["store_path"])
    if _site_pkgs not in sys.path:
        sys.path.insert(0, _site_pkgs)

from {module} import {function}
sys.exit({function}())
'''

MANIFEST_VERSION = 1


class RuntimeBuilder:
    """Builds runtime directories from package manifests.

    The runtime directory structure:
    project/.uvg/runtime/
        manifest.json
        fingerprint
        site-packages/
            numpy -> ~/.uvg/store/objects/sha256/<hash>/...
            pandas -> ~/.uvg/store/objects/sha256/<hash>/...
        bin/
            pytest
            black
    """

    def __init__(
        self,
        runtime_dir: Path,
        store_path: Path | None = None,
        python_exe: str | None = None,
    ) -> None:
        """Initialize runtime builder.

        Args:
            runtime_dir: Path to the runtime directory.
            store_path: Path to the UVG store. Defaults to ~/.uvg/store.
            python_exe: Path to Python executable. Defaults to sys.executable.
        """
        self.runtime_dir = runtime_dir
        self.site_packages_dir = runtime_dir / "site-packages"
        self.bin_dir = runtime_dir / "bin"

        if store_path is None:
            store_path = Path.home() / ".uvg" / "store"
        self.store_path = store_path

        self.python_exe = python_exe or sys.executable

    def build(
        self,
        packages: dict[str, dict[str, Any]],
        python_version: str,
        platform: str,
        architecture: str,
        abi: str,
        entry_points: dict[str, dict[str, str]] | None = None,
    ) -> RuntimeManifest:
        """Build a runtime from package specifications.

        Args:
            packages: Dict mapping package name to package info.
                Each package info must have: version, wheel_hash,
                abi, platform, dependencies, is_native.
            python_version: Python version string.
            platform: Platform string.
            architecture: Architecture string.
            abi: ABI tag string.
            entry_points: Optional dict of entry point definitions.

        Returns:
            The constructed RuntimeManifest.
        """
        self._clean_runtime()

        manifest_packages: dict[str, ManifestPackage] = {}
        package_hashes: dict[str, tuple[str, str]] = {}

        for name, pkg_info in packages.items():
            store_obj_path = self._resolve_store_path(
                pkg_info["wheel_hash"],
                pkg_info["abi"],
                pkg_info["platform"],
                architecture,
            )

            manifest_pkg = ManifestPackage(
                name=name,
                version=pkg_info["version"],
                wheel_hash=pkg_info["wheel_hash"],
                store_path=str(store_obj_path),
                abi=pkg_info["abi"],
                platform=pkg_info["platform"],
                dependencies=pkg_info.get("dependencies", []),
                is_native=pkg_info.get("is_native", False),
            )
            manifest_packages[name] = manifest_pkg
            package_hashes[name] = (pkg_info["version"], pkg_info["wheel_hash"])

        fp_input = FingerprintInput.create(
            python_version=python_version,
            platform=platform,
            architecture=architecture,
            abi=abi,
            manifest_version=MANIFEST_VERSION,
            packages=package_hashes,
        )
        fingerprint = compute_fingerprint(fp_input)

        manifest = RuntimeManifest(
            version=MANIFEST_VERSION,
            fingerprint=fingerprint,
            python_version=python_version,
            platform=platform,
            architecture=architecture,
            abi=abi,
            packages=manifest_packages,
            entry_points={},
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        if entry_points:
            for ep_name, ep_info in entry_points.items():
                manifest.entry_points[ep_name] = ManifestEntryPoint(
                    name=ep_name,
                    module=ep_info["module"],
                    function=ep_info["function"],
                )

        self._create_directories()
        self._create_symlinks(manifest)
        self._create_entry_points(manifest)
        self._write_manifest(manifest)
        self._write_fingerprint(fingerprint)

        return manifest

    def _clean_runtime(self) -> None:
        """Remove existing runtime directory."""
        if self.runtime_dir.exists():
            shutil.rmtree(self.runtime_dir)

    def _create_directories(self) -> None:
        """Create runtime directories."""
        self.site_packages_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_store_path(
        self,
        wheel_hash: str,
        abi: str,
        platform: str,
        architecture: str,
    ) -> Path:
        """Resolve the store path for a package.

        Args:
            wheel_hash: Package wheel hash.
            abi: ABI tag.
            platform: Platform tag.
            architecture: Architecture.

        Returns:
            Path to the store object.
        """
        hash_short = wheel_hash.removeprefix("sha256:")[:16]
        return self.store_path / "objects" / "sha256" / f"{hash_short}-{abi}-{platform}-{architecture}"

    def _create_symlinks(self, manifest: RuntimeManifest) -> None:
        """Create symlinks from runtime to store objects.

        Args:
            manifest: Runtime manifest.
        """
        for pkg in manifest.packages.values():
            if pkg.editable and pkg.source_path:
                source = Path(pkg.source_path)
            else:
                store_obj = Path(pkg.store_path)
                source = store_obj / "lib" / f"python{manifest.python_version}" / "site-packages" / pkg.name

            if not source.exists():
                continue

            target = self.site_packages_dir / pkg.name
            if target.exists() or target.is_symlink():
                target.unlink()

            target.symlink_to(source)

            dist_info = source.parent / f"{pkg.name}-{pkg.version}.dist-info"
            if dist_info.exists():
                dist_link = self.site_packages_dir / f"{pkg.name}-{pkg.version}.dist-info"
                if dist_link.exists() or dist_link.is_symlink():
                    dist_link.unlink()
                dist_link.symlink_to(dist_info)

    def _create_entry_points(self, manifest: RuntimeManifest) -> None:
        """Create entry point scripts.

        Args:
            manifest: Runtime manifest.
        """
        for ep in manifest.entry_points.values():
            script = ENTRY_POINT_SCRIPT.format(
                python_exe=self.python_exe,
                name=ep.name,
                module=ep.module,
                function=ep.function,
            )
            script_path = self.bin_dir / ep.name
            script_path.write_text(script, encoding="utf-8")
            script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def _write_manifest(self, manifest: RuntimeManifest) -> None:
        """Write manifest to file.

        Args:
            manifest: Runtime manifest.
        """
        manifest.save(self.runtime_dir / "manifest.json")

    def _write_fingerprint(self, fingerprint: str) -> None:
        """Write fingerprint to file.

        Args:
            fingerprint: Runtime fingerprint string.
        """
        (self.runtime_dir / "fingerprint").write_text(fingerprint, encoding="utf-8")

    def verify(self) -> list[str]:
        """Verify runtime integrity.

        Returns:
            List of verification errors (empty if all pass).
        """
        errors: list[str] = []

        manifest_path = self.runtime_dir / "manifest.json"
        if not manifest_path.exists():
            errors.append("Manifest file missing")
            return errors

        try:
            manifest = RuntimeManifest.load(manifest_path)
        except Exception as e:
            errors.append(f"Failed to load manifest: {e}")
            return errors

        for pkg in manifest.packages.values():
            if pkg.editable and pkg.source_path:
                if not Path(pkg.source_path).exists():
                    errors.append(f"Editable source path missing: {pkg.name}")
            else:
                symlink = self.site_packages_dir / pkg.name
                if not symlink.exists():
                    errors.append(f"Package symlink missing: {pkg.name}")

        stored_fp = (self.runtime_dir / "fingerprint").read_text(encoding="utf-8").strip()
        if stored_fp != manifest.fingerprint:
            errors.append(f"Fingerprint mismatch: stored={stored_fp}, manifest={manifest.fingerprint}")

        return errors

    def get_python_path(self) -> list[str]:
        """Get the PYTHONPATH for this runtime.

        Returns:
            List of paths to add to PYTHONPATH.
        """
        manifest_path = self.runtime_dir / "manifest.json"
        if not manifest_path.exists():
            raise RuntimeNotFoundError(str(self.runtime_dir))

        manifest = RuntimeManifest.load(manifest_path)
        return manifest.get_site_packages_paths()

    def load_manifest(self) -> RuntimeManifest:
        """Load the runtime manifest.

        Returns:
            RuntimeManifest instance.

        Raises:
            RuntimeNotFoundError: If manifest is missing.
        """
        manifest_path = self.runtime_dir / "manifest.json"
        if not manifest_path.exists():
            raise RuntimeNotFoundError(str(self.runtime_dir))
        return RuntimeManifest.load(manifest_path)

    def get_fingerprint(self) -> str:
        """Get the runtime fingerprint.

        Returns:
            Fingerprint string.

        Raises:
            RuntimeNotFoundError: If fingerprint file is missing.
        """
        fp_path = self.runtime_dir / "fingerprint"
        if not fp_path.exists():
            raise RuntimeNotFoundError(str(self.runtime_dir))
        return fp_path.read_text(encoding="utf-8").strip()
