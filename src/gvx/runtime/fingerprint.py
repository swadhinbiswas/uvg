"""Runtime fingerprinting.

Computes deterministic fingerprints for runtime reuse and caching.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class FingerprintInput:
    """Inputs to fingerprint computation.

    All fields must be present and deterministic.
    """

    python_version: str
    platform: str
    architecture: str
    abi: str
    manifest_version: int
    packages: tuple[tuple[str, str, str], ...]

    @classmethod
    def create(
        cls,
        python_version: str,
        platform: str,
        architecture: str,
        abi: str,
        manifest_version: int,
        packages: dict[str, tuple[str, str]],
    ) -> FingerprintInput:
        """Create a fingerprint input from package data.

        Args:
            python_version: Python version string (e.g., "3.12").
            platform: Platform string (e.g., "linux").
            architecture: Architecture string (e.g., "x86_64").
            abi: ABI tag string (e.g., "cp312").
            manifest_version: Manifest format version.
            packages: Dict mapping package name to (version, hash).

        Returns:
            FingerprintInput with sorted package tuple.
        """
        sorted_packages = tuple((name, version, pkg_hash) for name, (version, pkg_hash) in sorted(packages.items()))
        return cls(
            python_version=python_version,
            platform=platform,
            architecture=architecture,
            abi=abi,
            manifest_version=manifest_version,
            packages=sorted_packages,
        )


def compute_fingerprint(input_data: FingerprintInput) -> str:
    """Compute a deterministic runtime fingerprint.

    The fingerprint is a SHA-256 hash of all runtime inputs,
    formatted in a deterministic order.

    Args:
        input_data: Fingerprint input data.

    Returns:
        Fingerprint string in format "runtime_<8_hex_chars>".
    """
    components = [
        str(input_data.manifest_version),
        input_data.python_version,
        input_data.platform,
        input_data.architecture,
        input_data.abi,
    ]

    for name, version, pkg_hash in input_data.packages:
        components.append(f"{name}=={version}:{pkg_hash}")

    content = "|".join(components)
    hash_value = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"runtime_{hash_value[:8]}"
